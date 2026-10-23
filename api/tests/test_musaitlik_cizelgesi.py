"""Öğretmenin müsaitlik çizelgesi: toplu değişiklik (ya hep ya hiç) ve yük (5.5, K2)."""

from __future__ import annotations

import uuid

import pytest

from conftest import DP, okul_basligi


@pytest.fixture
def okul(istemci, okul_olustur):
    """2 gün × 3 saat; Ayşe'nin 9-A'da 4 saat dersi var (müsait 6 saat)."""
    b = okul_basligi(okul_olustur("Müsaitlik Lisesi", gun_sayisi=2, gunluk_ders_saati=3))
    ayse = istemci.post("/api/ogretmenler", json={"ad": "Ayşe Yılmaz", "brans": "Matematik"}, headers=b).json()["id"]
    mat = istemci.post("/api/dersler", json={"ad": "Matematik", "kisa_ad": "MAT"}, headers=b).json()["id"]
    sube = istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=b).json()["id"]
    istemci.post(f"{DP}/atamalar", json={"sinif_id": sube, "ders_id": mat, "ogretmen_id": ayse, "haftalik_saat": 4}, headers=b)
    return {"b": b, "ayse": ayse}


def cizelge(istemci, okul) -> dict:
    yanit = istemci.get(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik", headers=okul["b"])
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def degistir(istemci, okul, *degisiklikler):
    return istemci.put(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik",
                       json={"degisiklikler": [{"gun": g, "saat": s, "durum": d} for g, s, d in degisiklikler]},
                       headers=okul["b"])


def test_bos_cizelge_ve_yuk(istemci, okul):
    c = cizelge(istemci, okul)
    assert c["hucreler"] == []
    assert c["yuk"] == {"ders_saati": 4, "musait_saat": 6, "kullanilabilir_saat": 6, "asim": False, "mesaj": None}


def test_toplu_degisiklik_tek_istekte(istemci, okul):
    yanit = degistir(istemci, okul, (0, 0, "gelemez"), (0, 1, "gelemez"), (1, 2, "tercih_etmez"))
    assert yanit.status_code == 200
    assert yanit.json()["hucreler"] == [
        {"gun": 0, "saat": 0, "durum": "gelemez"},
        {"gun": 0, "saat": 1, "durum": "gelemez"},
        {"gun": 1, "saat": 2, "durum": "tercih_etmez"},
    ]
    assert yanit.json()["yuk"]["musait_saat"] == 4  # tercih etmez müsait sayılır
    # Durum değişir; "musait" kaydı siler.
    yanit = degistir(istemci, okul, (0, 0, "tercih_etmez"), (0, 1, "musait"))
    assert yanit.json()["hucreler"] == [{"gun": 0, "saat": 0, "durum": "tercih_etmez"}, {"gun": 1, "saat": 2, "durum": "tercih_etmez"}]
    # Eski uç da aynı veriyi görür (dağılım özeti ve çözücü onu okur).
    assert len(istemci.get(f"{DP}/musaitlikler", headers=okul["b"]).json()) == 2


def test_biri_gecersizse_hicbiri_degismez(istemci, okul):
    degistir(istemci, okul, (0, 0, "gelemez"))
    yanit = degistir(istemci, okul, (0, 1, "gelemez"), (1, 0, "gelemez"), (1, 5, "gelemez"))  # 6. saat yok
    assert yanit.status_code == 422
    assert yanit.json()["detail"] == (
        "Gün/saat okulun ayarlarının dışında: 2. gün 6. saat (okulda 2 gün, günde 3 saat var). Hiçbir hücre değiştirilmedi.")
    assert cizelge(istemci, okul)["hucreler"] == [{"gun": 0, "saat": 0, "durum": "gelemez"}]


def test_ayni_hucre_iki_kez_reddedilir(istemci, okul):
    yanit = degistir(istemci, okul, (0, 0, "gelemez"), (0, 0, "musait"))
    assert yanit.status_code == 422 and "Aynı hücre iki kez" in yanit.json()["detail"]
    assert cizelge(istemci, okul)["hucreler"] == []


def test_kapasite_yukun_altina_dusunce_ayni_mesaj(istemci, okul):
    # Bir günün tamamı ve öteki günün bir saati gelemez: müsait 2 saat < 4 saat ders.
    yanit = degistir(istemci, okul, (0, 0, "gelemez"), (0, 1, "gelemez"), (0, 2, "gelemez"), (1, 0, "gelemez"))
    yuk = yanit.json()["yuk"]
    assert yuk["asim"] is True
    assert yuk["mesaj"] == "Ayşe Yılmaz'ın 4 saat dersi var, müsait olduğu 2 saat var."
    # Aynı mesaj program üretiminin ön kontrolünde de var (tek kaynak, ADR 0015).
    on_kontrol = istemci.get(f"{DP}/on-kontrol", headers=okul["b"]).json()["celiskiler"]
    assert yuk["mesaj"] in [c["mesaj"] for c in on_kontrol]


def test_baska_okulun_ogretmeni_404(istemci, okul, okul_olustur):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    assert istemci.get(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik", headers=b2).status_code == 404
    yanit = istemci.put(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik",
                        json={"degisiklikler": [{"gun": 0, "saat": 0, "durum": "gelemez"}]}, headers=b2)
    assert yanit.status_code == 404
    assert cizelge(istemci, okul)["hucreler"] == []
    assert istemci.get(f"{DP}/ogretmenler/{uuid.uuid4()}/musaitlik", headers=okul["b"]).status_code == 404


def test_bos_degisiklik_listesi_422(istemci, okul):
    yanit = istemci.put(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik", json={"degisiklikler": []}, headers=okul["b"])
    assert yanit.status_code == 422
