"""Çıktının veri modeli: veritabanından ve biçimden (PDF, Excel) habersiz düz yapılar.

`veri.py` bunları veritabanından doldurur; `pdf.py` ve `excel.py` yalnızca bunları okur. Böylece
çizim kodu testte elle kurulan bir modelle de çalışır ve iki biçim aynı hücreleri gösterir.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from okulapi.cekirdek.zil import Zil


@dataclass(frozen=True)
class Hucre:
    """Bir ders (blok dersse art arda saatleri tek hücrede, `uzunluk` > 1)."""

    gun: int
    saat: int
    uzunluk: int
    ders: str
    kisa_ad: str
    renk: str  # "#2563eb"
    sube: str
    ogretmen: str  # öğretmeni seçilmemişse boş


@dataclass(frozen=True)
class Cizelge:
    """Bir şubenin ya da bir öğretmenin haftası."""

    ad: str  # "9-A" ya da "Ayşe Yılmaz"
    tur: str  # "sube" | "ogretmen"
    hucreler: list[Hucre]
    kimlik: uuid.UUID | None = None  # şubenin ya da öğretmenin kaydı (tek şube/öğretmen seçimi için)

    @property
    def toplam_saat(self) -> int:
        return sum(h.uzunluk for h in self.hucreler)

    def hucre(self, gun: int, saat: int) -> Hucre | None:
        """Bu saatte başlayan hücre."""
        return next((h for h in self.hucreler if h.gun == gun and h.saat == saat), None)

    def ortulen(self, gun: int, saat: int) -> bool:
        """Bu saat, daha önce başlayan bir blok hücresinin içinde mi."""
        return any(h.gun == gun and h.saat < saat < h.saat + h.uzunluk for h in self.hucreler)


@dataclass(frozen=True)
class Hafta:
    gun_adlari: list[str]
    gun_saatleri: list[int]  # her gün kaç ders saati
    saat_sayisi: int  # en uzun gün (program daha uzunsa program)
    ogle_arasi_sonra: int | None
    zil: list[Zil] | None
    ogle_zili: Zil | None

    def var(self, gun: int, saat: int) -> bool:
        """Bu saat okulun haftasında var mı (kısa günün sonu yoktur)."""
        return saat < self.gun_saatleri[gun] if gun < len(self.gun_saatleri) else False

    def saat_basligi(self, saat: int) -> str:
        z = self.zil[saat] if self.zil and saat < len(self.zil) else None
        return f"{saat + 1}. ders" + (f"\n{z.metin}" if z else "")


@dataclass(frozen=True)
class ProgramCiktisi:
    okul: str
    program: str
    tarih: date
    hafta: Hafta
    subeler: list[Cizelge] = field(default_factory=list)
    ogretmenler: list[Cizelge] = field(default_factory=list)
