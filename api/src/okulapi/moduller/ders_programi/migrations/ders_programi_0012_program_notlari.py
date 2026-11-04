"""Programın esnek kural notları: tutmayan esnek hedefler, kişi kişi (ör. boş gün hedefi).

`notlar`: `[{"tur": "bos_gun", "mesaj": "Hasan Şahin: hedef 4 boş gündü, 3 verilebildi. ...",
"ilgili": [ogretmen_id]}]`. Üretim bitince worker yazar (`cozucu.kalite.bos_gun_notlari`); notu
üretildiği anın verisiyle hesaplandığı için sonradan değişen veri onu bozmaz. Eski programlarda boş.

Revision ID: ders_programi_0012
Revises: ders_programi_0011
Create Date: 2026-11-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ders_programi_0012"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("program", sa.Column("notlar", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("program", "notlar")
