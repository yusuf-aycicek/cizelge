"""Komut satırı: python -m cozucu <veri.json> [--sure 120] [--sinif 9-A] [--ogretmen "Ayşe Yılmaz"]

Programı üretir; durumu, kalite ölçülerini, sınıf ve öğretmen tablolarını ya da çözüm yoksa
nedenlerini yazdırır. `--kaydet` sonucu JSON olarak saklar; `--temel` önceki bir sonucu temel
alarak en az değişiklikle günceller.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from cozucu.anlatim import GUN_ADLARI
from cozucu.arayuz import VARSAYILAN_SURE_SINIRI_SN
from cozucu.cpsat import CpSatCozucu
from cozucu.dogrulama import dogrula
from cozucu.kalite import ders_gunleri, olc
from cozucu.model import CozumGirdisi, CozumSonucu, temel_program
from cozucu.veri_io import girdi_oku, sonuc_from_dict, sonuc_to_dict


def sinif_tablosu(girdi: CozumGirdisi, sonuc: CozumSonucu, sinif_id: str) -> str:
    atama = {a.id: a for a in girdi.atamalar}
    ders = {d.id: d.kisa_ad or d.ad for d in girdi.dersler}
    ogretmen = {o.id: _kisa_ad(o.ad) for o in girdi.ogretmenler}
    hucre = {}
    for y in sonuc.yerlesimler:
        a = atama[y.ders_atama_id]
        if a.sinif_id == sinif_id:
            hucre[y.gun, y.saat] = f"{ders[a.ders_id]} {ogretmen.get(a.ogretmen_id, '?')}" + ("*" if y.kilitli else "")
    return _tablo(girdi, hucre)


def ogretmen_tablosu(girdi: CozumGirdisi, sonuc: CozumSonucu, ogretmen_id: str) -> str:
    atama = {a.id: a for a in girdi.atamalar}
    ders = {d.id: d.kisa_ad or d.ad for d in girdi.dersler}
    sinif = {s.id: s.ad for s in girdi.siniflar}
    hucre = {}
    for y in sonuc.yerlesimler:
        a = atama[y.ders_atama_id]
        if a.ogretmen_id == ogretmen_id:
            hucre[y.gun, y.saat] = f"{sinif[a.sinif_id]} {ders[a.ders_id]}" + ("*" if y.kilitli else "")
    for m in girdi.musaitlikler:
        if m.ogretmen_id == ogretmen_id and (m.gun, m.saat) not in hucre:
            hucre[m.gun, m.saat] = "gelemez" if m.durum.value == "gelemez" else "(tercih etmez)"
    return _tablo(girdi, hucre)


def _tablo(girdi: CozumGirdisi, hucre: dict[tuple[int, int], str]) -> str:
    gunler = GUN_ADLARI[: girdi.ayar.gun_sayisi]
    genislik = max([12, *(len(v) for v in hucre.values())])
    satirlar = ["Saat | " + " | ".join(g.ljust(genislik) for g in gunler)]
    satirlar.append("-" * len(satirlar[0]))
    for s in range(girdi.ayar.gunluk_ders_saati):
        satirlar.append(
            f"{s + 1:>4} | " + " | ".join(hucre.get((g, s), "·").ljust(genislik) for g in range(len(gunler)))
        )
    return "\n".join(satirlar)


def _kisa_ad(ad: str) -> str:
    """"Ayşe Yılmaz" -> "A.Yılmaz"."""
    parcalar = ad.split()
    return f"{parcalar[0][0]}.{parcalar[-1]}" if len(parcalar) > 1 else ad


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="python -m cozucu", description="Haftalık ders programı üretir.")
    p.add_argument("veri", help="girdi JSON dosyası (veri/*.json)")
    p.add_argument("--sure", type=float, default=VARSAYILAN_SURE_SINIRI_SN,
                   help=f"süre sınırı, saniye (varsayılan {VARSAYILAN_SURE_SINIRI_SN:g})")
    p.add_argument("--sinif", nargs="*", help="yalnızca bu sınıfları yazdır (ör. 9-A); boş: hiçbiri")
    p.add_argument("--ogretmen", nargs="*", help="bu öğretmenlerin tablosunu da yazdır (ad ya da kimlik)")
    p.add_argument("--kaydet", help="sonucu bu JSON dosyasına yaz")
    p.add_argument("--temel", help="önceki bir sonuç JSON'u; en az değişiklikle güncelle")
    a = p.parse_args(argv)

    girdi = girdi_oku(a.veri)
    if a.temel:
        onceki = sonuc_from_dict(json.loads(Path(a.temel).read_text(encoding="utf-8")))
        girdi = replace(girdi, temel_yerlesimler=temel_program(girdi.atamalar, onceki.yerlesimler))

    sonuc = CpSatCozucu().coz(girdi, a.sure)
    print(f"Durum: {sonuc.durum.value}   Süre: {sonuc.sure_sn:.1f} sn   Toplam ceza: {sonuc.toplam_ceza}")
    for m in sonuc.mesajlar:
        print(f"  {m}")
    for c in sonuc.celiskiler:
        print(f"\n[{c.tur}] {c.mesaj}")
    if a.kaydet:
        Path(a.kaydet).write_text(json.dumps(sonuc_to_dict(sonuc), ensure_ascii=False), encoding="utf-8")
    if not sonuc.basarili:
        return 1

    hatalar = dogrula(girdi, sonuc.yerlesimler)
    o = olc(girdi, sonuc.yerlesimler)
    print(f"Doğrulama: {'geçti' if not hatalar else f'{len(hatalar)} HATA: ' + hatalar[0]}")
    print(
        f"Ölçüler: sınıf boşluğu {o.sinif_boslugu}, öğretmen penceresi {o.ogretmen_penceresi}, "
        f"bölünmüş ders {o.bolunmus_ders}, tercih etmez {o.tercih_etmez}, eksik boş gün {o.eksik_bos_gun}"
        + (f", değişen hücre {o.degisen_yerlesim}/{len(set(girdi.temel_yerlesimler))}" if girdi.temel_yerlesimler else "")
    )

    siniflar = girdi.siniflar if a.sinif is None else [s for s in girdi.siniflar if s.ad in a.sinif]
    for s in siniflar:
        print(f"\n### {s.ad}\n{sinif_tablosu(girdi, sonuc, s.id)}")
    gunler = ders_gunleri(girdi, sonuc.yerlesimler)
    for secim in a.ogretmen or []:
        for og in [o for o in girdi.ogretmenler if secim in (o.ad, o.id)]:
            yuk = sum(x.haftalik_saat for x in girdi.atamalar if x.ogretmen_id == og.id)
            print(f"\n### {og.ad} ({og.brans}, {yuk} saat, {gunler.get(og.id, 0)} gün)\n"
                  f"{ogretmen_tablosu(girdi, sonuc, og.id)}")
    return 0 if not hatalar else 2


if __name__ == "__main__":
    raise SystemExit(main())
