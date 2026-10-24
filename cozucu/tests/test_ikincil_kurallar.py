"""İkincil esnek kurallar (K6; docs/kisisellestirme-plani.md 4, f-h).

Her senaryoda yalnızca sınanan kural açıktır. Hem kaçınılabilen ihlalden kaçınıldığı hem de
kaçınılamayan ihlalin cezası denetlenir; modelin cezası bağımsız `kalite.olc` ile karşılaştırılır.
"""

import pytest

from cozucu import CozumDurumu, CpSatCozucu, DersAtama, Kapsam, KisitTanimi, OkulAyari, dogrula, olc
from cozucu.kalite import agirlikli_ceza
from cozucu.kisitlar import KAYIT_DEFTERI, GirdiHatasi, etkin_agirliklar, kural_olustur
from cozucu.tercihler import cezali_saatler, gunluk_en_az_ders
from yardimci import girdi_kur

from test_esnek_kisitlar import BLOKSUZ, atama, gelemez, kilit, yalniz

SAAT = "ders_saat_tercihi"
EN_AZ = "gunluk_en_az_ders"
YAYILIM = "ders_yayilimi"


def coz(girdi):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=10)
    assert sonuc.durum is CozumDurumu.OPTIMAL, sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    assert agirlikli_ceza(olc(girdi, sonuc.yerlesimler), etkin_agirliklar(girdi)) == sonuc.toplam_ceza
    return sonuc


def ozel(tur, parametreler, **kapsam):
    return KisitTanimi(tur, parametreler, zorunlu=False, kapsam=Kapsam(**kapsam))


def saatler(sonuc, atama_id):
    return sorted((y.gun, y.saat) for y in sonuc.yerlesimler if y.ders_atama_id == atama_id)


# --- kapsamlar ------------------------------------------------------------------------------

def test_kapsamlar():
    assert KAYIT_DEFTERI[SAAT].kapsamlar == {"ders", "sube", "sube_grubu"}
    assert KAYIT_DEFTERI[SAAT].zorunlu_eksenler == {"ders"}
    assert KAYIT_DEFTERI[EN_AZ].kapsamlar == {"ogretmen"}
    assert KAYIT_DEFTERI[YAYILIM].kapsamlar == {"ders", "sube", "sube_grubu"}


def test_saat_tercihi_dersiz_ozel_ayar_reddedilir():
    with pytest.raises(GirdiHatasi, match="ders belirtilmeli"):
        kural_olustur(KisitTanimi(SAAT, zorunlu=False, agirlik=3), [ozel(SAAT, {"saatler": [0]}, sinif_id="s1")])


def test_saat_tercihi_gecersiz_saat_reddedilir():
    with pytest.raises(GirdiHatasi):
        kural_olustur(KisitTanimi(SAAT, zorunlu=False, agirlik=3), [ozel(SAAT, {"kacin": [-1]}, ders_id="d")])


# --- dersin saat tercihi (f) ----------------------------------------------------------------

def test_okul_genelinde_saat_tercihi_yok():
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[atama("mat", saat=1)], kisitlar=yalniz(SAAT) + [BLOKSUZ])
    assert cezali_saatler(girdi, "s1", "mat") == frozenset()
    assert coz(girdi).toplam_ceza == 0


def test_matematik_sabah():
    # Matematik ilk iki saatte olsun; Fizik 2. saate kilitli: Matematik 1. saate konur.
    atamalar = [atama("mat", saat=1), atama("fiz", ogretmen="o2", saat=1)]
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=atamalar, kilitli_yerlesimler=[kilit("fiz", 0, 1)],
                      kisitlar=yalniz(SAAT) + [BLOKSUZ, ozel(SAAT, {"saatler": [0, 1]}, ders_id="mat")])
    sonuc = coz(girdi)
    assert saatler(sonuc, "mat") == [(0, 0)]
    assert sonuc.toplam_ceza == 0


def test_kacinilan_saat_kilitliyse_ceza():
    # Beden Eğitimi 3. saatten kaçınsın; kilit onu tam oraya koyuyor: 1 ders saati × ağırlık 3.
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[atama("bed", saat=1)], kilitli_yerlesimler=[kilit("bed", 0, 2)],
                      kisitlar=yalniz(SAAT) + [BLOKSUZ, ozel(SAAT, {"kacin": [2]}, ders_id="bed")])
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).saat_tercihi == 1
    assert sonuc.toplam_ceza == 3


def test_ders_sube_ayari_dersin_ayarini_ezer():
    # Matematik okulda sabah; 9-B'de öğleden sonra (ders + şube daha özel).
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[atama("a", sinif="9A", ders="mat"), atama("b", sinif="9B", ders="mat", ogretmen="o2")],
                      kisitlar=yalniz(SAAT) + [BLOKSUZ, ozel(SAAT, {"saatler": [0, 1]}, ders_id="mat"),
                                               ozel(SAAT, {"saatler": [2, 3]}, ders_id="mat", sinif_id="9B")])
    assert cezali_saatler(girdi, "9A", "mat") == {2, 3}
    assert cezali_saatler(girdi, "9B", "mat") == {0, 1}
    sonuc = coz(girdi)
    assert saatler(sonuc, "a")[0][1] in (0, 1)
    assert saatler(sonuc, "b")[0][1] in (2, 3)
    assert sonuc.toplam_ceza == 0


