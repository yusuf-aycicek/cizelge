"""Test düzeneği: gerçek PostgreSQL (docker compose up -d db).

Her test oturumunda `okul_test` veritabanı sıfırdan oluşturulur ve **migration'larla** kurulur
(`create_all` ile değil). Böylece migration'ların kendisi de her test çalıştırmasında sınanır.

Adres değiştirilebilir: OKULAPI_TEST_VERITABANI_URL=postgresql+psycopg://.../okul_test
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.kuyruk import BellekKuyrugu
from okulapi.cekirdek.veritabani import motor_olustur
from okulapi.main import uygulama_olustur
from okulapi.migrasyon import alembic_ayari

# Tablo sahibi (migration'lar, test veritabanını kurma, "RLS olmadan ne görünür" karşılaştırması).
TEST_URL = os.environ.get(
    "OKULAPI_TEST_VERITABANI_URL", "postgresql+psycopg://okul_sahip:okul_sahip@localhost:5433/okul_test"
)
# Uygulama rolü: testler, üretimdeki gibi RLS'ye tabi bu rolle çalışır.
UYGULAMA_ROLU, UYGULAMA_SIFRESI = "okul_uygulama", "okul_uygulama"
TEST_UYGULAMA_URL = make_url(TEST_URL).set(username=UYGULAMA_ROLU, password=UYGULAMA_SIFRESI).render_as_string(
    hide_password=False)


def uygulama_rolunu_hazirla(url: str) -> None:
    """Uygulama rolü küme düzeyindedir; yoksa oluşturulur, giriş yetkisi ve parolası verilir.
    (Docker'da bunu ilk başlatmada docker/postgres/init betiği yapar.)"""
    bakim = motor_olustur(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with bakim.connect() as baglanti:
            if not baglanti.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": UYGULAMA_ROLU}).first():
                baglanti.execute(text(f"CREATE ROLE {UYGULAMA_ROLU}"))
            baglanti.execute(text(f"ALTER ROLE {UYGULAMA_ROLU} LOGIN PASSWORD '{UYGULAMA_SIFRESI}'"))
    finally:
        bakim.dispose()


def bos_veritabani_olustur(url: str) -> None:
    """Verilen adresteki veritabanını silip yeniden oluşturur (bakım veritabanı `postgres` üzerinden)."""
    adres = make_url(url)
    bakim = motor_olustur(adres.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with bakim.connect() as baglanti:
            # CREATE/DROP DATABASE bir işlem (transaction) içinde çalışamaz: AUTOCOMMIT gerekir.
            baglanti.execute(text(f'DROP DATABASE IF EXISTS "{adres.database}" WITH (FORCE)'))
            baglanti.execute(text(f'CREATE DATABASE "{adres.database}"'))
    except Exception as hata:  # anlaşılır bir ipucu ver
        raise RuntimeError(
            f"Test veritabanına ulaşılamadı ({adres.render_as_string(hide_password=True)}). "
            "PostgreSQL çalışıyor mu? Depo kökünde: docker compose up -d db"
        ) from hata
    finally:
        bakim.dispose()


@pytest.fixture(autouse=True)
def hizli_parola_ozeti(monkeypatch):
    """argon2id'nin varsayılanları (64 MiB, 3 tur) bir özette ~170 ms sürer: saldırgan için yavaş
    olması istenen şey, ama yüzlerce testte gereksiz. Testler aynı algoritmayı ucuz parametrelerle
    kullanır; varsayılanları test_kimlik_servisi.py ayrıca denetler."""
    from okulapi.cekirdek.kimlik import parola

    monkeypatch.setattr(parola, "_OZETLEYICI", HIZLI_OZETLEYICI)


def _hizli_ozetleyici():
    from argon2 import PasswordHasher

    return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


HIZLI_OZETLEYICI = _hizli_ozetleyici()


@pytest.fixture(scope="session")
def ayarlar() -> Ayarlar:
    return Ayarlar(veritabani_url=TEST_UYGULAMA_URL, migrasyon_url=TEST_URL)


@pytest.fixture(scope="session")
def veritabani(ayarlar):
    """Migration'larla (tablo sahibi rolüyle) kurulmuş test veritabanının sahip adresi."""
    bos_veritabani_olustur(TEST_URL)
    uygulama_rolunu_hazirla(TEST_URL)
    command.upgrade(alembic_ayari(ayarlar), "heads")
    yield TEST_URL


@pytest.fixture(scope="session")
def motor(veritabani):
    """Uygulama rolüyle (RLS'ye tabi) motor: testler üretimdeki gibi bununla çalışır."""
    m = motor_olustur(TEST_UYGULAMA_URL)
    yield m
    m.dispose()


@pytest.fixture(scope="session")
def sahip_motor(veritabani):
    """Tablo sahibi (bu imajda süper kullanıcı): RLS'yi atlar. Yalnızca karşılaştırma için."""
    m = motor_olustur(veritabani)
    yield m
    m.dispose()


@pytest.fixture
def oturum_fabrikasi(motor):
    """Test başına bir dış işlem; oturumların commit'i yalnızca bir SAVEPOINT'i kapatır.

    Test bitince dış işlem geri alınır: servisler gerçekten commit etse de veritabanında iz kalmaz
    ve testler birbirini etkilemez. (join_transaction_mode="create_savepoint")
    """
    baglanti = motor.connect()
    dis_islem = baglanti.begin()
    fabrika = sessionmaker(bind=baglanti, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield fabrika
    dis_islem.rollback()
    baglanti.close()


@pytest.fixture
def kuyruk():
    """Bellek içi iş kuyruğu: testlerde Redis yok (gerçek RQ: test_kuyruk.py ve kabul testi)."""
    return BellekKuyrugu()


@pytest.fixture
def istemci(ayarlar, oturum_fabrikasi, kuyruk):
    uygulama = uygulama_olustur(ayarlar)
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi
    uygulama.state.kuyruk = kuyruk
    with TestClient(uygulama) as istemci:
        yield istemci
    uygulama.state.motor.dispose()


@pytest.fixture
def okul_olustur(istemci):
    """API ile okul oluşturur, kimliğini döner."""

    def olustur(ad: str = "Deneme Lisesi", **alanlar) -> str:
        yanit = istemci.post("/api/okullar", json={"ad": ad, **alanlar})
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    return olustur


def okul_basligi(okul_id: str) -> dict[str, str]:
    return {"X-Okul-Id": str(okul_id)}


MINI = os.path.join(os.path.dirname(__file__), "..", "..", "veri", "mini.json")
DP = "/api/ders-programi"


def mini_api_ile_yukle(istemci, okul_adi: str = "Mini Lisesi") -> tuple[str, dict[str, str]]:
    """Mini veri setini (veri/mini.json) API üzerinden yeni bir okula yükler.

    `istemci`: FastAPI TestClient ya da gerçek bir httpx.Client (kabul testi). (okul_id, kimlik
    haritası) döner: mini setteki kimlik ("o-ayse", "a-9a-mat" ...) -> veritabanı kimliği.
    Kilitli yerleşimler API ile yüklenemez (elle düzeltme yapım sırası 7'de).
    """
    import json

    with open(MINI, encoding="utf-8") as f:
        mini = json.load(f)
    okul = istemci.post("/api/okullar", json={"ad": okul_adi, **mini["ayar"]}).json()
    baslik = okul_basligi(okul["id"])
    harita: dict[str, str] = {}

    def ekle(yol: str, kayit: dict, govde: dict) -> None:
        yanit = istemci.post(yol, json=govde, headers=baslik)
        assert yanit.status_code == 201, (yol, yanit.text)
        if "id" in kayit:
            harita[kayit["id"]] = yanit.json()["id"]

    for o in mini["ogretmenler"]:
        ekle("/api/ogretmenler", o, {"ad": o["ad"], "brans": o["brans"]})
    for s in mini["siniflar"]:
        ekle("/api/siniflar", s, {"ad": s["ad"], "seviye": s["seviye"]})
    for d in mini["dersler"]:
        ekle("/api/dersler", d, {"ad": d["ad"], "kisa_ad": d["kisa_ad"]})
    for a in mini["atamalar"]:
        ekle(f"{DP}/atamalar", a, {"sinif_id": harita[a["sinif_id"]], "ders_id": harita[a["ders_id"]],
                                   "ogretmen_id": harita[a["ogretmen_id"]], "haftalik_saat": a["haftalik_saat"]})
    for m in mini["musaitlikler"]:
        ekle(f"{DP}/musaitlikler", m, {**m, "ogretmen_id": harita[m["ogretmen_id"]]})
    for k in mini["kisitlar"]:
        ekle(f"{DP}/kisitlar", k, k)
    return okul["id"], harita


@pytest.fixture
def mini_yukle(istemci):
    """Mini veri setini test istemcisiyle yükler (bkz. mini_api_ile_yukle)."""
    return lambda: mini_api_ile_yukle(istemci)
