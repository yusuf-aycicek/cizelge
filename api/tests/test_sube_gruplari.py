"""Şube grupları, gruba bağlı şablon, şube istisnaları ve şube grubu kapsamı (K5;
docs/kisisellestirme-plani.md bölüm 3, 6)."""

from __future__ import annotations

import uuid

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.engine import make_url

from conftest import DP, TEST_URL, bos_veritabani_olustur, okul_basligi
from okulapi.cekirdek.veritabani import motor_olustur
from okulapi.migrasyon import alembic_ayari

N = "gunluk_ders_siniri"
BLOK = "blok_deseni"


@pytest.fixture
def okul(istemci, okul_olustur):
    """11-A, 11-B, 11-C (seviye 11), 9-A; Matematik, Fizik, Din, Felsefe; "11 Sayısal" grubu."""
    b = okul_basligi(okul_olustur("Grup Lisesi", gun_sayisi=5, gunluk_ders_saati=8))

    def ekle(yol, govde):
        yanit = istemci.post(yol, json=govde, headers=b)
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    k = {"b": b}
    for ad, seviye in (("11-A", 11), ("11-B", 11), ("11-C", 11), ("9-A", 9)):
        k[ad] = ekle("/api/siniflar", {"ad": ad, "seviye": seviye})
    for ad in ("Matematik", "Fizik", "Din", "Felsefe"):
        k[ad] = ekle("/api/dersler", {"ad": ad})
    k["say"] = ekle("/api/sube-gruplari", {"ad": "11 Sayısal", "seviye": 11})
    return k


def grupla(istemci, okul, sube, grup):
    return istemci.patch(f"/api/siniflar/{okul[sube]}", json={"sube_grubu_id": grup}, headers=okul["b"])


def sablon(istemci, okul, ders, saat, seviye=11, grup=None):
    govde = {"seviye": seviye, "ders_id": okul[ders], "haftalik_saat": saat}
    if grup:
        govde["sube_grubu_id"] = grup
    yanit = istemci.post(f"{DP}/seviye-sablonlari", json=govde, headers=okul["b"])
    assert yanit.status_code == 201, yanit.text
    return yanit.json()


def uygula(istemci, okul, seviye=11, grup=None):
    govde = {"seviye": seviye, **({"sube_grubu_id": grup} if grup else {})}
    yanit = istemci.post(f"{DP}/seviye-sablonlari/uygula", json=govde, headers=okul["b"])
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def dersleri(istemci, okul, sube) -> dict[str, int]:
    ad = {okul[d]: d for d in ("Matematik", "Fizik", "Din", "Felsefe")}
    return {ad[a["ders_id"]]: a["haftalik_saat"] for a in istemci.get(f"{DP}/atamalar", headers=okul["b"]).json()
            if a["sinif_id"] == okul[sube]}


# --- şube grupları ----------------------------------------------------------------------------


def test_sube_gruba_alinir_ve_cikarilir(istemci, okul):
    yanit = grupla(istemci, okul, "11-A", okul["say"])
    assert yanit.status_code == 200 and yanit.json()["sube_grubu_id"] == okul["say"]
    assert grupla(istemci, okul, "11-A", None).json()["sube_grubu_id"] is None


def test_grubun_seviyesi_subeninkiyle_ayni_olmali(istemci, okul):
    yanit = grupla(istemci, okul, "9-A", okul["say"])
    assert yanit.status_code == 422
    assert yanit.json()["detail"] == '9-A 9. sınıf; 11. sınıfların grubu "11 Sayısal" içine alınamaz'
    grupla(istemci, okul, "11-A", okul["say"])
    yanit = istemci.patch(f"/api/siniflar/{okul['11-A']}", json={"seviye": 10}, headers=okul["b"])
    assert yanit.status_code == 422 and "gruptan çıkarın" in yanit.json()["detail"]


def test_grup_adi_okulda_tek_ve_seviyesi_degismez(istemci, okul):
    b = okul["b"]
    assert istemci.post("/api/sube-gruplari", json={"ad": "11 Sayısal", "seviye": 11}, headers=b).status_code == 409
    yanit = istemci.patch(f"/api/sube-gruplari/{okul['say']}", json={"ad": "11 Fen", "seviye": 10}, headers=b)
    assert yanit.status_code == 200 and yanit.json() == {"id": okul["say"], "ad": "11 Fen", "seviye": 11}


