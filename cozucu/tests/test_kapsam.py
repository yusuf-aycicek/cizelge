"""Kural kapsamı (ADR 0016): çözümleme, kayıt denetimi ve N ile M'nin özel ayarları."""

from typing import ClassVar

import pytest

from cozucu import (
    OKUL,
    CozumDurumu,
    CpSatCozucu,
    DersAtama,
    Kapsam,
    KisitTanimi,
    OkulAyari,
    Sinif,
    Yerlesim,
    dogrula,
)
from cozucu.kapsam import Varlik, cozumle, ortusur
from cozucu.kisitlar import KAYIT_DEFTERI, GirdiHatasi, KisitKurali, kural_olustur, kurallari_hazirla
from cozucu.kisitlar.temel import kaydet
from cozucu.on_kontrol import on_kontrol
from cozucu.veri_io import girdi_from_dict, girdi_to_dict
from cozucu.yuk import YukHesabi
from yardimci import girdi_kur

N = "gunluk_ders_siniri"
M = "ogretmen_gunluk_siniri"


def atama(id, sinif="s1", ders=None, ogretmen="o1", saat=1):
    return DersAtama(id=id, sinif_id=sinif, ders_id=ders or id, ogretmen_id=ogretmen, haftalik_saat=saat)


def ozel(tur, deger, **kapsam):
    ad = "n" if tur == N else "m"
    return KisitTanimi(tur, {ad: deger}, kapsam=Kapsam(**kapsam))


def coz(girdi):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=10)
    if sonuc.basarili:
        assert dogrula(girdi, sonuc.yerlesimler) == []
    return sonuc


# --- cozumle (saf) -----------------------------------------------------------------------

# 11-A şubesinin (grubu "say") Matematik dersi.
VARLIK = Varlik(ders_id="mat", sinif_id="11a", sube_grubu_id="say")


@pytest.mark.parametrize(
    ("kapsamlar", "kazanan"),
    [
        ([OKUL, Kapsam(sube_grubu_id="say")], Kapsam(sube_grubu_id="say")),
        ([Kapsam(sube_grubu_id="say"), Kapsam(sinif_id="11a")], Kapsam(sinif_id="11a")),
        # Ders şubeden önce gelir (4 > 2).
        ([Kapsam(sinif_id="11a"), Kapsam(ders_id="mat")], Kapsam(ders_id="mat")),
        ([Kapsam(ders_id="mat"), Kapsam(ders_id="mat", sube_grubu_id="say")], Kapsam(ders_id="mat", sube_grubu_id="say")),
        (
            [Kapsam(ders_id="mat", sube_grubu_id="say"), Kapsam(ders_id="mat", sinif_id="11a")],
            Kapsam(ders_id="mat", sinif_id="11a"),
        ),
        # Bütün aile birden: sıra fark etmez, en özel kazanır.
        (
            [
                Kapsam(ders_id="mat", sinif_id="11a"),
                OKUL,
                Kapsam(ders_id="mat"),
                Kapsam(sinif_id="11a"),
                Kapsam(sube_grubu_id="say"),
                Kapsam(ders_id="mat", sube_grubu_id="say"),
            ],
            Kapsam(ders_id="mat", sinif_id="11a"),
        ),
    ],
)
def test_en_ozel_kapsam_kazanir(kapsamlar, kazanan):
    assert cozumle(kapsamlar, VARLIK, kapsam=lambda k: k) == kazanan
    assert cozumle(list(reversed(kapsamlar)), VARLIK, kapsam=lambda k: k) == kazanan


def test_puanlar():
    assert [Kapsam(**k).puan for k in (
        {}, {"sube_grubu_id": "g"}, {"ogretmen_id": "o"}, {"sinif_id": "s"}, {"ders_id": "d"},
        {"ders_id": "d", "sube_grubu_id": "g"}, {"ders_id": "d", "sinif_id": "s"},
    )] == [0, 1, 1, 2, 4, 5, 6]


def test_uymayan_tanim_secilmez_hic_uyan_yoksa_none():
    baska = [Kapsam(ders_id="fiz"), Kapsam(sinif_id="11b"), Kapsam(sube_grubu_id="soz"), Kapsam(ders_id="mat", sinif_id="11b")]
    assert cozumle(baska, VARLIK, kapsam=lambda k: k) is None
    # Varlığın bilinmeyen ekseni (öğretmen) dolu bir kapsamla eşleşmez.
    assert cozumle([Kapsam(ogretmen_id="o1")], VARLIK, kapsam=lambda k: k) is None


