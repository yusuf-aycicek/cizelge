"""Bir programın zorunlu kısıtları sağladığını çözücüden bağımsız olarak denetler.

Bilinçli olarak `cpsat` ve `kisitlar` modüllerini kullanmaz: kurallar burada düz Python ile
yeniden yazılır. Böylece çözücüdeki bir hata doğrulayıcıya taşınmaz ve testler gerçek bir
ikinci görüş olur. Elle düzeltilmiş programları denetlemek için de kullanılabilir.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from cozucu.blok import BlokHesabi
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    CozumGirdisi,
    MusaitlikDurumu,
    Yerlesim,
)


def dogrula(girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> list[str]:
    """İhlal listesini döner. Boş liste = program tüm zorunlu kısıtları sağlıyor."""
    hatalar: list[str] = []
    atamalar = {a.id: a for a in girdi.atamalar}

    gecerli: list[Yerlesim] = []
    for y in yerlesimler:
        if y.ders_atama_id not in atamalar:
            hatalar.append(f"Bilinmeyen atama yerleşmiş: {y.ders_atama_id}")
        elif not girdi.ayar.aralikta(y.gun, y.saat):
            hatalar.append(f"{y.ders_atama_id}: gün/saat aralık dışında ({y.gun}, {y.saat})")
        else:
            gecerli.append(y)

    # Aynı atama aynı hücreye iki kez yazılmamalı.
    hucre_sayaci = Counter((y.ders_atama_id, y.gun, y.saat) for y in gecerli)
    for (a, g, s), adet in hucre_sayaci.items():
        if adet > 1:
            hatalar.append(f"{a}: aynı hücreye {adet} kez yerleşmiş (gün {g}, saat {s})")

    # Haftalık saat.
    adetler = Counter(y.ders_atama_id for y in gecerli)
    for a in girdi.atamalar:
        if adetler[a.id] != a.haftalik_saat:
            hatalar.append(f"{a.id}: {a.haftalik_saat} saat olmalı, {adetler[a.id]} saat yerleşmiş")

    # Sınıf ve öğretmen çakışması.
    sinif_hucre: dict[tuple[str, int, int], list[str]] = defaultdict(list)
    ogretmen_hucre: dict[tuple[str, int, int], list[str]] = defaultdict(list)
    for y in gecerli:
        a = atamalar[y.ders_atama_id]
        sinif_hucre[a.sinif_id, y.gun, y.saat].append(a.id)
        if a.ogretmen_id is not None:
            ogretmen_hucre[a.ogretmen_id, y.gun, y.saat].append(a.id)
    for (sinif, g, s), liste in sinif_hucre.items():
        if len(liste) > 1:
            hatalar.append(f"Sınıf çakışması: {sinif} gün {g} saat {s}: {sorted(liste)}")
    for (ogretmen, g, s), liste in ogretmen_hucre.items():
        if len(liste) > 1:
            hatalar.append(f"Öğretmen çakışması: {ogretmen} gün {g} saat {s}: {sorted(liste)}")

    # Gelemez.
    for m in girdi.musaitlikler:
        if m.durum is MusaitlikDurumu.GELEMEZ and ogretmen_hucre.get((m.ogretmen_id, m.gun, m.saat)):
            hatalar.append(f"Gelemez ihlali: {m.ogretmen_id} gün {m.gun} saat {m.saat}")

    # Kilitli hücreler.
    yerlesen_hucreler = set(hucre_sayaci)
    for k in girdi.kilitli_yerlesimler:
        if (k.ders_atama_id, k.gun, k.saat) not in yerlesen_hucreler:
            hatalar.append(f"Kilitli hücre yerinde değil: {k.ders_atama_id} gün {k.gun} saat {k.saat}")

    # Aynı ders bir sınıfa günde en fazla n saat, (sınıf, ders) çifti bazında.
    # Sınır şubeye, derse ya da şube grubuna özel olabilir: her çift kendi değeriyle denetlenir.
    gunluk = Counter(
        (atamalar[y.ders_atama_id].sinif_id, atamalar[y.ders_atama_id].ders_id, y.gun)
        for y in gecerli
    )
    for (sinif, ders, g), adet in gunluk.items():
        n = girdi.zorunlu_parametre(
            GUNLUK_DERS_SINIRI_TURU, "n", VARSAYILAN_GUNLUK_DERS_SINIRI, sinif_id=sinif, ders_id=ders
        )
        if n is not None and adet > n:
            hatalar.append(f"Günlük sınır aşıldı: {sinif} {ders} gün {g}: {adet} > {n}")

    # Bir öğretmen günde en fazla m saat derse girer.
    ogretmen_gunluk = Counter((o, g) for (o, g, _s), liste in ogretmen_hucre.items() for _ in liste)
    for (ogretmen, g), adet in ogretmen_gunluk.items():
        m = girdi.zorunlu_parametre(
            OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI, ogretmen_id=ogretmen
        )
        if m is not None and adet > m:
            hatalar.append(f"Öğretmen günlük sınırı aşıldı: {ogretmen} gün {g}: {adet} > {m}")

    # Blok deseni: her gün en çok bir kesintisiz parça, öğle arasını kesmeden; parça boyları desen.
    # Hangi desenin geçerli olduğu tek kaynaktan (cozucu.blok), yerleşimin ona uyması burada denetlenir.
    bloklar = BlokHesabi(girdi)
    gun_saatleri: dict[tuple[str, int], list[int]] = defaultdict(list)
    for y in gecerli:
        gun_saatleri[y.ders_atama_id, y.gun].append(y.saat)
    for a in girdi.atamalar:
        desen = bloklar.desen(a)
        if desen is None:
            continue
        parcalar = []
        for g in range(girdi.ayar.gun_sayisi):
            saatler = sorted(gun_saatleri.get((a.id, g), []))
            if not saatler:
                continue
            kesintisiz = saatler[-1] - saatler[0] + 1 == len(saatler)
            ogle = any(girdi.ayar.ogle_arasiyla_ayrilir(g, s) for s in saatler[:-1])
            if not kesintisiz or ogle:
                hatalar.append(f"Blok bölünmüş: {a.id} gün {g}: {saatler}")
            parcalar.append(len(saatler))
        if sorted(parcalar, reverse=True) != list(desen.bloklar):
            hatalar.append(f"Blok deseni tutmuyor: {a.id}: {sorted(parcalar, reverse=True)} != {list(desen.bloklar)}")

    return hatalar
