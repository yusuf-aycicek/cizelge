"""Çelişki analizi: ön kontrolden geçen ama çözümsüz girdilerde en küçük çelişen kural kümesi.

Her senaryoda beklenen küme elle hesaplanmıştır ve en küçüktür: içindeki herhangi bir kuralı
kaldırmak çözümü mümkün kılar. Test hem fazladan hem de eksik madde olmadığını denetler.
"""

from cozucu import (
    CozumDurumu,
    CozumGirdisi,
    CpSatCozucu,
    Ders,
    DersAtama,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Ogretmen,
    Sinif,
    Yerlesim,
)
from cozucu.celiski import celiskileri_bul
from cozucu.on_kontrol import on_kontrol

OGRETMENLER = [
    Ogretmen("o-ayse", "Ayşe Yılmaz"),
    Ogretmen("o-zeynep", "Zeynep Demir"),
    Ogretmen("o-ali", "Ali Çelik"),
    Ogretmen("o-fatma", "Fatma Şahin"),
    Ogretmen("o-mehmet", "Mehmet Kaya"),
]
DERSLER = [
    Ders("d-mat", "Matematik"),
    Ders("d-fiz", "Fizik"),
    Ders("d-ing", "İngilizce"),
    Ders("d-tar", "Tarih"),
    Ders("d-tde", "Türk Dili ve Edebiyatı"),
]


def girdi(atamalar, musaitlikler=(), kilitler=(), ayar=OkulAyari(5, 6), siniflar=None):
    g = CozumGirdisi(
        ayar=ayar,
        ogretmenler=OGRETMENLER,
        siniflar=siniflar or [Sinif("s-9a", "9-A", 9)],
        dersler=DERSLER,
        atamalar=list(atamalar),
        musaitlikler=list(musaitlikler),
        kilitli_yerlesimler=list(kilitler),
    )
    assert on_kontrol(g) == [], "senaryo ön kontrolden geçmeli"
    return g


def yalnizca_musait(ogretmen, hucreler, ayar=OkulAyari(5, 6)):
    return [
        Musaitlik(ogretmen, gun, saat, MusaitlikDurumu.GELEMEZ)
        for gun in range(ayar.gun_sayisi)
        for saat in range(ayar.gunluk_ders_saati)
        if (gun, saat) not in hucreler
    ]


def maddeler(celiski):
    satirlar = celiski.mesaj.splitlines()
    assert satirlar[0].startswith("Şu kurallar birlikte sağlanamıyor")
    return {s.removeprefix("- ") for s in satirlar[1:]}


def test_kilit_ve_gelemez_zinciri():
    # Zeynep yalnızca pazartesi 1. saatte gelebiliyor; o saat matematiğe kilitli.
    g = girdi(
        atamalar=[
            DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 1),
            DersAtama("a-fiz", "s-9a", "d-fiz", "o-zeynep", 1),
        ],
        musaitlikler=yalnizca_musait("o-zeynep", {(0, 0)}),
        kilitler=[Yerlesim("a-mat", 0, 0, kilitli=True)],
    )
    [celiski] = celiskileri_bul(g, 10)
    assert maddeler(celiski) == {
        "Zeynep Demir'in gelemez saatleri",
        "9-A Matematik Pazartesi 1. saatte kilitli",
        "9-A Fizik haftada 1 saat (Zeynep Demir)",
    }
    assert set(celiski.ilgili) == {"o-zeynep", "a-mat", "a-fiz"}


def test_iki_ogretmen_ayni_dar_zamana_sikisiyor_ve_on_kontrol_yakalar():
    # Ayşe de Zeynep de yalnızca pzt-salı 1-3. saatlerde müsait (6'şar saat, ikisine de yeter);
    # ama ikisi de 9-A'ya 4'er saat girecek: 8 ders 6 saate sığmaz. Bunu artık sınıf müsaitliği
    # ön kontrolü yakalar; çelişki analizine gerek kalmaz.
    dar = {(g, s) for g in (0, 1) for s in (0, 1, 2)}
    g = CozumGirdisi(
        ayar=OkulAyari(5, 6), ogretmenler=OGRETMENLER, siniflar=[Sinif("s-9a", "9-A", 9)], dersler=DERSLER,
        atamalar=[
            DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 4),
            DersAtama("a-fiz", "s-9a", "d-fiz", "o-zeynep", 4),
        ],
        musaitlikler=yalnizca_musait("o-ayse", dar) + yalnizca_musait("o-zeynep", dar),
    )
    assert [c.tur for c in on_kontrol(g)] == ["sinif_musaitligi"]


