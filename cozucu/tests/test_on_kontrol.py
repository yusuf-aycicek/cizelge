"""Ön kontroller: her hata türü yakalanır, mesajlar adlarla yazılır, hepsi birlikte raporlanır."""

from dataclasses import replace

import pytest

from cozucu import (
    CozumGirdisi,
    Ders,
    DersAtama,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Ogretmen,
    Sinif,
    Yerlesim,
)
from cozucu.anlatim import iyelik
from cozucu.on_kontrol import on_kontrol


def temel(**degisiklik) -> CozumGirdisi:
    """5 gün x 6 saat; 9-A: Matematik (Ayşe, 6 saat) + Fizik (Zeynep, 3 saat). Sorunsuz."""
    girdi = CozumGirdisi(
        ayar=OkulAyari(5, 6),
        ogretmenler=[Ogretmen("o-ayse", "Ayşe Yılmaz"), Ogretmen("o-zeynep", "Zeynep Demir")],
        siniflar=[Sinif("s-9a", "9-A", 9)],
        dersler=[Ders("d-mat", "Matematik"), Ders("d-fiz", "Fizik")],
        atamalar=[
            DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 6),
            DersAtama("a-fiz", "s-9a", "d-fiz", "o-zeynep", 3),
        ],
    )
    return replace(girdi, **degisiklik)


def gelemez_gunler(ogretmen, gunler, saatler=range(6)):
    return [Musaitlik(ogretmen, g, s, MusaitlikDurumu.GELEMEZ) for g in gunler for s in saatler]


def tek(girdi):
    sorunlar = on_kontrol(girdi)
    assert len(sorunlar) == 1, sorunlar
    return sorunlar[0]


def test_sorunsuz_girdi():
    assert on_kontrol(temel()) == []


# --- tutarlılık ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "degisiklik, parca",
    [
        ({"atamalar": [DersAtama("a", "yok", "d-mat", "o-ayse", 1)]}, "tanımlı olmayan bir sınıfa"),
        ({"atamalar": [DersAtama("a", "s-9a", "yok", "o-ayse", 1)]}, "tanımlı olmayan bir derse"),
        ({"atamalar": [DersAtama("a", "s-9a", "d-mat", "yok", 1)]}, "tanımlı olmayan bir öğretmene"),
        ({"siniflar": [Sinif("s-9a", "9-A", 9), Sinif("s-9a", "9-B", 9)]}, "Aynı kimlikle 2 sınıf"),
        ({"musaitlikler": [Musaitlik("yok", 0, 0, MusaitlikDurumu.GELEMEZ)]}, "tanımlı olmayan bir öğretmen"),
        ({"musaitlikler": [Musaitlik("o-ayse", 5, 0, MusaitlikDurumu.GELEMEZ)]}, "aralığı dışında"),
        ({"kilitli_yerlesimler": [Yerlesim("yok", 0, 0)]}, "tanımlı olmayan bir atamaya"),
        ({"kilitli_yerlesimler": [Yerlesim("a-mat", 0, 6)]}, "aralığı dışında"),
        ({"kisitlar": [KisitTanimi("uydurma")]}, "Bilinmeyen kısıt türü"),
        ({"kisitlar": [KisitTanimi("ogretmen_gunluk_siniri", {"m": 0})]}, "geçersiz parametre"),
        ({"kisitlar": [KisitTanimi("ogretmen_gunluk_siniri", zorunlu=False)]}, "yalnızca zorunlu"),
    ],
)
def test_tutarsiz_veri(degisiklik, parca):
    sorun = tek(temel(**degisiklik))
    assert parca in sorun.mesaj


def test_tutarsiz_veri_varsa_kapasite_kontrolleri_yapilmaz():
    # Sınıf kapasitesi de aşılıyor ama önce veri düzeltilmeli: yalnızca tutarlılık hatası döner.
    girdi = temel(atamalar=[DersAtama("a", "s-9a", "d-mat", "yok", 40)])
    assert [s.tur for s in on_kontrol(girdi)] == ["tutarsiz_veri"]


