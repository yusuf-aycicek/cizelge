"""Şube grupları ve şube istisnaları (K5; docs/kisisellestirme-plani.md bölüm 3 ve 6).

- `seviye_sablonu.sube_grubu_id`: boşsa satır seviyenin şablonudur. **Var olan bütün satırlar
  boş kalır, yani seviye şablonları olduğu gibi korunur.** Benzersizlik `(okul_id, seviye,
  sube_grubu_id, ders_id)` olur, `NULLS NOT DISTINCT`: seviyenin şablonunda bir ders yine bir kez.
  Grup silinince şablonu da silinir (CASCADE).
- `kisit.sube_grubu_id`: şube grubuna özel ayar (ADR 0016). Şube ile şube grubu aynı kapsamda
  bulunamaz; öğretmen kapsamı grupla da birleşemez. Benzersizlik grubu da kapsar; kısıt adı
  kuralla 63 karakteri aşacağı için `uq_kisit_kapsam`.
- `sube_ders_istisnasi` (sinif_id, ders_id, tur `almaz`/`ek`, haftalik_saat yalnızca `ek` için):
  `UNIQUE (okul_id, sinif_id, ders_id)`, RLS.

`depends_on = cekirdek_0007`: `sube_grubu` tablosu çekirdekte.

Revision ID: ders_programi_0007
Revises: ders_programi_0006
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ders_programi_0007"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = "cekirdek_0007"

ROL = "okul_uygulama"
ESKI_KISIT_UQ = "uq_kisit_okul_id_tur_ders_id_sinif_id_ogretmen_id"


def upgrade() -> None:
    # Seviye şablonu: gruba bağlanabilir.
    op.add_column("seviye_sablonu", sa.Column("sube_grubu_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_seviye_sablonu_okul_id_sube_grubu_id_sube_grubu"), "seviye_sablonu", "sube_grubu",
        ["okul_id", "sube_grubu_id"], ["okul_id", "id"], ondelete="CASCADE",
    )
    op.drop_constraint(op.f("uq_seviye_sablonu_okul_id_seviye_ders_id"), "seviye_sablonu", type_="unique")
    op.create_unique_constraint(
        op.f("uq_seviye_sablonu_okul_id_seviye_sube_grubu_id_ders_id"), "seviye_sablonu",
        ["okul_id", "seviye", "sube_grubu_id", "ders_id"], postgresql_nulls_not_distinct=True,
    )

    # Kural kapsamı: şube grubu.
    op.add_column("kisit", sa.Column("sube_grubu_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_kisit_okul_id_sube_grubu_id_sube_grubu"), "kisit", "sube_grubu",
        ["okul_id", "sube_grubu_id"], ["okul_id", "id"], ondelete="CASCADE",
    )
    op.drop_constraint(op.f("ck_kisit_kapsam_ailesi"), "kisit", type_="check")
    op.create_check_constraint(
        op.f("ck_kisit_kapsam_ailesi"), "kisit",
        "ogretmen_id IS NULL OR (ders_id IS NULL AND sinif_id IS NULL AND sube_grubu_id IS NULL)",
    )
    op.create_check_constraint(op.f("ck_kisit_sube_ya_da_grup"), "kisit", "sinif_id IS NULL OR sube_grubu_id IS NULL")
    op.drop_constraint(op.f(ESKI_KISIT_UQ), "kisit", type_="unique")
    op.create_unique_constraint(
        op.f("uq_kisit_kapsam"), "kisit", ["okul_id", "tur", "ders_id", "sinif_id", "sube_grubu_id", "ogretmen_id"],
        postgresql_nulls_not_distinct=True,
    )

    # Şube ders istisnaları.
    op.create_table(
        "sube_ders_istisnasi",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
        sa.Column("sinif_id", sa.Uuid(), nullable=False),
        sa.Column("ders_id", sa.Uuid(), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("haftalik_saat", sa.Integer(), nullable=True),
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sube_ders_istisnasi")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f("fk_sube_ders_istisnasi_okul_id_okul"),
                                ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["okul_id", "sinif_id"], ["sinif.okul_id", "sinif.id"],
                                name=op.f("fk_sube_ders_istisnasi_okul_id_sinif_id_sinif"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["okul_id", "ders_id"], ["ders.okul_id", "ders.id"],
                                name=op.f("fk_sube_ders_istisnasi_okul_id_ders_id_ders"), ondelete="CASCADE"),
        sa.UniqueConstraint("okul_id", "id", name=op.f("uq_sube_ders_istisnasi_okul_id_id")),
        sa.UniqueConstraint("okul_id", "sinif_id", "ders_id",
                            name=op.f("uq_sube_ders_istisnasi_okul_id_sinif_id_ders_id")),
        sa.CheckConstraint("tur IN ('almaz', 'ek')", name=op.f("ck_sube_ders_istisnasi_tur")),
        sa.CheckConstraint(
            "(tur = 'ek') = (haftalik_saat IS NOT NULL) AND (haftalik_saat IS NULL OR haftalik_saat >= 1)",
            name=op.f("ck_sube_ders_istisnasi_haftalik_saat"),
        ),
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON sube_ders_istisnasi TO {ROL}")
    op.execute("ALTER TABLE sube_ders_istisnasi ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sube_ders_istisnasi FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON sube_ders_istisnasi "
               "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")


def downgrade() -> None:
    op.execute("DROP POLICY okul_izolasyonu ON sube_ders_istisnasi")
    op.drop_table("sube_ders_istisnasi")

    # Gruba özel ayarlar ve grup şablonları eski şemada ifade edilemez: silinir.
    op.execute("DELETE FROM kisit WHERE sube_grubu_id IS NOT NULL")
    op.drop_constraint(op.f("uq_kisit_kapsam"), "kisit", type_="unique")
    op.create_unique_constraint(
        op.f(ESKI_KISIT_UQ), "kisit", ["okul_id", "tur", "ders_id", "sinif_id", "ogretmen_id"],
        postgresql_nulls_not_distinct=True,
    )
    op.drop_constraint(op.f("ck_kisit_sube_ya_da_grup"), "kisit", type_="check")
    op.drop_constraint(op.f("ck_kisit_kapsam_ailesi"), "kisit", type_="check")
    op.create_check_constraint(
        op.f("ck_kisit_kapsam_ailesi"), "kisit", "ogretmen_id IS NULL OR (ders_id IS NULL AND sinif_id IS NULL)",
    )
    op.drop_constraint(op.f("fk_kisit_okul_id_sube_grubu_id_sube_grubu"), "kisit", type_="foreignkey")
    op.drop_column("kisit", "sube_grubu_id")

    op.execute("DELETE FROM seviye_sablonu WHERE sube_grubu_id IS NOT NULL")
    op.drop_constraint(op.f("uq_seviye_sablonu_okul_id_seviye_sube_grubu_id_ders_id"), "seviye_sablonu",
                       type_="unique")
    op.create_unique_constraint(
        op.f("uq_seviye_sablonu_okul_id_seviye_ders_id"), "seviye_sablonu", ["okul_id", "seviye", "ders_id"],
    )
    op.drop_constraint(op.f("fk_seviye_sablonu_okul_id_sube_grubu_id_sube_grubu"), "seviye_sablonu",
                       type_="foreignkey")
    op.drop_column("seviye_sablonu", "sube_grubu_id")
