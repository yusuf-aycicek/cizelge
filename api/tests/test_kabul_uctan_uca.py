"""Yapım sırası 3 kabul testi (CLAUDE.md bölüm 8): API'den istek atılır, durum
`bekliyor` -> `uretiliyor` -> `hazir` olarak değişir.

Çalışan gerçek sisteme HTTP ile bağlanır: api, redis, worker ve db konteynerleri (docker compose
up). Gerçek Redis, gerçek RQ, gerçek worker (fork eden RQ worker'ı), gerçek çözücü. Hiçbir şey
taklit edilmez.

    docker compose up -d --build --wait
    cd api && .venv/Scripts/python -m pytest -m uctan_uca -s

Varsayılan test çalıştırmasında yer almaz (geliştirme veritabanına yeni bir okul ekler).
Sistem çalışmıyorsa nedeni yazılarak atlanır. Adres: OKULAPI_KABUL_URL (varsayılan
http://localhost:8000).
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

from conftest import DP, mini_api_ile_yukle, okul_basligi

ADRES = os.environ.get("OKULAPI_KABUL_URL", "http://localhost:8000")
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

pytestmark = pytest.mark.uctan_uca


@pytest.fixture(scope="module")
def sistem():
    istemci = httpx.Client(base_url=ADRES, timeout=10)
    try:
        saglik = istemci.get("/api/saglik")
    except httpx.HTTPError as hata:
        pytest.skip(f"Sistem çalışmıyor ({ADRES}): {hata}. Önce: docker compose up -d --build --wait")
    assert saglik.status_code == 200, saglik.text
    yield istemci
    istemci.close()


def durumu_izle(istemci, baslik, program_id, sinir_sn: float = 120) -> list[str]:
    """Arayüzün yapacağı gibi durumu sorar (burada sık: kısa süren durumları da görmek için).
    Gözlenen durumların sırasını, tekrarsız döner."""
    gorulen: list[str] = []
    bitis = time.monotonic() + sinir_sn
    while time.monotonic() < bitis:
        durum = istemci.get(f"{DP}/programlar/{program_id}", headers=baslik).json()["durum"]
        if not gorulen or gorulen[-1] != durum:
            gorulen.append(durum)
        if durum in ("hazir", "basarisiz"):
            return gorulen
        time.sleep(0.02)
    pytest.fail(f"Program {sinir_sn} sn içinde bitmedi; görülen: {gorulen}")


def cizelge(istemci, baslik, program_id, sinif_adi: str) -> str:
    """Bir sınıfın haftalık çizelgesi (metin tablo): satırlar ders saatleri, sütunlar günler."""
    okul = istemci.get("/api/okul", headers=baslik).json()
    sinif = next(s for s in istemci.get("/api/siniflar", headers=baslik).json() if s["ad"] == sinif_adi)
    dersler = {d["id"]: d["kisa_ad"] for d in istemci.get("/api/dersler", headers=baslik).json()}
    ogretmenler = {o["id"]: o["ad"] for o in istemci.get("/api/ogretmenler", headers=baslik).json()}
    atamalar = {a["id"]: a for a in istemci.get(f"{DP}/atamalar", headers=baslik).json()}
    yerlesimler = istemci.get(f"{DP}/programlar/{program_id}/yerlesimler", headers=baslik).json()

    hucre = {}
    for y in yerlesimler:
        a = atamalar[y["ders_atama_id"]]
        if a["sinif_id"] == sinif["id"]:
            soyad = ogretmenler[a["ogretmen_id"]].split()[-1]
            hucre[(y["gun"], y["saat"])] = f"{dersler[a['ders_id']]} {soyad}" + (" *" if y["kilitli"] else "")

    gunler = GUNLER[: okul["gun_sayisi"]]
    genislik = max([len(g) for g in gunler] + [len(h) for h in hucre.values()]) + 2
    satirlar = [f"{sinif_adi} haftalık ders çizelgesi",
                "Saat | " + " | ".join(g.ljust(genislik) for g in gunler),
                "-----+-" + "-+-".join("-" * genislik for _ in gunler)]
    for saat in range(okul["gunluk_ders_saati"]):
        satirlar.append(f"{saat + 1:>4} | " + " | ".join(hucre.get((g, saat), "").ljust(genislik)
                                                      for g in range(len(gunler))))
    return "\n".join(satirlar)


def test_uretim_istegi_gercek_sistemde_bekliyor_uretiliyor_hazir(sistem):
    okul_id, _ = mini_api_ile_yukle(sistem, f"Kabul Testi Lisesi {time.strftime('%Y-%m-%d %H:%M:%S')}")
    baslik = okul_basligi(okul_id)

    yanit = sistem.post(f"{DP}/programlar", json={"ad": "Güz dönemi", "sure_siniri_sn": 60}, headers=baslik)
    assert yanit.status_code == 202, yanit.text
    program = yanit.json()
    gorulen = [program["durum"]] + durumu_izle(sistem, baslik, program["id"])
    gorulen = [d for i, d in enumerate(gorulen) if i == 0 or gorulen[i - 1] != d]

    son = sistem.get(f"{DP}/programlar/{program['id']}", headers=baslik).json()
    print(f"\nGözlenen durumlar: {' -> '.join(gorulen)}")
    print(f"Çözüm: {son['cozum_durumu']}, ceza {son['toplam_ceza']}, çözücü {son['sure_sn']} sn, "
          f"başlama {son['baslama']}, bitiş {son['bitis']}")
    print(f"Ölçümler: {son['olcumler']}")

    assert gorulen == ["bekliyor", "uretiliyor", "hazir"], son.get("hata_mesaji")
    assert son["cozum_durumu"] in ("optimal", "uygun") and son["baslama"] < son["bitis"]
    yerlesimler = sistem.get(f"{DP}/programlar/{program['id']}/yerlesimler", headers=baslik).json()
    assert len(yerlesimler) == 71
    assert son["olcumler"]["sinif_boslugu"] == 0

    print()
    print(cizelge(sistem, baslik, program["id"], "9-A"))
