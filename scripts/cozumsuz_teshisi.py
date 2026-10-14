"""Çözümsüz örnek teşhisi: tam dolu bir sınıfın bütün öğretmenleri aynı saatte gelemez.

`gercekci_gosterimler.py` (4) bu örnekte ana çözücünün 60 sn içinde çözümsüzlüğü kanıtlayamadığını
gösterdi (durum `bilinmiyor`, çelişki analizi hiç çalışmadı). Bu betik ayrı ayrı ölçer:
1. yalnızca zorunlu kısıtlarla (esnek hedef olmadan) çözümsüzlük ne kadar sürede kanıtlanıyor,
2. çelişki analizi doğrudan çağrılınca ne kadar sürüyor ve ne buluyor.

Kullanım: cozucu/.venv/Scripts/python.exe scripts/cozumsuz_teshisi.py veri/gercekci.json [--analiz] [--ikinci-kontrol]
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from dataclasses import replace

from ortools.sat.python import cp_model

from cozucu import CpSatCozucu, Musaitlik, MusaitlikDurumu
from cozucu.celiski import celiskileri_bul
from cozucu.kisitlar import Baglam, kurallari_hazirla
from cozucu.on_kontrol import _Kontrol
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

    if "--analiz" in sys.argv:
        t = time.perf_counter()
        celiskiler = celiskileri_bul(cozumsuz, 30)
        print(f"2. Çelişki analizi (bütçe 30 sn): {time.perf_counter() - t:.1f} sn, {len(celiskiler)} çelişki",
              flush=True)
        for c in celiskiler:
            print(f"\n```\n{c.mesaj}\n```\nMadde sayısı: {c.mesaj.count(chr(10))}", flush=True)

    # 3. Kullanıcının göreceği sonuç (sınıf müsaitliği ön kontrolü ile).
    t = time.perf_counter()
    sonuc = CpSatCozucu().coz(cozumsuz)
    print(f"\n3. Kullanıcının göreceği: durum {sonuc.durum.value}, {time.perf_counter() - t:.2f} sn", flush=True)
    for c in sonuc.celiskiler:
        print(f"[{c.tur}] {c.mesaj}", flush=True)

    # 4. Ön kontrol olmasaydı: ana çözüm -> (bilinmiyor) -> ikinci kontrol -> çelişki analizi.
    if "--ikinci-kontrol" in sys.argv:
        asil = _Kontrol.sinif_musaitligi
        _Kontrol.sinif_musaitligi = lambda self, onceki: []
        try:
            sureler = {}
            asil_ikinci = CpSatCozucu._uygunluk_kontrolu

            def olculen(self, g, sure):
                t2 = time.perf_counter()
                d = asil_ikinci(self, g, sure)
                sureler["ikinci"] = (time.perf_counter() - t2, d)
                return d

            CpSatCozucu._uygunluk_kontrolu = olculen
            t = time.perf_counter()
            sonuc = CpSatCozucu().coz(cozumsuz)
            toplam = time.perf_counter() - t
        finally:
            _Kontrol.sinif_musaitligi = asil
            CpSatCozucu._uygunluk_kontrolu = asil_ikinci
        ikinci = sureler.get("ikinci")
        print(f"\n4. Sınıf müsaitliği kontrolü kapalıyken: durum {sonuc.durum.value}, toplam {toplam:.1f} sn"
              + (f"; ikinci kontrol {ikinci[0]:.1f} sn (sonuç: {ikinci[1]})"
                 if ikinci else "; ikinci kontrole gerek kalmadı (ana çözüm kendisi kanıtladı)"), flush=True)
        for m in sonuc.mesajlar:
            print(f"  {m}", flush=True)
        for c in sonuc.celiskiler:
            print(f"  [{c.tur}] {c.mesaj.count(chr(10))} maddelik çelişki kümesi", flush=True)


if __name__ == "__main__":
    main()
