"""Zamana göre kalite ölçümü: çözücü verilen anlarda ne kadar iyi bir program bulmuş?

Tek bir uzun çalıştırma yapılır. Her iyileşen ara çözüm zamanıyla kaydedilir. Her kontrol
noktasında (ör. 10, 30, 60, 120. saniye) o ana kadarki en iyi çözüm bağımsız `kalite.olc` ile
ölçülür. Böylece "60 saniyede dursaydık ne elde ederdik" sorusu dört ayrı çalıştırma
yapmadan cevaplanır.

Toplam ceza iki türlü raporlanır:
- `model`: CP-SAT'ın amaç değeri.
- `gercek`: bağımsız ölçümlerin ağırlıklı toplamı.
En iyi çözümde ikisi eşittir. Ara çözümlerde model değeri büyük olabilir, çünkü yardımcı
değişkenler henüz sıkılaşmamış olabilir. Kullanıcının göreceği kalite `gercek` değeridir.

Çok iş parçacıklı CP-SAT deterministik değildir. Bu yüzden her ölçüm birkaç tohumla tekrarlanır.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cozucu.cpsat import CpSatCozucu
from cozucu.dogrulama import dogrula
from cozucu.kalite import KaliteOlcumu, agirlikli_ceza, olc
from cozucu.kisitlar import etkin_agirliklar
from cozucu.model import CozumDurumu, CozumGirdisi, Yerlesim

VARSAYILAN_NOKTALAR = (10.0, 30.0, 60.0, 120.0)


@dataclass(frozen=True)
class KontrolNoktasi:
    tohum: int
    saniye: float
    model_ceza: int | None  # None: o ana kadar hiç çözüm yok
    gercek_ceza: int | None
    olcum: KaliteOlcumu | None


@dataclass(frozen=True)
class Calistirma:
    tohum: int
    ilk_cozum_sn: float | None
    iyilesme_sayisi: int
    son_durum: CozumDurumu
    noktalar: list[KontrolNoktasi]


# (tohum, gözlemci) -> çözücü. Farklı stratejileri (ör. iki aşamalı) aynı ölçümle karşılaştırmak için.
CozucuFabrikasi = Callable[[int, Callable[[float, int, list[Yerlesim]], None]], CpSatCozucu]


def varsayilan_fabrika(tohum: int, gozlemci) -> CpSatCozucu:
    return CpSatCozucu(tohum=tohum, gozlemci=gozlemci)


def olc_zamana_gore(
    girdi: CozumGirdisi,
    tohum: int = 0,
    noktalar: Sequence[float] = VARSAYILAN_NOKTALAR,
    fabrika: CozucuFabrikasi = varsayilan_fabrika,
) -> Calistirma:
    kayitlar: list[tuple[float, int, list[Yerlesim]]] = []

    def kaydet(sure: float, amac: int, yerlesimler: list[Yerlesim]) -> None:
        kayitlar.append((sure, amac, yerlesimler))

    sonuc = fabrika(tohum, kaydet).coz(girdi, max(noktalar))
    agirliklar = etkin_agirliklar(girdi)
    sonuclar: list[KontrolNoktasi] = []
    for n in noktalar:
        onceki = [k for k in kayitlar if k[0] <= n]
        if not onceki:
            sonuclar.append(KontrolNoktasi(tohum, n, None, None, None))
            continue
        _sure, amac, yerlesimler = onceki[-1]
        hatalar = dogrula(girdi, yerlesimler)
        if hatalar:
            raise AssertionError(f"Ara çözüm geçersiz ({n} sn): {hatalar[0]}")
        o = olc(girdi, yerlesimler)
        sonuclar.append(KontrolNoktasi(tohum, n, amac, agirlikli_ceza(o, agirliklar), o))
    return Calistirma(
        tohum=tohum,
        ilk_cozum_sn=kayitlar[0][0] if kayitlar else None,
        iyilesme_sayisi=len(kayitlar),
        son_durum=sonuc.durum,
        noktalar=sonuclar,
    )


def tablo(calistirmalar: list[Calistirma]) -> str:
    """Markdown tablo: her tohum ve kontrol noktası bir satır."""
    satirlar = [
        "| Tohum | Saniye | Gerçek ceza | Model ceza | Sınıf boşluğu | Pencere | Bölünmüş | "
        "Tercih etmez | Eksik boş gün |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in calistirmalar:
        for k in c.noktalar:
            if k.olcum is None:
                satirlar.append(f"| {c.tohum} | {k.saniye:g} | çözüm yok | | | | | | |")
                continue
            o = k.olcum
            satirlar.append(
                f"| {c.tohum} | {k.saniye:g} | {k.gercek_ceza} | {k.model_ceza} | {o.sinif_boslugu} | "
                f"{o.ogretmen_penceresi} | {o.bolunmus_ders} | {o.tercih_etmez} | {o.eksik_bos_gun} |"
            )
    ozet = [
        f"- Tohum {c.tohum}: ilk çözüm {c.ilk_cozum_sn:.1f} sn, {c.iyilesme_sayisi} iyileşme, "
        f"son durum {c.son_durum.value}"
        if c.ilk_cozum_sn is not None
        else f"- Tohum {c.tohum}: hiç çözüm bulunamadı ({c.son_durum.value})"
        for c in calistirmalar
    ]
    return "\n".join(satirlar + [""] + ozet)


def main(argv: list[str] | None = None) -> None:
    import argparse
    import sys

    from cozucu.veri_io import girdi_oku

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Zamana göre kalite ölçümü.")
    p.add_argument("veri")
    p.add_argument("--tohum", type=int, nargs="+", default=[0, 1, 2])
    p.add_argument("--noktalar", type=float, nargs="+", default=list(VARSAYILAN_NOKTALAR))
    a = p.parse_args(argv)
    girdi = girdi_oku(a.veri)
    baslangic = time.perf_counter()
    print(f"## {a.veri}\n", flush=True)
    calistirmalar = []
    for t in a.tohum:  # her çalıştırma bitince yazılır: ölçüm yarıda kalırsa sonuçlar kaybolmaz
        calistirmalar.append(olc_zamana_gore(girdi, t, a.noktalar))
        print(f"### Tohum {t}\n\n{tablo(calistirmalar[-1:])}\n", flush=True)
    print(f"### Hepsi\n\n{tablo(calistirmalar)}")
    print(f"\nToplam ölçüm süresi: {time.perf_counter() - baslangic:.0f} sn")


if __name__ == "__main__":
    main()
