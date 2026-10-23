"""Blok dersler (dağılım şekli) API'si: okul önerisi, derse ve ders + şubeye özel şekil (K4).

Hesap çözücüdeki kuralla aynıdır (`cozucu.blok`); burada API'nin sözleşmesi denetlenir:
- `/kurallar/blok_deseni` okul ayarı: öneri açık/kapalı, saate göre önerilen şekiller;
- `/kurallar/blok_deseni/ozel`: derse ya da ders + şubeye özel şekil, "blok yok" dahil;
- `/dagilim-sekilleri`: her atamanın şekli, nereden geldiği, öneri düştüyse nedeni;
- ön kontrol açıkça seçilmiş ama uygulanamayan şekli söyler.
"""

from __future__ import annotations

import pytest

from conftest import DP, okul_basligi

B = "blok_deseni"


@pytest.fixture
def okul(istemci, okul_olustur):
    """5 gün × 6 saat. Ayşe: 9-A ve 9-B Matematik (5 saat). Ali: 9-A Fizik (4 saat), yalnızca 2 gün gelir."""
    b = okul_basligi(okul_olustur("Blok Lisesi", gun_sayisi=5, gunluk_ders_saati=6))

    def ekle(yol, govde):
        yanit = istemci.post(yol, json=govde, headers=b)
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    k = {"b": b}
    k["ayse"] = ekle("/api/ogretmenler", {"ad": "Ayşe Yılmaz"})
    k["ali"] = ekle("/api/ogretmenler", {"ad": "Ali Çelik"})
    k["mat"] = ekle("/api/dersler", {"ad": "Matematik", "kisa_ad": "MAT"})
    k["fiz"] = ekle("/api/dersler", {"ad": "Fizik", "kisa_ad": "FİZ"})
    k["9-A"] = ekle("/api/siniflar", {"ad": "9-A", "seviye": 9})
    k["9-B"] = ekle("/api/siniflar", {"ad": "9-B", "seviye": 9})
    for s in ("9-A", "9-B"):
        k[f"{s}-mat"] = ekle(f"{DP}/atamalar", {"sinif_id": k[s], "ders_id": k["mat"], "ogretmen_id": k["ayse"],
                                                 "haftalik_saat": 5})
    k["9-A-fiz"] = ekle(f"{DP}/atamalar", {"sinif_id": k["9-A"], "ders_id": k["fiz"], "ogretmen_id": k["ali"],
                                            "haftalik_saat": 4})
    istemci.put(f"{DP}/ogretmenler/{k['ali']}/musaitlik", headers=b, json={"degisiklikler": [
        {"gun": g, "saat": s, "durum": "gelemez"} for g in (2, 3, 4) for s in range(6)]})
    return k


def sekiller(istemci, okul) -> dict[str, dict]:
    return {s["atama_id"]: s for s in istemci.get(f"{DP}/dagilim-sekilleri", headers=okul["b"]).json()}


def ozel(istemci, okul, kapsam, desen):
    return istemci.put(f"{DP}/kurallar/{B}/ozel", headers=okul["b"],
                       json={"kapsam": kapsam, "parametreler": {"desen": desen}})


def test_kural_listede_okul_onerisi_acik(istemci, okul):
    k = next(x for x in istemci.get(f"{DP}/kurallar", headers=okul["b"]).json() if x["tur"] == B)
    assert (k["ad"], k["zorunlu"], k["parametreler"], k["kapsamlar"]) == (
        "Dağılım şekli (blok dersler)", True, {"otomatik": True}, ["ders", "sube"])


def test_okul_onerisi_ve_dusen_oneri_nedeniyle(istemci, okul):
    s = sekiller(istemci, okul)
    assert (s[okul["9-A-mat"]]["metin"], s[okul["9-A-mat"]]["kaynak"], s[okul["9-A-mat"]]["desen"]) == (
        "2+2+1", "okul", [2, 2, 1])
    # Fizik 4 saat → 2+2 önerisi; Ali yalnızca 2 gün geliyor, 2 blok sığar: öneri uygulanır.
    assert s[okul["9-A-fiz"]]["metin"] == "2+2"
    # Salı yalnızca 1. ve 3. saat açık: art arda 2 saat yalnızca pazartesi; 2+2 sığmaz, öneri düşer.
    # Bloksuz yerleşim yine mümkün (pazartesi 2 + salı 2).
    istemci.put(f"{DP}/ogretmenler/{okul['ali']}/musaitlik", headers=okul["b"], json={"degisiklikler": [
        {"gun": 1, "saat": s, "durum": "gelemez"} for s in (1, 3, 4, 5)]})
    fiz = sekiller(istemci, okul)[okul["9-A-fiz"]]
    assert (fiz["metin"], fiz["kaynak"], fiz["dusen_oneri"], fiz["nedenler"]) == (
        "blok yok", "yok", "2+2", ["öğretmenin müsaitliğine sığmıyor"])
    # Öneri düştüğü için ön kontrol sorun görmez.
    assert istemci.get(f"{DP}/on-kontrol", headers=okul["b"]).json()["celiskiler"] == []


def test_okul_onerisi_kapatilir_ve_saate_gore_degistirilir(istemci, okul):
    b = okul["b"]
    yanit = istemci.put(f"{DP}/kurallar/{B}", headers=b, json={"parametreler": {"varsayilanlar": {"5": [1, 2, 2]}}})
    assert yanit.status_code == 200, yanit.text
    assert yanit.json()["parametreler"] == {"otomatik": True, "varsayilanlar": {"5": [2, 2, 1]}}
    yanit = istemci.put(f"{DP}/kurallar/{B}", headers=b, json={"parametreler": {"varsayilanlar": {"5": [3, 1, 1]}}})
    assert yanit.status_code == 200
    assert sekiller(istemci, okul)[okul["9-A-mat"]]["dusen_oneri"] == "3+1+1"  # N = 2: öneri düşer
    istemci.put(f"{DP}/kurallar/{B}", headers=b, json={"parametreler": {"otomatik": False}})
    assert {s["kaynak"] for s in sekiller(istemci, okul).values()} == {"yok"}


