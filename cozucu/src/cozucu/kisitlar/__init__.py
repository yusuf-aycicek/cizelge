"""Kısıt kuralları. Alt modüllerin içe aktarılması kayıt defterini doldurur."""

from collections import defaultdict

from cozucu.blok import BLOK_DESENI_TURU
from cozucu.kisitlar import esnek, zorunlu  # noqa: F401  (kayıt için)
from cozucu.kisitlar.temel import KAYIT_DEFTERI, Baglam, GirdiHatasi, KisitKurali, kural_olustur
from cozucu.kisitlar.zorunlu import TEMEL_KURALLAR
from cozucu.model import (
    BOS_GUN_TURU,
    GUNLUK_DERS_SINIRI_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    VARSAYILAN_HEDEF_BOS_GUN,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    CozumGirdisi,
    KisitTanimi,
)

# Okul hiçbir şey tanımlamazsa uygulanan okul geneli kurallar. Ağırlıklar plan kararı 3 ve 7.
# Öncelik: sınıf boşluğu (30) > değişiklik (8) > tercih etmez (5) > boş gün (4) > pencere (3)
# > bölünmüş ders (2).
VARSAYILAN_KISITLAR: tuple[KisitTanimi, ...] = (
    KisitTanimi(GUNLUK_DERS_SINIRI_TURU, {"n": VARSAYILAN_GUNLUK_DERS_SINIRI}, zorunlu=True),
    KisitTanimi(OGRETMEN_GUNLUK_SINIRI_TURU, {"m": VARSAYILAN_OGRETMEN_GUNLUK_SINIRI}, zorunlu=True),
    # Dersler haftalık saate göre önerilen bloklara bölünür (2+2+1...); uygulanamayan atamada öneri düşer.
    KisitTanimi(BLOK_DESENI_TURU, {"otomatik": True}, zorunlu=True),
    KisitTanimi("tercih_etmez", zorunlu=False, agirlik=5),
    KisitTanimi("ogretmen_penceresi", zorunlu=False, agirlik=3),
    KisitTanimi("sinif_boslugu", zorunlu=False, agirlik=30),  # diğer bütün esnek kurallardan baskın
    KisitTanimi("ardisik_ders", zorunlu=False, agirlik=2),
    KisitTanimi(BOS_GUN_TURU, {"hedef_bos_gun": VARSAYILAN_HEDEF_BOS_GUN}, zorunlu=False, agirlik=4),
    # Yalnızca temel program varsa etkili. Öğretmen konforu kurallarından ağır, sınıf boşluğundan hafif.
    KisitTanimi("degisiklik", zorunlu=False, agirlik=8),
)


def etkin_agirliklar(girdi: CozumGirdisi) -> dict[str, int]:
    """Esnek kural türü -> bu okulda geçerli ağırlık (okul tanımı varsayılanı ezer)."""
    tanimlar = {t.tur: t for t in VARSAYILAN_KISITLAR}
    tanimlar.update({t.tur: t for t in girdi.kisitlar if t.kapsam.okul_mu})
    return {tur: t.agirlik for tur, t in tanimlar.items() if not t.zorunlu}


def kurallari_hazirla(girdi: CozumGirdisi) -> list[KisitKurali]:
    """Temel kurallar + varsayılanlar; okulun tanımı aynı `tur`'daki varsayılanın yerini alır.

    Her `tur` için **tek** kural örneği kurulur: parametreleri okul geneli tanımdan gelir, aynı
    türün kapsamlı tanımları (özel ayarlar) örneğe verilir. "En özel kazanır" kuralın içinde
    `deger()` ile çözülür; iki örnek aynı kısıtı iki kez eklemez (ADR 0016).

    Ağırlığı 0 olan esnek kural modele hiç eklenmez (kapatılmış sayılır).
    """
    tanimlar = {t.tur: t for t in VARSAYILAN_KISITLAR}
    ozeller: dict[str, list[KisitTanimi]] = defaultdict(list)
    for t in girdi.kisitlar:
        if t.kapsam.okul_mu:
            tanimlar[t.tur] = t
        else:
            ozeller[t.tur].append(t)
    for tur in ozeller.keys() - tanimlar.keys():
        raise GirdiHatasi(f"'{tur}' için özel ayar var ama okul geneli tanımı yok")
    kurallar: list[KisitKurali] = [k() for k in TEMEL_KURALLAR]
    for tanim in tanimlar.values():
        kural = kural_olustur(tanim, ozeller.get(tanim.tur, ()))
        if kural.zorunlu or kural.agirlik > 0:
            kurallar.append(kural)
    return kurallar


__all__ = [
    "KAYIT_DEFTERI",
    "TEMEL_KURALLAR",
    "VARSAYILAN_KISITLAR",
    "Baglam",
    "GirdiHatasi",
    "KisitKurali",
    "kural_olustur",
    "etkin_agirliklar",
    "kurallari_hazirla",
]