def test_ayni_ozgullukte_iki_uyan_tanim_tutarsizdir():
    with pytest.raises(ValueError):
        cozumle([Kapsam(ders_id="mat"), Kapsam(ders_id="mat")], VARLIK, kapsam=lambda k: k)


def test_ogretmen_kapsami_ders_ya_da_sube_ile_birlesemez():
    for eksen in ({"ders_id": "mat"}, {"sinif_id": "9a"}, {"sube_grubu_id": "say"}):
        with pytest.raises(ValueError, match="Öğretmen kapsamı"):
            Kapsam(ogretmen_id="o1", **eksen)
    with pytest.raises(ValueError, match="şube grubu"):
        Kapsam(sinif_id="9a", sube_grubu_id="say")


# --- kayıt ve kural oluşturma ------------------------------------------------------------


def test_kaydet_ogretmen_ve_ders_eksenini_birlikte_bildiren_kurali_reddeder():
    class Karisik(KisitKurali):
        tur: ClassVar[str] = "karisik_deneme"
        kapsamlar = frozenset({"ogretmen", "ders"})

        def uygula(self, baglam):
            return []

    with pytest.raises(ValueError, match="birlikte bildiremez"):
        kaydet(Karisik)
    assert "karisik_deneme" not in KAYIT_DEFTERI


def test_kayitli_hicbir_kural_iki_aileyi_karistirmaz():
    for sinif in KAYIT_DEFTERI.values():
        assert not ({"ogretmen"} <= sinif.kapsamlar and sinif.kapsamlar - {"ogretmen"}), sinif.tur


def test_n_ve_m_kapsamlari():
    assert KAYIT_DEFTERI[N].kapsamlar == {"ders", "sube", "sube_grubu"}
    assert KAYIT_DEFTERI[M].kapsamlar == {"ogretmen"}
    assert KAYIT_DEFTERI["sinif_boslugu"].kapsamlar == frozenset()


@pytest.mark.parametrize(
    ("okul", "ozel_tanim", "mesaj"),
    [
        (KisitTanimi("sinif_boslugu", zorunlu=False, agirlik=30),
         KisitTanimi("sinif_boslugu", kapsam=Kapsam(ogretmen_id="o1")), "'sinif_boslugu' öğretmene özel ayarlanamaz"),
        (KisitTanimi(N, {"n": 2}), KisitTanimi(N, {"n": 3}, kapsam=Kapsam(ogretmen_id="o1")), "öğretmene özel ayarlanamaz"),
        (KisitTanimi(M, {"m": 8}), ozel(M, 6, ders_id="mat"), "derse özel ayarlanamaz"),
        (KisitTanimi(M, {"m": 8}), ozel(M, 0, ogretmen_id="o1"), "geçersiz parametreler"),
        (KisitTanimi(M, {"m": 8}), KisitTanimi(M, {"m": 6}), "ikinci bir okul geneli"),
    ],
)
def test_kural_olustur_gecersiz_ozel_ayari_reddeder(okul, ozel_tanim, mesaj):
    with pytest.raises(GirdiHatasi, match=mesaj):
        kural_olustur(okul, [ozel_tanim])


def test_kural_olustur_ayni_kapsamda_iki_ozel_ayari_reddeder():
    with pytest.raises(GirdiHatasi, match="aynı kapsamda"):
        kural_olustur(KisitTanimi(M, {"m": 8}), [ozel(M, 6, ogretmen_id="o1"), ozel(M, 5, ogretmen_id="o1")])


def test_kural_olustur_kapsamli_tanimi_okul_tanimi_yerine_kabul_etmez():
    with pytest.raises(GirdiHatasi, match="okul geneli tanım bekleniyordu"):
        kural_olustur(ozel(M, 6, ogretmen_id="o1"))


def test_ozel_ayarin_kipi_okul_tanimindan_gelir():
    # Özel ayar zorunlu=True varsayılanıyla gelse de okul tanımı esnekse esnek çalışır.
    kural = kural_olustur(KisitTanimi(N, {"n": 2}, zorunlu=False, agirlik=7), [ozel(N, 3, ders_id="mat")])
    (_, ornek), = kural.ozel
    assert (ornek.zorunlu, ornek.agirlik, ornek.n) == (False, 7, 3)


def test_kurallari_hazirla_her_tur_icin_tek_ornek_kurar():
    girdi = girdi_kur(
        ayar=OkulAyari(2, 4),
        atamalar=[atama("mat")],
        kisitlar=[KisitTanimi(N, {"n": 2}), ozel(N, 3, ders_id="mat"), ozel(N, 1, sinif_id="s1")],
    )
    kurallar = [k for k in kurallari_hazirla(girdi) if k.tur == N]
    assert len(kurallar) == 1
    assert kurallar[0].n == 2 and len(kurallar[0].ozel) == 2


