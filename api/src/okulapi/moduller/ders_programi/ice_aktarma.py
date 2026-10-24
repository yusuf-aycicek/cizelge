"""Excel'den içe aktarma (yapım sırası 8a, ADR 0021): öğretmenler, sınıflar (şube grubuyla), dersler
ve ders dağılımı.

Akış iki adımdır ve ikisi de aynı dosyayı okur:
1. **Önizleme** (`onizle`): dosya okunur, her satır için ne olacağı hesaplanır (eklenecek,
   güncellenecek, değişmeyen, hatalı). Hiçbir şey yazılmaz.
2. **Kaydet** (`kaydet`): aynı plan yeniden hesaplanır; hatalı satır varsa hiçbir şey yazılmaz.
   Önizlemedeki planın özeti (`ozet`) verilir; veri arada değiştiyse plan da değişir ve kayıt
   reddedilir (409), kullanıcı onaylamadığı bir şeyi kaydetmez. Bütün yazma tek işlemdir.

Eşleştirme adla yapılır, kimlikle değil: Excel'i dolduran kullanıcı kimlik bilmez. Ad karşılaştırması
`anahtar` ile Türkçe büyük/küçük harf ("İ/i", "I/ı") ve boşluk farklarını yok sayar; böylece "9-A"
ile "9 - a" ya da "AYŞE YILMAZ" ile "Ayşe  Yılmaz" aynı kayıttır ve çoğaltılmaz. Var olan kaydın
adı değiştirilmez (okulda yazıldığı gibi kalır).

Boş hücre "değiştirme" demektir: var olan öğretmenin branşı, şubenin grubu, atamanın öğretmeni boş
bırakılırsa olduğu gibi kalır.

Bu modülde durur, çekirdekte değil: dosya ders dağılımını (bu modülün tablosu) da içerir; modül
çekirdeğe bağımlı olabilir, tersi olamaz (ADR 0008). Okul filtresi depolardan gelir: plan yalnızca
oturumun okulunun kayıtlarıyla eşleşir.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.exc import IntegrityError

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, SinifDeposu, SubeGrubuDeposu
from okulapi.cekirdek.ders_renkleri import siradaki_renk
from okulapi.cekirdek.modeller import Ders, Ogretmen, Sinif, SubeGrubu
from okulapi.cekirdek.servisler import GecersizVeri, KayitCakismasi
from okulapi.moduller.ders_programi.depo import DersAtamaDeposu
from okulapi.moduller.ders_programi.modeller import DersAtama

MAKS_BOYUT = 2 * 1024 * 1024  # yüklenen dosya (bayt)
MAKS_ACIK_BOYUT = 40 * 1024 * 1024  # dosyanın içindeki XML'lerin toplamı (sıkıştırma bombasına karşı)
MAKS_SATIR = 2000  # bir sayfadaki veri satırı
MAKS_HAM_SATIR = 10000  # boşlar dahil okunan satır
MAKS_SAAT = 40


@dataclass(frozen=True)
class Sutun:
    alan: str
    baslik: str
    zorunlu: bool = False
    genislik: int = 18


@dataclass(frozen=True)
class Sayfa:
    tur: str
    ad: str
    aciklama: str
    sutunlar: tuple[Sutun, ...]
    ornek: tuple[Any, ...]


SAYFALAR = (
    Sayfa("ogretmen", "Öğretmenler",
          "Her satır bir öğretmen. Okulda aynı adlı öğretmen varsa yeni kayıt açılmaz, branşı güncellenir.",
          (Sutun("ad", "Ad Soyad", True, 28), Sutun("brans", "Branş", genislik=22)),
          ("Ayşe Yılmaz (örnek)", "Matematik")),
    Sayfa("sinif", "Sınıflar",
          "Her satır bir şube. Seviye 1-12. Şube grubu isteğe bağlıdır (ör. 11 Sayısal); yoksa açılır.",
          (Sutun("ad", "Şube", True, 14), Sutun("seviye", "Seviye", genislik=10), Sutun("grup", "Şube grubu", genislik=22)),
          ("9-A (örnek)", 9, None)),
    Sayfa("ders", "Dersler",
          "Her satır bir ders. Kısa ad çizelgede dar hücrelerde görünür (en çok 20 harf).",
          (Sutun("ad", "Ders", True, 30), Sutun("kisa_ad", "Kısa ad", genislik=12)),
          ("Matematik (örnek)", "MAT")),
    Sayfa("dagilim", "Ders dağılımı",
          "Her satır bir şubenin bir dersi: haftalık saat ve öğretmen. Şube, ders ve öğretmen okulda ya da "
          "bu dosyanın diğer sayfalarında olmalı. Öğretmen boş bırakılabilir.",
          (Sutun("sube", "Şube", True, 14), Sutun("ders", "Ders", True, 30), Sutun("saat", "Haftalık saat", True, 14),
           Sutun("ogretmen", "Öğretmen", genislik=28)),
          ("9-A (örnek)", "Matematik", 6, "Ayşe Yılmaz")),
)
SAYFA = {s.tur: s for s in SAYFALAR}
ORNEK = "(örnek)"
ORNEK_NOTU = f"İlk sütunu “{ORNEK}” ile biten satır örnektir ve okunmaz; silebilir ya da üzerine yazabilirsiniz."


def anahtar(metin: Any) -> str:
    """Eşleştirme anahtarı: Türkçe küçük harf, boşluklar tekleşmiş, tire/eğik çizgi çevresi boşluksuz."""
    m = unicodedata.normalize("NFC", str(metin)).replace("I", "ı").replace("İ", "i").lower()
    m = re.sub(r"\s+", " ", m).strip()
    return re.sub(r"\s*([-/.])\s*", r"\1", m)


def _deger(hucre: Any) -> Any:
    """Hücre değeri: metin boşlukları tekleşmiş (boşsa None), tam sayıya eşit ondalık tam sayı."""
    if hucre is None:
        return None
    if isinstance(hucre, float) and hucre.is_integer():
        return int(hucre)
    if isinstance(hucre, (int, float)) and not isinstance(hucre, bool):
        return hucre
    metin = re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(hucre))).strip()
    return metin or None


def _tam_sayi(deger: Any) -> int | None:
    if isinstance(deger, int) and not isinstance(deger, bool):
        return deger
    if isinstance(deger, str) and re.fullmatch(r"\d{1,3}", deger):
        return int(deger)
    return None


# --- şablon ------------------------------------------------------------------------------------


def sablon_xlsx() -> bytes:
    """Boş şablon: her sayfada açıklama satırı, başlık satırı ve bir örnek satır."""
    kitap = Workbook()
    kitap.remove(kitap.active)
    for sayfa in SAYFALAR:
        ws = kitap.create_sheet(sayfa.ad)
        son = len(sayfa.sutunlar)
        ws.cell(1, 1, f"{sayfa.aciklama} {ORNEK_NOTU}").alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=son)
        ws.row_dimensions[1].height = 48
        for i, s in enumerate(sayfa.sutunlar, start=1):
            baslik = ws.cell(2, i, s.baslik + (" *" if s.zorunlu else ""))
            baslik.font = Font(bold=True)
            baslik.fill = PatternFill("solid", fgColor="E6E9EE")
            ornek = ws.cell(3, i, sayfa.ornek[i - 1])
            ornek.font = Font(italic=True, color="57606A")
            ws.column_dimensions[chr(64 + i)].width = s.genislik
        ws.freeze_panes = "A3"
        for s_no, s in enumerate(sayfa.sutunlar, start=1):
            if s.alan in ("seviye", "saat"):
                ust = 12 if s.alan == "seviye" else MAKS_SAAT
                kural = DataValidation(type="whole", operator="between", formula1="1", formula2=str(ust),
                                       error=f"1 ile {ust} arasında bir tam sayı yazın", showErrorMessage=True)
                ws.add_data_validation(kural)
                kural.add(f"{chr(64 + s_no)}3:{chr(64 + s_no)}{MAKS_SATIR + 2}")
    tampon = BytesIO()
    kitap.save(tampon)
    return tampon.getvalue()


# --- dosyayı okuma -----------------------------------------------------------------------------


@dataclass
class OkunanSayfa:
    sayfa: Sayfa
    satirlar: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    atlanan_ornek: int = 0


def oku(icerik: bytes) -> list[OkunanSayfa]:
    """Dosyadaki tanınan sayfalar (şablondaki adlarla; büyük/küçük harf ve boşluk farkı önemsiz).
    Sütunlar başlık adlarıyla bulunur; sırası değişebilir, fazladan sütun yok sayılır."""
    if len(icerik) > MAKS_BOYUT:
        raise GecersizVeri(f"Dosya çok büyük: en çok {MAKS_BOYUT // (1024 * 1024)} MB yüklenebilir")
    try:
        arsiv = zipfile.ZipFile(BytesIO(icerik))
        acik = sum(i.file_size for i in arsiv.infolist())
    except zipfile.BadZipFile:
        raise GecersizVeri("Dosya bir Excel dosyası (.xlsx) değil. Şablonu indirip doldurun") from None
    if acik > MAKS_ACIK_BOYUT:
        raise GecersizVeri("Dosyanın içeriği çok büyük; şablondaki sayfalardan fazlasını silip yeniden deneyin")
    try:
        kitap = load_workbook(BytesIO(icerik), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001  (openpyxl bozuk dosyada çeşitli hatalar fırlatır)
        raise GecersizVeri("Excel dosyası okunamadı. Dosyayı Excel'de açıp .xlsx olarak yeniden kaydedin") from None
    adlar = {anahtar(ad): ad for ad in kitap.sheetnames}
    sonuc = []
    try:
        for sayfa in SAYFALAR:
            if anahtar(sayfa.ad) in adlar:
                sonuc.append(_sayfayi_oku(kitap[adlar[anahtar(sayfa.ad)]], sayfa))
    finally:
        kitap.close()
    if not sonuc:
        raise GecersizVeri("Dosyada tanınan sayfa yok (Öğretmenler, Sınıflar, Dersler, Ders dağılımı). Şablonu indirip doldurun")
    return sonuc


def _sayfayi_oku(ws, sayfa: Sayfa) -> OkunanSayfa:
    okunan = OkunanSayfa(sayfa)
    sutun_yeri: dict[str, int | None] | None = None
    for no, degerler in enumerate(ws.iter_rows(values_only=True), start=1):
        if no > MAKS_HAM_SATIR:
            raise GecersizVeri(f"“{sayfa.ad}” sayfasında çok fazla satır var (en çok {MAKS_SATIR} kayıt)")
        if sutun_yeri is None:
            # Başlık satırı: zorunlu başlıkların hepsi bulunan ilk satır ("Ad Soyad *" da olur).
            bulunan = {anahtar(str(d).rstrip(" *")): i for i, d in enumerate(degerler) if isinstance(d, str)}
            if all(anahtar(s.baslik) in bulunan for s in sayfa.sutunlar if s.zorunlu):
                sutun_yeri = {s.alan: bulunan.get(anahtar(s.baslik)) for s in sayfa.sutunlar}
            elif no >= 5:
                break
            continue
        satir = {alan: _deger(degerler[i]) if i is not None and i < len(degerler) else None
                 for alan, i in sutun_yeri.items()}
        if all(v is None for v in satir.values()):
            continue
        ilk = satir[sayfa.sutunlar[0].alan]
        if isinstance(ilk, str) and anahtar(ilk).endswith(ORNEK):
            okunan.atlanan_ornek += 1
            continue
        okunan.satirlar.append((no, satir))
        if len(okunan.satirlar) > MAKS_SATIR:
            raise GecersizVeri(f"“{sayfa.ad}” sayfasında çok fazla satır var (en çok {MAKS_SATIR} kayıt)")
    if sutun_yeri is None:
        basliklar = ", ".join(s.baslik for s in sayfa.sutunlar if s.zorunlu)
        raise GecersizVeri(f"“{sayfa.ad}” sayfasında başlık satırı bulunamadı (ilk satırlarda {basliklar} olmalı)")
    return okunan


# --- plan --------------------------------------------------------------------------------------


@dataclass
class SatirSonucu:
    satir: int
    ad: str
    ayrinti: str = ""


@dataclass
class SayfaSonucu:
    sayfa: str
    baslik: str
    eklenecek: list[SatirSonucu] = field(default_factory=list)
    guncellenecek: list[SatirSonucu] = field(default_factory=list)
    hatali: list[SatirSonucu] = field(default_factory=list)
    degismeyen: int = 0
    atlanan_ornek: int = 0


@dataclass(frozen=True)
class Yeni:
    """Bu içe aktarmada açılacak kayıt (kaydederken gerçek kimliğine çevrilir)."""

    tur: str
    anahtar: str


@dataclass
class Plan:
    sayfalar: list[SayfaSonucu]
    islemler: list[tuple] = field(default_factory=list)

    @property
    def hata_sayisi(self) -> int:
        return sum(len(s.hatali) for s in self.sayfalar)

    @property
    def ozet(self) -> str:
        """Planın parmak izi: önizlemede gösterilenle kaydedilenin aynı olduğunu denetler."""
        metin = json.dumps([[str(p) for p in i[:2]] + [i[2]] for i in self.islemler], default=str, sort_keys=True)
        return hashlib.sha256(metin.encode()).hexdigest()[:20]

    def yanit(self) -> dict[str, Any]:
        return {
            "sayfalar": self.sayfalar,
            "eklenecek_sayisi": sum(len(s.eklenecek) for s in self.sayfalar),
            "guncellenecek_sayisi": sum(len(s.guncellenecek) for s in self.sayfalar),
            "hata_sayisi": self.hata_sayisi,
            "ozet": self.ozet,
        }


def _metin(deger: Any) -> str | None:
    return None if deger is None else str(deger)


def _gruplu(kayitlar) -> dict[str, list]:
    sonuc: dict[str, list] = {}
    for k in kayitlar:
        sonuc.setdefault(anahtar(k.ad), []).append(k)
    return sonuc


class _Planlayici:
    def __init__(self, oturum) -> None:
        self.mevcut = {"ogretmen": _gruplu(OgretmenDeposu(oturum).listele()),
                       "ders": _gruplu(DersDeposu(oturum).listele()),
                       "sinif": _gruplu(SinifDeposu(oturum).listele())}
        self.gruplar = _gruplu(SubeGrubuDeposu(oturum).listele())
        self.grup_kimligi = {g.id: g for v in self.gruplar.values() for g in v}
        self.atamalar = {(a.sinif_id, a.ders_id): a for a in DersAtamaDeposu(oturum).listele()}
        self.islemler: list[tuple] = []
        # anahtar -> kimlik ya da Yeni; hatalı satırların anahtarı -> satır no
        self.ref: dict[str, dict[str, Any]] = {"ogretmen": {}, "ders": {}, "sinif": {}}
        self.hatali: dict[str, dict[str, int]] = {"ogretmen": {}, "ders": {}, "sinif": {}}
        self.yeni_gruplar: dict[str, int] = {}  # anahtar -> seviye
        self.sinif_seviyesi: dict[str, int] = {}

    def planla(self, okunanlar: list[OkunanSayfa]) -> Plan:
        sirali = sorted(okunanlar, key=lambda o: [s.tur for s in SAYFALAR].index(o.sayfa.tur))
        sonuclar = []
        for okunan in sirali:
            sonuc = SayfaSonucu(okunan.sayfa.tur, okunan.sayfa.ad, atlanan_ornek=okunan.atlanan_ornek)
            getattr(self, f"_{okunan.sayfa.tur}")(okunan.satirlar, sonuc)
            sonuclar.append(sonuc)
        return Plan(sonuclar, self.islemler)

    # Ortak: ad, tekrar ve okulda birden çok eşleşme denetimi. Hata varsa None.
    def _ad(self, tur: str, no: int, d: dict, sonuc: SayfaSonucu, gorulen: dict, uzunluk: int, adi: str):
        ad = _metin(d["ad"])
        if ad is None:
            sonuc.hatali.append(SatirSonucu(no, "", f"{adi} boş"))
            return None
        k = anahtar(ad)
        if len(ad) > uzunluk:
            neden = f"{adi} en çok {uzunluk} karakter olabilir"
        elif k in gorulen:
            neden = f"“{ad}” bu sayfada {gorulen[k]}. satırda da var"
        elif len(self.mevcut[tur].get(k, [])) > 1:
            neden = f"Okulda “{ad}” adlı birden çok kayıt var; hangisi olduğu anlaşılamıyor. Önce adlarını ayırın"
        else:
            gorulen[k] = no
            return ad, k
        sonuc.hatali.append(SatirSonucu(no, ad, neden))
        self.hatali[tur].setdefault(k, no)
        return None

    def _ogretmen(self, satirlar, sonuc: SayfaSonucu) -> None:
        gorulen: dict[str, int] = {}
        for no, d in satirlar:
            ad_k = self._ad("ogretmen", no, d, sonuc, gorulen, 200, "Ad Soyad")
            if ad_k is None:
                continue
            ad, k = ad_k
            brans = _metin(d["brans"])
            if brans is not None and len(brans) > 100:
                sonuc.hatali.append(SatirSonucu(no, ad, "Branş en çok 100 karakter olabilir"))
                self.hatali["ogretmen"][k] = no
                continue
            mevcut = self.mevcut["ogretmen"].get(k)
            if mevcut:
                o = mevcut[0]
                self.ref["ogretmen"][k] = o.id
                if brans is not None and brans != o.brans:
                    sonuc.guncellenecek.append(SatirSonucu(no, o.ad, f"Branş: {o.brans or '—'} → {brans}"))
                    self.islemler.append(("ogretmen_guncelle", o.id, {"brans": brans}))
                else:
                    sonuc.degismeyen += 1
            else:
                self.ref["ogretmen"][k] = Yeni("ogretmen", k)
                sonuc.eklenecek.append(SatirSonucu(no, ad, f"Branş: {brans}" if brans else ""))
                self.islemler.append(("ogretmen_ekle", Yeni("ogretmen", k), {"ad": ad, "brans": brans or ""}))

    def _ders(self, satirlar, sonuc: SayfaSonucu) -> None:
        gorulen: dict[str, int] = {}
        for no, d in satirlar:
            ad_k = self._ad("ders", no, d, sonuc, gorulen, 200, "Ders adı")
            if ad_k is None:
                continue
            ad, k = ad_k
            kisa = _metin(d["kisa_ad"])
            if kisa is not None and len(kisa) > 20:
                sonuc.hatali.append(SatirSonucu(no, ad, "Kısa ad en çok 20 karakter olabilir"))
                self.hatali["ders"][k] = no
                continue
            mevcut = self.mevcut["ders"].get(k)
            if mevcut:
                ders = mevcut[0]
                self.ref["ders"][k] = ders.id
                if kisa is not None and kisa != ders.kisa_ad:
                    sonuc.guncellenecek.append(SatirSonucu(no, ders.ad, f"Kısa ad: {ders.kisa_ad or '—'} → {kisa}"))
                    self.islemler.append(("ders_guncelle", ders.id, {"kisa_ad": kisa}))
                else:
                    sonuc.degismeyen += 1
            else:
                self.ref["ders"][k] = Yeni("ders", k)
                sonuc.eklenecek.append(SatirSonucu(no, ad, f"Kısa ad: {kisa}" if kisa else ""))
                self.islemler.append(("ders_ekle", Yeni("ders", k), {"ad": ad, "kisa_ad": kisa or ""}))

    def _sinif(self, satirlar, sonuc: SayfaSonucu) -> None:
        gorulen: dict[str, int] = {}
        for no, d in satirlar:
            ad_k = self._ad("sinif", no, d, sonuc, gorulen, 50, "Şube adı")
            if ad_k is None:
                continue
            ad, k = ad_k
            neden, islemler, ayrinti = self._sinif_plani(ad, k, d)
            if neden:
                sonuc.hatali.append(SatirSonucu(no, ad, neden))
                self.hatali["sinif"][k] = no
                continue
            mevcut = self.mevcut["sinif"].get(k)
            self.islemler += islemler
            if mevcut:
                self.ref["sinif"][k] = mevcut[0].id
                if any(i[0] == "sinif_guncelle" for i in islemler):
                    sonuc.guncellenecek.append(SatirSonucu(no, mevcut[0].ad, ayrinti))
                else:
                    sonuc.degismeyen += 1
            else:
                self.ref["sinif"][k] = Yeni("sinif", k)
                sonuc.eklenecek.append(SatirSonucu(no, ad, ayrinti))

    def _sinif_plani(self, ad: str, k: str, d: dict) -> tuple[str | None, list[tuple], str]:
        mevcut = (self.mevcut["sinif"].get(k) or [None])[0]
        seviye = _tam_sayi(d["seviye"])
        if d["seviye"] is not None and (seviye is None or not 1 <= seviye <= 12):
            return "Seviye 1 ile 12 arasında bir tam sayı olmalı", [], ""
        if mevcut is None and seviye is None:
            return "Yeni şube için seviye gerekli", [], ""
        seviye = seviye if seviye is not None else mevcut.seviye
        eski_grup = self.grup_kimligi.get(mevcut.sube_grubu_id) if mevcut and mevcut.sube_grubu_id else None
        islemler: list[tuple] = []
        grup_ref: Any = mevcut.sube_grubu_id if mevcut else None
        grup_adi = eski_grup.ad if eski_grup else None
        if d["grup"] is not None:
            grup_adi = str(d["grup"])
            gk = anahtar(grup_adi)
            if len(grup_adi) > 100:
                return "Şube grubu adı en çok 100 karakter olabilir", [], ""
            grubu = self.gruplar.get(gk)
            if grubu and len(grubu) > 1:
                return f"Okulda “{grup_adi}” adlı birden çok grup var", [], ""
            grup_seviyesi = grubu[0].seviye if grubu else self.yeni_gruplar.get(gk)
            if grup_seviyesi is not None and grup_seviyesi != seviye:
                return (f"{ad} {seviye}. sınıf; “{grubu[0].ad if grubu else grup_adi}” grubu {grup_seviyesi}. "
                        "sınıfların grubu"), [], ""
            if grubu:
                grup_ref, grup_adi = grubu[0].id, grubu[0].ad
            else:
                grup_ref = Yeni("grup", gk)
                if gk not in self.yeni_gruplar:
                    self.yeni_gruplar[gk] = seviye
                    islemler.append(("grup_ekle", grup_ref, {"ad": grup_adi, "seviye": seviye}))
        elif eski_grup and eski_grup.seviye != seviye:
            return (f"{ad}, {eski_grup.seviye}. sınıfların grubu “{eski_grup.ad}” içinde; seviyesini değiştirmek için "
                    "Şube grubu sütununa aynı seviyeden bir grup yazın"), [], ""
        self.sinif_seviyesi[k] = seviye
        if mevcut is None:
            islemler.append(("sinif_ekle", Yeni("sinif", k), {"ad": ad, "seviye": seviye, "sube_grubu_id": grup_ref}))
            ayrinti = f"{seviye}. sınıf" + (f", {grup_adi}" if grup_adi else "")
            if isinstance(grup_ref, Yeni) and islemler[0][0] == "grup_ekle":
                ayrinti += " (yeni grup)"
            return None, islemler, ayrinti
        degisiklik, parcalar = {}, []
        if seviye != mevcut.seviye:
            degisiklik["seviye"] = seviye
            parcalar.append(f"Seviye: {mevcut.seviye} → {seviye}")
        if grup_ref != mevcut.sube_grubu_id:
            degisiklik["sube_grubu_id"] = grup_ref
            parcalar.append(f"Grup: {eski_grup.ad if eski_grup else '—'} → {grup_adi}"
                            + (" (yeni grup)" if any(i[0] == "grup_ekle" for i in islemler) else ""))
        if degisiklik:
            islemler.append(("sinif_guncelle", mevcut.id, degisiklik))
        return None, islemler, "; ".join(parcalar)

    def _baglanti(self, tur: str, deger: Any, adi: str) -> tuple[Any, str | None]:
        """Şube, ders ya da öğretmen adını kimliğe (ya da bu dosyada açılacak kayda) çevirir."""
        k = anahtar(deger)
        if k in self.hatali[tur]:
            return None, f"“{deger}” {adi} hatalı satırda ({self.hatali[tur][k]}. satır)"
        if k in self.ref[tur]:
            return self.ref[tur][k], None
        mevcut = self.mevcut[tur].get(k, [])
        if len(mevcut) > 1:
            return None, f"Okulda “{deger}” adlı birden çok {adi} var; hangisi olduğu anlaşılamıyor"
        if mevcut:
            return mevcut[0].id, None
        sayfa = {"ogretmen": "Öğretmenler", "ders": "Dersler", "sinif": "Sınıflar"}[tur]
        return None, f"“{deger}” adlı {adi} yok; {sayfa} sayfasına ekleyin ya da adını düzeltin"

    def _dagilim(self, satirlar, sonuc: SayfaSonucu) -> None:
        gorulen: dict[tuple[str, str], int] = {}
        for no, d in satirlar:
            sube, ders, saat_hucre, ogretmen = d["sube"], d["ders"], d["saat"], d["ogretmen"]
            ad = " · ".join(str(x) for x in (sube, ders) if x is not None)
            if sube is None or ders is None:
                sonuc.hatali.append(SatirSonucu(no, ad, "Şube ve ders boş olamaz"))
                continue
            saat = _tam_sayi(saat_hucre)
            neden = None
            if saat is None or not 1 <= saat <= MAKS_SAAT:
                neden = f"Haftalık saat 1 ile {MAKS_SAAT} arasında bir tam sayı olmalı"
            cift = (anahtar(sube), anahtar(ders))
            if neden is None and cift in gorulen:
                neden = f"Bu şubenin bu dersi bu sayfada {gorulen[cift]}. satırda da var"
            sinif_id, n1 = self._baglanti("sinif", sube, "şube")
            ders_id, n2 = self._baglanti("ders", ders, "ders")
            ogretmen_id, n3 = self._baglanti("ogretmen", ogretmen, "öğretmen") if ogretmen is not None else (None, None)
            neden = neden or n1 or n2 or n3
            if neden:
                sonuc.hatali.append(SatirSonucu(no, ad, neden))
                continue
            gorulen[cift] = no
            ogretmen_metni = f", {ogretmen}" if ogretmen is not None else ""
            mevcut = self.atamalar.get((sinif_id, ders_id))
            if mevcut is None:
                sonuc.eklenecek.append(SatirSonucu(no, ad, f"{saat} saat{ogretmen_metni}"))
                self.islemler.append(("atama_ekle", f"{sinif_id}|{ders_id}",
                                      {"sinif_id": sinif_id, "ders_id": ders_id, "haftalik_saat": saat,
                                       "ogretmen_id": ogretmen_id}))
                continue
            degisiklik, parcalar = {}, []
            if saat != mevcut.haftalik_saat:
                degisiklik["haftalik_saat"] = saat
                parcalar.append(f"Saat: {mevcut.haftalik_saat} → {saat}")
            if ogretmen is not None and ogretmen_id != mevcut.ogretmen_id:
                degisiklik["ogretmen_id"] = ogretmen_id
                parcalar.append(f"Öğretmen: → {ogretmen}")
            if degisiklik:
                sonuc.guncellenecek.append(SatirSonucu(no, ad, "; ".join(parcalar)))
                self.islemler.append(("atama_guncelle", mevcut.id, degisiklik))
            else:
                sonuc.degismeyen += 1


def onizle(oturum, icerik: bytes) -> Plan:
    return _Planlayici(oturum).planla(oku(icerik))


class IceAktarmaHatali(GecersizVeri):
    """Dosyada hatalı satır var: hiçbir şey kaydedilmez (422)."""


def kaydet(oturum, icerik: bytes, ozet: str) -> dict[str, int]:
    """Planı tek işlemde uygular. Hatalı satır varsa (422) ya da plan önizlemedekinden farklıysa
    (409: veri arada değişti) hiçbir şey yazılmaz."""
    plan = onizle(oturum, icerik)
    if plan.hata_sayisi:
        raise IceAktarmaHatali(f"Dosyada {plan.hata_sayisi} hatalı satır var; hiçbir şey kaydedilmedi. Önizlemeye bakın")
    if plan.ozet != ozet:
        raise KayitCakismasi("Okulun verisi önizlemeden sonra değişti; hiçbir şey kaydedilmedi. Yeniden önizleyin")
    olusan: dict[Yeni, uuid.UUID] = {}
    renkler = [d.renk for d in DersDeposu(oturum).listele()]

    def kimlik(deger: Any) -> Any:
        return olusan[deger] if isinstance(deger, Yeni) else deger

    try:
        for tur, hedef, alanlar in plan.islemler:
            alanlar = {a: kimlik(v) for a, v in alanlar.items()}
            if tur.endswith("_guncelle"):
                model = {"ogretmen": Ogretmen, "ders": Ders, "sinif": Sinif, "atama": DersAtama}[tur.split("_")[0]]
                nesne = oturum.get(model, hedef)
                for a, v in alanlar.items():
                    setattr(nesne, a, v)
                continue
            if tur == "ders_ekle":
                alanlar["renk"] = siradaki_renk(renkler)
                renkler.append(alanlar["renk"])
            model = {"ogretmen_ekle": Ogretmen, "ders_ekle": Ders, "grup_ekle": SubeGrubu, "sinif_ekle": Sinif,
                     "atama_ekle": DersAtama}[tur]
            nesne = model(**alanlar)
            oturum.add(nesne)
            oturum.flush()
            if isinstance(hedef, Yeni):
                olusan[hedef] = nesne.id
        oturum.flush()
        oturum.commit()
    except IntegrityError as hata:
        oturum.rollback()
        raise KayitCakismasi("Kayıt sırasında bir çakışma oldu; hiçbir şey kaydedilmedi. Yeniden önizleyin") from hata
    return {"eklenen": sum(1 for i in plan.islemler if i[0].endswith("_ekle")),
            "guncellenen": sum(1 for i in plan.islemler if i[0].endswith("_guncelle"))}
