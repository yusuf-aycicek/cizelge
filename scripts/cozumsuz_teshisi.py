"""Çözümsüz örnek teşhisi: tam dolu bir sınıfın bütün öğretmenleri aynı saatte gelemez.

`gercekci_gosterimler.py` (4) bu örnekte ana çözücünün 60 sn içinde çözümsüzlüğü kanıtlayamadığını
gösterdi (durum `bilinmiyor`, çelişki analizi hiç çalışmadı). Bu betik ayrı ayrı ölçer:
1. yalnızca zorunlu kısıtlarla (esnek hedef olmadan) çözümsüzlük ne kadar sürede kanıtlanıyor,
2. çelişki analizi doğrudan çağrılınca ne kadar sürüyor ve ne buluyor.

Kullanım: cozucu/.venv/Scripts/python.exe scripts/cozumsuz_teshisi.py veri/gercekci.json
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from dataclasses import replace

from ortools.sat.python import cp_model

from cozucu import Musaitlik, MusaitlikDurumu
from cozucu.celiski import celiskileri_bul
from cozucu.kisitlar import Baglam, kurallari_hazirla
from cozucu.veri_io import girdi_oku


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    girdi = girdi_oku(sys.argv[1])
    saat = Counter()
    for a in girdi.atamalar:
        saat[a.sinif_id] += a.haftalik_saat
    hedef = next(s for s in girdi.siniflar if saat[s.id] == girdi.ayar.haftalik_kapasite)
    ogretmenler = sorted({a.ogretmen_id for a in girdi.atamalar if a.sinif_id == hedef.id})
    cozumsuz = replace(
        girdi,
        musaitlikler=[m for m in girdi.musaitlikler if not (m.gun == 0 and m.saat == 0 and m.ogretmen_id in ogretmenler)]
        + [Musaitlik(o, 0, 0, MusaitlikDurumu.GELEMEZ) for o in ogretmenler],
    )
    print(f"{hedef.ad}: {saat[hedef.id]} saat, {len(ogretmenler)} öğretmen, hepsi Pazartesi 1. saatte gelemez\n", flush=True)

    b = Baglam.kur(cozumsuz)
    for k in kurallari_hazirla(cozumsuz):
        if k.zorunlu:
            k.uygula(b)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 60
    s.parameters.num_workers = 8
    t = time.perf_counter()
    durum = s.solve(b.model)
    print(f"1. Yalnızca zorunlu kısıtlar: {s.status_name(durum)}, {time.perf_counter() - t:.1f} sn", flush=True)

    t = time.perf_counter()
    celiskiler = celiskileri_bul(cozumsuz, 30)
    print(f"2. Çelişki analizi (bütçe 30 sn): {time.perf_counter() - t:.1f} sn, {len(celiskiler)} çelişki", flush=True)
    for c in celiskiler:
        print(f"\n```\n{c.mesaj}\n```\nMadde sayısı: {c.mesaj.count(chr(10))}", flush=True)


if __name__ == "__main__":
    main()
