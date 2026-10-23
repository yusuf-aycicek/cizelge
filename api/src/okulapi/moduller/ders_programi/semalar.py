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


class TopluOgretmenAta(BaseModel):
    """Aynı öğretmeni birden fazla atamaya tek seferde verir (ör. 9-A, 9-B, 9-C Matematik).
    `ogretmen_id: null` hepsinin öğretmenini boşaltır."""

    atama_idleri: list[uuid.UUID] = Field(min_length=1, max_length=500)
    ogretmen_id: uuid.UUID | None


# --- ders dağılımı özeti (öğretmen ve sınıf yükü) -----------------------------------------


class OgretmenYukuYanit(BaseModel):
    ogretmen_id: uuid.UUID
    ders_saati: int
    musait_saat: int = Field(description="Haftada gelemez olmadığı saat sayısı")
    kullanilabilir_saat: int = Field(description="Günlük ders sınırıyla birlikte derse girebileceği en fazla saat")
    asim: bool
    mesaj: str | None = Field(description="Aşım varsa ön kontrolün mesajı")


class SinifYukuYanit(BaseModel):
    sinif_id: uuid.UUID
    ders_saati: int
    kapasite: int
    ogretmensiz_atama: int
    asim: bool
    mesaj: str | None


class DagilimOzeti(BaseModel):
    """Ders dağılımının erken uyarıları. Hesap, program üretiminin ön kontrolüyle aynıdır
    (çözücü paketi, `cozucu.yuk`; ADR 0015)."""

    haftalik_kapasite: int
    ogretmen_gunluk_siniri: int
    ogretmensiz_atama: int = Field(description="Öğretmeni seçilmemiş atama sayısı (bütün okul)")
    ogretmenler: list[OgretmenYukuYanit]
    siniflar: list[SinifYukuYanit]


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
    # Üçü de boşsa okul geneli; değilse özel ayar. Özel ayarlar `/kurallar/{tur}/ozel` ile yazılır.
    ders_id: uuid.UUID | None = None
    sinif_id: uuid.UUID | None = None
    ogretmen_id: uuid.UUID | None = None


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
    # Kuralın özel ayar alabildiği yerler (çözücünün kural sınıfından) ve okuldaki özel ayarlar.
    kapsamlar: list[Literal["ogretmen", "ders", "sube"]]
    ozel_ayarlar: list[OzelAyarYanit]


class KuralAyari(BaseModel):
    parametreler: dict[str, int] | None = None
    seviye: OnemSeviyesi | None = None


class KuralKapsami(BaseModel):
    """Özel ayarın yeri. Öğretmen tek başına; ders ve şube tek başına ya da birlikte (ADR 0016)."""

    ogretmen_id: uuid.UUID | None = None
    ders_id: uuid.UUID | None = None
    sinif_id: uuid.UUID | None = None


class OzelAyar(BaseModel):
    kapsam: KuralKapsami
    parametreler: dict[str, int]


class OzelAyarYanit(BaseModel):
    kapsam: KuralKapsami
    ad: str = Field(description="Kapsamın adı: \"Ayşe Yılmaz\", \"9-A · Matematik\"")
    parametreler: dict[str, int]


# --- program -----------------------------------------------------------------------------


class ProgramUret(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    # Doluysa en az değişiklikle güncelleme; o programın kilitli hücreleri de korunur.
    temel_program_id: uuid.UUID | None = None
    # Çözücü süre sınırı. Varsayılan 120 sn (docs/olcumler.md).
    sure_siniri_sn: int = Field(default=120, ge=5, le=3600)


class CeliskiYanit(BaseModel):
    """Programın üretilmesini engelleyen bir sorun (ön kontrol ya da çelişki analizi)."""

    tur: str
    mesaj: str
    ilgili: list[str] = Field(default_factory=list, description="İlgili öğretmen, şube ya da atama kimlikleri")


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
    celiskiler: list[CeliskiYanit] | None
    sure_sn: float | None


class YerlesimYanit(_Yanit):
    id: uuid.UUID
    ders_atama_id: uuid.UUID
    gun: int
    saat: int
    kilitli: bool


KuralYanit.model_rebuild()
