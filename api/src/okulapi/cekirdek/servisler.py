"""Servis katmanı: iş kuralları ve işlem (transaction) sınırı.

Servis bir iş birimini baştan sona yürütür ve sonunda `commit` eder. Hata olursa değişiklikler
geri alınır. HTTP'yi bilmez: hataları kendi istisnalarıyla (`KayitBulunamadi`, `KayitCakismasi`,
`GecersizVeri`) bildirir, API katmanı bunları durum kodlarına çevirir.

Veritabanı kısıt ihlalleri (PostgreSQL hata kodları, SQLSTATE) anlaşılır mesajlara çevrilir:
- 23505 unique_violation: aynı adla ikinci kayıt;
- 23503 foreign_key_violation: başka kayıtların kullandığı bir kaydı silmek;
- 23514 check_violation: CHECK kısıtı (ör. seviye 1-12) ihlali.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from okulapi.cekirdek.ders_renkleri import RENK_KODLARI, siradaki_renk
from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulaAitDepo, OkulDeposu, SinifDeposu
from okulapi.cekirdek.kiraci import veritabaninda_okulu_ayarla
from okulapi.cekirdek.modeller import Okul, OkulaAitMixin
from okulapi.cekirdek.modul import Modul

T = TypeVar("T", bound=OkulaAitMixin)

BENZERSIZLIK_IHLALI = "23505"
YABANCI_ANAHTAR_IHLALI = "23503"
CHECK_IHLALI = "23514"


class KayitBulunamadi(Exception):
    def __init__(self, varlik: str) -> None:
        super().__init__(f"{varlik} bulunamadı")


class KayitCakismasi(Exception):
    pass


class GecersizVeri(Exception):
    pass


class AyarEtkisiOnayGerekli(KayitCakismasi):
    """Okul ayarı değişikliği modül verisini etkiliyor ve bu açıkça onaylanmadı (409)."""

    def __init__(self, etkiler: list[str]) -> None:
        super().__init__("Bu değişiklik mevcut kayıtları etkiliyor; devam etmek için etkileri onaylayın.")
        self.etkiler = etkiler


class HizmetKullanilamiyor(Exception):
    """Bağımlı bir altyapı parçasına (ör. iş kuyruğu) ulaşılamadı; istek sonra yeniden denenebilir."""


def _sqlstate(hata: IntegrityError) -> str | None:
    return getattr(hata.orig, "sqlstate", None)


class CrudServisi(Generic[T]):
    """Okula ait bir varlık için temel CRUD. Alt sınıf depoyu ve mesajları verir."""

    depo_sinifi: type[OkulaAitDepo[T]]
    varlik: str  # mesajlarda: "Öğretmen"
    cakisma_mesaji: str = "Bu kayıt zaten var"
    kullanimda_mesaji: str = "Bu kayıt başka kayıtlar tarafından kullanılıyor, silinemez"

    def __init__(self, oturum: Session, moduller: Sequence[Modul] = ()) -> None:
        self.oturum = oturum
        self.depo = self.depo_sinifi(oturum)
        self.moduller = moduller

    def listele(self) -> list[T]:
        return self.depo.listele()

    def getir(self, kayit_id: uuid.UUID) -> T:
        nesne = self.depo.getir(kayit_id)
        if nesne is None:
            raise KayitBulunamadi(self.varlik)
        return nesne

    def _dogrula(self, alanlar: dict[str, Any], nesne: T | None = None) -> None:
        """Genişletme noktası: alt sınıf iş kurallarını burada denetler ve `GecersizVeri` /
        `KayitBulunamadi` fırlatır. `nesne` güncellemede var olan kayıttır, oluşturmada None."""

    def olustur(self, alanlar: dict[str, Any]) -> T:
        self._dogrula(alanlar)
        return self._kaydet(lambda: self.depo.ekle(self.depo.model(**alanlar)))

    def guncelle(self, kayit_id: uuid.UUID, degisiklikler: dict[str, Any]) -> T:
        nesne = self.getir(kayit_id)
        self._dogrula(degisiklikler, nesne)

        def uygula() -> T:
            for alan, deger in degisiklikler.items():
                setattr(nesne, alan, deger)
            self.oturum.flush()
            return nesne

        return self._kaydet(uygula)

    def sil(self, kayit_id: uuid.UUID) -> None:
        nesne = self.getir(kayit_id)
        ad = getattr(nesne, "ad", None)
        try:
            self._kaydet(lambda: self.depo.sil(nesne))
        except KayitCakismasi:
            # Yabancı anahtar: kayıt bir modülde kullanılıyor. Nerede kullanıldığını modüllere
            # sor (kanca, ADR 0014); kullanıcı ne yapacağını bilsin.
            aciklamalar = [
                metin
                for m in self.moduller
                if m.kullanim_aciklamasi
                for metin in m.kullanim_aciklamasi(self.oturum, self.depo.model.__tablename__, kayit_id)
            ]
            if not aciklamalar:
                raise
            raise KayitCakismasi(f"{ad or self.varlik} silinemez: " + " ".join(aciklamalar)) from None

    def _kaydet(self, islem):
        try:
            sonuc = islem()
            self.oturum.commit()
            return sonuc
        except IntegrityError as hata:
            self.oturum.rollback()
            durum = _sqlstate(hata)
            if durum == BENZERSIZLIK_IHLALI:
                raise KayitCakismasi(self.cakisma_mesaji) from hata
            if durum == YABANCI_ANAHTAR_IHLALI:
                raise KayitCakismasi(self.kullanimda_mesaji) from hata
            if durum == CHECK_IHLALI:
                raise GecersizVeri(f"{self.varlik}: geçersiz değer") from hata
            raise


class OgretmenServisi(CrudServisi):
    depo_sinifi = OgretmenDeposu
    varlik = "Öğretmen"


class SinifServisi(CrudServisi):
    depo_sinifi = SinifDeposu
    varlik = "Sınıf"
    cakisma_mesaji = "Bu okulda bu adla bir sınıf zaten var"


class DersServisi(CrudServisi):
    depo_sinifi = DersDeposu
    varlik = "Ders"
    cakisma_mesaji = "Bu okulda bu adla bir ders zaten var"

    def olustur(self, alanlar: dict[str, Any]):
        """Renk verilmezse okulda en az kullanılan palet rengi atanır (ders_renkleri.py)."""
        if not alanlar.get("renk"):
            alanlar = {**alanlar, "renk": siradaki_renk(d.renk for d in self.depo.listele())}
        return super().olustur(alanlar)

    def _dogrula(self, alanlar: dict[str, Any], nesne=None) -> None:
        if "renk" in alanlar and alanlar["renk"] not in RENK_KODLARI:
            raise GecersizVeri("Ders rengi paletteki renklerden biri olmalı")


class OkulServisi:
    """Okul oluşturma ve aktif okulun ayarları. Bir oturum yalnızca kendi okulunu okuyup yazar."""

    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum
        self.depo = OkulDeposu(oturum)

    def olustur(self, alanlar: dict[str, Any]) -> Okul:
        okul = Okul(id=uuid.uuid4(), **alanlar)
        # RLS: okul satırı yalnızca kendi bağlamında eklenip okunabilir (bkz. kiraci).
        veritabaninda_okulu_ayarla(self.oturum, okul.id)
        self.depo.ekle(okul)
        self.oturum.commit()
        return okul

    def getir(self, okul_id: uuid.UUID) -> Okul:
        okul = self.depo.getir(okul_id)
        if okul is None:
            raise KayitBulunamadi("Okul")
        return okul

    def ayar_etkileri(self, okul_id: uuid.UUID, gun_sayisi: int | None, gunluk_ders_saati: int | None,
                      moduller: Sequence[Modul], uygula: bool = False) -> list[str]:
        """Gün/saat ayarı değişirse modül verisine ne olur (kullanıcının diliyle). Çekirdek modül
        tablolarını bilmez; her modüle kancasıyla sorar (ADR 0014)."""
        okul = self.getir(okul_id)
        gun = gun_sayisi if gun_sayisi is not None else okul.gun_sayisi
        saat = gunluk_ders_saati if gunluk_ders_saati is not None else okul.gunluk_ders_saati
        return [e for m in moduller if m.okul_ayari_etkisi for e in m.okul_ayari_etkisi(self.oturum, gun, saat, uygula)]

    def guncelle(self, okul_id: uuid.UUID, degisiklikler: dict[str, Any], moduller: Sequence[Modul] = (),
                 etkileri_onayla: bool = False) -> Okul:
        """Etkisi olan bir gün/saat değişikliği (ör. aralık dışında kalan müsaitlik kayıtları)
        açık onay olmadan yapılmaz: `AyarEtkisiOnayGerekli` (409) etkileri listeler. Onaylanırsa
        ayar ve etkiler (modüllerin uyguladığı) tek işlemde kaydedilir."""
        okul = self.getir(okul_id)
        gun, saat = degisiklikler.get("gun_sayisi"), degisiklikler.get("gunluk_ders_saati")
        etkiler = self.ayar_etkileri(okul_id, gun, saat, moduller) if (gun or saat) else []
        if etkiler and not etkileri_onayla:
            raise AyarEtkisiOnayGerekli(etkiler)
        for alan, deger in degisiklikler.items():
            setattr(okul, alan, deger)
        if etkiler:
            self.ayar_etkileri(okul_id, gun, saat, moduller, uygula=True)
        try:
            self.oturum.commit()
        except IntegrityError as hata:
            self.oturum.rollback()
            raise GecersizVeri("Okul: geçersiz değer") from hata
        return okul
