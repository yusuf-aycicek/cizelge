"""Ders programı servisleri: iş kuralları.

Kurallar:
- Atamanın, şablonun ve müsaitliğin gösterdiği sınıf, ders ve öğretmen **bu okulda** olmalı.
  Servis bunu önce kendisi denetler ve anlaşılır bir mesaj verir (422). Bileşik yabancı anahtar
  aynı kuralı veritabanında ikinci kez, kesin olarak uygular.
- Bir sınıf, bir ders, bir atama (UNIQUE ihlali -> 409).
- Müsaitliğin günü ve saati okulun ayarlarının içinde olmalı.
- Kısıt türü ve parametreleri çözücünün kendi kural kayıt defteriyle doğrulanır. API ve çözücü
  aynı kural listesini bilir; çözücüye yeni bir kural eklenince API'de değişiklik gerekmez.
"""

from __future__ import annotations

import uuid
from typing import Any

from cozucu.blok import BlokHesabi
from cozucu.kapsam import cozumle
from cozucu.kisitlar import GirdiHatasi, kural_olustur
from cozucu.model import KisitTanimi
from cozucu.on_kontrol import on_kontrol
from cozucu.on_kontrol import uyarilar as on_kontrol_uyarilari
from cozucu.yuk import YukHesabi
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulDeposu, SinifDeposu, SubeGrubuDeposu
from okulapi.cekirdek.kiraci import oturumun_okulu
from okulapi.cekirdek.kuyruk import IsKuyrugu, KuyrukHatasi
from okulapi.cekirdek.servisler import (
    CrudServisi,
    GecersizVeri,
    HizmetKullanilamiyor,
    KayitBulunamadi,
    KayitCakismasi,
    hafta_metni,
)
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.depo import (
    DersAtamaDeposu,
    KisitDeposu,
    MusaitlikDeposu,
    ProgramDeposu,
    SeviyeSablonuDeposu,
    SubeIstisnasiDeposu,
    YerlesimDeposu,
)
from okulapi.moduller.ders_programi.modeller import (
    ETKIN_DURUMLAR,
    DersAtama,
    Musaitlik,
    Program,
    SeviyeSablonu,
    SubeDersIstisnasi,
    Yerlesim,
)
from okulapi.moduller.ders_programi.elle import islem_sayilari
from okulapi.moduller.ders_programi.uretim import (
    URETIM_BASARISIZ,
    URETIM_ISI,
    is_suresi_siniri_sn,
    takili_uretimleri_temizle,
    veri_ozeti,
)


def _bu_okulda_olmali(depo, kayit_id: uuid.UUID | None, varlik: str) -> None:
    """Otomatik okul filtresi yüzünden başka okulun kaydı da "bulunamaz"."""
    if kayit_id is not None and depo.getir(kayit_id) is None:
        raise GecersizVeri(f"{varlik} bu okulda bulunamadı")


def sablon_kaynaklari(oturum) -> dict[uuid.UUID, uuid.UUID | None]:
    """Her şubenin kullandığı şablon: şubenin grubunun şablonunda en az bir ders varsa grubun
    kimliği, yoksa None (seviyenin şablonu). Tek kaynak: uygulama, istisna listesi ve arayüz aynı
    kuralı buradan alır."""
    dolu_gruplar = {s.sube_grubu_id for s in SeviyeSablonuDeposu(oturum).listele() if s.sube_grubu_id}
    return {s.id: s.sube_grubu_id if s.sube_grubu_id in dolu_gruplar else None
            for s in SinifDeposu(oturum).listele()}


def sube_sablonu(oturum, sinif) -> dict[uuid.UUID, int]:
    """Şubenin kullandığı şablonun dersleri: ders_id -> haftalık saat."""
    grup = sablon_kaynaklari(oturum).get(sinif.id)
    return {s.ders_id: s.haftalik_saat for s in SeviyeSablonuDeposu(oturum).sablonun(sinif.seviye, grup)}


