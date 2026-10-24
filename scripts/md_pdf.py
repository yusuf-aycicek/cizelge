"""Markdown -> PDF (A4): küçük bir Markdown çevirici + Edge (web/ içindeki Playwright ile).

Kullanım (depo kökünden):
    python scripts/md_pdf.py docs/rapor.md docs/rapor.pdf

Yalnızca bu depodaki belgelerin kullandığı Markdown alt kümesini anlar: başlıklar, paragraflar,
madde ve numaralı listeler, tablolar, kod blokları, alıntılar, resimler, satır içi kod, kalın yazı,
bağlantılar. "<" ile başlayan satırlar ham HTML olarak aynen geçer (kapak, sayfa sonu). Resim yolları
Markdown dosyasının dizinine göre çözülür. Gerekenler: Node ve `web/node_modules` (npm ci), Edge.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"

STIL = """
@page { size: A4; margin: 20mm 18mm 20mm 18mm;
  @bottom-center { content: counter(page); font: 9pt "DejaVu Sans", "Segoe UI", sans-serif; color: #666; } }
@page :first { @bottom-center { content: none; } }
body { font: 10.5pt/1.5 "Segoe UI", "DejaVu Sans", sans-serif; color: #1d1d1d; }
h1 { font-size: 20pt; } h2 { font-size: 15pt; margin-top: 1.4em; border-bottom: 1px solid #bbb; padding-bottom: .15em; }
h3 { font-size: 12pt; margin-top: 1.1em; } h2, h3 { break-after: avoid; }
p, li { text-align: justify; } li { margin: .15em 0; }
code { font: 9pt Consolas, "DejaVu Sans Mono", monospace; background: #f3f1ed; padding: 0 .2em; border-radius: 2px; }
pre { background: #f3f1ed; padding: .6em .8em; border-radius: 3px; break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: .6em 0; font-size: 9pt; break-inside: auto; }
th, td { border: 1px solid #c8c3ba; padding: .25em .4em; vertical-align: top; text-align: left; }
th { background: #efe9df; } tr { break-inside: avoid; }
blockquote { margin: .6em 0; padding: .3em .9em; border-left: 3px solid #b8955a; background: #fbf7ec; }
figure { margin: .6em 0; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 205mm; }
.sayfa-sonu { break-after: page; }
.kapak { text-align: center; padding-top: 35mm; }
.kapak-kurum { font-size: 14pt; line-height: 1.6; }
.kapak-baslik { font-size: 24pt; margin: 30mm 0 12mm; border: none; }
.kapak-ders { font-size: 14pt; margin-bottom: 40mm; }
.kapak-yazar { font-size: 13pt; line-height: 1.6; } .kapak-tarih { margin-top: 20mm; color: #555; }
"""


def satir_ici(metin: str) -> str:
    parcalar = re.split(r"(`[^`]+`)", metin)
    sonuc = []
    for p in parcalar:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            sonuc.append(f"<code>{html.escape(p[1:-1])}</code>")
            continue
        p = html.escape(p, quote=False)
        p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', p)
        sonuc.append(p)
    return "".join(sonuc)


def hucreler(satir: str) -> list[str]:
    return [h.strip() for h in satir.strip().strip("|").split("|")]


def cevir(md: str) -> str:
    satirlar = md.splitlines()
    cikti: list[str] = []
    i = 0
    while i < len(satirlar):
        s = satirlar[i]
        if not s.strip():
            i += 1
            continue
        if s.lstrip().startswith("<"):
            cikti.append(s)
            i += 1
        elif s.startswith("```"):
            j = i + 1
            while j < len(satirlar) and not satirlar[j].startswith("```"):
                j += 1
            cikti.append("<pre><code>" + html.escape("\n".join(satirlar[i + 1 : j])) + "</code></pre>")
            i = j + 1
        elif m := re.match(r"^(#{1,4}) (.+)$", s):
            n = len(m[1])
            cikti.append(f"<h{n}>{satir_ici(m[2])}</h{n}>")
            i += 1
        elif m := re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", s):
            cikti.append(f'<figure><img src="{m[2]}" alt="{html.escape(m[1])}"></figure>')
            i += 1
        elif s.startswith("|"):
            j = i
            while j < len(satirlar) and satirlar[j].startswith("|"):
                j += 1
            tablo = satirlar[i:j]
            bas = "".join(f"<th>{satir_ici(h)}</th>" for h in hucreler(tablo[0]))
            govde = "".join(
                "<tr>" + "".join(f"<td>{satir_ici(h)}</td>" for h in hucreler(t)) + "</tr>" for t in tablo[2:]
            )
            cikti.append(f"<table><thead><tr>{bas}</tr></thead><tbody>{govde}</tbody></table>")
            i = j
        elif s.startswith(">"):
            j = i
            while j < len(satirlar) and satirlar[j].startswith(">"):
                j += 1
            ic = " ".join(t.lstrip("> ").strip() for t in satirlar[i:j])
            cikti.append(f"<blockquote><p>{satir_ici(ic)}</p></blockquote>")
            i = j
        elif re.match(r"^(- |\d+\. )", s):
            numarali = bool(re.match(r"^\d+\. ", s))
            maddeler: list[str] = []
            j = i
            while j < len(satirlar):
                t = satirlar[j]
                if re.match(r"^(- |\d+\. )", t):
                    maddeler.append(re.sub(r"^(- |\d+\. )", "", t).strip())
                elif t.startswith("  ") and t.strip() and maddeler:
                    maddeler[-1] += " " + t.strip()
                else:
                    break
                j += 1
            etiket = "ol" if numarali else "ul"
            cikti.append(f"<{etiket}>" + "".join(f"<li>{satir_ici(m)}</li>" for m in maddeler) + f"</{etiket}>")
            i = j
        else:
            j = i
            parca = []
            while j < len(satirlar) and satirlar[j].strip() and not re.match(r"^(#|\||```|>|- |\d+\. |!\[|<)", satirlar[j]):
                parca.append(satirlar[j].strip())
                j += 1
            if not parca:  # tanınmayan satır: paragraf olarak geç
                parca, j = [s.strip()], i + 1
            cikti.append(f"<p>{satir_ici(' '.join(parca))}</p>")
            i = j
    return "\n".join(cikti)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    kaynak, hedef = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    govde = cevir(kaynak.read_text(encoding="utf-8"))
    baslik = re.search(r"<h1[^>]*>(.*?)</h1>", govde)
    sayfa = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><base href="{kaynak.parent.as_uri()}/">'
             f"<title>{baslik[1] if baslik else kaynak.stem}</title><style>{STIL}</style></head><body>{govde}</body></html>")
    with tempfile.TemporaryDirectory() as gecici:
        yol = Path(gecici) / "belge.html"
        yol.write_text(sayfa, encoding="utf-8")
        # Yazdırma, arayüzün Playwright'ı ve bilgisayardaki Edge ile (web/scripts/pdf-yazdir.mjs).
        sonuc = subprocess.run(["node", "scripts/pdf-yazdir.mjs", str(yol), str(hedef)], cwd=WEB,
                               shell=os.name == "nt")
    if sonuc.returncode != 0 or not hedef.exists():
        return sonuc.returncode or 1
    print(f"{hedef}  {hedef.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