def test_baska_okulun_grubu_kullanilamaz(istemci, okul, okul_olustur):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    sube = istemci.post("/api/siniflar", json={"ad": "11-X", "seviye": 11}, headers=b2).json()["id"]
    yanit = istemci.patch(f"/api/siniflar/{sube}", json={"sube_grubu_id": okul["say"]}, headers=b2)
    assert yanit.status_code == 422 and yanit.json()["detail"] == "Şube grubu bu okulda bulunamadı"
    assert istemci.get("/api/sube-gruplari", headers=b2).json() == []
    assert istemci.delete(f"/api/sube-gruplari/{okul['say']}", headers=b2).status_code == 404


def test_grup_silinince_subeler_grupsuz_kalir_sablonu_ve_ozel_ayarlari_silinir(istemci, okul):
    b = okul["b"]
    grupla(istemci, okul, "11-A", okul["say"])
    sablon(istemci, okul, "Fizik", 4, grup=okul["say"])
    istemci.put(f"{DP}/kurallar/{N}/ozel", json={"kapsam": {"sube_grubu_id": okul["say"]}, "parametreler": {"n": 3}},
                headers=b)
    assert istemci.delete(f"/api/sube-gruplari/{okul['say']}", headers=b).status_code == 204
    assert istemci.get(f"/api/siniflar/{okul['11-A']}", headers=b).json()["sube_grubu_id"] is None
    assert istemci.get(f"{DP}/seviye-sablonlari", headers=b).json() == []
    kural = next(k for k in istemci.get(f"{DP}/kurallar", headers=b).json() if k["tur"] == N)
    assert kural["ozel_ayarlar"] == []


# --- gruba bağlı şablon -------------------------------------------------------------------------


def test_grubun_sablonu_grubun_subelerine_seviyeninki_ötekilere_uygulanir(istemci, okul):
    grupla(istemci, okul, "11-A", okul["say"])
    grupla(istemci, okul, "11-B", okul["say"])
    sablon(istemci, okul, "Matematik", 4)  # 11. sınıflar
    sablon(istemci, okul, "Matematik", 6, grup=okul["say"])
    sablon(istemci, okul, "Fizik", 4, grup=okul["say"])

    seviye = uygula(istemci, okul)
    assert (seviye["subeler"], seviye["olusturulan"]) == (["11-C"], 1)
    assert seviye["baska_sablonlu"] == [{"sinif": "11-A", "sablon": "11 Sayısal"},
                                        {"sinif": "11-B", "sablon": "11 Sayısal"}]
    grup = uygula(istemci, okul, grup=okul["say"])
    assert (grup["subeler"], grup["olusturulan"]) == (["11-A", "11-B"], 4)
    assert grup["baska_sablonlu"] == [{"sinif": "11-C", "sablon": "11. sınıflar"}]
    assert dersleri(istemci, okul, "11-A") == {"Matematik": 6, "Fizik": 4}
    assert dersleri(istemci, okul, "11-C") == {"Matematik": 4}


def test_bos_grup_sablonu_varken_grubun_subeleri_seviyenin_sablonunu_kullanir(istemci, okul):
    grupla(istemci, okul, "11-A", okul["say"])
    sablon(istemci, okul, "Matematik", 4)
    assert uygula(istemci, okul)["subeler"] == ["11-A", "11-B", "11-C"]


def test_grup_sablonunun_seviyesi_grubunki_olmali(istemci, okul):
    yanit = istemci.post(f"{DP}/seviye-sablonlari", headers=okul["b"],
                         json={"seviye": 9, "ders_id": okul["Fizik"], "haftalik_saat": 2, "sube_grubu_id": okul["say"]})
    assert yanit.status_code == 422
    assert yanit.json()["detail"] == '"11 Sayısal" 11. sınıfların grubu; şablonu 11. sınıf olmalı'


def test_ayni_derse_seviye_ve_grup_sablonunda_ayri_satir_ayni_sablonda_tek(istemci, okul):
    sablon(istemci, okul, "Fizik", 2)
    sablon(istemci, okul, "Fizik", 4, grup=okul["say"])
    yanit = istemci.post(f"{DP}/seviye-sablonlari", json={"seviye": 11, "ders_id": okul["Fizik"], "haftalik_saat": 3},
                         headers=okul["b"])
    assert yanit.status_code == 409  # NULLS NOT DISTINCT: seviyenin şablonunda bir ders bir kez


