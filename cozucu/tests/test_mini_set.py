"""Uçtan uca: mini veri seti çözülür ve bağımsız doğrulayıcıdan geçer."""

from pathlib import Path

import pytest

from cozucu import CozumDurumu, CpSatCozucu, dogrula, olc
from cozucu.veri_io import girdi_oku

MINI = Path(__file__).resolve().parents[2] / "veri" / "mini.json"


@pytest.fixture(scope="module")
def girdi():
    return girdi_oku(MINI)


@pytest.fixture(scope="module")
def sonuc(girdi):
    return CpSatCozucu().coz(girdi, sure_siniri_sn=30)


def test_mini_set_cozulur_ve_dogrulanir(girdi, sonuc):
    assert len(girdi.siniflar) == 3 and len(girdi.ogretmenler) == 5
    assert sonuc.durum in (CozumDurumu.OPTIMAL, CozumDurumu.UYGUN), sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    assert len(sonuc.yerlesimler) == sum(a.haftalik_saat for a in girdi.atamalar)
    assert [(y.ders_atama_id, y.gun, y.saat) for y in sonuc.yerlesimler if y.kilitli] == [
        ("a-9a-mat", 1, 0)
    ]


def test_mini_set_en_iyi_cozum_ve_ceza_bagimsiz_olcumle_tutarli(girdi, sonuc):
    # En iyi çözümde modelin cezası, bağımsız ölçümlerin ağırlıklı toplamına eşit olmalı.
    assert sonuc.durum is CozumDurumu.OPTIMAL
    o = olc(girdi, sonuc.yerlesimler)
    beklenen = (
        5 * o.tercih_etmez + 3 * o.ogretmen_penceresi + 10 * o.sinif_boslugu + 2 * o.bolunmus_ders
        + 4 * o.eksik_bos_gun + 20 * o.degisen_yerlesim
    )
    assert sonuc.toplam_ceza == beklenen


def test_mini_set_siniflarda_ara_bosluk_yok(girdi, sonuc):
    assert olc(girdi, sonuc.yerlesimler).sinif_boslugu == 0


def test_mini_set_en_az_degisiklikle_guncelleme(girdi, sonuc):
    # Mehmet temel programda en çok ders verdiği gün artık gelemiyor. O günkü k dersi kaymak
    # zorunda (alt sınır k). Temel programla yapılan güncelleme alt sınıra yakın kalmalı.
    from collections import Counter
    from dataclasses import replace

    from cozucu import Musaitlik, MusaitlikDurumu, temel_program

    temel = temel_program(girdi.atamalar, sonuc.yerlesimler)
    mehmet = {(a.sinif_id, a.ders_id) for a in girdi.atamalar if a.ogretmen_id == "o-mehmet"}
    gunler = Counter(t.gun for t in temel if (t.sinif_id, t.ders_id) in mehmet)
    gun, k = gunler.most_common(1)[0]
    yeni_girdi = replace(
        girdi,
        musaitlikler=girdi.musaitlikler + [Musaitlik("o-mehmet", gun, s, MusaitlikDurumu.GELEMEZ) for s in range(6)],
        temel_yerlesimler=temel,
    )
    yeni = CpSatCozucu().coz(yeni_girdi, sure_siniri_sn=30)
    assert yeni.basarili and dogrula(yeni_girdi, yeni.yerlesimler) == []
    degisen = olc(yeni_girdi, yeni.yerlesimler).degisen_yerlesim
    assert k <= degisen <= k + 4, (k, degisen)
