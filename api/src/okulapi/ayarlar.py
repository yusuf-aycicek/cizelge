"""Uygulama ayarları. Ortam değişkenlerinden okunur (önek: OKULAPI_).

Örnek: OKULAPI_VERITABANI_URL=postgresql+psycopg://kullanici:sifre@db:5432/okul
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Ayarlar(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OKULAPI_")

    # Geliştirme varsayılanı: docker-compose'daki `db` servisine bilgisayardan bağlanmak için.
    # 4. alt adımda (RLS) migration için tablo sahibi rolü, uygulama için ayrı bir rol kullanılacak.
    veritabani_url: str = "postgresql+psycopg://okul_sahip:okul_sahip@localhost:5433/okul"

    # Yüklenecek modüller. Yeni bir modül eklemek için adını buraya (ya da ortam değişkenine,
    # ör. OKULAPI_ETKIN_MODULLER='["ders_programi","kutuphane"]') eklemek yeterlidir.
    etkin_moduller: list[str] = ["ders_programi"]
