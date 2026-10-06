"""Esnek kurallar: cezanın beklenen yönde çalıştığını gösteren küçük senaryolar.

Her senaryoda yalnızca sınanan kural açıktır (diğer esnek kuralların ağırlığı 0). Hem
"kaçınılabilen ihlalden kaçınılır" hem de "kaçınılamayan ihlalin cezası tam beklenen değer"
denetlenir. Ayrıca modeldeki ceza, bağımsız `kalite.olc` ölçümüyle karşılaştırılır.
"""

import pytest

from cozucu import (
    CozumDurumu,
    CpSatCozucu,
    DersAtama,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Yerlesim,
    dogrula,
    olc,
)
from yardimci import girdi_kur

from cozucu.kisitlar import VARSAYILAN_KISITLAR

ESNEK_TURLER = [t.tur for t in VARSAYILAN_KISITLAR if not t.zorunlu]


def yalniz(tur, agirlik=None):
    """`tur` dışındaki esnek kuralları kapatan kisit listesi."""
    tanimlar = []
    for t in VARSAYILAN_KISITLAR:
        if t.zorunlu:
            continue
        a = (agirlik if agirlik is not None else t.agirlik) if t.tur == tur else 0
        tanimlar.append(KisitTanimi(t.tur, zorunlu=False, agirlik=a))
    return tanimlar


def atama(id, sinif="s1", ders=None, ogretmen="o1", saat=1):
    return DersAtama(id=id, sinif_id=sinif, ders_id=ders or id, ogretmen_id=ogretmen, haftalik_saat=saat)


def gelemez(ogretmen, gun, saat):
    return Musaitlik(ogretmen, gun, saat, MusaitlikDurumu.GELEMEZ)


def kilit(atama_id, gun, saat):
    return Yerlesim(atama_id, gun, saat, kilitli=True)


def coz(girdi):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=10)
    assert sonuc.durum is CozumDurumu.OPTIMAL, sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    return sonuc


def saatler(sonuc, atama_id):
    return sorted(y.saat for y in sonuc.yerlesimler if y.ders_atama_id == atama_id)


# --- tercih etmez ---------------------------------------------------------------------


def test_tercih_etmez_saatinden_kacinilir():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 2),
        atamalar=[atama("a")],
        musaitlikler=[Musaitlik("o1", 0, 0, MusaitlikDurumu.TERCIH_ETMEZ)],
        kisitlar=yalniz("tercih_etmez"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "a") == [1] and sonuc.toplam_ceza == 0


def test_tercih_etmez_kacinilamazsa_agirlik_kadar_ceza():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 1),
        atamalar=[atama("a")],
        musaitlikler=[Musaitlik("o1", 0, 0, MusaitlikDurumu.TERCIH_ETMEZ)],
        kisitlar=yalniz("tercih_etmez", agirlik=7),
    )
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 7
    assert olc(girdi, sonuc.yerlesimler).tercih_etmez == 1


# --- öğretmen penceresi -------------------------------------------------------------


