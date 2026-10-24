"""PDF çıktısı (ReportLab, ADR 0020): şube ve öğretmen programları (A4 yatay) ve çarşaf liste (A3 yatay).

Yalnızca `ProgramCiktisi`'ni okur. Türkçe karakterler için DejaVu Sans gömülür (ReportLab yalnızca
kullanılan harfleri gömer; dosya küçük kalır). Renk: hücre zemini dersin renginin açık tonu, solda
dersin renginde kalın çizgi; siyah-beyaz yazıcıda zemin açık gri, yazı siyah kalır.
"""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from okulapi.moduller.ders_programi.cikti.model import Cizelge, Hafta, ProgramCiktisi

_YAZITIPI = Path(__file__).parent / "yazitipi"
NORMAL, KALIN = "DejaVuSans", "DejaVuSans-Bold"


def _yazitiplerini_kaydet() -> None:
    if NORMAL not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(NORMAL, _YAZITIPI / "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont(KALIN, _YAZITIPI / "DejaVuSans-Bold.ttf"))
        pdfmetrics.registerFontFamily(NORMAL, normal=NORMAL, bold=KALIN, italic=NORMAL, boldItalic=KALIN)


CIZGI = colors.HexColor("#8a8a8a")
KOYU = colors.HexColor("#1f2328")
SOLUK = colors.HexColor("#57606a")
YOK_ZEMIN = colors.HexColor("#ececec")  # kısa günün olmayan saati
OGLE_ZEMIN = colors.HexColor("#f3f3f3")
BASLIK_ZEMIN = colors.HexColor("#e6e9ee")


def _ton(renk: str, oran: float = 0.82) -> colors.Color:
    """Rengin beyazla karışımı (açık zemin; yazı siyah kalır)."""
    c = colors.HexColor(renk)
    return colors.Color(c.red + (1 - c.red) * oran, c.green + (1 - c.green) * oran, c.blue + (1 - c.blue) * oran)


def _stil(boyut: float, kalin: bool = False, renk=KOYU, ortala: bool = False) -> ParagraphStyle:
    return ParagraphStyle("s", fontName=KALIN if kalin else NORMAL, fontSize=boyut, leading=boyut * 1.2,
                          textColor=renk, alignment=TA_CENTER if ortala else 0)


def _p(metin: str, stil: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(metin).replace("\n", "<br/>"), stil)


def tarih_metni(cikti: ProgramCiktisi) -> str:
    return cikti.tarih.strftime("%d.%m.%Y")


def _sayfa_cercevesi(cikti: ProgramCiktisi, alt_baslik: str) -> Callable:
    """Her sayfanın üstü (okul, program, tarih) ve altı (sayfa numarası)."""

    def ciz(tuval, belge) -> None:
        g, y = belge.pagesize
        tuval.saveState()
        tuval.setFillColor(KOYU)
        tuval.setFont(KALIN, 12)
        tuval.drawString(belge.leftMargin, y - 11 * mm, cikti.okul)
        tuval.setFont(NORMAL, 9)
        tuval.setFillColor(SOLUK)
        tuval.drawString(belge.leftMargin, y - 16 * mm, f"{alt_baslik} · {cikti.program}")
        tuval.drawRightString(g - belge.rightMargin, y - 11 * mm, tarih_metni(cikti))
        tuval.setStrokeColor(CIZGI)
        tuval.setLineWidth(0.5)
        tuval.line(belge.leftMargin, y - 18.5 * mm, g - belge.rightMargin, y - 18.5 * mm)
        tuval.setFont(NORMAL, 8)
        tuval.drawRightString(g - belge.rightMargin, 7 * mm, f"Sayfa {belge.page}")
        tuval.restoreState()

    return ciz


def _belge(cikti: ProgramCiktisi, boyut, alt_baslik: str, cizimler: list, kenar: float = 12 * mm) -> bytes:
    tampon = BytesIO()
    belge = SimpleDocTemplate(
        tampon, pagesize=boyut, leftMargin=kenar, rightMargin=kenar, topMargin=22 * mm, bottomMargin=12 * mm,
        title=f"{cikti.okul} – {alt_baslik}", author=cikti.okul, subject=cikti.program, creator="Çizelge",
    )
    cerceve = _sayfa_cercevesi(cikti, alt_baslik)
    belge.build(cizimler, onFirstPage=cerceve, onLaterPages=cerceve)
    return tampon.getvalue()


# --- şube ve öğretmen programları (A4 yatay, her biri ayrı sayfa) ------------------------------


def _haftalik_tablo(cizelge: Cizelge, hafta: Hafta, genislik: float, yukseklik: float) -> Table:
    gunler = len(hafta.gun_adlari)
    satirlar: list[list] = [[_p("", _stil(9))] + [_p(g, _stil(9.5, True, ortala=True)) for g in hafta.gun_adlari]]
    stil: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), BASLIK_ZEMIN),
        ("BACKGROUND", (0, 1), (0, -1), BASLIK_ZEMIN),
        ("GRID", (0, 0), (-1, -1), 0.5, CIZGI),
        ("BOX", (0, 0), (-1, -1), 1.2, KOYU),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    yukseklikler = [8 * mm]
    ogle_var = hafta.ogle_arasi_sonra is not None and hafta.ogle_arasi_sonra < hafta.saat_sayisi
    ders_yuksekligi = min(18 * mm, max(9 * mm, (yukseklik - 8 * mm - (6 * mm if ogle_var else 0)) / hafta.saat_sayisi))
    satir_no: dict[int, int] = {}
    for s in range(hafta.saat_sayisi):
        satir_no[s] = len(satirlar)
        satirlar.append([_p(hafta.saat_basligi(s), _stil(8, True))] + [""] * gunler)
        yukseklikler.append(ders_yuksekligi)
        if ogle_var and s + 1 == hafta.ogle_arasi_sonra:
            z = hafta.ogle_zili
            satirlar.append([_p("Öğle arası" + (f" · {z.metin}" if z else ""), _stil(7.5, renk=SOLUK, ortala=True))]
                            + [""] * gunler)
            r = len(satirlar) - 1
            stil += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), OGLE_ZEMIN),
                     ("TOPPADDING", (0, r), (-1, r), 1), ("BOTTOMPADDING", (0, r), (-1, r), 1)]
            yukseklikler.append(6 * mm)

    ikinci = "sube" if cizelge.tur == "ogretmen" else "ogretmen"
    for g in range(gunler):
        for s in range(hafta.saat_sayisi):
            r, c = satir_no[s], g + 1
            h = cizelge.hucre(g, s)
            if h:
                alt = getattr(h, ikinci)
                son = satir_no[s + h.uzunluk - 1]
                if cizelge.tur == "ogretmen":
                    # Aynı dersin farklı şubelerdeki art arda saatleri tek blok gibi görünmesin:
                    # şube adı kalın ve her hücrenin üstünde, altında koyu ayraç.
                    satirlar[r][c] = [_p(h.sube, _stil(9.5, True)), _p(h.ders, _stil(7.5, renk=SOLUK))]
                    stil += [("LINEABOVE", (c, r), (c, r), 1.2, KOYU), ("LINEBELOW", (c, son), (c, son), 1.2, KOYU)]
                else:
                    satirlar[r][c] = [_p(h.ders, _stil(9, True)), _p(alt, _stil(7.5, renk=SOLUK))] if alt else _p(h.ders, _stil(9, True))
                stil += [("SPAN", (c, r), (c, son)), ("BACKGROUND", (c, r), (c, son), _ton(h.renk)),
                         ("LINEBEFORE", (c, r), (c, son), 3, colors.HexColor(h.renk))]
            elif not hafta.var(g, s) and not cizelge.ortulen(g, s):
                stil.append(("BACKGROUND", (c, r), (c, r), YOK_ZEMIN))
    ilk = 28 * mm
    return Table(satirlar, colWidths=[ilk] + [(genislik - ilk) / gunler] * gunler, rowHeights=yukseklikler,
                 style=TableStyle(stil))


