"""Çekirdek tabloları: okul, kullanici, ogretmen, sinif, ders.

`--autogenerate` ile taslak üretildi, elle gözden geçirildi:
- `id` ve `okul_id` her tabloda başa alındı (taslakta mixin sütunları sona düşmüştü).
- okul.gun_sayisi ve gunluk_ders_saati için veritabanı tarafında da varsayılan değer verildi.
Kısıt adları `ADLANDIRMA_KURALI`'ndan gelir (op.f(...): "bu adı olduğu gibi kullan").

Okula ait her tablodaki `UNIQUE (okul_id, id)`, modül tablolarının bileşik yabancı anahtarla
bağlanabilmesi içindir (docs/adr/0009). `okul_id` ile başladığı için okula göre süzülen sorgular
için indeks görevi de görür.

Revision ID: cekirdek_0002
Revises: cekirdek_0001
Create Date: 2026-10-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "cekirdek_0002"
down_revision: Union[str, Sequence[str], None] = "cekirdek_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _okula_ait_sutunlar() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
    ]


def _zaman_damgalari() -> list[sa.Column]:
    return [
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _okula_ait_kisitlar(tablo: str) -> list:
    return [
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{tablo}")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f(f"fk_{tablo}_okul_id_okul"),
                                ondelete="RESTRICT"),
        sa.UniqueConstraint("okul_id", "id", name=op.f(f"uq_{tablo}_okul_id_id")),
    ]


def upgrade() -> None:
    op.create_table(
        "okul",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("gun_sayisi", sa.Integer(), server_default="5", nullable=False),
        sa.Column("gunluk_ders_saati", sa.Integer(), server_default="8", nullable=False),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_okul")),
        sa.CheckConstraint("gun_sayisi BETWEEN 1 AND 7", name=op.f("ck_okul_gun_sayisi")),
        sa.CheckConstraint("gunluk_ders_saati BETWEEN 1 AND 16", name=op.f("ck_okul_gunluk_ders_saati")),
    )
    op.create_table(
        "kullanici",
        *_okula_ait_sutunlar(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("sifre_hash", sa.String(length=200), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        *_zaman_damgalari(),
        *_okula_ait_kisitlar("kullanici"),
        sa.UniqueConstraint("email", name=op.f("uq_kullanici_email")),
        sa.CheckConstraint("rol IN ('mudur', 'mudur_yardimcisi')", name=op.f("ck_kullanici_rol")),
    )
    op.create_table(
        "ogretmen",
        *_okula_ait_sutunlar(),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("brans", sa.String(length=100), server_default="", nullable=False),
        *_zaman_damgalari(),
        *_okula_ait_kisitlar("ogretmen"),
    )
    op.create_table(
        "sinif",
        *_okula_ait_sutunlar(),
        sa.Column("ad", sa.String(length=50), nullable=False),
        sa.Column("seviye", sa.Integer(), nullable=False),
        *_zaman_damgalari(),
        *_okula_ait_kisitlar("sinif"),
        sa.UniqueConstraint("okul_id", "ad", name=op.f("uq_sinif_okul_id_ad")),
        sa.CheckConstraint("seviye BETWEEN 1 AND 12", name=op.f("ck_sinif_seviye")),
    )
    op.create_table(
        "ders",
        *_okula_ait_sutunlar(),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("kisa_ad", sa.String(length=20), server_default="", nullable=False),
        *_zaman_damgalari(),
        *_okula_ait_kisitlar("ders"),
        sa.UniqueConstraint("okul_id", "ad", name=op.f("uq_ders_okul_id_ad")),
    )


def downgrade() -> None:
    # Ters sırada: okul tablosu, ona bağlı tablolardan sonra silinir.
    op.drop_table("ders")
    op.drop_table("sinif")
    op.drop_table("ogretmen")
    op.drop_table("kullanici")
    op.drop_table("okul")
