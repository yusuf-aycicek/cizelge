"""Okul geneli kurallar, kullanıcının diliyle (docs/arayuz-plani.md bölüm 2.3).

- Varsayılan kurallar çözücüden gelir (`cozucu.kisitlar.VARSAYILAN_KISITLAR`); okul bir kuralı
  değiştirince `kisit` tablosuna aynı türde bir kayıt yazılır ve varsayılanın yerini alır.
  "Varsayılana dön" o kaydı siler. Arayüz varsayılanları kendisi bilmez, buradan okur.
- Esnek kuralların ağırlığı arayüzde sayı olarak değil, **önem seviyesi** olarak seçilir:
  Önemsiz / Önemli / Çok önemli. Her kuralın kendi üç sayısı vardır (varsayılan ağırlıklar
  kurala göre farklıdır) ve **"Önemli" = çözücünün varsayılan ağırlığı**. Karşılıklar yalnızca
  `ONEM_KARSILIKLARI`'nda tanımlıdır; okul müdürünün cevaplarına göre burada ayarlanacak
  (CLAUDE.md bölüm 10). Eşitliği test_kurallar.py denetler.
- **Özel ayarlar** (ADR 0016): bir kuralın okul değeri bir öğretmene, derse ya da şubeye özel
  ezilebilir. Aynı `kisit` tablosunda kapsam sütunları dolu satırlardır. Hangi kuralın hangi
  kapsamı desteklediğini çözücünün kural sınıfı bildirir (`kapsamlar`); burada tekrar yazılmaz.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from cozucu.blok import BLOK_DESENI_TURU, desen_dogrula
from cozucu.kapsam import Kapsam, ortusur
from cozucu.kisitlar import KAYIT_DEFTERI, VARSAYILAN_KISITLAR, GirdiHatasi, kural_olustur
from cozucu.model import KisitTanimi
from sqlalchemy import select
from sqlalchemy.orm import Session

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, SinifDeposu, SubeGrubuDeposu
from okulapi.cekirdek.servisler import GecersizVeri, KayitBulunamadi
from okulapi.moduller.ders_programi.modeller import Kisit

ONEM_SEVIYELERI = ("onemsiz", "onemli", "cok_onemli")
OZEL = "ozel"  # kayıtlı ağırlık hiçbir seviyeye denk gelmiyorsa (ör. API ile elle girilmiş)

ONEM_KARSILIKLARI: dict[str, dict[str, int]] = {
    "sinif_boslugu": {"onemsiz": 10, "onemli": 30, "cok_onemli": 60},
    "degisiklik": {"onemsiz": 3, "onemli": 8, "cok_onemli": 20},
    "tercih_etmez": {"onemsiz": 2, "onemli": 5, "cok_onemli": 12},
    "bos_gun": {"onemsiz": 1, "onemli": 4, "cok_onemli": 10},
    "ogretmen_penceresi": {"onemsiz": 1, "onemli": 3, "cok_onemli": 8},
    "ardisik_ders": {"onemsiz": 1, "onemli": 2, "cok_onemli": 5},
}

# Arayüzde gösterim sırası ve metinler. Esnekler varsayılan önem sırasıyla (ağır olan önce).
KURAL_METINLERI: dict[str, tuple[str, str]] = {
    "gunluk_ders_siniri": (
        "Aynı dersin günlük sınırı",
        "Aynı ders bir sınıfa günde en fazla bu kadar saat konur.",
    ),
    "ogretmen_gunluk_siniri": (
        "Öğretmenin günlük ders sınırı",
        "Bir öğretmen günde en fazla bu kadar saat derse girer.",
    ),
    BLOK_DESENI_TURU: (
        "Dağılım şekli (blok dersler)",
        "Bir dersin haftalık saatleri art arda bloklara bölünür (ör. 5 saat: 2+2+1); her blok ayrı "
        "bir günde. Okul önerisi uygulanamayan derste kendiliğinden kalkar.",
    ),
    "sinif_boslugu": (
        "Sınıfların boş saati olmasın",
        "Dersler günün başından başlar; sınıfın gün ortasında boş saati kalmaz.",
    ),
    "degisiklik": (
        "Mevcut programa bağlılık",
        "Bir program temel alınarak yeniden üretilirken dersler olabildiğince yerinde kalır.",
    ),
    "tercih_etmez": (
        "Öğretmenin tercih etmediği saatler",
        "Öğretmenin \"tercih etmez\" işaretlediği saatlere ders konmamaya çalışılır.",
    ),
    "bos_gun": (
        "Öğretmene boş gün",
        "Her öğretmene haftada bu kadar boş gün kazandırılmaya çalışılır. Ders yükü buna izin "
        "vermeyen öğretmen için zorlanmaz.",
    ),
    "ogretmen_penceresi": (
        "Öğretmenin boş (pencere) saatleri",
        "Öğretmenin aynı gündeki iki dersi arasında boş saat kalmamaya çalışılır.",
    ),
    "ardisik_ders": (
        "Bir dersin saatleri arka arkaya",
        "Bir dersin aynı gündeki saatleri arka arkaya konmaya çalışılır.",
    ),
}

VARSAYILANLAR: dict[str, KisitTanimi] = {t.tur: t for t in VARSAYILAN_KISITLAR}

# Parametrelerin en küçük değerleri: kullanıcının diliyle hata için (çözücü de ayrıca denetler).
PARAMETRE_ALT_SINIRLARI = {"n": 1, "m": 1, "hedef_bos_gun": 0}
# Okul tanımında verilmesi gerekmeyen parametreler ve özel ayarın okul tanımından farklı adları.
ISTEGE_BAGLI_PARAMETRELER: dict[str, set[str]] = {BLOK_DESENI_TURU: {"varsayilanlar"}}
OZEL_PARAMETRELER: dict[str, set[str]] = {BLOK_DESENI_TURU: {"desen"}}
DESEN_ORNEGI = "Dağılım şekli \"2+2+1\" gibi olmalı; her blok 1-8 saat"


def _desen(deger: Any) -> list[int]:
    try:
        return list(desen_dogrula(deger))
    except ValueError as hata:
        raise GecersizVeri(DESEN_ORNEGI) from hata

# API'nin bugün desteklediği kapsam eksenleri (çözücüdeki adlarıyla). Şube grubu K5'te gelir.
API_EKSENLERI = ("ogretmen", "ders", "sube", "sube_grubu")
EKSEN_METINLERI = {"ogretmen": "öğretmene", "ders": "derse", "sube": "şubeye", "sube_grubu": "şube grubuna"}
# Eksen -> Kisit sütunu / kapsam alanı.
EKSEN_SUTUNLARI = {"ders": "ders_id", "sube": "sinif_id", "sube_grubu": "sube_grubu_id", "ogretmen": "ogretmen_id"}
# Bir özel ayarın kapsamı: {"ders_id": ..., "sinif_id": ..., "sube_grubu_id": ..., "ogretmen_id": ...}.
KapsamSozlugu = dict[str, uuid.UUID | None]


def kapsamlar(tur: str) -> list[str]:
    """Kuralın özel ayar alabildiği eksenler: çözücünün kural sınıfından."""
    return [e for e in API_EKSENLERI if e in KAYIT_DEFTERI[tur].kapsamlar]


def zorunlu_eksenler(tur: str) -> list[str]:
    """Özel ayarda dolu olması gereken eksenler (ör. dağılım şekli bir ders ister)."""
    return [e for e in API_EKSENLERI if e in KAYIT_DEFTERI[tur].zorunlu_eksenler]


def _kapsam_eksenleri(kapsam: KapsamSozlugu) -> set[str]:
    return {e for e, sutun in EKSEN_SUTUNLARI.items() if kapsam.get(sutun) is not None}


def _tam_kapsam(kapsam: KapsamSozlugu) -> KapsamSozlugu:
    return {sutun: kapsam.get(sutun) for sutun in EKSEN_SUTUNLARI.values()}


def seviye(tur: str, agirlik: int) -> str:
    for ad, deger in ONEM_KARSILIKLARI[tur].items():
        if deger == agirlik:
            return ad
    return OZEL


class KurallarServisi:
    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum

    def _kayit(self, tur: str, kapsam: KapsamSozlugu | None = None) -> Kisit | None:
        """Bu kapsamdaki tanım; kapsam verilmezse okul geneli tanım."""
        kosullar = [
            getattr(Kisit, sutun).is_(None) if deger is None else getattr(Kisit, sutun) == deger
            for sutun, deger in _tam_kapsam(kapsam or {}).items()
        ]
        return self.oturum.scalars(select(Kisit).where(Kisit.tur == tur, *kosullar)).one_or_none()

    def _kural(self, tur: str, kayit: Kisit | None, ozeller: list[Kisit] | None = None) -> dict[str, Any]:
        if ozeller is None:
            ozeller = [k for k in self.oturum.scalars(select(Kisit).where(Kisit.tur == tur)) if not k.okul_geneli]
        v = VARSAYILANLAR[tur]
        parametreler = dict(kayit.parametreler) if kayit else dict(v.parametreler)
        agirlik = kayit.agirlik if kayit else v.agirlik
        ad, aciklama = KURAL_METINLERI[tur]
        return {
            "tur": tur,
            "ad": ad,
            "aciklama": aciklama,
            "zorunlu": v.zorunlu,
            "parametreler": parametreler,
            "varsayilan_parametreler": dict(v.parametreler),
            "agirlik": None if v.zorunlu else agirlik,
            "seviye": None if v.zorunlu else seviye(tur, agirlik),
            "varsayilan_seviye": None if v.zorunlu else seviye(tur, v.agirlik),
            "varsayilan": kayit is None,
            "kapsamlar": kapsamlar(tur),
            "zorunlu_eksenler": zorunlu_eksenler(tur),
            "ozel_ayarlar": self._ozel_ayarlar(ozeller),
        }

    def _ozel_ayarlar(self, ozeller: list[Kisit]) -> list[dict[str, Any]]:
        """Özel ayarlar, adlarıyla: arayüz kimlik değil "Ayşe Yılmaz", "9-A · Matematik",
        "11 Sayısal grubu · Matematik" gösterir."""
        ogretmen = {o.id: o.ad for o in OgretmenDeposu(self.oturum).listele()} if any(k.ogretmen_id for k in ozeller) else {}
        sinif = {s.id: s.ad for s in SinifDeposu(self.oturum).listele()} if any(k.sinif_id for k in ozeller) else {}
        grup = ({g.id: f"{g.ad} grubu" for g in SubeGrubuDeposu(self.oturum).listele()}
                if any(k.sube_grubu_id for k in ozeller) else {})
        ders = {d.id: d.ad for d in DersDeposu(self.oturum).listele()} if any(k.ders_id for k in ozeller) else {}
        satirlar = []
        for k in ozeller:
            parcalar = [sinif.get(k.sinif_id), grup.get(k.sube_grubu_id), ders.get(k.ders_id), ogretmen.get(k.ogretmen_id)]
            satirlar.append({
                "kapsam": {sutun: getattr(k, sutun) for sutun in EKSEN_SUTUNLARI.values()},
                "ad": " · ".join(p for p in parcalar if p),
                "parametreler": dict(k.parametreler),
            })
        return sorted(satirlar, key=lambda s: s["ad"].casefold())

    def listele(self) -> list[dict[str, Any]]:
        okul: dict[str, Kisit] = {}
        ozel: dict[str, list[Kisit]] = defaultdict(list)
        for k in self.oturum.scalars(select(Kisit)):
            if k.okul_geneli:
                okul[k.tur] = k
            else:
                ozel[k.tur].append(k)
        return [self._kural(tur, okul.get(tur), ozel.get(tur, [])) for tur in KURAL_METINLERI]

    def _parametreleri_dogrula(self, tur: str, parametreler: dict[str, Any], ozel: bool = False) -> dict[str, Any]:
        """Parametre adlarını ve değerlerini denetler; tek gösterime getirilmiş parametreleri döner."""
        v = VARSAYILANLAR[tur]
        gereken = OZEL_PARAMETRELER.get(tur, set(v.parametreler)) if ozel else set(v.parametreler)
        olabilen = gereken | (set() if ozel else ISTEGE_BAGLI_PARAMETRELER.get(tur, set()))
        if not gereken <= set(parametreler) <= olabilen:
            raise GecersizVeri(f"Bu kuralın ayarları: {', '.join(sorted(olabilen)) or 'yok'}")
        sonuc = dict(parametreler)
        for ad, deger in parametreler.items():
            if ad == "desen":
                sonuc[ad] = _desen(deger)
            elif ad == "otomatik":
                if not isinstance(deger, bool):
                    raise GecersizVeri("otomatik açık ya da kapalı (true/false) olmalı")
            elif ad == "varsayilanlar":
                if not isinstance(deger, dict):
                    raise GecersizVeri("Saate göre dağılım şekilleri {\"4\": [2, 1, 1]} biçiminde olmalı")
                sonuc[ad] = {}
                for saat, desen in deger.items():
                    if not str(saat).isdigit() or not 1 <= int(saat) <= 40:
                        raise GecersizVeri(f"Haftalık saat 1-40 arasında olmalı: {saat}")
                    bloklar = _desen(desen)
                    if bloklar and sum(bloklar) != int(saat):
                        raise GecersizVeri(
                            f"{saat} saatlik dersin dağılım şekli {'+'.join(map(str, bloklar))} olamaz: "
                            f"toplamı {sum(bloklar)} saat")
                    sonuc[ad][str(int(saat))] = bloklar
            elif isinstance(deger, bool) or not isinstance(deger, int):
                raise GecersizVeri(f"{KURAL_METINLERI[tur][0]}: bir sayı olmalı")
            elif deger < PARAMETRE_ALT_SINIRLARI.get(ad, 0):
                raise GecersizVeri(f"{KURAL_METINLERI[tur][0]}: en az {PARAMETRE_ALT_SINIRLARI.get(ad, 0)} olmalı")
        return sonuc

    def ayarla(self, tur: str, parametreler: dict[str, int] | None, onem: str | None) -> dict[str, Any]:
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        v = VARSAYILANLAR[tur]
        if onem is not None and v.zorunlu:
            raise GecersizVeri("Zorunlu kuralların önem seviyesi yoktur")
        kayit = self._kayit(tur)
        yeni_parametreler = {**(kayit.parametreler if kayit else v.parametreler), **(parametreler or {})}
        yeni_parametreler = self._parametreleri_dogrula(tur, yeni_parametreler)
        agirlik = ONEM_KARSILIKLARI[tur][onem] if onem else (kayit.agirlik if kayit else v.agirlik)
        try:
            kural_olustur(KisitTanimi(tur, yeni_parametreler, zorunlu=v.zorunlu, agirlik=agirlik))
        except GirdiHatasi as hata:
            raise GecersizVeri(str(hata)) from hata
        if kayit is None:
            kayit = Kisit(tur=tur, zorunlu=v.zorunlu, agirlik=agirlik, parametreler=yeni_parametreler)
            self.oturum.add(kayit)
        else:
            kayit.parametreler, kayit.agirlik = yeni_parametreler, agirlik
        self.oturum.commit()
        return self._kural(tur, kayit)

    def varsayilana_don(self, tur: str) -> dict[str, Any]:
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        kayit = self._kayit(tur)
        if kayit is not None:
            self.oturum.delete(kayit)
            self.oturum.commit()
        return self._kural(tur, None)

    # --- özel ayarlar ---------------------------------------------------------------------

    def ozel_ayarla(self, tur: str, kapsam: KapsamSozlugu, parametreler: dict[str, int]) -> dict[str, Any]:
        """Bir kuralın bu kapsamdaki özel değerini ekler ya da günceller."""
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        ad = KURAL_METINLERI[tur][0]
        kapsam = _tam_kapsam(kapsam)
        eksenler = _kapsam_eksenleri(kapsam)
        if not eksenler:
            raise GecersizVeri("Özel ayar için bir öğretmen, ders, şube ya da şube grubu seçin")
        desteklenmeyen = eksenler - set(kapsamlar(tur))
        if desteklenmeyen:
            neye = " ve ".join(EKSEN_METINLERI[e] for e in API_EKSENLERI if e in desteklenmeyen)
            raise GecersizVeri(f"\"{ad}\" kuralı {neye} özel ayarlanamaz")
        for depo, kimlik, varlik in (
            (OgretmenDeposu, kapsam["ogretmen_id"], "Öğretmen"), (DersDeposu, kapsam["ders_id"], "Ders"),
            (SinifDeposu, kapsam["sinif_id"], "Şube"), (SubeGrubuDeposu, kapsam["sube_grubu_id"], "Şube grubu"),
        ):
            # Otomatik okul filtresi yüzünden başka okulun kaydı da "bulunamaz" (bileşik FK da reddeder).
            if kimlik is not None and depo(self.oturum).getir(kimlik) is None:
                raise GecersizVeri(f"{varlik} bu okulda bulunamadı")
        parametreler = self._parametreleri_dogrula(tur, parametreler, ozel=True)
        okul = self._kayit(tur)
        v = VARSAYILANLAR[tur]
        zorunlu, agirlik = v.zorunlu, okul.agirlik if okul else v.agirlik
        okul_tanimi = KisitTanimi(tur, dict(okul.parametreler) if okul else dict(v.parametreler), zorunlu=zorunlu, agirlik=agirlik)
        try:
            cozucu_kapsami = Kapsam(**{s: None if d is None else str(d) for s, d in kapsam.items()})
            kural_olustur(okul_tanimi, [KisitTanimi(tur, parametreler, kapsam=cozucu_kapsami)])
        except (GirdiHatasi, ValueError) as hata:  # ValueError: Kapsam'ın aile denetimi
            raise GecersizVeri(str(hata)) from hata
        kayit = self._kayit(tur, kapsam)
        if kayit is None:
            kayit = Kisit(tur=tur, zorunlu=zorunlu, agirlik=agirlik, parametreler=parametreler, **kapsam)
            self.oturum.add(kayit)
        else:
            kayit.parametreler = parametreler
        self.oturum.commit()
        return self._kural(tur, okul)

    def ozel_etki(self, tur: str, kapsam: KapsamSozlugu) -> dict[str, Any]:
        """Bu kapsama özel ayar verilirse neyi ezer, neyin altında kalır (kaydetmeden önce gösterim).

        Örtüşen özel ayarlardan puanı küçük olanları ezer, büyük olanlar onun yerine geçer; puan
        ve örtüşme `cozucu.kapsam`tan (çözücüyle aynı kural, ADR 0015)."""
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        kapsam = _tam_kapsam(kapsam)
        eksenler = _kapsam_eksenleri(kapsam)
        if not eksenler or eksenler - set(kapsamlar(tur)):
            raise GecersizVeri(f"\"{KURAL_METINLERI[tur][0]}\" kuralı bu kapsamda özel ayarlanamaz")
        try:
            yeni = Kapsam(**{s: None if d is None else str(d) for s, d in kapsam.items()})
        except ValueError as hata:
            raise GecersizVeri(str(hata)) from hata
        grubu = {str(s.id): None if s.sube_grubu_id is None else str(s.sube_grubu_id) for s in SinifDeposu(self.oturum).listele()}
        sonuc: dict[str, Any] = {"mevcut": None, "ezdikleri": [], "ezenler": []}
        for satir in self._kural(tur, None)["ozel_ayarlar"]:
            k = Kapsam(**{s: None if d is None else str(d) for s, d in satir["kapsam"].items()})
            if k == yeni:
                sonuc["mevcut"] = satir
            elif ortusur(yeni, k, grubu.get):
                sonuc["ezdikleri" if k.puan < yeni.puan else "ezenler"].append(satir)
        return sonuc

    def ozel_kaldir(self, tur: str, kapsam: KapsamSozlugu) -> dict[str, Any]:
        """Özel ayarı siler: o kapsamda okul değeri geçerli olur. Yoksa bir şey yapmaz."""
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        if not _kapsam_eksenleri(kapsam):
            raise GecersizVeri("Kaldırılacak özel ayarın öğretmenini, dersini, şubesini ya da şube grubunu belirtin")
        kayit = self._kayit(tur, kapsam)
        if kayit is not None:
            self.oturum.delete(kayit)
            self.oturum.commit()
        return self._kural(tur, self._kayit(tur))
