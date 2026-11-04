"""Ders dağılımı: yük özeti (erken uyarılar) ve toplu öğretmen atama.

Özet, program üretiminin ön kontroluyla aynı hesabı kullanır (cozucu.yuk, ADR 0015). Bunu
`test_ozet_on_kontrolle_ayni_mesajlari_verir` doğrudan karşılaştırarak denetler.
"""

from __future__ import annotations

import uuid

import pytest
from cozucu.on_kontrol import on_kontrol

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur


@pytest.fixture
def okul(istemci, okul_olustur):
    """5 gün × 6 saat. 9-A, 9-B, 9-C (seviye 9); Matematik, Fizik; Ayşe, Zeynep, Ali."""
    okul_id = okul_olustur("A Lisesi", gun_sayisi=5, gunluk_ders_saati=6)
    b = okul_basligi(okul_id)

    def ekle(yol, govde):
        yanit = istemci.post(yol, json=govde, headers=b)
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    kim = {"okul": okul_id, "baslik": b}
    for s in ("9-A", "9-B", "9-C"):
        kim[s] = ekle("/api/siniflar", {"ad": s, "seviye": 9})
    kim["mat"] = ekle("/api/dersler", {"ad": "Matematik"})
    kim["fiz"] = ekle("/api/dersler", {"ad": "Fizik"})
    kim["ayse"] = ekle("/api/ogretmenler", {"ad": "Ayşe Yılmaz", "brans": "Matematik"})
    kim["zeynep"] = ekle("/api/ogretmenler", {"ad": "Zeynep Demir", "brans": "Fizik"})
    kim["ali"] = ekle("/api/ogretmenler", {"ad": "Ali Çelik"})
    kim["ekle"] = ekle
    return kim


def atama(okul, sinif, ders, ogretmen, saat):
    return okul["ekle"](f"{DP}/atamalar", {"sinif_id": okul[sinif], "ders_id": okul[ders],
                                          "ogretmen_id": okul[ogretmen] if ogretmen else None,
                                          "haftalik_saat": saat})


def gelemez(okul, ogretmen, gunler, saatler=range(6)):
    for g in gunler:
        for s in saatler:
            okul["ekle"](f"{DP}/musaitlikler", {"ogretmen_id": okul[ogretmen], "gun": g, "saat": s,
                                               "durum": "gelemez"})