def test_migration_var_olan_seviye_sablonlarini_korur():
    """K5 öncesi şablon satırları seviyenin şablonu olarak kalır; benzersizlik korunur."""
    url = make_url(TEST_URL).set(database="okul_test_sube_grubu").render_as_string(hide_password=False)
    bos_veritabani_olustur(url)
    ayar = alembic_ayari(veritabani_url=url)
    command.upgrade(ayar, "ders_programi_0006")
    okul, ders = uuid.uuid4(), uuid.uuid4()
    motor = motor_olustur(url)
    try:
        with motor.begin() as b:
            b.execute(text("INSERT INTO okul (id, ad) VALUES (:id, 'A')"), {"id": okul})
            b.execute(text("INSERT INTO ders (id, okul_id, ad) VALUES (:id, :o, 'Fizik')"),
                      {"id": ders, "o": okul})
            b.execute(text("INSERT INTO seviye_sablonu (id, okul_id, seviye, ders_id, haftalik_saat) "
                           "VALUES (:id, :o, 9, :d, 2)"), {"id": uuid.uuid4(), "o": okul, "d": ders})
        command.upgrade(ayar, "heads")
        with motor.connect() as b:
            assert b.execute(text("SELECT seviye, sube_grubu_id, haftalik_saat FROM seviye_sablonu")).all() == [(9, None, 2)]
            with pytest.raises(Exception, match="uq_seviye_sablonu_okul_id_seviye_sube_grubu_id_ders_id"):
                b.execute(text("INSERT INTO seviye_sablonu (id, okul_id, seviye, ders_id, haftalik_saat) "
                               "VALUES (:id, :o, 9, :d, 3)"), {"id": uuid.uuid4(), "o": okul, "d": ders})
        command.downgrade(ayar, "ders_programi_0006")
        with motor.connect() as b:
            assert b.execute(text("SELECT seviye, haftalik_saat FROM seviye_sablonu")).all() == [(9, 2)]
    finally:
        motor.dispose()


# --- şube istisnaları ---------------------------------------------------------------------------


def istisna(istemci, okul, sube, ders, tur, saat=None):
    govde = {"sinif_id": okul[sube], "ders_id": okul[ders], "tur": tur, **({"haftalik_saat": saat} if saat else {})}
    return istemci.post(f"{DP}/istisnalar", json=govde, headers=okul["b"])


def test_almaz_istisnasi_dersi_kaldirir_ve_sablon_yeniden_uygulaninca_geri_gelmez(istemci, okul):
    sablon(istemci, okul, "Matematik", 4)
    sablon(istemci, okul, "Din", 2)
    uygula(istemci, okul)
    yanit = istisna(istemci, okul, "11-B", "Din", "almaz")
    assert yanit.status_code == 201
    assert {k: yanit.json()[k] for k in ("tur", "sinif_adi", "ders_adi", "sablonda", "atanmis", "uyari")} == {
        "tur": "almaz", "sinif_adi": "11-B", "ders_adi": "Din", "sablonda": True, "atanmis": False, "uyari": None}
    assert dersleri(istemci, okul, "11-B") == {"Matematik": 4}

    rapor = uygula(istemci, okul)
    assert rapor["olusturulan"] == 0 and rapor["istisna_atlanan"] == [{"sinif": "11-B", "ders": "Din"}]
    assert dersleri(istemci, okul, "11-B") == {"Matematik": 4}  # Din geri gelmedi
    assert dersleri(istemci, okul, "11-A") == {"Matematik": 4, "Din": 2}

    # İşaret kaldırılınca ders şablondaki saatle geri gelir.
    kaldir = istemci.delete(f"{DP}/istisnalar/{yanit.json()['id']}", headers=okul["b"])
    assert kaldir.status_code == 200 and kaldir.json() == {"geri_eklenen_saat": 2}
    assert dersleri(istemci, okul, "11-B") == {"Matematik": 4, "Din": 2}
    assert istemci.get(f"{DP}/istisnalar", headers=okul["b"]).json() == []


def test_ek_istisnasi_dersi_ekler_ve_raporda_gorunur(istemci, okul):
    sablon(istemci, okul, "Matematik", 4)
    yanit = istisna(istemci, okul, "11-A", "Felsefe", "ek", saat=2)
    assert yanit.status_code == 201 and yanit.json()["sablonda"] is False
    assert dersleri(istemci, okul, "11-A") == {"Felsefe": 2}
    rapor = uygula(istemci, okul)
    assert rapor["istisna_ek"] == [{"sinif": "11-A", "ders": "Felsefe", "haftalik_saat": 2, "eklendi": False}]
    assert dersleri(istemci, okul, "11-A") == {"Matematik": 4, "Felsefe": 2}

    # Ek ders silinince "ek" istisnası da kalkar: şablon uygulanınca geri gelmez.
    atama = next(a for a in istemci.get(f"{DP}/atamalar", headers=okul["b"]).json()
                 if a["sinif_id"] == okul["11-A"] and a["ders_id"] == okul["Felsefe"])
    assert istemci.delete(f"{DP}/atamalar/{atama['id']}", headers=okul["b"]).status_code == 204
    assert istemci.get(f"{DP}/istisnalar", headers=okul["b"]).json() == []
    assert uygula(istemci, okul)["istisna_ek"] == []
    assert dersleri(istemci, okul, "11-A") == {"Matematik": 4}


