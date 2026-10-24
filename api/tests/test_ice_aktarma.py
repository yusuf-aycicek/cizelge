"""Excel'den içe aktarma (8a, ADR 0021): şablon, önizleme, tek işlemde kayıt, eşleştirme, sınırlar,
okul izolasyonu."""

from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook

from conftest import DP, okul_basligi
from okulapi.moduller.ders_programi import ice_aktarma

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
IA = f"{DP}/ice-aktarma"


def dosya(**sayfalar: list[list]) -> bytes:
    """Şablon biçiminde dosya: her sayfada açıklama, başlık, sonra verilen satırlar."""
    adlar = {"ogretmen": "Öğretmenler", "sinif": "Sınıflar", "ders": "Dersler", "dagilim": "Ders dağılımı"}
    kitap = Workbook()
    kitap.remove(kitap.active)
    for tur, satirlar in sayfalar.items():
        ws = kitap.create_sheet(adlar[tur])
        ws.append(["açıklama"])
        ws.append([s.baslik for s in ice_aktarma.SAYFA[tur].sutunlar])
        for satir in satirlar:
            ws.append(satir)
    tampon = BytesIO()
    kitap.save(tampon)
    return tampon.getvalue()


def onizle(istemci, baslik, icerik: bytes):
    return istemci.post(f"{IA}/onizleme", content=icerik, headers={**baslik, "Content-Type": XLSX})


def kaydet(istemci, baslik, icerik: bytes, ozet: str):
    return istemci.post(IA, params={"ozet": ozet}, content=icerik, headers={**baslik, "Content-Type": XLSX})


def sayfa(onizleme: dict, tur: str) -> dict:
    return next(s for s in onizleme["sayfalar"] if s["sayfa"] == tur)


def listele(istemci, baslik, yol: str) -> list[dict]:
    return istemci.get(yol, headers=baslik).json()


@pytest.fixture
def bos_okul(okul_olustur):
    return okul_basligi(okul_olustur("Aktarma Lisesi"))


TAM = dict(
    ogretmen=[["Ayşe Yılmaz", "Matematik"], ["Ali Çelik", "Fizik"]],
    ders=[["Matematik", "MAT"], ["Fizik", "FİZ"]],
    sinif=[["9-A", 9, None], ["11-A", 11, "11 Sayısal"], ["11-B", 11, "11 sayısal"]],
    dagilim=[["9-A", "Matematik", 6, "Ayşe Yılmaz"], ["11-A", "Fizik", 3, "ali  çelik"], ["11-B", "Fizik", 2, None]],
)


def test_sablon_dort_sayfa_aciklama_baslik_ve_ornek(istemci, bos_okul):
    yanit = istemci.get(f"{IA}/sablon.xlsx", headers=bos_okul)
    assert yanit.status_code == 200 and yanit.headers["content-type"] == XLSX
    kitap = load_workbook(BytesIO(yanit.content))
    assert kitap.sheetnames == ["Öğretmenler", "Sınıflar", "Dersler", "Ders dağılımı"]
    ws = kitap["Ders dağılımı"]
    assert "Öğretmen boş bırakılabilir" in ws["A1"].value and "örnektir ve okunmaz" in ws["A1"].value
    assert [c.value for c in ws[2]] == ["Şube *", "Ders *", "Haftalık saat *", "Öğretmen"]
    assert [c.value for c in ws[3]] == ["9-A (örnek)", "Matematik", 6, "Ayşe Yılmaz"]
    # Şablon olduğu gibi yüklenirse örnek satırlar okunmaz; hiçbir şey eklenmez.
    o = onizle(istemci, bos_okul, yanit.content).json()
    assert o["eklenecek_sayisi"] == 0 and o["hata_sayisi"] == 0
    assert all(s["atlanan_ornek"] == 1 for s in o["sayfalar"])


