"""Günlere göre ders saati ve öğle arası (K3; docs/kisisellestirme-plani.md 4.3)."""

import pytest

from cozucu import (
    CozumDurumu,
    CozumGirdisi,
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
from cozucu.celiski import celiskileri_bul
from cozucu.kalite import agirlikli_ceza
from cozucu.kisitlar import etkin_agirliklar
from cozucu.on_kontrol import on_kontrol
from cozucu.yuk import YukHesabi, bos_gun_hedefi, kapasite_metni
from yardimci import girdi_kur

from test_esnek_kisitlar import yalniz

# Pazartesi-perşembe 6 saat, cuma 4 saat: haftada 28 saat.
KISA_CUMA = OkulAyari(5, 6, gun_saatleri=(6, 6, 6, 6, 4))


def coz(girdi: CozumGirdisi, sure: float = 10):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=sure)
    assert sonuc.durum in (CozumDurumu.OPTIMAL, CozumDurumu.UYGUN), sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    return sonuc


# --- okul ayarı -------------------------------------------------------------------------


def test_her_gun_ayni_varsayilan():
    ayar = OkulAyari(5, 8)
    assert ayar.gunluk_saatler == (8,) * 5
    assert ayar.haftalik_kapasite == 40
    assert not ayar.gunlere_gore_farkli


def test_gunlere_gore_kapasite_ve_aralik():
    assert KISA_CUMA.haftalik_kapasite == 28
    assert KISA_CUMA.gunlere_gore_farkli
    assert KISA_CUMA.aralikta(4, 3) and not KISA_CUMA.aralikta(4, 4)
    assert KISA_CUMA.aralikta(0, 5)


def test_json_listesi_demete_cevrilir():
    assert OkulAyari(2, 3, gun_saatleri=[3, 2]).gun_saatleri == (3, 2)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "alanlar",
    [
        {"gun_saatleri": (6, 6)},  # gün sayısı tutmuyor
        {"gun_saatleri": (6, 6, 6, 6, 7)},  # en uzun günden uzun
        {"gun_saatleri": (6, 6, 6, 6, 0)},  # boş gün değil, en az 1 saat
        {"ogle_arasi_sonra": 6},  # son dersten sonra öğle arası olmaz
        {"ogle_arasi_sonra": 0},
    ],
)
def test_gecersiz_ayar(alanlar):
    with pytest.raises(ValueError):
        OkulAyari(5, 6, **alanlar)


def test_ogle_arasi_kisa_gunde_yok():
    ayar = OkulAyari(5, 6, gun_saatleri=(6, 6, 6, 6, 4), ogle_arasi_sonra=4)
    assert ayar.ogle_arasiyla_ayrilir(0, 3)  # 4. ile 5. ders arası
    assert not ayar.ogle_arasiyla_ayrilir(0, 2)
    assert not ayar.ogle_arasiyla_ayrilir(4, 3)  # cuma 4 saat: öğle arasından önce biter


# --- çözücü -------------------------------------------------------------------------------


def test_kisa_gunun_sonuna_ders_konmaz():
    # Tek sınıf 28 saat: haftanın bütün hücreleri dolmak zorunda; cuma yalnızca 4 saat.
    atamalar = [DersAtama(f"a{i}", "s1", f"d{i}", f"o{i}", 4) for i in range(7)]
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=atamalar)
    sonuc = coz(girdi)
    assert len(sonuc.yerlesimler) == 28
    assert all(y.saat < 4 for y in sonuc.yerlesimler if y.gun == 4)


def test_dogrulayici_kisa_gunun_disini_yakalar():
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama("a", "s1", "d", "o", 1)])
    hatalar = dogrula(girdi, [Yerlesim("a", 4, 5)])
    assert any("aralık dışında" in h for h in hatalar)


def test_kisa_gunde_kilit_aralik_disi():
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama("a", "s1", "d", "o", 1)],
                      kilitli_yerlesimler=[Yerlesim("a", 4, 5, kilitli=True)])
    sorunlar = on_kontrol(girdi)
    assert [c.tur for c in sorunlar] == ["tutarsiz_veri"]
    assert "Cuma 6. saat" in sorunlar[0].mesaj


