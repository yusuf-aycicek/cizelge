# Yapı bağlamı depo köküdür (docker-compose.yml: context: .): API, depodaki çözücü paketine
# (/cozucu) bağımlıdır. Worker aynı imajı kullanır, yalnızca komutu farklıdır (python -m okulworker):
# iş fonksiyonları okulapi modüllerinde olduğu için worker'ın API ile aynı kodu çalıştırması gerekir.
#
# İki aşama (ADR 0028): ilk aşama Node ile arayüzü derler, son imaja yalnızca derlenmiş dosyalar
# (web/dist, birkaç MB) geçer. Node, npm ve node_modules son imajda yoktur.

FROM node:22-slim AS arayuz
WORKDIR /web
# Önce yalnızca bağımlılık listesi: package*.json değişmedikçe npm ci katmanı önbellekten gelir.
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Bütün paketler kilitli sürümlerle kurulur (api/requirements.lock, pip constraints): temiz kurulum
# testlerin geçtiği sürümleri alır, yeni çıkan bir sürüm imajı sessizce değiştirmez. Çözücü, API ve
# worker aynı ortamda olduğu için tek kilit dosyası kullanılır.
COPY api/requirements.lock api/requirements.lock

# Önce çözücü (OR-Tools ile), sonra API. Çözücü değişmedikçe onun katmanı önbellekten gelir.
COPY cozucu/pyproject.toml cozucu/pyproject.toml
COPY cozucu/src cozucu/src
RUN pip install --no-cache-dir -c api/requirements.lock ./cozucu

COPY api/pyproject.toml api/pyproject.toml
COPY api/src api/src
RUN pip install --no-cache-dir -c api/requirements.lock ./api

COPY worker/pyproject.toml worker/pyproject.toml
COPY worker/src worker/src
RUN pip install --no-cache-dir -c api/requirements.lock ./worker

# Örnek okul komutunun veri setleri (docker compose exec api python -m okulapi ornek-okul ...).
COPY veri/mini.json veri/gercekci.json veri/
ENV OKULAPI_VERI_DIZINI=/app/veri

# Yayındaki tek servis başlangıcı (Render: migration, demo okul, worker, API; docker/yayin-baslat.sh).
# Docker Compose kendi komutunu verir, bunu kullanmaz.
COPY docker/yayin-baslat.sh /app/yayin-baslat.sh

# Derlenmiş arayüz: API onu aynı adresten sunar (okulapi/cekirdek/arayuz.py). En sonda: arayüz
# değişince yalnızca bu katman yenilenir.
COPY --from=arayuz /web/dist /app/arayuz
ENV OKULAPI_ARAYUZ_DIZINI=/app/arayuz

EXPOSE 8000
# Port, barındırma ortamının verdiği PORT değişkeninden (Render); yoksa 8000.
CMD ["sh", "-c", "exec uvicorn okulapi.main:uygulama_olustur --factory --host 0.0.0.0 --port ${PORT:-8000}"]
