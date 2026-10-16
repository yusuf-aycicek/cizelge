"""Okul ayarı değişikliğinin modül verisine etkisi ve silinemeyen kayıtların açıklaması (ADR 0014).

- Gün/saat azaltılınca aralık dışında kalan müsaitlik kayıtları silinir, programlar değişmez.
- Etkisi olan değişiklik açık onay olmadan yapılmaz (409 + etkiler); önizleme ucu hiçbir şeyi
  değiştirmez.
- Öğretmen, sınıf ya da ders silinemezse mesaj nerede kullanıldığını ve ne yapılacağını söyler.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.cekirdek.servisler import KayitCakismasi, OgretmenServisi
from okulapi.moduller.ders_programi.modeller import Program, Yerlesim


@pytest.fixture
def okul(istemci, okul_olustur):
    """5 gün, günde 8 saat; Ayşe ve Zeynep; 9-A, 9-B, 10-A; Matematik, Fizik."""
    okul_id = okul_olustur("Ayar Lisesi", gun_sayisi=5, gunluk_ders_saati=8)
    b = okul_basligi(okul_id)

    def ekle(yol, govde):
        yanit = istemci.post(yol, json=govde, headers=b)
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    k = {"id": uuid.UUID(okul_id), "b": b, "ekle": ekle}
    k["ayse"] = ekle("/api/ogretmenler", {"ad": "Ayşe Yılmaz"})
    k["zeynep"] = ekle("/api/ogretmenler", {"ad": "Zeynep Demir"})
    for s in ("9-A", "9-B", "10-A"):
        k[s] = ekle("/api/siniflar", {"ad": s, "seviye": int(s.split("-")[0])})
    k["mat"] = ekle("/api/dersler", {"ad": "Matematik", "kisa_ad": "MAT"})
    k["fiz"] = ekle("/api/dersler", {"ad": "Fizik", "kisa_ad": "FIZ"})
    return k


def musaitlik(istemci, k, ogretmen, gun, saat):
    return k["ekle"](f"{DP}/musaitlikler", {"ogretmen_id": k[ogretmen], "gun": gun, "saat": saat, "durum": "gelemez"})


def atama(istemci, k, sinif, ders, ogretmen="ayse"):
    return k["ekle"](f"{DP}/atamalar", {"sinif_id": k[sinif], "ders_id": k[ders], "ogretmen_id": k[ogretmen],
                                        "haftalik_saat": 2})


def programli(fabrika, k, atama_id, hucreler, ad="Güz") -> uuid.UUID:
    simdi = datetime.now(timezone.utc)
    with okul_oturumu(fabrika, k["id"]) as o:
        p = Program(ad=ad, durum="hazir", baslama=simdi, bitis=simdi, cozum_durumu="optimal", toplam_ceza=0)
        o.add(p)
        o.flush()
        o.add_all([Yerlesim(program_id=p.id, ders_atama_id=uuid.UUID(atama_id), gun=g, saat=s) for g, s in hucreler])
        o.commit()
        return p.id


# --- okul ayarı -----------------------------------------------------------------------------

def test_artirmanin_ya_da_aralik_icindeki_degisikligin_etkisi_yok(istemci, okul):
    musaitlik(istemci, okul, "ayse", 4, 7)  # cuma 8. saat
    for govde in ({"gun_sayisi": 6}, {"gunluk_ders_saati": 9}, {"gun_sayisi": 5, "gunluk_ders_saati": 8}):
        yanit = istemci.post("/api/okul/ayar-etkisi", json=govde, headers=okul["b"])
        assert yanit.json() == {"etkiler": []}, govde
    assert istemci.patch("/api/okul", json={"gun_sayisi": 6}, headers=okul["b"]).status_code == 200


def test_onizleme_etkileri_kullanicinin_diliyle_soyler_ve_hicbir_seyi_degistirmez(istemci, okul, oturum_fabrikasi):
    musaitlik(istemci, okul, "ayse", 4, 0)  # cuma: gün 4 gidecek
    musaitlik(istemci, okul, "zeynep", 1, 7)  # salı 8. saat: saat 7 gidecek
    musaitlik(istemci, okul, "ayse", 0, 0)  # kalır
    a = atama(istemci, okul, "9-A", "mat")
    programli(oturum_fabrikasi, okul, a, [(0, 0), (4, 1)], ad="Güz dönemi")

    yanit = istemci.post("/api/okul/ayar-etkisi", json={"gun_sayisi": 4, "gunluk_ders_saati": 7}, headers=okul["b"])

    assert yanit.json()["etkiler"] == [
        "2 müsaitlik kaydı yeni ayarların dışında kalıyor ve silinecek (2 öğretmen; ör. Ayşe Yılmaz, Cuma 1. saat).",
        "1 programda (Güz dönemi) yeni ayarların dışında kalan 1 ders saati var. Programlar silinmez, eski "
        "ayarlarla üretilmiş olarak kalır; yeni ayarlarla programı yeniden üretmeniz gerekir.",
    ]
    assert len(istemci.get(f"{DP}/musaitlikler", headers=okul["b"]).json()) == 3
    assert istemci.get("/api/okul", headers=okul["b"]).json()["gun_sayisi"] == 5


def test_etkili_degisiklik_onaysiz_reddedilir_ve_hicbir_sey_degismez(istemci, okul):
    musaitlik(istemci, okul, "ayse", 4, 0)
    yanit = istemci.patch("/api/okul", json={"gun_sayisi": 4, "ad": "Yeni Ad"}, headers=okul["b"])
    assert yanit.status_code == 409
    assert yanit.json()["detail"] == "Bu değişiklik mevcut kayıtları etkiliyor; devam etmek için etkileri onaylayın."
    assert yanit.json()["etkiler"][0].startswith("1 müsaitlik kaydı yeni ayarların dışında kalıyor")
    okul_ = istemci.get("/api/okul", headers=okul["b"]).json()
    assert (okul_["gun_sayisi"], okul_["ad"]) == (5, "Ayar Lisesi")
    assert len(istemci.get(f"{DP}/musaitlikler", headers=okul["b"]).json()) == 1


def test_onaylanan_degisiklik_aralik_disindaki_musaitligi_siler_programa_dokunmaz(istemci, okul, oturum_fabrikasi):
    disari = musaitlik(istemci, okul, "ayse", 4, 0)
    iceri = musaitlik(istemci, okul, "ayse", 3, 6)
    a = atama(istemci, okul, "9-A", "mat")
    program = programli(oturum_fabrikasi, okul, a, [(0, 0), (4, 1)])

    yanit = istemci.patch("/api/okul", json={"gun_sayisi": 4, "etkileri_onayla": True}, headers=okul["b"])

    assert yanit.status_code == 200 and yanit.json()["gun_sayisi"] == 4
    kalan = {m["id"] for m in istemci.get(f"{DP}/musaitlikler", headers=okul["b"]).json()}
    assert kalan == {iceri} and disari not in kalan
    yerlesimler = istemci.get(f"{DP}/programlar/{program}/yerlesimler", headers=okul["b"]).json()
    assert sorted((y["gun"], y["saat"]) for y in yerlesimler) == [(0, 0), (4, 1)]


def test_onay_alani_sadece_ayar_degisikliginde_anlamli(istemci, okul):
    yanit = istemci.patch("/api/okul", json={"ad": "Başka", "etkileri_onayla": True}, headers=okul["b"])
    assert yanit.status_code == 200 and yanit.json()["ad"] == "Başka"


def test_baska_okulun_kayitlari_etkiye_karismaz(istemci, okul, okul_olustur):
    b_okul = okul_olustur("B Lisesi", gun_sayisi=5, gunluk_ders_saati=8)
    b = okul_basligi(b_okul)
    b_ogr = istemci.post("/api/ogretmenler", json={"ad": "B Öğretmeni"}, headers=b).json()["id"]
    istemci.post(f"{DP}/musaitlikler", json={"ogretmen_id": b_ogr, "gun": 4, "saat": 0, "durum": "gelemez"}, headers=b)
    assert istemci.post("/api/okul/ayar-etkisi", json={"gun_sayisi": 4}, headers=okul["b"]).json() == {"etkiler": []}
    assert istemci.patch("/api/okul", json={"gun_sayisi": 4}, headers=okul["b"]).status_code == 200
    assert len(istemci.get(f"{DP}/musaitlikler", headers=b).json()) == 1


# --- silinemeyen kayıtlar -------------------------------------------------------------------

def test_sinif_silinemezse_derslerini_soyler(istemci, okul):
    atama(istemci, okul, "9-A", "mat")
    atama(istemci, okul, "9-A", "fiz", "zeynep")
    yanit = istemci.delete(f"/api/siniflar/{okul['9-A']}", headers=okul["b"])
    assert (yanit.status_code, yanit.json()["detail"]) == (409, (
        "9-A silinemez: bu sınıfa 2 ders atanmış (9-A Fizik, 9-A Matematik). Önce Ders dağılımı sayfasında "
        "bu sınıfın derslerini kaldırın."))


def test_ders_silinemezse_atamalari_ve_sablonu_soyler(istemci, okul):
    atama(istemci, okul, "10-A", "mat")
    atama(istemci, okul, "9-A", "mat")
    okul["ekle"](f"{DP}/seviye-sablonlari", {"seviye": 9, "ders_id": okul["mat"], "haftalik_saat": 4})
    yanit = istemci.delete(f"/api/dersler/{okul['mat']}", headers=okul["b"])
    assert yanit.json()["detail"] == (
        "Matematik silinemez: 2 sınıfa atanmış (9-A Matematik, 10-A Matematik). 9. sınıf seviye şablonunda var. "
        "Önce Ders dağılımı ve Seviye şablonu sayfalarında bu dersi kaldırın.")


def test_cok_kullanimda_ilk_bes_ve_kalan_sayisi(istemci, okul):
    for s in ("11-A", "11-B", "12-A", "12-B"):
        okul[s] = okul["ekle"]("/api/siniflar", {"ad": s, "seviye": int(s.split("-")[0])})
    for s in ("9-A", "9-B", "10-A", "11-A", "11-B", "12-A", "12-B"):
        atama(istemci, okul, s, "mat")
    detay = istemci.delete(f"/api/ogretmenler/{okul['ayse']}", headers=okul["b"]).json()["detail"]
    assert detay.startswith("Ayşe Yılmaz silinemez: 7 derste öğretmen olarak seçili (9-A Matematik, 9-B Matematik, "
                            "10-A Matematik, 11-A Matematik, 11-B Matematik ve 2 tane daha).")


def test_kullanilmayan_kayit_silinir(istemci, okul):
    assert istemci.delete(f"/api/dersler/{okul['fiz']}", headers=okul["b"]).status_code == 204


def test_kanca_yoksa_genel_mesaj(istemci, okul, oturum_fabrikasi):
    """Çekirdek kancasız da çalışır: modül listesi verilmezse genel mesaj (modül bağımsızlığı)."""
    atama(istemci, okul, "9-A", "mat")
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        with pytest.raises(KayitCakismasi, match="Bu kayıt başka kayıtlar tarafından kullanılıyor, silinemez"):
            OgretmenServisi(o).sil(uuid.UUID(okul["ayse"]))