def test_okul_tanimi_olmayan_ozel_ayar_varsayilanin_uzerine_kurulur():
    # Okul N tanımlamadıysa varsayılan (2) okul değeridir; özel ayar yine çalışır.
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[atama("mat", saat=3)], kisitlar=[ozel(N, 3, ders_id="mat")])
    assert coz(girdi).basarili


# --- N: derse, şubeye, şube grubuna özel ------------------------------------------------


def _iki_sube(*kisitlar, gruplar=("say", None)):
    """İki şube, ikisinde de 1 günde 3 saatlik Matematik; okul N = 2."""
    return girdi_kur(
        ayar=OkulAyari(1, 4),
        siniflar=[Sinif("s1", "11-A", 11, sube_grubu_id=gruplar[0]), Sinif("s2", "11-B", 11, sube_grubu_id=gruplar[1])],
        atamalar=[atama("a1", sinif="s1", ders="mat", ogretmen="o1", saat=3),
                  atama("a2", sinif="s2", ders="mat", ogretmen="o2", saat=3)],
        kisitlar=[KisitTanimi(N, {"n": 2}), *kisitlar],
    )


def _kapasite_hatali_subeler(girdi):
    return {c.ilgili[0] for c in on_kontrol(girdi) if c.tur == "ders_gun_kapasitesi"}


def test_okul_n_iki_iken_iki_sube_de_sigmaz():
    assert _kapasite_hatali_subeler(_iki_sube()) == {"s1", "s2"}


def test_derse_ozel_n_butun_subelere_uygulanir():
    girdi = _iki_sube(ozel(N, 3, ders_id="mat"))
    assert _kapasite_hatali_subeler(girdi) == set()
    sonuc = coz(girdi)
    assert sonuc.basarili and len(sonuc.yerlesimler) == 6


def test_subeye_ozel_n_yalnizca_o_subeye_uygulanir():
    girdi = _iki_sube(ozel(N, 3, sinif_id="s1"))
    assert _kapasite_hatali_subeler(girdi) == {"s2"}
    mesaj = next(c.mesaj for c in on_kontrol(girdi) if c.tur == "ders_gun_kapasitesi")
    assert "bir ders bir sınıfa günde en fazla 2 saat" in mesaj


def test_sube_grubuna_ozel_n_grubun_subelerine_uygulanir():
    assert _kapasite_hatali_subeler(_iki_sube(ozel(N, 3, sube_grubu_id="say"))) == {"s2"}


def test_daha_ozel_kapsam_daha_genel_olani_ezer():
    # Matematik 3 (ders, puan 4) ama 11-A'da Matematik 2 (ders + şube, puan 6): 11-A sığmaz.
    girdi = _iki_sube(ozel(N, 3, ders_id="mat"), ozel(N, 2, ders_id="mat", sinif_id="s1"))
    assert _kapasite_hatali_subeler(girdi) == {"s1"}
    mesaj = next(c.mesaj for c in on_kontrol(girdi) if c.tur == "ders_gun_kapasitesi")
    assert "en fazla 2 saat konabildiği" in mesaj


def test_ozel_n_on_kontrol_mesajinda_ozel_ayar_olarak_anilir():
    girdi = _iki_sube(ozel(N, 1, sinif_id="s1"))
    mesaj = next(c.mesaj for c in on_kontrol(girdi) if c.ilgili[0] == "s1")
    assert "bu ders bu şubeye günde en fazla 1 saat konabildiği (özel ayar)" in mesaj


def test_ozel_n_cozucude_uygulanir_on_kontrolden_bagimsiz():
    # Okul N = 3, 11-A'ya özel 1: 2 saatlik ders iki güne birer saat dağılmak zorunda.
    girdi = girdi_kur(
        ayar=OkulAyari(2, 4),
        atamalar=[atama("a1", sinif="s1", ders="mat", saat=2)],
        kisitlar=[KisitTanimi(N, {"n": 3}), ozel(N, 1, sinif_id="s1")],
    )
    sonuc = coz(girdi)
    assert sonuc.basarili
    assert sorted(y.gun for y in sonuc.yerlesimler) == [0, 1]


def test_dogrulama_ozel_n_ihlalini_yakalar():
    girdi = girdi_kur(
        ayar=OkulAyari(2, 4),
        atamalar=[atama("a1", sinif="s1", ders="mat", saat=2)],
        kisitlar=[KisitTanimi(N, {"n": 3}), ozel(N, 1, ders_id="mat")],
    )
    ayni_gun = [Yerlesim("a1", 0, 0), Yerlesim("a1", 0, 1)]
    assert any("Günlük sınır aşıldı" in h for h in dogrula(girdi, ayni_gun))
    girdi.kisitlar.pop()  # özel ayar olmadan aynı yerleşim geçerli
    assert dogrula(girdi, ayni_gun) == []


