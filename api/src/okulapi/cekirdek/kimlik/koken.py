"""Köken (Origin) denetimi: siteler arası istek sahteciliğine (CSRF) karşı ikinci katman (ADR 0013).

Birinci katman çerezin `SameSite=Strict` olmasıdır: tarayıcı başka bir siteden gelen isteğe oturum
çerezini eklemez. Bu katman ayrıca, veri değiştiren isteklerde (POST, PUT, PATCH, DELETE)
tarayıcının gönderdiği `Origin` başlığına bakar: başlık varsa ve izin verilen kökenlerden biri
değilse istek 403 alır.

- Tarayıcılar veri değiştiren isteklerde `Origin` başlığını her zaman gönderir. Başlık yoksa istek
  tarayıcıdan değildir (curl, testler, sunucudaki araçlar). CSRF yalnızca tarayıcıyla yapılabilen
  bir saldırı olduğu için bunlar kabul edilir. Bu isteklerin de oturum çerezi olmalıdır.
- `Origin: null` (ör. sandbox'lı iframe, dosyadan açılmış sayfa) izinli değildir.
- Okuma istekleri (GET, HEAD, OPTIONS) denetlenmez: veri değiştirmezler. SameSite çerez zaten
  eklenmez.

İzin verilen kökenler ayardan gelir (`izinli_kokenler`). Arayüz ile API tarayıcıya aynı köken
üzerinden görünür: geliştirmede Vite'ın adresi, yayında sitenin adresi.
"""

from __future__ import annotations

from starlette.responses import JSONResponse

GUVENLI_YONTEMLER = {"GET", "HEAD", "OPTIONS"}
IZINSIZ_KOKEN = "Bu isteğe izin verilmiyor (köken denetimi)"


class KokenDenetimi:
    """ASGI ara katmanı (middleware): her istek uç fonksiyonlarından önce buradan geçer."""

    def __init__(self, uygulama, izinli_kokenler: list[str]) -> None:
        self.uygulama = uygulama
        self.izinli = {k.rstrip("/") for k in izinli_kokenler}

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http" and scope["method"] not in GUVENLI_YONTEMLER:
            koken = dict(scope["headers"]).get(b"origin")
            if koken is not None and koken.decode("latin-1").rstrip("/") not in self.izinli:
                await JSONResponse({"detail": IZINSIZ_KOKEN}, status_code=403)(scope, receive, send)
                return
        await self.uygulama(scope, receive, send)
