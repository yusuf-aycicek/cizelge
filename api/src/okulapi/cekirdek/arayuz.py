"""Derlenmiş arayüzü (web/dist) API ile aynı adresten sunar (ADR 0028).

Yayında arayüz ve API tek serviste çalışır: tarayıcı ikisini aynı kökenden görür, oturum çerezi
SameSite=Strict kalır, CORS ve vekil sunucu gerekmez. Kurallar:

- `/api/*` her zaman API'nindir: tanımsız bir API yolu index.html değil JSON 404 döner.
- `/assets/*` dosyalarının adında içerik özeti (hash) vardır; içerik değişince ad da değişir. Bu
  yüzden bir yıl önbelleklenir (`immutable`). Olmayan bir asset 404'tür: eski bir sayfanın istediği
  silinmiş dosya index.html olarak dönerse tarayıcı onu betik diye çalıştırmaya kalkar.
- Diğer var olan dosyalar (ör. favicon) ve index.html önbelleklenmez: yeni sürüm hemen görünür.
- Bilinmeyen her yol index.html döner; sayfayı React Router seçer (/giris, /program/5, /p/<jeton>).

Dizin ayardan gelir (`arayuz_dizini`); verilmezse ya da yoksa hiçbir şey eklenmez (geliştirmede
arayüzü Vite sunar, testler yalnızca API'yi kurar).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

UZUN_ONBELLEK = "public, max-age=31536000, immutable"
ONBELLEKSIZ = "no-cache"


def arayuzu_bagla(uygulama: FastAPI, dizin: str | None) -> None:
    """Bütün API router'larından sonra çağrılır: buradaki yol hepsini yakalar, önce onlar eşleşir."""
    if not dizin:
        return
    kok = Path(dizin).resolve()
    index = kok / "index.html"
    if not index.is_file():
        return

    @uygulama.api_route("/{yol:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def arayuz(yol: str) -> FileResponse:
        if yol == "api" or yol.startswith("api/"):
            raise HTTPException(status_code=404)
        dosya = (kok / yol).resolve()
        # "../" ile dizinin dışına çıkılamaz; dışarıyı gösteren yol bilinmeyen sayfa sayılır.
        if dosya != kok and dosya.is_relative_to(kok) and dosya.is_file():
            onbellek = UZUN_ONBELLEK if yol.startswith("assets/") else ONBELLEKSIZ
            return FileResponse(dosya, headers={"Cache-Control": onbellek})
        if yol.startswith("assets/"):
            raise HTTPException(status_code=404)
        return FileResponse(index, headers={"Cache-Control": ONBELLEKSIZ})
