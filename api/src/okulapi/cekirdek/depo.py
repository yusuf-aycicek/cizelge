"""Depo (repository) katmanı: veri erişimi.

Depolar SQL'i ve sorguları bilir, HTTP'yi ve iş kurallarını bilmez. Okul filtresi depoda elle
yazılmaz; oturum düzeyinde otomatik uygulanır (`okulapi.cekirdek.kiraci`). Bu yüzden
`OkulaAitDepo` her model için aynıdır ve modüller de kendi modelleri için bunu kullanır.
"""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from okulapi.cekirdek.modeller import Ders, Okul, OkulaAitMixin, Ogretmen, Sinif

T = TypeVar("T", bound=OkulaAitMixin)


class OkulaAitDepo(Generic[T]):
    model: type[T]

    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum

    def listele(self) -> list[T]:
        return list(self.oturum.scalars(select(self.model).order_by(self.model.olusturma, self.model.id)))

    def getir(self, kayit_id: uuid.UUID) -> T | None:
        # Başka okulun kaydı otomatik filtre yüzünden bulunamaz: sonuç None olur.
        return self.oturum.get(self.model, kayit_id)

    def ekle(self, nesne: T) -> T:
        self.oturum.add(nesne)
        self.oturum.flush()  # veritabanı kısıtları burada (commit'ten önce) denetlenir
        return nesne

    def sil(self, nesne: T) -> None:
        self.oturum.delete(nesne)
        self.oturum.flush()


class OgretmenDeposu(OkulaAitDepo[Ogretmen]):
    model = Ogretmen


class SinifDeposu(OkulaAitDepo[Sinif]):
    model = Sinif


class DersDeposu(OkulaAitDepo[Ders]):
    model = Ders


class OkulDeposu:
    """Okul kök kayıttır, okul filtresine tabi değildir. Erişim servis katmanında denetlenir."""

    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum

    def getir(self, okul_id: uuid.UUID) -> Okul | None:
        return self.oturum.get(Okul, okul_id)

    def ekle(self, okul: Okul) -> Okul:
        self.oturum.add(okul)
        self.oturum.flush()
        return okul
