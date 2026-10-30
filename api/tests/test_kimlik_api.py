"""Kimlik uçları ve yapım sırası 4 kabul testleri (CLAUDE.md bölüm 8):

    "X-Okul-Id başlığı tamamen kaldırılmıştır; aktif okul yalnızca oturumdan belirlenir. Başlık
    gönderilse bile yok sayıldığı ve oturumsuz isteklerin okula ait veriye erişemediği testle
    kanıtlanır."

Ayrıca: çerez özellikleri, köken (Origin) denetimi (ADR 0013), giriş/çıkış akışı, kaba kuvvet
yanıtı, kullanıcı yönetimi uçları.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import CEREZ, IZINLI_KOKEN, PAROLA, api_ile_kayit, cerezden_jeton, okul_basligi
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.kimlik.koken import IZINSIZ_KOKEN
from okulapi.main import uygulama_olustur
from okulapi.ornek_okul import DEMO_EMAIL

KAYNAK = Path(__file__).resolve().parents[1] / "src"
YENI = "yepyeni-parola-2026"

# Oturum gerektirmeyen uçlar. Liste bilerek elle yazılır: yeni bir açık uç eklemek bilinçli bir
# karar olmalı (bu test güncellenmeden eklenirse aşağıdaki test kırılır).
ACIK_UCLAR = {("get", "/api/saglik"), ("post", "/api/kayit"), ("post", "/api/giris"), ("post", "/api/cikis"),
              # Demo düğmesi (ADR 0027): yalnızca demo hesabına oturum açar, sunucu ayarıyla açılır.
              ("get", "/api/oturum/demo"), ("post", "/api/oturum/demo"),
              # Paylaşım linki (ADR 0022): okul bağlamı açmaz, yalnızca jetonun kapsamı; test_paylasim.py.
              ("get", "/api/ders-programi/paylasim/{jeton}"), ("get", "/api/ders-programi/paylasim/{jeton}/program.pdf")}


def cerez(jeton: str) -> dict[str, str]:
    return {"Cookie": f"{CEREZ}={jeton}"}


def giris(istemci, email, sifre=PAROLA) -> str:
    yanit = istemci.post("/api/giris", json={"email": email, "sifre": sifre})
    assert yanit.status_code == 200, yanit.text
    istemci.cookies.clear()
    return cerezden_jeton(yanit)


def okul_ve_ogretmen(istemci, ad: str) -> tuple[str, str]:
    okul_id, email, _ = api_ile_kayit(istemci, ad)
    yanit = istemci.post("/api/ogretmenler", json={"ad": f"{ad} Öğretmeni"}, headers=okul_basligi(okul_id))
    assert yanit.status_code == 201
    return okul_id, email


# --- kabul: başlık yok sayılır, oturumsuz erişim yok ------------------------------------------

def test_okul_basligi_gonderilse_bile_yok_sayilir(istemci):
    a, _ = okul_ve_ogretmen(istemci, "A Lisesi")
    b, _ = okul_ve_ogretmen(istemci, "B Lisesi")

    # A'nın oturumu + B'yi gösteren başlık: A'nın verisi görünür, B'ninki görünmez.
    yanit = istemci.get("/api/ogretmenler", headers={**okul_basligi(a), "X-Okul-Id": b})
    assert yanit.status_code == 200
    assert [o["ad"] for o in yanit.json()] == ["A Lisesi Öğretmeni"]
    assert istemci.get("/api/okul", headers={**okul_basligi(a), "X-Okul-Id": b}).json()["id"] == a

    # Başlık tek başına hiçbir şey açmaz.
    yanit = istemci.get("/api/ogretmenler", headers={"X-Okul-Id": b})
    assert yanit.status_code == 401


def test_kaynak_kodunda_okul_basligi_gecmez():
    ihlaller = [f"{d.relative_to(KAYNAK)}:{i}" for d in KAYNAK.rglob("*.py")
                for i, satir in enumerate(d.read_text(encoding="utf-8").splitlines(), 1)
                if re.search(r"x[-_]okul[-_]id", satir, re.IGNORECASE)]
    assert ihlaller == []


def _uclar(uygulama) -> list[tuple[str, str]]:
    """(yöntem, yol) listesi, uygulamanın kendisinden (OpenAPI şeması)."""
    return [(yontem, yol) for yol, yontemler in uygulama.openapi()["paths"].items() for yontem in yontemler]


def test_acik_uclar_listesi_guncel(istemci):
    assert ACIK_UCLAR <= set(_uclar(istemci.app))


@pytest.mark.parametrize("cerez_degeri", [None, "uydurma-jeton", ""])
def test_oturumsuz_istek_okula_ait_her_ucta_401(istemci, cerez_degeri):
    """Liste uygulamanın uçlarından otomatik çıkarılır: yeni bir uç eklenip korunması unutulursa
    bu test kırılır. Gerçek bir okulun kimliği başlıkta da gönderilir (yok sayılmalı)."""
    gercek_okul, _ = okul_ve_ogretmen(istemci, "Hedef Lisesi")
    basliklar = {"X-Okul-Id": gercek_okul}
    if cerez_degeri is not None:
        basliklar["Cookie"] = f"{CEREZ}={cerez_degeri}"
    korunan = [(y, p) for y, p in _uclar(istemci.app) if (y, p) not in ACIK_UCLAR]
    assert len(korunan) >= 30

    sizanlar = []
    for yontem, yol in korunan:
        somut = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), yol)
        yanit = istemci.request(yontem.upper(), somut, json={}, headers=basliklar)
        if yanit.status_code != 401:
            sizanlar.append((yontem, yol, yanit.status_code))
    assert sizanlar == []


def test_gecerli_oturumla_ayni_uclar_acilir(istemci):
    okul, _ = okul_ve_ogretmen(istemci, "A Lisesi")
    for yol in ("/api/ben", "/api/okul", "/api/ogretmenler", "/api/kullanicilar", "/api/ders-programi/programlar"):
        assert istemci.get(yol, headers=okul_basligi(okul)).status_code == 200, yol


# --- çerez -------------------------------------------------------------------------------------

def _kayit_yaniti(istemci, email="ayse@a.test", sifre=PAROLA, okul="A Lisesi"):
    return istemci.post("/api/kayit", json={"okul": {"ad": okul}, "ad": "Ayşe Yılmaz", "email": email, "sifre": sifre})


def test_kayit_cerezi_httponly_samesite_strict_path_api(istemci):
    yanit = _kayit_yaniti(istemci)
    assert yanit.status_code == 201
    set_cookie = yanit.headers["set-cookie"]
    assert re.search(r"HttpOnly", set_cookie, re.I) and re.search(r"SameSite=strict", set_cookie, re.I)
    assert "Path=/api" in set_cookie and "Max-Age=604800" in set_cookie
    assert "Secure" not in set_cookie  # test ayarı: http
    govde = yanit.json()
    assert govde["kullanici"]["rol"] == "mudur" and govde["okul"]["ad"] == "A Lisesi"
    assert cerezden_jeton(yanit) not in yanit.text  # jeton gövdede yok


def test_secure_ayari_acikken_cerez_secure(ayarlar, oturum_fabrikasi):
    uygulama = uygulama_olustur(ayarlar.model_copy(update={"cerez_secure": True}))
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi
    with TestClient(uygulama, base_url="https://testserver") as istemci:
        assert "Secure" in _kayit_yaniti(istemci).headers["set-cookie"]
    uygulama.state.motor.dispose()


def test_ayarlar_ortam_degiskenlerinden(monkeypatch):
    monkeypatch.setenv("OKULAPI_CEREZ_SECURE", "false")
    monkeypatch.setenv("OKULAPI_IZINLI_KOKENLER", '["http://localhost:5173","https://okul.example"]')
    a = Ayarlar()
    assert a.cerez_secure is False and a.izinli_kokenler == ["http://localhost:5173", "https://okul.example"]
    monkeypatch.delenv("OKULAPI_CEREZ_SECURE")
    monkeypatch.delenv("OKULAPI_IZINLI_KOKENLER")
    assert Ayarlar().cerez_secure is True and Ayarlar().izinli_kokenler == []  # güvenli varsayılan


# --- giriş, ben, çıkış ------------------------------------------------------------------------

def test_giris_ben_cikis_akisi(istemci):
    _kayit_yaniti(istemci)
    istemci.cookies.clear()
    yanit = istemci.post("/api/giris", json={"email": "AYSE@a.test", "sifre": PAROLA})
    assert yanit.status_code == 200 and yanit.json()["kullanici"]["email"] == "ayse@a.test"
    jeton = cerezden_jeton(yanit)
    istemci.cookies.clear()

    ben = istemci.get("/api/ben", headers=cerez(jeton))
    assert ben.status_code == 200 and ben.json()["kullanici"]["ad"] == "Ayşe Yılmaz"

    cikis = istemci.post("/api/cikis", headers=cerez(jeton))
    assert cikis.status_code == 204
    assert re.search(r'oturum="?"?;.*Max-Age=0', cikis.headers["set-cookie"])  # tarayıcıdaki çerez silinir
    assert istemci.get("/api/ben", headers=cerez(jeton)).status_code == 401
    assert istemci.post("/api/cikis").status_code == 204  # oturumsuz çıkış da sorun değil


def test_yanlis_parola_ve_bilinmeyen_eposta_ayni_yaniti_alir(istemci):
    _kayit_yaniti(istemci)
    a = istemci.post("/api/giris", json={"email": "ayse@a.test", "sifre": "yanlis-parola-1234"})
    b = istemci.post("/api/giris", json={"email": "kimse@a.test", "sifre": "yanlis-parola-1234"})
    assert (a.status_code, a.json()) == (b.status_code, b.json()) == (401, {"detail": "E-posta ya da parola hatalı"})


def test_kaba_kuvvet_429_ve_retry_after(istemci):
    _kayit_yaniti(istemci)
    for _ in range(5):
        assert istemci.post("/api/giris", json={"email": "ayse@a.test", "sifre": "yanlis-parola-1234"}).status_code == 401
    yanit = istemci.post("/api/giris", json={"email": "ayse@a.test", "sifre": PAROLA})
    assert yanit.status_code == 429 and yanit.headers["Retry-After"] == "900"
    assert "15 dakika" in yanit.json()["detail"]


# --- demo oturumu (ADR 0027) ------------------------------------------------------------------

DEMO_PAROLA = "demo-okul-parolasi"


@pytest.fixture
def demo_istemci(ayarlar, oturum_fabrikasi, kuyruk):
    """OKULAPI_DEMO_PAROLA tanımlı sunucu."""
    uygulama = uygulama_olustur(ayarlar.model_copy(update={"demo_parola": DEMO_PAROLA}))
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi
    uygulama.state.kuyruk = kuyruk
    with TestClient(uygulama) as istemci:
        yield istemci
    uygulama.state.motor.dispose()


def _demo_hesabi(istemci) -> None:
    yanit = _kayit_yaniti(istemci, email=DEMO_EMAIL, sifre=DEMO_PAROLA, okul="Demo Lisesi")
    assert yanit.status_code == 201, yanit.text
    istemci.cookies.clear()


def test_demo_parolasi_yoksa_demo_kapali(istemci):
    _demo_hesabi(istemci)  # hesap olsa bile sunucu ayarı yoksa açılmaz
    assert istemci.get("/api/oturum/demo").json() == {"acik": False}
    yanit = istemci.post("/api/oturum/demo")
    assert yanit.status_code == 404 and "set-cookie" not in yanit.headers


def test_demo_oturumu_girisle_ayni_cerezi_yazar(demo_istemci):
    _demo_hesabi(demo_istemci)
    assert demo_istemci.get("/api/oturum/demo").json() == {"acik": True}
    yanit = demo_istemci.post("/api/oturum/demo")
    assert yanit.status_code == 200, yanit.text
    set_cookie = yanit.headers["set-cookie"]
    assert re.search(r"HttpOnly", set_cookie, re.I) and re.search(r"SameSite=strict", set_cookie, re.I)
    assert "Path=/api" in set_cookie
    assert DEMO_PAROLA not in yanit.text and cerezden_jeton(yanit) not in yanit.text
    assert yanit.json()["kullanici"]["email"] == DEMO_EMAIL and yanit.json()["okul"]["ad"] == "Demo Lisesi"
    demo_istemci.cookies.clear()
    assert demo_istemci.get("/api/ben", headers=cerez(cerezden_jeton(yanit))).json()["okul"]["ad"] == "Demo Lisesi"


def test_yanlis_parola_denemeleri_demoyu_kilitlemez(demo_istemci):
    _demo_hesabi(demo_istemci)
    for _ in range(5):
        demo_istemci.post("/api/giris", json={"email": DEMO_EMAIL, "sifre": "yanlis-parola-1234"})
    assert demo_istemci.post("/api/giris", json={"email": DEMO_EMAIL, "sifre": DEMO_PAROLA}).status_code == 429
    assert demo_istemci.post("/api/oturum/demo").status_code == 200


def test_kayitta_kullanilan_eposta_ve_kisa_parola(istemci):
    _kayit_yaniti(istemci)
    yanit = _kayit_yaniti(istemci, email="Ayse@A.test", okul="B Lisesi")
    assert yanit.status_code == 409 and yanit.json()["detail"] == "Bu e-posta adresi başka bir hesapta kullanılıyor"
    yanit = _kayit_yaniti(istemci, email="yeni@a.test", sifre="kisa-parola")
    assert yanit.status_code == 422 and yanit.json()["detail"] == "Parola en az 12 karakter olmalı"


# --- köken (Origin) denetimi ------------------------------------------------------------------

@pytest.mark.parametrize(
    ("koken", "beklenen"),
    [
        (None, 401),                      # tarayıcı dışı istemci: denetim yok, giriş yanlış -> 401
        (IZINLI_KOKEN, 401),              # izinli köken (Vite): denetimden geçer
        (IZINLI_KOKEN + "/", 401),
        ("http://kotu.example", 403),
        ("http://localhost:5174", 403),   # port farklı = başka köken
        ("https://localhost:5173", 403),  # şema farklı = başka köken
        ("null", 403),
    ],
)
def test_veri_degistiren_isteklerde_koken_denetimi(istemci, koken, beklenen):
    basliklar = {"Origin": koken} if koken else {}
    yanit = istemci.post("/api/giris", json={"email": "x@a.test", "sifre": "yanlis-parola-1234"}, headers=basliklar)
    assert yanit.status_code == beklenen
    if beklenen == 403:
        assert yanit.json()["detail"] == IZINSIZ_KOKEN


def test_csrf_gecerli_cerez_ve_yabanci_koken_veriyi_degistiremez(istemci):
    """Başka bir site, kullanıcının tarayıcısından onun çereziyle istek attırsa bile (SameSite'ın
    işlemediği eski bir tarayıcı varsayımı) köken denetimi durdurur."""
    okul, _ = okul_ve_ogretmen(istemci, "A Lisesi")
    ogretmen = istemci.get("/api/ogretmenler", headers=okul_basligi(okul)).json()[0]["id"]
    yanit = istemci.delete(f"/api/ogretmenler/{ogretmen}", headers={**okul_basligi(okul), "Origin": "http://kotu.example"})
    assert yanit.status_code == 403
    assert len(istemci.get("/api/ogretmenler", headers=okul_basligi(okul)).json()) == 1
    # Okuma istekleri denetlenmez (veri değiştirmez).
    assert istemci.get("/api/ogretmenler", headers={**okul_basligi(okul), "Origin": "http://kotu.example"}).status_code == 200


def test_izinli_koken_tanimlanmamissa_tarayicidan_yazma_yok(ayarlar, oturum_fabrikasi):
    uygulama = uygulama_olustur(ayarlar.model_copy(update={"izinli_kokenler": []}))
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi
    with TestClient(uygulama) as istemci:
        assert istemci.post("/api/giris", json={}, headers={"Origin": IZINLI_KOKEN}).status_code == 403
    uygulama.state.motor.dispose()


# --- kullanıcı yönetimi uçları ----------------------------------------------------------------

@pytest.fixture
def okul(istemci):
    """Müdür (Ayşe) ve yardımcı (Mehmet), ikisi de giriş yapmış."""
    _kayit_yaniti(istemci)
    istemci.cookies.clear()
    mudur = giris(istemci, "ayse@a.test")
    yanit = istemci.post("/api/kullanicilar", json={"ad": "Mehmet Kaya", "email": "Mehmet@A.test", "sifre": PAROLA},
                         headers=cerez(mudur))
    assert yanit.status_code == 201 and yanit.json()["rol"] == "mudur_yardimcisi"
    ben = istemci.get("/api/ben", headers=cerez(mudur)).json()
    return {"mudur": mudur, "mudur_id": ben["kullanici"]["id"], "yardimci_id": yanit.json()["id"],
            "yardimci": giris(istemci, "mehmet@a.test")}


def test_yardimci_listeler_ama_yonetemez(istemci, okul):
    y = cerez(okul["yardimci"])
    assert [k["ad"] for k in istemci.get("/api/kullanicilar", headers=y).json()] == ["Ayşe Yılmaz", "Mehmet Kaya"]
    for yontem, yol, govde in (
        ("POST", "/api/kullanicilar", {"ad": "X", "email": "x@a.test", "sifre": PAROLA}),
        ("PUT", f"/api/kullanicilar/{okul['mudur_id']}/sifre", {"sifre": YENI}),
        ("PUT", f"/api/kullanicilar/{okul['yardimci_id']}/rol", {"rol": "mudur"}),
        ("DELETE", f"/api/kullanicilar/{okul['mudur_id']}", None),
    ):
        yanit = istemci.request(yontem, yol, json=govde, headers=y)
        assert (yanit.status_code, yanit.json()["detail"]) == (403, "Bu işlemi yalnızca okul müdürü yapabilir"), yol
    # Okulun geri kalan verisini müdür gibi düzenler (CLAUDE.md bölüm 2).
    assert istemci.post("/api/ogretmenler", json={"ad": "Zeynep"}, headers=y).status_code == 201


def test_mudur_parola_belirleyince_yardimcinin_oturumu_kapanir(istemci, okul):
    yanit = istemci.put(f"/api/kullanicilar/{okul['yardimci_id']}/sifre", json={"sifre": YENI}, headers=cerez(okul["mudur"]))
    assert yanit.status_code == 204
    assert istemci.get("/api/ben", headers=cerez(okul["yardimci"])).status_code == 401
    assert istemci.get("/api/ben", headers=cerez(okul["mudur"])).status_code == 200
    giris(istemci, "mehmet@a.test", YENI)


def test_kendi_sifresini_degistirince_yalnizca_bu_oturum_kalir(istemci, okul):
    baska = giris(istemci, "ayse@a.test")  # ikinci bilgisayar
    yanit = istemci.put("/api/ben/sifre", json={"eski": "yanlis-parola-1234", "yeni": YENI}, headers=cerez(okul["mudur"]))
    assert (yanit.status_code, yanit.json()["detail"]) == (422, "Mevcut parola hatalı")
    yanit = istemci.put("/api/ben/sifre", json={"eski": PAROLA, "yeni": YENI}, headers=cerez(okul["mudur"]))
    assert yanit.status_code == 204
    assert istemci.get("/api/ben", headers=cerez(okul["mudur"])).status_code == 200
    assert istemci.get("/api/ben", headers=cerez(baska)).status_code == 401


def test_silinen_kullanicinin_oturumu_kapanir(istemci, okul):
    assert istemci.delete(f"/api/kullanicilar/{okul['yardimci_id']}", headers=cerez(okul["mudur"])).status_code == 204
    assert istemci.get("/api/ben", headers=cerez(okul["yardimci"])).status_code == 401


def test_son_mudur_api_ile_de_korunur(istemci, okul):
    m = cerez(okul["mudur"])
    yanit = istemci.delete(f"/api/kullanicilar/{okul['mudur_id']}", headers=m)
    assert yanit.status_code == 409 and "son müdürü silinemez" in yanit.json()["detail"]
    yanit = istemci.put(f"/api/kullanicilar/{okul['mudur_id']}/rol", json={"rol": "mudur_yardimcisi"}, headers=m)
    assert yanit.status_code == 409 and "son müdürü rolü düşürülemez" in yanit.json()["detail"]
    # Mehmet müdür olunca Ayşe rolünü bırakabilir; yeni rol bir sonraki istekte geçerli.
    assert istemci.put(f"/api/kullanicilar/{okul['yardimci_id']}/rol", json={"rol": "mudur"}, headers=m).status_code == 200
    assert istemci.put(f"/api/kullanicilar/{okul['mudur_id']}/rol", json={"rol": "mudur_yardimcisi"}, headers=m).status_code == 200
    assert istemci.post("/api/kullanicilar", json={"ad": "X", "email": "x@a.test", "sifre": PAROLA}, headers=m).status_code == 403
    assert istemci.put(f"/api/kullanicilar/{okul['mudur_id']}/rol", json={"rol": "ogretmen"},
                       headers=cerez(okul["yardimci"])).status_code == 422


def test_baska_okulun_kullanicisi_404(istemci, okul):
    b_okul, _, _ = api_ile_kayit(istemci, "B Lisesi")
    for yontem, yol, govde in (("DELETE", f"/api/kullanicilar/{okul['yardimci_id']}", None),
                               ("PUT", f"/api/kullanicilar/{okul['yardimci_id']}/sifre", {"sifre": YENI})):
        assert istemci.request(yontem, yol, json=govde, headers=okul_basligi(b_okul)).status_code == 404
    assert istemci.get("/api/ben", headers=cerez(okul["yardimci"])).status_code == 200
