"""Uygulama ayarları. Ortam değişkenlerinden okunur (önek: OKULAPI_).

Örnek: OKULAPI_VERITABANI_URL=postgresql+psycopg://kullanici:sifre@db:5432/okul
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Ayarlar(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OKULAPI_")

    # İki ayrı rol (docs/adr/0009):
    # - uygulama `okul_uygulama` rolüyle bağlanır: tabloların sahibi değildir, yalnızca okuma/yazma
    #   yetkisi vardır, satır düzeyi güvenliğe (RLS) tabidir;
    # - migration'lar tablo sahibi `okul_sahip` rolüyle çalışır (tablo oluşturur, RLS politikası yazar).
    # Varsayılanlar geliştirme içindir (docker-compose'daki db servisine bilgisayardan bağlanmak).
    veritabani_url: str = "postgresql+psycopg://okul_uygulama:okul_uygulama@localhost:5433/okul"
    migrasyon_url: str = "postgresql+psycopg://okul_sahip:okul_sahip@localhost:5433/okul"

    # Yüklenecek modüller. Yeni bir modül eklemek için adını buraya (ya da ortam değişkenine,
    # ör. OKULAPI_ETKIN_MODULLER='["ders_programi","kutuphane"]') eklemek yeterlidir.
    etkin_moduller: list[str] = ["ders_programi"]

    # İş kuyruğu (Redis + RQ, ADR 0011). Redis bilgisayara açılmaz (plan karar g): bu varsayılan
    # yalnızca konteyner içindeki adlandırmayla anlamlıdır; docker-compose aynısını verir.
    redis_url: str = "redis://redis:6379/0"
    kuyruk_adi: str = "program_uretimi"

    # Kimlik doğrulama (ADR 0012).
    oturum_hareketsizlik_saat: int = 12  # bu kadar süre kullanılmayan oturum geçersiz olur
    oturum_en_uzun_gun: int = 7  # kullanılsa da en fazla bu kadar
    giris_hata_esigi: int = 5  # pencere içinde bu kadar hatalı deneme e-postayı kilitler
    giris_pencere_dk: int = 15
    giris_kilit_dk: int = 15

    # Tarayıcı tarafı (ADR 0013). Arayüz ile API tarayıcıya her zaman aynı köken (origin) üzerinden
    # görünür: geliştirmede Vite proxy'si, yayında aynı alan adı.
    cerez_adi: str = "oturum"
    # Secure: çerez yalnızca HTTPS üzerinden gönderilir. Varsayılan açık (yayın); yerel
    # geliştirmede http çalışabilsin diye docker-compose kapatır: OKULAPI_CEREZ_SECURE=false
    cerez_secure: bool = True
    # Veri değiştiren isteklerde (POST, PUT, PATCH, DELETE) kabul edilen Origin başlıkları.
    # Varsayılan boş: tarayıcıdan gelen hiçbir yazma isteği kabul edilmez; ortam açıkça belirtir.
    # Örnek (geliştirme): OKULAPI_IZINLI_KOKENLER='["http://localhost:5173","http://localhost:8000"]'
    izinli_kokenler: list[str] = []
