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


@pytest.fixture
def istemci(ayarlar, veritabani):
    uygulama = uygulama_olustur(ayarlar)
    with TestClient(uygulama) as istemci:
        yield istemci
    uygulama.state.motor.dispose()
