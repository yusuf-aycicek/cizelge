"""Her zorunlu kural için küçük senaryolar. Sonuçlar ayrıca bağımsız doğrulayıcıdan geçirilir."""

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
)
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
    girdi = CozumGirdisi(ayar=OkulAyari(5, 6), atamalar=[atama("a", saat=4), atama("b", saat=3)])
    sonuc = coz(girdi)
    assert sonuc.durum is CozumDurumu.OPTIMAL
    assert len(hucreler(sonuc, "a")) == 4 and len(hucreler(sonuc, "b")) == 3


def test_bos_girdi_bos_program():
    sonuc = coz(CozumGirdisi(ayar=OkulAyari(5, 8)))
    assert sonuc.basarili and sonuc.yerlesimler == []


def test_sinif_ayni_saatte_iki_derste_olamaz():
    # 1 gün x 2 saat, sınıfın iki dersi var, öğretmenler farklı: ancak ayrı saatlere sığar.
    iki = [atama("a", ogretmen="o1"), atama("b", ogretmen="o2")]
    sonuc = coz(CozumGirdisi(ayar=OkulAyari(1, 2), atamalar=iki))
    assert sonuc.basarili
    assert hucreler(sonuc, "a") != hucreler(sonuc, "b")

    sonuc = coz(CozumGirdisi(ayar=OkulAyari(1, 1), atamalar=iki))
    assert sonuc.durum is CozumDurumu.COZUMSUZ


def test_ogretmen_ayni_saatte_iki_sinifta_olamaz():
    iki = [atama("a", sinif="s1"), atama("b", sinif="s2")]  # ikisi de o1
    sonuc = coz(CozumGirdisi(ayar=OkulAyari(1, 2), atamalar=iki))
    assert sonuc.basarili
    assert hucreler(sonuc, "a") != hucreler(sonuc, "b")

    sonuc = coz(CozumGirdisi(ayar=OkulAyari(1, 1), atamalar=iki))
    assert sonuc.durum is CozumDurumu.COZUMSUZ


def test_farkli_sinif_ve_ogretmen_ayni_saatte_olabilir():
    iki = [atama("a", sinif="s1", ogretmen="o1"), atama("b", sinif="s2", ogretmen="o2")]
    sonuc = coz(CozumGirdisi(ayar=OkulAyari(1, 1), atamalar=iki))
    assert sonuc.basarili


def test_gelemez_saatine_ders_konmaz():
    gelemez = [Musaitlik("o1", 0, s, MusaitlikDurumu.GELEMEZ) for s in (0, 1)]
    girdi = CozumGirdisi(ayar=OkulAyari(1, 3), atamalar=[atama("a")], musaitlikler=gelemez)
    assert hucreler(coz(girdi), "a") == [(0, 2)]


def test_tercih_etmez_zorunlu_degildir():
    # Tek uygun saat "tercih etmez" olsa bile ders oraya konabilir.
    tercih = [Musaitlik("o1", 0, 0, MusaitlikDurumu.TERCIH_ETMEZ)]
    girdi = CozumGirdisi(ayar=OkulAyari(1, 1), atamalar=[atama("a")], musaitlikler=tercih)
    assert hucreler(coz(girdi), "a") == [(0, 0)]


def test_kilitli_hucre_yerinde_kalir():
    girdi = CozumGirdisi(
        ayar=OkulAyari(5, 8),
        atamalar=[atama("a", saat=2)],
        kilitli_yerlesimler=[Yerlesim("a", 3, 7, kilitli=True)],
    )
    sonuc = coz(girdi)
    assert (3, 7) in hucreler(sonuc, "a")
    kilitli = [y for y in sonuc.yerlesimler if y.kilitli]
    assert [(y.gun, y.saat) for y in kilitli] == [(3, 7)]


