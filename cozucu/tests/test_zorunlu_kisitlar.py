"""Her zorunlu kural için küçük senaryolar. Sonuçlar ayrıca bağımsız doğrulayıcıdan geçirilir."""

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
)
from yardimci import girdi_kur

from cozucu.kisitlar import KAYIT_DEFTERI


def atama(id, sinif="s1", ders=None, ogretmen="o1", saat=1):
    return DersAtama(id=id, sinif_id=sinif, ders_id=ders or id, ogretmen_id=ogretmen, haftalik_saat=saat)


def coz(girdi):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=10)
    if sonuc.basarili:
        assert dogrula(girdi, sonuc.yerlesimler) == []
    return sonuc


def hucreler(sonuc, atama_id):
    return sorted((y.gun, y.saat) for y in sonuc.yerlesimler if y.ders_atama_id == atama_id)


def test_haftalik_saat_kadar_yerlesir():
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[atama("a", saat=4), atama("b", saat=3)])
    sonuc = coz(girdi)
    assert sonuc.durum is CozumDurumu.OPTIMAL
    assert len(hucreler(sonuc, "a")) == 4 and len(hucreler(sonuc, "b")) == 3


def test_bos_girdi_bos_program():
    sonuc = coz(girdi_kur(ayar=OkulAyari(5, 8)))
    assert sonuc.basarili and sonuc.yerlesimler == []


def gelemez(ogretmen, gun, saat):
    return Musaitlik(ogretmen, gun, saat, MusaitlikDurumu.GELEMEZ)


def kilit(atama_id, gun, saat):
    return Yerlesim(atama_id, gun, saat, kilitli=True)


def on_kontrol_turleri(sonuc):
    assert sonuc.durum is CozumDurumu.ON_KONTROL_HATASI
    return {c.tur for c in sonuc.celiskiler}


def test_sinif_ayni_saatte_iki_derste_olamaz():
    # 1 gün x 2 saat, sınıfın iki dersi var, öğretmenler farklı: ancak ayrı saatlere sığar.
    iki = [atama("a", ogretmen="o1"), atama("b", ogretmen="o2")]
    sonuc = coz(girdi_kur(ayar=OkulAyari(1, 2), atamalar=iki))
    assert sonuc.basarili
    assert hucreler(sonuc, "a") != hucreler(sonuc, "b")

    # Ön kontrolden geçer (her öğretmenin 1 müsait saati var) ama ikisi de aynı saate muhtaç.
    ikisi_de_ilk_saat = [gelemez("o1", 0, 1), gelemez("o2", 0, 1)]
    sonuc = coz(girdi_kur(ayar=OkulAyari(1, 2), atamalar=iki, musaitlikler=ikisi_de_ilk_saat))
    assert sonuc.durum is CozumDurumu.COZUMSUZ


def test_sinif_kapasitesi_asilirsa_on_kontrol_yakalar():
    iki = [atama("a", ogretmen="o1"), atama("b", ogretmen="o2")]
    assert on_kontrol_turleri(coz(girdi_kur(ayar=OkulAyari(1, 1), atamalar=iki))) == {"sinif_kapasitesi"}


def test_ogretmen_ayni_saatte_iki_sinifta_olamaz():
    iki = [atama("a", sinif="s1"), atama("b", sinif="s2")]  # ikisi de o1
    sonuc = coz(girdi_kur(ayar=OkulAyari(1, 2), atamalar=iki))
    assert sonuc.basarili
    assert hucreler(sonuc, "a") != hucreler(sonuc, "b")

    # Her iki sınıfın 2. saati başka derslerle kilitli: o1'in iki dersi de 1. saate muhtaç.
    dort = iki + [atama("c", sinif="s1", ogretmen="o2"), atama("d", sinif="s2", ogretmen="o3")]
    girdi = girdi_kur(ayar=OkulAyari(1, 2), atamalar=dort, kilitli_yerlesimler=[kilit("c", 0, 1), kilit("d", 0, 1)])
    assert coz(girdi).durum is CozumDurumu.COZUMSUZ


