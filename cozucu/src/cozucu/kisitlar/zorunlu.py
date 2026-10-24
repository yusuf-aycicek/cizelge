"""Zorunlu kurallar: ihlal edilemezler, modele doğrudan kısıt olarak eklenirler.

İlk altısı programın anlamını oluşturur ve her zaman uygulanır (TEMEL_KURALLAR).
`GunlukDersSiniri` ve `OgretmenGunlukSiniri` okul geneli kurallardır, kayıt defterine kayıtlıdır ve parametresi
`kisit` tablosundan değiştirilebilir; okul isterse günlük ders sınırını esnek de yapabilir.

Her zorunlu kısıt `baglam.grupla` ile anlamlı bir gruba bağlanır; çelişki analizi
(`cozucu.celiski`) bu gruplarla "hangi kurallar birlikte sağlanamıyor" sorusunu cevaplar.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from cozucu.blok import BLOK_DESENI_TURU, BlokHesabi, baslangiclar, desen_dogrula
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


class GunUzunlugu(KisitKurali):
    """Günün uzunluğunu aşan saatlere ders konmaz (ör. cuma 7 saatse 8. saat yoktur).

    Değişkenler en uzun güne göre kurulur (`Baglam.saatler`); kısa günün sonundaki hücreler
    burada 0'a sabitlenir. Böylece öteki kurallar her günü aynı biçimde dolaşır; CP-SAT ön
    işlemesi sabit değişkenleri zaten modelden atar.
    """

    tur = "gun_uzunlugu"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        ayar = baglam.girdi.ayar
        for g in baglam.gunler:
            for s in range(ayar.saat_sayisi(g), len(baglam.saatler)):
                for a in baglam.girdi.atamalar:
                    kisit = baglam.model.add(baglam.x[a.id, g, s] == 0)
                    baglam.grupla(kisit, "gun_uzunlugu", g)
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


@kaydet
class BlokDeseni(KisitKurali):
    """Bir dersin haftalık saatleri desendeki bloklara bölünür ("2+2+1"); her blok ayrı bir günde,
    art arda, günün içinde ve öğle arasını kesmeden (docs/kisisellestirme-plani.md 4.1).

    Parametreler: okul geneli `otomatik` (haftalık saate göre önerilen desen) ve `varsayilanlar`
    (saat → desen, öneriyi değiştirir); derse, ders + şubeye ya da ders + şube grubuna özel `desen`
    (`[]` = blok yok).
    Hangi atamaya hangi desenin uygulanacağı `cozucu.blok.BlokHesabi`'dan gelir (tek kaynak).

    Model: `bas[g, s, b]` = "b saatlik blok g günü s saatinde başlıyor". Yalnızca bloğun sığdığı
    başlangıçlar için değişken üretilir; öğle arası ve gün uzunluğu böylece ayrı kısıt gerekmeden
    uygulanır. Kısıtlar: her ders saati tam bir bloğa ait (x = kapsayan başlangıçların toplamı),
    günde en çok bir blok, her boydan desendeki kadar blok.
    """

    tur = BLOK_DESENI_TURU
    kapsamlar = frozenset({"ders", "sube", "sube_grubu"})
    zorunlu_eksenler = frozenset({"ders"})

    def __init__(self, otomatik: bool = True, varsayilanlar: dict | None = None, desen: list | None = None) -> None:
        if not isinstance(otomatik, bool):
            raise ValueError(f"otomatik true ya da false olmalı: {otomatik!r}")
        for saat, d in (varsayilanlar or {}).items():
            bloklar = desen_dogrula(d)
            if bloklar and sum(bloklar) != int(saat):
                raise ValueError(f"{saat} saat için desen toplamı {sum(bloklar)}")
        if desen is not None:
            desen_dogrula(desen)
        self.otomatik = otomatik
        self.varsayilanlar = varsayilanlar or {}
        self.desen = desen

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        hesap = BlokHesabi(baglam.girdi)
        ayar = baglam.girdi.ayar
        for a in baglam.girdi.atamalar:
            d = hesap.desen(a)
            if d is None:
                continue
            m = baglam.model
            sayilar = Counter(d.bloklar)
            bas = {
                (g, s, b): m.new_bool_var(f"bas[{a.id},{g},{s},{b}]")
                for g in baglam.gunler for b in sayilar for s in baslangiclar(ayar, g, b)
            }
            kisitlar = []
            for g in baglam.gunler:
                for s in baglam.saatler:
                    kapsayan = [v for (gg, s0, b), v in bas.items() if gg == g and s0 <= s < s0 + b]
                    kisitlar.append(m.add(baglam.x[a.id, g, s] == sum(kapsayan)))
                kisitlar.append(m.add(sum(v for (gg, _s, _b), v in bas.items() if gg == g) <= 1))
            for b, adet in sayilar.items():
                kisitlar.append(m.add(sum(v for (_g, _s, bb), v in bas.items() if bb == b) == adet))
            for k in kisitlar:
                baglam.grupla(k, "blok", a.id)
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
    GunUzunlugu,
    KilitliHucre,
)
