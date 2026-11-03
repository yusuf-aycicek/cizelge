"""Uygulama ayarları. Ortam değişkenlerinden okunur (önek: OKULAPI_).

Örnek: OKULAPI_VERITABANI_URL=postgresql+psycopg://kullanici:sifre@db:5432/okul
"""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Ayarlar(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OKULAPI_")

    # Çalışma ortamı. Varsayılan bilerek güvenli olandır ("yayin"): veriyi silen geliştirme araçları
    # (python -m okulapi ornek-okul) yalnızca OKULAPI_ORTAM=gelistirme açıkça verilince çalışır.
    # Yayındaki bir sunucu bu değişkeni hiç tanımlamaz.
    ortam: Literal["gelistirme", "yayin"] = "yayin"

    # İki ayrı rol (docs/adr/0009):
    # - uygulama `okul_uygulama` rolüyle bağlanır: tabloların sahibi değildir, yalnızca okuma/yazma
    #   yetkisi vardır, satır düzeyi güvenliğe (RLS) tabidir;
    # - migration'lar tablo sahibi `okul_sahip` rolüyle çalışır (tablo oluşturur, RLS politikası yazar).
    # Varsayılanlar geliştirme içindir (docker-compose'daki db servisine bilgisayardan bağlanmak).
    veritabani_url: str = "postgresql+psycopg://okul_uygulama:okul_uygulama@localhost:5433/okul"
    migrasyon_url: str = "postgresql+psycopg://okul_sahip:okul_sahip@localhost:5433/okul"

    @field_validator("veritabani_url", "migrasyon_url")
    @classmethod
    def _surucu_ekle(cls, url: str) -> str:
        """Barındırıcıların verdiği adres (ör. Neon: postgresql://...?sslmode=require) olduğu gibi
        yapıştırılabilsin: sürücü belirtilmemişse psycopg eklenir. SSL ayarı adresin içinde kalır."""
        for onek in ("postgresql://", "postgres://"):
            if url.startswith(onek):
                return "postgresql+psycopg://" + url.removeprefix(onek)
        return url

    # Yüklenecek modüller. Yeni bir modül eklemek için adını buraya (ya da ortam değişkenine,
    # ör. OKULAPI_ETKIN_MODULLER='["ders_programi","kutuphane"]') eklemek yeterlidir.
    etkin_moduller: list[str] = ["ders_programi"]

    # İş kuyruğu (Redis + RQ, ADR 0011). Redis bilgisayara açılmaz (plan karar g): bu varsayılan
    # yalnızca konteyner içindeki adlandırmayla anlamlıdır; docker-compose aynısını verir.
    redis_url: str = "redis://redis:6379/0"
    kuyruk_adi: str = "program_uretimi"
    # Çözücünün paralel arama iş parçacığı sayısı (CP-SAT num_workers). Bellek iş parçacığı sayısıyla
    # artar: küçük sunucularda (ör. 512 MB) düşürülür, OKULAPI_COZUCU_IS_PARCACIGI=2.
    cozucu_is_parcacigi: int = 8

    # Yayındaki demo okulun parolası (python -m okulapi demo-okul). Verilmezse demo okul kurulmaz.
    demo_parola: str | None = None
    # Demo okul en son bu kadar dakika önce kurulduysa bir sonraki "Demo ile dene" girişi onu
    # silip baştan kurar (ADR 0027). Yalnızca demo okul etkilenir.
    demo_sifirlama_dk: int = 60

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
    # Derlenmiş arayüzün dizini (web/dist). Verilirse API onu aynı adresten sunar (ADR 0028);
    # Docker imajı /app/arayuz verir. Boşsa yalnızca API çalışır (geliştirmede arayüzü Vite sunar).
    arayuz_dizini: str | None = None
