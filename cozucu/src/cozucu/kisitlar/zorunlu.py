"""Zorunlu kurallar: ihlal edilemezler, modele doğrudan kısıt olarak eklenirler.

İlk beşi programın anlamını oluşturur ve her zaman uygulanır (TEMEL_KURALLAR).
`GunlukDersSiniri` okul geneli bir kuraldır, kayıt defterine kayıtlıdır ve parametresi
`kisit` tablosundan değiştirilebilir; okul isterse onu esnek de yapabilir.
"""

from __future__ import annotations

from collections import defaultdict

from cozucu.kisitlar.temel import Baglam, CezaTerimi, KisitKurali, kaydet
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
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
            baglam.model.add(
                sum(baglam.x[a.id, g, s] for g in baglam.gunler for s in baglam.saatler)
                == a.haftalik_saat
            )
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
                baglam.model.add(baglam.hucre(a.id, m.gun, m.saat) == 0)
        return []


class KilitliHucre(KisitKurali):
    """Kilitli hücreler yerinde kalır."""

    tur = "kilitli_hucre"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        for y in baglam.girdi.kilitli_yerlesimler:
            baglam.model.add(baglam.hucre(y.ders_atama_id, y.gun, y.saat) == 1)
        return []


@kaydet
class GunlukDersSiniri(KisitKurali):
    """Aynı ders bir sınıfa günde en fazla n saat konur.

    Atama bazında değil (sınıf, ders) çifti bazında sayılır: ileride aynı derse birden
    fazla atama girildiğinde de kural doğru çalışır. Varsayılan olarak zorunludur; okul
    esnek tanımlarsa n'i aşan her saat ceza puanı getirir.
    """

    tur = GUNLUK_DERS_SINIRI_TURU
    esnek_olabilir = True

    def __init__(self, n: int = VARSAYILAN_GUNLUK_DERS_SINIRI) -> None:
        if n < 1:
            raise ValueError(f"n en az 1 olmalı: {n}")
        self.n = n

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        cezalar: list[CezaTerimi] = []
        for atamalar in sinif_ders_gruplari(baglam).values():
            for g in baglam.gunler:
                toplam = sum(baglam.dolu(atamalar, g, s) for s in baglam.saatler)
                if self.zorunlu:
                    baglam.model.add(toplam <= self.n)
                else:
                    fazla = baglam.model.new_int_var(0, len(baglam.saatler), "")
                    baglam.model.add(fazla >= toplam - self.n)
                    cezalar.append((fazla, self.agirlik))
        return cezalar


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
