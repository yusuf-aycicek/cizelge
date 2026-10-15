"""Sağlık kontrolü: API ayakta mı, veritabanına ulaşabiliyor mu? Docker healthcheck ve arayüzün
ana sayfası bunu kullanır.

Not: `from __future__ import annotations` yok (FastAPI yanıt modelini çalışma anında okur).
"""

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

router = APIRouter(tags=["sağlık"])

VERITABANI_YOK = "Veritabanına ulaşılamıyor"


class SaglikYanit(BaseModel):
    durum: Literal["ok"]
    veritabani: Literal["ok"]
    moduller: list[str]


@router.get(
    "/saglik",
    response_model=SaglikYanit,
    responses={503: {"description": VERITABANI_YOK}},
)
def saglik(istek: Request):
    try:
        with istek.app.state.motor.connect() as baglanti:
            baglanti.execute(text("SELECT 1"))
    except OperationalError:
        # Biçim diğer hatalarla aynı: {"detail": "..."} (arayüz tek yerde çözer).
        return JSONResponse({"detail": VERITABANI_YOK}, status_code=503)
    return SaglikYanit(durum="ok", veritabani="ok", moduller=istek.app.state.modul_adlari)