def test_onizleme_kaydetmez_onay_tek_islemde_kaydeder(istemci, bos_okul):
    icerik = dosya(**TAM)
    o = onizle(istemci, bos_okul, icerik).json()
    assert o["hata_sayisi"] == 0, o
    assert [len(sayfa(o, t)["eklenecek"]) for t in ("ogretmen", "sinif", "ders", "dagilim")] == [2, 3, 2, 3]
    assert "(yeni grup)" in sayfa(o, "sinif")["eklenecek"][1]["ayrinti"]
    assert listele(istemci, bos_okul, "/api/ogretmenler") == []  # önizleme bir şey yazmadı

    yanit = kaydet(istemci, bos_okul, icerik, o["ozet"])
    assert yanit.status_code == 200, yanit.text
    assert yanit.json() == {"eklenen": 11, "guncellenen": 0}  # 2 + 2 + 1 grup + 3 + 3
    gruplar = listele(istemci, bos_okul, "/api/sube-gruplari")
    assert [(g["ad"], g["seviye"]) for g in gruplar] == [("11 Sayısal", 11)]  # "11 sayısal" aynı grup
    siniflar = {s["ad"]: s for s in listele(istemci, bos_okul, "/api/siniflar")}
    assert siniflar["11-A"]["sube_grubu_id"] == siniflar["11-B"]["sube_grubu_id"] == gruplar[0]["id"]
    ogretmenler = {o["ad"]: o["id"] for o in listele(istemci, bos_okul, "/api/ogretmenler")}
    atamalar = listele(istemci, bos_okul, f"{DP}/atamalar")
    assert sorted((a["haftalik_saat"], a["ogretmen_id"]) for a in atamalar) == sorted(
        [(6, ogretmenler["Ayşe Yılmaz"]), (3, ogretmenler["Ali Çelik"]), (2, None)], key=str)
    dersler = listele(istemci, bos_okul, "/api/dersler")
    assert len({d["renk"] for d in dersler}) == 2  # her yeni derse paletten farklı renk


def test_ayni_dosya_ikinci_kez_cogaltmaz_turkce_harf_ve_bosluk_farki(istemci, bos_okul):
    icerik = dosya(**TAM)
    assert kaydet(istemci, bos_okul, icerik, onizle(istemci, bos_okul, icerik).json()["ozet"]).status_code == 200
    ikinci = dosya(
        ogretmen=[["AYŞE  YILMAZ", "Matematik"], ["ali çelik", "Fizik ve Kimya"]],
        ders=[["MATEMATİK", None], ["fizik", "FİZ"]],
        sinif=[["9 - a", None, None], ["11-A", 11, "11  SAYISAL"]],
        dagilim=[["9-a", "matematik", 5, None]],
    )
    o = onizle(istemci, bos_okul, ikinci).json()
    assert o["hata_sayisi"] == 0 and o["eklenecek_sayisi"] == 0, o
    guncel = {t: [(s["ad"], s["ayrinti"]) for s in sayfa(o, t)["guncellenecek"]] for t in ("ogretmen", "dagilim")}
    # Var olan adlar okulda yazıldığı gibi kalır; boş öğretmen hücresi atamanın öğretmenini değiştirmez.
    assert guncel["ogretmen"] == [("Ali Çelik", "Branş: Fizik → Fizik ve Kimya")]
    assert guncel["dagilim"] == [("9-a · matematik", "Saat: 6 → 5")]
    assert sayfa(o, "sinif")["degismeyen"] == 2 and sayfa(o, "ders")["degismeyen"] == 2
    assert kaydet(istemci, bos_okul, ikinci, o["ozet"]).json() == {"eklenen": 0, "guncellenen": 2}
    assert len(listele(istemci, bos_okul, "/api/ogretmenler")) == 2
    assert len(listele(istemci, bos_okul, "/api/siniflar")) == 3
    atama = next(a for a in listele(istemci, bos_okul, f"{DP}/atamalar") if a["haftalik_saat"] == 5)
    assert atama["ogretmen_id"] is not None