def _imza() -> Table:
    """Sağ altta "Okul Müdürü" imza alanı (ad ve imza elle yazılır)."""
    alan = Table([[""], [_p("Okul Müdürü", _stil(9.5, True, ortala=True))], [_p("Ad Soyad · İmza", _stil(7.5, renk=SOLUK, ortala=True))]],
                 colWidths=[60 * mm], rowHeights=[12 * mm, 5 * mm, 4 * mm],
                 style=TableStyle([("LINEBELOW", (0, 0), (0, 0), 0.6, KOYU), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    alan.hAlign = "RIGHT"
    return alan


def haftalik_pdf(cikti: ProgramCiktisi, cizelgeler: list[Cizelge], alt_baslik: str, imza: bool = False) -> bytes:
    """Her çizelge ayrı sayfa (A4 yatay). Öğretmen sayfasında haftalık toplam ders saati yazar."""
    _yazitiplerini_kaydet()  # paragraflar oluşturulurken yazı tipi kayıtlı olmalı
    sayfa = landscape(A4)
    genislik = sayfa[0] - 24 * mm
    yukseklik = sayfa[1] - 34 * mm - 11 * mm - (23 * mm if imza else 0) - 3 * mm
    cizimler: list = []
    for i, c in enumerate(cizelgeler):
        if i:
            cizimler.append(PageBreak())
        baslik = f"{c.ad} haftalık ders programı"
        ust = [_p(baslik, _stil(14, True))]
        if c.tur == "ogretmen":
            ust.append(_p(f"Haftalık toplam: {c.toplam_saat} ders saati", _stil(9.5, renk=SOLUK)))
        else:
            ust.append(_p(f"Haftalık {c.toplam_saat} ders saati", _stil(9.5, renk=SOLUK)))
        cizimler.append(KeepTogether(ust + [Spacer(1, 2 * mm), _haftalik_tablo(c, cikti.hafta, genislik, yukseklik)]))
        if imza:
            cizimler += [Spacer(1, 4 * mm), _imza()]
    if not cizelgeler:
        cizimler.append(_p("Bu programda gösterilecek ders yok.", _stil(11)))
    return _belge(cikti, sayfa, alt_baslik, cizimler)


# --- çarşaf liste (A3 yatay) -------------------------------------------------------------------

AD_SUTUNU, TOPLAM_SUTUNU, EN_DAR = 40 * mm, 11 * mm, 7.5 * mm


def carsaf_gun_gruplari(hafta: Hafta, kullanilabilir: float) -> list[list[int]]:
    """Günler, sayfaya sığan gruplara bölünür (sütun EN_DAR'dan daralmasın diye). Sığarsa tek grup."""
    gunler = list(range(len(hafta.gun_adlari)))
    alan = kullanilabilir - AD_SUTUNU - TOPLAM_SUTUNU
    gun_basina = max(1, int(alan // (hafta.saat_sayisi * EN_DAR)))
    return [gunler[i:i + gun_basina] for i in range(0, len(gunler), gun_basina)]


def _ogretmen_kisa(ad: str) -> str:
    """"Ayşe Yılmaz" -> "A. Yılmaz" (çarşaf hücresi dar)."""
    parcalar = ad.split()
    return ad if len(parcalar) < 2 else f"{parcalar[0][0]}. {parcalar[-1]}"


def _carsaf_tablo(cizelgeler: list[Cizelge], hafta: Hafta, gunler: list[int], genislik: float) -> Table:
    H = hafta.saat_sayisi
    sutun = (genislik - AD_SUTUNU - TOPLAM_SUTUNU) / (len(gunler) * H)
    kucuk = 6.3 if sutun < 10 * mm else 7
    ust1: list = [_p("", _stil(7))]
    ust2: list = [_p("Öğretmen" if cizelgeler and cizelgeler[0].tur == "ogretmen" else "Şube", _stil(7.5, True))]
    stil: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.35, CIZGI),
        ("BOX", (0, 0), (-1, -1), 1.2, KOYU),
        ("BACKGROUND", (0, 0), (-1, 1), BASLIK_ZEMIN),
        ("BACKGROUND", (0, 2), (0, -1), BASLIK_ZEMIN),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
    for i, g in enumerate(gunler):
        bas = 1 + i * H
        ust1 += [_p(hafta.gun_adlari[g], _stil(8, True, ortala=True))] + [""] * (H - 1)
        ust2 += [_p(str(s + 1), _stil(7, True, ortala=True)) for s in range(H)]
        stil += [("SPAN", (bas, 0), (bas + H - 1, 0)), ("LINEBEFORE", (bas, 0), (bas, -1), 1.2, KOYU)]
        if hafta.ogle_arasi_sonra and hafta.ogle_arasi_sonra < H:
            stil.append(("LINEBEFORE", (bas + hafta.ogle_arasi_sonra, 1), (bas + hafta.ogle_arasi_sonra, -1), 1.2, SOLUK))
    ust1.append("")
    ust2.append(_p("Top.", _stil(6.5, True, ortala=True)))
    stil.append(("LINEBEFORE", (-1, 0), (-1, -1), 1.2, KOYU))

    satirlar = [ust1, ust2]
    for c in cizelgeler:
        r = len(satirlar)
        satir: list = [_p(c.ad, _stil(7.5, True))] + [""] * (len(gunler) * H) + [_p(str(c.toplam_saat), _stil(7, ortala=True))]
        for i, g in enumerate(gunler):
            for s in range(H):
                k = 1 + i * H + s
                h = c.hucre(g, s)
                if h:
                    alt = h.sube if c.tur == "ogretmen" else _ogretmen_kisa(h.ogretmen)
                    ust = h.kisa_ad if c.tur == "sube" else h.sube
                    ikinci = h.kisa_ad if c.tur == "ogretmen" else alt
                    satir[k] = [_p(ust, _stil(kucuk, True, ortala=True)), _p(ikinci, _stil(kucuk - 0.8, renk=SOLUK, ortala=True))]
                    stil += [("SPAN", (k, r), (k + h.uzunluk - 1, r)),
                             ("BACKGROUND", (k, r), (k + h.uzunluk - 1, r), _ton(h.renk, 0.78))]
                elif not hafta.var(g, s) and not c.ortulen(g, s):
                    stil.append(("BACKGROUND", (k, r), (k, r), YOK_ZEMIN))
        satirlar.append(satir)
    return Table(satirlar, colWidths=[AD_SUTUNU] + [sutun] * (len(gunler) * H) + [TOPLAM_SUTUNU],
                 rowHeights=[6 * mm, 5 * mm] + [9.5 * mm] * len(cizelgeler), repeatRows=2, style=TableStyle(stil))


def carsaf_pdf(cikti: ProgramCiktisi, tur: str) -> bytes:
    """Bütün okul tek tabloda: satırlar öğretmenler (`tur="ogretmen"`) ya da şubeler, sütunlar gün ve
    saatler. Satırlar sayfaya sığmazsa tablo bölünür, başlık her sayfada tekrarlanır; günler sığmazsa
    gün gruplarına ayrılır (ör. Pazartesi-Çarşamba, Perşembe-Cuma)."""
    _yazitiplerini_kaydet()
    sayfa = landscape(A3)
    genislik = sayfa[0] - 20 * mm
    cizelgeler = cikti.ogretmenler if tur == "ogretmen" else cikti.subeler
    alt_baslik = "Çarşaf liste (öğretmenler)" if tur == "ogretmen" else "Çarşaf liste (şubeler)"
    cizimler: list = []
    for i, gunler in enumerate(carsaf_gun_gruplari(cikti.hafta, genislik)):
        if i:
            cizimler.append(PageBreak())
        cizimler.append(_carsaf_tablo(cizelgeler, cikti.hafta, gunler, genislik))
    return _belge(cikti, sayfa, alt_baslik, cizimler, kenar=10 * mm)
