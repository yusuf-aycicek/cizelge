"""Elle düzeltme işlemleri (7.1): `program_islemi`, geri alma için.

Her taşıma ve kilit değişikliği bir satır; geri alma en büyük `sira`yı tersine çevirir.
`(okul_id, program_id) -> program` bileşik FK (başka okulun programına işlem yazılamaz) ve
CASCADE; RLS öteki okula ait tablolarla aynı (ders_programi_0003).

Revision ID: ders_programi_0009
Revises: ders_programi_0008
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ders_programi_0009"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROL = "okul_uygulama"


def upgrade() -> None:
    op.create_table(
        "program_islemi",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("sira", sa.Integer(), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("veri", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_islemi")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f("fk_program_islemi_okul_id_okul"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["okul_id", "program_id"], ["program.okul_id", "program.id"],
                                name=op.f("fk_program_islemi_okul_id_program_id_program"), ondelete="CASCADE"),
        sa.CheckConstraint("tur IN ('tasima', 'kilit')", name=op.f("ck_program_islemi_tur")),
        sa.CheckConstraint("sira > 0", name=op.f("ck_program_islemi_sira")),
        sa.UniqueConstraint("okul_id", "id", name=op.f("uq_program_islemi_okul_id_id")),
        sa.UniqueConstraint("program_id", "sira", name=op.f("uq_program_islemi_program_id_sira")),
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON program_islemi TO {ROL}")
    op.execute("ALTER TABLE program_islemi ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE program_islemi FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON program_islemi "
               "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")


def downgrade() -> None:
    op.drop_table("program_islemi")
