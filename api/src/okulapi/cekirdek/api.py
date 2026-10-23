"""Çekirdek endpoint'leri: /api/okul, /api/ogretmenler, /api/siniflar, /api/dersler.

Router yalnızca HTTP ile ilgilenir: yol, durum kodu, şema doğrulaması. İşi servise devreder.
Okula ait varlıkların CRUD'u tek bir fabrika (`crud_router`) ile üretilir; modüller de aynı
fabrikayı kendi varlıkları için kullanabilir.

Not: Bu dosyada `from __future__ import annotations` yoktur. FastAPI, fabrika içindeki
fonksiyonların tip ipuçlarını (ör. `olustur_semasi`) çalışma anında gerçek sınıflar olarak okur.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from okulapi.cekirdek import semalar
from okulapi.cekirdek.bagimliliklar import AktifOkulId, OkulOturumu
from okulapi.cekirdek.ders_renkleri import DERS_RENKLERI
from okulapi.cekirdek.servisler import CrudServisi, DersServisi, OgretmenServisi, OkulServisi, SinifServisi


def crud_router(
    yol: str,
    servis_sinifi: type[CrudServisi],
    olustur_semasi: type[BaseModel],
    guncelle_semasi: type[BaseModel],
    yanit_semasi: type[BaseModel],
    etiket: str,
) -> APIRouter:
    router = APIRouter(prefix=yol, tags=[etiket])

    @router.get("", response_model=list[yanit_semasi])
    def listele(oturum: OkulOturumu) -> Any:
        return servis_sinifi(oturum).listele()

    @router.get("/{kayit_id}", response_model=yanit_semasi)
    def getir(kayit_id: uuid.UUID, oturum: OkulOturumu) -> Any:
        return servis_sinifi(oturum).getir(kayit_id)

    @router.post("", response_model=yanit_semasi, status_code=status.HTTP_201_CREATED)
    def olustur(veri: olustur_semasi, oturum: OkulOturumu) -> Any:  # type: ignore[valid-type]
        return servis_sinifi(oturum).olustur(veri.model_dump())

    @router.patch("/{kayit_id}", response_model=yanit_semasi)
    def guncelle(kayit_id: uuid.UUID, veri: guncelle_semasi, oturum: OkulOturumu) -> Any:  # type: ignore[valid-type]
        # exclude_unset: yalnızca istekte gönderilen alanlar değişir.
        return servis_sinifi(oturum).guncelle(kayit_id, veri.model_dump(exclude_unset=True))

    @router.delete("/{kayit_id}", status_code=status.HTTP_204_NO_CONTENT)
    def sil(kayit_id: uuid.UUID, oturum: OkulOturumu, istek: Request) -> Response:
        # Modüller: silinemezse kaydın nerede kullanıldığını söylerler (ADR 0014).
        servis_sinifi(oturum, istek.app.state.moduller).sil(kayit_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


okul_router = APIRouter(tags=["okul"])


@okul_router.get("/ders-renkleri", response_model=list[semalar.DersRengi], tags=["ders"])
def ders_renkleri(_okul_id: AktifOkulId) -> Any:
    """Ders renk paleti. Her renk çipteki beyaz yazıyla en az 4.5:1 kontrastlıdır."""
    return [{"renk": r, "ad": ad} for r, ad in DERS_RENKLERI]


@okul_router.get("/okul", response_model=semalar.OkulYanit)
def okul_getir(okul_id: AktifOkulId, oturum: OkulOturumu) -> Any:
    return OkulServisi(oturum).getir(okul_id)


@okul_router.patch(
    "/okul", response_model=semalar.OkulYanit,
    responses={409: {"description": "Değişiklik mevcut kayıtları etkiliyor; `etkiler` listesi döner"}},
)
def okul_guncelle(veri: semalar.OkulGuncelle, okul_id: AktifOkulId, oturum: OkulOturumu, istek: Request) -> Any:
    degisiklikler = veri.model_dump(exclude_unset=True, exclude={"etkileri_onayla"})
    return OkulServisi(oturum).guncelle(okul_id, degisiklikler, istek.app.state.moduller, veri.etkileri_onayla)


@okul_router.post("/okul/ayar-etkisi", response_model=semalar.AyarEtkisiYanit)
def okul_ayar_etkisi(veri: semalar.AyarEtkisiIstegi, okul_id: AktifOkulId, oturum: OkulOturumu, istek: Request) -> Any:
    """Önizleme: gün/saat bu değerlere getirilirse mevcut kayıtlara ne olur? Hiçbir şeyi değiştirmez."""
    etkiler = OkulServisi(oturum).ayar_etkileri(okul_id, veri.model_dump(exclude_unset=True), istek.app.state.moduller)
    return {"etkiler": etkiler}


ROUTERLAR = [
    okul_router,
    crud_router("/ogretmenler", OgretmenServisi, semalar.OgretmenOlustur, semalar.OgretmenGuncelle,
                semalar.OgretmenYanit, "öğretmen"),
    crud_router("/siniflar", SinifServisi, semalar.SinifOlustur, semalar.SinifGuncelle,
                semalar.SinifYanit, "sınıf"),
    crud_router("/dersler", DersServisi, semalar.DersOlustur, semalar.DersGuncelle,
                semalar.DersYanit, "ders"),
]
