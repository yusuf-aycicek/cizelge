"""Bir programın zorunlu kısıtları sağladığını çözücüden bağımsız olarak denetler.

Bilinçli olarak `cpsat` ve `kisitlar` modüllerini kullanmaz: kurallar burada düz Python ile
yeniden yazılır. Böylece çözücüdeki bir hata doğrulayıcıya taşınmaz ve testler gerçek bir
ikinci görüş olur. Elle düzeltilmiş programları denetlemek için de kullanılabilir.
"""

from __future__ import annotations

from collections import Counter, defaultdict

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
    gun_sayisi, saat_sayisi = girdi.ayar.gun_sayisi, girdi.ayar.gunluk_ders_saati

    gecerli: list[Yerlesim] = []
    for y in yerlesimler:
        if y.ders_atama_id not in atamalar:
            hatalar.append(f"Bilinmeyen atama yerleşmiş: {y.ders_atama_id}")
        elif not (0 <= y.gun < gun_sayisi and 0 <= y.saat < saat_sayisi):
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
    n = girdi.zorunlu_parametre(GUNLUK_DERS_SINIRI_TURU, "n", VARSAYILAN_GUNLUK_DERS_SINIRI)
    if n is not None:
        gunluk = Counter(
            (atamalar[y.ders_atama_id].sinif_id, atamalar[y.ders_atama_id].ders_id, y.gun)
            for y in gecerli
        )
        for (sinif, ders, g), adet in gunluk.items():
            if adet > n:
                hatalar.append(f"Günlük sınır aşıldı: {sinif} {ders} gün {g}: {adet} > {n}")

    # Bir öğretmen günde en fazla m saat derse girer.
    m = girdi.zorunlu_parametre(OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI)
    if m is not None:
        ogretmen_gunluk = Counter((o, g) for (o, g, _s), liste in ogretmen_hucre.items() for _ in liste)
        for (ogretmen, g), adet in ogretmen_gunluk.items():
            if adet > m:
                hatalar.append(f"Öğretmen günlük sınırı aşıldı: {ogretmen} gün {g}: {adet} > {m}")

    return hatalar