class SeviyeSablonuServisi(CrudServisi):
    """Seviyenin ya da bir şube grubunun şablonu (`sube_grubu_id`; K5)."""

    depo_sinifi = SeviyeSablonuDeposu
    varlik = "Seviye şablonu satırı"
    cakisma_mesaji = "Bu şablonda bu ders zaten var"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        _bu_okulda_olmali(DersDeposu(self.oturum), alanlar.get("ders_id"), "Ders")
        if alanlar.get("sube_grubu_id") is not None:
            grup = self._grup(alanlar["sube_grubu_id"])
            if grup.seviye != alanlar.get("seviye"):
                raise GecersizVeri(f"\"{grup.ad}\" {grup.seviye}. sınıfların grubu; şablonu {grup.seviye}. sınıf olmalı")

    def _grup(self, grup_id: uuid.UUID):
        grup = SubeGrubuDeposu(self.oturum).getir(grup_id)
        if grup is None:
            raise GecersizVeri("Şube grubu bu okulda bulunamadı")
        return grup

    def toplu_kaydet(self, seviye: int, sube_grubu_id: uuid.UUID | None,
                     satirlar: list[dict[str, Any]]) -> list[SeviyeSablonu]:
        """Şablonu tek seferde kaydeder: şablon tam olarak saati 0'dan büyük satırlar olur. Listede
        olmayan ya da saati 0 olan ders şablondan çıkar; saati değişen güncellenir. Ya hepsi ya hiçbiri."""
        if sube_grubu_id is not None and self._grup(sube_grubu_id).seviye != seviye:
            raise GecersizVeri("Şube grubu bu seviyede değil")
        istenen: dict[uuid.UUID, int] = {}
        ders_deposu = DersDeposu(self.oturum)
        for satir in satirlar:
            if satir["ders_id"] in istenen:
                raise GecersizVeri("Aynı ders listede iki kez var")
            istenen[satir["ders_id"]] = satir["haftalik_saat"]
            if satir["haftalik_saat"] > 0:
                _bu_okulda_olmali(ders_deposu, satir["ders_id"], "Ders")
        mevcut = {s.ders_id: s for s in self.depo.sablonun(seviye, sube_grubu_id)}
        for ders_id, satir in mevcut.items():
            saat = istenen.get(ders_id, 0)
            if saat == 0:
                self.depo.sil(satir)
            elif satir.haftalik_saat != saat:
                satir.haftalik_saat = saat
        for ders_id, saat in istenen.items():
            if saat > 0 and ders_id not in mevcut:
                self.depo.ekle(SeviyeSablonu(seviye=seviye, sube_grubu_id=sube_grubu_id, ders_id=ders_id,
                                             haftalik_saat=saat))
        self.oturum.commit()
        return self.depo.sablonun(seviye, sube_grubu_id)

    def hepsine_uygula(self) -> list[dict[str, Any]]:
        """Dolu her şablonu (seviye ve şube grubu) şubelerine uygular; rapor seviye seviye. Tek işlem:
        bir şablon hata verirse hiçbiri uygulanmaz. Şablonların şubeleri ayrık olduğundan
        (`sablon_kaynaklari`) sıra sonucu değiştirmez."""
        gruplar = {g.id: g.ad for g in SubeGrubuDeposu(self.oturum).listele()}
        anahtarlar = sorted({(s.seviye, s.sube_grubu_id) for s in self.depo.listele()},
                            key=lambda k: (k[0], k[1] is not None, gruplar.get(k[1], "").casefold() if k[1] else ""))
        raporlar = [
            {"seviye": seviye, "sube_grubu_id": grup, "sablon": gruplar[grup] if grup else f"{seviye}. sınıflar",
             "sonuc": self.uygula(seviye, grup, kaydet=False)}
            for seviye, grup in anahtarlar
        ]
        self.oturum.commit()
        return raporlar

    def uygula(self, seviye: int, sube_grubu_id: uuid.UUID | None = None, kaydet: bool = True) -> dict[str, Any]:
        """Şablonu, onu kullanan şubelere uygular: eksik (sınıf, ders) için öğretmeni boş atama
        oluşturur. Var olan atamalar çoğaltılmaz ve değiştirilmez; saati şablondan farklı olanlar
        raporlanır (kullanıcı bilerek farklı tutmuş olabilir).

        - Grubun şablonu grubun şubelerine; seviyenin şablonu o seviyede kendi grubunun şablonunu
          kullanmayan şubelere uygulanır (`sablon_kaynaklari`). Ötekiler raporda adıyla geçer.
        - Şube istisnaları: `almaz` dersi eklenmez (silinmiş ders geri gelmez), `ek` dersi
          şablonda olmasa da istisnadaki saatle eklenir. İkisi de raporda listelenir.
        """
        if sube_grubu_id is not None and self._grup(sube_grubu_id).seviye != seviye:
            raise GecersizVeri("Şube grubu bu seviyede değil")
        sablon = self.depo.sablonun(seviye, sube_grubu_id)
        kaynak = sablon_kaynaklari(self.oturum)
        seviyedekiler = [s for s in SinifDeposu(self.oturum).listele() if s.seviye == seviye]
        siniflar = [s for s in seviyedekiler if kaynak[s.id] == sube_grubu_id]
        gruplar = {g.id: g.ad for g in SubeGrubuDeposu(self.oturum).listele()}
        dersler = {d.id: d.ad for d in DersDeposu(self.oturum).listele()}
        atama_deposu = DersAtamaDeposu(self.oturum)
        var_olan = {(a.sinif_id, a.ders_id): a for a in atama_deposu.siniflarin([s.id for s in siniflar])}
        istisnalar = {(i.sinif_id, i.ders_id): i for i in SubeIstisnasiDeposu(self.oturum).listele()}

        olusturulan, zaten_var, farkli, atlanan, ek = 0, 0, [], [], []

        def ekle(sinif, ders_id: uuid.UUID, saat: int) -> None:
            atama_deposu.ekle(DersAtama(sinif_id=sinif.id, ders_id=ders_id, ogretmen_id=None, haftalik_saat=saat))

        for sinif in siniflar:
            sablondaki = set()
            for satir in sablon:
                sablondaki.add(satir.ders_id)
                istisna = istisnalar.get((sinif.id, satir.ders_id))
                atama = var_olan.get((sinif.id, satir.ders_id))
                if istisna is not None and istisna.tur == "almaz":
                    atlanan.append({"sinif": sinif.ad, "ders": dersler[satir.ders_id]})
                    continue
                if atama is None:
                    ekle(sinif, satir.ders_id, satir.haftalik_saat)
                    olusturulan += 1
                    continue
                zaten_var += 1
                if atama.haftalik_saat != satir.haftalik_saat:
                    farkli.append({"atama_id": atama.id, "sinif": sinif.ad, "ders": dersler[satir.ders_id],
                                   "atamadaki_saat": atama.haftalik_saat, "sablondaki_saat": satir.haftalik_saat})
            for (sinif_id, ders_id), istisna in istisnalar.items():
                if sinif_id != sinif.id or istisna.tur != "ek" or ders_id in sablondaki:
                    continue
                eklendi = (sinif.id, ders_id) not in var_olan
                if eklendi:
                    ekle(sinif, ders_id, istisna.haftalik_saat)
                ek.append({"sinif": sinif.ad, "ders": dersler[ders_id], "haftalik_saat": istisna.haftalik_saat,
                           "eklendi": eklendi})
        if kaydet:
            self.oturum.commit()
        else:
            self.oturum.flush()
        siralama = lambda d: (d["sinif"].casefold(), d["ders"].casefold())  # noqa: E731
        return {
            "sube_sayisi": len(siniflar), "subeler": sorted(s.ad for s in siniflar), "olusturulan": olusturulan,
            "zaten_var": zaten_var, "farkli_saatli": farkli,
            "istisna_atlanan": sorted(atlanan, key=siralama), "istisna_ek": sorted(ek, key=siralama),
            "baska_sablonlu": sorted(
                ({"sinif": s.ad, "sablon": gruplar[kaynak[s.id]] if kaynak[s.id] else f"{seviye}. sınıflar"}
                 for s in seviyedekiler if s not in siniflar),
                key=lambda d: d["sinif"].casefold(),
            ),
        }


