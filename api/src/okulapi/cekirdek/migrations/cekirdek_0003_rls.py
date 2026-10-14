"""Çekirdek tabloları için satır düzeyi güvenlik (RLS) ve uygulama rolü (docs/adr/0009).

- `okul_uygulama`: uygulamanın bağlandığı rol. Tabloların sahibi değildir; yalnızca tablo
  yetkileri (GRANT) vardır ve RLS politikalarına tabidir. Giriş yetkisi ve parolası altyapıda
  verilir (docker/postgres/init); rol yoksa burada girişsiz (NOLOGIN) oluşturulur ki migration
  her ortamda çalışsın.
- `aktif_okul_id()`: işlemin okulu. Uygulama her işlemin başında `SET LOCAL app.okul_id` yapar
  (okulapi.cekirdek.kiraci). Ayar yoksa ya da boşsa NULL döner ve hiçbir politika geçmez.
- Politika: okula ait her tabloda `okul_id = aktif_okul_id()`; okul tablosunda `id = aktif_okul_id()`.
  USING okumayı (SELECT, UPDATE/DELETE'in göreceği satırları), WITH CHECK yazılan yeni satırı
  denetler: başka okula satır yazılamaz.
- FORCE ROW LEVEL SECURITY: tablo sahibi de politikaya tabi olsun (süper kullanıcı yine atlar;
  bu yüzden uygulama asla süper kullanıcı ya da sahip rolüyle bağlanmaz).

Bu migration uygulama kodunu içe aktarmaz: uygulanmış bir migration ileride değişmemelidir.

Revision ID: cekirdek_0003
Revises: cekirdek_0002
Create Date: 2026-10-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "cekirdek_0003"
down_revision: Union[str, Sequence[str], None] = "cekirdek_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROL = "okul_uygulama"
OKULA_AIT = ("kullanici", "ogretmen", "sinif", "ders")


def upgrade() -> None:
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{ROL}') THEN
                CREATE ROLE {ROL} NOLOGIN;
            END IF;
        END $$
    """)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROL}")
    op.execute("""
        CREATE FUNCTION aktif_okul_id() RETURNS uuid LANGUAGE sql STABLE AS $$
            -- current_setting(..., true): ayar hiç tanımlanmadıysa hata yerine NULL döner.
            -- SET LOCAL'ın süresi dolunca değer boş metin ('') olarak kalır: nullif ile NULL'a çevrilir.
            SELECT nullif(current_setting('app.okul_id', true), '')::uuid
        $$
    """)
    op.execute(f"GRANT EXECUTE ON FUNCTION aktif_okul_id() TO {ROL}")

    # Okul: uygulama okul ekler ve günceller ama silmez.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON okul TO {ROL}")
    op.execute("ALTER TABLE okul ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE okul FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY okul_izolasyonu ON okul USING (id = aktif_okul_id()) WITH CHECK (id = aktif_okul_id())")

    for tablo in OKULA_AIT:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tablo} TO {ROL}")
        op.execute(f"ALTER TABLE {tablo} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tablo} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY okul_izolasyonu ON {tablo} "
                   "USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id = aktif_okul_id())")


def downgrade() -> None:
    for tablo in (*OKULA_AIT, "okul"):
        op.execute(f"DROP POLICY okul_izolasyonu ON {tablo}")
        op.execute(f"ALTER TABLE {tablo} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tablo} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {tablo} FROM {ROL}")
    op.execute("DROP FUNCTION aktif_okul_id()")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROL}")
    # Rol silinmez: küme (cluster) düzeyindedir, başka veritabanları da kullanıyor olabilir.
