"""Blok dersler: dağılım şekli (K4; docs/kisisellestirme-plani.md 4.1)."""

from collections import defaultdict

import pytest

from cozucu import (
    CozumDurumu,
    CpSatCozucu,
    DersAtama,
    Kapsam,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    TemelYerlesim,
    Yerlesim,
    dogrula,
    olc,
)
from cozucu.blok import BlokHesabi, desen_dogrula, desen_metni, otomatik_desen
from cozucu.celiski import celiskileri_bul
from cozucu.kalite import agirlikli_ceza
from cozucu.kisitlar import etkin_agirliklar
from cozucu.on_kontrol import on_kontrol
from yardimci import girdi_kur

from test_esnek_kisitlar import yalniz

BLOK = "blok_deseni"
BLOKSUZ = KisitTanimi(BLOK, {"otomatik": False})


def ozel(desen, ders="d", sinif=None, grup=None):
    return KisitTanimi(BLOK, {"desen": desen}, kapsam=Kapsam(ders_id=ders, sinif_id=sinif, sube_grubu_id=grup))


def gelemez(ogretmen, gun, saat):
    return Musaitlik(ogretmen, gun, saat, MusaitlikDurumu.GELEMEZ)


def coz(girdi, sure=10):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=sure)
    assert sonuc.durum is CozumDurumu.OPTIMAL, sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    return sonuc


def parcalar(sonuc, atama_id):
    """Atamanın günlere göre saatleri: {gün: [saatler]}."""
    gunler = defaultdict(list)
    for y in sonuc.yerlesimler:
        if y.ders_atama_id == atama_id:
            gunler[y.gun].append(y.saat)
    return {g: sorted(s) for g, s in gunler.items()}


def boylar(sonuc, atama_id):
    return sorted((len(s) for s in parcalar(sonuc, atama_id).values()), reverse=True)


# --- desen ------------------------------------------------------------------------------------


def test_otomatik_desen():
    assert [desen_metni(otomatik_desen(h)) for h in range(1, 8)] == [
        "1", "2", "2+1", "2+2", "2+2+1", "2+2+2", "2+2+2+1"]
    assert desen_metni(()) == "blok yok"


def test_desen_tek_gosterime_getirilir_ve_denetlenir():
    assert desen_dogrula([1, 2, 2]) == (2, 2, 1)
    for kotu in ("2+2", [0], [9], [2.0], [True], None):
        with pytest.raises(ValueError):
            desen_dogrula(kotu)


def test_desen_nereden_gelir():
    atamalar = [DersAtama("a", "s1", "d", "o1", 5), DersAtama("b", "s2", "d", "o1", 5),
                DersAtama("c", "s1", "e", "o2", 4), DersAtama("f", "s1", "f", "o3", 4)]
    # Okul: 4 saat → 2+1+1; d dersi bütün şubelerde 3+2 (N 3); s2'nin d dersi blok yok; f dersi blok yok.
    kisitlar = [KisitTanimi(BLOK, {"otomatik": True, "varsayilanlar": {"4": [2, 1, 1]}}),
                KisitTanimi("gunluk_ders_siniri", {"n": 3}),
                ozel([3, 2]), ozel([], sinif="s2"), ozel([], ders="f")]
    hesap = BlokHesabi(girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar, kisitlar=kisitlar))
    sonuc = {a.id: hesap.desen(a) for a in atamalar}
    assert (sonuc["a"].metin, sonuc["a"].ozel) == ("3+2", True)
    assert sonuc["b"] is None  # ders + şube özel ayarı ders ayarından özel
    assert (sonuc["c"].metin, sonuc["c"].ozel) == ("2+1+1", False)
    assert sonuc["f"] is None