def test_ogretmen_penceresi_kapanir():
    # o1'in 9-A dersi 1. saatte kilitli; 9-B dersi bitişik saate (2. saat) gelmeli.
    girdi = girdi_kur(
        ayar=OkulAyari(1, 5),
        atamalar=[atama("a", sinif="s1"), atama("b", sinif="s2")],
        kilitli_yerlesimler=[kilit("a", 0, 0)],
        kisitlar=yalniz("ogretmen_penceresi"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "b") == [1] and sonuc.toplam_ceza == 0


def test_ogretmen_penceresi_kacinilamazsa_saat_basina_ceza():
    # 2. ve 3. saatte gelemez: en iyi ihtimalle 4. saat, pencere = 2 saat.
    girdi = girdi_kur(
        ayar=OkulAyari(1, 5),
        atamalar=[atama("a", sinif="s1"), atama("b", sinif="s2")],
        musaitlikler=[gelemez("o1", 0, 1), gelemez("o1", 0, 2)],
        kilitli_yerlesimler=[kilit("a", 0, 0)],
        kisitlar=yalniz("ogretmen_penceresi"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "b") == [3]
    assert sonuc.toplam_ceza == 3 * 2
    assert olc(girdi, sonuc.yerlesimler).ogretmen_penceresi == 2


# --- sınıf boşluğu ------------------------------------------------------------------


def test_sinif_bosluklari_gun_sonuna_toplanir():
    # 3. saat kilitli; diğer iki ders 1. ve 2. saati doldurmalı, boşluk kalmamalı.
    girdi = girdi_kur(
        ayar=OkulAyari(1, 6),
        atamalar=[atama("a", ogretmen="o1"), atama("b", ogretmen="o2"), atama("c", ogretmen="o3")],
        kilitli_yerlesimler=[kilit("c", 0, 2)],
        kisitlar=yalniz("sinif_boslugu"),
    )
    sonuc = coz(girdi)
    assert sorted(y.saat for y in sonuc.yerlesimler) == [0, 1, 2]
    assert sonuc.toplam_ceza == 0


def test_bas_taraftaki_bosluk_da_sayilir():
    # Tek ders, öğretmen 1. saatte gelemez: ders 2. saate konur, baştaki 1 boş saat cezalı.
    girdi = girdi_kur(
        ayar=OkulAyari(1, 6),
        atamalar=[atama("a")],
        musaitlikler=[gelemez("o1", 0, 0)],
        kisitlar=yalniz("sinif_boslugu"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "a") == [1]
    assert sonuc.toplam_ceza == 10
    assert olc(girdi, sonuc.yerlesimler).sinif_boslugu == 1


# --- ardışık ders -------------------------------------------------------------------


def test_cift_ders_bitisik_konur():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 6),
        atamalar=[atama("mat", saat=2)],
        kilitli_yerlesimler=[kilit("mat", 0, 3)],
        kisitlar=yalniz("ardisik_ders"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "mat") in ([2, 3], [3, 4]) and sonuc.toplam_ceza == 0


def test_cift_ders_bolunmek_zorundaysa_ceza():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 6),
        atamalar=[atama("mat", saat=2)],
        musaitlikler=[gelemez("o1", 0, 2), gelemez("o1", 0, 4)],
        kilitli_yerlesimler=[kilit("mat", 0, 3)],
        kisitlar=yalniz("ardisik_ders"),
    )
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 2
    assert olc(girdi, sonuc.yerlesimler).bolunmus_ders == 1


def test_iki_gune_bolunen_ders_cezasizdir():
    # 2 saatlik ders iki ayrı güne birer saat konursa "bölünmüş" sayılmaz.
    girdi = girdi_kur(
        ayar=OkulAyari(2, 3),
        atamalar=[atama("mat", saat=2)],
        kilitli_yerlesimler=[kilit("mat", 0, 0), kilit("mat", 1, 0)],
        kisitlar=yalniz("ardisik_ders"),
    )
    assert coz(girdi).toplam_ceza == 0


# --- günlük ders sınırının esnek kipi -----------------------------------------------


def test_gunluk_sinir_esnek_olunca_asilabilir_ama_cezalidir():
    tanimlar = yalniz("yok") + [
        KisitTanimi("gunluk_ders_siniri", {"n": 1}, zorunlu=False, agirlik=4)
    ]
    girdi = girdi_kur(ayar=OkulAyari(1, 3), atamalar=[atama("a", saat=2)], kisitlar=tanimlar)
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 4


# --- tanımlar ve hatalar ------------------------------------------------------------


def test_varsayilan_kurallar_okul_tanimi_olmadan_calisir():
    # kisitlar boş: varsayılan ağırlıklar devrede, 1. saat gelemez -> sınıf boşluğu 10.
    girdi = girdi_kur(ayar=OkulAyari(1, 3), atamalar=[atama("a")], musaitlikler=[gelemez("o1", 0, 0)])
    assert coz(girdi).toplam_ceza == 10


def test_agirlik_sifir_kurali_kapatir():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 3),
        atamalar=[atama("a")],
        musaitlikler=[gelemez("o1", 0, 0)],
        kisitlar=[KisitTanimi("sinif_boslugu", zorunlu=False, agirlik=0)],
    )
    assert coz(girdi).toplam_ceza == 0


