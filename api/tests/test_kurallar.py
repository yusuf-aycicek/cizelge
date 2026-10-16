"""Okul geneli kurallar ve önem seviyeleri (moduller/ders_programi/kurallar.py)."""

from __future__ import annotations

import uuid

import pytest
from cozucu.kisitlar import VARSAYILAN_KISITLAR

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.kurallar import KURAL_METINLERI, ONEM_KARSILIKLARI, ONEM_SEVIYELERI

ESNEKLER = {t.tur: t.agirlik for t in VARSAYILAN_KISITLAR if not t.zorunlu}


# --- karşılıklar: tek yer, çözücüyle tutarlı ------------------------------------------------

def test_onemli_cozucunun_varsayilan_agirligidir():
    assert set(ONEM_KARSILIKLARI) == set(ESNEKLER)
    for tur, agirlik in ESNEKLER.items():
        assert ONEM_KARSILIKLARI[tur]["onemli"] == agirlik, tur


def test_seviyeler_artan_ve_sifirdan_buyuk():
    for tur, karsilik in ONEM_KARSILIKLARI.items():
        degerler = [karsilik[s] for s in ONEM_SEVIYELERI]
        assert 0 < degerler[0] < degerler[1] < degerler[2], tur


def test_her_varsayilan_kuralin_metni_var():
    assert set(KURAL_METINLERI) == {t.tur for t in VARSAYILAN_KISITLAR}


# --- uçlar ------------------------------------------------------------------------------------

@pytest.fixture
def b(okul_olustur):
    return okul_basligi(okul_olustur("Kural Lisesi"))


def kurallar(istemci, b) -> dict[str, dict]:
    return {k["tur"]: k for k in istemci.get(f"{DP}/kurallar", headers=b).json()}


def test_varsayilanlar(istemci, b):
    k = kurallar(istemci, b)
    assert list(k) == list(KURAL_METINLERI)
    assert k["gunluk_ders_siniri"]["parametreler"] == {"n": 2} and k["gunluk_ders_siniri"]["seviye"] is None
    assert k["ogretmen_gunluk_siniri"]["parametreler"] == {"m": 8}
    assert k["bos_gun"]["parametreler"] == {"hedef_bos_gun": 1}
    assert all(x["varsayilan"] for x in k.values())
    assert {t: x["seviye"] for t, x in k.items() if not x["zorunlu"]} == {t: "onemli" for t in ESNEKLER}
    assert k["sinif_boslugu"]["ad"] == "Sınıfların boş saati olmasın"


def test_seviye_secilince_agirlik_karsiligi_kaydedilir_ve_cozucuye_gider(istemci, b, oturum_fabrikasi):
    yanit = istemci.put(f"{DP}/kurallar/bos_gun", json={"seviye": "cok_onemli"}, headers=b)
    assert yanit.status_code == 200
    assert (yanit.json()["seviye"], yanit.json()["agirlik"], yanit.json()["varsayilan"]) == ("cok_onemli", 10, False)
    assert yanit.json()["parametreler"] == {"hedef_bos_gun": 1}  # dokunulmadı

    okul_id = istemci.get("/api/okul", headers=b).json()["id"]
    with okul_oturumu(oturum_fabrikasi, uuid.UUID(okul_id)) as o:
        girdi = cozum_girdisi_olustur(o)
    assert [(t.tur, t.agirlik, t.zorunlu) for t in girdi.kisitlar] == [("bos_gun", 10, False)]


def test_parametre_degisir_ve_varsayilana_donulur(istemci, b):
    yanit = istemci.put(f"{DP}/kurallar/gunluk_ders_siniri", json={"parametreler": {"n": 3}}, headers=b)
    assert yanit.json()["parametreler"] == {"n": 3}
    assert len(istemci.get(f"{DP}/kisitlar", headers=b).json()) == 1
    yanit = istemci.delete(f"{DP}/kurallar/gunluk_ders_siniri", headers=b)
    assert yanit.json()["parametreler"] == {"n": 2} and yanit.json()["varsayilan"] is True
    assert istemci.get(f"{DP}/kisitlar", headers=b).json() == []


@pytest.mark.parametrize(("tur", "govde", "durum", "mesaj"), [
    ("gunluk_ders_siniri", {"parametreler": {"n": 0}}, 422, "Aynı dersin günlük sınırı: en az 1 olmalı"),
    ("bos_gun", {"parametreler": {"hedef_bos_gun": -1}}, 422, "Öğretmene boş gün: en az 0 olmalı"),
    ("gunluk_ders_siniri", {"parametreler": {"x": 1}}, 422, "Bu kuralın ayarları: n"),
    ("gunluk_ders_siniri", {"seviye": "onemli"}, 422, "Zorunlu kuralların önem seviyesi yoktur"),
    ("uydurma", {"seviye": "onemli"}, 404, "Kural bulunamadı"),
])
def test_gecersiz_ayarlar_anlasilir_hata(istemci, b, tur, govde, durum, mesaj):
    yanit = istemci.put(f"{DP}/kurallar/{tur}", json=govde, headers=b)
    assert (yanit.status_code, yanit.json()["detail"]) == (durum, mesaj)


def test_elle_girilmis_agirlik_ozel_gorunur(istemci, b):
    istemci.post(f"{DP}/kisitlar", json={"tur": "tercih_etmez", "zorunlu": False, "agirlik": 7}, headers=b)
    assert kurallar(istemci, b)["tercih_etmez"]["seviye"] == "ozel"