# --- M: öğretmene özel --------------------------------------------------------------------


def _iki_ogretmen(*kisitlar):
    """İki öğretmen, ikisinin de 2 günde 6 saati var; okul M = 8."""
    return girdi_kur(
        ayar=OkulAyari(2, 4),
        atamalar=[atama(f"{o}-{s}", sinif=s, ogretmen=o, saat=3) for o in ("o1", "o2") for s in (f"s{o}1", f"s{o}2")],
        kisitlar=[KisitTanimi(N, {"n": 4}), KisitTanimi(M, {"m": 8}), *kisitlar],
    )


def test_ogretmene_ozel_m_yalnizca_o_ogretmene_uygulanir():
    girdi = _iki_ogretmen(ozel(M, 2, ogretmen_id="o1"))
    sorunlar = [c for c in on_kontrol(girdi) if c.tur == "ogretmen_kapasitesi"]
    assert [c.ilgili[0] for c in sorunlar] == ["o1"]
    assert "günde en fazla 2 saat derse girebildiği için yalnızca 4 saati" in sorunlar[0].mesaj
    hesap = YukHesabi(girdi)
    assert (hesap.ogretmen_siniri("o1"), hesap.ogretmen_siniri("o2"), hesap.m) == (2, 4, 4)


def test_ogretmene_ozel_m_cozucude_uygulanir():
    girdi = _iki_ogretmen(ozel(M, 3, ogretmen_id="o1"))
    sonuc = coz(girdi)
    assert sonuc.basarili
    atama_ogretmen = {a.id: a.ogretmen_id for a in girdi.atamalar}
    o1_gunluk = [sum(1 for y in sonuc.yerlesimler if atama_ogretmen[y.ders_atama_id] == "o1" and y.gun == g) for g in (0, 1)]
    assert o1_gunluk == [3, 3]


def test_dogrulama_ozel_m_ihlalini_yakalar():
    girdi = girdi_kur(ayar=OkulAyari(1, 4), atamalar=[atama("a", saat=3)],
                      kisitlar=[KisitTanimi(N, {"n": 4}), ozel(M, 2, ogretmen_id="o1")])
    yerlesim = [Yerlesim("a", 0, s) for s in range(3)]
    assert any("Öğretmen günlük sınırı aşıldı" in h for h in dogrula(girdi, yerlesim))


def test_celiski_aciklamasi_ozel_m_degerini_soyler():
    from cozucu.celiski import _anlat

    girdi = girdi_kur(
        ayar=OkulAyari(1, 4),
        atamalar=[atama("a", sinif="s1", ders="mat", saat=2), atama("b", sinif="s1", ders="fiz", ogretmen="o2")],
        kisitlar=[ozel(M, 2, ogretmen_id="o1"), ozel(N, 3, ders_id="mat")],
    )
    mesaj = _anlat(girdi, [("ogretmen_gunluk", "o1"), ("ogretmen_gunluk", "o2"), ("gunluk_ders", "s1", "mat"), ("gunluk_ders", "s1", "fiz")]).mesaj
    assert "o1 günde en fazla 2 saat derse girebilir" in mesaj
    assert "o2 günde en fazla 8 saat derse girebilir" in mesaj
    assert "s1 mat bir günde en fazla 3 saat" in mesaj
    assert "s1 fiz bir günde en fazla 2 saat" in mesaj


def test_on_kontrol_gecersiz_ozel_ayari_madde_madde_soyler():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 4),
        atamalar=[atama("a")],
        kisitlar=[ozel(M, 6, ders_id="a"),
                  KisitTanimi("sinif_boslugu", kapsam=Kapsam(ogretmen_id="o1"))],
    )
    mesajlar = [c.mesaj for c in on_kontrol(girdi) if c.tur == "gecersiz_kisit"]
    assert mesajlar == ["'ogretmen_gunluk_siniri' derse özel ayarlanamaz", "'sinif_boslugu' öğretmene özel ayarlanamaz"]


