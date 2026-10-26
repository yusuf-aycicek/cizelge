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
from okulapi.ornek_okul import (
    DEMO_EMAIL,
    DEMO_OKUL,
    ORNEK_EMAIL,
    ORNEK_OKUL,
    ORNEK_PAROLA,
    SILME_SIRASI,
    GelistirmeOrtamiDegil,
    demo_okul_kur,
    deneme_okullarini_sil,
    okula_ait_tablolar,
    ornek_okul_kur,
)


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


def test_veritabani_adresine_surucu_eklenir_ssl_ayari_korunur(monkeypatch):
    neon = "postgresql://okul_uygulama:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    monkeypatch.setenv("OKULAPI_VERITABANI_URL", neon)
    monkeypatch.setenv("OKULAPI_MIGRASYON_URL", "postgres://sahip:p@h/neondb?sslmode=require")
    a = Ayarlar()
    assert a.veritabani_url == "postgresql+psycopg://" + neon.removeprefix("postgresql://")
    assert a.migrasyon_url == "postgresql+psycopg://sahip:p@h/neondb?sslmode=require"


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


# --- demo-okul (yayında, silmeden) ----------------------------------------------------------

DEMO_PAROLA = "demo-okul-parolasi"


def test_demo_okul_parolasiz_hicbir_sey_yapmaz(yuklu, ayarlar, capsys):
    assert main(["demo-okul"], ayarlar=ayarlar) == 2
    assert "OKULAPI_DEMO_PAROLA" in capsys.readouterr().err
    assert okul_sayisi(ayarlar) == 1


def test_demo_okul_yayinda_silmeden_eklenir_ikinci_kez_eklenmez(yuklu, ayarlar, capsys):
    yayin = ayarlar.model_copy(update={"demo_parola": DEMO_PAROLA})
    assert yayin.ortam == "yayin"
    assert main(["demo-okul"], ayarlar=yayin) == 0
    assert "Demo okul yüklendi: 5 ogretmen, 3 sinif" in capsys.readouterr().out
    assert okul_sayisi(yayin) == 2  # var olan okul yerinde
    assert main(["demo-okul"], ayarlar=yayin) == 0
    assert "zaten var" in capsys.readouterr().out
    assert okul_sayisi(yayin) == 2

    uygulama = uygulama_olustur(yayin.model_copy(update={"cerez_secure": False}))
    try:
        with TestClient(uygulama) as istemci:
            yanit = istemci.post("/api/giris", json={"email": DEMO_EMAIL, "sifre": DEMO_PAROLA})
            assert yanit.status_code == 200, yanit.text
            assert istemci.get("/api/okul").json()["ad"] == DEMO_OKUL
            assert len(istemci.get("/api/ders-programi/atamalar").json()) == 18
    finally:
        uygulama.state.motor.dispose()


def test_demo_okul_yarida_kalirsa_yarim_okul_kalmaz(yuklu, ayarlar, monkeypatch):
    import okulapi.ornek_okul as ornek

    def bozuk(*_):
        raise RuntimeError("yükleme yarıda kaldı")

    monkeypatch.setattr(ornek, "_sablonlari_uret", bozuk)
    with pytest.raises(RuntimeError):
        demo_okul_kur(ayarlar, DEMO_PAROLA)
    assert okul_sayisi(ayarlar) == 1  # kaydedilen demo okul geri silindi, öncekine dokunulmadı
    monkeypatch.undo()
    assert demo_okul_kur(ayarlar, DEMO_PAROLA) is not None  # yeniden denenebilir
    assert okul_sayisi(ayarlar) == 2


# --- deneme-temizle ---------------------------------------------------------------------------


def _deneme_okulu(ayarlar, email: str) -> None:
    """Betiğin yaptığı gibi: kayıt, öğretmen, ders, şube, atama, şablon, müsaitlik, özel ayar."""
    uygulama = uygulama_olustur(ayarlar.model_copy(update={"cerez_secure": False, "ortam": "gelistirme"}))
    try:
        with TestClient(uygulama) as i:
            assert i.post("/api/kayit", json={"okul": {"ad": f"Deneme {email}"}, "ad": "Denetim", "email": email,
                                              "sifre": "ekran-goruntusu-parolasi"}).status_code == 201
            o = i.post("/api/ogretmenler", json={"ad": "Ayşe", "brans": ""}).json()["id"]
            d = i.post("/api/dersler", json={"ad": "Matematik", "kisa_ad": "MAT"}).json()["id"]
            s = i.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}).json()["id"]
            i.post("/api/ders-programi/atamalar", json={"sinif_id": s, "ders_id": d, "ogretmen_id": o, "haftalik_saat": 2})
            i.post("/api/ders-programi/seviye-sablonlari", json={"seviye": 9, "ders_id": d, "haftalik_saat": 2})
            i.post("/api/ders-programi/musaitlikler", json={"ogretmen_id": o, "gun": 0, "saat": 0, "durum": "gelemez"})
            i.put("/api/ders-programi/kurallar/ogretmen_gunluk_siniri/ozel",
                  json={"kapsam": {"ogretmen_id": o}, "parametreler": {"m": 6}})
    finally:
        uygulama.state.motor.dispose()


def _epostalar(ayarlar) -> set[str]:
    motor = create_engine(ayarlar.migrasyon_url)
    try:
        with motor.connect() as b:
            return set(b.scalars(text("SELECT email FROM kullanici")))
    finally:
        motor.dispose()


def test_deneme_okullari_silinir_ornek_okul_kalir(yuklu, gelistirme, capsys):
    _deneme_okulu(gelistirme, "tasma-1729000000000@ornek.test")
    _deneme_okulu(gelistirme, "ekran-1729000000001@ornek.test")
    _deneme_okulu(gelistirme, "bos-1729000000002@ornek.test")
    _deneme_okulu(gelistirme, "tasma-gercek@okul.k12.tr")  # kalıba uymaz: kalır
    assert okul_sayisi(gelistirme) == 5

    assert main(["deneme-temizle"], ayarlar=gelistirme) == 0
    assert "3 deneme okulu silindi" in capsys.readouterr().out
    assert _epostalar(gelistirme) == {ORNEK_EMAIL, "tasma-gercek@okul.k12.tr"}
    assert main(["deneme-temizle"], ayarlar=gelistirme) == 0  # ikinci kez: silinecek bir şey yok
    assert "0 deneme okulu silindi." in capsys.readouterr().out


def test_deneme_temizle_yayinda_calismaz(yuklu, ayarlar, capsys):
    _deneme_okulu(ayarlar, "tasma-1@ornek.test")
    assert main(["deneme-temizle"], ayarlar=ayarlar) == 3
    with pytest.raises(GelistirmeOrtamiDegil):
        deneme_okullarini_sil(ayarlar)
    assert okul_sayisi(ayarlar) == 2


def test_silme_sirasi_okula_ait_butun_tablolari_kapsar(gelistirme):
    motor = create_engine(gelistirme.migrasyon_url)
    try:
        with motor.connect() as b:
            assert okula_ait_tablolar(b) == set(SILME_SIRASI)
    finally:
        motor.dispose()
