"""İkincil esnek kuralların (K6) varlık başına değerleri: tek kaynak.

Çözücüdeki kural ve kalite ölçümü aynı değeri buradan alır (ADR 0015'teki ilke); böylece
modelin cezası ile `kalite.olc` birebir tutarlı kalır.

- Dersin saat tercihi (`ders_saat_tercihi`): bir (şube, ders) için cezalı saatler.
- Öğretmenin geldiği günde en az ders (`gunluk_en_az_ders`): öğretmenin etkin alt sınırı.
- Aynı dersin günlere yayılması (`ders_yayilimi`): bir (şube, ders) için açık mı.
"""

from __future__ import annotations

from cozucu.model import (
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    CozumGirdisi,
    MusaitlikDurumu,
)

SAAT_TERCIHI_TURU = "ders_saat_tercihi"
EN_AZ_DERS_TURU = "gunluk_en_az_ders"
YAYILIM_TURU = "ders_yayilimi"
# Öğretmen geldiği bir günde en az kaç ders saati vermeli ("bir saat için gelmem").
VARSAYILAN_GUNLUK_EN_AZ_DERS = 2


def cezali_saatler(girdi: CozumGirdisi, sinif_id: str, ders_id: str) -> frozenset[int]:
    """Bu şubenin bu dersinin konması cezalı saatler (boş: tercih yok).

    `saatler` doluysa yalnızca onlar tercih edilir, dışındaki her saat cezalıdır; `kacin`daki
    saatler her zaman cezalıdır. Saatler 0'dan başlar (0 = 1. ders).
    """
    tercih = girdi.parametre(SAAT_TERCIHI_TURU, "saatler", [], sinif_id=sinif_id, ders_id=ders_id)
    kacin = girdi.parametre(SAAT_TERCIHI_TURU, "kacin", [], sinif_id=sinif_id, ders_id=ders_id)
    tum = range(girdi.ayar.gunluk_ders_saati)
    return frozenset(s for s in tum if (tercih and s not in tercih) or s in kacin)


def gunluk_en_az_ders(girdi: CozumGirdisi, ogretmen_id: str, yuk: int) -> int:
    """Öğretmenin geldiği bir günde en az kaç ders vermesi hedefleniyor (1 ya da az: kural yok).

    Okul ya da öğretmene özel değer, öğretmenin yapabileceğiyle sınırlanır: haftalık yükü ve
    bir günde verebileceği en çok ders (günlük sınır M ile o gün müsait olduğu saatin küçüğü,
    en iyi gün). Ders saati yetmeyen öğretmene ceza yazılmaz: 1 saat dersi olan öğretmen o
    gün 1 saat için gelmek zorundadır.
    """
    k = girdi.parametre(EN_AZ_DERS_TURU, "k", VARSAYILAN_GUNLUK_EN_AZ_DERS, ogretmen_id=ogretmen_id)
    m = girdi.parametre(OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI, ogretmen_id=ogretmen_id)
    ayar = girdi.ayar
    gelemez = [0] * ayar.gun_sayisi
    for mu in girdi.musaitlikler:
        if mu.ogretmen_id == ogretmen_id and mu.durum is MusaitlikDurumu.GELEMEZ and ayar.aralikta(mu.gun, mu.saat):
            gelemez[mu.gun] += 1
    en_iyi_gun = max(min(m, ayar.saat_sayisi(g) - gelemez[g]) for g in range(ayar.gun_sayisi))
    return max(0, min(k, yuk, en_iyi_gun))


def yayilsin(girdi: CozumGirdisi, sinif_id: str, ders_id: str) -> bool:
    """Bu şubenin bu dersi art arda günlere yığılmasın mı (varsayılan: evet)."""
    return bool(girdi.parametre(YAYILIM_TURU, "yayilsin", True, sinif_id=sinif_id, ders_id=ders_id))
