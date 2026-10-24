"""Program çıktıları (7.2): PDF (şube, öğretmen, çarşaf liste) ve Excel.

Doğrulama dosyanın içeriğinden yapılır: PDF'in metni (pypdf) ve Excel'in hücreleri (openpyxl).
Okul izolasyonu: başka okul, programı ve şubeyi/öğretmeni bilse de çıktı alamaz (404).
"""

from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from conftest import DP, okul_basligi
from okulapi.moduller.ders_programi.cikti.model import Cizelge, Hafta, Hucre
from okulapi.moduller.ders_programi.cikti.pdf import _haftalik_tablo, _yazitiplerini_kaydet, carsaf_gun_gruplari
from test_program_uretimi import okul, program_ekle, uret, worker_calistir  # noqa: F401  (okul: fikstür)


@pytest.fixture
def hazir_program(istemci, okul, kuyruk, oturum_fabrikasi):
    p = uret(istemci, okul, ad="Eylül Programı").json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, p)
    return p


def pdf_al(istemci, okul, p, yol, **params) -> PdfReader:
    yanit = istemci.get(f"{DP}/programlar/{p}/cikti/{yol}", params=params, headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    assert yanit.headers["content-type"] == "application/pdf"
    return PdfReader(BytesIO(yanit.content))


def sayfa_metinleri(pdf: PdfReader) -> list[str]:
    return [s.extract_text() for s in pdf.pages]


def yerlesimler(istemci, okul, p):
    return istemci.get(f"{DP}/programlar/{p}/yerlesimler", headers=okul["baslik"]).json()


# --- şube ve öğretmen PDF'i --------------------------------------------------------------------


def test_sube_pdfi_her_sube_ayri_sayfa_a4_yatay_turkce_metin(istemci, okul, hazir_program):
    pdf = pdf_al(istemci, okul, hazir_program, "subeler.pdf")
    metinler = sayfa_metinleri(pdf)
    assert len(metinler) == 3
    # Sınıf sırası: seviye, sonra ad (9-A, 9-B, 10-A).
    for metin, sube in zip(metinler, ["9-A", "9-B", "10-A"]):
        assert f"{sube} haftalık ders programı" in metin
        assert "Mini Lisesi" in metin and "Eylül Programı" in metin
        assert all(g in metin for g in ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
    assert "Türk Dili ve Edebiyatı" in metinler[0] and "Ayşe Yılmaz" in metinler[0]
    g, y = pdf.pages[0].mediabox.width, pdf.pages[0].mediabox.height
    assert (round(g), round(y)) == (842, 595)  # A4 yatay (pt)
    # Türkçe harfler için yazı tipi gömülü (alt küme).
    yazitipleri = {f["/BaseFont"] for f in pdf.pages[0]["/Resources"]["/Font"].values()}
    assert any("DejaVuSans" in str(f) for f in yazitipleri)
    gomulu = [f.get_object() for f in pdf.pages[0]["/Resources"]["/Font"].values() if "DejaVu" in f["/BaseFont"]]
    assert len(gomulu) == 2 and all("/FontFile2" in f["/FontDescriptor"] for f in gomulu)


def test_blok_ders_tek_hucre(istemci, okul, hazir_program):
    """9-A Matematik 6 saat, 2+2+2: üç blok, şube sayfasında ders adı üç kez yazar (saat başına değil)."""
    mat = okul["harita"]["a-9a-mat"]
    gunler = sorted({y["gun"] for y in yerlesimler(istemci, okul, hazir_program) if y["ders_atama_id"] == mat})
    assert len(gunler) == 3
    metin = sayfa_metinleri(pdf_al(istemci, okul, hazir_program, "subeler.pdf"))[0]
    assert metin.count("Matematik") == 3


def test_ogretmen_pdfi_haftalik_toplamla(istemci, okul, hazir_program):
    metinler = sayfa_metinleri(pdf_al(istemci, okul, hazir_program, "ogretmenler.pdf"))
    assert len(metinler) == 5
    ayse = next(m for m in metinler if "Ayşe Yılmaz haftalık ders programı" in m)
    toplam = sum(1 for y in yerlesimler(istemci, okul, hazir_program)
                 if y["ders_atama_id"] in {okul["harita"][k] for k in okul["harita"] if k.endswith("-mat")})
    assert f"Haftalık toplam: {toplam} ders saati" in ayse
    assert "9-A" in ayse and "Okul Müdürü" not in ayse


def test_ogretmen_tablosunda_farkli_subelerin_art_arda_saatleri_ayri_hucre():
    """Aynı ders, 9-A ve 9-B art arda: iki hücre, ikisinde de şube adı, aralarında koyu ayraç."""
    hafta = Hafta(gun_adlari=["Pazartesi"], gun_saatleri=[4], saat_sayisi=4, ogle_arasi_sonra=None,
                  zil=None, ogle_zili=None)
    hucreler = [Hucre(gun=0, saat=s, uzunluk=1, ders="Matematik", kisa_ad="MAT", renk="#2563eb", sube=sube,
                      ogretmen="Ayşe Yılmaz") for s, sube in [(0, "9-A"), (1, "9-B")]]
    _yazitiplerini_kaydet()
    tablo = _haftalik_tablo(Cizelge(ad="Ayşe Yılmaz", tur="ogretmen", hucreler=hucreler), hafta, 500, 300)
    cizgiler = {(k[0], k[1], k[2]) for k in tablo._linecmds if k[0] in ("LINEABOVE", "LINEBELOW")}  # noqa: SLF001
    assert ("LINEBELOW", (1, 1), (1, 1)) in cizgiler and ("LINEABOVE", (1, 2), (1, 2)) in cizgiler
    metinler = [p.text for p in tablo._cellvalues[1][1] + tablo._cellvalues[2][1]]  # noqa: SLF001
    assert "9-A" in metinler and "9-B" in metinler


def test_tek_sube_ve_tek_ogretmen_imza_alaniyla(istemci, okul, hazir_program):
    yanit = istemci.get(f"{DP}/programlar/{hazir_program}/cikti/subeler.pdf",
                        params={"sinif_id": okul["harita"]["s-9b"], "imza": True}, headers=okul["baslik"])
    assert "9-B programı.pdf" in yanit.headers["content-disposition"].replace("%20", " ").replace("%C4%B1", "ı")
    metinler = sayfa_metinleri(PdfReader(BytesIO(yanit.content)))
    assert len(metinler) == 1 and "9-B haftalık ders programı" in metinler[0] and "Okul Müdürü" in metinler[0]
    metinler = sayfa_metinleri(pdf_al(istemci, okul, hazir_program, "ogretmenler.pdf", ogretmen_id=okul["harita"]["o-ali"]))
    assert len(metinler) == 1 and "Ali Çelik haftalık ders programı" in metinler[0]
    yanit = istemci.get(f"{DP}/programlar/{hazir_program}/cikti/subeler.pdf", params={"sinif_id": str(uuid.uuid4())},
                        headers=okul["baslik"])
    assert yanit.status_code == 404


def test_zil_saatleri_ve_ogle_arasi_sayfada(istemci, okul, hazir_program):
    yanit = istemci.patch("/api/okul", json={"ilk_ders_baslangic": "08:30", "ogle_arasi_sonra": 3}, headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    metin = sayfa_metinleri(pdf_al(istemci, okul, hazir_program, "subeler.pdf"))[0]
    assert "08:30–09:10" in metin and "Öğle arası · 10:50–11:30" in metin


def test_carsaf_liste_a3_yatay_butun_okul(istemci, okul, hazir_program):
    pdf = pdf_al(istemci, okul, hazir_program, "carsaf.pdf")
    assert (round(pdf.pages[0].mediabox.width), round(pdf.pages[0].mediabox.height)) == (1191, 842)
    metin = "".join(sayfa_metinleri(pdf))
    assert "Çarşaf liste (öğretmenler)" in metin
    assert all(ad in metin for ad in ["Ayşe Yılmaz", "Mehmet Kaya", "Zeynep Demir", "Ali Çelik", "Fatma Şahin"])
    metin = "".join(sayfa_metinleri(pdf_al(istemci, okul, hazir_program, "carsaf.pdf", satir="sube")))
    assert "Çarşaf liste (şubeler)" in metin and all(s in metin for s in ["9-A", "9-B", "10-A"])


def test_carsaf_gunleri_sigmazsa_gruplara_boler():
    def hafta(gun, saat):
        return Hafta(gun_adlari=["G"] * gun, gun_saatleri=[saat] * gun, saat_sayisi=saat, ogle_arasi_sonra=None,
                     zil=None, ogle_zili=None)

    genislik = 400 * 2.8346  # A3 yatay, kenarlar düşülmüş (pt)
    assert carsaf_gun_gruplari(hafta(5, 8), genislik) == [[0, 1, 2, 3, 4]]
    gruplar = carsaf_gun_gruplari(hafta(6, 12), genislik)
    assert len(gruplar) == 2 and sum(gruplar, []) == list(range(6))


def test_hazir_olmayan_programin_ciktisi_yok(istemci, okul, oturum_fabrikasi):
    p = program_ekle(oturum_fabrikasi, okul["id"], durum="bekliyor")
    for yol in ("subeler.pdf", "ogretmenler.pdf", "carsaf.pdf", "program.xlsx"):
        yanit = istemci.get(f"{DP}/programlar/{p}/cikti/{yol}", headers=okul["baslik"])
        assert yanit.status_code == 409 and "hazır değil" in yanit.json()["detail"]


# --- okul izolasyonu ---------------------------------------------------------------------------


def test_baska_okul_cikti_alamaz(istemci, okul, hazir_program, okul_olustur):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    p, h = hazir_program, okul["harita"]
    istekler = [
        ("subeler.pdf", {}), ("subeler.pdf", {"sinif_id": h["s-9a"]}), ("ogretmenler.pdf", {}),
        ("ogretmenler.pdf", {"ogretmen_id": h["o-ayse"]}), ("carsaf.pdf", {}), ("program.xlsx", {}),
    ]
    for yol, params in istekler:
        yanit = istemci.get(f"{DP}/programlar/{p}/cikti/{yol}", params=params, headers=b2)
        assert yanit.status_code == 404, (yol, yanit.status_code)
        assert istemci.get(f"{DP}/programlar/{p}/cikti/{yol}", params=params).status_code == 401


# --- Excel -------------------------------------------------------------------------------------


def excel_al(istemci, okul, p):
    yanit = istemci.get(f"{DP}/programlar/{p}/cikti/program.xlsx", headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    assert yanit.headers["content-type"].startswith("application/vnd.openxmlformats")
    return load_workbook(BytesIO(yanit.content))


def test_excel_sekmeleri_ve_hucreleri(istemci, okul, hazir_program):
    kitap = excel_al(istemci, okul, hazir_program)
    assert kitap.sheetnames == ["Şubeler", "Öğretmenler", "Çarşaf (öğretmenler)", "Çarşaf (şubeler)", "Liste"]
    subeler = kitap["Şubeler"]
    assert subeler["A1"].value == "9-A haftalık ders programı"
    assert [subeler.cell(3, k).value for k in range(1, 8)] == ["Saat", "Zil", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    # Blok: 9-A Matematik üç blok, her biri iki satırlık birleşik hücre; her şube ayrı sayfa.
    mat = [h for h in subeler.iter_rows(min_row=4, max_row=9) for h in h if h.value and h.value.startswith("Matematik")]
    assert len(mat) == 3
    birlesik = {str(a) for a in subeler.merged_cells.ranges}
    assert all(f"{h.coordinate}:{h.column_letter}{h.row + 1}" in birlesik for h in mat)
    assert len(subeler.row_breaks.brk) == 2
    assert subeler.page_setup.orientation == "landscape" and subeler.sheet_properties.pageSetUpPr.fitToPage

    ogretmenler = kitap["Öğretmenler"]
    basliklar = [h.value for h in ogretmenler["A"] if h.value and "haftalık ders programı" in str(h.value)]
    assert "Ayşe Yılmaz haftalık ders programı" in basliklar and len(basliklar) == 5


def test_excel_carsaf_ve_liste_filtrelenebilir(istemci, okul, hazir_program):
    kitap = excel_al(istemci, okul, hazir_program)
    carsaf = kitap["Çarşaf (öğretmenler)"]
    adlar = [carsaf.cell(r, 1).value for r in range(3, carsaf.max_row + 1)]
    assert sorted(adlar) == sorted(["Ayşe Yılmaz", "Mehmet Kaya", "Zeynep Demir", "Ali Çelik", "Fatma Şahin"])
    assert carsaf.auto_filter.ref.startswith("A2:") and carsaf.freeze_panes == "B3"
    assert carsaf.print_title_rows == "$1:$2" and int(carsaf.page_setup.paperSize) == int(carsaf.PAPERSIZE_A3)
    # Toplam sütunu yerleşimlerle aynı (Ayşe: matematik dersleri).
    ayse = adlar.index("Ayşe Yılmaz") + 3
    toplam = sum(1 for y in yerlesimler(istemci, okul, hazir_program)
                 if y["ders_atama_id"] in {okul["harita"][k] for k in okul["harita"] if k.endswith("-mat")})
    assert carsaf.cell(ayse, carsaf.max_column).value == toplam

    liste = kitap["Liste"]
    assert [h.value for h in liste[1]] == ["Şube", "Ders", "Kısa ad", "Öğretmen", "Gün", "Gün no", "Saat", "Zil", "Blok (saat)"]
    assert liste.max_row - 1 == len(yerlesimler(istemci, okul, hazir_program))
    assert liste.auto_filter.ref == f"A1:I{liste.max_row}"
    # 9-A Türk Dili ve Edebiyatı 5 saat (öğretmeni Mehmet Kaya): listede 5 satır.
    tde = [r for r in liste.iter_rows(min_row=2, values_only=True) if r[0] == "9-A" and r[1] == "Türk Dili ve Edebiyatı"]
    assert len(tde) == 5 and {r[3] for r in tde} == {"Mehmet Kaya"}