def test_kilit_gelemez_ile_celisirse_cozumsuz():
    girdi = CozumGirdisi(
        ayar=OkulAyari(1, 2),
        atamalar=[atama("a")],
        musaitlikler=[Musaitlik("o1", 0, 0, MusaitlikDurumu.GELEMEZ)],
        kilitli_yerlesimler=[Yerlesim("a", 0, 0, kilitli=True)],
    )
    assert coz(girdi).durum is CozumDurumu.COZUMSUZ


def test_gunluk_ders_siniri_varsayilan_iki():
    # 2 gün x 4 saat, 4 saatlik ders: varsayılan n=2 ile her güne tam 2 saat düşer.
    sonuc = coz(CozumGirdisi(ayar=OkulAyari(2, 4), atamalar=[atama("a", saat=4)]))
    gunler = [g for g, _ in hucreler(sonuc, "a")]
    assert gunler.count(0) == 2 and gunler.count(1) == 2

    sonuc = coz(CozumGirdisi(ayar=OkulAyari(2, 4), atamalar=[atama("a", saat=5)]))
    assert sonuc.durum is CozumDurumu.COZUMSUZ


def test_gunluk_ders_siniri_parametre_ile_degisir():
    tek = [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 1})]
    girdi = CozumGirdisi(ayar=OkulAyari(2, 4), atamalar=[atama("a", saat=3)], kisitlar=tek)
    assert coz(girdi).durum is CozumDurumu.COZUMSUZ

    uc = [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 3})]
    girdi = CozumGirdisi(ayar=OkulAyari(1, 4), atamalar=[atama("a", saat=3)], kisitlar=uc)
    assert coz(girdi).basarili


def test_gunluk_ders_siniri_sinif_ders_cifti_bazinda():
    # Aynı sınıfa aynı ders iki ayrı atamayla girilse de günlük toplam sınırı aşamaz.
    iki = [atama("a1", ders="mat", ogretmen="o1", saat=2), atama("a2", ders="mat", ogretmen="o2", saat=1)]
    sonuc = coz(CozumGirdisi(ayar=OkulAyari(1, 4), atamalar=iki))
    assert sonuc.durum is CozumDurumu.COZUMSUZ


def test_ogretmensiz_atama_ogretmen_cakismasina_katilmaz():
    iki = [atama("a", sinif="s1", ogretmen=None), atama("b", sinif="s2", ogretmen=None)]
    assert coz(CozumGirdisi(ayar=OkulAyari(1, 1), atamalar=iki)).basarili


def test_kayit_defteri_gunluk_siniri_icerir():
    assert "gunluk_ders_siniri" in KAYIT_DEFTERI


@pytest.mark.parametrize(
    "girdi_degisikligi, mesaj_parcasi",
    [
        ({"kisitlar": [KisitTanimi(tur="olmayan_kural")]}, "Bilinmeyen kısıt türü"),
        ({"kisitlar": [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 0})]}, "geçersiz parametre"),
        ({"kisitlar": [KisitTanimi(tur="gunluk_ders_siniri", parametreler={"m": 2})]}, "geçersiz parametre"),
        ({"kilitli_yerlesimler": [Yerlesim("yok", 0, 0)]}, "Bilinmeyen ders ataması"),
        ({"kilitli_yerlesimler": [Yerlesim("a", 9, 0)]}, "okul ayarının dışında"),
        ({"musaitlikler": [Musaitlik("o1", 0, 9, MusaitlikDurumu.GELEMEZ)]}, "okul ayarının dışında"),
    ],
)
def test_tutarsiz_girdi_istisna_degil_on_kontrol_hatasi_doner(girdi_degisikligi, mesaj_parcasi):
    girdi = CozumGirdisi(ayar=OkulAyari(5, 6), atamalar=[atama("a")], **girdi_degisikligi)
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=5)
    assert sonuc.durum is CozumDurumu.ON_KONTROL_HATASI
    assert mesaj_parcasi in sonuc.mesajlar[0]