def test_bos_gun_hedefi_ozel_m_ile_hesaplanir():
    # o1'in 6 saati var, 3 gün, günde 4 saat. Okul M ile hedef gün max(⌈6/4⌉, 3-1) = 2: boş gün
    # mümkün. o1'e özel M = 2 ile ⌈6/2⌉ = 3 gün gerekir: boş gün hedefi düşer, ceza yazılmaz.
    from cozucu.kalite import olc

    girdi = girdi_kur(
        ayar=OkulAyari(3, 4),
        atamalar=[atama("a", sinif="s1", saat=3), atama("b", sinif="s2", saat=3)],
        # Sınıf boşluğu kapalı: iki şubeden biri her gün 2. saatte başlamak zorunda, ceza toplamı
        # yalnızca boş gün kuralını ölçsün.
        kisitlar=[KisitTanimi(N, {"n": 1}), ozel(M, 2, ogretmen_id="o1"), KisitTanimi("sinif_boslugu", zorunlu=False, agirlik=0)],
    )
    sonuc = coz(girdi)
    assert sonuc.basarili
    assert olc(girdi, sonuc.yerlesimler).eksik_bos_gun == 0
    # Çözücüdeki boş gün kuralı da aynı hedefi kullanır: kaçınılmaz üçüncü gün cezalanmaz.
    # (o1 her gün 0. ve 1. saatte: pencere yok; toplam ceza 0.)
    assert sonuc.toplam_ceza == 0


# --- serileştirme -------------------------------------------------------------------------


def test_kapsam_json_gidis_donus():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 4),
        siniflar=[Sinif("s1", "9-A", 9, sube_grubu_id="g1")],
        atamalar=[atama("a")],
        kisitlar=[ozel(M, 6, ogretmen_id="o1"), ozel(N, 1, ders_id="a", sube_grubu_id="g1"), KisitTanimi(N, {"n": 2})],
    )
    geri = girdi_from_dict(girdi_to_dict(girdi))
    assert geri.kisitlar == girdi.kisitlar
    assert [k.kapsam for k in geri.kisitlar] == [Kapsam(ogretmen_id="o1"), Kapsam(ders_id="a", sube_grubu_id="g1"), OKUL]
    assert geri.siniflar[0].sube_grubu_id == "g1"


def test_kapsami_olmayan_eski_veri_okul_geneli_okunur():
    veri = {"ayar": {"gun_sayisi": 1, "gunluk_ders_saati": 4}, "kisitlar": [{"tur": N, "parametreler": {"n": 1}}]}
    assert girdi_from_dict(veri).kisitlar[0].kapsam == OKUL


def test_parametre_varlik_icin_cozumlenir():
    girdi = girdi_kur(
        ayar=OkulAyari(1, 4),
        siniflar=[Sinif("s1", "11-A", 11, sube_grubu_id="say")],
        kisitlar=[KisitTanimi(N, {"n": 2}), ozel(N, 3, sube_grubu_id="say"), ozel(N, 1, ders_id="mat", sinif_id="s1")],
    )
    assert girdi.parametre(N, "n", 2) == 2
    assert girdi.parametre(N, "n", 2, sinif_id="s1", ders_id="fiz") == 3
    assert girdi.parametre(N, "n", 2, sinif_id="s1", ders_id="mat") == 1
    assert girdi.parametre(N, "n", 2, sinif_id="s9", ders_id="mat") == 2


def test_ortusme_eksen_eksen_ve_grup_uyeligiyle():
    grubu = {"s1": "say", "s2": None}.get
    mat, fiz = Kapsam(ders_id="mat"), Kapsam(ders_id="fiz")
    assert ortusur(mat, Kapsam(ders_id="mat", sinif_id="s1"), grubu)
    assert not ortusur(fiz, Kapsam(ders_id="mat", sinif_id="s1"), grubu)
    assert ortusur(Kapsam(sinif_id="s1"), Kapsam(sube_grubu_id="say"), grubu)
    assert ortusur(Kapsam(sube_grubu_id="say"), Kapsam(ders_id="mat", sinif_id="s1"), grubu)
    assert not ortusur(Kapsam(sinif_id="s2"), Kapsam(sube_grubu_id="say"), grubu)
    assert not ortusur(Kapsam(sube_grubu_id="say", ders_id="mat"), Kapsam(sinif_id="s2"), grubu)
    assert not ortusur(Kapsam(sinif_id="s1"), Kapsam(sinif_id="s2"), grubu)
    assert not ortusur(Kapsam(sube_grubu_id="say"), Kapsam(sube_grubu_id="soz"), grubu)
    assert ortusur(Kapsam(sinif_id="s1"), mat, grubu)
    assert ortusur(Kapsam(ogretmen_id="o1"), Kapsam(ogretmen_id="o1"), grubu)
    assert not ortusur(Kapsam(ogretmen_id="o1"), Kapsam(ogretmen_id="o2"), grubu)