def ozet(istemci, okul) -> dict:
    yanit = istemci.get(f"{DP}/dagilim-ozeti", headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def ogretmen(oz, okul, ad) -> dict:
    return next(o for o in oz["ogretmenler"] if o["ogretmen_id"] == okul[ad])


def sinif(oz, okul, ad) -> dict:
    return next(s for s in oz["siniflar"] if s["sinif_id"] == okul[ad])


# --- özet ---------------------------------------------------------------------------------


def test_bos_okulun_ozeti(istemci, okul):
    oz = ozet(istemci, okul)
    assert oz["haftalik_kapasite"] == 30
    assert oz["ogretmen_gunluk_siniri"] == 6  # varsayılan 8, ama gün 6 saat
    assert oz["ogretmensiz_atama"] == 0
    assert len(oz["ogretmenler"]) == 3 and len(oz["siniflar"]) == 3
    assert ogretmen(oz, okul, "ali") == {"ogretmen_id": okul["ali"], "ders_saati": 0, "musait_saat": 30,
                                          "kullanilabilir_saat": 30, "hedefli_kapasite": 24, "asim": False, "mesaj": None,
                                          "yuk_uyarisi": None}


def test_ogretmen_asimi_ve_ogretmensiz_atama(istemci, okul):
    atama(okul, "9-A", "mat", "ayse", 6)
    atama(okul, "9-B", "mat", "ayse", 6)
    atama(okul, "9-A", "fiz", "zeynep", 3)
    atama(okul, "9-B", "fiz", None, 3)
    gelemez(okul, "ayse", [0, 1, 2, 3])  # yalnızca cuma müsait: 6 saat

    oz = ozet(istemci, okul)
    ayse = ogretmen(oz, okul, "ayse")
    assert (ayse["ders_saati"], ayse["musait_saat"], ayse["kullanilabilir_saat"], ayse["asim"]) == (12, 6, 6, True)
    assert ayse["mesaj"] == "Ayşe Yılmaz'ın 12 saat dersi var, müsait olduğu 6 saat var."
    assert ogretmen(oz, okul, "zeynep")["asim"] is False
    assert oz["ogretmensiz_atama"] == 1
    assert sinif(oz, okul, "9-B")["ogretmensiz_atama"] == 1
    assert sinif(oz, okul, "9-B")["ders_saati"] == 9
    assert sinif(oz, okul, "9-A")["ogretmensiz_atama"] == 0


def test_sinif_asimi(istemci, okul):
    atama(okul, "9-A", "mat", "ayse", 6)
    atama(okul, "9-A", "fiz", "zeynep", 25)
    s = sinif(ozet(istemci, okul), okul, "9-A")
    assert (s["ders_saati"], s["kapasite"], s["asim"]) == (31, 30, True)
    assert s["mesaj"] == "9-A sınıfının haftada 31 saat dersi var, haftalık kapasite 30 saat (5 gün × 6 saat)."


def test_gunluk_sinir_kuralı_ozete_yansir(istemci, okul):
    yanit = istemci.put(f"{DP}/kurallar/ogretmen_gunluk_siniri", json={"parametreler": {"m": 4}},
                        headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    oz = ozet(istemci, okul)
    assert oz["ogretmen_gunluk_siniri"] == 4
    assert ogretmen(oz, okul, "ali")["kullanilabilir_saat"] == 20


def test_ozet_on_kontrolle_ayni_mesajlari_verir(istemci, okul, oturum_fabrikasi):
    """Tek kaynak: özetteki aşım mesajları, program üretiminin ön kontrolünün kapasite sorunlarıyla
    birebir aynıdır."""
    atama(okul, "9-A", "mat", "ayse", 6)
    atama(okul, "9-B", "mat", "ayse", 6)
    atama(okul, "9-A", "fiz", "zeynep", 25)
    gelemez(okul, "ayse", [0, 1, 2])
    gelemez(okul, "ayse", [3], range(4))  # müsait: perşembe 2 + cuma 6 = 8 saat
    istemci.put(f"{DP}/kurallar/ogretmen_gunluk_siniri", json={"parametreler": {"m": 4}}, headers=okul["baslik"])
    oz = ozet(istemci, okul)
    ozetteki = {x["mesaj"] for x in oz["ogretmenler"] + oz["siniflar"] if x["asim"]}
    assert ogretmen(oz, okul, "ayse")["mesaj"] == (
        "Ayşe Yılmaz'ın 12 saat dersi var. Müsait olduğu 8 saatin, günde en fazla 4 saat derse "
        "girebildiği için yalnızca 6 saati kullanılabilir.")

    with okul_oturumu(oturum_fabrikasi, uuid.UUID(okul["okul"])) as oturum:
        sorunlar = on_kontrol(cozum_girdisi_olustur(oturum))
    on_kontroldeki = {s.mesaj for s in sorunlar if s.tur in ("ogretmen_kapasitesi", "sinif_kapasitesi")}
    assert len(ozetteki) == 3  # Ayşe, Zeynep (25 > 5 × 4) ve 9-A
    assert ozetteki == on_kontroldeki


def test_ozet_yalnizca_kendi_okulunu_gosterir(istemci, okul, okul_olustur):
    atama(okul, "9-A", "mat", "ayse", 6)
    b = okul_basligi(okul_olustur("B Lisesi"))
    yanit = istemci.get(f"{DP}/dagilim-ozeti", headers=b)
    assert yanit.status_code == 200
    assert yanit.json()["ogretmenler"] == [] and yanit.json()["siniflar"] == []


# --- toplu öğretmen atama -------------------------------------------------------------------


def toplu(istemci, okul, idler, ogretmen_id):
    return istemci.post(f"{DP}/atamalar/toplu-ogretmen", headers=okul["baslik"],
                        json={"atama_idleri": idler, "ogretmen_id": ogretmen_id})


def atamalar(istemci, okul) -> dict[str, str | None]:
    return {a["id"]: a["ogretmen_id"] for a in istemci.get(f"{DP}/atamalar", headers=okul["baslik"]).json()}


def test_toplu_ogretmen_atama(istemci, okul):
    idler = [atama(okul, s, "mat", None, 5) for s in ("9-A", "9-B", "9-C")]
    yanit = toplu(istemci, okul, idler, okul["ayse"])
    assert yanit.status_code == 200, yanit.text
    assert sorted(a["id"] for a in yanit.json()) == sorted(idler)
    assert set(atamalar(istemci, okul).values()) == {okul["ayse"]}
    assert ogretmen(ozet(istemci, okul), okul, "ayse")["ders_saati"] == 15

    yanit = toplu(istemci, okul, idler[:2], None)  # öğretmeni boşaltma
    assert yanit.status_code == 200
    assert atamalar(istemci, okul) == {idler[0]: None, idler[1]: None, idler[2]: okul["ayse"]}


def test_toplu_atamada_ayni_kimlik_iki_kez_sorun_degil(istemci, okul):
    a = atama(okul, "9-A", "mat", None, 5)
    yanit = toplu(istemci, okul, [a, a], okul["ayse"])
    assert yanit.status_code == 200 and len(yanit.json()) == 1


def test_toplu_atama_hepsi_ya_da_hicbiri(istemci, okul, okul_olustur):
    """Atamalardan biri bu okulda yoksa (başka okulun ya da hiç olmayan) hiçbiri değişmez."""
    a = atama(okul, "9-A", "mat", None, 5)
    b = okul_basligi(okul_olustur("B Lisesi"))
    b_sinif = istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=b).json()["id"]
    b_ders = istemci.post("/api/dersler", json={"ad": "Matematik"}, headers=b).json()["id"]
    b_atama = istemci.post(f"{DP}/atamalar", headers=b, json={"sinif_id": b_sinif, "ders_id": b_ders,
                                                               "haftalik_saat": 5}).json()["id"]
    for yabanci in (b_atama, str(uuid.uuid4())):
        yanit = toplu(istemci, okul, [a, yabanci], okul["ayse"])
        assert yanit.status_code == 404
        assert yanit.json()["detail"] == "Ders ataması bulunamadı"
    assert atamalar(istemci, okul) == {a: None}
    assert istemci.get(f"{DP}/atamalar", headers=b).json()[0]["ogretmen_id"] is None


def test_toplu_atamada_baska_okulun_ogretmeni_reddedilir(istemci, okul, okul_olustur):
    a = atama(okul, "9-A", "mat", None, 5)
    b = okul_basligi(okul_olustur("B Lisesi"))
    b_ogretmen = istemci.post("/api/ogretmenler", json={"ad": "B'nin öğretmeni"}, headers=b).json()["id"]
    yanit = toplu(istemci, okul, [a], b_ogretmen)
    assert yanit.status_code == 422
    assert yanit.json()["detail"] == "Öğretmen bu okulda bulunamadı"
    assert atamalar(istemci, okul) == {a: None}


def test_toplu_atamada_bos_liste_reddedilir(istemci, okul):
    yanit = toplu(istemci, okul, [], okul["ayse"])
    assert yanit.status_code == 422