@pytest.mark.parametrize(
    "tanim, mesaj",
    [
        (KisitTanimi("tercih_etmez", zorunlu=True), "yalnızca esnek"),
        (KisitTanimi("sinif_boslugu", zorunlu=False, agirlik=-1), "negatif"),
    ],
)
def test_gecersiz_esnek_tanim_on_kontrol_hatasi(tanim, mesaj):
    girdi = girdi_kur(ayar=OkulAyari(1, 3), atamalar=[atama("a")], kisitlar=[tanim])
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=5)
    assert sonuc.durum is CozumDurumu.ON_KONTROL_HATASI
    assert any(mesaj in c.mesaj for c in sonuc.celiskiler), sonuc.celiskiler


# --- bağımsız ölçüm ----------------------------------------------------------------


def test_kalite_olcumu_elle_kurulmus_program():
    #          saat: 0    1    2    3
    # s1 gün 0:      a    -    b    b      -> sınıf boşluğu 1
    # o1 gün 0:      a    -    b    b      -> pencere 1
    # s1 gün 1:      -    c    -    c      -> baştaki boşluk 1 + ortadaki 1; c bölünmüş (1)
    girdi = girdi_kur(
        ayar=OkulAyari(2, 4),
        atamalar=[atama("a"), atama("b", saat=2), atama("c", ogretmen="o2", saat=2)],
        musaitlikler=[Musaitlik("o2", 1, 3, MusaitlikDurumu.TERCIH_ETMEZ)],
    )
    program = [
        Yerlesim("a", 0, 0), Yerlesim("b", 0, 2), Yerlesim("b", 0, 3),
        Yerlesim("c", 1, 1), Yerlesim("c", 1, 3),
    ]
    olcum = olc(girdi, program)
    assert olcum.sinif_boslugu == 3
    assert olcum.ogretmen_penceresi == 1 + 1  # o1 gün 0 + o2 gün 1
    assert olcum.bolunmus_ders == 1
    assert olcum.tercih_etmez == 1


# --- öğretmene boş gün --------------------------------------------------------------

from cozucu import TemelYerlesim, temel_program  # noqa: E402
from cozucu.kalite import ders_gunleri  # noqa: E402


def bes_tek_saat(ogretmen="o1"):
    """o1'in 9-A'ya beş ayrı dersi, her biri haftada 1 saat (5 gün x 6 saat)."""
    return [atama(f"d{i}", ogretmen=ogretmen) for i in range(5)]


def test_bos_gun_hedefe_ulasilir():
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=bes_tek_saat(), kisitlar=yalniz("bos_gun"))
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] <= 4
    assert sonuc.toplam_ceza == 0


def test_bos_gun_hedefe_ulasan_ogretmen_daha_fazla_sikistirilmaz():
    # Dersler dört ayrı güne kilitli: 1 boş gün var, hedef tuttu. Tek güne toplamak mümkün
    # olsa da ceza 0'dır; kural "en az gün" değil "hedef boş gün" ister.
    girdi = girdi_kur(
        ayar=OkulAyari(5, 6),
        atamalar=bes_tek_saat(),
        kilitli_yerlesimler=[kilit("d0", 0, 0), kilit("d1", 1, 0), kilit("d2", 2, 0), kilit("d3", 3, 0)],
        kisitlar=yalniz("bos_gun"),
    )
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 0
    assert olc(girdi, sonuc.yerlesimler).eksik_bos_gun == 0


def test_bos_gun_kacinilamazsa_ceza():
    kilitler = [kilit(f"d{g}", g, 0) for g in range(5)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=bes_tek_saat(), kilitli_yerlesimler=kilitler,
                      kisitlar=yalniz("bos_gun"))
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 4
    assert olc(girdi, sonuc.yerlesimler).eksik_bos_gun == 1


def test_bos_gun_hedef_parametresi():
    tanimlar = yalniz("bos_gun") + [KisitTanimi("bos_gun", {"hedef_bos_gun": 2}, zorunlu=False, agirlik=4)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=bes_tek_saat(), kisitlar=tanimlar)
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] <= 3 and sonuc.toplam_ceza == 0


def test_yuku_yuksek_ogretmene_ceza_yazilmaz():
    # 25 saat, günde en fazla 6: 4 günde (24) bitmez, hedef 5 gün. Her gün çalışır, ceza 0.
    atamalar = [atama(f"a{i}", sinif=f"s{i}", saat=5) for i in range(5)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar, kisitlar=yalniz("bos_gun"))
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] == 5
    assert sonuc.toplam_ceza == 0


