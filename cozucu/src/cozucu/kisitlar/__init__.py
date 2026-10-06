"""Kısıt kuralları. Alt modüllerin içe aktarılması kayıt defterini doldurur."""

from cozucu.kisitlar import esnek, zorunlu  # noqa: F401  (kayıt için)
from cozucu.kisitlar.temel import KAYIT_DEFTERI, Baglam, GirdiHatasi, KisitKurali, kural_olustur
from cozucu.kisitlar.zorunlu import TEMEL_KURALLAR
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    CozumGirdisi,
    KisitTanimi,
)

# Okul hiçbir şey tanımlamazsa uygulanan okul geneli kurallar. Ağırlıklar plan kararı 3.
VARSAYILAN_KISITLAR: tuple[KisitTanimi, ...] = (
    KisitTanimi(GUNLUK_DERS_SINIRI_TURU, {"n": VARSAYILAN_GUNLUK_DERS_SINIRI}, zorunlu=True),
    KisitTanimi("tercih_etmez", zorunlu=False, agirlik=5),
    KisitTanimi("ogretmen_penceresi", zorunlu=False, agirlik=3),
    KisitTanimi("sinif_boslugu", zorunlu=False, agirlik=10),
    KisitTanimi("ardisik_ders", zorunlu=False, agirlik=2),
)


def kurallari_hazirla(girdi: CozumGirdisi) -> list[KisitKurali]:
    """Temel kurallar + varsayılanlar; okulun tanımı aynı `tur`'daki varsayılanın yerini alır.

    Ağırlığı 0 olan esnek kural modele hiç eklenmez (kapatılmış sayılır).
    """
    tanimlar = {t.tur: t for t in VARSAYILAN_KISITLAR}
    tanimlar.update({t.tur: t for t in girdi.kisitlar})
    kurallar: list[KisitKurali] = [k() for k in TEMEL_KURALLAR]
    for tanim in tanimlar.values():
        kural = kural_olustur(tanim)
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
    "kurallari_hazirla",
]
