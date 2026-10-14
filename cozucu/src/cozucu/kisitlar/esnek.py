"""Esnek kurallar: ihlal edilebilirler ama her ihlal ceza puanı getirir (bkz. docs/adr/0004).

Her kural (ceza ifadesi, ağırlık) çiftleri döner; çözücü ağırlıklı toplamı en aza indirir.
Ceza ifadeleri, `cozucu.kalite` modülündeki bağımsız ölçümlerle birebir aynı şeyi sayar:
cezası sıfır olan bir program o ölçüde kusursuzdur.

Yardımcı boolean'lar yalnızca alttan sınırlanır (ör. `once >= dolu`). Amaç fonksiyonu
onları aşağı ittiği için en iyi çözümde tam istenen değeri alırlar; böylece model doğrusal
ve küçük kalır.

Ceza terimleri amaca yalnızca negatif olamayan tek bir değişken olarak girer (bkz.
docs/adr/0007). `okulda - dolu` gibi bir fark doğrudan amaca yazılırsa ders değişkenleri
amaçta negatif katsayı alır ve CP-SAT'ın alt sınırı çok negatiften başlar. Bu, gerçekçi sette
60. saniyedeki cezayı %33 kötüleştiriyordu. Fark bunun yerine bir 0/1 "boşluk" değişkenine
bağlanır: `bosluk >= okulda - dolu`.
"""

from __future__ import annotations

from cozucu.kisitlar.temel import Baglam, CezaTerimi, KisitKurali, kaydet
from cozucu.kisitlar.zorunlu import sinif_ders_gruplari
from cozucu.model import (
    BOS_GUN_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_HEDEF_BOS_GUN,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    MusaitlikDurumu,
    TemelYerlesim,
)


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
                    pencere = baglam.model.new_bool_var("")  # okulda ama dersi yok
                    baglam.model.add(pencere >= okulda - dolu[s])
                    cezalar.append((pencere, self.agirlik))
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
                for s in saatler:
                    bosluk = baglam.model.new_bool_var("")  # sonra dersi var ama bu saat boş
                    baglam.model.add(bosluk >= sonra[s] - dolu[s])
                    cezalar.append((bosluk, self.agirlik))
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


@kaydet
class BosGun(EsnekKural):
    """Her öğretmene hedeflenen sayıda boş gün kazandırmak.

    Amaç en fazla sıkıştırma değil, hedefe ulaşmaktır:
        günlük sınır = min(öğretmen günlük sınırı M, okulun günlük ders saati)
        hedef gün    = max(⌈toplam saat / günlük sınır⌉, gün sayısı − hedef boş gün)
        ceza         = max(0, ders verilen gün − hedef gün)
    Hedefe ulaşan öğretmen daha fazla sıkıştırılmaz. Yükü yüzünden boş günü mümkün olmayan
    öğretmenin hedefi zaten bütün günlerdir, ona ceza yazılmaz.
    """

    tur = BOS_GUN_TURU

    def __init__(self, hedef_bos_gun: int = VARSAYILAN_HEDEF_BOS_GUN) -> None:
        if hedef_bos_gun < 0:
            raise ValueError(f"hedef_bos_gun negatif olamaz: {hedef_bos_gun}")
        self.hedef_bos_gun = hedef_bos_gun

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        gun_sayisi = len(baglam.gunler)
        m = baglam.girdi.zorunlu_parametre(
            OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI
        )
        gunluk_sinir = min(m or len(baglam.saatler), len(baglam.saatler))
        cezalar: list[CezaTerimi] = []
        for atamalar in baglam.ogretmen_atamalari.values():
            yuk = sum(a.haftalik_saat for a in atamalar)
            hedef_gun = max(-(-yuk // gunluk_sinir), gun_sayisi - self.hedef_bos_gun)
            if hedef_gun >= gun_sayisi:
                continue  # her gün çalışması serbest: ceza hiç doğmaz
            gun_var = []
            for g in baglam.gunler:
                var = baglam.model.new_bool_var("")
                for s in baglam.saatler:
                    baglam.model.add(var >= baglam.dolu(atamalar, g, s))
                gun_var.append(var)
            fazla = baglam.model.new_int_var(0, gun_sayisi, "")
            baglam.model.add(fazla >= sum(gun_var) - hedef_gun)
            cezalar.append((fazla, self.agirlik))
        return cezalar


@kaydet
class Degisiklik(EsnekKural):
    """En az değişiklikle güncelleme: temel programdaki her hücre yeni programda yoksa ceza.

    Hücreler (sınıf, ders, gün, saat) ile eşleştirilir. Temel program yoksa kural hiçbir şey
    yapmaz. Temel program ayrıca CP-SAT'a başlangıç ipucu olarak verilir: arama oradan başlar,
    ama ipucu sonucu zorlamaz (bkz. docs/adr/0006).

    Temel programda olup artık var olmayan dersler (ders kaldırılmış, okul saati kısalmış)
    kaçınılmaz değişikliklerdir. Sabit ceza olarak eklenirler; en iyi programı etkilemezler
    ama toplam ceza, `kalite.degisen_yerlesim` ölçümüyle birebir tutarlı kalır.
    """

    tur = "degisiklik"

    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        temel = set(baglam.girdi.temel_yerlesimler)
        if not temel:
            return []
        gruplar = sinif_ders_gruplari(baglam)
        cezalar: list[CezaTerimi] = []
        for t in temel:
            atamalar = gruplar.get((t.sinif_id, t.ders_id))
            if atamalar is None or t.gun not in baglam.gunler or t.saat not in baglam.saatler:
                cezalar.append((1, self.agirlik))
            else:
                degisti = baglam.model.new_bool_var("")
                baglam.model.add(degisti >= 1 - baglam.dolu(atamalar, t.gun, t.saat))
                cezalar.append((degisti, self.agirlik))

        for (sinif_id, ders_id), atamalar in gruplar.items():
            for a in atamalar:
                for g in baglam.gunler:
                    for s in baglam.saatler:
                        temelde = TemelYerlesim(sinif_id, ders_id, g, s) in temel
                        baglam.model.add_hint(baglam.x[a.id, g, s], temelde)
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

