"""Ders programı dalının kökü (boş).

`depends_on = "cekirdek_0001"`: Alembic bu revizyondan önce çekirdeğin kökünü uygular. Modülün
tabloları (3. alt adım) çekirdek tablolarına yabancı anahtarla bağlanacağı için, o migration
da ilgili çekirdek revizyonuna `depends_on` ile bağlanacak.

Revision ID: ders_programi_0001
Revises:
Create Date: 2026-10-14
"""

from typing import Sequence, Union

revision: str = "ders_programi_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = ("ders_programi",)
depends_on: Union[str, Sequence[str], None] = ("cekirdek_0001",)


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