class SubeIstisnasiServisi:
    """Şubenin şablondan ayrıldığı dersler (K5): "bu şube bu dersi almaz" ve "ek olarak alır".

    İstisna ders dağılımını da hemen değiştirir, kullanıcı iki ayrı iş yapmasın:
    - `almaz` konunca şubenin o dersi (varsa) kaldırılır; istisna kaldırılınca ders şubenin
      şablonundaysa şablondaki saatle (öğretmeni boş) geri eklenir.
    - `ek` konunca ders şubede yoksa istisnadaki saatle eklenir. `ek` kaldırılınca ders şubede
      kalır (silmek veri kaybı olurdu); dersi kaldırmak ders dağılımından yapılır.
    """

    def __init__(self, oturum) -> None:
        self.oturum = oturum
        self.depo = SubeIstisnasiDeposu(oturum)

    def listele(self) -> list[dict[str, Any]]:
        """İstisnalar, şablon ve atamalarla karşılaştırılmış: tutarsız olan (ör. "almaz" ama
        dersi atanmış) kullanıcıya söylenir; otomatik düzeltilmez."""
        siniflar = {s.id: s for s in SinifDeposu(self.oturum).listele()}
        dersler = {d.id: d.ad for d in DersDeposu(self.oturum).listele()}
        atamalar = {(a.sinif_id, a.ders_id) for a in DersAtamaDeposu(self.oturum).listele()}
        kaynak = sablon_kaynaklari(self.oturum)
        sablonlar = {(s.seviye, s.sube_grubu_id, s.ders_id) for s in SeviyeSablonuDeposu(self.oturum).listele()}
        satirlar = []
        for i in self.depo.listele():
            sinif, ders = siniflar[i.sinif_id], dersler[i.ders_id]
            sablonda = (sinif.seviye, kaynak[sinif.id], i.ders_id) in sablonlar
            atanmis = (i.sinif_id, i.ders_id) in atamalar
            uyari = None
            if i.tur == "almaz" and atanmis:
                uyari = f"{sinif.ad} için \"{ders} almaz\" istisnası var, ama {sinif.ad}'ye {ders} atanmış."
            elif i.tur == "ek" and not atanmis:
                uyari = f"{ders} {sinif.ad}'nin ek dersi, ama şubede yok; şablonu uygulayınca eklenir."
            satirlar.append({"id": i.id, "sinif_id": i.sinif_id, "ders_id": i.ders_id, "tur": i.tur,
                             "haftalik_saat": i.haftalik_saat, "sinif_adi": sinif.ad, "ders_adi": ders,
                             "sablonda": sablonda, "atanmis": atanmis, "uyari": uyari})
        return sorted(satirlar, key=lambda s: (s["sinif_adi"].casefold(), s["ders_adi"].casefold()))

    def olustur(self, sinif_id: uuid.UUID, ders_id: uuid.UUID, tur: str, haftalik_saat: int | None) -> dict[str, Any]:
        sinif = SinifDeposu(self.oturum).getir(sinif_id)
        if sinif is None:
            raise GecersizVeri("Şube bu okulda bulunamadı")
        _bu_okulda_olmali(DersDeposu(self.oturum), ders_id, "Ders")
        if tur == "almaz" and haftalik_saat is not None:
            raise GecersizVeri("\"Almaz\" istisnasında haftalık saat olmaz")
        if tur == "ek" and haftalik_saat is None:
            raise GecersizVeri("Ek ders için haftalık saat girin")
        atama_deposu = DersAtamaDeposu(self.oturum)
        atama = next((a for a in atama_deposu.siniflarin([sinif_id]) if a.ders_id == ders_id), None)
        try:
            istisna = self.depo.ekle(SubeDersIstisnasi(sinif_id=sinif_id, ders_id=ders_id, tur=tur,
                                                       haftalik_saat=haftalik_saat))
            if tur == "almaz" and atama is not None:
                atama_deposu.sil(atama)  # eski programlardaki yerleşimleri de gider (CASCADE)
            elif tur == "ek" and atama is None:
                atama_deposu.ekle(DersAtama(sinif_id=sinif_id, ders_id=ders_id, ogretmen_id=None,
                                            haftalik_saat=haftalik_saat))
            self.oturum.commit()
        except IntegrityError as hata:
            self.oturum.rollback()
            raise KayitCakismasi("Bu şubenin bu ders için zaten bir istisnası var") from hata
        return next(s for s in self.listele() if s["id"] == istisna.id)

    def sil(self, istisna_id: uuid.UUID) -> dict[str, Any]:
        """İstisnayı kaldırır. `almaz` kalkınca ders şubenin şablonundaysa geri eklenir."""
        istisna = self.depo.getir(istisna_id)
        if istisna is None:
            raise KayitBulunamadi("Şube istisnası")
        geri_eklenen = None
        if istisna.tur == "almaz":
            sinif = SinifDeposu(self.oturum).getir(istisna.sinif_id)
            saat = sube_sablonu(self.oturum, sinif).get(istisna.ders_id)
            atama_deposu = DersAtamaDeposu(self.oturum)
            var = any(a.ders_id == istisna.ders_id for a in atama_deposu.siniflarin([sinif.id]))
            if saat is not None and not var:
                atama_deposu.ekle(DersAtama(sinif_id=sinif.id, ders_id=istisna.ders_id, ogretmen_id=None,
                                            haftalik_saat=saat))
                geri_eklenen = saat
        self.depo.sil(istisna)
        self.oturum.commit()
        return {"geri_eklenen_saat": geri_eklenen}


