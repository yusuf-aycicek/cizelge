"""Ders programı tabloları için satır düzeyi güvenlik (RLS).

Modül kendi tablolarının güvenliğini kendi dalında getirir; çekirdek modül tablolarını bilmez.
`depends_on = "cekirdek_0003"`: uygulama rolü ve `aktif_okul_id()` fonksiyonu çekirdekte tanımlı.
Politikalar çekirdektekiyle aynı biçimdedir (gerekçeler cekirdek_0003'te).

Revision ID: ders_programi_0003
Revises: ders_programi_0002
Create Date: 2026-10-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "ders_programi_0003"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = "cekirdek_0003"

ROL = "okul_uygulama"
OKULA_AIT = ("seviye_sablonu", "ders_atama", "musaitlik", "kisit", "program", "yerlesim")


def upgrade() -> None:
    for tablo in OKULA_AIT:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tablo} TO {ROL}")
        op.execute(f"ALTER TABLE {tablo} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tablo} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY okul_izolasyonu ON {tablo} "
                   "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")


def downgrade() -> None:
    for tablo in OKULA_AIT:
        op.execute(f"DROP POLICY okul_izolasyonu ON {tablo}")
        op.execute(f"ALTER TABLE {tablo} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tablo} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {tablo} FROM {ROL}")
