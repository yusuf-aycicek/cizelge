"""Öğretmen ve sınıf yükü (yuk.py): ön kontrolün ve API'nin ders dağılımı özetinin ortak hesabı."""

from cozucu import (
    CozumGirdisi,
    Ders,
    DersAtama,
    Kapsam,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Ogretmen,
    Sinif,
)
from cozucu.on_kontrol import on_kontrol
from cozucu.yuk import YukHesabi


def girdi(**alanlar) -> CozumGirdisi:
    """5 gün x 6 saat. Ayşe: 9-A ve 9-B Matematik (6+6). Zeynep: 9-A Fizik (3). Ali: dersi yok.
    9-B Fizik'in öğretmeni seçilmemiş."""
    varsayilan = dict(
        ayar=OkulAyari(5, 6),
        ogretmenler=[Ogretmen("o-ayse", "Ayşe Yılmaz"), Ogretmen("o-zeynep", "Zeynep Demir"),
                     Ogretmen("o-ali", "Ali Çelik")],
        siniflar=[Sinif("s-9a", "9-A", 9), Sinif("s-9b", "9-B", 9), Sinif("s-10a", "10-A", 10)],
        dersler=[Ders("d-mat", "Matematik"), Ders("d-fiz", "Fizik")],
        atamalar=[
            DersAtama("a1", "s-9a", "d-mat", "o-ayse", 6),
            DersAtama("a2", "s-9b", "d-mat", "o-ayse", 6),
            DersAtama("a3", "s-9a", "d-fiz", "o-zeynep", 3),
            DersAtama("a4", "s-9b", "d-fiz", None, 3),
        ],
    )
    varsayilan.update(alanlar)
    return CozumGirdisi(**varsayilan)


def gelemez(ogretmen, gun, saatler):
    return [Musaitlik(ogretmen, gun, s, MusaitlikDurumu.GELEMEZ) for s in saatler]


def ogretmenler(g: CozumGirdisi) -> dict:
    return {y.ogretmen_id: y for y in YukHesabi(g).ogretmen_yukleri()}


def test_her_ogretmen_listelenir_dersi_olmayan_da():
    yukler = YukHesabi(girdi()).ogretmen_yukleri()
    assert [y.ogretmen_id for y in yukler] == ["o-ayse", "o-zeynep", "o-ali"]
    ayse, zeynep, ali = yukler
    assert (ayse.ders_saati, ayse.musait_saat, ayse.kullanilabilir_saat) == (12, 30, 30)
    assert ayse.atama_idleri == ("a1", "a2")
    assert zeynep.ders_saati == 3
    assert (ali.ders_saati, ali.atama_idleri, ali.asim) == (0, (), False)


def test_gelemez_saatler_musaitlikten_duser_tercih_etmez_dusmez():
    g = girdi(musaitlikler=[
        *gelemez("o-ayse", 0, range(6)),  # pazartesi bütün gün
        *gelemez("o-ayse", 1, [0, 1]),
        Musaitlik("o-ayse", 2, 0, MusaitlikDurumu.TERCIH_ETMEZ),
    ])
    ayse = ogretmenler(g)["o-ayse"]
    assert ayse.musait_saat == 30 - 8
    assert YukHesabi(g).musait_saat("o-ayse") == [0, 4, 6, 6, 6]


def test_ayni_gelemez_hucresi_iki_kez_sayilmaz():
    g = girdi(musaitlikler=gelemez("o-ayse", 0, [0]) * 2)
    assert ogretmenler(g)["o-ayse"].musait_saat == 29


def test_okulun_araligi_disindaki_gelemez_sayilmaz():
    g = girdi(musaitlikler=[*gelemez("o-ayse", 0, [6, 7]), *gelemez("o-ayse", 5, [0])])
    assert ogretmenler(g)["o-ayse"].musait_saat == 30


def test_gunluk_sinir_kullanilabilir_saati_kisar():
    g = girdi(kisitlar=[KisitTanimi("ogretmen_gunluk_siniri", {"m": 4})])
    ayse = ogretmenler(g)["o-ayse"]
    assert (ayse.musait_saat, ayse.kullanilabilir_saat) == (30, 20)


def test_gunluk_sinir_gun_uzunlugundan_buyukse_gun_uzunlugu_gecerli():
    g = girdi(kisitlar=[KisitTanimi("ogretmen_gunluk_siniri", {"m": 10})])
    assert YukHesabi(g).m == 6
    assert ogretmenler(g)["o-ayse"].kullanilabilir_saat == 30


def test_varsayilan_gunluk_sinir_8():
    g = girdi(ayar=OkulAyari(5, 10))
    assert YukHesabi(g).m == 8
    assert ogretmenler(g)["o-ayse"].kullanilabilir_saat == 40


