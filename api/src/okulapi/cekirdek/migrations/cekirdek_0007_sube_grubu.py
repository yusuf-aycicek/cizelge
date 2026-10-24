"""Şube grupları (K5): "11 Sayısal", "11 Sözel" gibi aynı seviyedeki şubelerin grupları.

- `sube_grubu` (ad, seviye): okula ait, `UNIQUE (okul_id, ad)`; RLS politikası çekirdekteki
  kalıpla (cekirdek_0003).
- `sinif.sube_grubu_id`: boş olabilir. Bileşik FK, `ON DELETE SET NULL (sube_grubu_id)`: grup
  silinince şubeler grupsuz kalır, `okul_id` sütununa dokunulmaz (PostgreSQL 15+).

Var olan şubeler grupsuz kalır: davranış değişmez, veri taşıması gerekmez.

Revision ID: cekirdek_0007
Revises: cekirdek_0006
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "cekirdek_0007"
down_revision: Union[str, Sequence[str], None] = "cekirdek_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROL = "okul_uygulama"


def upgrade() -> None:
    op.create_table(
        "sube_grubu",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
        sa.Column("ad", sa.String(length=100), nullable=False),
        sa.Column("seviye", sa.Integer(), nullable=False),
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sube_grubu")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f("fk_sube_grubu_okul_id_okul"), ondelete="RESTRICT"),
        sa.UniqueConstraint("okul_id", "id", name=op.f("uq_sube_grubu_okul_id_id")),
        sa.UniqueConstraint("okul_id", "ad", name=op.f("uq_sube_grubu_okul_id_ad")),
        sa.CheckConstraint("seviye BETWEEN 1 AND 12", name=op.f("ck_sube_grubu_seviye")),
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON sube_grubu TO {ROL}")
    op.execute("ALTER TABLE sube_grubu ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sube_grubu FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON sube_grubu "
               "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")

    op.add_column("sinif", sa.Column("sube_grubu_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_sinif_okul_id_sube_grubu_id_sube_grubu"), "sinif", "sube_grubu",
        ["okul_id", "sube_grubu_id"], ["okul_id", "id"], ondelete="SET NULL (sube_grubu_id)",
    )
    op.create_index(op.f("ix_sinif_okul_id_sube_grubu_id"), "sinif", ["okul_id", "sube_grubu_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sinif_okul_id_sube_grubu_id"), table_name="sinif")
    op.drop_constraint(op.f("fk_sinif_okul_id_sube_grubu_id_sube_grubu"), "sinif", type_="foreignkey")
    op.drop_column("sinif", "sube_grubu_id")
    op.execute("DROP POLICY okul_izolasyonu ON sube_grubu")
    op.drop_table("sube_grubu")
