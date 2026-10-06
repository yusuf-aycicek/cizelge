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
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    Celiski,
    CozumGirdisi,
    DersAtama,
    MusaitlikDurumu,
)


def on_kontrol(girdi: CozumGirdisi) -> list[Celiski]:
    """Boş liste = ön kontrolden geçti (çözüm olduğu garanti değildir)."""
    kontrol = _Kontrol(girdi)
    sorunlar = kontrol.tutarlilik()
    if sorunlar:
        return sorunlar
    return (
        kontrol.ogretmensiz_atama()
        + kontrol.sinif_kapasitesi()
        + kontrol.ogretmen_kapasitesi()
        + kontrol.ders_gun_kapasitesi()
        + kontrol.kilitler()
    )


class _Kontrol:
    def __init__(self, girdi: CozumGirdisi) -> None:
        self.girdi = girdi
        self.ad = Anlatim(girdi)
        self.gun_sayisi = girdi.ayar.gun_sayisi
        self.saat_sayisi = girdi.ayar.gunluk_ders_saati
        n = girdi.zorunlu_parametre(GUNLUK_DERS_SINIRI_TURU, "n", VARSAYILAN_GUNLUK_DERS_SINIRI)
        m = girdi.zorunlu_parametre(OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI)
        # Esnek tanımlanmış sınır zorunlu kontrol gerektirmez: gün uzunluğu kadar kabul edilir.
        self.n = n if n is not None else self.saat_sayisi
        self.m = min(m if m is not None else self.saat_sayisi, self.saat_sayisi)
        self.atama = {a.id: a for a in girdi.atamalar}
        # Öğretmen -> her gün için gelemez olmadığı saat sayısı (aynı hücre iki kez sayılmaz).
        gelemez_hucreler = {
            (mu.ogretmen_id, mu.gun, mu.saat)
            for mu in girdi.musaitlikler
            if mu.durum is MusaitlikDurumu.GELEMEZ
        }
        gelemez_gunluk = Counter((o, g) for o, g, _s in gelemez_hucreler)
        self._musait = {
            o: [self.saat_sayisi - gelemez_gunluk[o, g] for g in range(self.gun_sayisi)]
            for o in {o for o, _g, _s in gelemez_hucreler}
        }

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
        kapasite = self.girdi.ayar.haftalik_kapasite
        sorunlar = []
        for sinif_id, atamalar in self._gruplar(lambda a: a.sinif_id).items():
            yuk = sum(a.haftalik_saat for a in atamalar)
            if yuk > kapasite:
                sorunlar.append(Celiski(
                    "sinif_kapasitesi",
                    f"{self.ad.sinif(sinif_id)} sınıfının haftada {yuk} saat dersi var, haftalık "
                    f"kapasite {kapasite} saat ({self.gun_sayisi} gün × {self.saat_sayisi} saat).",
                    (sinif_id, *(a.id for a in atamalar)),
                ))
        return sorunlar

    def ogretmen_kapasitesi(self) -> list[Celiski]:
        sorunlar = []
        for ogretmen_id, atamalar in self._gruplar(lambda a: a.ogretmen_id).items():
            if ogretmen_id is None:
                continue
            yuk = sum(a.haftalik_saat for a in atamalar)
            musait = self._musait_saat(ogretmen_id)
            kullanilabilir = sum(min(s, self.m) for s in musait)
            if yuk <= kullanilabilir:
                continue
            ad = iyelik(self.ad.ogretmen(ogretmen_id))
            if kullanilabilir == sum(musait):
                mesaj = f"{ad} {yuk} saat dersi var, müsait olduğu {kullanilabilir} saat var."
            else:
                mesaj = (
                    f"{ad} {yuk} saat dersi var. Müsait olduğu {sum(musait)} saatin, günde en fazla "
                    f"{self.m} saat derse girebildiği için yalnızca {kullanilabilir} saati kullanılabilir."
                )
            sorunlar.append(Celiski("ogretmen_kapasitesi", mesaj, (ogretmen_id, *(a.id for a in atamalar))))
        return sorunlar

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
        """Her gün için öğretmenin gelemez olmadığı saat sayısı."""
        return self._musait.get(ogretmen_id, [self.saat_sayisi] * self.gun_sayisi)