def test_asim_ve_mesaj():
    g = girdi(musaitlikler=[*gelemez("o-ayse", 0, range(6)), *gelemez("o-ayse", 1, range(6)),
                            *gelemez("o-ayse", 2, range(6)), *gelemez("o-ayse", 3, range(2))])
    hesap = YukHesabi(g)
    ayse = {y.ogretmen_id: y for y in hesap.ogretmen_yukleri()}["o-ayse"]
    assert (ayse.ders_saati, ayse.kullanilabilir_saat, ayse.asim) == (12, 10, True)
    assert hesap.ogretmen_mesaji(ayse) == "Ayşe Yılmaz'ın 12 saat dersi var, müsait olduğu 10 saat var."
    zeynep = {y.ogretmen_id: y for y in hesap.ogretmen_yukleri()}["o-zeynep"]
    assert hesap.ogretmen_mesaji(zeynep) is None


def test_tam_sinirda_asim_yok():
    g = girdi(kisitlar=[KisitTanimi("ogretmen_gunluk_siniri", {"m": 2}),
                        KisitTanimi("gunluk_ders_siniri", {"n": 6})],
              atamalar=[DersAtama("a1", "s-9a", "d-mat", "o-ayse", 10)])
    ayse = ogretmenler(g)["o-ayse"]
    assert (ayse.ders_saati, ayse.kullanilabilir_saat, ayse.asim) == (10, 10, False)


def test_sinif_yukleri():
    hesap = YukHesabi(girdi())
    yukler = {y.sinif_id: y for y in hesap.sinif_yukleri()}
    assert list(yukler) == ["s-9a", "s-9b", "s-10a"]
    assert (yukler["s-9a"].ders_saati, yukler["s-9a"].kapasite, yukler["s-9a"].ogretmensiz_atama) == (9, 30, 0)
    assert (yukler["s-9b"].ders_saati, yukler["s-9b"].ogretmensiz_atama) == (9, 1)
    assert (yukler["s-10a"].ders_saati, yukler["s-10a"].atama_idleri) == (0, ())
    assert hesap.sinif_mesaji(yukler["s-9a"]) is None


def test_sinif_asimi_ve_mesaj():
    g = girdi(atamalar=[DersAtama("a1", "s-9a", "d-mat", "o-ayse", 20),
                        DersAtama("a3", "s-9a", "d-fiz", "o-zeynep", 11)])
    hesap = YukHesabi(g)
    yuk = hesap.sinif_yukleri()[0]
    assert (yuk.ders_saati, yuk.asim) == (31, True)
    assert hesap.sinif_mesaji(yuk) == (
        "9-A sınıfının haftada 31 saat dersi var, haftalık kapasite 30 saat (5 gün × 6 saat)."
    )


def test_on_kontrol_ayni_hesabi_ve_mesaji_kullanir():
    """Tek kaynak: ön kontrolün kapasite sorunları, yük hesabının aşımlarıyla birebir aynı."""
    g = girdi(
        atamalar=[DersAtama("a1", "s-9a", "d-mat", "o-ayse", 20),
                  DersAtama("a3", "s-9a", "d-fiz", "o-zeynep", 11),
                  DersAtama("a2", "s-9b", "d-mat", "o-ayse", 6)],
        musaitlikler=gelemez("o-ayse", 0, range(6)),
        kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 6})],
    )
    hesap = YukHesabi(g)
    beklenen = {hesap.ogretmen_mesaji(y) for y in hesap.ogretmen_yukleri() if y.asim}
    beklenen |= {hesap.sinif_mesaji(y) for y in hesap.sinif_yukleri() if y.asim}
    assert len(beklenen) == 2
    kapasite = {s.mesaj for s in on_kontrol(g) if s.tur in ("ogretmen_kapasitesi", "sinif_kapasitesi")}
    assert kapasite == beklenen


def test_hedefli_kapasite_bos_gun_hedefini_hesaba_katar():
    # 5 gün x 6 saat: okul geneli hedef 1 boş gün -> en geniş 4 gün = 24 (kullanılabilir 30).
    assert YukHesabi(girdi()).hedefli_kapasite("o-ayse") == 24
    # Öğretmene özel hedef 4 boş gün -> 1 gün; pazartesi bütün gün gelemez, salı 2 saat gelemez.
    ozel = KisitTanimi("bos_gun", {"hedef_bos_gun": 4}, zorunlu=False, kapsam=Kapsam(ogretmen_id="o-ayse"))
    g = girdi(kisitlar=[ozel], musaitlikler=[*gelemez("o-ayse", 0, range(6)), *gelemez("o-ayse", 1, [0, 1])])
    assert YukHesabi(g).hedefli_kapasite("o-ayse") == 6
    # Günlük sınır da sayılır (m = 4): 4 gün x 4.
    assert YukHesabi(girdi(kisitlar=[KisitTanimi("ogretmen_gunluk_siniri", {"m": 4})])).hedefli_kapasite("o-ayse") == 16


def test_hedefli_kapasite_hedef_yoksa_bos():
    sifir = KisitTanimi("bos_gun", {"hedef_bos_gun": 0}, zorunlu=False, agirlik=4)
    assert YukHesabi(girdi(kisitlar=[sifir])).hedefli_kapasite("o-ayse") is None
    kapali = KisitTanimi("bos_gun", {"hedef_bos_gun": 1}, zorunlu=False, agirlik=0)
    assert YukHesabi(girdi(kisitlar=[kapali])).hedefli_kapasite("o-ayse") is None
