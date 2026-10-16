"""Çözücü çağrılmadan önce yapılan hızlı ve kesin kontroller.

Bir kontrol hata buluyorsa çözüm kesinlikle yoktur (ya da veri çözücüye verilemez). Mesajlar
kullanıcının diliyle ve adlarla yazılır. Bulunan bütün sorunlar birlikte döner, ilk hatada
durulmaz: kullanıcı hepsini tek seferde düzeltebilsin.

Sıra: önce veri tutarlılığı. Tutarsız veri varsa kapasite kontrolleri yapılmaz, çünkü bozuk
referanslarla yapılan hesaplar yanıltıcı mesajlar üretir.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from cozucu.anlatim import Anlatim, iyelik
from cozucu.kisitlar import GirdiHatasi, kural_olustur
from cozucu.model import Celiski, CozumGirdisi, DersAtama, MusaitlikDurumu
from cozucu.yuk import YukHesabi


def on_kontrol(girdi: CozumGirdisi) -> list[Celiski]:
    """Boş liste = ön kontrolden geçti (çözüm olduğu garanti değildir)."""
    kontrol = _Kontrol(girdi)
    sorunlar = kontrol.tutarlilik()
    if sorunlar:
        return sorunlar
    sorunlar = (
        kontrol.ogretmensiz_atama()
        + kontrol.sinif_kapasitesi()
        + kontrol.ogretmen_kapasitesi()
        + kontrol.ders_gun_kapasitesi()
        + kontrol.kilitler()
    )
    return sorunlar + kontrol.sinif_musaitligi(sorunlar)


class _Kontrol:
    def __init__(self, girdi: CozumGirdisi) -> None:
        self.girdi = girdi
        self.ad = Anlatim(girdi)
        # Günlük sınırlar, müsait saatler ve yükler tek yerde hesaplanır (yuk.py, ADR 0015).
        self.yuk = YukHesabi(girdi)
        self.gun_sayisi = self.yuk.gun_sayisi
        self.saat_sayisi = self.yuk.saat_sayisi
        self.n = self.yuk.n
        self.m = self.yuk.m
        self.atama = {a.id: a for a in girdi.atamalar}
        self._gelemez = self.yuk.gelemez

    # --- veri tutarlılığı -------------------------------------------------------------

    def tutarlilik(self) -> list[Celiski]:
        g = self.girdi
        sorunlar: list[Celiski] = []

        def ekle(mesaj: str, *ilgili: str) -> None:
            sorunlar.append(Celiski("tutarsiz_veri", mesaj, tuple(ilgili)))

        for liste_adi, kayitlar in (
            ("öğretmen", g.ogretmenler),
            ("sınıf", g.siniflar),
            ("ders", g.dersler),
            ("ders ataması", g.atamalar),
        ):
            for kimlik, adet in Counter(k.id for k in kayitlar).items():
                if adet > 1:
                    ekle(f"Aynı kimlikle {adet} {liste_adi} kaydı var: {kimlik}", kimlik)

        ogretmenler = {o.id for o in g.ogretmenler}
        siniflar = {s.id for s in g.siniflar}
        dersler = {d.id for d in g.dersler}
        for a in g.atamalar:
            if a.sinif_id not in siniflar:
                ekle(f"'{a.id}' ataması tanımlı olmayan bir sınıfa bağlı: {a.sinif_id}", a.id)
            if a.ders_id not in dersler:
                ekle(f"'{a.id}' ataması tanımlı olmayan bir derse bağlı: {a.ders_id}", a.id)
            if a.ogretmen_id is not None and a.ogretmen_id not in ogretmenler:
                ekle(f"'{a.id}' ataması tanımlı olmayan bir öğretmene bağlı: {a.ogretmen_id}", a.id)

        for mu in g.musaitlikler:
            if mu.ogretmen_id not in ogretmenler:
                ekle(f"Müsaitlik tanımlı olmayan bir öğretmen için girilmiş: {mu.ogretmen_id}", mu.ogretmen_id)
            elif not self._aralikta(mu.gun, mu.saat):
                ekle(
                    f"{iyelik(self.ad.ogretmen(mu.ogretmen_id))} müsaitliği okulun gün/saat aralığı "
                    f"dışında: {self.ad.zaman(mu.gun, mu.saat)}",
                    mu.ogretmen_id,
                )

        for k in g.kilitli_yerlesimler:
            if k.ders_atama_id not in self.atama:
                ekle(f"Kilitli hücre tanımlı olmayan bir atamaya ait: {k.ders_atama_id}", k.ders_atama_id)
            elif not self._aralikta(k.gun, k.saat):
                ekle(
                    f"{self.ad.atama(k.ders_atama_id)} için kilitli hücre okulun gün/saat aralığı "
                    f"dışında: {self.ad.zaman(k.gun, k.saat)}",
                    k.ders_atama_id,
                )

        for tanim in g.kisitlar:
            try:
                kural_olustur(tanim)
            except GirdiHatasi as hata:
                sorunlar.append(Celiski("gecersiz_kisit", str(hata), (tanim.tur,)))
        return sorunlar

    def _aralikta(self, gun: int, saat: int) -> bool:
        return 0 <= gun < self.gun_sayisi and 0 <= saat < self.saat_sayisi

    # --- kapasite ----------------------------------------------------------------------

    def ogretmensiz_atama(self) -> list[Celiski]:
        return [
            Celiski("ogretmen_secilmemis", f"{self.ad.atama(a)} dersine öğretmen seçilmemiş.", (a.id, a.sinif_id))
            for a in self.girdi.atamalar
            if a.ogretmen_id is None
        ]

    def sinif_kapasitesi(self) -> list[Celiski]:
        return [
            Celiski("sinif_kapasitesi", self.yuk.sinif_mesaji(y), (y.sinif_id, *y.atama_idleri))
            for y in self.yuk.sinif_yukleri()
            if y.asim
        ]

    def ogretmen_kapasitesi(self) -> list[Celiski]:
        return [
            Celiski("ogretmen_kapasitesi", self.yuk.ogretmen_mesaji(y), (y.ogretmen_id, *y.atama_idleri))
            for y in self.yuk.ogretmen_yukleri()
            if y.asim
        ]

    def ders_gun_kapasitesi(self) -> list[Celiski]:
        """Bir ders bir sınıfa günde en fazla n saat konabilir; öğretmenin müsait günleri de sınırlar."""
        sorunlar = []
        for (sinif_id, ders_id), atamalar in self._gruplar(lambda a: (a.sinif_id, a.ders_id)).items():
            toplam = sum(a.haftalik_saat for a in atamalar)
            ogretmenler = {a.ogretmen_id for a in atamalar}
            if None in ogretmenler:
                gunluk = [self.n] * self.gun_sayisi
            else:
                gunluk = [
                    min(self.n, sum(min(self._musait_saat(o)[g], self.m) for o in ogretmenler))
                    for g in range(self.gun_sayisi)
                ]
            kapasite = sum(gunluk)
            if toplam <= kapasite:
                continue
            uygun_gun = sum(1 for k in gunluk if k > 0)
            neden = f"bir ders bir sınıfa günde en fazla {self.n} saat konabildiği"
            if uygun_gun < self.gun_sayisi:
                kim = ", ".join(sorted(self.ad.ogretmen(o) for o in ogretmenler if o is not None))
                neden += f" ve {kim} yalnızca {uygun_gun} gün müsait olduğu"
            sorunlar.append(Celiski(
                "ders_gun_kapasitesi",
                f"{self.ad.sinif_ders(sinif_id, ders_id)} haftada {toplam} saat, ama {neden} için "
                f"en fazla {kapasite} saat yerleşebilir.",
                (sinif_id, *(a.id for a in atamalar)),
            ))
        return sorunlar

    def sinif_musaitligi(self, onceki: list[Celiski]) -> list[Celiski]:
        """Sınıfın dersleri, öğretmenlerinin müsait saatlerine sığıyor mu?

        Tek sınıf için kesin bir gerekli koşul: öğretmenlerin başka sınıflardaki dersleri hesaba
        katılmaz, yani bu kontrol hiçbir zaman yanlış alarm vermez. İki aşama:
        1. Sayım: öğretmenlerinden en az birinin gelebildiği saat sayısı < ders saati mi?
           Kimsenin gelemediği saatler adıyla söylenir.
        2. Akış: her ders yalnızca kendi öğretmeninin müsait saatlerine ve günde en fazla n saat
           yerleşebilir; her saate en fazla bir ders. Yerleşebilen en fazla saat (max-flow) < ders
           saati mi? (Ör. iki öğretmen yalnızca aynı birkaç saatte müsaitse.)
        Daha önce başka bir kontrolün raporladığı sınıflar atlanır (aynı sorun iki kez söylenmesin).
        """
        raporlanan = {i for c in onceki for i in c.ilgili}
        sorunlar = []
        for sinif_id, atamalar in self._gruplar(lambda a: a.sinif_id).items():
            if sinif_id in raporlanan or any(a.ogretmen_id is None for a in atamalar):
                continue
            ders_saati = sum(a.haftalik_saat for a in atamalar)
            ogretmenler = {a.ogretmen_id for a in atamalar}
            hucreler = [(g, s) for g in range(self.gun_sayisi) for s in range(self.saat_sayisi)]
            kimse_yok = [h for h in hucreler if all((o, *h) in self._gelemez for o in ogretmenler)]
            ilgili = (sinif_id, *sorted(ogretmenler))
            ad = self.ad.sinif(sinif_id)
            if ders_saati > len(hucreler) - len(kimse_yok):
                zamanlar = [self.ad.zaman(g, s) for g, s in kimse_yok]
                liste = ", ".join(zamanlar[:5]) + (f" ve {len(zamanlar) - 5} saat daha" if len(zamanlar) > 5 else "")
                sorunlar.append(Celiski(
                    "sinif_musaitligi",
                    f"{iyelik(ad)} haftada {ders_saati} saat dersi var, ama öğretmenlerinden en az birinin "
                    f"gelebildiği yalnızca {len(hucreler) - len(kimse_yok)} saat var. Şu saatlerde "
                    f"öğretmenlerinin hiçbiri gelemiyor: {liste}.",
                    ilgili,
                ))
                continue
            yerlesebilir = self._en_fazla_yerlesim(atamalar)
            if yerlesebilir < ders_saati:
                sorunlar.append(Celiski(
                    "sinif_musaitligi",
                    f"{iyelik(ad)} haftada {ders_saati} saat dersi var, ama öğretmenlerinin müsait "
                    f"saatleri ve bir dersin günde en fazla {self.n} saat olabilmesi kuralıyla en fazla "
                    f"{yerlesebilir} saati yerleşebilir. Bazı öğretmenleri yalnızca aynı saatlerde "
                    f"müsait olabilir.",
                    ilgili,
                ))
        return sorunlar

    def _en_fazla_yerlesim(self, atamalar: list[DersAtama]) -> int:
        """Ağ akışı: kaynak -> ders (haftalık saat) -> (ders, gün) (n) -> saat (1) -> hedef.

        Kenar kapasiteleri küçük ve ağ küçük (bir sınıf), basit artırım yolu (BFS) yeterli.
        """
        kapasite: dict[tuple, dict[tuple, int]] = defaultdict(lambda: defaultdict(int))
        kaynak, hedef = ("kaynak",), ("hedef",)
        for a in atamalar:
            kapasite[kaynak][("ders", a.id)] += a.haftalik_saat
            for g in range(self.gun_sayisi):
                kapasite[("ders", a.id)][("gun", a.id, g)] += self.n
                for s in range(self.saat_sayisi):
                    if (a.ogretmen_id, g, s) not in self._gelemez:
                        kapasite[("gun", a.id, g)][("saat", g, s)] = 1
                        kapasite[("saat", g, s)][hedef] = 1
        akis = 0
        while True:
            onceki: dict[tuple, tuple] = {kaynak: kaynak}
            kuyruk = [kaynak]
            while kuyruk and hedef not in onceki:
                dugum = kuyruk.pop(0)
                for komsu, kalan in kapasite[dugum].items():
                    if kalan > 0 and komsu not in onceki:
                        onceki[komsu] = dugum
                        kuyruk.append(komsu)
            if hedef not in onceki:
                return akis
            # Yol üzerindeki en küçük kapasite kadar akış gönder (ters kenarları da güncelle).
            yol, dugum = [], hedef
            while dugum != kaynak:
                yol.append((onceki[dugum], dugum))
                dugum = onceki[dugum]
            miktar = min(kapasite[u][v] for u, v in yol)
            for u, v in yol:
                kapasite[u][v] -= miktar
                kapasite[v][u] += miktar
            akis += miktar

    # --- kilitler ------------------------------------------------------------------------

    def kilitler(self) -> list[Celiski]:
        sorunlar: list[Celiski] = []

        def ekle(mesaj: str, *ilgili: str) -> None:
            sorunlar.append(Celiski("kilit_celiskisi", mesaj, tuple(ilgili)))

        kilitler = sorted({(k.ders_atama_id, k.gun, k.saat) for k in self.girdi.kilitli_yerlesimler})
        gelemez = {
            (mu.ogretmen_id, mu.gun, mu.saat)
            for mu in self.girdi.musaitlikler
            if mu.durum is MusaitlikDurumu.GELEMEZ
        }
        sinif_hucre: dict[tuple[str, int, int], list[DersAtama]] = defaultdict(list)
        ogretmen_hucre: dict[tuple[str, int, int], list[DersAtama]] = defaultdict(list)
        atama_sayisi: Counter[str] = Counter()
        ders_gun: Counter[tuple[str, str, int]] = Counter()
        ogretmen_gun: Counter[tuple[str, int]] = Counter()

        for atama_id, g, s in kilitler:
            a = self.atama[atama_id]
            if a.ogretmen_id is not None and (a.ogretmen_id, g, s) in gelemez:
                ekle(
                    f"{self.ad.atama(a)} {self.ad.zaman(g, s)}te kilitli, ama "
                    f"{self.ad.ogretmen(a.ogretmen_id)} o saatte gelemez.",
                    a.id, a.ogretmen_id,
                )
            sinif_hucre[a.sinif_id, g, s].append(a)
            if a.ogretmen_id is not None:
                ogretmen_hucre[a.ogretmen_id, g, s].append(a)
                ogretmen_gun[a.ogretmen_id, g] += 1
            atama_sayisi[a.id] += 1
            ders_gun[a.sinif_id, a.ders_id, g] += 1

        for (sinif_id, g, s), liste in sinif_hucre.items():
            if len(liste) > 1:
                dersler = ", ".join(self.ad.ders(a.ders_id) for a in liste)
                ekle(
                    f"{self.ad.sinif(sinif_id)} sınıfında {self.ad.zaman(g, s)}e birden fazla ders "
                    f"kilitli: {dersler}.",
                    sinif_id, *(a.id for a in liste),
                )
        for (ogretmen_id, g, s), liste in ogretmen_hucre.items():
            if len(liste) > 1:
                dersler = ", ".join(self.ad.atama(a) for a in liste)
                ekle(
                    f"{self.ad.ogretmen(ogretmen_id)} {self.ad.zaman(g, s)}te birden fazla sınıfa "
                    f"kilitli: {dersler}.",
                    ogretmen_id, *(a.id for a in liste),
                )
        for atama_id, adet in atama_sayisi.items():
            a = self.atama[atama_id]
            if adet > a.haftalik_saat:
                ekle(
                    f"{self.ad.atama(a)} için {adet} kilitli hücre var, ama dersin haftada "
                    f"{a.haftalik_saat} saati var.",
                    a.id,
                )
        for (sinif_id, ders_id, g), adet in ders_gun.items():
            if adet > self.n:
                ekle(
                    f"{self.ad.sinif_ders(sinif_id, ders_id)} {self.ad.gun(g)} gününe {adet} saat "
                    f"kilitli, ama bir ders bir sınıfa günde en fazla {self.n} saat konabilir.",
                    sinif_id,
                )
        for (ogretmen_id, g), adet in ogretmen_gun.items():
            if adet > self.m:
                ekle(
                    f"{self.ad.ogretmen(ogretmen_id)} {self.ad.gun(g)} günü {adet} saate kilitli, "
                    f"ama bir öğretmen günde en fazla {self.m} saat derse girebilir.",
                    ogretmen_id,
                )
        return sorunlar

    # --- yardımcılar -------------------------------------------------------------------

    def _gruplar(self, anahtar) -> dict:
        gruplar: dict = defaultdict(list)
        for a in self.girdi.atamalar:
            gruplar[anahtar(a)].append(a)
        return gruplar

    def _musait_saat(self, ogretmen_id: str) -> list[int]:
        return self.yuk.musait_saat(ogretmen_id)
