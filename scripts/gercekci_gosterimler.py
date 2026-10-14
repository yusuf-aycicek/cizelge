"""Gerçekçi set gösterimleri (docs/olcumler.md için):

(2) Bir sınıfın ve bir öğretmenin haftalık programı (60 sn'lik çözüm).
(3) En az değişiklik: en yoğun öğretmenin en yoğun günü kapatılır; temel programla 10 ve 60 sn,
    sıfırdan 60 sn. Kaç ders değişiyor, ilk çözüm ne zaman geliyor?
(4) Bilerek çözümsüz örnek: tam dolu (40 saat) bir sınıfın bütün öğretmenleri Pazartesi 1. saatte
    gelemez. Ön kontrolden geçer, çözümü yoktur. Çelişki analizinin süresi ve mesajı.

Her bölüm bittiği anda yazdırılır (flush). Çıktıyı dosyaya yönlendirin:
    cozucu/.venv/Scripts/python.exe scripts/gercekci_gosterimler.py veri/gercekci.json \
        > scripts/sonuclar/gosterimler.md
Ölçüm sırasında işlemci kullanan başka bir iş çalıştırılmamalıdır.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from dataclasses import replace

from cozucu import CpSatCozucu, Musaitlik, MusaitlikDurumu, dogrula, olc, temel_program
from cozucu import cpsat
from cozucu.anlatim import GUN_ADLARI
from cozucu.cli import ogretmen_tablosu, sinif_tablosu
from cozucu.kalite import ders_gunleri
from cozucu.on_kontrol import on_kontrol
from cozucu.veri_io import girdi_oku


def yaz(metin=""):
    print(metin, flush=True)


def olcu_metni(o):
    return (f"sınıf boşluğu {o.sinif_boslugu}, pencere {o.ogretmen_penceresi}, bölünmüş {o.bolunmus_ders}, "
            f"tercih etmez {o.tercih_etmez}, eksik boş gün {o.eksik_bos_gun}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    girdi = girdi_oku(sys.argv[1])
    ad = {o.id: o.ad for o in girdi.ogretmenler}
    atama = {a.id: a for a in girdi.atamalar}
    yaz(f"# Gerçekçi set gösterimleri ({sys.argv[1]})\n")

    # --- (2) sınıf ve öğretmen programı ----------------------------------------------------
    temel_sonuc = CpSatCozucu().coz(girdi, 60)
    assert temel_sonuc.basarili and dogrula(girdi, temel_sonuc.yerlesimler) == []
    o = olc(girdi, temel_sonuc.yerlesimler)
    yaz(f"## (2) Haftalık program (60 sn, durum {temel_sonuc.durum.value}, ceza {temel_sonuc.toplam_ceza})\n")
    yaz(f"Ölçüler: {olcu_metni(o)}\n")
    sinif = girdi.siniflar[0]
    yaz(f"### {sinif.ad}\n\n```\n{sinif_tablosu(girdi, temel_sonuc, sinif.id)}\n```\n")
    # Gelemez ve tercih etmez saati olan, yükü en yüksek öğretmen.
    mus = Counter((m.ogretmen_id, m.durum) for m in girdi.musaitlikler)
    yuk = Counter()
    for a in girdi.atamalar:
        yuk[a.ogretmen_id] += a.haftalik_saat
    adaylar = [oid for oid in ad if mus[(oid, MusaitlikDurumu.GELEMEZ)] and mus[(oid, MusaitlikDurumu.TERCIH_ETMEZ)]]
    secilen = max(adaylar or list(ad), key=lambda oid: yuk[oid])
    og = next(x for x in girdi.ogretmenler if x.id == secilen)
    gun_sayisi = ders_gunleri(girdi, temel_sonuc.yerlesimler).get(og.id, 0)
    yaz(f"### {og.ad} ({og.brans}, {yuk[og.id]} saat, {gun_sayisi} gün)\n\n"
        f"```\n{ogretmen_tablosu(girdi, temel_sonuc, og.id)}\n```\n")

    # --- (3) en az değişiklik ------------------------------------------------------------
    temel = temel_program(girdi.atamalar, temel_sonuc.yerlesimler)
    gunluk = Counter((atama[y.ders_atama_id].ogretmen_id, y.gun) for y in temel_sonuc.yerlesimler)
    (ogretmen, gun), k = gunluk.most_common(1)[0]
    degismis = replace(
        girdi,
        musaitlikler=[m for m in girdi.musaitlikler if not (m.ogretmen_id == ogretmen and m.gun == gun)]
        + [Musaitlik(ogretmen, gun, s, MusaitlikDurumu.GELEMEZ) for s in range(girdi.ayar.gunluk_ders_saati)],
    )
    olcum_girdisi = replace(degismis, temel_yerlesimler=temel)
    yaz(f"## (3) En az değişiklik: {ad[ogretmen]} artık {GUN_ADLARI[gun]} gelemiyor\n")
    yaz(f"Temel programda o gün {k} dersi var (en az {k} ders yer değiştirmek zorunda). "
        f"Toplam {len(temel)} ders saati.\n")
    yaz("| Yöntem | Süre sınırı | Değişen ders saati | İlk çözüm | Durum | Ölçüler |")
    yaz("|---|---|---|---|---|---|")
    for etiket, g, sure in (("Temel programla", olcum_girdisi, 10), ("Temel programla", olcum_girdisi, 60),
                            ("Sıfırdan", degismis, 60)):
        ilk = []
        s = CpSatCozucu(gozlemci=lambda t, _a, _y: ilk.append(t)).coz(g, sure)
        assert s.basarili and dogrula(degismis, s.yerlesimler) == []
        o = olc(olcum_girdisi, s.yerlesimler)
        yaz(f"| {etiket} | {sure} sn | {o.degisen_yerlesim} | {ilk[0]:.1f} sn | {s.durum.value} | {olcu_metni(o)} |")
    yaz()

    # --- (4) çözümsüz örnek ----------------------------------------------------------------
    sinif_saat = Counter()
    for a in girdi.atamalar:
        sinif_saat[a.sinif_id] += a.haftalik_saat
    hedef = next(s for s in girdi.siniflar if sinif_saat[s.id] == girdi.ayar.haftalik_kapasite)
    ogretmenler = sorted({a.ogretmen_id for a in girdi.atamalar if a.sinif_id == hedef.id})
    cozumsuz = replace(
        girdi,
        musaitlikler=[m for m in girdi.musaitlikler if not (m.gun == 0 and m.saat == 0 and m.ogretmen_id in ogretmenler)]
        + [Musaitlik(o, 0, 0, MusaitlikDurumu.GELEMEZ) for o in ogretmenler],
    )
    yaz(f"## (4) Çözümsüz örnek: {hedef.ad} ({sinif_saat[hedef.id]} saat, tam dolu), {len(ogretmenler)} "
        f"öğretmeninin hepsi Pazartesi 1. saatte gelemez\n")
    sorunlar = on_kontrol(cozumsuz)
    yaz(f"Ön kontrol: {'geçti (bu çelişkiyi yakalayamaz)' if not sorunlar else sorunlar[0].mesaj}\n")

    # Çözümsüzlük kanıtı ile çelişki analizini ayrı ölç.
    asil = cpsat.celiskileri_bul
    sureler = {}

    def olculen(*a, **k):
        t = time.perf_counter()
        sonuc = asil(*a, **k)
        sureler["analiz"] = time.perf_counter() - t
        return sonuc

    cpsat.celiskileri_bul = olculen
    try:
        t = time.perf_counter()
        s = CpSatCozucu().coz(cozumsuz, 60)
        toplam = time.perf_counter() - t
    finally:
        cpsat.celiskileri_bul = asil
    analiz = sureler.get("analiz", 0.0)
    yaz(f"Durum: {s.durum.value}. Toplam {toplam:.1f} sn = çözümsüzlük kanıtı {toplam - analiz:.1f} sn + "
        f"çelişki analizi {analiz:.1f} sn (analiz bütçesi {cpsat.CELISKI_ANALIZ_SURESI_SN:g} sn).\n")
    for c in s.celiskiler:
        yaz(f"```\n{c.mesaj}\n```")
        yaz(f"\nMadde sayısı: {c.mesaj.count(chr(10))}")


if __name__ == "__main__":
    main()
