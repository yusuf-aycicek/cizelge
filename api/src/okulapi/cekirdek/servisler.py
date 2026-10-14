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
from typing import Any, Generic, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulaAitDepo, OkulDeposu, SinifDeposu
from okulapi.cekirdek.modeller import Okul, OkulaAitMixin

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


def _sqlstate(hata: IntegrityError) -> str | None:
    return getattr(hata.orig, "sqlstate", None)


class CrudServisi(Generic[T]):
    """Okula ait bir varlık için temel CRUD. Alt sınıf depoyu ve mesajları verir."""

    depo_sinifi: type[OkulaAitDepo[T]]
    varlik: str  # mesajlarda: "Öğretmen"
    cakisma_mesaji: str = "Bu kayıt zaten var"
    kullanimda_mesaji: str = "Bu kayıt başka kayıtlar tarafından kullanılıyor, silinemez"

    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum
        self.depo = self.depo_sinifi(oturum)

    def listele(self) -> list[T]:
        return self.depo.listele()

    def getir(self, kayit_id: uuid.UUID) -> T:
        nesne = self.depo.getir(kayit_id)
        if nesne is None:
            raise KayitBulunamadi(self.varlik)
        return nesne

    def olustur(self, alanlar: dict[str, Any]) -> T:
        return self._kaydet(lambda: self.depo.ekle(self.depo.model(**alanlar)))

    def guncelle(self, kayit_id: uuid.UUID, degisiklikler: dict[str, Any]) -> T:
        nesne = self.getir(kayit_id)

        def uygula() -> T:
            for alan, deger in degisiklikler.items():
                setattr(nesne, alan, deger)
            self.oturum.flush()
            return nesne

        return self._kaydet(uygula)

    def sil(self, kayit_id: uuid.UUID) -> None:
        nesne = self.getir(kayit_id)
        self._kaydet(lambda: self.depo.sil(nesne))

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


class OkulServisi:
    """Okul oluşturma ve aktif okulun ayarları. Bir oturum yalnızca kendi okulunu okuyup yazar."""

    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum
        self.depo = OkulDeposu(oturum)

    def olustur(self, alanlar: dict[str, Any]) -> Okul:
        okul = self.depo.ekle(Okul(**alanlar))
        self.oturum.commit()
        return okul

    def getir(self, okul_id: uuid.UUID) -> Okul:
        okul = self.depo.getir(okul_id)
        if okul is None:
            raise KayitBulunamadi("Okul")
        return okul

    def guncelle(self, okul_id: uuid.UUID, degisiklikler: dict[str, Any]) -> Okul:
        okul = self.getir(okul_id)
        for alan, deger in degisiklikler.items():
            setattr(okul, alan, deger)
        try:
            self.oturum.commit()
        except IntegrityError as hata:
            self.oturum.rollback()
            raise GecersizVeri("Okul: geçersiz değer") from hata
        return okul
