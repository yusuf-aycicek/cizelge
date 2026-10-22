"""Ders rengi: `ders.renk` (#rrggbb), paletten (cekirdek/ders_renkleri.py).

Var olan derslere her okulda ada göre sırayla palet renkleri verilir; sonra sütun NOT NULL olur ve
biçimi CHECK ile denetlenir. Paletin üyeliğini servis denetler: palet bir migration gerektirmeden
değişebilsin.

Palet burada kopyalanır, içe aktarılmaz: migration geçmişi uygulamanın bugünkü koduna bağlı
kalmamalı (paleti değiştiren biri eski migration'ın sonucunu değiştirmesin).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "cekirdek_0005"
down_revision: Union[str, Sequence[str], None] = "cekirdek_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PALET = ("#1d4ed8", "#c2410c", "#15803d", "#7e22ce", "#0e7490", "#be123c", "#a16207",
         "#0369a1", "#a21caf", "#4d7c0f", "#7c2d12", "#0f766e", "#be185d", "#475569")


def upgrade() -> None:
    op.add_column("ders", sa.Column("renk", sa.String(7), nullable=True))
    dizi = "ARRAY[" + ", ".join(f"'{r}'" for r in PALET) + "]"
    op.execute(f"""
        UPDATE ders SET renk = s.renk
        FROM (
            SELECT id, ({dizi})[((row_number() OVER (PARTITION BY okul_id ORDER BY ad)) - 1) % {len(PALET)} + 1] AS renk
            FROM ders
        ) AS s
        WHERE ders.id = s.id
    """)
    op.alter_column("ders", "renk", nullable=False)
    op.create_check_constraint(op.f("ck_ders_renk_bicimi"), "ders", "renk ~ '^#[0-9a-f]{6}$'")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_ders_renk_bicimi"), "ders", type_="check")
    op.drop_column("ders", "renk")
