"""Çekirdek dalının kökü (boş).

Bütün modül dallarının ilk revizyonu buna `depends_on` ile bağlanır. Çekirdek tabloları
2. alt adımda bunun üzerine eklenecek.

Revision ID: cekirdek_0001
Revises:
Create Date: 2026-10-14
"""

from typing import Sequence, Union

revision: str = "cekirdek_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = ("cekirdek",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
