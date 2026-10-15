"""web/openapi.json, API'nin güncel şemasıyla aynı mı? Arayüzün tipleri bu dosyadan üretilir.

API değişip dosya yenilenmezse bu test kırılır. Yenilemek için:
    api/.venv/Scripts/python scripts/openapi_yaz.py && (cd web && npm run api:tipler)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]


def test_web_openapi_json_guncel():
    spec = importlib.util.spec_from_file_location("openapi_yaz", KOK / "scripts" / "openapi_yaz.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    # Satır sonu farkı (Windows git: CRLF) içerik farkı sayılmaz.
    kayitli = (KOK / "web" / "openapi.json").read_text(encoding="utf-8").replace("
", "
")
    assert kayitli == modul.sema_metni(), "API şeması değişti: scripts/openapi_yaz.py ve npm run api:tipler çalıştırın"