# --- kapasite ------------------------------------------------------------------------


def test_ogretmen_secilmemis():
    girdi = temel(atamalar=[DersAtama("a-mat", "s-9a", "d-mat", None, 6)])
    sorun = tek(girdi)
    assert sorun.tur == "ogretmen_secilmemis"
    assert sorun.mesaj == "9-A Matematik dersine öğretmen seçilmemiş."
    assert sorun.ilgili == ("a-mat", "s-9a")


def test_sinif_kapasitesi():
    girdi = temel(atamalar=[
        DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 20),
        DersAtama("a-fiz", "s-9a", "d-fiz", "o-zeynep", 12),
    ], kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 6})])
    sorun = tek(girdi)
    assert sorun.tur == "sinif_kapasitesi"
    assert sorun.mesaj == "9-A sınıfının haftada 32 saat dersi var, haftalık kapasite 30 saat (5 gün × 6 saat)."


def test_ogretmen_kapasitesi_musait_saat():
    # Ayşe yalnızca pazartesi ve salı müsait (12 saat), ama 3 sınıfa 6'şar saat (18) dersi var.
    girdi = temel(
        siniflar=[Sinif("s-9a", "9-A", 9), Sinif("s-9b", "9-B", 9), Sinif("s-9c", "9-C", 9)],
        atamalar=[DersAtama(f"a-{s}", f"s-{s}", "d-mat", "o-ayse", 6) for s in ("9a", "9b", "9c")],
        musaitlikler=gelemez_gunler("o-ayse", [2, 3, 4]),
        kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 3})],
    )
    sorun = tek(girdi)
    assert sorun.tur == "ogretmen_kapasitesi"
    assert sorun.mesaj == "Ayşe Yılmaz'ın 18 saat dersi var, müsait olduğu 12 saat var."
    assert sorun.ilgili[0] == "o-ayse"


def test_ogretmen_kapasitesi_gunluk_sinir_ile():
    girdi = temel(
        atamalar=[DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 6)],
        musaitlikler=gelemez_gunler("o-ayse", [1, 2, 3, 4]),
        kisitlar=[
            KisitTanimi("ogretmen_gunluk_siniri", {"m": 4}),
            KisitTanimi("gunluk_ders_siniri", {"n": 6}),
        ],
    )
    # Tek gün müsait olduğu için ders gün kapasitesi de aşılıyor; ikisi de raporlanır.
    sorunlar = {s.tur: s for s in on_kontrol(girdi)}
    assert set(sorunlar) == {"ogretmen_kapasitesi", "ders_gun_kapasitesi"}
    assert sorunlar["ogretmen_kapasitesi"].mesaj == (
        "Ayşe Yılmaz'ın 6 saat dersi var. Müsait olduğu 6 saatin, günde en fazla 4 saat derse "
        "girebildiği için yalnızca 4 saati kullanılabilir."
    )


def test_ders_gun_kapasitesi_ogretmen_musait_gunleri():
    # Matematik 6 saat, günde en fazla 2 saat; Ayşe yalnızca 2 gün müsait -> en fazla 4 saat.
    girdi = temel(musaitlikler=gelemez_gunler("o-ayse", [0, 1, 2]))
    sorun = tek(girdi)
    assert sorun.tur == "ders_gun_kapasitesi"
    assert sorun.mesaj == (
        "9-A Matematik haftada 6 saat, ama bir ders bir sınıfa günde en fazla 2 saat konabildiği ve "
        "Ayşe Yılmaz yalnızca 2 gün müsait olduğu için en fazla 4 saat yerleşebilir."
    )


def test_ders_gun_kapasitesi_esnek_sinirda_denetlenmez():
    girdi = temel(
        musaitlikler=gelemez_gunler("o-ayse", [0, 1, 2]),
        kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 2}, zorunlu=False, agirlik=1)],
    )
    assert on_kontrol(girdi) == []