def test_iki_sinif_arasindaki_cakisma():
    # Ayşe 9-A ve 9-B'ye birer saat girer. İki sınıfın 2. saati başka derslere kilitli; Ayşe'nin
    # iki dersi de 1. saate muhtaç. Her sınıfa tek tek bakan ön kontrol bunu göremez.
    g = girdi(
        ayar=OkulAyari(1, 2),
        siniflar=[Sinif("s-9a", "9-A", 9), Sinif("s-9b", "9-B", 9)],
        atamalar=[
            DersAtama("a-9a-mat", "s-9a", "d-mat", "o-ayse", 1),
            DersAtama("a-9b-mat", "s-9b", "d-mat", "o-ayse", 1),
            DersAtama("a-9a-fiz", "s-9a", "d-fiz", "o-zeynep", 1),
            DersAtama("a-9b-ing", "s-9b", "d-ing", "o-ali", 1),
        ],
        kilitler=[Yerlesim("a-9a-fiz", 0, 1), Yerlesim("a-9b-ing", 0, 1)],
    )
    [celiski] = celiskileri_bul(g, 10)
    assert maddeler(celiski) == {
        "9-A Fizik Pazartesi 2. saatte kilitli",
        "9-B İngilizce Pazartesi 2. saatte kilitli",
        "9-A Matematik haftada 1 saat (Ayşe Yılmaz)",
        "9-B Matematik haftada 1 saat (Ayşe Yılmaz)",
    }


def test_gunluk_sinir_ve_kilitler():
    # 2 gün x 4 saat. Pazartesi ilk üç saat başka derslere kilitli; matematik pazartesiye en
    # fazla 1 saat girebilir, salıya da günlük sınır yüzünden en fazla 2: 3 < 4.
    ayar = OkulAyari(2, 4)
    g = girdi(
        ayar=ayar,
        atamalar=[
            DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 4),
            DersAtama("a-ing", "s-9a", "d-ing", "o-ali", 1),
            DersAtama("a-tar", "s-9a", "d-tar", "o-fatma", 1),
            DersAtama("a-tde", "s-9a", "d-tde", "o-mehmet", 1),
        ],
        kilitler=[Yerlesim("a-ing", 0, 0), Yerlesim("a-tar", 0, 1), Yerlesim("a-tde", 0, 2)],
    )
    [celiski] = celiskileri_bul(g, 10)
    assert maddeler(celiski) == {
        "9-A İngilizce Pazartesi 1. saatte kilitli",
        "9-A Tarih Pazartesi 2. saatte kilitli",
        "9-A Türk Dili ve Edebiyatı Pazartesi 3. saatte kilitli",
        "9-A Matematik bir günde en fazla 2 saat olabilir",
        "9-A Matematik haftada 4 saat (Ayşe Yılmaz)",
    }


def test_cozucu_cozumsuzlukte_celiskiyi_doner():
    g = girdi(
        atamalar=[
            DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 1),
            DersAtama("a-fiz", "s-9a", "d-fiz", "o-zeynep", 1),
        ],
        musaitlikler=yalnizca_musait("o-zeynep", {(0, 0)}),
        kilitler=[Yerlesim("a-mat", 0, 0, kilitli=True)],
    )
    sonuc = CpSatCozucu().coz(g, sure_siniri_sn=10)
    assert sonuc.durum is CozumDurumu.COZUMSUZ
    assert [c.tur for c in sonuc.celiskiler] == ["celiski"]


def test_cozumu_olan_girdide_celiski_yok():
    g = girdi(atamalar=[DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 4)])
    assert celiskileri_bul(g, 5) == []


