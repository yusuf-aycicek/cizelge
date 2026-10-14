#!/bin/sh
# PostgreSQL ilk kez başlatılırken (boş veri biriminde) bir kez çalışır.
# Uygulamanın bağlanacağı rol: tabloların sahibi değil, RLS'ye tabi (docs/adr/0009).
# Tablo yetkileri ve RLS politikaları migration'larla verilir (cekirdek_0003 ve modüllerinki).
# Parola ortam değişkeninden gelir; migration dosyalarına yazılmaz.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE okul_uygulama LOGIN PASSWORD '${OKUL_UYGULAMA_SIFRESI}';
EOSQL
