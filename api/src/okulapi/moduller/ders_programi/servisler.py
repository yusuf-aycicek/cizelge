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

from cozucu.kisitlar import GirdiHatasi, kural_olustur
from cozucu.model import KisitTanimi

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulDeposu, SinifDeposu
from okulapi.cekirdek.kiraci import oturumun_okulu
from okulapi.cekirdek.servisler import CrudServisi, GecersizVeri, KayitBulunamadi
from okulapi.moduller.ders_programi.depo import (
    DersAtamaDeposu,
    KisitDeposu,
    MusaitlikDeposu,
    ProgramDeposu,
    SeviyeSablonuDeposu,
    YerlesimDeposu,
)
from okulapi.moduller.ders_programi.modeller import DersAtama, Program, Yerlesim


def _bu_okulda_olmali(depo, kayit_id: uuid.UUID | None, varlik: str) -> None:
    """Otomatik okul filtresi yüzünden başka okulun kaydı da "bulunamaz"."""
    if kayit_id is not None and depo.getir(kayit_id) is None:
        raise GecersizVeri(f"{varlik} bu okulda bulunamadı")


class SeviyeSablonuServisi(CrudServisi):
    depo_sinifi = SeviyeSablonuDeposu
    varlik = "Seviye şablonu satırı"
    cakisma_mesaji = "Bu seviyenin şablonunda bu ders zaten var"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        _bu_okulda_olmali(DersDeposu(self.oturum), alanlar.get("ders_id"), "Ders")

    def uygula(self, seviye: int) -> dict[str, Any]:
        """Şablonu bu seviyedeki her şubeye uygular: eksik (sınıf, ders) için öğretmeni boş atama
        oluşturur. Var olan atamalar çoğaltılmaz ve değiştirilmez; saati şablondan farklı olanlar
        raporlanır (kullanıcı bilerek farklı tutmuş olabilir)."""
        sablon = self.depo.seviyenin(seviye)
        siniflar = [s for s in SinifDeposu(self.oturum).listele() if s.seviye == seviye]
        dersler = {d.id: d.ad for d in DersDeposu(self.oturum).listele()}
        atama_deposu = DersAtamaDeposu(self.oturum)
        var_olan = {(a.sinif_id, a.ders_id): a for a in atama_deposu.siniflarin([s.id for s in siniflar])}

        olusturulan, zaten_var, farkli = 0, 0, []
        for sinif in siniflar:
            for satir in sablon:
                atama = var_olan.get((sinif.id, satir.ders_id))
                if atama is None:
                    atama_deposu.ekle(DersAtama(sinif_id=sinif.id, ders_id=satir.ders_id, ogretmen_id=None,
                                                haftalik_saat=satir.haftalik_saat))
                    olusturulan += 1
                    continue
                zaten_var += 1
                if atama.haftalik_saat != satir.haftalik_saat:
                    farkli.append({"atama_id": atama.id, "sinif": sinif.ad, "ders": dersler[satir.ders_id],
                                   "atamadaki_saat": atama.haftalik_saat, "sablondaki_saat": satir.haftalik_saat})
        self.oturum.commit()
        return {"sube_sayisi": len(siniflar), "olusturulan": olusturulan, "zaten_var": zaten_var,
                "farkli_saatli": farkli}


class DersAtamaServisi(CrudServisi):
    depo_sinifi = DersAtamaDeposu
    varlik = "Ders ataması"
    cakisma_mesaji = "Bu sınıfa bu ders zaten atanmış (bir sınıf, bir ders, bir atama)"
    kullanimda_mesaji = "Bu ders ataması kullanılıyor, silinemez"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        _bu_okulda_olmali(SinifDeposu(self.oturum), alanlar.get("sinif_id"), "Sınıf")
        _bu_okulda_olmali(DersDeposu(self.oturum), alanlar.get("ders_id"), "Ders")
        _bu_okulda_olmali(OgretmenDeposu(self.oturum), alanlar.get("ogretmen_id"), "Öğretmen")


class MusaitlikServisi(CrudServisi):
    depo_sinifi = MusaitlikDeposu
    varlik = "Müsaitlik"
    cakisma_mesaji = "Bu öğretmenin bu saat için zaten bir müsaitlik kaydı var"

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        _bu_okulda_olmali(OgretmenDeposu(self.oturum), alanlar.get("ogretmen_id"), "Öğretmen")
        okul = OkulDeposu(self.oturum).getir(oturumun_okulu(self.oturum))
        gun = alanlar.get("gun", nesne.gun if nesne else 0)
        saat = alanlar.get("saat", nesne.saat if nesne else 0)
        if gun >= okul.gun_sayisi or saat >= okul.gunluk_ders_saati:
            raise GecersizVeri(
                f"Gün/saat okulun ayarlarının dışında (okulda {okul.gun_sayisi} gün, günde "
                f"{okul.gunluk_ders_saati} saat var; gün ve saat 0'dan başlar)"
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


class ProgramServisi:
    """Yalnızca okuma. Program üretme (oluşturma ve sonucu yazma) yapım sırası 3'te worker ile."""

    def __init__(self, oturum) -> None:
        self.oturum = oturum
        self.depo = ProgramDeposu(oturum)

    def listele(self) -> list[Program]:
        return self.depo.listele()

    def getir(self, program_id: uuid.UUID) -> Program:
        program = self.depo.getir(program_id)
        if program is None:
            raise KayitBulunamadi("Program")
        return program

    def yerlesimler(self, program_id: uuid.UUID) -> list[Yerlesim]:
        self.getir(program_id)
        return YerlesimDeposu(self.oturum).programin(program_id)
