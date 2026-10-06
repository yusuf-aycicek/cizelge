"""Doğrulayıcı, bilerek bozulmuş programları yakalamalı; geçerli programa ses çıkarmamalı."""

import pytest

from cozucu import (
    CozumGirdisi,
    DersAtama,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Yerlesim,
    dogrula,
)

# 2 gün x 3 saat. s1: mat (o1, 3 saat) + ing (o2, 1 saat). s2: mat (o1, 2 saat).
GIRDI = CozumGirdisi(
    ayar=OkulAyari(2, 3),
    atamalar=[
        DersAtama("s1-mat", "s1", "mat", "o1", 3),
        DersAtama("s1-ing", "s1", "ing", "o2", 1),
        DersAtama("s2-mat", "s2", "mat", "o1", 2),
    ],
    musaitlikler=[Musaitlik("o2", 1, 2, MusaitlikDurumu.GELEMEZ)],
    kilitli_yerlesimler=[Yerlesim("s1-ing", 0, 2, kilitli=True)],
)

# Elle kurulmuş geçerli program:
#        gün 0              gün 1
# saat0  s1-mat             s1-mat
# saat1  s1-mat             s2-mat
# saat2  s1-ing, s2-mat     (boş)
GECERLI = [
    Yerlesim("s1-mat", 0, 0),
    Yerlesim("s1-mat", 0, 1),
    Yerlesim("s1-mat", 1, 0),
    Yerlesim("s1-ing", 0, 2, kilitli=True),
    Yerlesim("s2-mat", 0, 2),
    Yerlesim("s2-mat", 1, 1),
]


def degistir(eski, yeni):
    return [yeni if y == eski else y for y in GECERLI]


def test_gecerli_program_hatasiz():
    assert dogrula(GIRDI, GECERLI) == []


@pytest.mark.parametrize(
    "program, beklenen",
    [
        (GECERLI[1:], "3 saat olmalı, 2 saat"),
        (GECERLI + [Yerlesim("s1-mat", 1, 2)], "3 saat olmalı, 4 saat"),
        (GECERLI + [Yerlesim("s1-mat", 0, 0)], "aynı hücreye 2 kez"),
        (degistir(Yerlesim("s1-mat", 1, 0), Yerlesim("s1-mat", 0, 2)), "Sınıf çakışması"),
        (degistir(Yerlesim("s2-mat", 1, 1), Yerlesim("s2-mat", 0, 0)), "Öğretmen çakışması"),
        (
            degistir(Yerlesim("s1-ing", 0, 2, kilitli=True), Yerlesim("s1-ing", 1, 2)),
            "Gelemez ihlali",
        ),
        (
            degistir(Yerlesim("s1-ing", 0, 2, kilitli=True), Yerlesim("s1-ing", 1, 1)),
            "Kilitli hücre yerinde değil",
        ),
        (GECERLI + [Yerlesim("yok", 0, 0)], "Bilinmeyen atama"),
        (degistir(Yerlesim("s2-mat", 1, 1), Yerlesim("s2-mat", 1, 3)), "aralık dışında"),
    ],
)
def test_bozuk_program_yakalanir(program, beklenen):
    hatalar = dogrula(GIRDI, program)
    assert any(beklenen in h for h in hatalar), hatalar


def test_gunluk_sinir_asimi_yakalanir():
    # s1-mat'ın üç saati de gün 0'a: varsayılan n=2 aşılır (s1-ing gün 1'e kaydırılır, kilit yok).
    girdi = CozumGirdisi(ayar=GIRDI.ayar, atamalar=GIRDI.atamalar)
    program = [
        Yerlesim("s1-mat", 0, 0),
        Yerlesim("s1-mat", 0, 1),
        Yerlesim("s1-mat", 0, 2),
        Yerlesim("s1-ing", 1, 0),
        Yerlesim("s2-mat", 1, 1),
        Yerlesim("s2-mat", 1, 2),
    ]
    assert any("Günlük sınır aşıldı" in h for h in dogrula(girdi, program))

    uc = [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 3})]
    assert dogrula(CozumGirdisi(ayar=girdi.ayar, atamalar=girdi.atamalar, kisitlar=uc), program) == []