def test_ek_dersi_silinmisse_sablon_uygulaninca_eklenir(istemci, okul, oturum_fabrikasi):
    sablon(istemci, okul, "Matematik", 4)
    istisna(istemci, okul, "11-A", "Felsefe", "ek", saat=2)
    # Atama istisnayı kaldırmadan (veritabanından) silinmiş: liste uyarır, uygulama ekler.
    from okulapi.cekirdek.kiraci import okul_oturumu
    from okulapi.moduller.ders_programi.modeller import DersAtama

    okul_id = istemci.get("/api/okul", headers=okul["b"]).json()["id"]
    with okul_oturumu(oturum_fabrikasi, uuid.UUID(okul_id)) as o:
        o.query(DersAtama).filter(DersAtama.ders_id == uuid.UUID(okul["Felsefe"])).delete()
        o.commit()
    [i] = istemci.get(f"{DP}/istisnalar", headers=okul["b"]).json()
    assert i["uyari"] == "Felsefe 11-A'nin ek dersi, ama şubede yok; şablonu uygulayınca eklenir."
    rapor = uygula(istemci, okul)
    assert rapor["istisna_ek"] == [{"sinif": "11-A", "ders": "Felsefe", "haftalik_saat": 2, "eklendi": True}]
    assert dersleri(istemci, okul, "11-A") == {"Matematik": 4, "Felsefe": 2}


def test_almaz_ama_atanmis_ise_uyarilir_otomatik_duzeltilmez(istemci, okul):
    istisna(istemci, okul, "11-B", "Din", "almaz")
    istemci.post(f"{DP}/atamalar", json={"sinif_id": okul["11-B"], "ders_id": okul["Din"], "haftalik_saat": 2},
                 headers=okul["b"])
    [i] = istemci.get(f"{DP}/istisnalar", headers=okul["b"]).json()
    assert i["atanmis"] is True
    assert i["uyari"] == "11-B için \"Din almaz\" istisnası var, ama 11-B'ye Din atanmış."


def test_istisna_dogrulamasi_ve_tekligi(istemci, okul):
    assert istisna(istemci, okul, "11-A", "Din", "ek").status_code == 422  # saat yok
    assert istisna(istemci, okul, "11-A", "Din", "almaz", saat=2).status_code == 422
    assert istisna(istemci, okul, "11-A", "Din", "almaz").status_code == 201
    yanit = istisna(istemci, okul, "11-A", "Din", "ek", saat=2)
    assert yanit.status_code == 409 and yanit.json()["detail"] == "Bu şubenin bu ders için zaten bir istisnası var"


def test_istisnalar_okul_ici(istemci, okul, okul_olustur):
    i = istisna(istemci, okul, "11-A", "Din", "almaz").json()
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    assert istemci.get(f"{DP}/istisnalar", headers=b2).json() == []
    assert istemci.delete(f"{DP}/istisnalar/{i['id']}", headers=b2).status_code == 404
    yanit = istemci.post(f"{DP}/istisnalar", headers=b2,
                         json={"sinif_id": okul["11-A"], "ders_id": okul["Din"], "tur": "almaz"})
    assert yanit.status_code == 422 and yanit.json()["detail"] == "Şube bu okulda bulunamadı"


def test_sube_silinince_istisnasi_da_silinir(istemci, okul):
    istisna(istemci, okul, "9-A", "Din", "almaz")
    assert istemci.delete(f"/api/siniflar/{okul['9-A']}", headers=okul["b"]).status_code == 204
    assert istemci.get(f"{DP}/istisnalar", headers=okul["b"]).json() == []


# --- şube grubu kapsamı (ADR 0016) --------------------------------------------------------------


def ozel(istemci, okul, tur, kapsam, parametreler):
    return istemci.put(f"{DP}/kurallar/{tur}/ozel", json={"kapsam": kapsam, "parametreler": parametreler},
                       headers=okul["b"])