def test_sube_grubuna_ozel_desen_ve_kapsam_onceligi():
    # Öncelik (kisisellestirme-plani 2.2): ders + şube (6) > ders + şube grubu (5) > ders (4) > okul.
    from cozucu import Sinif

    siniflar = [Sinif("s1", "11-A", 11, "say"), Sinif("s2", "11-B", 11, "say"), Sinif("s3", "11-C", 11, "soz")]
    atamalar = [DersAtama(f"a{i}", f"s{i}", "d", "o1", 5) for i in (1, 2, 3)]
    kisitlar = [ozel([3, 1, 1]), ozel([2, 1, 1, 1], grup="say"), ozel([], sinif="s2")]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), siniflar=siniflar, atamalar=atamalar,
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 3}), *kisitlar])
    hesap = BlokHesabi(girdi)
    assert hesap.desen(atamalar[0]).metin == "2+1+1+1"  # grubun şekli dersinkini ezer
    assert hesap.desen(atamalar[1]) is None  # şubenin şekli grubunkini ezer
    assert hesap.desen(atamalar[2]).metin == "3+1+1"  # başka grup: dersin şekli
    sonuc = coz(girdi)
    assert boylar(sonuc, "a1") == [2, 1, 1, 1] and boylar(sonuc, "a3") == [3, 1, 1]


def test_okul_bloklari_kapatabilir():
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 5)], kisitlar=[BLOKSUZ])
    assert BlokHesabi(girdi).desen(girdi.atamalar[0]) is None


def test_ozel_desen_ders_belirtmeli():
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 5)],
                      kisitlar=[KisitTanimi(BLOK, {"desen": [2, 2, 1]}, kapsam=Kapsam(sinif_id="s1"))])
    [sorun] = on_kontrol(girdi)
    assert sorun.tur == "gecersiz_kisit" and "ders belirtilmeli" in sorun.mesaj


# --- çözücü -------------------------------------------------------------------------------------


def test_otomatik_desen_uygulanir_her_blok_ayri_gunde_art_arda():
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 5),
                                                     DersAtama("b", "s1", "e", "o2", 6)])
    sonuc = coz(girdi)
    assert boylar(sonuc, "a") == [2, 2, 1]
    assert boylar(sonuc, "b") == [2, 2, 2]
    for saatler in parcalar(sonuc, "a").values():
        assert saatler == list(range(saatler[0], saatler[0] + len(saatler)))


def test_blok_ogle_arasini_kesmez_ve_kisa_gunu_asmaz():
    # Tek gün 5 saat, öğle arası 2. dersten sonra: 3'lük blok yalnızca 3.-5. saate sığar.
    ayar = OkulAyari(1, 5, ogle_arasi_sonra=2)
    girdi = girdi_kur(ayar=ayar, atamalar=[DersAtama("a", "s1", "d", "o1", 3)],
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 3}), ozel([3])])
    assert parcalar(coz(girdi), "a") == {0: [2, 3, 4]}
    # Cuma 2 saat: 3 saatlik blok cumaya sığmaz.
    ayar = OkulAyari(2, 4, gun_saatleri=(4, 2))
    girdi = girdi_kur(ayar=ayar, atamalar=[DersAtama("a", "s1", "d", "o1", 3)],
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 3}), ozel([3])])
    assert list(parcalar(coz(girdi), "a")) == [0]


def test_otomatik_oneri_uygulanamazsa_dusar():
    # Öğretmen yalnızca 2 gün gelebilir; 5 saat 2+2+1 üç gün ister: öneri düşer, program yine çıkar.
    gunler = [gelemez("o1", g, s) for g in (2, 3, 4) for s in range(6)]
    atama = DersAtama("a", "s1", "d", "o1", 5)
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[atama], musaitlikler=gunler,
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 3})])
    assert BlokHesabi(girdi).desen(atama) is None
    assert on_kontrol(girdi) == []
    coz(girdi)
    # Günlük sınır 1 iken 2'li blok olamaz: öneri düşer.
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 4)],
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 1})])
    assert BlokHesabi(girdi).desen(girdi.atamalar[0]) is None


def test_kalite_olcumu_blokla_model_cezasiyla_tutarli():
    ayar = OkulAyari(5, 6, gun_saatleri=(6, 6, 6, 6, 4), ogle_arasi_sonra=3)
    atamalar = [DersAtama(f"a{i}", f"s{i % 2}", f"d{i}", f"o{i % 3}", 3 + i % 3) for i in range(6)]
    girdi = girdi_kur(ayar=ayar, atamalar=atamalar)
    sonuc = coz(girdi, sure=20)
    assert agirlikli_ceza(olc(girdi, sonuc.yerlesimler), etkin_agirliklar(girdi)) == sonuc.toplam_ceza


# --- kilitli hücreler ve temel program --------------------------------------------------------