def test_mini_set_sayma_celiskisi_en_kucuk_kume_ve_hizli():
    # Mehmet yalnızca pzt-çar 1-5. saatlerde müsait: 15 saat = yükü, her saati dolu olmalı.
    # Salı 1. saatte üç sınıf da başka derslere kilitli: Mehmet'e 14 saat kalır.
    # Varsayım çekirdeği burada "9-A TDE günde en fazla 2" gibi gereksiz gruplar da içeriyordu;
    # küçültme (sabit literallerle) bunları atar ve süre bütçesinin çok altında biter.
    import time
    from dataclasses import replace
    from pathlib import Path

    from cozucu.veri_io import girdi_oku

    mini = girdi_oku(Path(__file__).resolve().parents[2] / "veri" / "mini.json")
    musait = {(g, s) for g in (0, 1, 2) for s in range(5)}
    g = replace(
        mini,
        musaitlikler=[m for m in mini.musaitlikler if m.ogretmen_id != "o-mehmet"]
        + yalnizca_musait("o-mehmet", musait),
        kilitli_yerlesimler=mini.kilitli_yerlesimler + [Yerlesim("a-9b-fiz", 1, 0), Yerlesim("a-10a-ing", 1, 0)],
    )
    assert on_kontrol(g) == []
    baslangic = time.perf_counter()
    [celiski] = celiskileri_bul(g, 30)
    assert time.perf_counter() - baslangic < 15
    assert maddeler(celiski) == {
        "Mehmet Kaya'nın gelemez saatleri",
        "9-A Matematik Salı 1. saatte kilitli",
        "9-B Fizik Salı 1. saatte kilitli",
        "10-A İngilizce Salı 1. saatte kilitli",
        "9-A Türk Dili ve Edebiyatı haftada 5 saat (Mehmet Kaya)",
        "9-B Türk Dili ve Edebiyatı haftada 5 saat (Mehmet Kaya)",
        "10-A Türk Dili ve Edebiyatı haftada 5 saat (Mehmet Kaya)",
    }


# --- ana çözüm "bilinmiyor" dönerse: yalnızca zorunlu kısıtlarla ikinci kontrol ------------

from ortools.sat.python import cp_model  # noqa: E402


class _SuresiYetmeyen(CpSatCozucu):
    """Ana çözümün süre içinde hiçbir şey bulamadığı durumu taklit eder."""

    def __init__(self, ikinci=None):
        super().__init__()
        self._ikinci = ikinci

    def _ana_cozum(self, baglam, sure, baslangic):
        return cp_model.UNKNOWN, None

    def _uygunluk_kontrolu(self, girdi, sure):
        return self._ikinci if self._ikinci is not None else super()._uygunluk_kontrolu(girdi, sure)


def _iki_sinif_cakismasi():
    return girdi(
        ayar=OkulAyari(1, 2),
        siniflar=[Sinif("s-9a", "9-A", 9), Sinif("s-9b", "9-B", 9)],
        atamalar=[
            DersAtama("a-9a-mat", "s-9a", "d-mat", "o-ayse", 1),
            DersAtama("a-9b-mat", "s-9b", "d-mat", "o-ayse", 1),
            DersAtama("a-9a-fiz", "s-9a", "d-fiz", "o-zeynep", 1),
            DersAtama("a-9b-ing", "s-9b", "d-ing", "o-ali", 1),
        ],
        kilitler=[Yerlesim("a-9a-fiz", 0, 1), Yerlesim("a-9b-ing", 0, 1)],
    )


def test_bilinmiyor_ama_cozumsuz_ise_celiski_aciklanir():
    sonuc = _SuresiYetmeyen().coz(_iki_sinif_cakismasi(), sure_siniri_sn=5)
    assert sonuc.durum is CozumDurumu.COZUMSUZ
    assert [c.tur for c in sonuc.celiskiler] == ["celiski"]


def test_bilinmiyor_ama_cozum_varsa_daha_uzun_sure_onerilir():
    g = girdi(atamalar=[DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 4)])
    sonuc = _SuresiYetmeyen().coz(g, sure_siniri_sn=5)
    assert sonuc.durum is CozumDurumu.BILINMIYOR and sonuc.celiskiler == []
    assert "Kurallara uyan bir program var" in sonuc.mesajlar[0]


def test_ikinci_kontrol_de_sonuc_vermezse_durum_acikca_soylenir():
    g = girdi(atamalar=[DersAtama("a-mat", "s-9a", "d-mat", "o-ayse", 4)])
    sonuc = _SuresiYetmeyen(ikinci=cp_model.UNKNOWN).coz(g, sure_siniri_sn=5)
    assert sonuc.durum is CozumDurumu.BILINMIYOR
    assert "ne program bulunabildi ne de programın olmadığı kanıtlanabildi" in sonuc.mesajlar[0]
