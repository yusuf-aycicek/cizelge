"""Program üretimi için sonuç alanları ve durum tutarlılık kısıtları (yapım sırası 3).

Yeni sütunların hepsi boş olabilir: var olan programlar etkilenmez, değerler üretim bitince dolar.
Kısıtların gerekçeleri modeller.py'deki `Program` açıklamasında. Liste değerleri burada sabit
yazılır (modelden içe aktarılmaz): migration, yazıldığı andaki şemayı anlatmalı; model ileride
değişse de bu dosyanın anlamı değişmemeli.

Revision ID: ders_programi_0004
Revises: ders_programi_0003
Create Date: 2026-10-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ders_programi_0004"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KISITLAR = {
    "cozum_durumu": "cozum_durumu IN ('optimal', 'uygun', 'cozumsuz', 'on_kontrol_hatasi', 'bilinmiyor')",
    "toplam_ceza": "toplam_ceza >= 0",
    "baslama": "durum NOT IN ('uretiliyor', 'hazir') OR baslama IS NOT NULL",
    "hazir_cozum": "durum <> 'hazir' OR (cozum_durumu IS NOT NULL AND cozum_durumu IN ('optimal', 'uygun'))",
    "bitis": "durum NOT IN ('hazir', 'basarisiz') OR bitis IS NOT NULL",
}


def upgrade() -> None:
    op.add_column("program", sa.Column("baslama", sa.DateTime(timezone=True), nullable=True))
    op.add_column("program", sa.Column("cozum_durumu", sa.String(length=20), nullable=True))
    op.add_column("program", sa.Column("toplam_ceza", sa.Integer(), nullable=True))
    op.add_column("program", sa.Column("olcumler", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("program", sa.Column("celiskiler", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("program", sa.Column("sure_sn", sa.Float(), nullable=True))
    op.add_column("program", sa.Column("girdi_ozeti", sa.String(length=64), nullable=True))
    # Adlar adlandırma kuralıyla aynı: ck_program_<ad> (cekirdek/veritabani.py, ADLANDIRMA_KURALI).
    for ad, kosul in KISITLAR.items():
        op.create_check_constraint(op.f(f"ck_program_{ad}"), "program", kosul)
    # "Bu okulun etkin üretimi var mı?" sorusu (plan karar c) her üretim isteğinde sorulur.
    op.create_index(op.f("ix_program_okul_id_durum"), "program", ["okul_id", "durum"])


def downgrade() -> None:
    op.drop_index(op.f("ix_program_okul_id_durum"), table_name="program")
    for ad in reversed(list(KISITLAR)):
        op.drop_constraint(op.f(f"ck_program_{ad}"), "program", type_="check")
    for sutun in ("girdi_ozeti", "sure_sn", "celiskiler", "olcumler", "toplam_ceza", "cozum_durumu", "baslama"):
        op.drop_column("program", sutun)
