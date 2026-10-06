from cozucu import (
    CozumDurumu,
    CozumGirdisi,
    CozumSonucu,
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
from cozucu.veri_io import (
    girdi_from_dict,
    girdi_oku,
    girdi_to_dict,
    girdi_yaz,
    sonuc_from_dict,
    sonuc_to_dict,
)


def ornek_girdi() -> CozumGirdisi:
    return CozumGirdisi(
        ayar=OkulAyari(gun_sayisi=5, gunluk_ders_saati=6),
        ogretmenler=[Ogretmen(id="o1", ad="Ayşe Yılmaz", brans="Matematik")],
        siniflar=[Sinif(id="s1", ad="9-A", seviye=9)],
        dersler=[Ders(id="d1", ad="Matematik", kisa_ad="MAT")],
        atamalar=[DersAtama(id="a1", sinif_id="s1", ders_id="d1", ogretmen_id="o1", haftalik_saat=4)],
        musaitlikler=[Musaitlik(ogretmen_id="o1", gun=0, saat=0, durum=MusaitlikDurumu.GELEMEZ)],
        kisitlar=[KisitTanimi(tur="gunluk_ders_siniri", parametreler={"n": 2})],
        kilitli_yerlesimler=[Yerlesim(ders_atama_id="a1", gun=1, saat=2, kilitli=True)],
    )


def test_girdi_sozluk_gidis_donus():
    girdi = ornek_girdi()
    sozluk = girdi_to_dict(girdi)
    assert sozluk["musaitlikler"][0]["durum"] == "gelemez"
    assert girdi_from_dict(sozluk) == girdi


def test_girdi_dosya_gidis_donus(tmp_path):
    yol = tmp_path / "girdi.json"
    girdi_yaz(ornek_girdi(), yol)
    assert "Ayşe" in yol.read_text(encoding="utf-8")
    assert girdi_oku(yol) == ornek_girdi()


def test_eksik_listeler_bos_kabul_edilir():
    girdi = girdi_from_dict({"ayar": {"gun_sayisi": 5, "gunluk_ders_saati": 8}})
    assert girdi.atamalar == [] and girdi.kisitlar == []


def test_sonuc_gidis_donus():
    sonuc = CozumSonucu(
        durum=CozumDurumu.UYGUN,
        yerlesimler=[Yerlesim(ders_atama_id="a1", gun=0, saat=1)],
        toplam_ceza=7,
        mesajlar=["süre doldu"],
        sure_sn=1.5,
    )
    assert sonuc_from_dict(sonuc_to_dict(sonuc)) == sonuc