def test_kilitli_hucre_bir_blogun_parcasi_olur():
    # 4 saat 2+2; pazartesi 3. saat kilitli: bloğun öteki saati 2. ya da 4. saat olur.
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 4)],
                      kilitli_yerlesimler=[Yerlesim("a", 0, 2, kilitli=True)])
    sonuc = coz(girdi)
    assert parcalar(sonuc, "a")[0] in ([1, 2], [2, 3])
    assert boylar(sonuc, "a") == [2, 2]


def test_ayni_gun_iki_kilit_tek_bloga_sigmali():
    # 2+2 ama pazartesi 1. ve 4. saat kilitli: tek bloğa sığmaz.
    kilitler = [Yerlesim("a", 0, 0, kilitli=True), Yerlesim("a", 0, 3, kilitli=True)]
    atama = DersAtama("a", "s1", "d", "o1", 4)
    # Okul önerisi: düşer, kilitli hücreler yerinde, program çıkar.
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[atama], kilitli_yerlesimler=kilitler,
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 4})])
    assert BlokHesabi(girdi).desen(atama) is None
    coz(girdi)
    # Açıkça seçilmiş şekil: ön kontrol söyler.
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[atama], kilitli_yerlesimler=kilitler,
                      kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 4}), ozel([2, 2])])
    [sorun] = on_kontrol(girdi)
    assert sorun.tur == "blok_deseni"
    assert sorun.mesaj == ("s1 d'in kilitli hücreleri dağılım şekli 2+2 ile uyuşmuyor: aynı gündeki kilitli "
                           "saatler tek bir bloğa sığmalı ve her kilitli güne ayrı bir blok düşmeli.")


def test_kilit_ve_gelemez_birlikte_blogu_imkansiz_kilarsa_oneri_duser():
    # Kilit 4. saatte, öğretmen 3. ve 5. saatte gelemez: 2'li blok kilidin yanına konamaz.
    girdi = girdi_kur(ayar=OkulAyari(1, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 2)],
                      musaitlikler=[gelemez("o1", 0, 2), gelemez("o1", 0, 4)],
                      kilitli_yerlesimler=[Yerlesim("a", 0, 3, kilitli=True)])
    assert BlokHesabi(girdi).desen(girdi.atamalar[0]) is None
    coz(girdi)


def test_temel_program_blokla_en_az_degisiklik():
    # Temel program bloklara uygun. o1 artık pazartesi 1. saatte gelemiyor: a'nın pazartesi bloğu
    # kayar (1 değişiklik: 1.-2. saat yerine 2.-3. saat), geri kalan her şey yerinde kalır.
    atamalar = [DersAtama("a", "s1", "d", "o1", 4), DersAtama("b", "s2", "e", "o2", 3)]
    temel = [TemelYerlesim("s1", "d", 0, 0), TemelYerlesim("s1", "d", 0, 1),
             TemelYerlesim("s1", "d", 2, 3), TemelYerlesim("s1", "d", 2, 4),
             TemelYerlesim("s2", "e", 1, 0), TemelYerlesim("s2", "e", 1, 1), TemelYerlesim("s2", "e", 3, 0)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar, temel_yerlesimler=temel,
                      musaitlikler=[gelemez("o1", 0, 0)], kisitlar=yalniz("degisiklik"))
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).degisen_yerlesim == 1
    assert boylar(sonuc, "a") == [2, 2] and boylar(sonuc, "b") == [2, 1]
    assert parcalar(sonuc, "a")[0] == [1, 2]


def test_bloka_uymayan_temel_program_blok_kurali_kazanir():
    # Temel programda 1+1 bölünmüş ders; blok kuralı zorunlu: yeni program 2'li blok kurar.
    temel = [TemelYerlesim("s1", "d", 0, 0), TemelYerlesim("s1", "d", 1, 0)]
    girdi = girdi_kur(ayar=OkulAyari(2, 4), atamalar=[DersAtama("a", "s1", "d", "o1", 2)],
                      temel_yerlesimler=temel, kisitlar=yalniz("degisiklik"))
    sonuc = coz(girdi)
    assert boylar(sonuc, "a") == [2]
    assert olc(girdi, sonuc.yerlesimler).degisen_yerlesim == 1


# --- ön kontrol ---------------------------------------------------------------------------------


