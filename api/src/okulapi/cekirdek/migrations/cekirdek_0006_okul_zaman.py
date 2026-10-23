"""Okulun zamanı: günlere göre ders saati, öğle arası ve zil saatleri (K3).

- `gun_saatleri int[]`: her gün için ders saati sayısı (ör. {8,8,8,8,7}). NULL = her gün
  `gunluk_ders_saati`. Doluysa en az bir gün farklıdır (servis "hepsi aynı" listeyi NULL'a
  çevirir: aynı durumun tek gösterimi olsun) ve `gunluk_ders_saati` en uzun gündür.
- `ogle_arasi_sonra`: öğle arası kaçıncı dersten sonra (4 = 4. ile 5. ders arası); NULL = yok.
- Zil saatleri yalnızca gösterim içindir: `ilk_ders_baslangic` NULL ise tanımsız.

Var olan okullar NULL'larla kalır: davranış değişmez, veri taşıması gerekmez.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "cekirdek_0006"
down_revision: Union[str, Sequence[str], None] = "cekirdek_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PostgreSQL dizisi üzerinde CHECK: `x <= ALL(dizi)` dizinin her elemanı için doğru olmalı demektir.
# Alt sorgu CHECK'te kullanılamaz; "en uzun gün" bu yüzden ">= ALL" ve "= ANY" ile ifade edilir.
GUN_SAATLERI = (
    "gun_saatleri IS NULL OR ("
    "cardinality(gun_saatleri) = gun_sayisi"
    " AND 1 <= ALL(gun_saatleri)"
    " AND gunluk_ders_saati >= ALL(gun_saatleri)"
    " AND gunluk_ders_saati = ANY(gun_saatleri))"
)


def upgrade() -> None:
    op.add_column("okul", sa.Column("gun_saatleri", postgresql.ARRAY(sa.Integer()), nullable=True))
    op.add_column("okul", sa.Column("ogle_arasi_sonra", sa.Integer(), nullable=True))
    op.add_column("okul", sa.Column("ilk_ders_baslangic", sa.Time(), nullable=True))
    op.add_column("okul", sa.Column("ders_suresi_dk", sa.Integer(), server_default="40", nullable=False))
    op.add_column("okul", sa.Column("teneffus_dk", sa.Integer(), server_default="10", nullable=False))
    op.add_column("okul", sa.Column("ogle_arasi_dk", sa.Integer(), server_default="40", nullable=False))
    op.create_check_constraint(op.f("ck_okul_gun_saatleri"), "okul", GUN_SAATLERI)
    op.create_check_constraint(
        op.f("ck_okul_ogle_arasi_sonra"), "okul",
        "ogle_arasi_sonra IS NULL OR ogle_arasi_sonra BETWEEN 1 AND gunluk_ders_saati - 1",
    )
    op.create_check_constraint(op.f("ck_okul_ders_suresi_dk"), "okul", "ders_suresi_dk BETWEEN 10 AND 120")
    op.create_check_constraint(op.f("ck_okul_teneffus_dk"), "okul", "teneffus_dk BETWEEN 0 AND 60")
    op.create_check_constraint(op.f("ck_okul_ogle_arasi_dk"), "okul", "ogle_arasi_dk BETWEEN 0 AND 180")


def downgrade() -> None:
    for ad in ("ogle_arasi_dk", "teneffus_dk", "ders_suresi_dk", "ogle_arasi_sonra", "gun_saatleri"):
        op.drop_constraint(op.f(f"ck_okul_{ad}"), "okul", type_="check")
    for sutun in ("ogle_arasi_dk", "teneffus_dk", "ders_suresi_dk", "ilk_ders_baslangic", "ogle_arasi_sonra",
                  "gun_saatleri"):
        op.drop_column("okul", sutun)
