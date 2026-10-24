"""Elle taşıma (7.1): blok bütün taşınır; yalnızca yeni zorunlu ihlal engeller; esnek kötüleşme uyarır."""

import pytest

from cozucu import DersAtama, KisitTanimi, Musaitlik, MusaitlikDurumu, OkulAyari, Ogretmen, Sinif, Ders, Yerlesim
from cozucu.dogrulama import ihlaller
from cozucu.tasima import ENGEL, UYARI, UYGUN, Degerlendirici, TasimaHatasi, blok_hucreleri, tasi
from yardimci import girdi_kur

# 3 gün x 4 saat, öğle arası 2. dersten sonra. 9-A: Matematik 2 saat (blok 2, Ayşe), Fizik 1 (Mehmet).
# 9-B: Kimya 1 (Ayşe). Ayşe salı 4. saat gelemez; Mehmet çarşamba 1. saat tercih etmez.
GIRDI = girdi_kur(
    ayar=OkulAyari(3, 4, ogle_arasi_sonra=2),
    ogretmenler=[Ogretmen("o-ayse", "Ayşe Yılmaz"), Ogretmen("o-mehmet", "Mehmet Kaya")],
    siniflar=[Sinif("9a", "9-A", 9), Sinif("9b", "9-B", 9)],
    dersler=[Ders("mat", "Matematik"), Ders("fiz", "Fizik"), Ders("kim", "Kimya")],
    atamalar=[
        DersAtama("9a-mat", "9a", "mat", "o-ayse", 2),
        DersAtama("9a-fiz", "9a", "fiz", "o-mehmet", 1),
        DersAtama("9b-kim", "9b", "kim", "o-ayse", 1),
    ],
    musaitlikler=[
        Musaitlik("o-ayse", 1, 3, MusaitlikDurumu.GELEMEZ),
        Musaitlik("o-mehmet", 2, 0, MusaitlikDurumu.TERCIH_ETMEZ),
    ],
)
# 9-A: Matematik pazartesi 1-2, Fizik salı 1. 9-B: Kimya pazartesi 3.
PROGRAM = [
    Yerlesim("9a-mat", 0, 0), Yerlesim("9a-mat", 0, 1), Yerlesim("9a-fiz", 1, 0), Yerlesim("9b-kim", 0, 2),
]


def test_baslangic_gecerli():
    assert ihlaller(GIRDI, PROGRAM) == []


def test_blok_butun_tasinir_sekilsiz_ders_tek_saat():
    assert blok_hucreleri(GIRDI, PROGRAM, "9a-mat", 0, 1) == [(0, 0), (0, 1)]
    assert blok_hucreleri(GIRDI, PROGRAM, "9a-fiz", 1, 0) == [(1, 0)]
    with pytest.raises(TasimaHatasi):
        blok_hucreleri(GIRDI, PROGRAM, "9a-fiz", 0, 0)
    yeni = tasi(PROGRAM, "9a-mat", [(0, 0), (0, 1)], 1, 0)
    assert sorted((y.gun, y.saat) for y in yeni if y.ders_atama_id == "9a-mat") == [(1, 0), (1, 1)]


def test_blok_disinda_dagilim_sekli_kapaliysa_tek_saat():
    girdi = girdi_kur(ayar=GIRDI.ayar, atamalar=GIRDI.atamalar, kisitlar=[KisitTanimi("blok_deseni", {"otomatik": False})])
    assert blok_hucreleri(girdi, PROGRAM, "9a-mat", 0, 1) == [(0, 1)]


def test_uygun_tasima():
    d = Degerlendirici(GIRDI, PROGRAM).degerlendir("9a-mat", 0, 0, 2, 0)
    assert (d.durum, d.nedenler, d.hucreler) == (UYGUN, (), ((2, 0), (2, 1)))


@pytest.mark.parametrize("kaynak, hedef, beklenen", [
    (("9a-fiz", 1, 0), (0, 0), "9-A Pazartesi 1. saat iki derste olur (Fizik, Matematik)"),
    (("9b-kim", 0, 2), (0, 1), "Ayşe Yılmaz Pazartesi 2. saat iki şubede olur (9-A, 9-B)"),
    (("9b-kim", 0, 2), (1, 3), "Ayşe Yılmaz Salı 4. saat gelemez"),
    (("9a-mat", 0, 0), (1, 1), "9-A Matematik Salı günü öğle arasını keser (blok bütün kalmalı)"),
])
def test_zorunlu_ihlal_engeller_nedeni_kullanici_dilinde(kaynak, hedef, beklenen):
    d = Degerlendirici(GIRDI, PROGRAM).degerlendir(*kaynak, *hedef)
    assert d.durum == ENGEL
    assert beklenen in d.nedenler