# --- öğretmenin geldiği günde en az ders (g) --------------------------------------------------

def tek_saatlik_dersler(adet, ogretmen="o1"):
    return [DersAtama(f"t{i}", f"s{i}", f"d{i}", ogretmen, 1) for i in range(adet)]


def test_bir_saat_icin_gelmez():
    # 4 tek saatlik ders, 5 gün: kural kapalıyken her güne dağılabilirdi; açıkken her gün en az 2.
    girdi = girdi_kur(ayar=OkulAyari(5, 4), atamalar=tek_saatlik_dersler(4), kisitlar=yalniz(EN_AZ) + [BLOKSUZ])
    sonuc = coz(girdi)
    gunler = [y.gun for y in sonuc.yerlesimler]
    assert all(gunler.count(g) >= 2 for g in set(gunler))
    assert sonuc.toplam_ceza == 0


def test_kilitler_tek_saatlik_gun_birakirsa_ceza():
    kilitler = [kilit("t0", 0, 0), kilit("t1", 1, 0), kilit("t2", 1, 1)]
    girdi = girdi_kur(ayar=OkulAyari(2, 4), atamalar=tek_saatlik_dersler(3), kilitli_yerlesimler=kilitler,
                      kisitlar=yalniz(EN_AZ) + [BLOKSUZ])
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).az_dersli_gun == 1
    assert sonuc.toplam_ceza == 3


def test_ders_saati_yetmeyene_ceza_yok():
    # 1 saatlik öğretmen: k etkin 1, kural yok. Günde 1 saat müsait öğretmen: en iyi gün 1.
    girdi = girdi_kur(ayar=OkulAyari(5, 4), atamalar=tek_saatlik_dersler(1), kisitlar=yalniz(EN_AZ) + [BLOKSUZ])
    assert gunluk_en_az_ders(girdi, "o1", 1) == 1
    assert coz(girdi).toplam_ceza == 0
    musait = [gelemez("o1", g, s) for g in range(2) for s in range(1, 4)]
    girdi = girdi_kur(ayar=OkulAyari(2, 4), atamalar=tek_saatlik_dersler(2), musaitlikler=musait,
                      kisitlar=yalniz(EN_AZ) + [BLOKSUZ])
    assert gunluk_en_az_ders(girdi, "o1", 2) == 1
    assert coz(girdi).toplam_ceza == 0


def test_ogretmene_ozel_en_az_ders():
    # Okulda 2, bu öğretmene 3: 6 tek saatlik ders 3 + 3 dağılır (2 + 2 + 2 değil).
    girdi = girdi_kur(ayar=OkulAyari(5, 4), atamalar=tek_saatlik_dersler(6),
                      kisitlar=yalniz(EN_AZ) + [BLOKSUZ, ozel(EN_AZ, {"k": 3}, ogretmen_id="o1")])
    assert gunluk_en_az_ders(girdi, "o1", 6) == 3
    sonuc = coz(girdi)
    gunler = [y.gun for y in sonuc.yerlesimler]
    assert all(gunler.count(g) >= 3 for g in set(gunler))


# --- aynı dersin günlere yayılması (h) --------------------------------------------------------

def test_ayni_ders_art_arda_gunlere_yigilmaz():
    # 2 saat, günde en fazla 1 (N=1), 5 gün: art arda olmayan iki gün seçilir.
    n1 = KisitTanimi("gunluk_ders_siniri", {"n": 1})
    girdi = girdi_kur(ayar=OkulAyari(5, 2), atamalar=[atama("mat", saat=2)], kisitlar=yalniz(YAYILIM) + [BLOKSUZ, n1])
    sonuc = coz(girdi)
    g1, g2 = sorted(g for g, _s in saatler(sonuc, "mat"))
    assert g2 - g1 >= 2
    assert sonuc.toplam_ceza == 0


def test_kacinilamayan_yigilma_cezasi():
    # 3 gün, 3 saat, günde 1: üç gün de dolu, iki art arda çift × ağırlık 2.
    n1 = KisitTanimi("gunluk_ders_siniri", {"n": 1})
    girdi = girdi_kur(ayar=OkulAyari(3, 2), atamalar=[atama("mat", saat=3)], kisitlar=yalniz(YAYILIM) + [BLOKSUZ, n1])
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).art_arda_gun == 2
    assert sonuc.toplam_ceza == 4


def test_derse_ozel_kapatilabilir():
    n1 = KisitTanimi("gunluk_ders_siniri", {"n": 1})
    kilitler = [kilit("mat", 0, 0), kilit("mat", 1, 0)]
    girdi = girdi_kur(ayar=OkulAyari(5, 2), atamalar=[atama("mat", saat=2)], kilitli_yerlesimler=kilitler,
                      kisitlar=yalniz(YAYILIM) + [BLOKSUZ, n1, ozel(YAYILIM, {"yayilsin": False}, ders_id="mat")])
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).art_arda_gun == 0
    assert sonuc.toplam_ceza == 0
