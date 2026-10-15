"""API'nin OpenAPI şemasını web/openapi.json'a yazar; arayüzün TypeScript tipleri bundan üretilir.

Kullanım (depo kökünden, API'nin sanal ortamıyla):
    api/.venv/Scripts/python scripts/openapi_yaz.py
    cd web && npm run api:tipler

Şema, çalışan bir sunucuya gerek olmadan uygulama nesnesinden alınır. Kararlı biçimde yazılır
(sıralı anahtarlar): şema değişmedikçe dosya değişmez. api/tests/test_openapi_guncel.py dosyanın
API ile aynı olduğunu, web'deki test de tiplerin bu dosyadan üretildiğini denetler.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
HEDEF = KOK / "web" / "openapi.json"


def sema_metni() -> str:
    from okulapi.ayarlar import Ayarlar
    from okulapi.main import uygulama_olustur

    uygulama = uygulama_olustur(Ayarlar())
    try:
        return json.dumps(uygulama.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    finally:
        uygulama.state.motor.dispose()


def main() -> int:
    HEDEF.write_text(sema_metni(), encoding="utf-8")
    print(f"{HEDEF.relative_to(KOK)} yazıldı. Şimdi: cd web && npm run api:tipler")
    return 0


if __name__ == "__main__":
    sys.exit(main())
