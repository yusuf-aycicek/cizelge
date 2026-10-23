"""Öğretmen ve sınıf yükü: haftalık ders saatinin kapasiteyle karşılaştırılması.

Bu hesabın tek kaynağı burasıdır (ADR 0015). İki kullanıcısı vardır:
- ön kontrol (`on_kontrol.py`): kapasiteyi aşan öğretmen ve sınıf için program üretilmez;
- API'nin ders dağılımı özeti: arayüz, veri girilirken aynı sonucu erken uyarı olarak gösterir.

Kurallar:
- Öğretmenin bir gündeki müsait saati: okulun günlük ders saati eksi o gün "gelemez" işaretli
  saatleri. "Tercih etmez" saatler müsait sayılır (esnek kural).
- Kullanılabilir saat: her gün için müsait saat ile öğretmenin günlük ders sınırının (M) küçüğü,
  haftalık toplamı. M zorunlu değilse (esnek tanımlanmışsa) günlük ders saati kadar kabul edilir.
  M öğretmene, N derse ya da şubeye özel olabilir (ADR 0016): her varlık kendi değeriyle sayılır.
- Sınıfın kapasitesi: gün sayısı × günlük ders saati.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from cozucu.anlatim import Anlatim, iyelik
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    CozumGirdisi,
    DersAtama,
    MusaitlikDurumu,
)


@dataclass(frozen=True)
class OgretmenYuku:
    ogretmen_id: str
    ders_saati: int  # atamalarının haftalık saatleri toplamı
    musait_saat: int  # haftada "gelemez" olmadığı saat sayısı
    kullanilabilir_saat: int  # günlük ders sınırıyla birlikte derse girebileceği en fazla saat
    atama_idleri: tuple[str, ...] = ()

    @property
    def asim(self) -> bool:
        return self.ders_saati > self.kullanilabilir_saat


@dataclass(frozen=True)
class SinifYuku:
    sinif_id: str
    ders_saati: int
    kapasite: int  # haftalık kapasite: gün sayısı × günlük ders saati
    ogretmensiz_atama: int  # öğretmeni seçilmemiş atama sayısı
    atama_idleri: tuple[str, ...] = ()

    @property
    def asim(self) -> bool:
        return self.ders_saati > self.kapasite


class YukHesabi:
    """Bir okulun girdisi için günlük sınırlar, müsait saatler ve yükler."""

    def __init__(self, girdi: CozumGirdisi) -> None:
        self.girdi = girdi
        self.ad = Anlatim(girdi)
        self.gun_sayisi = girdi.ayar.gun_sayisi
        self.saat_sayisi = girdi.ayar.gunluk_ders_saati
        n = girdi.zorunlu_parametre(GUNLUK_DERS_SINIRI_TURU, "n", VARSAYILAN_GUNLUK_DERS_SINIRI)
        m = girdi.zorunlu_parametre(OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI)
        # Okul geneli değerler. Esnek tanımlanmış sınır zorunlu kontrol gerektirmez: gün uzunluğu
        # kadar kabul edilir. Varlığa özel değer için `ders_siniri` ve `ogretmen_siniri`.
        self.n = n if n is not None else self.saat_sayisi
        self.m = min(m if m is not None else self.saat_sayisi, self.saat_sayisi)
        # Aynı hücre için iki kayıt varsa bir kez sayılır. Okulun aralığı dışındaki kayıt sayılmaz
        # (ön kontrol onu ayrıca tutarsız veri olarak raporlar).
        self.gelemez = {
            (mu.ogretmen_id, mu.gun, mu.saat)
            for mu in girdi.musaitlikler
            if mu.durum is MusaitlikDurumu.GELEMEZ and mu.gun < self.gun_sayisi and mu.saat < self.saat_sayisi
        }
        gelemez_gunluk = Counter((o, g) for o, g, _s in self.gelemez)
        self._musait = {
            o: [self.saat_sayisi - gelemez_gunluk[o, g] for g in range(self.gun_sayisi)]
            for o in {o for o, _g, _s in self.gelemez}
        }

    def ders_siniri(self, sinif_id: str, ders_id: str) -> int:
        """Bu şubeye bu dersin günde en fazla kaç saat konabileceği (özel ayar dahil)."""
        n = self.girdi.zorunlu_parametre(
            GUNLUK_DERS_SINIRI_TURU, "n", VARSAYILAN_GUNLUK_DERS_SINIRI, sinif_id=sinif_id, ders_id=ders_id
        )
        return n if n is not None else self.saat_sayisi

    def ogretmen_siniri(self, ogretmen_id: str | None) -> int:
        """Öğretmenin günde en fazla kaç saat derse girebileceği (özel ayar dahil, gün uzunluğuyla sınırlı)."""
        if ogretmen_id is None:
            return self.m
        m = self.girdi.zorunlu_parametre(
            OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI, ogretmen_id=ogretmen_id
        )
        return min(m if m is not None else self.saat_sayisi, self.saat_sayisi)

    def musait_saat(self, ogretmen_id: str) -> list[int]:
        """Her gün için öğretmenin gelemez olmadığı saat sayısı."""
        return self._musait.get(ogretmen_id, [self.saat_sayisi] * self.gun_sayisi)

    # --- öğretmen ------------------------------------------------------------------------

    def ogretmen_yukleri(self) -> list[OgretmenYuku]:
        """Her öğretmen için bir satır (dersi olmayanlar da, 0 saatle). Sıra: öğretmen listesi,
        ardından listede olmayan ama atamada geçen kimlikler."""
        atamalar = _grupla(self.girdi.atamalar, lambda a: a.ogretmen_id)
        kimlikler = [o.id for o in self.girdi.ogretmenler]
        bilinen = set(kimlikler)
        kimlikler += [o for o in atamalar if o is not None and o not in bilinen]
        return [self._ogretmen_yuku(o, atamalar.get(o, [])) for o in kimlikler]

    def _ogretmen_yuku(self, ogretmen_id: str, atamalar: list[DersAtama]) -> OgretmenYuku:
        musait = self.musait_saat(ogretmen_id)
        m = self.ogretmen_siniri(ogretmen_id)
        return OgretmenYuku(
            ogretmen_id=ogretmen_id,
            ders_saati=sum(a.haftalik_saat for a in atamalar),
            musait_saat=sum(musait),
            kullanilabilir_saat=sum(min(s, m) for s in musait),
            atama_idleri=tuple(a.id for a in atamalar),
        )

    def ogretmen_mesaji(self, yuk: OgretmenYuku) -> str | None:
        """Aşım varsa kullanıcının diliyle açıklama, yoksa None."""
        if not yuk.asim:
            return None
        ad = iyelik(self.ad.ogretmen(yuk.ogretmen_id))
        if yuk.kullanilabilir_saat == yuk.musait_saat:
            return f"{ad} {yuk.ders_saati} saat dersi var, müsait olduğu {yuk.kullanilabilir_saat} saat var."
        return (
            f"{ad} {yuk.ders_saati} saat dersi var. Müsait olduğu {yuk.musait_saat} saatin, günde en "
            f"fazla {self.ogretmen_siniri(yuk.ogretmen_id)} saat derse girebildiği için yalnızca {yuk.kullanilabilir_saat} saati "
            f"kullanılabilir."
        )

    # --- sınıf ---------------------------------------------------------------------------

    def sinif_yukleri(self) -> list[SinifYuku]:
        """Her sınıf için bir satır (dersi olmayanlar da). Sıra: sınıf listesi, ardından listede
        olmayan ama atamada geçen kimlikler."""
        atamalar = _grupla(self.girdi.atamalar, lambda a: a.sinif_id)
        kimlikler = [s.id for s in self.girdi.siniflar]
        bilinen = set(kimlikler)
        kimlikler += [s for s in atamalar if s not in bilinen]
        kapasite = self.girdi.ayar.haftalik_kapasite
        return [
            SinifYuku(
                sinif_id=s,
                ders_saati=sum(a.haftalik_saat for a in atamalar.get(s, [])),
                kapasite=kapasite,
                ogretmensiz_atama=sum(1 for a in atamalar.get(s, []) if a.ogretmen_id is None),
                atama_idleri=tuple(a.id for a in atamalar.get(s, [])),
            )
            for s in kimlikler
        ]

    def sinif_mesaji(self, yuk: SinifYuku) -> str | None:
        if not yuk.asim:
            return None
        return (
            f"{self.ad.sinif(yuk.sinif_id)} sınıfının haftada {yuk.ders_saati} saat dersi var, haftalık "
            f"kapasite {yuk.kapasite} saat ({self.gun_sayisi} gün × {self.saat_sayisi} saat)."
        )


def _grupla(atamalar: list[DersAtama], anahtar) -> dict:
    gruplar: dict = defaultdict(list)
    for a in atamalar:
        gruplar[anahtar(a)].append(a)
    return gruplar
