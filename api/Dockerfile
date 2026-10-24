# Yapı bağlamı depo köküdür (docker-compose.yml: context: .): API, depodaki çözücü paketine
# (/cozucu) bağımlıdır. Worker aynı imajı kullanır, yalnızca komutu farklıdır (python -m okulworker):
# iş fonksiyonları okulapi modüllerinde olduğu için worker'ın API ile aynı kodu çalıştırması gerekir.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Önce çözücü (OR-Tools ile), sonra API. Çözücü değişmedikçe onun katmanı önbellekten gelir.
COPY cozucu/pyproject.toml cozucu/pyproject.toml
COPY cozucu/src cozucu/src
RUN pip install --no-cache-dir ./cozucu

COPY api/pyproject.toml api/pyproject.toml
COPY api/src api/src
RUN pip install --no-cache-dir ./api

COPY worker/pyproject.toml worker/pyproject.toml
COPY worker/src worker/src
RUN pip install --no-cache-dir ./worker

# Örnek okul komutunun veri setleri (docker compose exec api python -m okulapi ornek-okul ...).
COPY veri/mini.json veri/gercekci.json veri/
ENV OKULAPI_VERI_DIZINI=/app/veri

EXPOSE 8000
CMD ["uvicorn", "okulapi.main:uygulama_olustur", "--factory", "--host", "0.0.0.0", "--port", "8000"]
