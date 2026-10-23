"""API sözleşmesi: istek ve yanıt şemaları (Pydantic).

ORM modellerinden ayrıdır. Veritabanına bir sütun eklemek API'yi kendiliğinden değiştirmez,
API'ye bir alan eklemek de veritabanını. Doğrulama sınırları veritabanının CHECK kısıtlarıyla
aynıdır; API daha erken ve daha anlaşılır hata verir (422), veritabanı yine de son güvencedir.
"""

from __future__ import annotations

import uuid
from datetime import time
from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class _Yanit(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM nesnesinden doğrudan oluşturulabilir


class OkulOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    gun_sayisi: int = Field(default=5, ge=1, le=7)
    gunluk_ders_saati: int = Field(default=8, ge=1, le=16)


# Bir günün ders saati sayısı (günlük ders saatiyle aynı sınırlar).
GunSaati = Annotated[int, Field(ge=1, le=16)]


class OkulGuncelle(BaseModel):
    """Kısmi güncelleme: gönderilmeyen alan değişmez; `null` gönderilen alan boşaltılır."""

    ad: str | None = Field(default=None, min_length=1, max_length=200)
    gun_sayisi: int | None = Field(default=None, ge=1, le=7)
    gunluk_ders_saati: int | None = Field(default=None, ge=1, le=16)
    # Günlere göre ders saati (her gün için bir sayı); null = her gün `gunluk_ders_saati`.
    gun_saatleri: list[GunSaati] | None = Field(default=None, min_length=1, max_length=7)
    ogle_arasi_sonra: int | None = Field(default=None, ge=1, le=15)  # null = öğle arası yok
    # Zil saatleri (yalnızca gösterim); başlangıç null = tanımsız.
    ilk_ders_baslangic: time | None = None
    ders_suresi_dk: int = Field(default=40, ge=10, le=120)
    teneffus_dk: int = Field(default=10, ge=0, le=60)
    ogle_arasi_dk: int = Field(default=40, ge=0, le=180)
    # Gün/saat azaltılınca mevcut kayıtlar etkilenebilir; etkiler bu alanla açıkça onaylanmadıkça
    # değişiklik yapılmaz (409, etkiler listesiyle). Önizleme: POST /api/okul/ayar-etkisi.
    etkileri_onayla: bool = False


class AyarEtkisiIstegi(BaseModel):
    gun_sayisi: int | None = Field(default=None, ge=1, le=7)
    gunluk_ders_saati: int | None = Field(default=None, ge=1, le=16)
    gun_saatleri: list[GunSaati] | None = Field(default=None, min_length=1, max_length=7)
    ogle_arasi_sonra: int | None = Field(default=None, ge=1, le=15)


class AyarEtkisiYanit(BaseModel):
    """Bu değişiklik yapılırsa mevcut kayıtlara ne olur (kullanıcının diliyle). Boşsa etkisi yok."""

    etkiler: list[str]


class OkulYanit(_Yanit):
    id: uuid.UUID
    ad: str
    gun_sayisi: int
    gunluk_ders_saati: int  # en uzun gün
    # Her gün için ders saati sayısı; günler aynıysa da tam liste (ORM'deki `gunluk_saatler`).
    gun_saatleri: list[int] = Field(validation_alias=AliasChoices("gunluk_saatler", "gun_saatleri"))
    ogle_arasi_sonra: int | None
    ilk_ders_baslangic: time | None
    ders_suresi_dk: int
    teneffus_dk: int
    ogle_arasi_dk: int


class OgretmenOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    brans: str = Field(default="", max_length=100)


class OgretmenGuncelle(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    brans: str | None = Field(default=None, max_length=100)


class OgretmenYanit(_Yanit):
    id: uuid.UUID
    ad: str
    brans: str


class SinifOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=50)
    seviye: int = Field(ge=1, le=12)


class SinifGuncelle(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=50)
    seviye: int | None = Field(default=None, ge=1, le=12)


class SinifYanit(_Yanit):
    id: uuid.UUID
    ad: str
    seviye: int


class DersOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    kisa_ad: str = Field(default="", max_length=20)
    # Verilmezse okulda en az kullanılan palet rengi atanır. Palet: GET /api/ders-renkleri.
    renk: str | None = Field(default=None, description="Paletteki bir renk (#rrggbb)")


class DersGuncelle(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    kisa_ad: str | None = Field(default=None, max_length=20)
    renk: str | None = Field(default=None, description="Paletteki bir renk (#rrggbb)")


class DersYanit(_Yanit):
    id: uuid.UUID
    ad: str
    kisa_ad: str
    renk: str


class DersRengi(BaseModel):
    renk: str
    ad: str
