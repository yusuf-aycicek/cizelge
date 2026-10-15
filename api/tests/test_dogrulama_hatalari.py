"""Doğrulama hataları Türkçe ve tek biçimde döner: {"detail": "...", "alanlar": {yol: mesaj}}."""

from __future__ import annotations

import uuid

import pytest

from conftest import okul_basligi
from okulapi.cekirdek.dogrulama_hatalari import GENEL_MESAJ, GOVDE_OKUNAMADI


def kayit(istemci, **degisen):
    govde = {"okul": {"ad": "A Lisesi"}, "ad": "Ayşe", "email": "ayse@a.test", "sifre": "yeterince-uzun-parola"}
    for anahtar, deger in degisen.items():
        hedef = govde["okul"] if anahtar.startswith("okul_") else govde
        hedef[anahtar.removeprefix("okul_")] = deger
    return istemci.post("/api/kayit", json=govde)


@pytest.mark.parametrize(
    ("degisen", "alan", "mesaj"),
    [
        ({"okul_ad": ""}, "okul.ad", "Boş bırakılamaz"),
        ({"okul_gun_sayisi": 8}, "okul.gun_sayisi", "En fazla 7 olabilir"),
        ({"okul_gunluk_ders_saati": 0}, "okul.gunluk_ders_saati", "En az 1 olmalı"),
        ({"okul_gun_sayisi": "beş"}, "okul.gun_sayisi", "Tam sayı olmalı"),
        ({"email": "bozuk"}, "email", "Geçerli bir e-posta adresi girin"),
        ({"ad": "x" * 201}, "ad", "En fazla 200 karakter olabilir"),
    ],
)
def test_alan_hatalari_turkce_ve_yoluyla(istemci, degisen, alan, mesaj):
    yanit = kayit(istemci, **degisen)
    assert yanit.status_code == 422
    assert yanit.json() == {"detail": GENEL_MESAJ, "alanlar": {alan: mesaj}}


def test_eksik_alanlar_ve_birden_cok_hata(istemci):
    yanit = istemci.post("/api/kayit", json={"okul": {"ad": ""}})
    assert yanit.json() == {"detail": GENEL_MESAJ, "alanlar": {
        "okul.ad": "Boş bırakılamaz", "ad": "Bu alan gerekli", "email": "Bu alan gerekli", "sifre": "Bu alan gerekli"}}


def test_yol_parametresi_ve_secenek_hatalari(istemci, okul_olustur):
    baslik = okul_basligi(okul_olustur())
    yanit = istemci.get("/api/ogretmenler/abc", headers=baslik)
    assert yanit.json() == {"detail": GENEL_MESAJ, "alanlar": {"kayit_id": "Geçersiz kimlik"}}
    yanit = istemci.put(f"/api/kullanicilar/{uuid.uuid4()}/rol", json={"rol": "ogretmen"}, headers=baslik)
    assert yanit.json()["alanlar"] == {"rol": "Şunlardan biri olmalı: mudur ya da mudur_yardimcisi"}


def test_okunamayan_govde(istemci):
    yanit = istemci.post("/api/giris", content=b"{bozuk json", headers={"Content-Type": "application/json"})
    assert yanit.status_code == 422 and yanit.json() == {"detail": GOVDE_OKUNAMADI, "alanlar": {}}


def test_ingilizce_metin_sizmaz(istemci):
    yanit = kayit(istemci, okul_ad="", email="bozuk", okul_gun_sayisi=99)
    metin = yanit.text
    for ingilizce in ("should", "String", "Input", "Field required", " or "):
        assert ingilizce not in metin


def test_openapi_semasi_gercek_hata_bicimini_anlatir(istemci):
    s = istemci.get("/openapi.json").json()
    hata = s["components"]["schemas"]["HTTPValidationError"]
    assert hata["properties"]["detail"] == {"type": "string", "title": "Detail"}
    assert "alanlar" in hata["properties"] and "ValidationError" not in s["components"]["schemas"]
    # Şemada ValidationError'a giden kırık bir başvuru kalmamalı.
    assert "#/components/schemas/ValidationError" not in istemci.get("/openapi.json").text
