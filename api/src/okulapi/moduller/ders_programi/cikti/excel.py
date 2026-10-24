"""Excel çıktısı (openpyxl, ADR 0020). Yalnızca `ProgramCiktisi`'ni okur.

Sekmeler:
- Şubeler, Öğretmenler: her biri haftalık çizelge; aralarında sayfa sonu (her biri ayrı sayfa
  yazdırılır), blok dersler birleşik hücre;
- Çarşaf (öğretmenler), Çarşaf (şubeler): bütün okul tek tabloda; ad sütununda filtre, başlık
  satırları yazdırırken her sayfada tekrar;
- Liste: her ders saati bir satır (şube, ders, öğretmen, gün, saat, zil); filtrelenebilir, pivot
  tabloya uygun.
Hepsi yatay ve sayfa genişliğine sığdırılarak yazdırılır.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.worksheet import Worksheet

from okulapi.moduller.ders_programi.cikti.model import Cizelge, Hafta, ProgramCiktisi

INCE = Side(style="thin", color="8A8A8A")
KALIN = Side(style="medium", color="1F2328")
KENAR = Border(left=INCE, right=INCE, top=INCE, bottom=INCE)
BASLIK_ZEMIN = PatternFill("solid", fgColor="E6E9EE")
YOK_ZEMIN = PatternFill("solid", fgColor="ECECEC")
OGLE_ZEMIN = PatternFill("solid", fgColor="F3F3F3")
ORTA = Alignment(horizontal="center", vertical="center", wrap_text=True)
SOL = Alignment(horizontal="left", vertical="center", wrap_text=True)


def _stil(ws: Worksheet, ad: str, **ozellikler) -> str:
    """Adlandırılmış stil (kitapta bir kez kaydedilir). Hücreye ayrı ayrı yazı tipi, kenar ve zemin
    atamak büyük okulda saniyeler sürer (openpyxl her atamada stil nesnelerini karşılaştırır);
    adlandırılmış stil tek atamadır."""
    kitap = ws.parent
    if ad not in kitap.named_styles:
        kitap.add_named_style(NamedStyle(name=ad, **ozellikler))
    return ad


def _baslik(ws: Worksheet) -> str:
    return _stil(ws, "ç_başlık", font=Font(bold=True), fill=BASLIK_ZEMIN, alignment=ORTA, border=KENAR)


def _bos(ws: Worksheet, var: bool = True) -> str:
    return _stil(ws, "ç_boş", border=KENAR, alignment=ORTA) if var else _stil(ws, "ç_yok", border=KENAR, fill=YOK_ZEMIN)


def _ton(renk: str, oran: float = 0.8) -> PatternFill:
    """Ders renginin açık tonu (siyah-beyaz yazıcıda açık gri; yazı siyah kalır)."""
    r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
    karisim = "".join(f"{round(c + (255 - c) * oran):02X}" for c in (r, g, b))
    return PatternFill("solid", fgColor=karisim)


def _yazdirma(ws: Worksheet, cikti: ProgramCiktisi, kagit: int, baslik: str) -> None:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = kagit
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0  # yükseklik serbest: sayfa sayısı içeriğe göre
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.oddHeader.left.text = cikti.okul
    ws.oddHeader.center.text = f"{baslik} · {cikti.program}"
    ws.oddHeader.right.text = cikti.tarih.strftime("%d.%m.%Y")
    ws.oddFooter.right.text = "Sayfa &P / &N"


def _haftalik_sekme(ws: Worksheet, cikti: ProgramCiktisi, cizelgeler: list[Cizelge]) -> None:
    hafta = cikti.hafta
    gunler = len(hafta.gun_adlari)
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 13
    for g in range(gunler):
        ws.column_dimensions[get_column_letter(3 + g)].width = 24
    son_sutun = 2 + gunler
    r = 1
    for i, c in enumerate(cizelgeler):
        if i:
            ws.row_breaks.append(Break(id=r - 1))  # her çizelge ayrı sayfa
        ws.cell(r, 1, f"{c.ad} haftalık ders programı").font = Font(bold=True, size=14)
        alt = f"Haftalık toplam: {c.toplam_saat} ders saati" if c.tur == "ogretmen" else f"Haftalık {c.toplam_saat} ders saati"
        ws.cell(r + 1, 1, alt).font = Font(color="57606A")
        r += 2
        for k, metin in enumerate(["Saat", "Zil"] + hafta.gun_adlari, start=1):
            ws.cell(r, k, metin).style = _baslik(ws)
        r += 1
        satir_no: dict[int, int] = {}
        for s in range(hafta.saat_sayisi):
            satir_no[s] = r
            ws.row_dimensions[r].height = 34
            z = hafta.zil[s] if hafta.zil and s < len(hafta.zil) else None
            ws.cell(r, 1, f"{s + 1}. ders").style = _baslik(ws)
            ws.cell(r, 2, z.metin if z else "").style = _baslik(ws)
            for g in range(gunler):
                ws.cell(r, 3 + g).style = _bos(ws, hafta.var(g, s) or c.ortulen(g, s))
            r += 1
            if hafta.ogle_arasi_sonra is not None and s + 1 == hafta.ogle_arasi_sonra and s + 1 < hafta.saat_sayisi:
                oz = hafta.ogle_zili
                ws.cell(r, 1, "Öğle arası" + (f" · {oz.metin}" if oz else ""))
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=son_sutun)
                ws.cell(r, 1).style = _stil(ws, "ç_öğle", font=Font(italic=True, color="57606A", size=9),
                                            fill=OGLE_ZEMIN, alignment=ORTA)
                r += 1
        ikinci = "sube" if c.tur == "ogretmen" else "ogretmen"
        for h in c.hucreler:
            bas, son = satir_no[h.saat], satir_no[h.saat + h.uzunluk - 1]
            hucre = ws.cell(bas, 3 + h.gun, h.ders + (f"\n{getattr(h, ikinci)}" if getattr(h, ikinci) else ""))
            hucre.style = _stil(ws, f"ç_ders_{h.renk}", fill=_ton(h.renk), alignment=SOL, border=Border(
                left=Side(style="thick", color=h.renk[1:].upper()), right=INCE, top=INCE, bottom=INCE))
            if son > bas:
                ws.merge_cells(start_row=bas, start_column=3 + h.gun, end_row=son, end_column=3 + h.gun)
        r += 2


def _carsaf_sekme(ws: Worksheet, cikti: ProgramCiktisi, cizelgeler: list[Cizelge], tur: str) -> None:
    hafta: Hafta = cikti.hafta
    H = hafta.saat_sayisi
    ws.cell(2, 1, "Öğretmen" if tur == "ogretmen" else "Şube")
    ws.column_dimensions["A"].width = 22
    for g, gun in enumerate(hafta.gun_adlari):
        bas = 2 + g * H
        ws.cell(1, bas, gun)
        ws.merge_cells(start_row=1, start_column=bas, end_row=1, end_column=bas + H - 1)
        for s in range(H):
            ws.cell(2, bas + s, s + 1)
            ws.column_dimensions[get_column_letter(bas + s)].width = 7
    toplam_sutun = 2 + len(hafta.gun_adlari) * H
    ws.cell(2, toplam_sutun, "Toplam")
    ws.column_dimensions[get_column_letter(toplam_sutun)].width = 8
    for satir in (1, 2):
        for k in range(1, toplam_sutun + 1):
            ws.cell(satir, k).style = _baslik(ws)

    for i, c in enumerate(cizelgeler):
        r = 3 + i
        ws.row_dimensions[r].height = 28
        ws.cell(r, 1, c.ad).style = _stil(ws, "ç_ad", font=Font(bold=True), alignment=SOL, border=KENAR)
        for g in range(len(hafta.gun_adlari)):
            for s in range(H):
                ws.cell(r, 2 + g * H + s).style = _bos(ws, hafta.var(g, s) or c.ortulen(g, s))
        for h in c.hucreler:
            k = 2 + h.gun * H + h.saat
            metin = f"{h.sube}\n{h.kisa_ad}" if tur == "ogretmen" else f"{h.kisa_ad}\n{h.ogretmen}"
            ws.cell(r, k, metin).style = _stil(ws, f"ç_çarşaf_{h.renk}", fill=_ton(h.renk, 0.75), font=Font(size=8),
                                               alignment=ORTA, border=KENAR)
            if h.uzunluk > 1:
                ws.merge_cells(start_row=r, start_column=k, end_row=r, end_column=k + h.uzunluk - 1)
        ws.cell(r, toplam_sutun, c.toplam_saat).style = _bos(ws)
    son = 2 + len(cizelgeler)
    ws.auto_filter.ref = f"A2:{get_column_letter(toplam_sutun)}{son}"
    ws.freeze_panes = "B3"
    ws.print_title_rows = "1:2"
    ws.print_title_cols = "A:A"


def _liste_sekme(ws: Worksheet, cikti: ProgramCiktisi) -> None:
    hafta = cikti.hafta
    basliklar = ["Şube", "Ders", "Kısa ad", "Öğretmen", "Gün", "Gün no", "Saat", "Zil", "Blok (saat)"]
    ws.append(basliklar)
    for k, gen in enumerate([10, 26, 9, 22, 12, 7, 6, 13, 10], start=1):
        ws.column_dimensions[get_column_letter(k)].width = gen
        ws.cell(1, k).style = _baslik(ws)
    for c in cikti.subeler:
        for h in sorted(c.hucreler, key=lambda x: (x.gun, x.saat)):
            for s in range(h.saat, h.saat + h.uzunluk):
                z = hafta.zil[s] if hafta.zil and s < len(hafta.zil) else None
                ws.append([h.sube, h.ders, h.kisa_ad, h.ogretmen, hafta.gun_adlari[h.gun], h.gun + 1, s + 1,
                           z.metin if z else "", h.uzunluk])
    ws.auto_filter.ref = f"A1:{get_column_letter(len(basliklar))}{ws.max_row}"
    ws.freeze_panes = "A2"
    ws.print_title_rows = "1:1"


def program_xlsx(cikti: ProgramCiktisi) -> bytes:
    kitap = Workbook()
    kitap.properties.title = f"{cikti.okul} – {cikti.program}"
    kitap.properties.creator = "Çizelge"
    sekmeler = [
        ("Şubeler", lambda ws: _haftalik_sekme(ws, cikti, cikti.subeler), Worksheet.PAPERSIZE_A4),
        ("Öğretmenler", lambda ws: _haftalik_sekme(ws, cikti, cikti.ogretmenler), Worksheet.PAPERSIZE_A4),
        ("Çarşaf (öğretmenler)", lambda ws: _carsaf_sekme(ws, cikti, cikti.ogretmenler, "ogretmen"), Worksheet.PAPERSIZE_A3),
        ("Çarşaf (şubeler)", lambda ws: _carsaf_sekme(ws, cikti, cikti.subeler, "sube"), Worksheet.PAPERSIZE_A3),
        ("Liste", lambda ws: _liste_sekme(ws, cikti), Worksheet.PAPERSIZE_A4),
    ]
    for i, (ad, doldur, kagit) in enumerate(sekmeler):
        ws = kitap.active if i == 0 else kitap.create_sheet()
        ws.title = ad
        doldur(ws)
        _yazdirma(ws, cikti, kagit, ad)
    tampon = BytesIO()
    kitap.save(tampon)
    return tampon.getvalue()