class DersAtamaServisi(CrudServisi):
    depo_sinifi = DersAtamaDeposu
    varlik = "Ders ataması"
    cakisma_mesaji = "Bu sınıfa bu ders zaten atanmış (bir sınıf, bir ders, bir atama)"
    kullanimda_mesaji = "Bu ders ataması kullanılıyor, silinemez"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        _bu_okulda_olmali(SinifDeposu(self.oturum), alanlar.get("sinif_id"), "Sınıf")
        _bu_okulda_olmali(DersDeposu(self.oturum), alanlar.get("ders_id"), "Ders")
        _bu_okulda_olmali(OgretmenDeposu(self.oturum), alanlar.get("ogretmen_id"), "Öğretmen")

    def toplu_ogretmen_ata(self, atama_idleri: list[uuid.UUID], ogretmen_id: uuid.UUID | None) -> list[DersAtama]:
        """Hepsi ya da hiçbiri: atamalardan biri bu okulda yoksa hiçbiri değişmez (404)."""
        _bu_okulda_olmali(OgretmenDeposu(self.oturum), ogretmen_id, "Öğretmen")
        atamalar = [self.getir(i) for i in dict.fromkeys(atama_idleri)]

        def uygula() -> list[DersAtama]:
            for atama in atamalar:
                atama.ogretmen_id = ogretmen_id
            self.oturum.flush()
            return atamalar

        return self._kaydet(uygula)

    def sil(self, kayit_id: uuid.UUID) -> None:
        """Şubenin ek dersi kaldırılınca "ek" istisnası da kalkar: şablon uygulanınca geri gelmesin."""
        atama = self.getir(kayit_id)
        for i in SubeIstisnasiDeposu(self.oturum).listele():
            if (i.sinif_id, i.ders_id, i.tur) == (atama.sinif_id, atama.ders_id, "ek"):
                self.oturum.delete(i)
        super().sil(kayit_id)


