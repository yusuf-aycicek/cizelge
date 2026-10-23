"""Kural kapsamı: `kisit` satırı bir derse, şubeye ya da öğretmene özel olabilir (ADR 0016).

- Üç boş olabilir sütun: `ders_id`, `sinif_id`, `ogretmen_id`. Üçü de boşsa satır okul genelidir;
  var olan satırlar böyle kalır, veri taşıması gerekmez. (`sube_grubu_id` şube grubu tablosuyla
  birlikte K5'te eklenir.)
- Bileşik yabancı anahtarlar, `ON DELETE CASCADE`: öğretmen, ders ya da şube silinince ona özel
  ayar da gider; yetim ayar kalmaz.
- CHECK: öğretmen kapsamı ders ve şube kapsamıyla birleşemez (iki ayrık kural ailesi).
- `UNIQUE (okul_id, tur)` kalkar; yerine aynı kapsamda tek tanım: `UNIQUE NULLS NOT DISTINCT
  (okul_id, tur, ders_id, sinif_id, ogretmen_id)`. Varsayılan UNIQUE'te NULL'lar birbirinden farklı
  sayılır; o zaman okul geneli satır (üç NULL) iki kez girilebilirdi. `NULLS NOT DISTINCT`
  (PostgreSQL 15+) NULL'ları eşit sayar.

Revision ID: ders_programi_0006
Revises: ders_programi_0005
Create Date: 2026-10-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ders_programi_0006"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KAPSAM = (("ders_id", "ders"), ("sinif_id", "sinif"), ("ogretmen_id", "ogretmen"))


def upgrade() -> None:
    for sutun, _hedef in KAPSAM:
        op.add_column("kisit", sa.Column(sutun, sa.Uuid(), nullable=True))
    for sutun, hedef in KAPSAM:
        op.create_foreign_key(
            op.f(f"fk_kisit_okul_id_{sutun}_{hedef}"), "kisit", hedef,
            ["okul_id", sutun], ["okul_id", "id"], ondelete="CASCADE",
        )
    op.create_check_constraint(
        op.f("ck_kisit_kapsam_ailesi"), "kisit",
        "ogretmen_id IS NULL OR (ders_id IS NULL AND sinif_id IS NULL)",
    )
    op.drop_constraint(op.f("uq_kisit_okul_id_tur"), "kisit", type_="unique")
    op.create_unique_constraint(
        op.f("uq_kisit_okul_id_tur_ders_id_sinif_id_ogretmen_id"), "kisit",
        ["okul_id", "tur", "ders_id", "sinif_id", "ogretmen_id"], postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    # Özel ayarlar eski şemada ifade edilemez: silinir, okul geneli satırlar kalır.
    op.execute("DELETE FROM kisit WHERE ders_id IS NOT NULL OR sinif_id IS NOT NULL OR ogretmen_id IS NOT NULL")
    op.drop_constraint(op.f("uq_kisit_okul_id_tur_ders_id_sinif_id_ogretmen_id"), "kisit", type_="unique")
    op.create_unique_constraint(op.f("uq_kisit_okul_id_tur"), "kisit", ["okul_id", "tur"])
    op.drop_constraint(op.f("ck_kisit_kapsam_ailesi"), "kisit", type_="check")
    for sutun, hedef in KAPSAM:
        op.drop_constraint(op.f(f"fk_kisit_okul_id_{sutun}_{hedef}"), "kisit", type_="foreignkey")
        op.drop_column("kisit", sutun)