def test_ogretmen_kapasitesi_asilirsa_on_kontrol_yakalar():
    iki = [atama("a", sinif="s1"), atama("b", sinif="s2")]
    assert on_kontrol_turleri(coz(girdi_kur(ayar=OkulAyari(1, 1), atamalar=iki))) == {"ogretmen_kapasitesi"}


def test_farkli_sinif_ve_ogretmen_ayni_saatte_olabilir():
    iki = [atama("a", sinif="s1", ogretmen="o1"), atama("b", sinif="s2", ogretmen="o2")]
    sonuc = coz(girdi_kur(ayar=OkulAyari(1, 1), atamalar=iki))
    assert sonuc.basarili


def test_gelemez_saatine_ders_konmaz():
    girdi = girdi_kur(ayar=OkulAyari(1, 3), atamalar=[atama("a")], musaitlikler=[gelemez("o1", 0, 0), gelemez("o1", 0, 1)])
    assert hucreler(coz(girdi), "a") == [(0, 2)]


def test_tercih_etmez_zorunlu_degildir():
    # Tek uygun saat "tercih etmez" olsa bile ders oraya konabilir.
    tercih = [Musaitlik("o1", 0, 0, MusaitlikDurumu.TERCIH_ETMEZ)]
    girdi = girdi_kur(ayar=OkulAyari(1, 1), atamalar=[atama("a")], musaitlikler=tercih)
    assert hucreler(coz(girdi), "a") == [(0, 0)]


def test_kilitli_hucre_yerinde_kalir():
    girdi = girdi_kur(
        ayar=OkulAyari(5, 8),
        atamalar=[atama("a", saat=2)],
        kilitli_yerlesimler=[kilit("a", 3, 7)],
    )
    sonuc = coz(girdi)
    assert (3, 7) in hucreler(sonuc, "a")
    kilitli = [y for y in sonuc.yerlesimler if y.kilitli]
    assert [(y.gun, y.saat) for y in kilitli] == [(3, 7)]


def test_gelemez_saate_kilit_on_kontrol_yakalar():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 2),
        atamalar=[atama("a")],
        musaitlikler=[gelemez("o1", 0, 0)],
        kilitli_yerlesimler=[kilit("a", 0, 0)],
    )
    assert on_kontrol_turleri(coz(girdi)) == {"kilit_celiskisi"}


def test_gunluk_ders_siniri_varsayilan_iki():
    # 2 gün x 4 saat, 4 saatlik ders: varsayılan n=2 ile her güne tam 2 saat düşer.
    sonuc = coz(girdi_kur(ayar=OkulAyari(2, 4), atamalar=[atama("a", saat=4)]))
    gunler = [g for g, _ in hucreler(sonuc, "a")]
    assert gunler.count(0) == 2 and gunler.count(1) == 2

    # 5 saat 2 güne sığmaz (2 x 2): ön kontrol yakalar.
    sonuc = coz(girdi_kur(ayar=OkulAyari(2, 4), atamalar=[atama("a", saat=5)]))
    assert on_kontrol_turleri(sonuc) == {"ders_gun_kapasitesi"}


def test_gunluk_ders_siniri_cozucude_de_uygulanir():
    # Ön kontrolden geçer; ama 1. günün ilk üç saati başka derslere kilitli olduğundan
    # matematik 1. güne en fazla 1 saat girebilir: 1 + 2 < 4.
    atamalar = [atama("mat", saat=4)] + [atama(d, ogretmen=f"o-{d}") for d in ("b", "c", "d")]
    kilitler = [kilit("b", 0, 0), kilit("c", 0, 1), kilit("d", 0, 2)]
    girdi = girdi_kur(ayar=OkulAyari(2, 4), atamalar=atamalar, kilitli_yerlesimler=kilitler)
    assert coz(girdi).durum is CozumDurumu.COZUMSUZ


