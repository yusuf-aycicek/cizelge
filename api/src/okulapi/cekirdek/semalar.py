"""API sözleşmesi: istek ve yanıt şemaları (Pydantic).

ORM modellerinden ayrıdır. Veritabanına bir sütun eklemek API'yi kendiliğinden değiştirmez,
API'ye bir alan eklemek de veritabanını. Doğrulama sınırları veritabanının CHECK kısıtlarıyla
aynıdır; API daha erken ve daha anlaşılır hata verir (422), veritabanı yine de son güvencedir.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class _Yanit(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM nesnesinden doğrudan oluşturulabilir


class OkulOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    gun_sayisi: int = Field(default=5, ge=1, le=7)
    gunluk_ders_saati: int = Field(default=8, ge=1, le=16)


class OkulGuncelle(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    gun_sayisi: int | None = Field(default=None, ge=1, le=7)
    gunluk_ders_saati: int | None = Field(default=None, ge=1, le=16)


class OkulYanit(_Yanit):
    id: uuid.UUID
    ad: str
    gun_sayisi: int
    gunluk_ders_saati: int


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


class DersGuncelle(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    kisa_ad: str | None = Field(default=None, max_length=20)


class DersYanit(_Yanit):
    id: uuid.UUID
    ad: str
    kisa_ad: str
