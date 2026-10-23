"""`python -m okulapi ornek-okul`: veritabanını temizleyip mini setle örnek okulu yükler.

Veriyi sildiği için iki koruması vardır: açık ortam ayarı (OKULAPI_ORTAM=gelistirme; varsayılan
"yayin") ve --evet onayı.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from okulapi.__main__ import main
from okulapi.ayarlar import Ayarlar
from okulapi.main import uygulama_olustur
from okulapi.ornek_okul import ORNEK_EMAIL, ORNEK_OKUL, ORNEK_PAROLA, GelistirmeOrtamiDegil, ornek_okul_kur


def okul_sayisi(ayarlar) -> int:
    motor = create_engine(ayarlar.migrasyon_url)
    try:
        with motor.connect() as b:
            return b.scalar(text("SELECT count(*) FROM okul"))
    finally:
        motor.dispose()


@pytest.fixture
def gelistirme(ayarlar) -> Ayarlar:
    return ayarlar.model_copy(update={"ortam": "gelistirme"})


@pytest.fixture
def yuklu(gelistirme) -> None:
    """Veritabanında silinmemesi gereken bir okul var (korumalar çalışırsa yerinde kalır)."""
    ornek_okul_kur(gelistirme)
    assert okul_sayisi(gelistirme) == 1


def test_ortam_varsayilani_yayindir(monkeypatch):
    monkeypatch.delenv("OKULAPI_ORTAM", raising=False)
    assert Ayarlar().ortam == "yayin"


def test_ortam_degiskenden_okunur(monkeypatch):
    monkeypatch.setenv("OKULAPI_ORTAM", "gelistirme")
    assert Ayarlar().ortam == "gelistirme"


def test_gecersiz_ortam_reddedilir(monkeypatch):
    monkeypatch.setenv("OKULAPI_ORTAM", "uretim")
    with pytest.raises(ValueError):
        Ayarlar()


def test_yayin_ortaminda_onayla_bile_calismaz(yuklu, ayarlar, capsys):
    assert ayarlar.ortam == "yayin"
    assert main(["ornek-okul", "--evet"], ayarlar=ayarlar) == 3
    assert "OKULAPI_ORTAM=gelistirme" in capsys.readouterr().err
    assert okul_sayisi(ayarlar) == 1


def test_fonksiyon_dogrudan_cagrilsa_da_korunur(yuklu, ayarlar):
    with pytest.raises(GelistirmeOrtamiDegil):
        ornek_okul_kur(ayarlar)
    assert okul_sayisi(ayarlar) == 1


def test_gelistirmede_onaysiz_calismaz(yuklu, gelistirme, capsys):
    assert main(["ornek-okul"], ayarlar=gelistirme) == 2
    assert "--evet" in capsys.readouterr().err
    assert okul_sayisi(gelistirme) == 1


def test_ornek_okul_yuklenir_ve_bilinen_bilgiyle_girilir(gelistirme, capsys):
    assert main(["ornek-okul", "--evet"], ayarlar=gelistirme) == 0
    cikti = capsys.readouterr().out
    assert f"Giriş: {ORNEK_EMAIL} / {ORNEK_PAROLA}" in cikti
    assert main(["ornek-okul", "--evet"], ayarlar=gelistirme) == 0  # ikinci kez: yine tek okul
    assert okul_sayisi(gelistirme) == 1

    uygulama = uygulama_olustur(gelistirme)
    try:
        with TestClient(uygulama) as istemci:
            yanit = istemci.post("/api/giris", json={"email": ORNEK_EMAIL, "sifre": ORNEK_PAROLA})
            assert yanit.status_code == 200, yanit.text
            assert istemci.get("/api/okul").json()["ad"] == ORNEK_OKUL
            assert len(istemci.get("/api/ogretmenler").json()) == 5
            assert len(istemci.get("/api/siniflar").json()) == 3
            assert len(istemci.get("/api/ders-programi/atamalar").json()) == 18
            assert len(istemci.get("/api/ders-programi/musaitlikler").json()) == 15
            assert len(istemci.get("/api/ders-programi/seviye-sablonlari").json()) > 0
            ozet = istemci.get("/api/ders-programi/dagilim-ozeti").json()
            assert ozet["ogretmensiz_atama"] == 0
    finally:
        uygulama.state.motor.dispose()


def test_gercekci_set_secilebilir(gelistirme, capsys):
    assert main(["ornek-okul", "--evet", "--set", "gercekci"], ayarlar=gelistirme) == 0
    assert "42 ogretmen, 24 sinif" in capsys.readouterr().out
    assert okul_sayisi(gelistirme) == 1