def test_ogle_arasiyla_bolunen_ders_bolunmus_sayilir():
    # Günde tek ders, iki saat, 2. ve 3. saat kilitli; öğle arası 2. dersten sonra: bölünmüş (1).
    kilitler = [Yerlesim("a", 0, 1, kilitli=True), Yerlesim("a", 0, 2, kilitli=True)]
    ayar = OkulAyari(1, 4, ogle_arasi_sonra=2)
    girdi = girdi_kur(ayar=ayar, atamalar=[DersAtama("a", "s1", "d", "o", 2)], kilitli_yerlesimler=kilitler,
                      kisitlar=yalniz("ardisik_ders"))
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).bolunmus_ders == 1
    assert sonuc.toplam_ceza == 2
    # Öğle arası olmasa aynı yerleşim bitişiktir.
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[DersAtama("a", "s1", "d", "o", 2)],
                      kilitli_yerlesimler=kilitler, kisitlar=yalniz("ardisik_ders"))
    assert coz(girdi).toplam_ceza == 0


def test_cozucu_ogle_arasinin_iki_yanina_cift_ders_koymaz():
    # İki saatlik ders, 3 saatlik gün, öğle arası 2. dersten sonra: bitişik tek yer 1.-2. saat.
    girdi = girdi_kur(ayar=OkulAyari(1, 3, ogle_arasi_sonra=2), atamalar=[DersAtama("a", "s1", "d", "o", 2)],
                      kisitlar=yalniz("ardisik_ders"))
    sonuc = coz(girdi)
    assert sorted(y.saat for y in sonuc.yerlesimler) == [0, 1]
    assert sonuc.toplam_ceza == 0


def test_kalite_olcumu_model_cezasiyla_tutarli():
    # Kısa cuma ve öğle arası birlikteyken bütün esnek kurallar açık: ölçüm = model cezası.
    ayar = OkulAyari(5, 6, gun_saatleri=(6, 6, 6, 6, 4), ogle_arasi_sonra=4)
    atamalar = [DersAtama(f"a{i}", f"s{i % 2}", f"d{i}", f"o{i % 3}", 3) for i in range(6)]
    girdi = girdi_kur(ayar=ayar, atamalar=atamalar)
    sonuc = coz(girdi)
    assert sonuc.durum is CozumDurumu.OPTIMAL
    assert agirlikli_ceza(olc(girdi, sonuc.yerlesimler), etkin_agirliklar(girdi)) == sonuc.toplam_ceza


# --- kapasite ve ön kontrol -------------------------------------------------------------


def test_sinif_kapasitesi_gun_uzunluklariyla():
    # 29 saat: her gün 6 olsa sığardı (30), cuma 4 saatle 28.
    atamalar = [DersAtama("a1", "s1", "d1", "o1", 15), DersAtama("a2", "s1", "d2", "o2", 14)]
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=atamalar)
    yuk = YukHesabi(girdi).sinif_yukleri()[0]
    assert yuk.kapasite == 28 and yuk.asim
    sorunlar = [c for c in on_kontrol(girdi) if c.tur == "sinif_kapasitesi"]
    assert len(sorunlar) == 1
    assert "haftalık kapasite 28 saat (4 gün × 6 saat, Cuma 4 saat)" in sorunlar[0].mesaj
    # Aynı yük her gün 6 saatlik okulda sorun değil.
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar)
    assert not [c for c in on_kontrol(girdi) if c.tur == "sinif_kapasitesi"]


def test_kapasite_metni():
    assert kapasite_metni((8, 8, 8, 8, 8)) == "5 gün × 8 saat"
    assert kapasite_metni((8, 8, 8, 8, 7)) == "4 gün × 8 saat, Cuma 7 saat"
    assert kapasite_metni((8, 8, 6, 6)) == "2 gün × 8 saat, Çarşamba 6 saat, Perşembe 6 saat"


def test_ogretmen_kapasitesi_gun_uzunluklariyla():
    # Öğretmen pazartesi bütün gün gelemez: müsait 6+6+6+4 = 22 saat (her gün 6 olsa 24).
    pazartesi = [Musaitlik("o1", 0, s, MusaitlikDurumu.GELEMEZ) for s in range(6)]
    atamalar = [DersAtama(f"a{i}", f"s{i}", "d", "o1", 1) for i in range(23)]
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=atamalar, musaitlikler=pazartesi)
    yuk = next(y for y in YukHesabi(girdi).ogretmen_yukleri() if y.ogretmen_id == "o1")
    assert (yuk.musait_saat, yuk.kullanilabilir_saat, yuk.asim) == (22, 22, True)
    sorunlar = [c for c in on_kontrol(girdi) if c.tur == "ogretmen_kapasitesi"]
    assert len(sorunlar) == 1 and "müsait olduğu 22 saat" in sorunlar[0].mesaj


def test_ogretmen_gunluk_siniri_kisa_gunle_birlikte():
    # M = 5: pazartesi-perşembe 5'er saat, cuma günün kendisi 4 saat: en fazla 24.
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama(f"a{i}", f"s{i}", "d", "o1", 1) for i in range(25)],
                      kisitlar=[KisitTanimi("ogretmen_gunluk_siniri", {"m": 5})])
    yuk = next(y for y in YukHesabi(girdi).ogretmen_yukleri() if y.ogretmen_id == "o1")
    assert (yuk.musait_saat, yuk.kullanilabilir_saat) == (28, 24)