def on_kontrol_sonucu(oturum) -> dict[str, list[dict[str, Any]]]:
    """Program üretiminin ön kontrolü, üretmeden. Worker'ın çözücüye verdiği girdi
    (`cozum_girdisi_olustur`) ve çözücünün çağırdığı fonksiyon (`cozucu.on_kontrol.on_kontrol`)
    aynıdır: burada geçen bir okul üretimde ön kontrolde takılmaz, takılan da burada görünür.
    Özel ayarlar, müsaitlik, kurallar dahil (dağılım özeti yalnızca yük hesabını içerir)."""
    girdi = cozum_girdisi_olustur(oturum)
    return {
        "celiskiler": [_celiski(c) for c in on_kontrol(girdi)],
        # Programı engellemeyen uyarılar (öğretmenin haftalık yükü eşiklerin dışında; K6).
        "uyarilar": [_celiski(c) for c in on_kontrol_uyarilari(girdi)],
    }


def _celiski(c) -> dict[str, Any]:
    return {"tur": c.tur, "mesaj": c.mesaj, "ilgili": list(c.ilgili)}


# Okul önerisinin bir atamada neden uygulanmadığı, kısaca (ders listesinde gösterilir).
BLOK_SORUN_METINLERI = {
    "toplam": "şeklin toplamı haftalık saate eşit değil",
    "gunluk_sinir": "en büyük blok günlük sınırı aşıyor",
    "gun_sayisi": "blok sayısı gün sayısından fazla",
    "gune_sigmaz": "blok hiçbir güne sığmıyor (gün uzunluğu ya da öğle arası)",
    "musaitlik": "öğretmenin müsaitliğine sığmıyor",
    "kilit": "kilitli hücreler şekle uymuyor",
}


def dagilim_sekilleri(oturum) -> list[dict[str, Any]]:
    """Her atamanın dağılım şekli ve kaynağı. Hesap çözücüdeki kuralla aynı (`cozucu.blok`)."""
    girdi = cozum_girdisi_olustur(oturum)
    hesap = BlokHesabi(girdi)
    sinif_adi = {s.id: s.ad for s in girdi.siniflar}
    satirlar = []
    for a in girdi.atamalar:
        istenen, desen = hesap.istenen(a), hesap.desen(a)
        ozel = cozumle(hesap._ozeller, girdi.varlik(sinif_id=a.sinif_id, ders_id=a.ders_id))
        if ozel is not None:
            kaynak = "ders_sube" if ozel.kapsam.sinif_id else "ders_grup" if ozel.kapsam.sube_grubu_id else "ders"
        else:
            kaynak = "okul" if desen is not None else "yok"
        dusen = istenen is not None and not istenen.ozel and desen is None
        nedenler = hesap.sorunlar(a, istenen) if dusen else []
        sorunlar = hesap.sorunlar(a, istenen) if istenen is not None and istenen.ozel else []
        satirlar.append({
            "atama_id": a.id, "ders_id": a.ders_id, "sinif_id": a.sinif_id, "sinif_adi": sinif_adi[a.sinif_id],
            "haftalik_saat": a.haftalik_saat,
            "desen": list(desen.bloklar) if desen else None,
            "metin": desen.metin if desen else "blok yok",
            "kaynak": kaynak,
            "dusen_oneri": istenen.metin if dusen else None,
            "nedenler": [BLOK_SORUN_METINLERI[n] for n in nedenler],
            "sorunlar": [BLOK_SORUN_METINLERI[n] for n in sorunlar],
        })
    return satirlar


def dagilim_ozeti(oturum) -> dict[str, Any]:
    """Öğretmen ve sınıf yükleri, öğretmensiz atama sayısı. Hesap ve mesajlar çözücünün ön
    kontrolüyle aynı kaynaktandır (`cozucu.yuk.YukHesabi`, ADR 0015); burada yeniden yazılmaz."""
    girdi = cozum_girdisi_olustur(oturum)
    hesap = YukHesabi(girdi)
    siniflar = hesap.sinif_yukleri()
    return {
        "haftalik_kapasite": girdi.ayar.haftalik_kapasite,
        "ogretmen_gunluk_siniri": hesap.m,
        "ogretmensiz_atama": sum(y.ogretmensiz_atama for y in siniflar),
        "ogretmenler": [
            {"ogretmen_id": y.ogretmen_id, "ders_saati": y.ders_saati, "musait_saat": y.musait_saat,
             "kullanilabilir_saat": y.kullanilabilir_saat, "hedefli_kapasite": hesap.hedefli_kapasite(y.ogretmen_id),
             "asim": y.asim, "mesaj": hesap.ogretmen_mesaji(y),
             "yuk_uyarisi": hesap.ogretmen_yuk_uyarisi(y)}
            for y in hesap.ogretmen_yukleri()
        ],
        "siniflar": [
            {"sinif_id": y.sinif_id, "ders_saati": y.ders_saati, "kapasite": y.kapasite,
             "ogretmensiz_atama": y.ogretmensiz_atama, "asim": y.asim, "mesaj": hesap.sinif_mesaji(y)}
            for y in siniflar
        ],
    }