def test_hatali_satirlar_satir_numarasi_ve_sade_neden_hicbiri_kaydedilmez(istemci, bos_okul):
    icerik = dosya(
        ogretmen=[["Ayşe Yılmaz", "Matematik"], ["ayşe yılmaz", "Fizik"], [None, "Kimya"]],
        sinif=[["9-A", 9, None], ["9-B", 15, None], ["10-A", None, None], ["11-A", 11, "Grup"], ["9-C", 9, "grup"]],
        ders=[["Matematik", "MATEMATİK DERSİ UZUN KISA AD"]],
        dagilim=[["9-A", "Kimya", 2, None], ["9-A", "Matematik", 0, None], ["9-B", "Matematik", 2, None],
                 ["9-A", "Matematik", 2, "Veli Can"]],
    )
    o = onizle(istemci, bos_okul, icerik).json()
    hatalar = {t: [(h["satir"], h["ayrinti"]) for h in sayfa(o, t)["hatali"]]
               for t in ("ogretmen", "sinif", "ders", "dagilim")}
    assert hatalar["ogretmen"] == [(4, "“ayşe yılmaz” bu sayfada 3. satırda da var"), (5, "Ad Soyad boş")]
    assert hatalar["sinif"] == [
        (4, "Seviye 1 ile 12 arasında bir tam sayı olmalı"), (5, "Yeni şube için seviye gerekli"),
        (7, "9-C 9. sınıf; “grup” grubu 11. sınıfların grubu")]
    assert hatalar["ders"] == [(3, "Kısa ad en çok 20 karakter olabilir")]
    assert hatalar["dagilim"] == [
        (3, "“Kimya” adlı ders yok; Dersler sayfasına ekleyin ya da adını düzeltin"),
        (4, "Haftalık saat 1 ile 40 arasında bir tam sayı olmalı"),
        (5, "“9-B” şube hatalı satırda (4. satır)"),
        (6, "“Matematik” ders hatalı satırda (3. satır)")]
    assert o["hata_sayisi"] == 10
    # Onaylansa bile hiçbiri kaydedilmez (sağlam satırlar da).
    yanit = kaydet(istemci, bos_okul, icerik, o["ozet"])
    assert yanit.status_code == 422 and "hatalı satır" in yanit.json()["detail"]
    assert listele(istemci, bos_okul, "/api/ogretmenler") == [] and listele(istemci, bos_okul, "/api/siniflar") == []


def test_onizlemeden_sonra_veri_degistiyse_kaydetmez(istemci, bos_okul):
    icerik = dosya(ogretmen=[["Ayşe Yılmaz", "Matematik"]])
    o = onizle(istemci, bos_okul, icerik).json()
    istemci.post("/api/ogretmenler", json={"ad": "Ayşe Yılmaz", "brans": "Fizik"}, headers=bos_okul)
    yanit = kaydet(istemci, bos_okul, icerik, o["ozet"])
    assert yanit.status_code == 409 and "önizlemeden sonra değişti" in yanit.json()["detail"]
    assert [o["brans"] for o in listele(istemci, bos_okul, "/api/ogretmenler")] == ["Fizik"]


def test_kayitta_veritabani_hatasi_olursa_hicbiri_kalmaz(istemci, bos_okul, monkeypatch):
    """Tek işlem: son işlemde veritabanı reddederse öncekiler de geri alınır."""
    icerik = dosya(ogretmen=[["Ayşe Yılmaz", ""]], ders=[["Matematik", None]])
    o = onizle(istemci, bos_okul, icerik).json()
    monkeypatch.setattr(ice_aktarma, "siradaki_renk", lambda _r: "#zzzzzz")  # renk CHECK ihlali
    yanit = kaydet(istemci, bos_okul, icerik, o["ozet"])
    assert yanit.status_code == 409, yanit.text
    assert listele(istemci, bos_okul, "/api/ogretmenler") == []


