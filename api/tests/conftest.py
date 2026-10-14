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
from okulapi.cekirdek.veritabani import motor_olustur
from okulapi.main import uygulama_olustur
from okulapi.migrasyon import alembic_ayari

TEST_URL = os.environ.get(
    "OKULAPI_TEST_VERITABANI_URL", "postgresql+psycopg://okul_sahip:okul_sahip@localhost:5433/okul_test"
)


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


@pytest.fixture(scope="session")
def ayarlar() -> Ayarlar:
    return Ayarlar(veritabani_url=TEST_URL)


@pytest.fixture(scope="session")
def veritabani(ayarlar):
    """Migration'larla kurulmuş test veritabanının adresi."""
    bos_veritabani_olustur(TEST_URL)
    command.upgrade(alembic_ayari(ayarlar), "heads")
    yield TEST_URL


@pytest.fixture(scope="session")
def motor(veritabani):
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
def istemci(ayarlar, oturum_fabrikasi):
    uygulama = uygulama_olustur(ayarlar)
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi
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
