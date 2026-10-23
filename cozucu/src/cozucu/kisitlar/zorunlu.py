"""Zorunlu kurallar: ihlal edilemezler, modele doğrudan kısıt olarak eklenirler.

İlk beşi programın anlamını oluşturur ve her zaman uygulanır (TEMEL_KURALLAR).
`GunlukDersSiniri` ve `OgretmenGunlukSiniri` okul geneli kurallardır, kayıt defterine kayıtlıdır ve parametresi
`kisit` tablosundan değiştirilebilir; okul isterse günlük ders sınırını esnek de yapabilir.

Her zorunlu kısıt `baglam.grupla` ile anlamlı bir gruba bağlanır; çelişki analizi
(`cozucu.celiski`) bu gruplarla "hangi kurallar birlikte sağlanamıyor" sorusunu cevaplar.
"""

from __future__ import annotations

from collections import defaultdict

from cozucu.kisitlar.temel import Baglam, CezaTerimi, KisitKurali, kaydet
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    DersAtama,
    MusaitlikDurumu,
)


def _ayni_saatte_en_fazla_bir(baglam: Baglam, atamalar: list[DersAtama]) -> None:
    for g in baglam.gunler:
        for s in baglam.saatler:
            baglam.model.add_at_most_one(baglam.x[a.id, g, s] for a in atamalar)


class HaftalikSaat(KisitKurali):
    """Her atama tam olarak haftalık saati kadar yerleşir."""

    tur = "haftalik_saat"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for a in baglam.girdi.atamalar:
            kisit = baglam.model.add(
                sum(baglam.x[a.id, g, s] for g in baglam.gunler for s in baglam.saatler)
                == a.haftalik_saat
            )
            baglam.grupla(kisit, "haftalik_saat", a.id)
        return []


class SinifCakismasi(KisitKurali):
    """Bir sınıf aynı saatte en fazla bir derste olur."""

    tur = "sinif_cakismasi"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for atamalar in baglam.sinif_atamalari.values():
            _ayni_saatte_en_fazla_bir(baglam, atamalar)
        return []


class OgretmenCakismasi(KisitKurali):
    """Bir öğretmen aynı saatte en fazla bir sınıfta olur."""

    tur = "ogretmen_cakismasi"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for atamalar in baglam.ogretmen_atamalari.values():
            _ayni_saatte_en_fazla_bir(baglam, atamalar)
        return []


class Gelemez(KisitKurali):
    """Öğretmen "gelemez" işaretli saatlere yerleştirilmez."""

    tur = "gelemez"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for m in baglam.girdi.musaitlikler:
            if m.durum is not MusaitlikDurumu.GELEMEZ:
                continue
            for a in baglam.ogretmen_atamalari.get(m.ogretmen_id, []):
                kisit = baglam.model.add(baglam.hucre(a.id, m.gun, m.saat) == 0)
                baglam.grupla(kisit, "gelemez", m.ogretmen_id)
        return []


class KilitliHucre(KisitKurali):
    """Kilitli hücreler yerinde kalır."""

    tur = "kilitli_hucre"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for y in baglam.girdi.kilitli_yerlesimler:
            kisit = baglam.model.add(baglam.hucre(y.ders_atama_id, y.gun, y.saat) == 1)
            baglam.grupla(kisit, "kilit", y.ders_atama_id, y.gun, y.saat)
        return []


@kaydet
class GunlukDersSiniri(KisitKurali):
    """Aynı ders bir sınıfa günde en fazla n saat konur.

    Atama bazında değil (sınıf, ders) çifti bazında sayılır: ileride aynı derse birden
    fazla atama girildiğinde de kural doğru çalışır. Varsayılan olarak zorunludur; okul
    esnek tanımlarsa n'i aşan her saat ceza puanı getirir.

    Derse, şubeye ya da şube grubuna özel ayarlanabilir ("11-A'da Matematik günde 3 saat").
    """

    tur = GUNLUK_DERS_SINIRI_TURU
    esnek_olabilir = True
    kapsamlar = frozenset({"ders", "sube", "sube_grubu"})

    def __init__(self, n: int = VARSAYILAN_GUNLUK_DERS_SINIRI) -> None:
        if n < 1:
            raise ValueError(f"n en az 1 olmalı: {n}")
        self.n = n

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        cezalar: list[CezaTerimi] = []
        for (sinif_id, ders_id), atamalar in sinif_ders_gruplari(baglam).items():
            n = self.deger(baglam, "n", sinif_id=sinif_id, ders_id=ders_id)
            for g in baglam.gunler:
                toplam = sum(baglam.dolu(atamalar, g, s) for s in baglam.saatler)
                if self.zorunlu:
                    kisit = baglam.model.add(toplam <= n)
                    baglam.grupla(kisit, "gunluk_ders", sinif_id, ders_id)
                else:
                    fazla = baglam.model.new_int_var(0, len(baglam.saatler), "")
                    baglam.model.add(fazla >= toplam - n)
                    cezalar.append((fazla, self.agirlik))
        return cezalar


@kaydet
class OgretmenGunlukSiniri(KisitKurali):
    """Bir öğretmen günde en fazla m saat derse girer (okuldan gelen kural, varsayılan 8).

    Öğretmene özel ayarlanabilir ("Ayşe Yılmaz günde en fazla 6 saat").
    """

    tur = OGRETMEN_GUNLUK_SINIRI_TURU
    kapsamlar = frozenset({"ogretmen"})

    def __init__(self, m: int = VARSAYILAN_OGRETMEN_GUNLUK_SINIRI) -> None:
        if m < 1:
            raise ValueError(f"m en az 1 olmalı: {m}")
        self.m = m

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for ogretmen_id, atamalar in baglam.ogretmen_atamalari.items():
            m = self.deger(baglam, "m", ogretmen_id=ogretmen_id)
            if m >= len(baglam.saatler):
                continue  # okulun günü zaten m saatten kısa: kısıt hiçbir şeyi değiştirmez
            for g in baglam.gunler:
                kisit = baglam.model.add(
                    sum(baglam.dolu(atamalar, g, s) for s in baglam.saatler) <= m
                )
                baglam.grupla(kisit, "ogretmen_gunluk", ogretmen_id)
        return []


def sinif_ders_gruplari(baglam: Baglam) -> dict[tuple[str, str], list[DersAtama]]:
    gruplar: dict[tuple[str, str], list[DersAtama]] = defaultdict(list)
    for a in baglam.girdi.atamalar:
        gruplar[a.sinif_id, a.ders_id].append(a)
    return dict(gruplar)


TEMEL_KURALLAR: tuple[type[KisitKurali], ...] = (
    HaftalikSaat,
    SinifCakismasi,
    OgretmenCakismasi,
    Gelemez,
    KilitliHucre,
)
