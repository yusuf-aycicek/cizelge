# Yapı bağlamı depo köküdür (docker-compose.yml: context: .). Yapım sırası 3'te worker
# çözücü paketine (/cozucu) ihtiyaç duyduğunda aynı bağlamdan kopyalanabilsin diye.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Önce yalnızca paket tanımı ve kaynak: kod değişmedikçe bağımlılık katmanı önbellekten gelir.
COPY api/pyproject.toml api/pyproject.toml
COPY api/src api/src
RUN pip install --no-cache-dir ./api

EXPOSE 8000
CMD ["uvicorn", "okulapi.main:uygulama_olustur", "--factory", "--host", "0.0.0.0", "--port", "8000"]
