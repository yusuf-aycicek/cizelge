"""Uygulama fabrikası: çekirdeği kurar, etkin modülleri yükleyip router'larını bağlar.

Çalıştırma: uvicorn okulapi.main:uygulama_olustur --factory
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import okulapi.cekirdek.kiraci  # noqa: F401  (okul filtresi olayları kaydolur)
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek import saglik
from okulapi.cekirdek.dogrulama_hatalari import dogrulama_hatasi_isleyici, openapi_semasini_uyarla
from okulapi.cekirdek.api import ROUTERLAR as CEKIRDEK_ROUTERLARI
from okulapi.cekirdek.modul import modulleri_yukle
from okulapi.cekirdek.kimlik.api import router as kimlik_router
from okulapi.cekirdek.kimlik.koken import KokenDenetimi
from okulapi.cekirdek.kimlik.servis import CokFazlaDeneme, GirisHatasi, YetkiYok
from okulapi.cekirdek.kuyruk import RqKuyrugu
from okulapi.cekirdek.servisler import (
    AyarEtkisiOnayGerekli,
    GecersizVeri,
    HizmetKullanilamiyor,
    KayitBulunamadi,
    KayitCakismasi,
)
from okulapi.cekirdek.veritabani import motor_olustur, oturum_fabrikasi

# Servis istisnası -> HTTP durum kodu. Başka okulun kaydı da "bulunamadı" (404) döner: kaydın
# var olduğu bile sızmasın.
_HATA_KODLARI = {
    GirisHatasi: 401, YetkiYok: 403, KayitBulunamadi: 404, KayitCakismasi: 409, GecersizVeri: 422,
    CokFazlaDeneme: 429, HizmetKullanilamiyor: 503,
}


def _hata_isleyici(kod: int):
    def isle(istek: Request, hata: Exception) -> JSONResponse:
        basliklar = {}
        if kod == 429:  # istemci ne zaman yeniden deneyebileceğini bilsin
            basliklar["Retry-After"] = str(istek.app.state.ayarlar.giris_kilit_dk * 60)
        return JSONResponse({"detail": str(hata)}, status_code=kod, headers=basliklar)

    return isle


def _ayar_etkisi_isleyici(_istek: Request, hata: Exception) -> JSONResponse:
    etkiler = getattr(hata, "etkiler", [])
    return JSONResponse({"detail": str(hata), "etkiler": etkiler}, status_code=409)


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

    uygulama.add_exception_handler(RequestValidationError, dogrulama_hatasi_isleyici)
    uygulama.add_exception_handler(AyarEtkisiOnayGerekli, _ayar_etkisi_isleyici)
    uygulama.add_middleware(KokenDenetimi, izinli_kokenler=ayarlar.izinli_kokenler)

    uygulama.include_router(saglik.router, prefix="/api")
    uygulama.include_router(kimlik_router, prefix="/api")
    for router in CEKIRDEK_ROUTERLARI:
        uygulama.include_router(router, prefix="/api")
    moduller = modulleri_yukle(ayarlar.etkin_moduller)
    for modul in moduller:
        uygulama.include_router(modul.router, prefix=f"/api/{modul.onek}")
    uygulama.state.modul_adlari = [m.ad for m in moduller]
    uygulama.state.moduller = moduller  # çekirdek kancaları sorar (ADR 0014)
    openapi_semasini_uyarla(uygulama)
    return uygulama
