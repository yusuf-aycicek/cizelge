"""Yayın (8b, ADR 0022): okulun yayınlanan programının dondurulmuş içeriği.

Okul başına tek satır (`UNIQUE (okul_id)`). Program silinince yayın kalır: bileşik FK yalnızca
`program_id`'yi boşaltır (PostgreSQL 15+ sütun listeli SET NULL). İçerik atamalara bağlı değildir:
atama silinince yayın eksilmez. RLS öteki okula ait tablolarla aynı.

Revision ID: ders_programi_0010
Revises: ders_programi_0009
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ders_programi_0010"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROL = "okul_uygulama"


def upgrade() -> None:
    op.create_table(
        "yayin",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=True),
        sa.Column("program_adi", sa.String(length=200), nullable=False),
        sa.Column("yayin_zamani", sa.DateTime(timezone=True), nullable=False),
        sa.Column("icerik", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("veri_ozeti", sa.String(length=64), nullable=True),
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_yayin")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f("fk_yayin_okul_id_okul"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["okul_id", "program_id"], ["program.okul_id", "program.id"],
                                name=op.f("fk_yayin_okul_id_program_id_program"), ondelete="SET NULL (program_id)"),
        sa.UniqueConstraint("okul_id", "id", name=op.f("uq_yayin_okul_id_id")),
        sa.UniqueConstraint("okul_id", name=op.f("uq_yayin_okul_id")),
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON yayin TO {ROL}")
    op.execute("ALTER TABLE yayin ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE yayin FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON yayin "
               "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")


def downgrade() -> None:
    op.drop_table("yayin")
