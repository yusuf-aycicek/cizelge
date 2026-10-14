"""Ders programı tabloları: seviye_sablonu, ders_atama, musaitlik, kisit, program, yerlesim.

`depends_on = "cekirdek_0002"`: bu tablolar çekirdeğin ogretmen, sinif, ders tablolarına yabancı
anahtarla bağlanır; Alembic önce çekirdeğin o revizyonunu uygular (docs/adr/0010).

`--autogenerate` ile taslak üretildi, elle gözden geçirildi: sütun sırası (id, okul_id başta),
açıklamalar. Bütün ilişkiler bileşik yabancı anahtardır: `(okul_id, x_id) -> x(okul_id, id)`.
Silme davranışlarının gerekçeleri modeller.py'de.

Revision ID: ders_programi_0002
Revises: ders_programi_0001
Create Date: 2026-10-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ders_programi_0002"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = "cekirdek_0002"


def _ortak_sutunlar() -> list[sa.Column]:
    return [sa.Column("id", sa.Uuid(), nullable=False), sa.Column("okul_id", sa.Uuid(), nullable=False)]


def _zaman_damgalari() -> list[sa.Column]:
    return [
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _ortak_kisitlar(tablo: str) -> list:
    return [
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{tablo}")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f(f"fk_{tablo}_okul_id_okul"), ondelete="RESTRICT"),
        sa.UniqueConstraint("okul_id", "id", name=op.f(f"uq_{tablo}_okul_id_id")),
    ]


def _okul_ici_fk(tablo: str, sutun: str, hedef: str, ondelete: str = "RESTRICT") -> sa.ForeignKeyConstraint:
    """(okul_id, sutun) -> hedef(okul_id, id): yalnızca aynı okuldaki satırı gösterebilir."""
    return sa.ForeignKeyConstraint(
        ["okul_id", sutun], [f"{hedef}.okul_id", f"{hedef}.id"],
        name=op.f(f"fk_{tablo}_okul_id_{sutun}_{hedef}"), ondelete=ondelete,
    )


def upgrade() -> None:
    op.create_table(
        "seviye_sablonu",
        *_ortak_sutunlar(),
        sa.Column("seviye", sa.Integer(), nullable=False),
        sa.Column("ders_id", sa.Uuid(), nullable=False),
        sa.Column("haftalik_saat", sa.Integer(), nullable=False),
        *_zaman_damgalari(),
        *_ortak_kisitlar("seviye_sablonu"),
        _okul_ici_fk("seviye_sablonu", "ders_id", "ders"),
        sa.UniqueConstraint("okul_id", "seviye", "ders_id", name=op.f("uq_seviye_sablonu_okul_id_seviye_ders_id")),
        sa.CheckConstraint("seviye BETWEEN 1 AND 12", name=op.f("ck_seviye_sablonu_seviye")),
        sa.CheckConstraint("haftalik_saat >= 1", name=op.f("ck_seviye_sablonu_haftalik_saat")),
    )
    op.create_table(
        "ders_atama",
        *_ortak_sutunlar(),
        sa.Column("sinif_id", sa.Uuid(), nullable=False),
        sa.Column("ders_id", sa.Uuid(), nullable=False),
        sa.Column("ogretmen_id", sa.Uuid(), nullable=True),  # boş: henüz öğretmen seçilmemiş
        sa.Column("haftalik_saat", sa.Integer(), nullable=False),
        *_zaman_damgalari(),
        *_ortak_kisitlar("ders_atama"),
        _okul_ici_fk("ders_atama", "sinif_id", "sinif"),
        _okul_ici_fk("ders_atama", "ders_id", "ders"),
        # MATCH SIMPLE (varsayılan): ogretmen_id NULL iken bu anahtar denetlenmez.
        _okul_ici_fk("ders_atama", "ogretmen_id", "ogretmen"),
        # Bir sınıf, bir ders, bir öğretmen: her (sınıf, ders) için tek atama.
        sa.UniqueConstraint("okul_id", "sinif_id", "ders_id", name=op.f("uq_ders_atama_okul_id_sinif_id_ders_id")),
        sa.CheckConstraint("haftalik_saat >= 1", name=op.f("ck_ders_atama_haftalik_saat")),
    )
    # Yabancı anahtarın gösteren tarafına PostgreSQL kendiliğinden indeks koymaz.
    op.create_index(op.f("ix_ders_atama_okul_id_ogretmen_id"), "ders_atama", ["okul_id", "ogretmen_id"])
    op.create_table(
        "musaitlik",
        *_ortak_sutunlar(),
        sa.Column("ogretmen_id", sa.Uuid(), nullable=False),
        sa.Column("gun", sa.Integer(), nullable=False),
        sa.Column("saat", sa.Integer(), nullable=False),
        sa.Column("durum", sa.String(length=20), nullable=False),
        *_zaman_damgalari(),
        *_ortak_kisitlar("musaitlik"),
        _okul_ici_fk("musaitlik", "ogretmen_id", "ogretmen", ondelete="CASCADE"),
        sa.UniqueConstraint("okul_id", "ogretmen_id", "gun", "saat",
                            name=op.f("uq_musaitlik_okul_id_ogretmen_id_gun_saat")),
        sa.CheckConstraint("durum IN ('gelemez', 'tercih_etmez')", name=op.f("ck_musaitlik_durum")),
        sa.CheckConstraint("gun BETWEEN 0 AND 6", name=op.f("ck_musaitlik_gun")),
        sa.CheckConstraint("saat BETWEEN 0 AND 15", name=op.f("ck_musaitlik_saat")),
    )
    op.create_table(
        "kisit",
        *_ortak_sutunlar(),
        sa.Column("tur", sa.String(length=50), nullable=False),
        sa.Column("parametreler", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("zorunlu", sa.Boolean(), nullable=False),
        sa.Column("agirlik", sa.Integer(), server_default="1", nullable=False),
        *_zaman_damgalari(),
        *_ortak_kisitlar("kisit"),
        sa.UniqueConstraint("okul_id", "tur", name=op.f("uq_kisit_okul_id_tur")),
        sa.CheckConstraint("agirlik >= 0", name=op.f("ck_kisit_agirlik")),
    )
    op.create_table(
        "program",
        *_ortak_sutunlar(),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("durum", sa.String(length=20), server_default="bekliyor", nullable=False),
        sa.Column("hata_mesaji", sa.Text(), nullable=True),
        sa.Column("temel_program_id", sa.Uuid(), nullable=True),
        sa.Column("sure_siniri_sn", sa.Integer(), server_default="120", nullable=False),
        sa.Column("bitis", sa.DateTime(timezone=True), nullable=True),
        *_zaman_damgalari(),
        *_ortak_kisitlar("program"),
        # Kendine bileşik yabancı anahtar. Temel program silinince yalnızca temel_program_id
        # boşalır (PostgreSQL 15+ sözdizimi), okul_id'ye dokunulmaz.
        _okul_ici_fk("program", "temel_program_id", "program", ondelete="SET NULL (temel_program_id)"),
        sa.CheckConstraint("durum IN ('bekliyor', 'uretiliyor', 'hazir', 'basarisiz')", name=op.f("ck_program_durum")),
        sa.CheckConstraint("sure_siniri_sn > 0", name=op.f("ck_program_sure_siniri_sn")),
    )
    op.create_table(
        "yerlesim",
        *_ortak_sutunlar(),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("ders_atama_id", sa.Uuid(), nullable=False),
        sa.Column("gun", sa.Integer(), nullable=False),
        sa.Column("saat", sa.Integer(), nullable=False),
        sa.Column("kilitli", sa.Boolean(), server_default="false", nullable=False),
        *_zaman_damgalari(),
        *_ortak_kisitlar("yerlesim"),
        _okul_ici_fk("yerlesim", "program_id", "program", ondelete="CASCADE"),
        _okul_ici_fk("yerlesim", "ders_atama_id", "ders_atama", ondelete="CASCADE"),
        sa.UniqueConstraint("program_id", "ders_atama_id", "gun", "saat",
                            name=op.f("uq_yerlesim_program_id_ders_atama_id_gun_saat")),
        sa.CheckConstraint("gun BETWEEN 0 AND 6", name=op.f("ck_yerlesim_gun")),
        sa.CheckConstraint("saat BETWEEN 0 AND 15", name=op.f("ck_yerlesim_saat")),
    )
    op.create_index(op.f("ix_yerlesim_okul_id_ders_atama_id"), "yerlesim", ["okul_id", "ders_atama_id"])


def downgrade() -> None:
    # Ters sırada: başka tabloların gösterdiği tablolar en son silinir.
    op.drop_index(op.f("ix_yerlesim_okul_id_ders_atama_id"), table_name="yerlesim")
    op.drop_table("yerlesim")
    op.drop_table("program")
    op.drop_table("kisit")
    op.drop_table("musaitlik")
    op.drop_index(op.f("ix_ders_atama_okul_id_ogretmen_id"), table_name="ders_atama")
    op.drop_table("ders_atama")
    op.drop_table("seviye_sablonu")
