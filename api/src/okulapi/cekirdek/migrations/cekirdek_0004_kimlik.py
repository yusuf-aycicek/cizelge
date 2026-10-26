"""Kimlik doğrulama: oturum, kaba kuvvet sayacı, e-posta benzersizliği ve RLS altında arama
(docs/kimlik-plani.md, ADR 0012, ADR 0009).

**Sorun.** Girişte ve oturum çözmede okul henüz bilinmez. `kullanici` ve `oturum` tabloları RLS'ye
tabidir: uygulama rolü `app.okul_id` olmadan hiçbir satır göremez.

**Çözüm.** Dar kapsamlı `SECURITY DEFINER` fonksiyonlar. Böyle bir fonksiyon çağıranın değil,
**sahibinin** yetkisiyle çalışır. Sahip, bu iş için açılan `okul_giris` rolüdür:
- `NOLOGIN`: kimse bu rolle bağlanamaz, yalnızca fonksiyonların sahibidir;
- süper kullanıcı değildir, RLS'yi atlama yetkisi (BYPASSRLS) yoktur;
- yalnızca gereken sütunlarda yetkisi vardır: `kullanici(id, okul_id, email, sifre_hash)`, `oturum`
  (okuma ve son kullanım zamanını güncelleme), `giris_denemesi`;
- iki tabloda yalnızca bu role tanımlı birer RLS politikası vardır (`TO okul_giris`). Uygulama
  rolü için var olan `okul_izolasyonu` politikası aynen kalır.

Fonksiyonlar:
- `giris_bilgisi(email)`: tam eşleşen tek e-postanın (kullanici_id, okul_id, sifre_hash) satırı;
- `oturum_coz(jeton_ozeti)`: süresi geçmemiş oturumun (oturum_id, kullanici_id, okul_id) satırı,
  son kullanım zamanını ilerletir (en çok dakikada bir: her istek bir yazma olmasın);
- `giris_kilitli_mi(email)`, `giris_hatasi_kaydet(email, esik, pencere, kilit_suresi)`,
  `giris_denemelerini_sil(email)`: kaba kuvvet sayacı. Eşik ve süreler uygulamadan gelir.

Her fonksiyonda `SET search_path = pg_catalog, public`: SECURITY DEFINER fonksiyonların bilinen
açığı, çağıranın arama yoluna koyduğu sahte bir tablonun ya da fonksiyonun sahibin yetkisiyle
çalışmasıdır. Arama yolu sabitlenir ve tablolar şemasıyla yazılır. Ayrıca `PUBLIC`'in çalıştırma
yetkisi kaldırılır; yalnızca `okul_uygulama` çağırabilir.

**E-posta.** Var olan e-postalar küçük harfe çevrilir. `UNIQUE (email)` (büyük/küçük harfe duyarlı)
yerine `lower(email)` üzerinde benzersiz indeks gelir. CHECK `email = lower(email)` eklenir.

Notlar:
- `ALTER FUNCTION ... OWNER TO okul_giris` için migration rolünün `okul_giris` üyesi ya da süper
  kullanıcı olması gerekir (geliştirmede `okul_sahip` süper kullanıcıdır; süper kullanıcı değilse,
  ör. Neon, migration rolü kendisine verir).
- E-postaları küçük harfe çeviren UPDATE: tablo sahibi süper kullanıcı değilse `FORCE ROW LEVEL
  SECURITY` yüzünden satırları göremez. Böyle bir ortamda bu migration'dan önce RLS geçici olarak
  kapatılmalıdır. Bu sürümde gerçek kullanıcı verisi yok.

Revision ID: cekirdek_0004
Revises: cekirdek_0003
Create Date: 2026-10-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "cekirdek_0004"
down_revision: Union[str, Sequence[str], None] = "cekirdek_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UYGULAMA = "okul_uygulama"
GIRIS = "okul_giris"
GUVENLI = "SECURITY DEFINER SET search_path = pg_catalog, public"

FONKSIYONLAR = {
    "giris_bilgisi(text)": f"""
        CREATE FUNCTION giris_bilgisi(p_email text)
        RETURNS TABLE (kullanici_id uuid, okul_id uuid, sifre_hash text)
        LANGUAGE sql STABLE {GUVENLI} AS $$
            -- Eşitlik: joker yok (LIKE değil). lower(email): benzersiz indeksi kullanır.
            SELECT k.id, k.okul_id, k.sifre_hash::text
            FROM public.kullanici k
            WHERE lower(k.email) = lower(p_email)
        $$""",
    "oturum_coz(text)": f"""
        CREATE FUNCTION oturum_coz(p_jeton_ozeti text)
        RETURNS TABLE (oturum_id uuid, kullanici_id uuid, okul_id uuid)
        LANGUAGE plpgsql VOLATILE {GUVENLI} AS $$
        DECLARE
            o record;
        BEGIN
            SELECT t.id, t.kullanici_id, t.okul_id, t.son_kullanim INTO o
            FROM public.oturum t
            WHERE t.jeton_ozeti = p_jeton_ozeti
              AND t.son_kullanim + t.hareketsizlik_siniri > now()
              AND t.bitis_mutlak > now();
            IF NOT FOUND THEN
                RETURN;
            END IF;
            IF o.son_kullanim < now() - interval '1 minute' THEN
                UPDATE public.oturum SET son_kullanim = now() WHERE id = o.id;
            END IF;
            RETURN QUERY SELECT o.id, o.kullanici_id, o.okul_id;
        END
        $$""",
    "giris_kilitli_mi(text)": f"""
        CREATE FUNCTION giris_kilitli_mi(p_email text) RETURNS boolean
        LANGUAGE sql STABLE {GUVENLI} AS $$
            SELECT EXISTS (
                SELECT FROM public.giris_denemesi g
                WHERE g.email = lower(p_email) AND g.kilit_bitis > now()
            )
        $$""",
    "giris_hatasi_kaydet(text, integer, interval, interval)": f"""
        CREATE FUNCTION giris_hatasi_kaydet(p_email text, p_esik integer, p_pencere interval,
                                            p_kilit_suresi interval) RETURNS boolean
        LANGUAGE plpgsql VOLATILE {GUVENLI} AS $$
        DECLARE
            n integer;
        BEGIN
            -- Eski kayıtlar: bilinmeyen e-postalarla tablo şişmesin.
            DELETE FROM public.giris_denemesi
            WHERE pencere_basi < now() - interval '1 day' AND (kilit_bitis IS NULL OR kilit_bitis < now());
            -- Pencere dolduysa sayaç sıfırdan başlar. ON CONFLICT: eşzamanlı denemeler de doğru sayılır.
            INSERT INTO public.giris_denemesi AS g (email, hata_sayisi, pencere_basi)
            VALUES (left(lower(p_email), 320), 1, now())
            ON CONFLICT (email) DO UPDATE SET
                hata_sayisi = CASE WHEN g.pencere_basi < now() - p_pencere THEN 1 ELSE g.hata_sayisi + 1 END,
                pencere_basi = CASE WHEN g.pencere_basi < now() - p_pencere THEN now() ELSE g.pencere_basi END
            RETURNING g.hata_sayisi INTO n;
            IF n >= p_esik THEN
                UPDATE public.giris_denemesi
                SET kilit_bitis = now() + p_kilit_suresi, hata_sayisi = 0, pencere_basi = now()
                WHERE email = left(lower(p_email), 320);
                RETURN true;  -- bu hatayla kilitlendi
            END IF;
            RETURN false;
        END
        $$""",
    "giris_denemelerini_sil(text)": f"""
        CREATE FUNCTION giris_denemelerini_sil(p_email text) RETURNS void
        LANGUAGE sql VOLATILE {GUVENLI} AS $$
            DELETE FROM public.giris_denemesi WHERE email = lower(p_email)
        $$""",
}


def upgrade() -> None:
    # --- e-posta: bütün sistemde, büyük/küçük harf ayrımsız tek ---------------------------------
    op.execute("UPDATE kullanici SET email = lower(email) WHERE email <> lower(email)")
    op.drop_constraint("uq_kullanici_email", "kullanici", type_="unique")
    op.create_index("uq_kullanici_email_kucuk", "kullanici", [sa.text("lower(email)")], unique=True)
    op.create_check_constraint(op.f("ck_kullanici_email_kucuk_harf"), "kullanici", "email = lower(email)")

    # --- tablolar --------------------------------------------------------------------------------
    op.create_table(
        "oturum",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("okul_id", sa.Uuid(), nullable=False),
        sa.Column("kullanici_id", sa.Uuid(), nullable=False),
        sa.Column("jeton_ozeti", sa.String(length=64), nullable=False),
        sa.Column("son_kullanim", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("hareketsizlik_siniri", sa.Interval(), nullable=False),
        sa.Column("bitis_mutlak", sa.DateTime(timezone=True), nullable=False),
        sa.Column("olusturma", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("guncelleme", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oturum")),
        sa.ForeignKeyConstraint(["okul_id"], ["okul.id"], name=op.f("fk_oturum_okul_id_okul"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["okul_id", "kullanici_id"], ["kullanici.okul_id", "kullanici.id"],
                                name=op.f("fk_oturum_okul_id_kullanici_id_kullanici"), ondelete="CASCADE"),
        sa.UniqueConstraint("okul_id", "id", name=op.f("uq_oturum_okul_id_id")),
        sa.UniqueConstraint("jeton_ozeti", name=op.f("uq_oturum_jeton_ozeti")),
    )
    op.create_index(op.f("ix_oturum_okul_id_kullanici_id"), "oturum", ["okul_id", "kullanici_id"])
    op.create_table(
        "giris_denemesi",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hata_sayisi", sa.Integer(), nullable=False),
        sa.Column("pencere_basi", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kilit_bitis", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("email", name=op.f("pk_giris_denemesi")),
    )

    # --- oturum: okula ait, uygulama rolü için diğer tablolarla aynı RLS ----------------------
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON oturum TO {UYGULAMA}")
    op.execute("ALTER TABLE oturum ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oturum FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON oturum "
               "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")
    # giris_denemesi: uygulama rolüne hiçbir yetki verilmez (yalnızca fonksiyonlar).

    # --- okul_giris rolü ve dar yetkileri ------------------------------------------------------
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{GIRIS}') THEN
                CREATE ROLE {GIRIS} NOLOGIN;
            END IF;
            -- Süper kullanıcı olmayan migration rolü (ör. Neon'un sahip rolü) fonksiyonu bu role
            -- devredebilmek için rolün üyesi olmalı. PostgreSQL 16+ rolü oluşturana bu yetkiyi verir.
            IF NOT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
                EXECUTE format('GRANT %I TO %I', '{GIRIS}', current_user);
            END IF;
        END $$
    """)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {GIRIS}")
    op.execute(f"GRANT SELECT (id, okul_id, email, sifre_hash) ON kullanici TO {GIRIS}")
    op.execute(f"GRANT SELECT (id, okul_id, kullanici_id, jeton_ozeti, son_kullanim, hareketsizlik_siniri, "
               f"bitis_mutlak), UPDATE (son_kullanim) ON oturum TO {GIRIS}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON giris_denemesi TO {GIRIS}")
    # Politikalar yalnızca okul_giris için; politikalar "VEYA" ile birleşir, uygulama rolünün
    # gördüğü değişmez.
    op.execute(f"CREATE POLICY giris_arama ON kullanici FOR SELECT TO {GIRIS} USING (true)")
    op.execute(f"CREATE POLICY giris_okuma ON oturum FOR SELECT TO {GIRIS} USING (true)")
    op.execute(f"CREATE POLICY giris_son_kullanim ON oturum FOR UPDATE TO {GIRIS} USING (true) WITH CHECK (true)")

    # --- fonksiyonlar --------------------------------------------------------------------------
    # PostgreSQL 15+: fonksiyonun yeni sahibinin şemada CREATE yetkisi olmalı (süper kullanıcı
    # olmayan migration rolünde, ör. Neon, denetlenir). Yalnızca devir sırasında verilir.
    op.execute(f"GRANT CREATE ON SCHEMA public TO {GIRIS}")
    for imza, tanim in FONKSIYONLAR.items():
        op.execute(tanim)
        op.execute(f"ALTER FUNCTION {imza} OWNER TO {GIRIS}")
        op.execute(f"REVOKE ALL ON FUNCTION {imza} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {imza} TO {UYGULAMA}")
    op.execute(f"REVOKE CREATE ON SCHEMA public FROM {GIRIS}")


def downgrade() -> None:
    for imza in FONKSIYONLAR:
        op.execute(f"DROP FUNCTION {imza}")
    op.execute("DROP POLICY giris_arama ON kullanici")
    op.execute(f"REVOKE ALL ON kullanici FROM {GIRIS}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {GIRIS}")
    op.drop_table("giris_denemesi")
    op.drop_index(op.f("ix_oturum_okul_id_kullanici_id"), table_name="oturum")
    op.drop_table("oturum")  # politikaları ve yetkileriyle birlikte
    op.drop_constraint(op.f("ck_kullanici_email_kucuk_harf"), "kullanici", type_="check")
    op.drop_index("uq_kullanici_email_kucuk", table_name="kullanici")
    op.create_unique_constraint("uq_kullanici_email", "kullanici", ["email"])
    # okul_giris rolü silinmez: küme düzeyindedir (cekirdek_0003'teki gibi).