@pytest.mark.parametrize("parametreler, parca", [
    ({"varsayilanlar": {"5": [2, 2]}}, "5 saatlik dersin dağılım şekli 2+2 olamaz: toplamı 4 saat"),
    ({"varsayilanlar": {"5": [0, 5]}}, "Dağılım şekli \"2+2+1\" gibi olmalı"),
    ({"varsayilanlar": {"5": "2+2+1"}}, "Bazı alanlar hatalı"),  # şema reddeder (liste değil)
    ({"otomatik": 1}, "otomatik açık ya da kapalı"),
    ({"bilinmeyen": True}, "Bu kuralın ayarları: otomatik, varsayilanlar"),
])
def test_gecersiz_okul_ayari(istemci, okul, parametreler, parca):
    yanit = istemci.put(f"{DP}/kurallar/{B}", headers=okul["b"], json={"parametreler": parametreler})
    assert yanit.status_code == 422 and parca in yanit.json()["detail"], yanit.text


def test_derse_ve_ders_subeye_ozel_sekil(istemci, okul):
    assert ozel(istemci, okul, {"ders_id": okul["mat"]}, [1, 1, 1, 2]).status_code == 200
    assert ozel(istemci, okul, {"ders_id": okul["mat"], "sinif_id": okul["9-B"]}, []).status_code == 200
    s = sekiller(istemci, okul)
    assert (s[okul["9-A-mat"]]["metin"], s[okul["9-A-mat"]]["kaynak"]) == ("2+1+1+1", "ders")
    assert (s[okul["9-B-mat"]]["metin"], s[okul["9-B-mat"]]["kaynak"]) == ("blok yok", "ders_sube")
    # Özel ayarların özetinde adlarıyla; şekil tek gösterimde.
    k = next(x for x in istemci.get(f"{DP}/kurallar", headers=okul["b"]).json() if x["tur"] == B)
    assert [(o["ad"], o["parametreler"]) for o in k["ozel_ayarlar"]] == [
        ("9-B · Matematik", {"desen": []}), ("Matematik", {"desen": [2, 1, 1, 1]})]


def test_ozel_sekil_ders_ister_ve_bicim_denetlenir(istemci, okul):
    yanit = ozel(istemci, okul, {"sinif_id": okul["9-A"]}, [2, 2, 1])
    assert yanit.status_code == 422 and "ders belirtilmeli" in yanit.json()["detail"]
    yanit = ozel(istemci, okul, {"ogretmen_id": okul["ayse"]}, [2, 2, 1])
    assert yanit.status_code == 422 and "öğretmene özel ayarlanamaz" in yanit.json()["detail"]
    yanit = ozel(istemci, okul, {"ders_id": okul["mat"]}, [0, 5])
    assert yanit.status_code == 422 and "her blok 1-8 saat" in yanit.json()["detail"]


def test_acikca_secilen_sekil_uygulanamazsa_on_kontrol_soyler(istemci, okul):
    ozel(istemci, okul, {"ders_id": okul["fiz"]}, [2, 2])
    istemci.put(f"{DP}/ogretmenler/{okul['ali']}/musaitlik", headers=okul["b"], json={"degisiklikler": [
        {"gun": 1, "saat": s, "durum": "gelemez"} for s in (1, 3, 4, 5)]})
    fiz = sekiller(istemci, okul)[okul["9-A-fiz"]]
    assert (fiz["kaynak"], fiz["sorunlar"]) == ("ders", ["öğretmenin müsaitliğine sığmıyor"])
    celiskiler = istemci.get(f"{DP}/on-kontrol", headers=okul["b"]).json()["celiskiler"]
    assert [c["mesaj"] for c in celiskiler if c["tur"] == "blok_deseni"] == [
        "9-A Fizik 2 blok istiyor (dağılım şekli 2+2) ve her blok ayrı bir güne konur, ama Ali Çelik'in art "
        "arda 2 saat müsait olduğu 1 gün var."]
    # Toplam tutmuyorsa yalnızca o söylenir.
    ozel(istemci, okul, {"ders_id": okul["mat"]}, [2, 2])
    mesajlar = [c["mesaj"] for c in istemci.get(f"{DP}/on-kontrol", headers=okul["b"]).json()["celiskiler"]
                if c["tur"] == "blok_deseni"]
    assert "9-A Matematik haftada 5 saat, ama dağılım şekli 2+2 (4 saat). Şekli ya da haftalık saati düzeltin." in mesajlar


def test_ozel_sekil_kaldirilinca_okul_onerisine_doner(istemci, okul):
    ozel(istemci, okul, {"ders_id": okul["mat"]}, [])
    assert sekiller(istemci, okul)[okul["9-A-mat"]]["kaynak"] == "ders"
    istemci.delete(f"{DP}/kurallar/{B}/ozel?ders_id={okul['mat']}", headers=okul["b"])
    assert sekiller(istemci, okul)[okul["9-A-mat"]]["metin"] == "2+2+1"


def test_baska_okulun_sekilleri_gorunmez(istemci, okul, okul_olustur):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    assert istemci.get(f"{DP}/dagilim-sekilleri", headers=b2).json() == []
    yanit = ozel(istemci, {"b": b2}, {"ders_id": okul["mat"]}, [2, 2, 1])
    assert yanit.status_code == 422 and "Ders bu okulda bulunamadı" in yanit.json()["detail"]
