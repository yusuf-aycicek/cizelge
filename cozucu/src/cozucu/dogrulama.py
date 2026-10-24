"""Bir programın zorunlu kısıtları sağladığını çözücüden bağımsız olarak denetler.

Bilinçli olarak `cpsat` ve `kisitlar` modüllerini kullanmaz: kurallar burada düz Python ile
yeniden yazılır. Böylece çözücüdeki bir hata doğrulayıcıya taşınmaz ve testler gerçek bir
ikinci görüş olur. Elle düzeltilmiş programları denetlemek için de kullanılır (7.1, `tasima`).

`ihlaller` her ihlali yapılandırılmış döner: türü, karşılaştırma anahtarı (aynı ihlal iki
programda aynı anahtarı taşır; taşıma yalnızca **yeni** ihlallere bakar), teknik metin (günlük ve
testler) ve kullanıcının diliyle mesaj ("Ayşe Yılmaz Salı 3. saatte 9-B'de derste").
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from cozucu.anlatim import Anlatim, iyelik
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


@dataclass(frozen=True)
class Ihlal:
    tur: str
    anahtar: tuple
    teknik: str
    mesaj: str


def dogrula(girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> list[str]:
    """İhlal listesini döner. Boş liste = program tüm zorunlu kısıtları sağlıyor."""
    return [i.teknik for i in ihlaller(girdi, yerlesimler)]


def ihlaller(girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> list[Ihlal]:
    """Zorunlu kısıt ihlalleri, yapılandırılmış. Boş liste = program geçerli."""
    hatalar: list[Ihlal] = []
    ad = Anlatim(girdi)

    def ekle(tur: str, anahtar: tuple, teknik: str, mesaj: str) -> None:
        hatalar.append(Ihlal(tur, (tur, *anahtar), teknik, mesaj))

    atamalar = {a.id: a for a in girdi.atamalar}

    gecerli: list[Yerlesim] = []
    for y in yerlesimler:
        if y.ders_atama_id not in atamalar:
            ekle("bilinmeyen", (y.ders_atama_id,), f"Bilinmeyen atama yerleşmiş: {y.ders_atama_id}",
                 "Programda artık olmayan bir ders var")
        elif not girdi.ayar.aralikta(y.gun, y.saat):
            ekle("aralik", (y.ders_atama_id, y.gun, y.saat), f"{y.ders_atama_id}: gün/saat aralık dışında ({y.gun}, {y.saat})",
                 f"{ad.zaman(y.gun, y.saat)} okulun haftasında yok")
        else:
            gecerli.append(y)

    # Aynı atama aynı hücreye iki kez yazılmamalı.
    hucre_sayaci = Counter((y.ders_atama_id, y.gun, y.saat) for y in gecerli)
    for (a, g, s), adet in hucre_sayaci.items():
        if adet > 1:
            ekle("tekrar", (a, g, s), f"{a}: aynı hücreye {adet} kez yerleşmiş (gün {g}, saat {s})",
                 f"{ad.atama(a)} {ad.zaman(g, s)} iki kez yerleşmiş")

    # Haftalık saat.
    adetler = Counter(y.ders_atama_id for y in gecerli)
    for a in girdi.atamalar:
        if adetler[a.id] != a.haftalik_saat:
            ekle("haftalik", (a.id,), f"{a.id}: {a.haftalik_saat} saat olmalı, {adetler[a.id]} saat yerleşmiş",
                 f"{ad.atama(a)} haftada {a.haftalik_saat} saat olmalı, {adetler[a.id]} saat yerleşmiş")

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
            dersler = ", ".join(sorted(ad.ders(atamalar[x].ders_id) for x in liste))
            ekle("sinif_cakismasi", (sinif, g, s), f"Sınıf çakışması: {sinif} gün {g} saat {s}: {sorted(liste)}",
                 f"{ad.sinif(sinif)} {ad.zaman(g, s)} iki derste olur ({dersler})")
    for (ogretmen, g, s), liste in ogretmen_hucre.items():
        if len(liste) > 1:
            subeler = ", ".join(sorted(ad.sinif(atamalar[x].sinif_id) for x in liste))
            ekle("ogretmen_cakismasi", (ogretmen, g, s), f"Öğretmen çakışması: {ogretmen} gün {g} saat {s}: {sorted(liste)}",
                 f"{ad.ogretmen(ogretmen)} {ad.zaman(g, s)} iki şubede olur ({subeler})")

    # Gelemez.
    for m in girdi.musaitlikler:
        if m.durum is MusaitlikDurumu.GELEMEZ and ogretmen_hucre.get((m.ogretmen_id, m.gun, m.saat)):
            ekle("gelemez", (m.ogretmen_id, m.gun, m.saat), f"Gelemez ihlali: {m.ogretmen_id} gün {m.gun} saat {m.saat}",
                 f"{ad.ogretmen(m.ogretmen_id)} {ad.zaman(m.gun, m.saat)} gelemez")

    # Kilitli hücreler.
    yerlesen_hucreler = set(hucre_sayaci)
    for k in girdi.kilitli_yerlesimler:
        if (k.ders_atama_id, k.gun, k.saat) not in yerlesen_hucreler:
            ekle("kilit", (k.ders_atama_id, k.gun, k.saat), f"Kilitli hücre yerinde değil: {k.ders_atama_id} gün {k.gun} saat {k.saat}",
                 f"{ad.atama(k.ders_atama_id)} {ad.zaman(k.gun, k.saat)} kilitli, yerinden çıkamaz")

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
            ekle("gunluk_sinir", (sinif, ders, g), f"Günlük sınır aşıldı: {sinif} {ders} gün {g}: {adet} > {n}",
                 f"{ad.sinif_ders(sinif, ders)} {ad.gun(g)} günü {adet} saat olur; günde en fazla {n} saat")

    # Bir öğretmen günde en fazla m saat derse girer.
    ogretmen_gunluk = Counter((o, g) for (o, g, _s), liste in ogretmen_hucre.items() for _ in liste)
    for (ogretmen, g), adet in ogretmen_gunluk.items():
        m = girdi.zorunlu_parametre(
            OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI, ogretmen_id=ogretmen
        )
        if m is not None and adet > m:
            ekle("ogretmen_gunluk_sinir", (ogretmen, g), f"Öğretmen günlük sınırı aşıldı: {ogretmen} gün {g}: {adet} > {m}",
                 f"{ad.ogretmen(ogretmen)} {ad.gun(g)} günü {adet} saat derse girer; günde en fazla {m} saat")

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
                neden = "öğle arasını keser" if kesintisiz else "bölünür"
                ekle("ogle_arasi" if kesintisiz else "blok_bolundu", (a.id, g), f"Blok bölünmüş: {a.id} gün {g}: {saatler}",
                     f"{ad.atama(a)} {ad.gun(g)} günü {neden} (blok bütün kalmalı)")
            parcalar.append(len(saatler))
        if sorted(parcalar, reverse=True) != list(desen.bloklar):
            olan = "+".join(map(str, sorted(parcalar, reverse=True)))
            ekle("blok_deseni", (a.id,), f"Blok deseni tutmuyor: {a.id}: {sorted(parcalar, reverse=True)} != {list(desen.bloklar)}",
                 f"{iyelik(ad.atama(a))} dağılımı {'+'.join(map(str, desen.bloklar))} olmalı, {olan} olur")

    return hatalar
