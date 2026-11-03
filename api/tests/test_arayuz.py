"""Derlenmiş arayüzün API ile aynı adresten sunulması (ADR 0028)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from okulapi.cekirdek.arayuz import ONBELLEKSIZ, UZUN_ONBELLEK
from okulapi.main import uygulama_olustur

INDEX = "<!doctype html><title>Çizelge</title>"


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "dist" / "assets").mkdir(parents=True)
    (tmp_path / "dist" / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "dist" / "assets" / "index-AbC123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "dist" / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "gizli.txt").write_text("dizin dışı", encoding="utf-8")
    return tmp_path / "dist"


@pytest.fixture
def arayuzlu_istemci(ayarlar, oturum_fabrikasi, dist):
    uygulama = uygulama_olustur(ayarlar.model_copy(update={"arayuz_dizini": str(dist)}))
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi
    with TestClient(uygulama) as istemci:
        yield istemci
    uygulama.state.motor.dispose()


def test_kok_ve_react_router_sayfalari_index_doner(arayuzlu_istemci):
    for yol in ["/", "/giris", "/program/5", "/p/jeton-abc", "/ogretmenler/x/y?z=1"]:
        yanit = arayuzlu_istemci.get(yol)
        assert yanit.status_code == 200, yol
        assert yanit.text == INDEX
        assert yanit.headers["cache-control"] == ONBELLEKSIZ
        assert yanit.headers["content-type"].startswith("text/html")


def test_hashli_dosyalar_uzun_onbelleklenir(arayuzlu_istemci):
    yanit = arayuzlu_istemci.get("/assets/index-AbC123.js")
    assert yanit.status_code == 200 and yanit.text == "console.log(1)"
    assert yanit.headers["cache-control"] == UZUN_ONBELLEK
    assert "javascript" in yanit.headers["content-type"]


def test_diger_dosyalar_onbelleklenmez(arayuzlu_istemci):
    yanit = arayuzlu_istemci.get("/favicon.svg")
    assert yanit.status_code == 200 and yanit.headers["cache-control"] == ONBELLEKSIZ


def test_olmayan_asset_index_degil_404(arayuzlu_istemci):
    # Eski sürümün istediği silinmiş betik HTML olarak dönmemeli.
    assert arayuzlu_istemci.get("/assets/index-eski.js").status_code == 404


def test_api_yollari_arayuze_dusmez(arayuzlu_istemci):
    assert arayuzlu_istemci.get("/api/saglik").json()["durum"] == "ok"
    for yol in ["/api/olmayan", "/api"]:
        yanit = arayuzlu_istemci.get(yol)
        assert yanit.status_code == 404, yol
        assert yanit.headers["content-type"] == "application/json"
    # Oturumsuz API isteği yine 401 (arayüz yakalamıyor).
    assert arayuzlu_istemci.get("/api/ben").status_code == 401


def test_dizin_disina_cikilamaz(arayuzlu_istemci):
    for yol in ["/../gizli.txt", "/%2e%2e/gizli.txt", "/assets/..%2f..%2fgizli.txt"]:
        yanit = arayuzlu_istemci.get(yol)
        assert "dizin dışı" not in yanit.text, yol


def test_belge_sayfasi_calisir(arayuzlu_istemci):
    assert arayuzlu_istemci.get("/openapi.json").json()["info"]["title"] == "Çizelge API"


def test_dizin_verilmezse_arayuz_sunulmaz(istemci):
    assert istemci.get("/giris").status_code == 404
    assert istemci.get("/").status_code == 404
