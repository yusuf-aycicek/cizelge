"""Kuralların özel ayarları: öğretmene, derse, şubeye özel değer (ADR 0016, K1)."""

from __future__ import annotations

import uuid

import pytest
from cozucu.kapsam import OKUL, Kapsam
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur

M = "ogretmen_gunluk_siniri"
N = "gunluk_ders_siniri"


@pytest.fixture
def okul(istemci, okul_olustur):
    b = okul_basligi(okul_olustur("Özel Ayar Lisesi"))
    ayse = istemci.post("/api/ogretmenler", json={"ad": "Ayşe Yılmaz", "brans": "Matematik"}, headers=b).json()["id"]
    mat = istemci.post("/api/dersler", json={"ad": "Matematik", "kisa_ad": "MAT"}, headers=b).json()["id"]
    sube = istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=b).json()["id"]
    return {"b": b, "ayse": ayse, "mat": mat, "sube": sube}


def kural(istemci, b, tur) -> dict:
    return next(k for k in istemci.get(f"{DP}/kurallar", headers=b).json() if k["tur"] == tur)


def ozel_yaz(istemci, b, tur, kapsam, parametreler):
    return istemci.put(f"{DP}/kurallar/{tur}/ozel", json={"kapsam": kapsam, "parametreler": parametreler}, headers=b)


def test_kurallar_desteklenen_kapsamlari_bildirir(istemci, okul):
    k = {x["tur"]: x for x in istemci.get(f"{DP}/kurallar", headers=okul["b"]).json()}
    assert k[N]["kapsamlar"] == ["ders", "sube", "sube_grubu"]
    assert k[M]["kapsamlar"] == ["ogretmen"]
    assert k["sinif_boslugu"]["kapsamlar"] == []
    assert all(x["ozel_ayarlar"] == [] for x in k.values())


def test_ogretmene_ozel_ayar_eklenir_guncellenir_kaldirilir(istemci, okul):
    b = okul["b"]
    yanit = ozel_yaz(istemci, b, M, {"ogretmen_id": okul["ayse"]}, {"m": 6})
    assert yanit.status_code == 200
    assert yanit.json()["parametreler"] == {"m": 8}  # okul değeri değişmedi
    assert yanit.json()["varsayilan"] is True
    assert yanit.json()["ozel_ayarlar"] == [{
        "kapsam": {"ogretmen_id": okul["ayse"], "ders_id": None, "sinif_id": None, "sube_grubu_id": None},
        "ad": "Ayşe Yılmaz",
        "parametreler": {"m": 6},
    }]

    # Aynı kapsama ikinci yazım günceller, yeni satır açmaz.
    ozel_yaz(istemci, b, M, {"ogretmen_id": okul["ayse"]}, {"m": 5})
    ozeller = kural(istemci, b, M)["ozel_ayarlar"]
    assert [o["parametreler"] for o in ozeller] == [{"m": 5}]

    yanit = istemci.delete(f"{DP}/kurallar/{M}/ozel", params={"ogretmen_id": okul["ayse"]}, headers=b)
    assert yanit.status_code == 200 and yanit.json()["ozel_ayarlar"] == []
    # Olmayanı kaldırmak hata değildir.
    assert istemci.delete(f"{DP}/kurallar/{M}/ozel", params={"ogretmen_id": okul["ayse"]}, headers=b).status_code == 200


def test_ders_sube_ve_ders_sube_birlikte_adlariyla_listelenir(istemci, okul):
    b = okul["b"]
    ozel_yaz(istemci, b, N, {"ders_id": okul["mat"]}, {"n": 3})
    ozel_yaz(istemci, b, N, {"sinif_id": okul["sube"]}, {"n": 1})
    ozel_yaz(istemci, b, N, {"ders_id": okul["mat"], "sinif_id": okul["sube"]}, {"n": 2})
    assert [(o["ad"], o["parametreler"]["n"]) for o in kural(istemci, b, N)["ozel_ayarlar"]] == [
        ("9-A", 1), ("9-A · Matematik", 2), ("Matematik", 3),
    ]


