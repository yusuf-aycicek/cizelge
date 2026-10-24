"""Paylaşım linkleri (8b, ADR 0022) ve girişsiz okuma fonksiyonu `paylasim_icerigi`.

`paylasim_linki`: okula ait sıradan tablo (RLS, bileşik FK). Kapsam: bütün okul, tek öğretmen ya
da tek şube; kapsam başına tek link. Öğretmen ya da şube silinince linki de silinir (CASCADE).

**Girişsiz okuma (giriş adımındaki yaklaşım, cekirdek_0004).** Linkle gelen istekte okul bilinmez;
uygulama rolü okul bağlamı olmadan hiçbir satır göremez. `paylasim_icerigi(jeton)` dar kapsamlı bir
`SECURITY DEFINER` fonksiyondur, sahibi `okul_paylasim` rolüdür:
- `NOLOGIN`, süper kullanıcı değil, BYPASSRLS yok;
- yalnızca `paylasim_linki (okul_id, tur, ogretmen_id, sinif_id, jeton)` ve
  `yayin (okul_id, yayin_zamani, icerik)` sütunlarını okur; ikisinde de yalnızca bu role tanımlı
  bir okuma politikası vardır (politikalar "VEYA" ile birleşir, uygulama rolününki değişmez);
- **süzme burada yapılır:** öğretmen linki yalnızca o öğretmenin (`kimlik` = `ogretmen_id`), şube
  linki yalnızca o şubenin çizelgesini döner; okul linki hepsini. Uygulama süzülmemiş içeriği hiç
  görmez.
`SET search_path = pg_catalog, public`; `PUBLIC`'in çalıştırma yetkisi kaldırılır, yalnızca
`okul_uygulama` çağırır.

Dönen değer: link yoksa NULL; varsa `{"tur", "yayin_zamani", "icerik"}` (yayın yoksa ikisi NULL).

Revision ID: ders_programi_0011
Revises: ders_programi_0010
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ders_programi_0011"
down_revision: Union[str, Sequence[str], None] = "ders_programi_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UYGULAMA = "okul_uygulama"
PAYLASIM = "okul_paylasim"
IMZA = "paylasim_icerigi(text)"

FONKSIYON = """
    CREATE FUNCTION paylasim_icerigi(p_jeton text) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        SELECT jsonb_build_object(
            'tur', l.tur,
            'yayin_zamani', y.yayin_zamani,
            'icerik', CASE WHEN y.icerik IS NULL THEN NULL ELSE
                (y.icerik - 'subeler' - 'ogretmenler') || jsonb_build_object(
                    'subeler', CASE l.tur
                        WHEN 'okul' THEN y.icerik -> 'subeler'
                        WHEN 'sube' THEN coalesce((
                            SELECT jsonb_agg(c) FROM jsonb_array_elements(y.icerik -> 'subeler') c
                            WHERE c ->> 'kimlik' = l.sinif_id::text), '[]'::jsonb)
                        ELSE '[]'::jsonb END,
                    'ogretmenler', CASE l.tur
                        WHEN 'okul' THEN y.icerik -> 'ogretmenler'
                        WHEN 'ogretmen' THEN coalesce((
                            SELECT jsonb_agg(c) FROM jsonb_array_elements(y.icerik -> 'ogretmenler') c
                            WHERE c ->> 'kimlik' = l.ogretmen_id::text), '[]'::jsonb)
                        ELSE '[]'::jsonb END)
            END)
        FROM public.paylasim_linki l
        LEFT JOIN public.yayin y ON y.okul_id = l.okul_id
        -- Eşitlik (joker yok); benzersiz indeksi kullanır.
        WHERE l.jeton = p_jeton
    $$"""


def upgrade() -> None:
    op.create_table(
        "paylasim_linki",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("ogretmen_id", sa.Uuid(), nullable=True),
        sa.Column("sinif_id", sa.Uuid(), nullable=True),
        sa.Column("jeton", sa.String(length=64), nullable=False),
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paylasim_linki")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f("fk_paylasim_linki_okul_id_okul"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["okul_id", "ogretmen_id"], ["ogretmen.okul_id", "ogretmen.id"],
                                name=op.f("fk_paylasim_linki_okul_id_ogretmen_id_ogretmen"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["okul_id", "sinif_id"], ["sinif.okul_id", "sinif.id"],
                                name=op.f("fk_paylasim_linki_okul_id_sinif_id_sinif"), ondelete="CASCADE"),
        sa.CheckConstraint(
            "(tur = 'okul' AND ogretmen_id IS NULL AND sinif_id IS NULL)"
            " OR (tur = 'ogretmen' AND ogretmen_id IS NOT NULL AND sinif_id IS NULL)"
            " OR (tur = 'sube' AND sinif_id IS NOT NULL AND ogretmen_id IS NULL)",
            name=op.f("ck_paylasim_linki_kapsam")),
        sa.CheckConstraint("length(jeton) >= 32", name=op.f("ck_paylasim_linki_jeton_uzunlugu")),
        sa.UniqueConstraint("okul_id", "id", name=op.f("uq_paylasim_linki_okul_id_id")),
        sa.UniqueConstraint("jeton", name=op.f("uq_paylasim_linki_jeton")),
        sa.UniqueConstraint("okul_id", "tur", "ogretmen_id", "sinif_id", name=op.f("uq_paylasim_linki_okul_id_tur_ogretmen_id_sinif_id"),
                            postgresql_nulls_not_distinct=True),
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON paylasim_linki TO {UYGULAMA}")
    op.execute("ALTER TABLE paylasim_linki ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE paylasim_linki FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON paylasim_linki "
               "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")

    # --- okul_paylasim rolü: yalnızca fonksiyonun sahibi ----------------------------------------
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{PAYLASIM}') THEN
                CREATE ROLE {PAYLASIM} NOLOGIN;
            END IF;
        END $$
    """)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {PAYLASIM}")
    op.execute(f"GRANT SELECT (okul_id, tur, ogretmen_id, sinif_id, jeton) ON paylasim_linki TO {PAYLASIM}")
    op.execute(f"GRANT SELECT (okul_id, yayin_zamani, icerik) ON yayin TO {PAYLASIM}")
    op.execute(f"CREATE POLICY paylasim_okuma ON paylasim_linki FOR SELECT TO {PAYLASIM} USING (true)")
    op.execute(f"CREATE POLICY paylasim_okuma ON yayin FOR SELECT TO {PAYLASIM} USING (true)")

    op.execute(FONKSIYON)
    op.execute(f"ALTER FUNCTION {IMZA} OWNER TO {PAYLASIM}")
    op.execute(f"REVOKE ALL ON FUNCTION {IMZA} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {IMZA} TO {UYGULAMA}")


def downgrade() -> None:
    op.execute(f"DROP FUNCTION {IMZA}")
    op.execute("DROP POLICY paylasim_okuma ON yayin")
    op.execute(f"REVOKE ALL ON yayin FROM {PAYLASIM}")
    op.drop_table("paylasim_linki")  # politikaları ve yetkileriyle birlikte
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {PAYLASIM}")
    # okul_paylasim rolü silinmez: küme düzeyindedir (okul_giris gibi).
