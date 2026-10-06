"""Esnek kurallar: ihlal edilebilirler ama her ihlal ceza puanı getirir (bkz. docs/adr/0004).

Her kural (ceza ifadesi, ağırlık) çiftleri döner; çözücü ağırlıklı toplamı en aza indirir.
Ceza ifadeleri, `cozucu.kalite` modülündeki bağımsız ölçümlerle birebir aynı şeyi sayar:
cezası sıfır olan bir program o ölçüde kusursuzdur.

Yardımcı boolean'lar yalnızca alttan sınırlanır (ör. `once >= dolu`). Amaç fonksiyonu
onları aşağı ittiği için en iyi çözümde tam istenen değeri alırlar; böylece model doğrusal
ve küçük kalır.
"""

from __future__ import annotations

from cozucu.kisitlar.temel import Baglam, CezaTerimi, KisitKurali, kaydet
from cozucu.kisitlar.zorunlu import sinif_ders_gruplari
from cozucu.model import MusaitlikDurumu


class EsnekKural(KisitKurali):
    zorunlu_olabilir = False
    esnek_olabilir = True


@kaydet
class TercihEtmez(EsnekKural):
    """Öğretmenin "tercih etmez" saatine konan her ders için ceza."""

    tur = "tercih_etmez"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        cezalar: list[CezaTerimi] = []
        for m in baglam.girdi.musaitlikler:
            if m.durum is not MusaitlikDurumu.TERCIH_ETMEZ:
                continue
            for a in baglam.ogretmen_atamalari.get(m.ogretmen_id, []):
                cezalar.append((baglam.hucre(a.id, m.gun, m.saat), self.agirlik))
        return cezalar


@kaydet
class OgretmenPenceresi(EsnekKural):
    """Öğretmenin gün içindeki ilk ve son dersi arasındaki her boş saat için ceza.

    Her saat için: once[s] = "s'de ya da öncesinde dersi var", sonra[s] = "s'de ya da
    sonrasında dersi var". İkisi de doğruysa öğretmen o saatte okuldadır. Okulda olduğu
    ama dersi olmadığı saatler penceredir.
    """

    tur = "ogretmen_penceresi"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        cezalar: list[CezaTerimi] = []
        saatler = list(baglam.saatler)
        for atamalar in baglam.ogretmen_atamalari.values():
            for g in baglam.gunler:
                dolu = [baglam.dolu(atamalar, g, s) for s in saatler]
                once = _kumulatif(baglam, dolu)
                sonra = _kumulatif(baglam, dolu[::-1])[::-1]
                for s in saatler:
                    okulda = baglam.model.new_bool_var("")
                    baglam.model.add(okulda >= once[s] + sonra[s] - 1)
                    cezalar.append((okulda - dolu[s], self.agirlik))
        return cezalar


@kaydet
class SinifBoslugu(EsnekKural):
    """Sınıfın, o gün sonrasında hâlâ dersi olan her boş saati için ceza.

    Ceza sıfırsa dersler günün başından itibaren kesintisiz dolar ve boş saatler
    günün sonunda toplanır.
    """

    tur = "sinif_boslugu"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        cezalar: list[CezaTerimi] = []
        saatler = list(baglam.saatler)
        for atamalar in baglam.sinif_atamalari.values():
            for g in baglam.gunler:
                dolu = [baglam.dolu(atamalar, g, s) for s in saatler]
                sonra = _kumulatif(baglam, dolu[::-1])[::-1]
                cezalar.extend((sonra[s] - dolu[s], self.agirlik) for s in saatler)
        return cezalar


@kaydet
class ArdisikDers(EsnekKural):
    """Bir dersin aynı gündeki saatleri tek blok halinde olmalı.

    Ceza = o günkü blok sayısı - 1 = toplam saat - bitişik çift sayısı - 1 (en az 0).
    Günde en fazla 2 saatlik derslerde bu, "bitişik olmayan çift ders" sayısıdır.
    (sınıf, ders) çifti bazında sayılır (günlük sınır kuralıyla aynı gerekçe).
    """

    tur = "ardisik_ders"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        cezalar: list[CezaTerimi] = []
        saatler = list(baglam.saatler)
        for atamalar in sinif_ders_gruplari(baglam).values():
            for g in baglam.gunler:
                dolu = [baglam.dolu(atamalar, g, s) for s in saatler]
                bitisik = []
                for s in saatler[:-1]:
                    b = baglam.model.new_bool_var("")
                    baglam.model.add(b <= dolu[s])
                    baglam.model.add(b <= dolu[s + 1])
                    bitisik.append(b)
                ceza = baglam.model.new_int_var(0, len(saatler), "")
                baglam.model.add(ceza >= sum(dolu) - sum(bitisik) - 1)
                cezalar.append((ceza, self.agirlik))
        return cezalar


def _kumulatif(baglam: Baglam, dolu: list) -> list:
    """k[s] >= dolu[s] ve k[s] >= k[s-1]: "s'de ya da daha önce dolu" (en iyi çözümde tam)."""
    sonuc = []
    for s, d in enumerate(dolu):
        k = baglam.model.new_bool_var("")
        baglam.model.add(k >= d)
        if s > 0:
            baglam.model.add(k >= sonuc[s - 1])
        sonuc.append(k)
    return sonuc