def test_gunluk_ders_siniri_parametre_ile_degisir():
    tek = [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 1})]
    girdi = girdi_kur(ayar=OkulAyari(2, 4), atamalar=[atama("a", saat=3)], kisitlar=tek)
    assert on_kontrol_turleri(coz(girdi)) == {"ders_gun_kapasitesi"}

    uc = [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 3})]
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[atama("a", saat=3)], kisitlar=uc)
    assert coz(girdi).basarili


def test_gunluk_ders_siniri_sinif_ders_cifti_bazinda():
    # Aynı sınıfa aynı ders iki ayrı atamayla girilse de günlük toplam sınırı aşamaz.
    iki = [atama("a1", ders="mat", ogretmen="o1", saat=2), atama("a2", ders="mat", ogretmen="o2", saat=1)]
    sonuc = coz(girdi_kur(ayar=OkulAyari(1, 4), atamalar=iki))
    assert on_kontrol_turleri(sonuc) == {"ders_gun_kapasitesi"}


def test_ogretmen_gunluk_siniri():
    # m=2: o1'in 4 saati 2 güne 2'şer saat dağılmak zorunda.
    iki = [atama("a", sinif="s1", saat=2), atama("b", sinif="s2", saat=2)]
    m2 = [KisitTanimi(tur="ogretmen_gunluk_siniri", parametreler={"m": 2})]
    sonuc = coz(girdi_kur(ayar=OkulAyari(2, 4), atamalar=iki, kisitlar=m2))
    gunler = [y.gun for y in sonuc.yerlesimler]
    assert gunler.count(0) == 2 and gunler.count(1) == 2

    # Tek günde 3 saat: müsait 4 saatin yalnızca 2'si kullanılabilir.
    uc = [atama("a", sinif="s1", saat=2), atama("b", sinif="s2", saat=1)]
    sonuc = coz(girdi_kur(ayar=OkulAyari(1, 4), atamalar=uc, kisitlar=m2))
    assert on_kontrol_turleri(sonuc) == {"ogretmen_kapasitesi"}
    assert "günde en fazla 2 saat" in sonuc.celiskiler[0].mesaj


def test_ogretmensiz_atama_cozulmez_on_kontrol_yakalar():
    iki = [atama("a", sinif="s1", ogretmen=None), atama("b", sinif="s2", ogretmen=None)]
    assert on_kontrol_turleri(coz(girdi_kur(ayar=OkulAyari(1, 1), atamalar=iki))) == {"ogretmen_secilmemis"}


def test_kayit_defteri_okul_geneli_kurallari_icerir():
    assert {"gunluk_ders_siniri", "ogretmen_gunluk_siniri"} <= set(KAYIT_DEFTERI)


@pytest.mark.parametrize(
    "girdi_degisikligi, mesaj_parcasi",
    [
        ({"kisitlar": [KisitTanimi(tur="olmayan_kural")]}, "Bilinmeyen kısıt türü"),
        ({"kisitlar": [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 0})]}, "geçersiz parametre"),
        ({"kisitlar": [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"m": 2})]}, "geçersiz parametre"),
        ({"kilitli_yerlesimler": [Yerlesim("yok", 0, 0)]}, "tanımlı olmayan bir atamaya"),
        ({"kilitli_yerlesimler": [Yerlesim("a", 9, 0)]}, "gün/saat aralığı dışında"),
        ({"musaitlikler": [Musaitlik("o1", 0, 9, MusaitlikDurumu.GELEMEZ)]}, "gün/saat aralığı dışında"),
    ],
)
def test_tutarsiz_girdi_istisna_degil_on_kontrol_hatasi_doner(girdi_degisikligi, mesaj_parcasi):
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[atama("a")], **girdi_degisikligi)
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=5)
    assert sonuc.durum is CozumDurumu.ON_KONTROL_HATASI
    assert any(mesaj_parcasi in c.mesaj for c in sonuc.celiskiler), sonuc.celiskiler
