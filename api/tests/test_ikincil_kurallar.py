"""İkincil kurallar (K6): saat tercihi, günde en az ders, günlere yayılım; API'de özel ayarlarıyla."""

from __future__ import annotations

import pytest

from conftest import DP, okul_basligi
from test_ozel_ayarlar import kural, ozel_yaz

SAAT = "ders_saat_tercihi"
EN_AZ = "gunluk_en_az_ders"
YAYILIM = "ders_yayilimi"


@pytest.fixture
def okul(istemci, okul_olustur):
    b = okul_basligi(okul_olustur("İkincil Kural Lisesi"))
    ayse = istemci.post("/api/ogretmenler", json={"ad": "Ayşe Yılmaz", "brans": "Matematik"}, headers=b).json()["id"]
    mat = istemci.post("/api/dersler", json={"ad": "Matematik", "kisa_ad": "MAT"}, headers=b).json()["id"]
    sube = istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=b).json()["id"]
    return {"b": b, "ayse": ayse, "mat": mat, "sube": sube}


def test_kurallar_listede_kapsamlariyla(istemci, okul):
    k = {x["tur"]: x for x in istemci.get(f"{DP}/kurallar", headers=okul["b"]).json()}
    assert (k[SAAT]["kapsamlar"], k[SAAT]["zorunlu_eksenler"], k[SAAT]["parametreler"]) == (["ders", "sube", "sube_grubu"], ["ders"], {})
    assert (k[EN_AZ]["kapsamlar"], k[EN_AZ]["parametreler"], k[EN_AZ]["seviye"]) == (["ogretmen"], {"k": 2}, "onemli")
    assert (k[YAYILIM]["kapsamlar"], k[YAYILIM]["parametreler"]) == (["ders", "sube", "sube_grubu"], {"yayilsin": True})


def test_ders_saat_tercihi_ozel_ayari(istemci, okul):
    # Matematik sabah (ilk dört saat); 9-A'da 5. saatten de kaçınsın. Saatler sıralanır, tekrar atılır.
    yanit = ozel_yaz(istemci, okul["b"], SAAT, {"ders_id": okul["mat"]}, {"saatler": [3, 0, 1, 2, 2]})
    assert yanit.status_code == 200, yanit.json()
    yanit = ozel_yaz(istemci, okul["b"], SAAT, {"ders_id": okul["mat"], "sinif_id": okul["sube"]}, {"kacin": [4]})
    assert yanit.status_code == 200, yanit.json()
    ozeller = {o["ad"]: o["parametreler"] for o in kural(istemci, okul["b"], SAAT)["ozel_ayarlar"]}
    assert ozeller == {"Matematik": {"saatler": [0, 1, 2, 3]}, "9-A · Matematik": {"kacin": [4]}}


@pytest.mark.parametrize(("kapsam", "parametreler", "mesaj"), [
    ({"sinif_id": "sube"}, {"saatler": [0]}, "'ders_saat_tercihi' özel ayarında ders belirtilmeli"),
    ({"ders_id": "mat"}, {"saatler": [], "kacin": []}, "Dersin saat tercihi için istenen ya da istenmeyen en az bir saat seçin"),
    ({"ders_id": "mat"}, {"saatler": [-1]}, "Saatler 1. ders 0 olmak üzere sayı listesi olmalı, ör. [0, 1, 2]"),
    ({"ders_id": "mat"}, {"sabah": True}, "Bu kuralın ayarları: kacin, saatler"),
])
def test_gecersiz_saat_tercihi(istemci, okul, kapsam, parametreler, mesaj):
    kapsam = {k: okul[v] for k, v in kapsam.items()}
    yanit = ozel_yaz(istemci, okul["b"], SAAT, kapsam, parametreler)
    assert (yanit.status_code, yanit.json()["detail"]) == (422, mesaj)


def test_en_az_ders_ve_yayilim(istemci, okul):
    b = okul["b"]
    assert istemci.put(f"{DP}/kurallar/{EN_AZ}", json={"parametreler": {"k": 3}}, headers=b).status_code == 200
    assert ozel_yaz(istemci, b, EN_AZ, {"ogretmen_id": okul["ayse"]}, {"k": 1}).status_code == 200
    assert ozel_yaz(istemci, b, YAYILIM, {"ders_id": okul["mat"]}, {"yayilsin": False}).status_code == 200
    yanit = ozel_yaz(istemci, b, YAYILIM, {"ders_id": okul["mat"]}, {"yayilsin": 0})
    assert (yanit.status_code, yanit.json()["detail"]) == (422, "yayilsin açık ya da kapalı (true/false) olmalı")
    yanit = istemci.put(f"{DP}/kurallar/{YAYILIM}", json={"seviye": "cok_onemli"}, headers=b).json()
    assert yanit["agirlik"] == 5
    assert kural(istemci, b, EN_AZ)["parametreler"] == {"k": 3}
