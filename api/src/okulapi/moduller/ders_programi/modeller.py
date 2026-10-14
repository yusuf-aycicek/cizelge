"""Ders programı modülünün tabloları.

Bütün ilişkiler **bileşik yabancı anahtardır**: `(okul_id, x_id) -> x(okul_id, id)`. Bir satır
yalnızca **aynı okuldaki** bir satırı gösterebilir. A okulunun ders ataması B okulunun öğretmenine
bağlanmak istenirse veritabanı bunu reddeder, uygulamada bir hata olsa bile (docs/adr/0009).
Hedef tablolardaki `UNIQUE (okul_id, id)` kısıtı (`OkulaAitMixin`) bunun için vardır.

Silme davranışları (ON DELETE) ve gerekçeleri:
- çekirdek kaydı (sınıf, ders, öğretmen) bir atamada kullanılıyorsa silinemez (RESTRICT): veri
  sessizce kaybolmasın, kullanıcı önce atamayı değiştirsin;
- öğretmen silinince müsaitlik kayıtları da silinir (CASCADE): müsaitlik öğretmenin parçasıdır;
  çekirdek bu tabloyu bilmeden silme işini veritabanı yapar (modüler yapıya uygun);
- program silinince yerleşimleri silinir (CASCADE); ders ataması silinince eski programlardaki
  yerleşimleri de silinir (CASCADE). RESTRICT olsaydı bir kez program üretilen bir atama bir daha
  silinemezdi. Eski program bu durumda eksik kalır; en az değişiklikle güncellemede bu, "kaldırılmış
  ders" olarak zaten doğru işlenir (çözücü ADR 0006);
- temel programı silinen programın `temel_program_id`'si boşalır: PostgreSQL 15+ ile gelen
  `ON DELETE SET NULL (temel_program_id)` yalnızca bu sütunu boşaltır, `okul_id`'ye dokunmaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from okulapi.cekirdek.modeller import OkulaAitMixin
from okulapi.cekirdek.veritabani import Base


def okul_ici_fk(sutun: str, hedef: str, ondelete: str = "RESTRICT") -> ForeignKeyConstraint:
    """`(okul_id, <sutun>) -> <hedef>(okul_id, id)`: yalnızca aynı okuldaki satırı gösterebilir."""
    return ForeignKeyConstraint(["okul_id", sutun], [f"{hedef}.okul_id", f"{hedef}.id"], ondelete=ondelete)


class SeviyeSablonu(OkulaAitMixin, Base):
    """Bir seviyenin (ör. 9. sınıflar) ders listesi ve haftalık saatleri."""

    __tablename__ = "seviye_sablonu"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "seviye", "ders_id"),
        okul_ici_fk("ders_id", "ders"),
        CheckConstraint("seviye BETWEEN 1 AND 12", name="seviye"),
        CheckConstraint("haftalik_saat >= 1", name="haftalik_saat"),
    )

    seviye: Mapped[int]
    ders_id: Mapped[uuid.UUID]
    haftalik_saat: Mapped[int]


class DersAtama(OkulaAitMixin, Base):
    """Bir sınıfa bir dersin haftada kaç saat, hangi öğretmenle verileceği. Çözücünün asıl girdisi.

    "Bir sınıf, bir ders, bir öğretmen" (CLAUDE.md bölüm 3): her (sınıf, ders) için tek atama.
    `ogretmen_id` boş olabilir: bileşik yabancı anahtar varsayılan olarak MATCH SIMPLE'dır, yani
    sütunlardan biri NULL ise denetlenmez. Öğretmen seçilince denetim kendiliğinden başlar.
    """

    __tablename__ = "ders_atama"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "sinif_id", "ders_id"),
        okul_ici_fk("sinif_id", "sinif"),
        okul_ici_fk("ders_id", "ders"),
        okul_ici_fk("ogretmen_id", "ogretmen"),
        CheckConstraint("haftalik_saat >= 1", name="haftalik_saat"),
        # PostgreSQL yabancı anahtarın *gösteren* tarafına kendiliğinden indeks koymaz. Öğretmen
        # silinirken (RESTRICT denetimi) ve "bu öğretmenin atamaları" sorgusunda kullanılır.
        Index(None, "okul_id", "ogretmen_id"),
    )

    sinif_id: Mapped[uuid.UUID]
    ders_id: Mapped[uuid.UUID]
    ogretmen_id: Mapped[uuid.UUID | None]
    haftalik_saat: Mapped[int]


class Musaitlik(OkulaAitMixin, Base):
    __tablename__ = "musaitlik"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "ogretmen_id", "gun", "saat"),
        okul_ici_fk("ogretmen_id", "ogretmen", ondelete="CASCADE"),
        CheckConstraint("durum IN ('gelemez', 'tercih_etmez')", name="durum"),
        CheckConstraint("gun BETWEEN 0 AND 6", name="gun"),
        CheckConstraint("saat BETWEEN 0 AND 15", name="saat"),
    )

    ogretmen_id: Mapped[uuid.UUID]
    gun: Mapped[int]  # 0 = pazartesi
    saat: Mapped[int]  # 0 = ilk ders
    durum: Mapped[str] = mapped_column(String(20))


class Kisit(OkulaAitMixin, Base):
    """Okul geneli kural. `tur` çözücünün kural kayıt defterindeki adlardan biridir."""

    __tablename__ = "kisit"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "tur"),
        CheckConstraint("agirlik >= 0", name="agirlik"),
    )

    tur: Mapped[str] = mapped_column(String(50))
    # JSONB: esnek yapılı ama sorgulanabilir ve indekslenebilir JSON (ör. {"n": 2}).
    parametreler: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    zorunlu: Mapped[bool]
    agirlik: Mapped[int] = mapped_column(default=1, server_default="1")


class Program(OkulaAitMixin, Base):
    """Bir program üretme denemesi. Yazan taraf: worker (yapım sırası 3)."""

    __tablename__ = "program"
    _tablo_kisitlari = (
        okul_ici_fk("temel_program_id", "program", ondelete="SET NULL (temel_program_id)"),
        CheckConstraint("durum IN ('bekliyor', 'uretiliyor', 'hazir', 'basarisiz')", name="durum"),
        CheckConstraint("sure_siniri_sn > 0", name="sure_siniri_sn"),
    )

    ad: Mapped[str] = mapped_column(String(200))
    durum: Mapped[str] = mapped_column(String(20), default="bekliyor", server_default="bekliyor")
    hata_mesaji: Mapped[str | None] = mapped_column(Text)
    temel_program_id: Mapped[uuid.UUID | None]
    sure_siniri_sn: Mapped[int] = mapped_column(default=120, server_default="120")
    bitis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Yerlesim(OkulaAitMixin, Base):
    """Programın bir hücresi: bu atama bu gün bu saatte."""

    __tablename__ = "yerlesim"
    _tablo_kisitlari = (
        UniqueConstraint("program_id", "ders_atama_id", "gun", "saat"),
        okul_ici_fk("program_id", "program", ondelete="CASCADE"),
        okul_ici_fk("ders_atama_id", "ders_atama", ondelete="CASCADE"),
        CheckConstraint("gun BETWEEN 0 AND 6", name="gun"),
        CheckConstraint("saat BETWEEN 0 AND 15", name="saat"),
        Index(None, "okul_id", "ders_atama_id"),  # atama silinirken CASCADE araması için
    )

    program_id: Mapped[uuid.UUID]
    ders_atama_id: Mapped[uuid.UUID]
    gun: Mapped[int]
    saat: Mapped[int]
    kilitli: Mapped[bool] = mapped_column(default=False, server_default="false")