def test_dosya_boyutu_satir_siniri_ve_bozuk_dosya(istemci, bos_okul, monkeypatch):
    yanit = onizle(istemci, bos_okul, b"x" * (ice_aktarma.MAKS_BOYUT + 1))
    assert yanit.status_code == 413 and "en çok 2 MB" in yanit.json()["detail"]
    yanit = onizle(istemci, bos_okul, b"duz metin, excel degil")
    assert yanit.status_code == 422 and "Excel dosyası (.xlsx) değil" in yanit.json()["detail"]
    monkeypatch.setattr(ice_aktarma, "MAKS_SATIR", 3)
    yanit = onizle(istemci, bos_okul, dosya(ogretmen=[[f"Öğretmen {i}", ""] for i in range(4)]))
    assert yanit.status_code == 422 and "çok fazla satır" in yanit.json()["detail"]
    assert onizle(istemci, bos_okul, dosya(ogretmen=[[f"Öğretmen {i}", ""] for i in range(3)])).status_code == 200
    # Tanınan sayfa yok; başlık satırı yok.
    kitap = Workbook()
    kitap.active.title = "Sayfa1"
    tampon = BytesIO()
    kitap.save(tampon)
    assert "tanınan sayfa yok" in onizle(istemci, bos_okul, tampon.getvalue()).json()["detail"]
    kitap.active.title = "öğretmenler"
    kitap.active.append(["Ad", "Soyad"])
    tampon = BytesIO()
    kitap.save(tampon)
    assert "başlık satırı bulunamadı" in onizle(istemci, bos_okul, tampon.getvalue()).json()["detail"]


def test_sikistirma_bombasi_reddedilir(istemci, bos_okul, monkeypatch):
    monkeypatch.setattr(ice_aktarma, "MAKS_ACIK_BOYUT", 1000)
    yanit = onizle(istemci, bos_okul, dosya(**TAM))
    assert yanit.status_code == 422 and "içeriği çok büyük" in yanit.json()["detail"]


def test_okul_izolasyonu(istemci, okul_olustur):
    """B okulundaki aynı adlı kayıtlarla eşleşmez, B'ye bir şey yazılmaz; oturumsuz istek 401."""
    a, b = okul_basligi(okul_olustur("A Lisesi")), okul_basligi(okul_olustur("B Lisesi"))
    istemci.post("/api/ogretmenler", json={"ad": "Ayşe Yılmaz", "brans": "Fizik"}, headers=b)
    istemci.post("/api/siniflar", json={"ad": "9-A", "seviye": 9}, headers=b)
    icerik = dosya(**TAM)
    o = onizle(istemci, a, icerik).json()
    assert sayfa(o, "ogretmen")["guncellenecek"] == [] and len(sayfa(o, "ogretmen")["eklenecek"]) == 2
    assert kaydet(istemci, a, icerik, o["ozet"]).status_code == 200
    assert [(t["ad"], t["brans"]) for t in listele(istemci, b, "/api/ogretmenler")] == [("Ayşe Yılmaz", "Fizik")]
    assert [s["ad"] for s in listele(istemci, b, "/api/siniflar")] == ["9-A"]
    assert listele(istemci, b, f"{DP}/atamalar") == []
    # Dağılım yalnızca B'de olan şubeye bağlanamaz.
    yalniz_b = dosya(dagilim=[["9-A", "Matematik", 2, None]])
    istemci.post("/api/dersler", json={"ad": "Matematik"}, headers=b)
    o = onizle(istemci, okul_basligi(okul_olustur("C Lisesi")), yalniz_b).json()
    assert "adlı şube yok" in sayfa(o, "dagilim")["hatali"][0]["ayrinti"]
    istemci.cookies.clear()
    assert istemci.post(f"{IA}/onizleme", content=icerik, headers={"Content-Type": XLSX}).status_code == 401
    assert istemci.get(f"{IA}/sablon.xlsx").status_code == 401
