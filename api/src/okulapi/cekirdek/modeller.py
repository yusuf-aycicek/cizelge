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
from datetime import datetime, timedelta

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    ForeignKey,
    Index,
    Interval,
    String,
    UniqueConstraint,
    column,
    func,
)
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
    """Yönetici hesabı (müdür ya da müdür yardımcısı). Giriş: okulapi.cekirdek.kimlik, ADR 0012.

    E-posta **bütün sistemde** tektir ve büyük/küçük harf ayrımı yapılmaz: giriş okul bilinmeden,
    yalnızca e-postayla yapılır. Saklanan e-posta küçük harftir (CHECK) ve benzersizlik
    `lower(email)` üzerindedir (CHECK kaldırılsa bile "Ayse@" ile "ayse@" iki hesap olamasın).
    """

    __tablename__ = "kullanici"
    _tablo_kisitlari = (
        Index("uq_kullanici_email_kucuk", func.lower(column("email")), unique=True),
        CheckConstraint("email = lower(email)", name="email_kucuk_harf"),
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


class Oturum(OkulaAitMixin, Base):
    """Giriş yapmış bir kullanıcının oturumu (ADR 0012).

    Tarayıcıdaki çerezde rastgele bir jeton durur; burada yalnızca onun SHA-256 özeti saklanır.
    Veritabanı sızsa bile özetten jeton elde edilemez, yani oturumlar çalınamaz.

    Geçerlilik: `son_kullanim + hareketsizlik_siniri > now()` ve `bitis_mutlak > now()`. İstek
    gelirken okul henüz bilinmez: oturum `oturum_coz()` veritabanı fonksiyonuyla çözülür
    (migration cekirdek_0004).
    """

    __tablename__ = "oturum"
    _tablo_kisitlari = (
        ForeignKeyConstraint(["okul_id", "kullanici_id"], ["kullanici.okul_id", "kullanici.id"], ondelete="CASCADE"),
        UniqueConstraint("jeton_ozeti"),
        Index(None, "okul_id", "kullanici_id"),
    )

    kullanici_id: Mapped[uuid.UUID]
    jeton_ozeti: Mapped[str] = mapped_column(String(64))
    son_kullanim: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hareketsizlik_siniri: Mapped[timedelta] = mapped_column(Interval)
    bitis_mutlak: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GirisDenemesi(Base):
    """Kaba kuvvet sayacı: e-posta başına hatalı giriş denemeleri (ADR 0012).

    **Okula ait değildir** (giriş okul bilinmeden yapılır) ve uygulama rolünün bu tabloya hiçbir
    yetkisi yoktur. Uygulama yalnızca `okul_giris` rolünün fonksiyonlarını çağırır
    (`giris_kilitli_mi`, `giris_hatasi_kaydet`, `giris_denemelerini_sil`). Model, şemanın kodda
    da belgelenmesi ve migration tutarlılık testi için vardır; uygulama kodu bu sınıfı kullanmaz.

    Kayıtlı olmayan e-postalar da sayılır: kilitlenme, e-postanın kayıtlı olup olmadığını söylemez.
    """

    __tablename__ = "giris_denemesi"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    hata_sayisi: Mapped[int]
    pencere_basi: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kilit_bitis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
