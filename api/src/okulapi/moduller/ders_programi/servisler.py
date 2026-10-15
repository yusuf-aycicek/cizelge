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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulDeposu, SinifDeposu
from okulapi.cekirdek.kiraci import oturumun_okulu
from okulapi.cekirdek.kuyruk import IsKuyrugu, KuyrukHatasi
from okulapi.cekirdek.servisler import (
    CrudServisi,
    GecersizVeri,
    HizmetKullanilamiyor,
    KayitBulunamadi,
    KayitCakismasi,
)
from okulapi.moduller.ders_programi.depo import (
    DersAtamaDeposu,
    KisitDeposu,
    MusaitlikDeposu,
    ProgramDeposu,
    SeviyeSablonuDeposu,
    YerlesimDeposu,
)
from okulapi.moduller.ders_programi.modeller import ETKIN_DURUMLAR, DersAtama, Program, Yerlesim
from okulapi.moduller.ders_programi.uretim import (
    URETIM_BASARISIZ,
    URETIM_ISI,
    is_suresi_siniri_sn,
    takili_uretimleri_temizle,
)


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
        return self.depo.listele()

    def getir(self, program_id: uuid.UUID) -> Program:
        self._temizle()
        return self._getir(program_id)

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
