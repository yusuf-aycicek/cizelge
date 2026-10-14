"""Sağlık kontrolü: API ayakta mı, veritabanına ulaşabiliyor mu? Docker healthcheck bunu kullanır."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

router = APIRouter(tags=["sağlık"])


@router.get("/saglik")
def saglik(istek: Request) -> JSONResponse:
    try:
        with istek.app.state.motor.connect() as baglanti:
            baglanti.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse({"durum": "hata", "veritabani": "ulaşılamıyor"}, status_code=503)
    return JSONResponse({"durum": "ok", "veritabani": "ok", "moduller": istek.app.state.modul_adlari})