def test_gunluk_sinir_ve_ogretmen_gunluk_siniri_engeller():
    girdi = girdi_kur(
        ayar=GIRDI.ayar, ogretmenler=GIRDI.ogretmenler, siniflar=GIRDI.siniflar, dersler=GIRDI.dersler,
        atamalar=[DersAtama("9a-fiz", "9a", "fiz", "o-mehmet", 3), DersAtama("9b-kim", "9b", "kim", "o-mehmet", 1)],
        kisitlar=[KisitTanimi("blok_deseni", {"otomatik": False}), KisitTanimi("ogretmen_gunluk_siniri", {"m": 3})],
    )
    program = [Yerlesim("9a-fiz", 0, 0), Yerlesim("9a-fiz", 0, 1), Yerlesim("9a-fiz", 1, 0), Yerlesim("9b-kim", 0, 2)]
    d = Degerlendirici(girdi, program).degerlendir("9a-fiz", 1, 0, 0, 3)
    assert "9-A Fizik Pazartesi günü 3 saat olur; günde en fazla 2 saat" in d.nedenler
    assert "Mehmet Kaya Pazartesi günü 4 saat derse girer; günde en fazla 3 saat" in d.nedenler


def test_haftanin_disina_tasinmaz():
    girdi = girdi_kur(ayar=OkulAyari(3, 4, gun_saatleri=(4, 4, 2)), atamalar=GIRDI.atamalar,
                      kisitlar=[KisitTanimi("blok_deseni", {"otomatik": False})])
    d = Degerlendirici(girdi, PROGRAM).degerlendir("9a-fiz", 1, 0, 2, 3)
    assert d.durum == ENGEL and any("okulun haftasında yok" in n for n in d.nedenler)


def test_kilitli_ders_tasinmaz():
    program = [Yerlesim("9a-mat", 0, 0, kilitli=True), *PROGRAM[1:]]
    d = Degerlendirici(GIRDI, program).degerlendir("9a-mat", 0, 1, 2, 2)
    assert d.durum == ENGEL and d.nedenler == ("9-A Matematik kilitli; taşımak için önce kilidi açın",)


def test_onceden_var_olan_ihlal_engellemez_yalnizca_yenisi():
    # Veri sonradan değişti: Mehmet artık salı 1. saat gelemez (programda zaten ihlal).
    girdi = girdi_kur(ayar=GIRDI.ayar, ogretmenler=GIRDI.ogretmenler, siniflar=GIRDI.siniflar, dersler=GIRDI.dersler,
                      atamalar=GIRDI.atamalar, musaitlikler=[*GIRDI.musaitlikler, Musaitlik("o-mehmet", 1, 0, MusaitlikDurumu.GELEMEZ)])
    assert ihlaller(girdi, PROGRAM)
    d = Degerlendirici(girdi, PROGRAM).degerlendir("9b-kim", 0, 2, 2, 0)
    assert d.durum != ENGEL


def test_esnek_olcu_kotulesirse_uyari():
    # Fizik'i çarşamba 1. saate: Mehmet'in tercih etmediği saat.
    d = Degerlendirici(GIRDI, PROGRAM).degerlendir("9a-fiz", 1, 0, 2, 0)
    assert d.durum == UYARI
    assert "Tercih edilmeyen saate konan ders 0 → 1" in d.nedenler
    # Sınıfı gün ortasında boş bırakan taşıma da uyarır (salı 4. saat: önünde üç boş saat; 9-B pazartesi zaten 2).
    d = Degerlendirici(GIRDI, PROGRAM).degerlendir("9a-fiz", 1, 0, 1, 3)
    assert d.durum == UYARI and "Sınıfların boş saati 2 → 5" in d.nedenler


def test_harita_her_baslangici_degerlendirir_kendi_yerini_atlar():
    harita = {(d.gun, d.saat): d for d in Degerlendirici(GIRDI, PROGRAM).harita("9a-mat", 0, 1)}
    assert (0, 0) not in harita  # kendi yeri
    assert (0, 3) not in harita  # 2 saatlik blok 4. saatten başlayamaz (gün biter)
    assert harita[(2, 0)].durum == UYGUN
    assert harita[(1, 0)].durum == ENGEL  # 9-A'nın salı 1. saatte Fizik'i var
    assert harita[(1, 1)].durum == ENGEL  # öğle arası
    assert len(harita) == 3 * 3 - 1
