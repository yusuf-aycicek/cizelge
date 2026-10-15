"""Kimlik uçları: kayıt, giriş, çıkış, ben, kullanıcı yönetimi (ADR 0012, ADR 0013).

Jeton bir çerezde taşınır:
- `HttpOnly`: JavaScript okuyamaz;
- `SameSite=Strict`: başka sitelerden gelen isteklere eklenmez;
- `Secure`: ayara bağlı (yayında açık);
- `Path=/api`: yalnızca API isteklerine eklenir.

Yanıt gövdesinde jeton yoktur.

Not: `from __future__ import annotations` yok (FastAPI tip ipuçlarını çalışma anında okur).
"""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from okulapi.cekirdek.bagimliliklar import AktifOturum, Kimlik, OkulOturumu
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.cekirdek.kimlik.servis import KullaniciServisi
from okulapi.cekirdek.modeller import Kullanici, Okul
from okulapi.cekirdek.semalar import OkulOlustur, OkulYanit

EPOSTA = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Uzunluk kuralı (12-256) serviste, Türkçe mesajla; burada yalnızca gövde boyutu sınırı.
PAROLA = Field(min_length=1, max_length=1000)

router = APIRouter(tags=["kimlik"])


# --- şemalar ----------------------------------------------------------------------------------

class KayitIstegi(BaseModel):
    okul: OkulOlustur
    ad: str = Field(min_length=1, max_length=200)
    email: str = EPOSTA
    sifre: str = PAROLA


class GirisIstegi(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    sifre: str = PAROLA


class KullaniciYanit(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ad: str
    email: str
    rol: str


class BenYanit(BaseModel):
    kullanici: KullaniciYanit
    okul: OkulYanit


class SifreDegistir(BaseModel):
    eski: str = PAROLA
    yeni: str = PAROLA


class YardimciOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    email: str = EPOSTA
    sifre: str = PAROLA


class SifreBelirle(BaseModel):
    sifre: str = PAROLA


class RolDegistir(BaseModel):
    rol: Literal["mudur", "mudur_yardimcisi"]


# --- çerez ------------------------------------------------------------------------------------

def _cerez_yaz(istek: Request, yanit: Response, jeton: str) -> None:
    ayarlar = istek.app.state.ayarlar
    yanit.set_cookie(
        ayarlar.cerez_adi, jeton,
        max_age=ayarlar.oturum_en_uzun_gun * 24 * 3600,
        path="/api", httponly=True, samesite="strict", secure=ayarlar.cerez_secure,
    )


def _cerez_sil(istek: Request, yanit: Response) -> None:
    ayarlar = istek.app.state.ayarlar
    yanit.delete_cookie(ayarlar.cerez_adi, path="/api", httponly=True, samesite="strict",
                        secure=ayarlar.cerez_secure)


def _ben(oturum, bilgi) -> dict[str, Any]:
    return {"kullanici": oturum.get(Kullanici, bilgi.kullanici_id), "okul": oturum.get(Okul, bilgi.okul_id)}


# --- kayıt, giriş, çıkış ----------------------------------------------------------------------

@router.post("/kayit", response_model=BenYanit, status_code=status.HTTP_201_CREATED)
def kayit(veri: KayitIstegi, kimlik: Kimlik, istek: Request, yanit: Response) -> Any:
    """Okul kaydı: okul, ilk müdür ve oturum tek işlemde. E-posta başka bir hesapta
    kullanılıyorsa 409."""
    okul, mudur, jeton = kimlik.kayit(veri.okul.model_dump(), veri.ad, veri.email, veri.sifre)
    _cerez_yaz(istek, yanit, jeton)
    return {"kullanici": mudur, "okul": okul}


@router.post("/giris", response_model=BenYanit)
def giris(veri: GirisIstegi, kimlik: Kimlik, istek: Request, yanit: Response) -> Any:
    """401: e-posta ya da parola hatalı (hangisi olduğu söylenmez). 429: çok fazla hatalı deneme."""
    bilgi, jeton = kimlik.giris(veri.email, veri.sifre)
    _cerez_yaz(istek, yanit, jeton)
    with okul_oturumu(istek.app.state.oturum_fabrikasi, bilgi.okul_id) as oturum:
        return _ben(oturum, bilgi)


@router.post("/cikis", status_code=status.HTTP_204_NO_CONTENT)
def cikis(kimlik: Kimlik, istek: Request) -> Response:
    """Oturum silinir, çerez temizlenir. Oturum yoksa da 204."""
    kimlik.cikis(istek.cookies.get(istek.app.state.ayarlar.cerez_adi))
    yanit = Response(status_code=status.HTTP_204_NO_CONTENT)
    _cerez_sil(istek, yanit)
    return yanit


# --- ben ------------------------------------------------------------------------------------

@router.get("/ben", response_model=BenYanit)
def ben(bilgi: AktifOturum, oturum: OkulOturumu) -> Any:
    """Arayüz açılışta "giriş yapılmış mı" diye bunu sorar: 200 ya da 401."""
    return _ben(oturum, bilgi)


@router.put("/ben/sifre", status_code=status.HTTP_204_NO_CONTENT)
def kendi_sifremi_degistir(veri: SifreDegistir, bilgi: AktifOturum, oturum: OkulOturumu) -> Response:
    """Mevcut parola gerekir. Bu oturum dışındaki bütün oturumlar kapanır."""
    KullaniciServisi(oturum, bilgi).kendi_parolasini_degistir(veri.eski, veri.yeni)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- kullanıcı yönetimi (yönetim işleri yalnızca müdür) ---------------------------------------

kullanici_router = APIRouter(prefix="/kullanicilar", tags=["kullanıcı"])


@kullanici_router.get("", response_model=list[KullaniciYanit])
def kullanicilari_listele(bilgi: AktifOturum, oturum: OkulOturumu) -> Any:
    return KullaniciServisi(oturum, bilgi).listele()


@kullanici_router.post("", response_model=KullaniciYanit, status_code=status.HTTP_201_CREATED)
def yardimci_ekle(veri: YardimciOlustur, bilgi: AktifOturum, oturum: OkulOturumu) -> Any:
    return KullaniciServisi(oturum, bilgi).yardimci_ekle(veri.ad, veri.email, veri.sifre)


@kullanici_router.put("/{kullanici_id}/sifre", status_code=status.HTTP_204_NO_CONTENT)
def sifre_belirle(kullanici_id: uuid.UUID, veri: SifreBelirle, bilgi: AktifOturum, oturum: OkulOturumu) -> Response:
    """Kullanıcının bütün oturumları kapanır."""
    KullaniciServisi(oturum, bilgi).parola_belirle(kullanici_id, veri.sifre)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@kullanici_router.put("/{kullanici_id}/rol", response_model=KullaniciYanit)
def rol_degistir(kullanici_id: uuid.UUID, veri: RolDegistir, bilgi: AktifOturum, oturum: OkulOturumu) -> Any:
    """409: okulun son müdürünün rolü düşürülemez."""
    return KullaniciServisi(oturum, bilgi).rol_degistir(kullanici_id, veri.rol)


@kullanici_router.delete("/{kullanici_id}", status_code=status.HTTP_204_NO_CONTENT)
def kullanici_sil(kullanici_id: uuid.UUID, bilgi: AktifOturum, oturum: OkulOturumu) -> Response:
    """Oturumları da silinir. 409: okulun son müdürü silinemez."""
    KullaniciServisi(oturum, bilgi).sil(kullanici_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(kullanici_router)