def test_okul_degeri_degisince_ozel_ayar_yerinde_kalir(istemci, okul):
    b = okul["b"]
    ozel_yaz(istemci, b, M, {"ogretmen_id": okul["ayse"]}, {"m": 6})
    istemci.put(f"{DP}/kurallar/{M}", json={"parametreler": {"m": 7}}, headers=b)
    yanit = istemci.delete(f"{DP}/kurallar/{M}", headers=b)  # okul değerini varsayılana döndür
    assert yanit.json()["parametreler"] == {"m": 8}
    assert [o["parametreler"] for o in yanit.json()["ozel_ayarlar"]] == [{"m": 6}]


@pytest.mark.parametrize(("tur", "kapsam", "parametreler", "mesaj"), [
    ("sinif_boslugu", {"ogretmen_id": "ayse"}, {}, "\"Sınıfların boş saati olmasın\" kuralı öğretmene özel ayarlanamaz"),
    (N, {"ogretmen_id": "ayse"}, {"n": 3}, "\"Aynı dersin günlük sınırı\" kuralı öğretmene özel ayarlanamaz"),
    (M, {"ders_id": "mat"}, {"m": 6}, "\"Öğretmenin günlük ders sınırı\" kuralı derse özel ayarlanamaz"),
    (M, {"ogretmen_id": "ayse", "ders_id": "mat"}, {"m": 6}, "\"Öğretmenin günlük ders sınırı\" kuralı derse özel ayarlanamaz"),
    (M, {}, {"m": 6}, "Özel ayar için bir öğretmen, ders, şube ya da şube grubu seçin"),
    (M, {"ogretmen_id": "ayse"}, {"m": 0}, "Öğretmenin günlük ders sınırı: en az 1 olmalı"),
    (M, {"ogretmen_id": "ayse"}, {"n": 3}, "Bu kuralın ayarları: m"),
    (M, {"ogretmen_id": "yok"}, {"m": 6}, "Öğretmen bu okulda bulunamadı"),
])
def test_gecersiz_ozel_ayar_anlasilir_hatayla_reddedilir(istemci, okul, tur, kapsam, parametreler, mesaj):
    kimlikler = {**okul, "yok": str(uuid.uuid4())}
    kapsam = {k: kimlikler[v] for k, v in kapsam.items()}
    yanit = ozel_yaz(istemci, okul["b"], tur, kapsam, parametreler)
    assert (yanit.status_code, yanit.json()["detail"]) == (422, mesaj)


def test_bilinmeyen_kural_404(istemci, okul):
    assert ozel_yaz(istemci, okul["b"], "uydurma", {"ogretmen_id": okul["ayse"]}, {"m": 6}).status_code == 404


def test_baska_okulun_ogretmenine_ozel_ayar_yazilamaz(istemci, okul, okul_olustur):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    yanit = ozel_yaz(istemci, b2, M, {"ogretmen_id": okul["ayse"]}, {"m": 6})
    assert (yanit.status_code, yanit.json()["detail"]) == (422, "Öğretmen bu okulda bulunamadı")
    # Birinci okulun özel ayarı ikinci okulda görünmez, oradan silinemez.
    ozel_yaz(istemci, okul["b"], M, {"ogretmen_id": okul["ayse"]}, {"m": 6})
    assert kural(istemci, b2, M)["ozel_ayarlar"] == []
    istemci.delete(f"{DP}/kurallar/{M}/ozel", params={"ogretmen_id": okul["ayse"]}, headers=b2)
    assert len(kural(istemci, okul["b"], M)["ozel_ayarlar"]) == 1


def test_ogretmen_silinince_ozel_ayari_da_silinir(istemci, okul):
    b = okul["b"]
    ozel_yaz(istemci, b, M, {"ogretmen_id": okul["ayse"]}, {"m": 6})
    assert istemci.delete(f"/api/ogretmenler/{okul['ayse']}", headers=b).status_code == 204
    assert kural(istemci, b, M)["ozel_ayarlar"] == []


