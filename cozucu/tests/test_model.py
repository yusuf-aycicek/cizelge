import pytest

from cozucu import (
    CozumDurumu,
    CozumGirdisi,
    CozumSonucu,
    DersAtama,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    ProgramCozucu,
    Yerlesim,
)


def test_okul_ayari_kapasite():
    assert OkulAyari(gun_sayisi=5, gunluk_ders_saati=8).haftalik_kapasite == 40


@pytest.mark.parametrize("gun,saat", [(0, 8), (8, 8), (5, 0)])
def test_okul_ayari_gecersiz_degerleri_reddeder(gun, saat):
    with pytest.raises(ValueError):
        OkulAyari(gun_sayisi=gun, gunluk_ders_saati=saat)


def test_ders_atama_haftalik_saat_pozitif_olmali():
    with pytest.raises(ValueError):
        DersAtama(id="a", sinif_id="s", ders_id="d", ogretmen_id="o", haftalik_saat=0)


def test_ders_atama_ogretmensiz_olabilir():
    atama = DersAtama(id="a", sinif_id="s", ders_id="d", ogretmen_id=None, haftalik_saat=2)
    assert atama.ogretmen_id is None


def test_negatif_gun_saat_reddedilir():
    with pytest.raises(ValueError):
        Yerlesim(ders_atama_id="a", gun=-1, saat=0)
    with pytest.raises(ValueError):
        Musaitlik(ogretmen_id="o", gun=0, saat=-1, durum=MusaitlikDurumu.GELEMEZ)


def test_sonuc_basarili_mi():
    assert CozumSonucu(durum=CozumDurumu.OPTIMAL).basarili
    assert CozumSonucu(durum=CozumDurumu.UYGUN).basarili
    assert not CozumSonucu(durum=CozumDurumu.COZUMSUZ).basarili
    assert not CozumSonucu(durum=CozumDurumu.ON_KONTROL_HATASI).basarili


def test_arayuz_dogrudan_orneklenemez():
    with pytest.raises(TypeError):
        ProgramCozucu()  # type: ignore[abstract]


def test_arayuz_gerceklenebilir():
    class SahteCozucu(ProgramCozucu):
        def coz(self, girdi, sure_siniri_sn=60.0):
            return CozumSonucu(durum=CozumDurumu.BILINMIYOR)

    sonuc = SahteCozucu().coz(CozumGirdisi(ayar=OkulAyari(5, 8)))
    assert sonuc.durum is CozumDurumu.BILINMIYOR
