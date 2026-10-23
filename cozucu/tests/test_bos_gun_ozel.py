"""Öğretmene özel boş gün hedefi ve iki yönlü ceza (K2; docs/kisisellestirme-plani.md 4.2)."""

from cozucu import (
    CozumDurumu,
    CpSatCozucu,
    DersAtama,
    Kapsam,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Yerlesim,
    dogrula,
    olc,
)
from cozucu.kalite import agirlikli_ceza, ders_gunleri
from cozucu.kisitlar import KAYIT_DEFTERI, etkin_agirliklar
from cozucu.yuk import bos_gun_hedefi
from yardimci import girdi_kur

from test_esnek_kisitlar import yalniz

BOS = "bos_gun"


def tek_saatler(ogretmen="o1", adet=5):
    """`adet` ayrı şubede birer saat: öğretmen istediği kadar güne yayılabilir."""
    return [DersAtama(f"{ogretmen}-{i}", f"s-{ogretmen}-{i}", f"d{i}", ogretmen, 1) for i in range(adet)]


def ozel_hedef(deger, ogretmen="o1"):
    return KisitTanimi(BOS, {"hedef_bos_gun": deger}, zorunlu=False, kapsam=Kapsam(ogretmen_id=ogretmen))


def coz(girdi):
    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=10)
    assert sonuc.durum is CozumDurumu.OPTIMAL, sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    # Kalite ölçümü, modelin cezasıyla birebir tutarlı (iki yön de sayılıyor).
    assert agirlikli_ceza(olc(girdi, sonuc.yerlesimler), etkin_agirliklar(girdi)) == sonuc.toplam_ceza
    return sonuc


def test_bos_gun_ogretmene_ozel_ayarlanabilir():
    assert KAYIT_DEFTERI[BOS].kapsamlar == {"ogretmen"}


def test_ozel_hedef_iki_bos_gun():
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(), kisitlar=yalniz(BOS) + [ozel_hedef(2)])
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] <= 3
    assert sonuc.toplam_ceza == 0


def test_ozel_hedef_sifir_ogretmeni_her_gune_yayar():
    # "Boş günüm olmasın": 5 saatlik öğretmen 5 güne yayılır (eksik gün cezası).
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(), kisitlar=yalniz(BOS) + [ozel_hedef(0)])
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] == 5
    assert sonuc.toplam_ceza == 0


def test_okul_geneli_hedefte_eksik_gun_cezasi_yok():
    # Okul hedefi 1 boş gün; bütün dersler tek güne kilitli (4 boş gün). Okul genelinde yalnızca
    # fazla gelmek cezalıdır: ceza 0.
    kilitler = [Yerlesim(f"o1-{i}", 0, i, kilitli=True) for i in range(5)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(), kilitli_yerlesimler=kilitler, kisitlar=yalniz(BOS))
    sonuc = coz(girdi)
    assert sonuc.toplam_ceza == 0
    assert olc(girdi, sonuc.yerlesimler).fazla_bos_gun == 0


def test_ozel_hedefte_eksik_gun_kacinilamazsa_ceza():
    # Aynı kilitler, ama öğretmene özel hedef 0: hedef 5 gün, 1 gün geliyor; 4 gün eksik × ağırlık 4.
    kilitler = [Yerlesim(f"o1-{i}", 0, i, kilitli=True) for i in range(5)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(), kilitli_yerlesimler=kilitler,
                      kisitlar=yalniz(BOS) + [ozel_hedef(0)])
    sonuc = coz(girdi)
    assert olc(girdi, sonuc.yerlesimler).fazla_bos_gun == 4
    assert sonuc.toplam_ceza == 4 * 4


def test_yuk_yetmezse_eksik_gun_cezasi_yok():
    # 3 saat dersi olan öğretmen "boş günüm olmasın" dese de 5 gün gelemez: hedef 3 gün.
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(adet=3), kisitlar=yalniz(BOS) + [ozel_hedef(0)])
    assert bos_gun_hedefi(girdi, "o1", 3).gun == 3
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] == 3
    assert sonuc.toplam_ceza == 0


def test_ozel_hedef_yalnizca_o_ogretmene_uygulanir():
    # o1'e 0 (her gün), o2'ye 2 (en fazla 3 gün); o3 okul geneli (en fazla 4 gün).
    atamalar = tek_saatler("o1") + tek_saatler("o2") + tek_saatler("o3")
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=atamalar,
                      kisitlar=yalniz(BOS) + [ozel_hedef(0, "o1"), ozel_hedef(2, "o2")])
    sonuc = coz(girdi)
    gunler = ders_gunleri(girdi, sonuc.yerlesimler)
    assert gunler["o1"] == 5 and gunler["o2"] <= 3 and gunler["o3"] <= 4
    assert sonuc.toplam_ceza == 0
    assert [bos_gun_hedefi(girdi, o, 5).iki_yonlu for o in ("o1", "o2", "o3")] == [True, True, False]


def test_ozel_hedef_okul_kurali_kapaliysa_uygulanmaz():
    # Okul boş gün kuralını kapattıysa (ağırlık 0) özel hedef de etkisiz: kip ve ağırlık okuldan.
    tanimlar = yalniz(BOS, agirlik=0) + [ozel_hedef(0)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(), kisitlar=tanimlar)
    assert coz(girdi).toplam_ceza == 0


def test_butun_gun_gelemezse_o_gun_hedeften_duser():
    # "Boş günüm olmasın" ama pazartesi bütün gün gelemez: en fazla 4 gün gelebilir, hedef 4 gün.
    # (Örnek okulda yapılan denemede bulundu: hedef 5 gün kalıyor, kaçınılmaz ceza yazılıyordu.)
    pazartesi = [Musaitlik("o1", 0, s, MusaitlikDurumu.GELEMEZ) for s in range(6)]
    girdi = girdi_kur(ayar=OkulAyari(5, 6), atamalar=tek_saatler(), musaitlikler=pazartesi,
                      kisitlar=yalniz(BOS) + [ozel_hedef(0)])
    assert bos_gun_hedefi(girdi, "o1", 5).gun == 4
    sonuc = coz(girdi)
    assert ders_gunleri(girdi, sonuc.yerlesimler)["o1"] == 4
    assert sonuc.toplam_ceza == 0
    # Günün bir saati gelemezse gün hâlâ gelinebilir: hedef 5.
    girdi.musaitlikler.pop()
    assert bos_gun_hedefi(girdi, "o1", 5).gun == 5
