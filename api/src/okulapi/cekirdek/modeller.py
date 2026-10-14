"""Çekirdek modelleri: okul (kök kayıt) ve okula ait temel varlıklar.

Okula ait her model `OkulaAitMixin`'den türer. Bu mixin şunları sağlar:
- `id` (uuid) ve `okul_id` (okul tablosuna yabancı anahtar),
- `UNIQUE (okul_id, id)`: diğer tablolar bu varlığa **bileşik yabancı anahtarla**
  `(okul_id, x_id) -> x(okul_id, id)` bağlanabilir. Böylece veritabanı bir okulun kaydının başka
  bir okulun kaydını göstermesini kendisi reddeder (bkz. docs/adr/0009),
- otomatik okul filtresi (`okulapi.cekirdek.kiraci`) bu mixin'i taşıyan bütün modellere uygulanır.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from okulapi.cekirdek.veritabani import Base


class ZamanDamgasi:
    # timestamptz: saat dilimi bilgisiyle saklanır (sunucu ve istemci farklı dilimlerde olsa da doğru).
    olusturma: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    guncelleme: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Okul(ZamanDamgasi, Base):
    """Kök kayıt. Okul tablosunun kendisinde okul_id yoktur."""

    __tablename__ = "okul"
    __table_args__ = (
        CheckConstraint("gun_sayisi BETWEEN 1 AND 7", name="gun_sayisi"),
        CheckConstraint("gunluk_ders_saati BETWEEN 1 AND 16", name="gunluk_ders_saati"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ad: Mapped[str] = mapped_column(String(200))
    gun_sayisi: Mapped[int] = mapped_column(default=5, server_default="5")
    gunluk_ders_saati: Mapped[int] = mapped_column(default=8, server_default="8")


class OkulaAitMixin(ZamanDamgasi):
    """Okula ait her tablonun ortak sütunları ve kısıtları.

    Alt sınıf kendi tablo kısıtlarını `_tablo_kisitlari` ile verir; mixin bunları
    `UNIQUE (okul_id, id)` ile birleştirir.
    """

    _tablo_kisitlari: tuple = ()

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    @declared_attr
    def okul_id(cls) -> Mapped[uuid.UUID]:
        # RESTRICT: okulun kaydı varken okul silinemez (verinin sessizce kaybolmasını önler).
        return mapped_column(ForeignKey("okul.id", ondelete="RESTRICT"))

    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        return (UniqueConstraint("okul_id", "id"), *cls._tablo_kisitlari)


class Kullanici(OkulaAitMixin, Base):
    """Yönetici hesabı. Endpoint'leri ve giriş yapım sırası 4'te (kimlik doğrulama)."""

    __tablename__ = "kullanici"
    _tablo_kisitlari = (
        UniqueConstraint("email"),  # e-posta bütün sistemde tektir (giriş okul seçmeden yapılır)
        CheckConstraint("rol IN ('mudur', 'mudur_yardimcisi')", name="rol"),
    )

    email: Mapped[str] = mapped_column(String(320))
    sifre_hash: Mapped[str] = mapped_column(String(200))
    ad: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(30))


class Ogretmen(OkulaAitMixin, Base):
    __tablename__ = "ogretmen"

    ad: Mapped[str] = mapped_column(String(200))
    brans: Mapped[str] = mapped_column(String(100), default="", server_default="")


class Sinif(OkulaAitMixin, Base):
    """Şube, ör. 9-A."""

    __tablename__ = "sinif"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "ad"),
        CheckConstraint("seviye BETWEEN 1 AND 12", name="seviye"),
    )

    ad: Mapped[str] = mapped_column(String(50))
    seviye: Mapped[int]


class Ders(OkulaAitMixin, Base):
    __tablename__ = "ders"
    _tablo_kisitlari = (UniqueConstraint("okul_id", "ad"),)

    ad: Mapped[str] = mapped_column(String(200))
    kisa_ad: Mapped[str] = mapped_column(String(20), default="", server_default="")
