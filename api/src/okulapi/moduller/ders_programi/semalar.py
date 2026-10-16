"""Ders programı modülünün API şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Yanit(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- seviye şablonu ------------------------------------------------------------------


class SeviyeSablonuOlustur(BaseModel):
    seviye: int = Field(ge=1, le=12)
    ders_id: uuid.UUID
    haftalik_saat: int = Field(ge=1)


class SeviyeSablonuGuncelle(BaseModel):
    haftalik_saat: int | None = Field(default=None, ge=1)


class SeviyeSablonuYanit(_Yanit):
    id: uuid.UUID
    seviye: int
    ders_id: uuid.UUID
    haftalik_saat: int


class SablonUygula(BaseModel):
    seviye: int = Field(ge=1, le=12)


class FarkliSaat(BaseModel):
    atama_id: uuid.UUID
    sinif: str
    ders: str
    atamadaki_saat: int
    sablondaki_saat: int


class SablonUygulamaSonucu(BaseModel):
    """Şablon uygulandı: oluşturulan atamalar, zaten var olanlar, saati şablondan farklı olanlar."""

    sube_sayisi: int
    olusturulan: int
    zaten_var: int
    farkli_saatli: list[FarkliSaat]


# --- ders atama -------------------------------------------------------------------------


class DersAtamaOlustur(BaseModel):
    sinif_id: uuid.UUID
    ders_id: uuid.UUID
    ogretmen_id: uuid.UUID | None = None
    haftalik_saat: int = Field(ge=1)


class DersAtamaGuncelle(BaseModel):
    """Sınıf ve ders değiştirilemez: (sınıf, ders) atamanın kimliğidir. Başka bir sınıf/ders için
    yeni atama oluşturulur. `ogretmen_id: null` göndermek öğretmeni boşaltır."""

    ogretmen_id: uuid.UUID | None = None
    haftalik_saat: int | None = Field(default=None, ge=1)


class DersAtamaYanit(_Yanit):
    id: uuid.UUID
    sinif_id: uuid.UUID
    ders_id: uuid.UUID
    ogretmen_id: uuid.UUID | None
    haftalik_saat: int


# --- müsaitlik ----------------------------------------------------------------------------


class MusaitlikOlustur(BaseModel):
    ogretmen_id: uuid.UUID
    gun: int = Field(ge=0, le=6, description="0 = pazartesi")
    saat: int = Field(ge=0, le=15, description="0 = ilk ders")
    durum: Literal["gelemez", "tercih_etmez"]


class MusaitlikGuncelle(BaseModel):
    durum: Literal["gelemez", "tercih_etmez"] | None = None


class MusaitlikYanit(_Yanit):
    id: uuid.UUID
    ogretmen_id: uuid.UUID
    gun: int
    saat: int
    durum: str


# --- kısıt --------------------------------------------------------------------------------


class KisitOlustur(BaseModel):
    tur: str = Field(min_length=1, max_length=50)
    parametreler: dict[str, Any] = Field(default_factory=dict)
    zorunlu: bool = True
    agirlik: int = Field(default=1, ge=0)


class KisitGuncelle(BaseModel):
    parametreler: dict[str, Any] | None = None
    zorunlu: bool | None = None
    agirlik: int | None = Field(default=None, ge=0)


class KisitYanit(_Yanit):
    id: uuid.UUID
    tur: str
    parametreler: dict[str, Any]
    zorunlu: bool
    agirlik: int


# --- kurallar (okul geneli kısıtlar, kullanıcının diliyle) --------------------------------


OnemSeviyesi = Literal["onemsiz", "onemli", "cok_onemli"]


class KuralYanit(BaseModel):
    tur: str
    ad: str
    aciklama: str
    zorunlu: bool
    parametreler: dict[str, int]
    varsayilan_parametreler: dict[str, int]
    # Yalnızca esnek kurallarda: sayısal ağırlık ve karşılık gelen önem seviyesi ("ozel": hiçbir
    # seviyeye denk gelmeyen, elle girilmiş ağırlık).
    agirlik: int | None
    seviye: Literal["onemsiz", "onemli", "cok_onemli", "ozel"] | None
    varsayilan_seviye: OnemSeviyesi | None
    varsayilan: bool


class KuralAyari(BaseModel):
    parametreler: dict[str, int] | None = None
    seviye: OnemSeviyesi | None = None


# --- program -----------------------------------------------------------------------------


class ProgramUret(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    # Doluysa en az değişiklikle güncelleme; o programın kilitli hücreleri de korunur.
    temel_program_id: uuid.UUID | None = None
    # Çözücü süre sınırı. Varsayılan 120 sn (docs/olcumler.md).
    sure_siniri_sn: int = Field(default=120, ge=5, le=3600)


class ProgramYanit(_Yanit):
    id: uuid.UUID
    ad: str
    durum: str
    hata_mesaji: str | None
    temel_program_id: uuid.UUID | None
    sure_siniri_sn: int
    olusturma: datetime
    baslama: datetime | None
    bitis: datetime | None
    # Üretim sonucu (üretim bitince dolar). girdi_ozeti iç bilgidir, dışarı verilmez.
    cozum_durumu: str | None
    toplam_ceza: int | None
    olcumler: dict[str, int] | None
    celiskiler: list[dict[str, Any]] | None
    sure_sn: float | None


class YerlesimYanit(_Yanit):
    id: uuid.UUID
    ders_atama_id: uuid.UUID
    gun: int
    saat: int
    kilitli: bool
