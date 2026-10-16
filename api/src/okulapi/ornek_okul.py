"""Geliştirme veritabanını temizleyip örnek bir okul yükler (demo ve ekran görüntüleri için).

    cd api && .venv/Scripts/python -m okulapi ornek-okul --evet

- Veritabanındaki **bütün** okullar, kullanıcılar ve oturumlar silinir (`TRUNCATE ... CASCADE`,
  tablo sahibi rolüyle). Bu yüzden `--evet` olmadan hiçbir şey yapılmaz.
- Örnek okul mini veri setinden (`veri/mini.json`) gelir. API'nin kendisinden geçerek yüklenir
  (süreç içinde, `TestClient` ile; sunucunun çalışması gerekmez): bütün doğrulamalar uygulanır.
- Her seviyenin şablonu o seviyenin ilk şubesinin derslerinden üretilir (Seviye şablonu sayfası
  boş görünmesin).
- Giriş bilgisi sabittir (`ORNEK_EMAIL`, `ORNEK_PAROLA`): ekran görüntüleri ve demo hep aynı
  veriyle açılır.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from okulapi.ayarlar import Ayarlar

ORNEK_EMAIL = "mudur@ornek.test"
ORNEK_PAROLA = "ornek-okul-parolasi"
ORNEK_OKUL = "Atatürk Anadolu Lisesi"
ORNEK_MUDUR = "Hatice Yıldız"
MINI = Path(__file__).resolve().parents[3] / "veri" / "mini.json"
DP = "/api/ders-programi"


def veri_setini_yukle(istemci, veri: dict[str, Any], baslik: dict[str, str] | None = None) -> dict[str, str]:
    """Bir veri setini (mini.json biçimi) giriş yapılmış bir okula API üzerinden yükler.

    `istemci`: FastAPI TestClient ya da httpx.Client. `baslik`: istek başlıkları (ör. oturum çerezi).
    Veri setindeki kimlik ("o-ayse") -> veritabanı kimliği haritası döner. Kilitli yerleşimler
    yüklenmez (elle düzeltme yapım sırası 7'de).
    """
    harita: dict[str, str] = {}

    def ekle(yol: str, kayit: dict, govde: dict) -> None:
        yanit = istemci.post(yol, json=govde, headers=baslik)
        if yanit.status_code != 201:
            raise RuntimeError(f"{yol}: {yanit.status_code} {yanit.text}")
        if "id" in kayit:
            harita[kayit["id"]] = yanit.json()["id"]

    for o in veri["ogretmenler"]:
        ekle("/api/ogretmenler", o, {"ad": o["ad"], "brans": o["brans"]})
    for s in veri["siniflar"]:
        ekle("/api/siniflar", s, {"ad": s["ad"], "seviye": s["seviye"]})
    for d in veri["dersler"]:
        ekle("/api/dersler", d, {"ad": d["ad"], "kisa_ad": d["kisa_ad"]})
    for a in veri["atamalar"]:
        ekle(f"{DP}/atamalar", a, {"sinif_id": harita[a["sinif_id"]], "ders_id": harita[a["ders_id"]],
                                   "ogretmen_id": harita[a["ogretmen_id"]], "haftalik_saat": a["haftalik_saat"]})
    for m in veri["musaitlikler"]:
        ekle(f"{DP}/musaitlikler", m, {**m, "ogretmen_id": harita[m["ogretmen_id"]]})
    for k in veri["kisitlar"]:
        ekle(f"{DP}/kisitlar", k, k)
    return harita


def _sablonlari_uret(istemci, veri: dict[str, Any], harita: dict[str, str]) -> int:
    """Her seviye için, o seviyenin (ada göre) ilk şubesinin dersleri ve saatleri."""
    ilk_sube: dict[int, str] = {}
    for s in sorted(veri["siniflar"], key=lambda s: s["ad"]):
        ilk_sube.setdefault(s["seviye"], s["id"])
    sayi = 0
    for seviye, sinif_id in ilk_sube.items():
        for a in veri["atamalar"]:
            if a["sinif_id"] == sinif_id:
                yanit = istemci.post(f"{DP}/seviye-sablonlari", json={
                    "seviye": seviye, "ders_id": harita[a["ders_id"]], "haftalik_saat": a["haftalik_saat"]})
                if yanit.status_code != 201:
                    raise RuntimeError(f"seviye şablonu: {yanit.status_code} {yanit.text}")
                sayi += 1
    return sayi


def veritabanini_temizle(migrasyon_url: str) -> None:
    """Okula ait bütün satırlar (okul tablosundan CASCADE) ve giriş denemesi sayaçları."""
    motor = create_engine(migrasyon_url)
    try:
        with motor.begin() as baglanti:
            baglanti.execute(text("TRUNCATE okul, giris_denemesi CASCADE"))
    finally:
        motor.dispose()


def ornek_okul_kur(ayarlar: Ayarlar, veri_yolu: Path = MINI) -> dict[str, int]:
    import warnings

    # Starlette'in TestClient'ı httpx için kullanım dışı uyarısı verir; bu komutun çıktısını kirletmesin.
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient

    from okulapi.main import uygulama_olustur

    veri = json.loads(veri_yolu.read_text(encoding="utf-8"))
    veritabanini_temizle(ayarlar.migrasyon_url)
    # Süreç içi istemci http üzerinden konuşur; Secure çerez geri gönderilmezdi. Bu çerez yalnızca
    # yükleme sırasında kullanılır, tarayıcıya hiç gitmez.
    uygulama = uygulama_olustur(ayarlar.model_copy(update={"cerez_secure": False}))
    try:
        with TestClient(uygulama) as istemci:
            yanit = istemci.post("/api/kayit", json={
                "okul": {"ad": ORNEK_OKUL, **veri["ayar"]}, "ad": ORNEK_MUDUR,
                "email": ORNEK_EMAIL, "sifre": ORNEK_PAROLA})
            if yanit.status_code != 201:
                raise RuntimeError(f"kayıt: {yanit.status_code} {yanit.text}")
            harita = veri_setini_yukle(istemci, veri)
            sablon = _sablonlari_uret(istemci, veri, harita)
    finally:
        uygulama.state.motor.dispose()
    return {"ogretmen": len(veri["ogretmenler"]), "sinif": len(veri["siniflar"]), "ders": len(veri["dersler"]),
            "atama": len(veri["atamalar"]), "musaitlik": len(veri["musaitlikler"]), "sablon": sablon}