def test_gunluk_sinir_ve_blok_sekli_gruba_ozel_verilebilir(istemci, okul):
    k = {x["tur"]: x for x in istemci.get(f"{DP}/kurallar", headers=okul["b"]).json()}
    assert k[N]["kapsamlar"] == ["ders", "sube", "sube_grubu"]
    assert k[BLOK]["kapsamlar"] == ["ders", "sube", "sube_grubu"]
    assert k["ogretmen_gunluk_siniri"]["kapsamlar"] == ["ogretmen"]

    yanit = ozel(istemci, okul, N, {"ders_id": okul["Matematik"], "sube_grubu_id": okul["say"]}, {"n": 3})
    assert yanit.status_code == 200
    assert yanit.json()["ozel_ayarlar"] == [{
        "kapsam": {"ders_id": okul["Matematik"], "sinif_id": None, "sube_grubu_id": okul["say"], "ogretmen_id": None},
        "ad": "11 Sayısal grubu · Matematik", "parametreler": {"n": 3}}]
    assert ozel(istemci, okul, BLOK, {"ders_id": okul["Matematik"], "sube_grubu_id": okul["say"]},
                {"desen": [3, 3]}).status_code == 200


def test_grup_kapsami_onceligi_ders_sube_grup(istemci, okul):
    """ders + şube (6) > ders + şube grubu (5) > ders (4) > şube grubu (1) > okul (0): dağılım şekli
    ucu (çözücüyle aynı hesap) hangi ayarın kazandığını söyler."""
    b = okul["b"]
    grupla(istemci, okul, "11-A", okul["say"])
    grupla(istemci, okul, "11-B", okul["say"])
    for sube in ("11-A", "11-B", "11-C"):
        istemci.post(f"{DP}/atamalar", json={"sinif_id": okul[sube], "ders_id": okul["Matematik"], "haftalik_saat": 6},
                     headers=b)
    ozel(istemci, okul, N, {"sube_grubu_id": okul["say"]}, {"n": 3})
    ozel(istemci, okul, BLOK, {"ders_id": okul["Matematik"]}, {"desen": [2, 2, 2]})
    ozel(istemci, okul, BLOK, {"ders_id": okul["Matematik"], "sube_grubu_id": okul["say"]}, {"desen": [3, 3]})
    ozel(istemci, okul, BLOK, {"ders_id": okul["Matematik"], "sinif_id": okul["11-B"]}, {"desen": [3, 2, 1]})
    sekiller = {s["sinif_adi"]: (s["metin"], s["kaynak"]) for s in istemci.get(f"{DP}/dagilim-sekilleri", headers=b).json()}
    assert sekiller == {"11-A": ("3+3", "ders_grup"), "11-B": ("3+2+1", "ders_sube"), "11-C": ("2+2+2", "ders")}
    # Gruba özel N = 3 yalnızca grupta: 11-C'de 3 saatlik blok ön kontrolde takılırdı (N = 2).
    celiskiler = istemci.get(f"{DP}/on-kontrol", headers=b).json()["celiskiler"]
    assert [c for c in celiskiler if c["tur"] != "ogretmen_secilmemis"] == []


def test_sube_ile_grup_ayni_kapsamda_olamaz_baska_okulun_grubu_reddedilir(istemci, okul, okul_olustur):
    yanit = ozel(istemci, okul, N, {"sinif_id": okul["11-A"], "sube_grubu_id": okul["say"]}, {"n": 3})
    assert yanit.status_code == 422 and "şube grubu birlikte bulunamaz" in yanit.json()["detail"]
    yanit = ozel(istemci, okul, "ogretmen_gunluk_siniri", {"sube_grubu_id": okul["say"]}, {"m": 6})
    assert yanit.status_code == 422 and yanit.json()["detail"] == '"Öğretmenin günlük ders sınırı" kuralı şube grubuna özel ayarlanamaz'
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    yanit = istemci.put(f"{DP}/kurallar/{N}/ozel", json={"kapsam": {"sube_grubu_id": okul["say"]}, "parametreler": {"n": 3}},
                        headers=b2)
    assert yanit.status_code == 422 and yanit.json()["detail"] == "Şube grubu bu okulda bulunamadı"


def test_gruba_ozel_ayar_kaldirilir(istemci, okul):
    ozel(istemci, okul, N, {"sube_grubu_id": okul["say"]}, {"n": 3})
    yanit = istemci.delete(f"{DP}/kurallar/{N}/ozel", params={"sube_grubu_id": okul["say"]}, headers=okul["b"])
    assert yanit.status_code == 200 and yanit.json()["ozel_ayarlar"] == []