class MusaitlikServisi(CrudServisi):
    depo_sinifi = MusaitlikDeposu
    varlik = "Müsaitlik"
    cakisma_mesaji = "Bu öğretmenin bu saat için zaten bir müsaitlik kaydı var"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        _bu_okulda_olmali(OgretmenDeposu(self.oturum), alanlar.get("ogretmen_id"), "Öğretmen")
        okul = OkulDeposu(self.oturum).getir(oturumun_okulu(self.oturum))
        gun = alanlar.get("gun", nesne.gun if nesne else 0)
        saat = alanlar.get("saat", nesne.saat if nesne else 0)
        if not okul.aralikta(gun, saat):
            raise GecersizVeri(
                f"Gün/saat okulun ayarlarının dışında (okulda {hafta_metni(okul)} var; gün ve saat 0'dan başlar)"
            )


class KisitServisi(CrudServisi):
    depo_sinifi = KisitDeposu
    varlik = "Kısıt"
    cakisma_mesaji = "Bu kural bu okulda zaten tanımlı; değiştirmek için var olanı güncelleyin"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        tanim = KisitTanimi(
            tur=alanlar.get("tur", nesne.tur if nesne else ""),
            parametreler=alanlar.get("parametreler", nesne.parametreler if nesne else {}) or {},
            zorunlu=alanlar.get("zorunlu", nesne.zorunlu if nesne else True),
            agirlik=alanlar.get("agirlik", nesne.agirlik if nesne else 1),
        )
        try:
            kural_olustur(tanim)  # çözücünün kayıt defteri: tür, kip ve parametreler geçerli mi?
        except GirdiHatasi as hata:
            raise GecersizVeri(str(hata)) from hata


ETKIN_URETIM_VAR = (
    "Bu okulun devam eden bir program üretimi var. Bitmesini bekleyin; durumu program listesinden "
    "izleyebilirsiniz."
)
KUYRUGA_ULASILAMADI = "Program üretim kuyruğuna ulaşılamadı. Biraz sonra yeniden deneyin."


