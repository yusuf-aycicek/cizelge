"""Program: `veri_ozeti` (6.3, "bu program eski verilerle üretildi" uyarısı).

`girdi_ozeti` çözücü girdisinin tamamının özetidir; temel programın yerleşimleri ve kilitleri de
içindedir. Temel program silinince ya da kilidi değişince değişir, okulun verisi değişmese de.
`veri_ozeti` yalnızca okulun verisinin (ayarlar, listeler, dağılım, müsaitlik, kurallar) özetidir:
şimdiki verinin özeti bundan farklıysa program eski verilerle üretilmiştir. Eski programlarda boş
kalır (bilinmiyor: uyarı gösterilmez).

Revision ID: ders_programi_0008
Revises: ders_programi_0007
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ders_programi_0008"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("program", sa.Column("veri_ozeti", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("program", "veri_ozeti")