def test_bos_gun_ogretmen_gunluk_sinirini_hesaba_katar():
    # 17 saat: M=8 (gün 6 saat) ile 4 güne sığar, hedef 4 gün. M=4 ile 4 x 4 = 16 < 17,
    # hedef 5 gün olur ve her gün çalışan öğretmene ceza yazılmaz.
    atamalar = [atama(f"a{i}", sinif=f"s{i}", saat=h) for i, h in enumerate((4, 4, 4, 5))]
    m4 = yalniz("bos_gun") + [KisitTanimi("ogretmen_gunluk_siniri", {"m": 4})]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar, kisitlar=m4)
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] == 5
    assert sonuc.toplam_ceza == 0

    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar, kisitlar=yalniz("bos_gun"))
    assert ders_gunleri(girdi, coz(girdi).yerlesimler)["o1"] == 4


# --- en az değişiklik ---------------------------------------------------------------


def test_temel_program_yoksa_degisiklik_kurali_etkisiz():
    girdi = girdi_kur(ayar=OkulAyari(1, 3), atamalar=[atama("a")], kisitlar=yalniz("degisiklik"))
    assert coz(girdi).toplam_ceza == 0


def test_uygun_temel_program_aynen_korunur():
    atamalar = [atama("a", ogretmen="o1", saat=2), atama("b", ogretmen="o2", saat=2)]
    temel = [TemelYerlesim("s1", "a", 0, 3), TemelYerlesim("s1", "a", 1, 0),
             TemelYerlesim("s1", "b", 0, 1), TemelYerlesim("s1", "b", 1, 5)]
    girdi = girdi_kur(ayar=OkulAyari(2, 6), atamalar=atamalar, temel_yerlesimler=temel,
                      kisitlar=yalniz("degisiklik"))
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 0
    assert set(temel_program(girdi.atamalar, sonuc.yerlesimler)) == set(temel)


def test_musaitlik_degisince_yalnizca_gereken_ders_kayar():
    # Temel: a 1. saatte, b 2. saatte. o1 artık 1. saatte gelemez. b'yi kaydırıp a'yı 2. saate
    # almak 2 değişiklik; a'yı boş 3. saate almak 1 değişiklik.
    temel = [TemelYerlesim("s1", "a", 0, 0), TemelYerlesim("s1", "b", 0, 1)]
    girdi = girdi_kur(
        ayar=OkulAyari(1, 3),
        atamalar=[atama("a", ogretmen="o1"), atama("b", ogretmen="o2")],
        musaitlikler=[gelemez("o1", 0, 0)],
        temel_yerlesimler=temel,
        kisitlar=yalniz("degisiklik"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "a") == [2] and saatler(sonuc, "b") == [1]
    assert sonuc.toplam_ceza == 20
    assert olc(girdi, sonuc.yerlesimler).degisen_yerlesim == 1


def test_eslestirme_sinif_ders_ile_ogretmen_degisse_de_korunur():
    # Temel program eski atamadan (o1) geldi; ders artık yeni bir atamayla (o2) veriliyor.
    temel = [TemelYerlesim("s1", "mat", 0, 2)]
    girdi = girdi_kur(
        ayar=OkulAyari(1, 4),
        atamalar=[atama("yeni-atama", ders="mat", ogretmen="o2")],
        temel_yerlesimler=temel,
        kisitlar=yalniz("degisiklik"),
    )
    sonuc = coz(girdi)
    assert saatler(sonuc, "yeni-atama") == [2] and sonuc.toplam_ceza == 0


def test_kaldirilan_dersin_hucresi_degisiklik_sayilir():
    temel = [TemelYerlesim("s1", "a", 0, 0), TemelYerlesim("s1", "kaldirildi", 0, 1)]
    girdi = girdi_kur(ayar=OkulAyari(1, 3), atamalar=[atama("a")], temel_yerlesimler=temel,
                      kisitlar=yalniz("degisiklik"))
    sonuc = coz(girdi)
    assert saatler(sonuc, "a") == [0]
    assert sonuc.toplam_ceza == 20
    assert olc(girdi, sonuc.yerlesimler).degisen_yerlesim == 1