class ProgramServisi:
    """Program üretme isteği, durum sorgulama, yerleşimler (ADR 0011).

    Okuma ve yeni üretim isteği önce takılı üretimleri temizler (`takili_uretimleri_temizle`):
    çökmüş bir worker'ın ya da kuyruğa hiç girmemiş bir isteğin bıraktığı program, okulun yeni
    üretim yapmasını kalıcı olarak engellemesin. `kuyruk` verilmezse yalnızca süreye dayalı
    (`uretiliyor`) temizlik yapılır.
    """

    def __init__(self, oturum, kuyruk: IsKuyrugu | None = None) -> None:
        self.oturum = oturum
        self.kuyruk = kuyruk
        self.depo = ProgramDeposu(oturum)

    def _temizle(self) -> None:
        if takili_uretimleri_temizle(self.oturum, self.kuyruk):
            self.oturum.commit()

    def listele(self) -> list[Program]:
        self._temizle()
        return self._eski_veri(self.depo.listele())

    def getir(self, program_id: uuid.UUID) -> Program:
        self._temizle()
        return self._eski_veri([self._getir(program_id)])[0]

    def _eski_veri(self, programlar: list[Program]) -> list[Program]:
        """Hazır programlara `eski_veri` (geçici öznitelik, yanıtta görünür): üretildiği andaki
        verinin özeti şimdikinden farklı mı. Şimdiki özet istek başına bir kez hesaplanır; özeti
        olmayan eski programda bilinmiyor (None)."""
        simdiki: str | None = None
        sayilar = islem_sayilari(self.oturum, [p.id for p in programlar])
        for p in programlar:
            p.elle_duzeltme = sayilar.get(p.id, 0)  # type: ignore[attr-defined]
            p.eski_veri = None  # type: ignore[attr-defined]
            if p.durum == "hazir" and p.veri_ozeti is not None:
                simdiki = simdiki or veri_ozeti(cozum_girdisi_olustur(self.oturum))
                p.eski_veri = p.veri_ozeti != simdiki  # type: ignore[attr-defined]
        return programlar

    def yeniden_adlandir(self, program_id: uuid.UUID, ad: str) -> Program:
        program = self._getir(program_id)
        program.ad = ad
        self.oturum.commit()
        return self.getir(program_id)

    def sil(self, program_id: uuid.UUID) -> None:
        """Bitmiş programı siler (yerleşimleri de). Üretimi süren program silinemez (409): worker
        sonucunu yazmaya çalışırdı. Bu programı temel alan programların bağı kopar (SET NULL)."""
        program = self._getir(program_id)
        if program.durum in ETKIN_DURUMLAR:
            raise KayitCakismasi("Üretimi süren program silinemez; bitmesini bekleyin")
        self.oturum.delete(program)
        self.oturum.commit()

    def fark(self, program_id: uuid.UUID, ile_id: uuid.UUID | None) -> dict[str, Any]:
        """Bu programın, başka bir programdan (verilmezse temel programından) farklı hücreleri.

        Hücreler (şube, ders, gün, saat) ile karşılaştırılır: aynı dersin aynı şubede aynı saatte
        olması "değişmedi" demektir. `degisen`: yeri değişen ders saati sayısı (kalite ölçüsündeki
        "değişen yerleşim"le aynı tanım); `subeler`: hangi şubede kaç saat."""
        program = self._getir(program_id)
        ile_id = ile_id or program.temel_program_id
        if ile_id is None:
            raise GecersizVeri("Karşılaştırılacak program yok: bu program bir programı temel almadan üretildi")
        ile = self._getir(ile_id)
        atamalar = {a.id: a for a in DersAtamaDeposu(self.oturum).listele()}
        yerlesimler = YerlesimDeposu(self.oturum)

        def hucre(y: Yerlesim) -> tuple:
            a = atamalar[y.ders_atama_id]
            return a.sinif_id, a.ders_id, y.gun, y.saat

        oteki = {hucre(y) for y in yerlesimler.programin(ile.id)}
        degisen = [y for y in yerlesimler.programin(program.id) if hucre(y) not in oteki]
        adlar = {s.id: s.ad for s in SinifDeposu(self.oturum).listele()}
        sayilar: dict[uuid.UUID, int] = {}
        for y in degisen:
            sinif = atamalar[y.ders_atama_id].sinif_id
            sayilar[sinif] = sayilar.get(sinif, 0) + 1
        return {
            "ile_id": ile.id,
            "ile_ad": ile.ad,
            "degisen": len(degisen),
            "subeler": sorted(({"sinif_id": k, "ad": adlar.get(k, "?"), "sayi": n} for k, n in sayilar.items()),
                              key=lambda x: x["ad"]),
            "hucreler": [{"ders_atama_id": y.ders_atama_id, "gun": y.gun, "saat": y.saat} for y in degisen],
        }

    def _getir(self, program_id: uuid.UUID) -> Program:
        program = self.depo.getir(program_id)
        if program is None:
            raise KayitBulunamadi("Program")
        return program

    def yerlesimler(self, program_id: uuid.UUID) -> list[Yerlesim]:
        self._getir(program_id)
        return YerlesimDeposu(self.oturum).programin(program_id)

    def uret(self, ad: str, temel_program_id: uuid.UUID | None, sure_siniri_sn: int) -> Program:
        """Yeni üretim isteği: program (`bekliyor`) eklenir, iş kuyruğa konur, sonra commit.

        Sıra bilerek "önce kuyruk, sonra commit"tir (ADR 0011 madde 4): commit edilmemiş program
        başka işlemlere görünmez, yani temizlik "bekliyor ama işi kuyrukta yok" durumunu yalnızca
        gerçekten öksüz kalmış programlarda görür. Worker işi commit'ten önce alırsa programı kısa
        bir süre yeniden arar (`uretim.BULUNAMAZSA_BEKLE_SN`).
        """
        if self.kuyruk is None:
            raise RuntimeError("Program üretmek için iş kuyruğu gerekli")
        self._temizle()  # 409 denetiminden önce: takılı üretim yeni isteği engellemesin
        etkin = select(Program.id).where(Program.durum.in_(ETKIN_DURUMLAR)).limit(1)
        if self.oturum.scalar(etkin) is not None:
            raise KayitCakismasi(ETKIN_URETIM_VAR)
        if temel_program_id is not None:
            temel = self._getir(temel_program_id)
            if temel.durum != "hazir":
                raise GecersizVeri("Temel alınacak program hazır (başarıyla üretilmiş) bir program olmalı")

        program = Program(ad=ad, temel_program_id=temel_program_id, sure_siniri_sn=sure_siniri_sn)
        self.oturum.add(program)
        try:
            self.oturum.flush()  # aynı anda gelen ikinci istek burada kısmi benzersiz indekse takılır
        except IntegrityError as hata:
            self.oturum.rollback()
            if "uq_program_okul_id_etkin" in str(hata.orig):
                raise KayitCakismasi(ETKIN_URETIM_VAR) from hata
            raise

        okul_id = oturumun_okulu(self.oturum)
        try:
            self.kuyruk.kuyruga_ekle(
                is_id=str(program.id),  # işin kimliği = program kimliği
                fonksiyon=URETIM_ISI,
                argumanlar={"okul_id": str(okul_id), "program_id": str(program.id)},
                zaman_asimi_sn=is_suresi_siniri_sn(sure_siniri_sn),
                basarisizlikta=URETIM_BASARISIZ,
            )
        except KuyrukHatasi as hata:
            # Program aynı istekte kapatılır: "bekliyor" kalıp okulu engellemesin, kullanıcı da
            # isteğinin kaydını ve nedenini görsün.
            program.durum, program.hata_mesaji, program.bitis = "basarisiz", KUYRUGA_ULASILAMADI, func.now()
            self.oturum.commit()
            raise HizmetKullanilamiyor(KUYRUGA_ULASILAMADI) from hata
        self.oturum.commit()
        return program


