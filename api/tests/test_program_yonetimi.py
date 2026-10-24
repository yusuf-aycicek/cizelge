"""Programlar (6.3): yeniden adlandırma, silme, iki program farkı, "eski verilerle üretildi"."""

from __future__ import annotations

from conftest import DP
from test_program_uretimi import SahteCozucu, getir, okul, uret, worker_calistir  # noqa: F401  (okul: fikstür)


def hazir(istemci, okul, oturum_fabrikasi, kuyruk, **govde) -> str:
    program_id = uret(istemci, okul, **govde).json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, program_id)
    assert getir(istemci, okul, program_id)["durum"] == "hazir"
    return program_id


def test_program_yeniden_adlandirilir_ve_silinir(istemci, okul, kuyruk, oturum_fabrikasi):
    b = okul["baslik"]
    p1 = hazir(istemci, okul, oturum_fabrikasi, kuyruk, ad="Eylül")
    yanit = istemci.patch(f"{DP}/programlar/{p1}", json={"ad": "  Güz dönemi  "}, headers=b)
    assert yanit.status_code == 200 and yanit.json()["ad"] == "Güz dönemi"
    assert istemci.patch(f"{DP}/programlar/{p1}", json={"ad": ""}, headers=b).status_code == 422

    # Bu programı temel alan program silinmez; bağı kopar.
    p2 = hazir(istemci, okul, oturum_fabrikasi, kuyruk, ad="Ekim", temel_program_id=p1)
    assert istemci.delete(f"{DP}/programlar/{p1}", headers=b).status_code == 204
    assert istemci.get(f"{DP}/programlar/{p1}", headers=b).status_code == 404
    assert getir(istemci, okul, p2)["temel_program_id"] is None
    assert istemci.get(f"{DP}/programlar/{p2}/yerlesimler", headers=b).json() != []


def test_uretimi_suren_program_silinemez(istemci, okul, kuyruk):
    p = uret(istemci, okul).json()["id"]
    yanit = istemci.delete(f"{DP}/programlar/{p}", headers=okul["baslik"])
    assert yanit.status_code == 409 and "bitmesini bekleyin" in yanit.json()["detail"]


def test_baska_okulun_programi_adlandirilamaz_silinemez(istemci, okul, kuyruk, oturum_fabrikasi, okul_olustur):
    from conftest import okul_basligi

    p = hazir(istemci, okul, oturum_fabrikasi, kuyruk)
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    assert istemci.patch(f"{DP}/programlar/{p}", json={"ad": "x"}, headers=b2).status_code == 404
    assert istemci.delete(f"{DP}/programlar/{p}", headers=b2).status_code == 404
    assert istemci.get(f"{DP}/programlar/{p}/fark", headers=b2).status_code == 404
    assert getir(istemci, okul, p)["ad"] == "Güz"


def test_fark_degisen_hucreleri_ve_subeleri_soyler(istemci, okul, kuyruk, oturum_fabrikasi):
    b, h = okul["baslik"], okul["harita"]
    p1 = hazir(istemci, okul, oturum_fabrikasi, kuyruk, ad="Eylül")
    yanit = istemci.get(f"{DP}/programlar/{p1}/fark", headers=b)
    assert yanit.status_code == 422 and "temel almadan" in yanit.json()["detail"]

    # Veri aynıyken temel alınarak üretilen program hiç değişmez.
    p2 = hazir(istemci, okul, oturum_fabrikasi, kuyruk, ad="Ekim", temel_program_id=p1)
    fark = istemci.get(f"{DP}/programlar/{p2}/fark", headers=b).json()
    assert (fark["ile_id"], fark["ile_ad"], fark["degisen"], fark["subeler"], fark["hucreler"]) == (p1, "Eylül", 0, [], [])

    # Ayşe ders verdiği bir gün bütün gün gelemezse o günkü dersleri yer değiştirir.
    ayseninkiler = {a["id"] for a in istemci.get(f"{DP}/atamalar", headers=b).json() if a["ogretmen_id"] == h["o-ayse"]}
    dersleri = [y for y in istemci.get(f"{DP}/programlar/{p2}/yerlesimler", headers=b).json() if y["ders_atama_id"] in ayseninkiler]
    gun = dersleri[0]["gun"]
    ayse_gun = [y for y in dersleri if y["gun"] == gun]
    for s in range(6):
        istemci.post(f"{DP}/musaitlikler", json={"ogretmen_id": h["o-ayse"], "gun": gun, "saat": s, "durum": "gelemez"}, headers=b)
    p3 = hazir(istemci, okul, oturum_fabrikasi, kuyruk, ad="Kasım", temel_program_id=p2)
    fark = istemci.get(f"{DP}/programlar/{p3}/fark", headers=b).json()
    assert fark["degisen"] >= len(ayse_gun) > 0
    assert fark["degisen"] == getir(istemci, okul, p3)["olcumler"]["degisen_yerlesim"]
    assert sum(s["sayi"] for s in fark["subeler"]) == fark["degisen"] == len(fark["hucreler"])
    assert {s["ad"] for s in fark["subeler"]} <= {"9-A", "9-B", "10-A"}
    # Herhangi iki program da karşılaştırılabilir.
    assert istemci.get(f"{DP}/programlar/{p3}/fark", params={"ile": p1}, headers=b).json()["ile_ad"] == "Eylül"


def test_veri_degisince_program_eski_veriyle_uretildi_sayilir(istemci, okul, kuyruk, oturum_fabrikasi):
    b, h = okul["baslik"], okul["harita"]
    p1 = hazir(istemci, okul, oturum_fabrikasi, kuyruk)
    assert getir(istemci, okul, p1)["eski_veri"] is False
    # Üretilmekte olan ya da başarısız programda bilgi yok.
    p_bekleyen = uret(istemci, okul).json()["id"]
    assert getir(istemci, okul, p_bekleyen)["eski_veri"] is None
    worker_calistir(oturum_fabrikasi, kuyruk, p_bekleyen)

    istemci.post(f"{DP}/musaitlikler", json={"ogretmen_id": h["o-ayse"], "gun": 4, "saat": 5, "durum": "tercih_etmez"}, headers=b)
    assert getir(istemci, okul, p1)["eski_veri"] is True
    liste = {p["id"]: p for p in istemci.get(f"{DP}/programlar", headers=b).json()}
    assert liste[p1]["eski_veri"] is True and liste[p_bekleyen]["eski_veri"] is True

    # Temel programın silinmesi okulun verisini değiştirmez: uyarı çıkmaz.
    p2 = hazir(istemci, okul, oturum_fabrikasi, kuyruk, temel_program_id=p1)
    istemci.delete(f"{DP}/programlar/{p1}", headers=b)
    assert getir(istemci, okul, p2)["eski_veri"] is False
