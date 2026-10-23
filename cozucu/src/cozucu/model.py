"""Çözücünün girdi ve çıktı veri yapıları.

Bunlar veritabanı tablolarının birebir kopyası değil, çözücünün ihtiyaç duyduğu düz verilerdir.
`okul_id` yoktur: çözücü her zaman tek bir okulun verisiyle çalışır, izolasyon üst katmanın işidir.
Kimlikler (id) metindir; veritabanındaki uuid'ler metin olarak geçirilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cozucu.kapsam import OKUL, Kapsam, Varlik, cozumle

# Aynı ders bir sınıfa günde en fazla kaç saat konur (kisit tablosunda yoksa).
VARSAYILAN_GUNLUK_DERS_SINIRI = 2
GUNLUK_DERS_SINIRI_TURU = "gunluk_ders_siniri"
# Bir öğretmen günde en fazla kaç saat derse girer (kisit tablosunda yoksa).
VARSAYILAN_OGRETMEN_GUNLUK_SINIRI = 8
OGRETMEN_GUNLUK_SINIRI_TURU = "ogretmen_gunluk_siniri"
# Her öğretmene hedeflenen boş gün sayısı (kisit tablosunda yoksa).
VARSAYILAN_HEDEF_BOS_GUN = 1
BOS_GUN_TURU = "bos_gun"


class MusaitlikDurumu(str, Enum):
    GELEMEZ = "gelemez"  # zorunlu: bu saate ders konamaz
    TERCIH_ETMEZ = "tercih_etmez"  # esnek: konursa ceza puanı


class CozumDurumu(str, Enum):
    OPTIMAL = "optimal"  # en iyi çözüm kanıtlandı
    UYGUN = "uygun"  # geçerli çözüm bulundu, süre dolduğu için en iyisi kanıtlanamadı
    COZUMSUZ = "cozumsuz"  # zorunlu kısıtların hepsini sağlayan çözüm yok
    ON_KONTROL_HATASI = "on_kontrol_hatasi"  # veri çözücüye verilemeyecek durumda
    BILINMIYOR = "bilinmiyor"  # süre içinde ne çözüm ne de çözümsüzlük kanıtı bulundu


def _negatif_olmasin(ad: str, deger: int) -> None:
    if deger < 0:
        raise ValueError(f"{ad} negatif olamaz: {deger}")


@dataclass(frozen=True)
class OkulAyari:
    """Okulun haftası.

    `gunluk_ders_saati` en uzun gündür: çizelgenin satır sayısı ve günlük sınırların tavanı.
    `gun_saatleri` günlere göre farklı ders saati sayısıdır (ör. cuma 7); boşsa her gün
    `gunluk_ders_saati`. Günün uzunluğunun dışındaki saatler o gün yoktur.
    `ogle_arasi_sonra`: öğle arası kaçıncı dersten sonra (ör. 4: 4. ile 5. ders arası); boşsa
    yok. O günün dersi bu sayıdan fazla değilse o gün öğle arası yoktur.
    """

    gun_sayisi: int
    gunluk_ders_saati: int
    gun_saatleri: tuple[int, ...] = ()
    ogle_arasi_sonra: int | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.gun_sayisi <= 7:
            raise ValueError(f"gun_sayisi 1-7 arasında olmalı: {self.gun_sayisi}")
        if self.gunluk_ders_saati < 1:
            raise ValueError(f"gunluk_ders_saati en az 1 olmalı: {self.gunluk_ders_saati}")
        # JSON'dan liste gelir; değişmez ve karşılaştırılabilir olsun diye demete çevrilir.
        object.__setattr__(self, "gun_saatleri", tuple(self.gun_saatleri))
        if self.gun_saatleri:
            if len(self.gun_saatleri) != self.gun_sayisi:
                raise ValueError(f"gun_saatleri {self.gun_sayisi} gün için olmalı: {self.gun_saatleri}")
            if not all(1 <= s <= self.gunluk_ders_saati for s in self.gun_saatleri):
                raise ValueError(f"gun_saatleri 1-{self.gunluk_ders_saati} arasında olmalı: {self.gun_saatleri}")
        if self.ogle_arasi_sonra is not None and not 1 <= self.ogle_arasi_sonra < self.gunluk_ders_saati:
            raise ValueError(f"ogle_arasi_sonra 1-{self.gunluk_ders_saati - 1} arasında olmalı: {self.ogle_arasi_sonra}")

    def saat_sayisi(self, gun: int) -> int:
        """O günün ders saati sayısı."""
        return self.gun_saatleri[gun] if self.gun_saatleri else self.gunluk_ders_saati

    @property
    def gunluk_saatler(self) -> tuple[int, ...]:
        return tuple(self.saat_sayisi(g) for g in range(self.gun_sayisi))

    @property
    def gunlere_gore_farkli(self) -> bool:
        return len(set(self.gunluk_saatler)) > 1

    def aralikta(self, gun: int, saat: int) -> bool:
        """Bu hücre okulun haftasında var mı (gün kısaysa sonundaki saatler yoktur)."""
        return 0 <= gun < self.gun_sayisi and 0 <= saat < self.saat_sayisi(gun)

    def ogle_arasiyla_ayrilir(self, gun: int, saat: int) -> bool:
        """`saat` ile `saat + 1` arasında o gün öğle arası var mı."""
        return (
            self.ogle_arasi_sonra is not None
            and saat + 1 == self.ogle_arasi_sonra
            and saat + 1 < self.saat_sayisi(gun)
        )

    @property
    def haftalik_kapasite(self) -> int:
        return sum(self.gunluk_saatler)


@dataclass(frozen=True)
class Ogretmen:
    id: str
    ad: str
    brans: str = ""


@dataclass(frozen=True)
class Sinif:
    id: str
    ad: str
    seviye: int
    sube_grubu_id: str | None = None  # "11 Sayısal" gibi; şube grubu kapsamlı ayarlar için


@dataclass(frozen=True)
class Ders:
    id: str
    ad: str
    kisa_ad: str = ""


@dataclass(frozen=True)
class DersAtama:
    """Bir sınıfa bir dersin haftada kaç saat, hangi öğretmenle verileceği.

    ogretmen_id boş olabilir (henüz seçilmemiş); ön kontrol bunu yakalar.
    """

    id: str
    sinif_id: str
    ders_id: str
    ogretmen_id: str | None
    haftalik_saat: int

    def __post_init__(self) -> None:
        if self.haftalik_saat < 1:
            raise ValueError(f"haftalik_saat en az 1 olmalı: {self.haftalik_saat}")


@dataclass(frozen=True)
class Musaitlik:
    ogretmen_id: str
    gun: int
    saat: int
    durum: MusaitlikDurumu

    def __post_init__(self) -> None:
        _negatif_olmasin("gun", self.gun)
        _negatif_olmasin("saat", self.saat)


@dataclass(frozen=True)
class KisitTanimi:
    """Bir kural tanımı. `tur`, kısıt kayıt defterindeki sınıfı seçer.

    `kapsam` boşsa okul genelidir; doluysa okul değerini o kapsamda ezen bir **özel ayardır**
    (ADR 0016). Kip (`zorunlu`) ve `agirlik` her zaman okul geneli tanımdan gelir; özel ayar
    yalnızca parametreleri değiştirir.
    """

    tur: str
    parametreler: dict[str, Any] = field(default_factory=dict, hash=False)
    zorunlu: bool = True
    agirlik: int = 1
    kapsam: Kapsam = OKUL


@dataclass(frozen=True)
class Yerlesim:
    """Programın bir hücresi: bu atama bu gün bu saatte."""

    ders_atama_id: str
    gun: int
    saat: int
    kilitli: bool = False

    def __post_init__(self) -> None:
        _negatif_olmasin("gun", self.gun)
        _negatif_olmasin("saat", self.saat)


@dataclass(frozen=True)
class TemelYerlesim:
    """Temel programın bir hücresi: bu sınıfa bu ders bu gün bu saatte.

    Atama kimliğiyle değil (sınıf, ders) ile tutulur. Öğretmeni değişen ya da silinip yeniden
    oluşturulan atama da "aynı ders" sayılır. Sistem "bir sınıf, bir ders, bir öğretmen"
    modelinde olduğu için (sınıf, ders) bir atamayı tek başına belirler.
    """

    sinif_id: str
    ders_id: str
    gun: int
    saat: int


def temel_program(atamalar: list[DersAtama], yerlesimler: list[Yerlesim]) -> list[TemelYerlesim]:
    """Bir çözümün yerleşimlerini, sonraki güncellemede temel alınacak biçime çevirir."""
    atama = {a.id: a for a in atamalar}
    return [
        TemelYerlesim(atama[y.ders_atama_id].sinif_id, atama[y.ders_atama_id].ders_id, y.gun, y.saat)
        for y in yerlesimler
        if y.ders_atama_id in atama
    ]


@dataclass
class CozumGirdisi:
    ayar: OkulAyari
    ogretmenler: list[Ogretmen] = field(default_factory=list)
    siniflar: list[Sinif] = field(default_factory=list)
    dersler: list[Ders] = field(default_factory=list)
    atamalar: list[DersAtama] = field(default_factory=list)
    musaitlikler: list[Musaitlik] = field(default_factory=list)
    kisitlar: list[KisitTanimi] = field(default_factory=list)
    kilitli_yerlesimler: list[Yerlesim] = field(default_factory=list)
    # İsteğe bağlı: en az değişiklikle güncellemede temel alınan program (bkz. docs/adr/0006).
    temel_yerlesimler: list[TemelYerlesim] = field(default_factory=list)

    def varlik(
        self, *, sinif_id: str | None = None, ders_id: str | None = None, ogretmen_id: str | None = None
    ) -> Varlik:
        """Kapsam çözümlemesi için varlık; şubenin grubu şube listesinden bulunur."""
        grup = next((s.sube_grubu_id for s in self.siniflar if s.id == sinif_id), None) if sinif_id else None
        return Varlik(ders_id=ders_id, sinif_id=sinif_id, sube_grubu_id=grup, ogretmen_id=ogretmen_id)

    def _okul_tanimi(self, tur: str) -> KisitTanimi | None:
        okul = None
        for tanim in self.kisitlar:
            if tanim.tur == tur and tanim.kapsam.okul_mu:
                okul = tanim
        return okul

    def parametre(self, tur: str, ad: str, varsayilan: int, **varlik: str | None) -> int:
        """Bir kuralın parametresi (kip fark etmeksizin).

        Varlık verilirse (`sinif_id=`, `ders_id=`, `ogretmen_id=`) ona uyan en özel ayar kazanır
        (`cozucu.kapsam.cozumle`); yoksa okul geneli tanım, o da yoksa varsayılan. Özel ayarda
        olmayan parametre, kural sınıfının kurucusundaki gibi varsayılanı alır.
        """
        okul = self._okul_tanimi(tur)
        deger = okul.parametreler.get(ad, varsayilan) if okul else varsayilan
        if varlik:
            ozeller = [t for t in self.kisitlar if t.tur == tur and not t.kapsam.okul_mu]
            ozel = cozumle(ozeller, self.varlik(**varlik))
            if ozel is not None:
                deger = ozel.parametreler.get(ad, varsayilan)
        return deger

    def zorunlu_parametre(self, tur: str, ad: str, varsayilan: int, **varlik: str | None) -> int | None:
        """Bir kuralın zorunlu kipteki parametresi (varlık için `parametre` gibi çözümlenir).

        Kural okul genelinde esnek tanımlanmışsa None (zorunlu değil): kip okul tanımından gelir.
        """
        okul = self._okul_tanimi(tur)
        if okul is not None and not okul.zorunlu:
            return None
        return self.parametre(tur, ad, varsayilan, **varlik)


@dataclass(frozen=True)
class Celiski:
    """Programın üretilmesini engelleyen bir sorun, kullanıcının diliyle.

    `ilgili`: sorunla ilgili öğretmen / sınıf / atama kimlikleri. Arayüz bunlarla ilgili
    satırları ve hücreleri vurgulayabilir.
    """

    tur: str
    mesaj: str
    ilgili: tuple[str, ...] = ()


@dataclass
class CozumSonucu:
    durum: CozumDurumu
    yerlesimler: list[Yerlesim] = field(default_factory=list)
    toplam_ceza: int | None = None
    mesajlar: list[str] = field(default_factory=list)  # genel bilgi (ör. süre doldu)
    sure_sn: float = 0.0
    celiskiler: list[Celiski] = field(default_factory=list)  # çözüm yoksa nedenleri

    @property
    def basarili(self) -> bool:
        return self.durum in (CozumDurumu.OPTIMAL, CozumDurumu.UYGUN)
