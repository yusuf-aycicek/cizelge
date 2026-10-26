#!/bin/sh
# Yayında (Render, tek web servisi) API imajının başlangıç komutu. Docker Compose'da kullanılmaz:
# orada api ve worker ayrı konteynerlerdir.
#
# Render'ın ücretsiz planında ayrı worker servisi olmadığı için worker aynı konteynerde, arka planda
# çalışır (docs/adr/0026). Sıra:
#   1. migration'lar (tablo sahibi rolüyle, OKULAPI_MIGRASYON_URL);
#   2. demo okul: yoksa eklenir, hiçbir şey silinmez (OKULAPI_DEMO_PAROLA verilmediyse atlanır);
#   3. worker arka planda; ölürse 5 sn sonra yeniden başlar;
#   4. API ön planda, Render'ın verdiği $PORT üzerinde (konteyner API ile yaşar).
set -e

python -m okulapi.migrasyon upgrade heads

if [ -n "$OKULAPI_DEMO_PAROLA" ]; then
  # Demo okul kurulamazsa da API açılsın: hata günlükte görünür.
  python -m okulapi demo-okul || echo "demo okul kurulamadı (yukarıdaki hataya bakın)" >&2
fi

(while true; do python -m okulworker; echo "worker durdu, 5 sn sonra yeniden başlıyor" >&2; sleep 5; done) &

# --proxy-headers: Render'ın önündeki vekil sunucu https'i X-Forwarded-Proto ile bildirir.
exec uvicorn okulapi.main:uygulama_olustur --factory --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips '*'