class MusaitlikCizelgesiServisi:
    """Bir öğretmenin müsaitlik çizelgesi (5.5): hücreler ve yükü, toplu değişiklik.

    - Çizelgede yalnızca müsait **olmayan** hücreler kayıtlıdır (`gelemez`, `tercih_etmez`);
      "müsait" kaydın silinmesidir.
    - Toplu değişiklik tek istektir ve **ya hep ya hiç**: önce hepsi denetlenir, biri geçersizse
      hiçbiri yazılmaz (sürükleyerek işaretlenen 12 hücreden biri okulun saatleri dışındaysa yarım
      bir değişiklik kalmaz). Yazım tek işlemdir (commit sonda).
    - Cevapta öğretmenin yükü de vardır; hesap ön kontrol ve dağılım özetiyle aynıdır
      (`cozucu.yuk.YukHesabi`, ADR 0015). Arayüz kapasite uyarısını buradan gösterir.
    """

    def __init__(self, oturum) -> None:
        self.oturum = oturum

    def _ogretmen(self, ogretmen_id: uuid.UUID):
        ogretmen = OgretmenDeposu(self.oturum).getir(ogretmen_id)
        if ogretmen is None:
            raise KayitBulunamadi("Öğretmen")
        return ogretmen

    def _kayitlar(self, ogretmen_id: uuid.UUID) -> dict[tuple[int, int], Musaitlik]:
        satirlar = self.oturum.scalars(select(Musaitlik).where(Musaitlik.ogretmen_id == ogretmen_id))
        return {(m.gun, m.saat): m for m in satirlar}

    def getir(self, ogretmen_id: uuid.UUID) -> dict[str, Any]:
        self._ogretmen(ogretmen_id)
        hucreler = sorted(self._kayitlar(ogretmen_id).values(), key=lambda m: (m.gun, m.saat))
        girdi = cozum_girdisi_olustur(self.oturum)
        hesap = YukHesabi(girdi)
        yuk = next(y for y in hesap.ogretmen_yukleri() if y.ogretmen_id == str(ogretmen_id))
        return {
            "ogretmen_id": ogretmen_id,
            "hucreler": [{"gun": m.gun, "saat": m.saat, "durum": m.durum} for m in hucreler],
            "yuk": {
                "ders_saati": yuk.ders_saati,
                "musait_saat": yuk.musait_saat,
                "kullanilabilir_saat": yuk.kullanilabilir_saat,
                "asim": yuk.asim,
                "mesaj": hesap.ogretmen_mesaji(yuk),
            },
        }

    def degistir(self, ogretmen_id: uuid.UUID, degisiklikler: list[dict[str, Any]]) -> dict[str, Any]:
        self._ogretmen(ogretmen_id)
        okul = OkulDeposu(self.oturum).getir(oturumun_okulu(self.oturum))
        gorulen: set[tuple[int, int]] = set()
        for d in degisiklikler:  # önce hepsi denetlenir: biri hatalıysa hiçbiri yazılmaz
            hucre = (d["gun"], d["saat"])
            if not okul.aralikta(d["gun"], d["saat"]):
                raise GecersizVeri(
                    f"Gün/saat okulun ayarlarının dışında: {d['gun'] + 1}. gün {d['saat'] + 1}. saat (okulda "
                    f"{hafta_metni(okul)} var). Hiçbir hücre değiştirilmedi."
                )
            if hucre in gorulen:
                raise GecersizVeri(f"Aynı hücre iki kez verildi: {d['gun'] + 1}. gün {d['saat'] + 1}. saat")
            gorulen.add(hucre)
        kayitlar = self._kayitlar(ogretmen_id)
        for d in degisiklikler:
            mevcut = kayitlar.get((d["gun"], d["saat"]))
            if d["durum"] == "musait":
                if mevcut is not None:
                    self.oturum.delete(mevcut)
            elif mevcut is None:
                self.oturum.add(Musaitlik(ogretmen_id=ogretmen_id, gun=d["gun"], saat=d["saat"], durum=d["durum"]))
            else:
                mevcut.durum = d["durum"]
        self.oturum.commit()
        return self.getir(ogretmen_id)
