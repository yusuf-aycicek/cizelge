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
from datetime import datetime, time, timedelta

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    ForeignKey,
    Index,
    Integer,
    Interval,
    String,
    UniqueConstraint,
    column,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from okulapi.cekirdek.ders_renkleri import DERS_RENKLERI
from okulapi.cekirdek.veritabani import Base


class ZamanDamgasi:
    # timestamptz: saat dilimi bilgisiyle saklanır (sunucu ve istemci farklı dilimlerde olsa da doğru).
    olusturma: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    guncelleme: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Okul(ZamanDamgasi, Base):
    """Kök kayıt. Okul tablosunun kendisinde okul_id yoktur.

    Zaman (K3, migration cekirdek_0006):
    - `gun_saatleri`: günlere göre ders saati sayısı; boşsa her gün `gunluk_ders_saati`. Doluysa
      en az bir gün farklıdır ve `gunluk_ders_saati` en uzun gündür (servis böyle yazar, CHECK
      denetler).
    - `ogle_arasi_sonra`: öğle arası kaçıncı dersten sonra (boş = yok).
    - Zil saatleri (yalnızca gösterim): `ilk_ders_baslangic` boşsa tanımsız.
    """

    __tablename__ = "okul"
    __table_args__ = (
        CheckConstraint("gun_sayisi BETWEEN 1 AND 7", name="gun_sayisi"),
        CheckConstraint("gunluk_ders_saati BETWEEN 1 AND 16", name="gunluk_ders_saati"),
        CheckConstraint(
            "gun_saatleri IS NULL OR (cardinality(gun_saatleri) = gun_sayisi AND 1 <= ALL(gun_saatleri)"
            " AND gunluk_ders_saati >= ALL(gun_saatleri) AND gunluk_ders_saati = ANY(gun_saatleri))",
            name="gun_saatleri",
        ),
        CheckConstraint(
            "ogle_arasi_sonra IS NULL OR ogle_arasi_sonra BETWEEN 1 AND gunluk_ders_saati - 1",
            name="ogle_arasi_sonra",
        ),
        CheckConstraint("ders_suresi_dk BETWEEN 10 AND 120", name="ders_suresi_dk"),
        CheckConstraint("teneffus_dk BETWEEN 0 AND 60", name="teneffus_dk"),
        CheckConstraint("ogle_arasi_dk BETWEEN 0 AND 180", name="ogle_arasi_dk"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ad: Mapped[str] = mapped_column(String(200))
    gun_sayisi: Mapped[int] = mapped_column(default=5, server_default="5")
    gunluk_ders_saati: Mapped[int] = mapped_column(default=8, server_default="8")
    gun_saatleri: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    ogle_arasi_sonra: Mapped[int | None]
    ilk_ders_baslangic: Mapped[time | None]
    ders_suresi_dk: Mapped[int] = mapped_column(default=40, server_default="40")
    teneffus_dk: Mapped[int] = mapped_column(default=10, server_default="10")
    ogle_arasi_dk: Mapped[int] = mapped_column(default=40, server_default="40")

    @property
    def gunluk_saatler(self) -> list[int]:
        """Her gün için ders saati sayısı (günler aynıysa da tam liste)."""
        return list(self.gun_saatleri) if self.gun_saatleri else [self.gunluk_ders_saati] * self.gun_sayisi

    def aralikta(self, gun: int, saat: int) -> bool:
        """Bu hücre okulun haftasında var mı (kısa günün sonundaki saatler yoktur)."""
        return 0 <= gun < self.gun_sayisi and 0 <= saat < self.gunluk_saatler[gun]


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


class SubeGrubu(OkulaAitMixin, Base):
    """Aynı seviyedeki şubelerin bir grubu, ör. "11 Sayısal" (K5, migration cekirdek_0007).

    Grubun şubeleri seviye şablonu yerine grubun şablonunu kullanabilir; kurallar gruba özel
    ayarlanabilir (ADR 0016). Grup silinince şubeleri grupsuz kalır (`SET NULL`).
    """

    __tablename__ = "sube_grubu"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "ad"),
        CheckConstraint("seviye BETWEEN 1 AND 12", name="seviye"),
    )

    ad: Mapped[str] = mapped_column(String(100))
    seviye: Mapped[int]


class Sinif(OkulaAitMixin, Base):
    """Şube, ör. 9-A. `sube_grubu_id`: şubenin grubu (boş = grupsuz); grubun seviyesi şubeninkiyle
    aynıdır (servis denetler)."""

    __tablename__ = "sinif"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "ad"),
        CheckConstraint("seviye BETWEEN 1 AND 12", name="seviye"),
        # Bileşik FK: grup aynı okulda olmalı. Grup silinince yalnızca grup sütunu boşalır
        # (PostgreSQL 15+ sütun listeli SET NULL; okul_id'ye dokunmaz).
        ForeignKeyConstraint(["okul_id", "sube_grubu_id"], ["sube_grubu.okul_id", "sube_grubu.id"],
                             ondelete="SET NULL (sube_grubu_id)"),
        Index(None, "okul_id", "sube_grubu_id"),
    )

    ad: Mapped[str] = mapped_column(String(50))
    seviye: Mapped[int]
    sube_grubu_id: Mapped[uuid.UUID | None]


class Ders(OkulaAitMixin, Base):
    __tablename__ = "ders"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "ad"),
        CheckConstraint("renk ~ '^#[0-9a-f]{6}$'", name="renk_bicimi"),
    )

    ad: Mapped[str] = mapped_column(String(200))
    kisa_ad: Mapped[str] = mapped_column(String(20), default="", server_default="")
    # Çipin rengi, #rrggbb. Yalnızca paletten (cekirdek/ders_renkleri.py); servis okulda en az
    # kullanılanı atar ve denetler. Varsayılan, servisi atlayan ORM yolları (ör. testler) içindir.
    renk: Mapped[str] = mapped_column(String(7), default=DERS_RENKLERI[0][0])


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