def _girdi(desen, saat=5, ayar=OkulAyari(5, 6), musaitlikler=(), n=None):
    kisitlar = [ozel(desen)] + ([KisitTanimi("gunluk_ders_siniri", {"n": n})] if n else [])
    return girdi_kur(ayar=ayar, atamalar=[DersAtama("a", "s1", "d", "o1", saat)], musaitlikler=list(musaitlikler),
                     kisitlar=kisitlar)


def _mesajlar(girdi):
    return [c.mesaj for c in on_kontrol(girdi) if c.tur == "blok_deseni"]


def test_on_kontrol_toplam():
    assert _mesajlar(_girdi([2, 2])) == [
        "s1 d haftada 5 saat, ama dağılım şekli 2+2 (4 saat). Şekli ya da haftalık saati düzeltin."]


def test_on_kontrol_gunluk_sinir():
    assert _mesajlar(_girdi([3, 2])) == [
        "s1 d 3 saatlik blok istiyor (dağılım şekli 3+2), ama bu ders bu şubeye günde en fazla 2 saat konabiliyor."]


def test_on_kontrol_gun_sayisi():
    assert _mesajlar(_girdi([1] * 5, ayar=OkulAyari(4, 6))) == [
        "s1 d 5 blok istiyor (dağılım şekli 1+1+1+1+1), ama haftada 4 gün var; her blok ayrı bir güne konur."]


def test_on_kontrol_ogle_arasi_yuzunden_sigmaz():
    ayar = OkulAyari(5, 6, ogle_arasi_sonra=3)  # her gün 3+3
    assert _mesajlar(_girdi([4, 1], ayar=ayar, n=4)) == [
        "s1 d 4 saatlik blok istiyor (dağılım şekli 4+1), ama hiçbir günde art arda 4 ders saati yok "
        "(öğle arası 3. dersten sonra günü bölüyor)."]


def test_on_kontrol_ogretmen_musaitligi():
    # o1 her gün 2. saatte gelemez (6 saatlik gün): art arda 2 saat yalnızca 3.-6. saatlerde; ama
    # salı-cuma bütün gün gelemez: 2'li blok için yalnızca pazartesi var, iki 2'li blok sığmaz.
    gelemezler = [gelemez("o1", g, 1) for g in range(5)] + [gelemez("o1", g, s) for g in (1, 2, 3, 4) for s in range(6)]
    assert _mesajlar(_girdi([2, 2], saat=4, musaitlikler=gelemezler)) == [
        "s1 d 2 blok istiyor (dağılım şekli 2+2) ve her blok ayrı bir güne konur, ama o1'un art arda 2 saat "
        "müsait olduğu 1 gün var."]


def test_on_kontrol_otomatik_oneriyi_denetlemez():
    # Aynı durum okul önerisiyle: sorun yok (öneri düşer).
    gelemezler = [gelemez("o1", g, s) for g in (1, 2, 3, 4) for s in range(6)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=[DersAtama("a", "s1", "d", "o1", 4)],
                      musaitlikler=gelemezler, kisitlar=[KisitTanimi("gunluk_ders_siniri", {"n": 4})])
    assert on_kontrol(girdi) == []


# --- çelişki analizi -------------------------------------------------------------------------------


def test_celiski_analizi_blogu_adiyla_soyler():
    # Tek gün, 4 saat, öğle arası 2. dersten sonra (2+2). İki ders, ikisi de 2'li blok; o1 2. saatte,
    # o2 1. saatte gelemez: iki blok da öğleden sonraya sığabiliyor ama ikisi birden sığmaz.
    # Ön kontrolden geçer (her ders tek başına sığıyor, saatler yetiyor).
    ayar = OkulAyari(1, 4, ogle_arasi_sonra=2)
    girdi = girdi_kur(ayar=ayar, atamalar=[DersAtama("a", "s1", "d", "o1", 2), DersAtama("b", "s1", "e", "o2", 2)],
                      musaitlikler=[gelemez("o1", 0, 1), gelemez("o2", 0, 0)],
                      kisitlar=[ozel([2]), ozel([2], ders="e")])
    assert on_kontrol(girdi) == []
    [celiski] = celiskileri_bul(girdi, 10)
    assert "s1 d'in 2 dağılımı (her blok ayrı bir günde, art arda)" in celiski.mesaj
    assert "s1 e'nin 2 dağılımı (her blok ayrı bir günde, art arda)" in celiski.mesaj
