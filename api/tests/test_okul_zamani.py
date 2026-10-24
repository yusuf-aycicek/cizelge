"""Okulun zamanı: günlere göre ders saati, öğle arası ve zil saatleri (K3).

- Ayar tek gösterime getirilir: bütün günler aynıysa `gun_saatleri` boş kalır, en uzun gün
  `gunluk_ders_saati` olur. Veritabanı CHECK'leri de aynı kuralı korur.
- Bir günü kısaltmak gün/saat azaltmayla aynı akıştır (ADR 0014): önizleme, onaysız 409,
  onaylanınca o günün dışarıda kalan müsaitlikleri aynı işlemde silinir, programlar kalır.
- Çözücü girdisi, ön kontrol ve kapasite hesabı günlere göre uzunluğu kullanır.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from test_okul_ayarlari import programli


@pytest.fixture
def okul(istemci, okul_olustur):
    """5 gün × 8 saat; Ayşe; 9-A; Matematik."""
    okul_id = okul_olustur("Zaman Lisesi", gun_sayisi=5, gunluk_ders_saati=8)
    b = okul_basligi(okul_id)

    def ekle(yol, govde):
        yanit = istemci.post(yol, json=govde, headers=b)
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    return {"id": uuid.UUID(okul_id), "b": b, "ekle": ekle,
            "ayse": ekle("/api/ogretmenler", {"ad": "Ayşe Yılmaz"}),
            "9-A": ekle("/api/siniflar", {"ad": "9-A", "seviye": 9}),
            "mat": ekle("/api/dersler", {"ad": "Matematik", "kisa_ad": "MAT"})}


def okul_getir(istemci, okul):
    return istemci.get("/api/okul", headers=okul["b"]).json()


def gelemez(okul, gun, saat, ogretmen="ayse"):
    return okul["ekle"](f"{DP}/musaitlikler", {"ogretmen_id": okul[ogretmen], "gun": gun, "saat": saat,
                                               "durum": "gelemez"})


# --- ayarın kendisi ------------------------------------------------------------------------

def test_varsayilan_her_gun_ayni_ve_zil_saatleri_tanimsiz(istemci, okul):
    o = okul_getir(istemci, okul)
    assert o["gun_saatleri"] == [8, 8, 8, 8, 8]
    assert (o["ogle_arasi_sonra"], o["ilk_ders_baslangic"]) == (None, None)
    assert (o["ders_suresi_dk"], o["teneffus_dk"], o["ogle_arasi_dk"]) == (40, 10, 40)


def test_gunlere_gore_ders_saati_kaydedilir(istemci, okul, oturum_fabrikasi):
    yanit = istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 6]}, headers=okul["b"])
    assert yanit.status_code == 200, yanit.text
    assert (yanit.json()["gun_saatleri"], yanit.json()["gunluk_ders_saati"]) == ([8, 8, 8, 8, 6], 8)
    # En uzun gün kısalırsa günlük ders saati de iner (çizelgenin satır sayısı).
    yanit = istemci.patch("/api/okul", json={"gun_saatleri": [7, 7, 7, 7, 6]}, headers=okul["b"])
    assert yanit.json()["gunluk_ders_saati"] == 7


def test_hepsi_ayni_liste_bos_saklanir(istemci, okul, oturum_fabrikasi):
    istemci.patch("/api/okul", json={"gun_saatleri": [6, 6, 6, 6, 6]}, headers=okul["b"])
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        satir = o.execute(text("SELECT gun_saatleri, gunluk_ders_saati FROM okul")).one()
    assert (satir.gun_saatleri, satir.gunluk_ders_saati) == (None, 6)
    assert okul_getir(istemci, okul)["gun_saatleri"] == [6] * 5


def test_gunluk_ders_saati_her_gune_uygulanir(istemci, okul):
    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 6]}, headers=okul["b"])
    yanit = istemci.patch("/api/okul", json={"gunluk_ders_saati": 7}, headers=okul["b"])
    assert yanit.json()["gun_saatleri"] == [7] * 5


def test_gun_sayisi_degisince_gunlere_gore_saatler_korunur(istemci, okul):
    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 6]}, headers=okul["b"])
    assert istemci.patch("/api/okul", json={"gun_sayisi": 6}, headers=okul["b"]).json()["gun_saatleri"] == [
        8, 8, 8, 8, 6, 8]


@pytest.mark.parametrize("govde, parca", [
    ({"gun_saatleri": [8, 8, 8]}, "5 gün için verilmeli"),
    ({"gun_sayisi": 4, "gun_saatleri": [8, 8, 8, 8, 6]}, "4 gün için verilmeli"),
    ({"ogle_arasi_sonra": 8}, "Öğle arası 8. dersten sonra olamaz: en uzun gün 8 saat"),
])
def test_gecersiz_hafta_anlasilir_hata(istemci, okul, govde, parca):
    yanit = istemci.patch("/api/okul", json=govde, headers=okul["b"])
    assert yanit.status_code == 422
    assert parca in str(yanit.json()["detail"])


def test_ogle_arasi_gunu_kisaltinca_korunmazsa_reddedilir(istemci, okul):
    istemci.patch("/api/okul", json={"ogle_arasi_sonra": 4}, headers=okul["b"])
    yanit = istemci.patch("/api/okul", json={"gunluk_ders_saati": 4}, headers=okul["b"])
    assert yanit.status_code == 422 and "Öğle arası 4. dersten sonra olamaz" in yanit.json()["detail"]
    assert istemci.patch("/api/okul", json={"gunluk_ders_saati": 4, "ogle_arasi_sonra": None},
                         headers=okul["b"]).status_code == 200


def test_gun_saati_sinirlari_semada(istemci, okul):
    for liste in ([8, 8, 8, 8, 0], [8, 8, 8, 8, 17]):
        assert istemci.patch("/api/okul", json={"gun_saatleri": liste}, headers=okul["b"]).status_code == 422


def test_zil_saatleri_kaydedilir_ve_kaldirilir(istemci, okul):
    govde = {"ilk_ders_baslangic": "08:30", "ders_suresi_dk": 40, "teneffus_dk": 10, "ogle_arasi_dk": 45,
             "ogle_arasi_sonra": 4}
    o = istemci.patch("/api/okul", json=govde, headers=okul["b"]).json()
    assert (o["ilk_ders_baslangic"], o["ogle_arasi_dk"], o["ogle_arasi_sonra"]) == ("08:30:00", 45, 4)
    # Zil saatleri sunucuda hesaplanır (tek kaynak: cekirdek/zil.py); arayüz ve çıktılar buradan okur.
    assert [z["baslangic"] for z in o["zil_saatleri"]] == [
        "08:30", "09:20", "10:10", "11:00", "12:25", "13:15", "14:05", "14:55"]
    assert o["zil_saatleri"][3] == {"baslangic": "11:00", "bitis": "11:40"}
    assert o["ogle_arasi_zili"] == {"baslangic": "11:40", "bitis": "12:25"}
    o = istemci.patch("/api/okul", json={"ilk_ders_baslangic": None}, headers=okul["b"]).json()
    assert o["ilk_ders_baslangic"] is None and o["ogle_arasi_sonra"] == 4
    assert (o["zil_saatleri"], o["ogle_arasi_zili"]) == (None, None)


def test_zil_onizlemesi_kaydetmeden_hesaplar(istemci, okul):
    govde = {"ilk_ders_baslangic": "08:00", "saat_sayisi": 3, "ders_suresi_dk": 45, "teneffus_dk": 15,
             "ogle_arasi_dk": 60, "ogle_arasi_sonra": 2}
    o = istemci.post("/api/okul/zil-onizleme", json=govde, headers=okul["b"]).json()
    assert [(z["baslangic"], z["bitis"]) for z in o["zil_saatleri"]] == [
        ("08:00", "08:45"), ("09:00", "09:45"), ("10:45", "11:30")]
    assert o["ogle_arasi_zili"] == {"baslangic": "09:45", "bitis": "10:45"}
    assert istemci.get("/api/okul", headers=okul["b"]).json()["zil_saatleri"] is None
    assert istemci.post("/api/okul/zil-onizleme", json=govde).status_code == 401


@pytest.mark.parametrize("sql", [
    "UPDATE okul SET gun_saatleri = '{8,8,8,8}'",  # gün sayısı tutmuyor
    "UPDATE okul SET gun_saatleri = '{8,8,8,8,9}'",  # en uzun günden uzun
    "UPDATE okul SET gun_saatleri = '{7,7,7,7,6}'",  # gunluk_ders_saati en uzun gün değil
    "UPDATE okul SET gun_saatleri = '{8,8,8,8,0}'",
    "UPDATE okul SET ogle_arasi_sonra = 8",
    "UPDATE okul SET teneffus_dk = -1",
])
def test_veritabani_tutarsiz_haftayi_reddeder(okul, oturum_fabrikasi, sql):
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        with pytest.raises(IntegrityError, match="check"):
            o.execute(text(sql))
            o.flush()


# --- bir günü kısaltmak: ADR 0014 akışı ------------------------------------------------------

def test_gunu_kisaltma_onizlemesi_etkilenenleri_listeler(istemci, okul, oturum_fabrikasi):
    gelemez(okul, 4, 6)  # cuma 7. saat: gidecek
    gelemez(okul, 4, 4)  # cuma 5. saat: kalır
    gelemez(okul, 3, 7)  # perşembe 8. saat: kalır (perşembe kısalmıyor)
    a = okul["ekle"](f"{DP}/atamalar", {"sinif_id": okul["9-A"], "ders_id": okul["mat"], "ogretmen_id": okul["ayse"],
                                         "haftalik_saat": 2})
    programli(oturum_fabrikasi, okul, a, [(3, 7), (4, 5)], ad="Güz dönemi")

    yanit = istemci.post("/api/okul/ayar-etkisi", json={"gun_saatleri": [8, 8, 8, 8, 5]}, headers=okul["b"])

    assert yanit.json()["etkiler"] == [
        "1 müsaitlik kaydı yeni ayarların dışında kalıyor ve silinecek (1 öğretmen: Ayşe Yılmaz; ör. Ayşe Yılmaz, "
        "Cuma 7. saat).",
        "1 programda (Güz dönemi) yeni ayarların dışında kalan 1 ders saati var. Programlar silinmez, eski "
        "ayarlarla üretilmiş olarak kalır; yeni ayarlarla programı yeniden üretmeniz gerekir.",
    ]
    assert len(istemci.get(f"{DP}/musaitlikler", headers=okul["b"]).json()) == 3
    assert okul_getir(istemci, okul)["gun_saatleri"] == [8] * 5


def test_gunu_kisaltma_onaysiz_reddedilir_onayla_ayni_islemde_temizlenir(istemci, okul, oturum_fabrikasi):
    disari = gelemez(okul, 4, 6)
    iceri = gelemez(okul, 4, 4)
    yanit = istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5]}, headers=okul["b"])
    assert yanit.status_code == 409 and yanit.json()["etkiler"]
    assert okul_getir(istemci, okul)["gun_saatleri"] == [8] * 5

    yanit = istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5], "etkileri_onayla": True},
                          headers=okul["b"])
    assert yanit.status_code == 200 and yanit.json()["gun_saatleri"] == [8, 8, 8, 8, 5]
    kalan = {m["id"] for m in istemci.get(f"{DP}/musaitlikler", headers=okul["b"]).json()}
    assert kalan == {iceri} and disari not in kalan


def test_gunu_uzatmanin_etkisi_yok(istemci, okul):
    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5]}, headers=okul["b"])
    yanit = istemci.post("/api/okul/ayar-etkisi", json={"gun_saatleri": [8, 8, 8, 8, 8]}, headers=okul["b"])
    assert yanit.json() == {"etkiler": []}


def test_ogle_arasi_ve_zil_degisikliginin_etkisi_yok(istemci, okul):
    gelemez(okul, 4, 7)
    yanit = istemci.patch("/api/okul", json={"ogle_arasi_sonra": 4, "ilk_ders_baslangic": "08:00"}, headers=okul["b"])
    assert yanit.status_code == 200


def test_kisa_gunun_disina_musaitlik_girilemez(istemci, okul):
    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5]}, headers=okul["b"])
    yanit = istemci.post(f"{DP}/musaitlikler", json={"ogretmen_id": okul["ayse"], "gun": 4, "saat": 5,
                                                      "durum": "gelemez"}, headers=okul["b"])
    assert yanit.status_code == 422 and "5 gün, günlere göre 8, 8, 8, 8, 5 saat" in yanit.json()["detail"]
    yanit = istemci.put(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik",
                        json={"degisiklikler": [{"gun": 4, "saat": 5, "durum": "gelemez"}]}, headers=okul["b"])
    assert yanit.status_code == 422 and "Hiçbir hücre değiştirilmedi" in yanit.json()["detail"]
    # Pazartesi 8. saat hâlâ var.
    assert gelemez(okul, 0, 7)


# --- çözücü girdisi, ön kontrol ve kapasite ---------------------------------------------------

def test_cozucu_girdisi_gun_uzunluklarini_ve_ogle_arasini_tasir(istemci, okul, oturum_fabrikasi):
    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5], "ogle_arasi_sonra": 4}, headers=okul["b"])
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        ayar = cozum_girdisi_olustur(o).ayar
    assert (ayar.gunluk_saatler, ayar.ogle_arasi_sonra, ayar.haftalik_kapasite) == ((8, 8, 8, 8, 5), 4, 37)


def test_on_kontrol_ve_dagilim_ozeti_kisa_gunu_sayar(istemci, okul):
    # 9-A'ya 38 saat: her gün 8 olsa sığardı (40), cuma 5 saatle kapasite 37.
    dersler = [okul["ekle"]("/api/dersler", {"ad": f"Ders {i}", "kisa_ad": f"D{i}"}) for i in range(19)]
    ogretmenler = [okul["ekle"]("/api/ogretmenler", {"ad": f"Öğretmen {i}"}) for i in range(19)]
    for d, o in zip(dersler, ogretmenler):
        okul["ekle"](f"{DP}/atamalar", {"sinif_id": okul["9-A"], "ders_id": d, "ogretmen_id": o, "haftalik_saat": 2})
    assert istemci.get(f"{DP}/on-kontrol", headers=okul["b"]).json()["celiskiler"] == []

    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5]}, headers=okul["b"])

    celiskiler = istemci.get(f"{DP}/on-kontrol", headers=okul["b"]).json()["celiskiler"]
    assert [c["mesaj"] for c in celiskiler if c["tur"] == "sinif_kapasitesi"] == [
        "9-A sınıfının haftada 38 saat dersi var, haftalık kapasite 37 saat (4 gün × 8 saat, Cuma 5 saat)."]
    ozet = istemci.get(f"{DP}/dagilim-ozeti", headers=okul["b"]).json()
    sinif = next(s for s in ozet["siniflar"] if s["sinif_id"] == okul["9-A"])
    assert (sinif["kapasite"], sinif["asim"]) == (37, True)


def test_ogretmen_kapasitesi_kisa_gunu_sayar(istemci, okul):
    # Ayşe pazartesi bütün gün gelemez: müsait 8+8+8+5 = 29 saat (cuma kısa).
    istemci.patch("/api/okul", json={"gun_saatleri": [8, 8, 8, 8, 5]}, headers=okul["b"])
    istemci.put(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik",
                json={"degisiklikler": [{"gun": 0, "saat": s, "durum": "gelemez"} for s in range(8)]}, headers=okul["b"])
    yuk = istemci.get(f"{DP}/ogretmenler/{okul['ayse']}/musaitlik", headers=okul["b"]).json()["yuk"]
    assert yuk["musait_saat"] == 29
