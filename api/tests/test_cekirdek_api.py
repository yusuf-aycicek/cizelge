"""Çekirdek API: okul, öğretmen, sınıf, ders CRUD'u; durum kodları; çekirdek tablolarında izolasyon.

Bütün tabloları ve modülleri kapsayan izolasyon kabul testi 4. alt adımda yazılacak.
"""

from __future__ import annotations

import uuid

import pytest

from conftest import okul_basligi

VARLIKLAR = [
    ("/api/ogretmenler", {"ad": "Ayşe Yılmaz", "brans": "Matematik"}, {"brans": "Fizik"}),
    ("/api/siniflar", {"ad": "9-A", "seviye": 9}, {"seviye": 10}),
    ("/api/dersler", {"ad": "Matematik", "kisa_ad": "MAT"}, {"kisa_ad": "MT"}),
]


# --- okul ------------------------------------------------------------------------------


def test_okul_olusturma_ve_ayarlar(istemci, okul_olustur):
    okul_id = okul_olustur("Atatürk Lisesi", gun_sayisi=5, gunluk_ders_saati=8)
    yanit = istemci.get("/api/okul", headers=okul_basligi(okul_id))
    assert yanit.status_code == 200
    assert yanit.json() == {"id": okul_id, "ad": "Atatürk Lisesi", "gun_sayisi": 5, "gunluk_ders_saati": 8,
                            "gun_saatleri": [8, 8, 8, 8, 8], "ogle_arasi_sonra": None, "ilk_ders_baslangic": None,
                            "ders_suresi_dk": 40, "teneffus_dk": 10, "ogle_arasi_dk": 40,
                            "zil_saatleri": None, "ogle_arasi_zili": None}

    yanit = istemci.patch("/api/okul", json={"gunluk_ders_saati": 7}, headers=okul_basligi(okul_id))
    assert yanit.status_code == 200 and yanit.json()["gunluk_ders_saati"] == 7


@pytest.mark.parametrize("okul", [{"ad": ""}, {"ad": "X", "gun_sayisi": 8}, {"ad": "X", "gunluk_ders_saati": 0}])
def test_gecersiz_okul_422(istemci, okul):
    yanit = istemci.post("/api/kayit", json={"okul": okul, "ad": "Müdür", "email": "m@x.test",
                                             "sifre": "yeterince-uzun-parola"})
    assert yanit.status_code == 422


def test_oturum_yoksa_401(istemci):
    yanit = istemci.get("/api/ogretmenler")
    assert yanit.status_code == 401 and yanit.json()["detail"] == "Oturum açmanız gerekiyor"


def test_gecersiz_cerez_401(istemci):
    assert istemci.get("/api/ogretmenler", headers={"Cookie": "oturum=uydurma"}).status_code == 401


# --- CRUD -------------------------------------------------------------------------------


@pytest.mark.parametrize("yol, olustur, degistir", VARLIKLAR)
def test_crud_akisi(istemci, okul_olustur, yol, olustur, degistir):
    baslik = okul_basligi(okul_olustur())
    yanit = istemci.post(yol, json=olustur, headers=baslik)
    assert yanit.status_code == 201, yanit.text
    kayit = yanit.json()
    assert {k: kayit[k] for k in olustur} == olustur

    assert [k["id"] for k in istemci.get(yol, headers=baslik).json()] == [kayit["id"]]
    assert istemci.get(f"{yol}/{kayit['id']}", headers=baslik).json() == kayit

    yanit = istemci.patch(f"{yol}/{kayit['id']}", json=degistir, headers=baslik)
    assert yanit.status_code == 200
    assert yanit.json() == {**kayit, **degistir}  # yalnızca gönderilen alan değişir

    assert istemci.delete(f"{yol}/{kayit['id']}", headers=baslik).status_code == 204
    assert istemci.get(f"{yol}/{kayit['id']}", headers=baslik).status_code == 404


def test_ayni_adla_ikinci_sinif_409_ama_baska_okulda_serbest(istemci, okul_olustur):
    a, b = okul_basligi(okul_olustur("A")), okul_basligi(okul_olustur("B"))
    assert istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=a).status_code == 201
    yanit = istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=a)
    assert yanit.status_code == 409
    assert yanit.json()["detail"] == "Bu okulda bu adla bir sınıf zaten var"
    assert istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=b).status_code == 201


@pytest.mark.parametrize("yol, veri", [
    ("/api/siniflar", {"ad": "13-A", "seviye": 13}),
    ("/api/siniflar", {"ad": "", "seviye": 9}),
    ("/api/ogretmenler", {"brans": "Fizik"}),
])
def test_gecersiz_veri_422(istemci, okul_olustur, yol, veri):
    assert istemci.post(yol, json=veri, headers=okul_basligi(okul_olustur())).status_code == 422


# --- izolasyon (çekirdek tabloları) ----------------------------------------------------


@pytest.mark.parametrize("yol, olustur, degistir", VARLIKLAR)
def test_baska_okulun_kaydina_erisilemez(istemci, okul_olustur, yol, olustur, degistir):
    a, b = okul_basligi(okul_olustur("A")), okul_basligi(okul_olustur("B"))
    b_kayit = istemci.post(yol, json=olustur, headers=b).json()

    assert istemci.get(yol, headers=a).json() == []
    assert istemci.get(f"{yol}/{b_kayit['id']}", headers=a).status_code == 404
    assert istemci.patch(f"{yol}/{b_kayit['id']}", json=degistir, headers=a).status_code == 404
    assert istemci.delete(f"{yol}/{b_kayit['id']}", headers=a).status_code == 404

    # B'nin kaydı değişmeden duruyor.
    assert istemci.get(f"{yol}/{b_kayit['id']}", headers=b).json() == b_kayit
