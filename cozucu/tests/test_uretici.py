"""Veri üretici: tekrarlanabilir, çözülebilir ve istenen özelliklerde setler üretir.

Varsayılan çalıştırmada küçük bir ayarla sınanır. Gerçekçi ve büyük setlerin kendisi
`slow` işaretli testlerde, `veri/` altındaki dosyalar üzerinden sınanır.
"""

from collections import defaultdict
from pathlib import Path

import pytest

from cozucu import CozumDurumu, CpSatCozucu, MusaitlikDurumu, dogrula, olc
from cozucu.arayuz import VARSAYILAN_SURE_SINIRI_SN
from cozucu.on_kontrol import on_kontrol
from cozucu.uretici import MUFREDAT, UreticiAyari, uret
from cozucu.veri_io import girdi_oku, girdi_to_dict

VERI = Path(__file__).resolve().parents[2] / "veri"
KUCUK = UreticiAyari(seviye_sube={9: 2, 10: 2}, yuk_araligi=(4, 30), gizli_cozum_suresi_sn=60)


@pytest.fixture(scope="module")
def kucuk():
    return uret(KUCUK, tohum=7)


def test_ayni_tohum_ayni_set(kucuk):
    girdi, gizli = kucuk
    girdi2, gizli2 = uret(KUCUK, tohum=7)
    assert girdi_to_dict(girdi) == girdi_to_dict(girdi2)
    assert gizli == gizli2


def test_gizli_program_seti_cozulebilir_kilar(kucuk):
    girdi, gizli = kucuk
    assert on_kontrol(girdi) == []
    assert dogrula(girdi, gizli) == []


def test_siniflar_mufredat_kadar_dolu(kucuk):
    girdi, _ = kucuk
    saat = defaultdict(int)
    for a in girdi.atamalar:
        saat[a.sinif_id] += a.haftalik_saat
    for s in girdi.siniflar:
        assert saat[s.id] == sum(h for _d, h in MUFREDAT[s.seviye])


def test_gelemez_saatleri_gizli_programla_celismez(kucuk):
    girdi, gizli = kucuk
    atama = {a.id: a for a in girdi.atamalar}
    dolu = {(atama[y.ders_atama_id].ogretmen_id, y.gun, y.saat) for y in gizli}
    gelemez = [m for m in girdi.musaitlikler if m.durum is MusaitlikDurumu.GELEMEZ]
    assert gelemez, "bazı öğretmenlerin gelemez saati olmalı"
    assert all((m.ogretmen_id, m.gun, m.saat) not in dolu for m in gelemez)
    assert any(m.durum is MusaitlikDurumu.TERCIH_ETMEZ for m in girdi.musaitlikler)


def test_bir_sinif_bir_ders_bir_ogretmen(kucuk):
    girdi, _ = kucuk
    ciftler = [(a.sinif_id, a.ders_id) for a in girdi.atamalar]
    assert len(ciftler) == len(set(ciftler))
    assert all(a.ogretmen_id is not None for a in girdi.atamalar)


# --- veri/ altındaki gerçekçi ve büyük setler ------------------------------------------


def _yukler(girdi):
    yuk = defaultdict(int)
    for a in girdi.atamalar:
        yuk[a.ogretmen_id] += a.haftalik_saat
    return yuk


@pytest.mark.slow
@pytest.mark.parametrize("dosya, sube, ogretmen_araligi", [
    ("gercekci.json", 24, (40, 50)),
    ("buyuk.json", 40, (70, 90)),
])
def test_kayitli_set_ozellikleri(dosya, sube, ogretmen_araligi):
    girdi = girdi_oku(VERI / dosya)
    assert len(girdi.siniflar) == sube
    assert ogretmen_araligi[0] <= len(girdi.ogretmenler) <= ogretmen_araligi[1]
    assert all(15 <= y <= 30 for y in _yukler(girdi).values())
    kapasite = girdi.ayar.haftalik_kapasite
    sinif_saat = defaultdict(int)
    for a in girdi.atamalar:
        sinif_saat[a.sinif_id] += a.haftalik_saat
    assert all(saat >= 0.95 * kapasite for saat in sinif_saat.values())
    assert on_kontrol(girdi) == []


@pytest.mark.slow
def test_kabul_gercekci_set_varsayilan_surede_cozulur():
    """Yapım sırası 1'in kabul kriteri: gerçekçi set süre sınırı içinde çözülür.

    Varsayılan süre (120 sn) sınıf boşluğunu sıfırladığı için seçildi; bu da denetlenir.
    """
    girdi = girdi_oku(VERI / "gercekci.json")
    sonuc = CpSatCozucu().coz(girdi)
    assert sonuc.durum in (CozumDurumu.OPTIMAL, CozumDurumu.UYGUN), sonuc.mesajlar
    assert sonuc.sure_sn <= VARSAYILAN_SURE_SINIRI_SN + 5
    assert dogrula(girdi, sonuc.yerlesimler) == []
    assert olc(girdi, sonuc.yerlesimler).sinif_boslugu == 0
