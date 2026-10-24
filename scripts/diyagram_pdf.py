"""docs/diyagramlar/cikti/*.png -> docs/diyagramlar/diyagramlar.pdf (A3 yatay, çıktı alınabilir).

Kullanım (depo kökünden, reportlab kurulu bir Python ile; API'nin sanal ortamında vardır):
    api/.venv/Scripts/python scripts/diyagram_pdf.py

Sayfa sırası ve açıklamalar docs/diyagramlar/README.md'deki "## <numara> | <tür> | <başlık>"
bölümlerinden gelir: açıklama tek yerde yazılır. Önce PNG'ler üretilmiş olmalı
(scripts/diyagramlari_uret.py).
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

KOK = Path(__file__).resolve().parents[1]
DIZIN = KOK / "docs" / "diyagramlar"
YAZITIPI = KOK / "api" / "src" / "okulapi" / "moduller" / "ders_programi" / "cikti" / "yazitipi"
BOLUM = re.compile(r"^## (\d\d) \| ([^|]+) \| (.+)$")


def bolumler() -> list[tuple[str, str, str, str]]:
    """README.md -> [(numara, tür, başlık, açıklama)] (dosyadaki sırayla)."""
    sonuc, simdiki = [], None
    for satir in (DIZIN / "README.md").read_text(encoding="utf-8").splitlines():
        if m := BOLUM.match(satir):
            simdiki = [m[1], m[2].strip(), m[3].strip(), ""]
            sonuc.append(simdiki)
        elif simdiki is not None and satir.strip():
            simdiki[3] += (" " if simdiki[3] else "") + satir.strip()
    return [tuple(b) for b in sonuc]


def satirlara_bol(metin: str, yazitipi: str, boy: float, genislik: float) -> list[str]:
    satirlar, simdiki = [], ""
    for kelime in metin.split():
        deneme = f"{simdiki} {kelime}".strip()
        if pdfmetrics.stringWidth(deneme, yazitipi, boy) <= genislik:
            simdiki = deneme
        else:
            satirlar.append(simdiki)
            simdiki = kelime
    if simdiki:
        satirlar.append(simdiki)
    return satirlar


def main() -> int:
    pdfmetrics.registerFont(TTFont("DejaVu", str(YAZITIPI / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(YAZITIPI / "DejaVuSans-Bold.ttf")))
    gen, yuk = landscape(A3)
    kenar = 12 * mm
    liste = bolumler()
    pngler = {p.name[:2]: p for p in (DIZIN / "cikti").glob("*.png")}
    eksik = [n for n, *_ in liste if n not in pngler]
    if eksik:
        print(f"PNG yok: {eksik}; önce scripts/diyagramlari_uret.py", file=sys.stderr)
        return 1

    c = Canvas(str(DIZIN / "diyagramlar.pdf"), pagesize=(gen, yuk))
    c.setTitle("Çizelge – UML diyagramları")
    c.setAuthor("Yusuf Ayçiçek")

    # Kapak ve içindekiler
    c.setFont("DejaVu-Bold", 30)
    c.drawString(kenar * 2, yuk - 60 * mm, "Çizelge – Okul Ders Programı Oluşturma Sistemi")
    c.setFont("DejaVu", 18)
    c.drawString(kenar * 2, yuk - 75 * mm, "UML diyagramları (sınıf, nesne, dağıtım, paket)")
    c.setFont("DejaVu", 12)
    c.drawString(kenar * 2, yuk - 85 * mm, f"Kodun son hâlinden üretildi: {date.today():%d.%m.%Y}. "
                 "Adlar api/tests/test_diyagramlar.py ile kodla denetlenir.")
    y = yuk - 105 * mm
    for sayfa, (numara, tur, baslik, _) in enumerate(liste, start=2):
        c.setFont("DejaVu", 13)
        c.drawString(kenar * 2, y, f"Sayfa {sayfa:>2}   {numara}  {tur}: {baslik}")
        y -= 8 * mm
    c.showPage()

    for numara, tur, baslik, aciklama in liste:
        c.setFont("DejaVu-Bold", 16)
        c.drawString(kenar, yuk - kenar - 4 * mm, f"{numara}  {tur}: {baslik}")
        satirlar = satirlara_bol(aciklama, "DejaVu", 10.5, gen - 2 * kenar)
        alt = kenar + len(satirlar) * 5 * mm + 4 * mm
        c.setFont("DejaVu", 10.5)
        for i, satir in enumerate(satirlar):
            c.drawString(kenar, alt - 4 * mm - (i + 1) * 5 * mm, satir)
        resim = ImageReader(str(pngler[numara]))
        rg, ry = resim.getSize()
        kutu_g, kutu_y = gen - 2 * kenar, yuk - 2 * kenar - 12 * mm - alt + kenar
        olcek = min(kutu_g / rg, kutu_y / ry)
        g, h = rg * olcek, ry * olcek
        c.drawImage(resim, (gen - g) / 2, alt + (kutu_y - h) / 2, g, h)
        c.setFont("DejaVu", 8)
        c.drawRightString(gen - kenar, kenar / 2, f"{pngler[numara].name}  ·  kaynak: docs/diyagramlar/{pngler[numara].stem}.puml")
        c.showPage()
    c.save()
    print(f"{(DIZIN / 'diyagramlar.pdf').relative_to(KOK)}  {len(liste) + 1} sayfa")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
