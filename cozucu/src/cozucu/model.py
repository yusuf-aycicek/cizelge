"""Çözücünün girdi ve çıktı veri yapıları.

Bunlar veritabanı tablolarının birebir kopyası değil, çözücünün ihtiyaç duyduğu düz verilerdir.
`okul_id` yoktur: çözücü her zaman tek bir okulun verisiyle çalışır, izolasyon üst katmanın işidir.
Kimlikler (id) metindir; veritabanındaki uuid'ler metin olarak geçirilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    gun_sayisi: int
    gunluk_ders_saati: int

    def __post_init__(self) -> None:
        if not 1 <= self.gun_sayisi <= 7:
            raise ValueError(f"gun_sayisi 1-7 arasında olmalı: {self.gun_sayisi}")
        if self.gunluk_ders_saati < 1:
            raise ValueError(f"gunluk_ders_saati en az 1 olmalı: {self.gunluk_ders_saati}")

    @property
    def haftalik_kapasite(self) -> int:
        return self.gun_sayisi * self.gunluk_ders_saati


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
    """Okul geneli bir kural. `tur`, kısıt kayıt defterindeki sınıfı seçer."""

    tur: str
    parametreler: dict[str, Any] = field(default_factory=dict, hash=False)
    zorunlu: bool = True
    agirlik: int = 1


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


@dataclass
class CozumSonucu:
    durum: CozumDurumu
    yerlesimler: list[Yerlesim] = field(default_factory=list)
    toplam_ceza: int | None = None
    mesajlar: list[str] = field(default_factory=list)
    sure_sn: float = 0.0

    @property
    def basarili(self) -> bool:
        return self.durum in (CozumDurumu.OPTIMAL, CozumDurumu.UYGUN)
