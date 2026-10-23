"""Ders renkleri: palet, okunaklılık, otomatik atama, değiştirme, migration'ın var olan dersleri doldurması."""

from __future__ import annotations

import re
import uuid

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.engine import make_url

from conftest import TEST_URL, bos_veritabani_olustur, okul_basligi
from okulapi.cekirdek.ders_renkleri import CIP_METNI, DERS_RENKLERI, siradaki_renk
from okulapi.cekirdek.veritabani import motor_olustur
from okulapi.migrasyon import alembic_ayari

PALET = [r for r, _ in DERS_RENKLERI]


def kontrast(a: str, b: str) -> float:
    def parlaklik(h: str) -> float:
        kanallar = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        kanallar = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kanallar]
        return 0.2126 * kanallar[0] + 0.7152 * kanallar[1] + 0.0722 * kanallar[2]

    x, y = sorted((parlaklik(a), parlaklik(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


# --- palet ---------------------------------------------------------------------------------


def test_kontrast_hesabi_bilinen_degerleri_verir():
    assert kontrast("#000000", "#ffffff") == pytest.approx(21, abs=0.01)
    assert kontrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


@pytest.mark.parametrize("renk, ad", DERS_RENKLERI)
def test_cip_yazisi_her_renkte_okunakli(renk, ad):
    """WCAG AA: normal boyutlu yazı en az 4.5:1."""
    assert kontrast(CIP_METNI, renk) >= 4.5, f"{ad} ({renk})"


def lab(h: str) -> tuple[float, float, float]:
    """sRGB -> CIELAB (D65): algısal renk uzaklığı için."""

    def dogrusal(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (dogrusal(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def test_renkler_birbirinden_ayirt_edilebilir():
    """Her iki palet rengi arasında CIELAB uzaklığı (ΔE) en az 15: yan yana çiplerde karışmaz."""
    import itertools
    import math

    en_yakin = min((math.dist(lab(a), lab(b)), a, b) for a, b in itertools.combinations(PALET, 2))
    assert en_yakin[0] >= 15, en_yakin


def test_ilk_14_renk_yerinde():
    """Var olan derslerin rengi değişmesin: ilk sürümün 14 rengi aynı sırada kalır."""
    assert PALET[:14] == ["#1d4ed8", "#c2410c", "#15803d", "#7e22ce", "#0e7490", "#be123c", "#a16207",
                          "#0369a1", "#a21caf", "#4d7c0f", "#7c2d12", "#0f766e", "#be185d", "#475569"]


def test_palet_bicimi():
    assert len(PALET) >= 20
    assert len(set(PALET)) == len(PALET)
    assert all(re.fullmatch(r"#[0-9a-f]{6}", r) for r in PALET)
    assert len({ad for _, ad in DERS_RENKLERI}) == len(DERS_RENKLERI)


def test_siradaki_renk_en_az_kullanilan():
    assert siradaki_renk([]) == PALET[0]
    assert siradaki_renk(PALET[:3]) == PALET[3]
    assert siradaki_renk(PALET + [PALET[0]]) == PALET[1]  # hepsi bir kez, ilki iki kez


# --- API -----------------------------------------------------------------------------------


@pytest.fixture
def baslik(okul_olustur):
    return okul_basligi(okul_olustur("Renk Lisesi"))


def ders_ekle(istemci, baslik, ad, **alanlar):
    return istemci.post("/api/dersler", json={"ad": ad, **alanlar}, headers=baslik)


def test_yeni_derslere_farkli_renkler_sirayla_verilir(istemci, baslik):
    renkler = [ders_ekle(istemci, baslik, ad).json()["renk"] for ad in ("Matematik", "Fizik", "Kimya")]
    assert renkler == PALET[:3]


def test_baska_okulun_renkleri_sayilmaz(istemci, baslik, okul_olustur):
    diger = okul_basligi(okul_olustur("Diğer Lisesi"))
    ders_ekle(istemci, diger, "Matematik")
    assert ders_ekle(istemci, baslik, "Matematik").json()["renk"] == PALET[0]


def test_renk_secilebilir_ve_degistirilebilir(istemci, baslik):
    yanit = ders_ekle(istemci, baslik, "Tarih", renk=PALET[5])
    assert yanit.status_code == 201 and yanit.json()["renk"] == PALET[5]
    yanit = istemci.patch(f"/api/dersler/{yanit.json()['id']}", json={"renk": PALET[7]}, headers=baslik)
    assert yanit.status_code == 200 and yanit.json()["renk"] == PALET[7]


@pytest.mark.parametrize("renk", ["#123456", "red", "#C2410C"])
def test_palet_disi_renk_reddedilir(istemci, baslik, renk):
    yanit = ders_ekle(istemci, baslik, "Tarih", renk=renk)
    assert yanit.status_code == 422
    assert yanit.json()["detail"] == "Ders rengi paletteki renklerden biri olmalı"


def test_renk_bosaltilamaz(istemci, baslik):
    kimlik = ders_ekle(istemci, baslik, "Tarih").json()["id"]
    yanit = istemci.patch(f"/api/dersler/{kimlik}", json={"renk": None}, headers=baslik)
    assert yanit.status_code == 422


def test_palet_ucu(istemci, baslik):
    yanit = istemci.get("/api/ders-renkleri", headers=baslik)
    assert yanit.status_code == 200
    assert yanit.json() == [{"renk": r, "ad": ad} for r, ad in DERS_RENKLERI]


def test_palet_ucu_oturum_ister(istemci):
    assert istemci.get("/api/ders-renkleri").status_code == 401


# --- migration ------------------------------------------------------------------------------


def test_migration_var_olan_derslere_okul_basina_sirayla_renk_verir():
    url = make_url(TEST_URL).set(database="okul_test_ders_rengi").render_as_string(hide_password=False)
    bos_veritabani_olustur(url)
    ayar = alembic_ayari(veritabani_url=url)
    command.upgrade(ayar, "cekirdek_0004")
    okul_a, okul_b = uuid.uuid4(), uuid.uuid4()
    motor = motor_olustur(url)
    try:
        with motor.begin() as b:
            for okul, ad in ((okul_a, "A"), (okul_b, "B")):
                b.execute(text("INSERT INTO okul (id, ad) VALUES (:id, :ad)"), {"id": okul, "ad": ad})
            for okul, dersler in ((okul_a, ["Tarih", "Fizik", "Kimya"]), (okul_b, ["Müzik"])):
                for ad in dersler:
                    b.execute(text("INSERT INTO ders (id, okul_id, ad) VALUES (:id, :okul, :ad)"),
                              {"id": uuid.uuid4(), "okul": okul, "ad": ad})
        command.upgrade(ayar, "cekirdek_0005")
        with motor.connect() as b:
            satirlar = b.execute(text("SELECT okul_id, ad, renk FROM ders ORDER BY okul_id, ad")).all()
            renkler = {(o, ad): renk for o, ad, renk in satirlar}
            assert renkler[(okul_a, "Fizik")] == PALET[0]  # ada göre sıra: Fizik, Kimya, Tarih
            assert renkler[(okul_a, "Kimya")] == PALET[1]
            assert renkler[(okul_a, "Tarih")] == PALET[2]
            assert renkler[(okul_b, "Müzik")] == PALET[0]  # her okul baştan başlar
            with pytest.raises(Exception, match="ck_ders_renk_bicimi"):
                b.execute(text("UPDATE ders SET renk = 'kirmizi'"))
        command.downgrade(ayar, "cekirdek_0004")
    finally:
        motor.dispose()