def test_kisa_gunde_ogretmen_musaitligi_aralik_disi():
    # Cuma 5. saat artık yok: oraya girilmiş müsaitlik tutarsız veridir (API azaltmada siler).
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama("a", "s1", "d", "o1", 1)],
                      musaitlikler=[Musaitlik("o1", 4, 4, MusaitlikDurumu.GELEMEZ)])
    sorunlar = on_kontrol(girdi)
    assert [c.tur for c in sorunlar] == ["tutarsiz_veri"]


def test_sinif_musaitligi_kisa_gunu_sayar():
    # 9-A'nın tek öğretmeni cuma dışında gelemez; cuma 4 saat: 5 saatlik ders sığmaz.
    gelemez = [Musaitlik("o1", g, s, MusaitlikDurumu.GELEMEZ) for g in range(4) for s in range(6)]
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama("a", "s1", "d", "o1", 5)], musaitlikler=gelemez,
                      kisitlar=[])
    turler = {c.tur for c in on_kontrol(girdi)}
    assert turler & {"ogretmen_kapasitesi", "ders_gun_kapasitesi", "sinif_musaitligi"}


def test_sinif_musaitligi_var_olmayan_saatleri_saymaz():
    # 9-A'nın 28 saati var (haftanın tamamı). İki öğretmeni de pazartesi 1. saatte gelemez:
    # gelinebilen 27 saat. Cuma 5.-6. saat sayılsaydı 29 saat "var" görünürdü.
    atamalar = [DersAtama(f"a{i}", "s1", f"d{i}", f"o{i % 2}", 2) for i in range(14)]
    gelemez = [Musaitlik(o, 0, 0, MusaitlikDurumu.GELEMEZ) for o in ("o0", "o1")]
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=atamalar, musaitlikler=gelemez)
    sorunlar = on_kontrol(girdi)
    assert [c.tur for c in sorunlar] == ["sinif_musaitligi"]
    assert "gelebildiği yalnızca 27 saat" in sorunlar[0].mesaj


def test_bos_gun_hedefi_kisa_gunu_sayar():
    # 24 saat, M = 6, cuma 4 saat: en uzun dört gün (6+6+6+6) yeter; 26 saatte 5 gün gerekir.
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama("a", "s1", "d", "o1", 1)])
    assert bos_gun_hedefi(girdi, "o1", 24).gun == 4
    assert bos_gun_hedefi(girdi, "o1", 26).gun == 5
    # Bir uzun, dört kısa gün (6, 2, 2, 2, 2): 10 saat için 3 gün gerekir (6+2+2); her gün 6
    # saat sayılsaydı 2 gün denirdi ve öğretmene kaçınılmaz ceza yazılırdı.
    girdi = girdi_kur(ayar=OkulAyari(5, 6, gun_saatleri=(6, 2, 2, 2, 2)), atamalar=[DersAtama("a", "s1", "d", "o1", 1)])
    assert bos_gun_hedefi(girdi, "o1", 10).gun == 4  # gün sayısı − 1 boş gün = 4 baskın
    assert bos_gun_hedefi(girdi, "o1", 12).gun == 4
    girdi.kisitlar.append(KisitTanimi("bos_gun", {"hedef_bos_gun": 3}, zorunlu=False, agirlik=4))
    assert bos_gun_hedefi(girdi, "o1", 10).gun == 3  # hedef 2 gün, ama yük 3 gün istiyor


# --- çelişki açıklaması -------------------------------------------------------------------


def test_celiski_kisa_gunu_adiyla_soyler():
    # Öğretmen yalnızca cuma 4.-6. saatte müsait; cuma 4 saat olduğu için yalnızca 4. saat var,
    # 2 saatlik ders sığmaz. (Ön kontrol de yakalar; burada çelişki analizinin gün uzunluğunu
    # adıyla söylediği denenir.)
    gelemez = [Musaitlik("o1", g, s, MusaitlikDurumu.GELEMEZ) for g in range(5) for s in range(6)
               if not (g == 4 and s >= 3)]
    girdi = girdi_kur(ayar=KISA_CUMA, atamalar=[DersAtama("a", "s1", "d", "o1", 2)], musaitlikler=gelemez)
    celiskiler = celiskileri_bul(girdi, sure_siniri_sn=10)
    assert len(celiskiler) == 1
    assert "Cuma 4 saat" in celiskiler[0].mesaj