def test_ders_ve_sube_silinince_ozel_ayarlari_da_silinir(istemci, okul):
    b = okul["b"]
    ozel_yaz(istemci, b, N, {"ders_id": okul["mat"]}, {"n": 3})
    ozel_yaz(istemci, b, N, {"sinif_id": okul["sube"]}, {"n": 1})
    assert istemci.delete(f"/api/dersler/{okul['mat']}", headers=b).status_code == 204
    assert istemci.delete(f"/api/siniflar/{okul['sube']}", headers=b).status_code == 204
    assert kural(istemci, b, N)["ozel_ayarlar"] == []


def test_ozel_ayarlar_cozucuye_kapsamiyla_gider(istemci, okul, oturum_fabrikasi):
    b = okul["b"]
    istemci.put(f"{DP}/kurallar/{M}", json={"parametreler": {"m": 7}}, headers=b)
    ozel_yaz(istemci, b, M, {"ogretmen_id": okul["ayse"]}, {"m": 6})
    ozel_yaz(istemci, b, N, {"ders_id": okul["mat"], "sinif_id": okul["sube"]}, {"n": 3})
    okul_id = istemci.get("/api/okul", headers=b).json()["id"]
    with okul_oturumu(oturum_fabrikasi, uuid.UUID(okul_id)) as o:
        girdi = cozum_girdisi_olustur(o)
    assert sorted(((t.tur, t.kapsam, t.parametreler) for t in girdi.kisitlar), key=str) == sorted([
        (M, OKUL, {"m": 7}),
        (M, Kapsam(ogretmen_id=okul["ayse"]), {"m": 6}),
        (N, Kapsam(ders_id=okul["mat"], sinif_id=okul["sube"]), {"n": 3}),
    ], key=str)
    assert girdi.parametre(M, "m", 8, ogretmen_id=okul["ayse"]) == 6


# --- veritabanı kısıtları: uygulama atlansa da korur ---------------------------------------


def _okul_id(istemci, b) -> uuid.UUID:
    return uuid.UUID(istemci.get("/api/okul", headers=b).json()["id"])


def _ekle(oturum, okul_id, **sutunlar):
    alanlar = {"tur": M, "zorunlu": True, "agirlik": 1, "parametreler": "{}", **sutunlar}
    adlar = ", ".join(["okul_id", *alanlar])
    yerler = ", ".join([":okul_id", *(f":{a}" for a in alanlar)])
    oturum.execute(text(f"INSERT INTO kisit (id, {adlar}) VALUES (gen_random_uuid(), {yerler})"),
                   {"okul_id": okul_id, **alanlar})


def test_veritabani_ogretmen_kapsamini_ders_ile_birlestirmez(istemci, okul, oturum_fabrikasi):
    okul_id = _okul_id(istemci, okul["b"])
    with okul_oturumu(oturum_fabrikasi, okul_id) as o, pytest.raises(IntegrityError, match="ck_kisit_kapsam_ailesi"):
        _ekle(o, okul_id, ogretmen_id=okul["ayse"], ders_id=okul["mat"])


def test_veritabani_ayni_kapsamda_iki_tanimi_reddeder(istemci, okul, oturum_fabrikasi):
    okul_id = _okul_id(istemci, okul["b"])
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        _ekle(o, okul_id)  # okul geneli: üç kapsam sütunu NULL
        with pytest.raises(IntegrityError, match="uq_kisit_kapsam"):
            with o.begin_nested():
                _ekle(o, okul_id)  # NULLS NOT DISTINCT: ikinci okul geneli satır da reddedilir
        _ekle(o, okul_id, ogretmen_id=okul["ayse"])
        with pytest.raises(IntegrityError, match="uq_kisit"):
            _ekle(o, okul_id, ogretmen_id=okul["ayse"])


def test_veritabani_baska_okulun_ogretmenine_baglamaz(istemci, okul, okul_olustur, oturum_fabrikasi):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    okul2 = _okul_id(istemci, b2)
    with okul_oturumu(oturum_fabrikasi, okul2) as o, pytest.raises(IntegrityError, match="fk_kisit_okul_id_ogretmen_id_ogretmen"):
        _ekle(o, okul2, ogretmen_id=okul["ayse"])
