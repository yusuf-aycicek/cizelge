"""Uygulama fabrikası: çekirdeği kurar, etkin modülleri yükleyip router'larını bağlar.

Çalıştırma: uvicorn okulapi.main:uygulama_olustur --factory
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import okulapi.cekirdek.kiraci  # noqa: F401  (okul filtresi olayları kaydolur)
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek import saglik
from okulapi.cekirdek.api import ROUTERLAR as CEKIRDEK_ROUTERLARI
from okulapi.cekirdek.modul import modulleri_yukle
from okulapi.cekirdek.kuyruk import RqKuyrugu
from okulapi.cekirdek.servisler import GecersizVeri, HizmetKullanilamiyor, KayitBulunamadi, KayitCakismasi
from okulapi.cekirdek.veritabani import motor_olustur, oturum_fabrikasi

# Servis istisnası -> HTTP durum kodu. Başka okulun kaydı da "bulunamadı" (404) döner: kaydın
# var olduğu bile sızmasın.
_HATA_KODLARI = {KayitBulunamadi: 404, KayitCakismasi: 409, GecersizVeri: 422, HizmetKullanilamiyor: 503}


def _hata_isleyici(kod: int):
    def isle(_istek: Request, hata: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(hata)}, status_code=kod)

    return isle


def uygulama_olustur(ayarlar: Ayarlar | None = None) -> FastAPI:
    ayarlar = ayarlar or Ayarlar()
    uygulama = FastAPI(title="Okul Ders Programı API", version="0.1.0")
    uygulama.state.ayarlar = ayarlar
    uygulama.state.motor = motor_olustur(ayarlar.veritabani_url)
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi(uygulama.state.motor)
    # Testler bunu BellekKuyrugu ile değiştirir. Redis bağlantısı ilk kullanımda kurulur.
    uygulama.state.kuyruk = RqKuyrugu(ayarlar.redis_url, ayarlar.kuyruk_adi)

    for hata_sinifi, kod in _HATA_KODLARI.items():
        uygulama.add_exception_handler(hata_sinifi, _hata_isleyici(kod))

    uygulama.include_router(saglik.router, prefix="/api")
    for router in CEKIRDEK_ROUTERLARI:
        uygulama.include_router(router, prefix="/api")
    moduller = modulleri_yukle(ayarlar.etkin_moduller)
    for modul in moduller:
        uygulama.include_router(modul.router, prefix=f"/api/{modul.onek}")
    uygulama.state.modul_adlari = [m.ad for m in moduller]
    return uygulama
