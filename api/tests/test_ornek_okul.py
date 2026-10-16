"""`python -m okulapi ornek-okul`: veritabanını temizleyip mini setle örnek okulu yükler."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from okulapi.__main__ import main
from okulapi.main import uygulama_olustur
from okulapi.ornek_okul import ORNEK_EMAIL, ORNEK_OKUL, ORNEK_PAROLA


def okul_sayisi(ayarlar) -> int:
    motor = create_engine(ayarlar.migrasyon_url)
    try:
        with motor.connect() as b:
            return b.scalar(text("SELECT count(*) FROM okul"))
    finally:
        motor.dispose()


def test_onaysiz_hicbir_sey_yapmaz(ayarlar, capsys):
    once = okul_sayisi(ayarlar)
    assert main(["ornek-okul"], ayarlar=ayarlar) == 2
    assert "--evet" in capsys.readouterr().err
    assert okul_sayisi(ayarlar) == once


def test_ornek_okul_yuklenir_ve_bilinen_bilgiyle_girilir(ayarlar, capsys):
    assert main(["ornek-okul", "--evet"], ayarlar=ayarlar) == 0
    cikti = capsys.readouterr().out
    assert f"Giriş: {ORNEK_EMAIL} / {ORNEK_PAROLA}" in cikti
    assert main(["ornek-okul", "--evet"], ayarlar=ayarlar) == 0  # ikinci kez: yine tek okul
    assert okul_sayisi(ayarlar) == 1

    uygulama = uygulama_olustur(ayarlar)
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
