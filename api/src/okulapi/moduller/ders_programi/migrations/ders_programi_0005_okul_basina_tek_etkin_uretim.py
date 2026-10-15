"""Okul başına en fazla bir etkin (bekliyor/uretiliyor) üretim: kısmi benzersiz indeks.

Uygulama yeni üretimden önce "etkin üretim var mı" diye bakar (409). Aynı anda gelen iki istek bu
denetimi birlikte geçebilir; bu indeks ikincisini veritabanında durdurur (ADR 0011 madde 7).

Revision ID: ders_programi_0005
Revises: ders_programi_0004
Create Date: 2026-10-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ders_programi_0005"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("uq_program_okul_id_etkin", "program", ["okul_id"], unique=True,
                    postgresql_where=sa.text("durum IN ('bekliyor', 'uretiliyor')"))


def downgrade() -> None:
    op.drop_index("uq_program_okul_id_etkin", table_name="program")