# --- kilitler ------------------------------------------------------------------------


def test_kilit_gelemez_saatte():
    girdi = temel(
        musaitlikler=[Musaitlik("o-ayse", 1, 0, MusaitlikDurumu.GELEMEZ)],
        kilitli_yerlesimler=[Yerlesim("a-mat", 1, 0, kilitli=True)],
    )
    sorun = tek(girdi)
    assert sorun.mesaj == "9-A Matematik Salı 1. saatte kilitli, ama Ayşe Yılmaz o saatte gelemez."


def test_ayni_sinif_ayni_saate_iki_kilit():
    girdi = temel(kilitli_yerlesimler=[Yerlesim("a-mat", 0, 0), Yerlesim("a-fiz", 0, 0)])
    sorun = tek(girdi)
    assert sorun.mesaj == "9-A sınıfında Pazartesi 1. saate birden fazla ders kilitli: Fizik, Matematik."


def test_ayni_ogretmen_ayni_saatte_iki_sinifa_kilitli():
    girdi = temel(
        siniflar=[Sinif("s-9a", "9-A", 9), Sinif("s-9b", "9-B", 9)],
        atamalar=[DersAtama("a-9a", "s-9a", "d-mat", "o-ayse", 2), DersAtama("a-9b", "s-9b", "d-mat", "o-ayse", 2)],
        kilitli_yerlesimler=[Yerlesim("a-9a", 0, 0), Yerlesim("a-9b", 0, 0)],
    )
    sorun = tek(girdi)
    assert "Ayşe Yılmaz Pazartesi 1. saatte birden fazla sınıfa kilitli" in sorun.mesaj


def test_kilit_sayisi_haftalik_saati_asar():
    girdi = temel(kilitli_yerlesimler=[Yerlesim("a-fiz", g, 0) for g in range(4)])
    assert "4 kilitli hücre var, ama dersin haftada 3 saati var" in tek(girdi).mesaj


def test_bir_gune_gunluk_siniri_asan_kilit():
    girdi = temel(kilitli_yerlesimler=[Yerlesim("a-mat", 2, s) for s in range(3)])
    assert tek(girdi).mesaj == (
        "9-A Matematik Çarşamba gününe 3 saat kilitli, ama bir ders bir sınıfa günde en fazla 2 saat konabilir."
    )


def test_birden_fazla_sorun_birlikte_raporlanir():
    girdi = temel(
        atamalar=[DersAtama("a-mat", "s-9a", "d-mat", None, 6), DersAtama("a-fiz", "s-9a", "d-fiz", "o-zeynep", 3)],
        musaitlikler=gelemez_gunler("o-zeynep", [0, 1, 2, 3]),
        kilitli_yerlesimler=[Yerlesim("a-fiz", 4, s) for s in range(3)],
    )
    assert {s.tur for s in on_kontrol(girdi)} == {"ogretmen_secilmemis", "ders_gun_kapasitesi", "kilit_celiskisi"}


# --- dil -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ad, beklenen",
    [
        ("Ayşe Yılmaz", "Ayşe Yılmaz'ın"),
        ("Mehmet Kaya", "Mehmet Kaya'nın"),
        ("Ali Çelik", "Ali Çelik'in"),
        ("Zeynep Demir", "Zeynep Demir'in"),
        ("Fatma Şahin", "Fatma Şahin'in"),
        ("Oğuz Konuk", "Oğuz Konuk'un"),
        ("Gül Öztürk", "Gül Öztürk'ün"),
        ("Ece Tekdemir", "Ece Tekdemir'in"),
        ("Hülya Su", "Hülya Su'nun"),
        ("AYŞE İNCİ", "AYŞE İNCİ'nin"),
    ],
)
def test_iyelik_eki(ad, beklenen):
    assert iyelik(ad) == beklenen
