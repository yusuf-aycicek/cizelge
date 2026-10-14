"""Ders programı modülü: CRUD, iş kuralları, bileşik yabancı anahtarlar, silme davranışları, şablon."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.modeller import DersAtama, Program, Yerlesim


@pytest.fixture
def okul(istemci, okul_olustur):
    """9-A, 9-B (seviye 9), 10-A; Matematik, Fizik; Ayşe ve Zeynep."""
    okul_id = okul_olustur("A Lisesi", gun_sayisi=5, gunluk_ders_saati=6)
    b = okul_basligi(okul_id)

    def ekle(yol, govde):
        yanit = istemci.post(yol, json=govde, headers=b)
        assert yanit.status_code == 201, yanit.text
        return yanit.json()["id"]

    kim = {
        "okul": okul_id,
        "9a": ekle("/api/siniflar", {"ad": "9-A", "seviye": 9}),
        "9b": ekle("/api/siniflar", {"ad": "9-B", "seviye": 9}),
        "10a": ekle("/api/siniflar", {"ad": "10-A", "seviye": 10}),
        "mat": ekle("/api/dersler", {"ad": "Matematik", "kisa_ad": "MAT"}),
        "fiz": ekle("/api/dersler", {"ad": "Fizik", "kisa_ad": "FIZ"}),
        "ayse": ekle("/api/ogretmenler", {"ad": "Ayşe Yılmaz"}),
        "zeynep": ekle("/api/ogretmenler", {"ad": "Zeynep Demir"}),
    }
    kim["baslik"] = b
    return kim


def atama_olustur(istemci, okul, sinif="9a", ders="mat", ogretmen="ayse", saat=6):
    return istemci.post(f"{DP}/atamalar", headers=okul["baslik"], json={
        "sinif_id": okul[sinif], "ders_id": okul[ders],
        "ogretmen_id": okul[ogretmen] if ogretmen else None, "haftalik_saat": saat})


# --- ders atama ---------------------------------------------------------------------------


def test_atama_crud_ve_ogretmeni_bosaltma(istemci, okul):
    yanit = atama_olustur(istemci, okul)
    assert yanit.status_code == 201
    atama = yanit.json()
    yol = f"{DP}/atamalar/{atama['id']}"
    yanit = istemci.patch(yol, json={"ogretmen_id": None}, headers=okul["baslik"])
    assert yanit.status_code == 200 and yanit.json()["ogretmen_id"] is None
    yanit = istemci.patch(yol, json={"ogretmen_id": okul["zeynep"], "haftalik_saat": 4}, headers=okul["baslik"])
    assert yanit.json()["ogretmen_id"] == okul["zeynep"] and yanit.json()["haftalik_saat"] == 4


def test_bir_sinif_bir_ders_bir_atama(istemci, okul):
    assert atama_olustur(istemci, okul).status_code == 201
    yanit = atama_olustur(istemci, okul, ogretmen="zeynep")
    assert yanit.status_code == 409
    assert "zaten atanmış" in yanit.json()["detail"]


def test_baska_okulun_ogretmeni_atanamaz(istemci, okul, okul_olustur):
    b = okul_basligi(okul_olustur("B Lisesi"))
    b_ogretmen = istemci.post("/api/ogretmenler", json={"ad": "B'nin öğretmeni"}, headers=b).json()["id"]
    yanit = istemci.post(f"{DP}/atamalar", headers=okul["baslik"], json={
        "sinif_id": okul["9a"], "ders_id": okul["mat"], "ogretmen_id": b_ogretmen, "haftalik_saat": 2})
    assert yanit.status_code == 422
    assert yanit.json()["detail"] == "Öğretmen bu okulda bulunamadı"


# --- bileşik yabancı anahtar: veritabanının kendisi reddeder ------------------------------


def test_bilesik_yabanci_anahtar_okullar_arasi_iliskiyi_reddeder(istemci, okul, okul_olustur, oturum_fabrikasi):
    """Uygulama katmanı atlanır (ham SQL): A'nın atamasını B'nin öğretmenine bağlamaya çalış."""
    b = okul_basligi(okul_olustur("B Lisesi"))
    b_ogretmen = istemci.post("/api/ogretmenler", json={"ad": "B'nin öğretmeni"}, headers=b).json()["id"]
    ekle = text("INSERT INTO ders_atama (id, okul_id, sinif_id, ders_id, ogretmen_id, haftalik_saat) "
                "VALUES (:id, :okul, :sinif, :ders, :ogretmen, 2)")
    # A'nın bağlamında (RLS bu satırı A'nın satırı olarak kabul eder); yabancı anahtar reddeder.
    with okul_oturumu(oturum_fabrikasi, uuid.UUID(okul["okul"])) as oturum:
        with pytest.raises(IntegrityError) as hata:
            oturum.execute(ekle, {"id": uuid.uuid4(), "okul": okul["okul"], "sinif": okul["9a"],
                                  "ders": okul["mat"], "ogretmen": b_ogretmen})
        assert hata.value.orig.sqlstate == "23503"  # foreign_key_violation
        assert "fk_ders_atama_okul_id_ogretmen_id_ogretmen" in str(hata.value.orig)
        oturum.rollback()
        # MATCH SIMPLE: öğretmen boşken bileşik anahtar denetlenmez, kayıt eklenebilir.
        oturum.execute(ekle, {"id": uuid.uuid4(), "okul": okul["okul"], "sinif": okul["9a"],
                              "ders": okul["mat"], "ogretmen": None})


# --- müsaitlik ------------------------------------------------------------------------------


def test_musaitlik_okul_ayarlarinin_icinde_olmali(istemci, okul):
    govde = {"ogretmen_id": okul["ayse"], "gun": 4, "saat": 5, "durum": "gelemez"}
    assert istemci.post(f"{DP}/musaitlikler", json=govde, headers=okul["baslik"]).status_code == 201
    yanit = istemci.post(f"{DP}/musaitlikler", json={**govde, "saat": 6}, headers=okul["baslik"])
    assert yanit.status_code == 422 and "günde 6 saat" in yanit.json()["detail"]
    assert istemci.post(f"{DP}/musaitlikler", json=govde, headers=okul["baslik"]).status_code == 409
    yanit = istemci.post(f"{DP}/musaitlikler", json={**govde, "durum": "belki"}, headers=okul["baslik"])
    assert yanit.status_code == 422


def test_ogretmen_silinince_musaitligi_de_silinir_ama_atamasi_varsa_silinemez(istemci, okul):
    b = okul["baslik"]
    istemci.post(f"{DP}/musaitlikler", json={"ogretmen_id": okul["zeynep"], "gun": 0, "saat": 0, "durum": "gelemez"},
                 headers=b)
    assert istemci.delete(f"/api/ogretmenler/{okul['zeynep']}", headers=b).status_code == 204  # CASCADE
    assert istemci.get(f"{DP}/musaitlikler", headers=b).json() == []

    atama_olustur(istemci, okul)
    yanit = istemci.delete(f"/api/ogretmenler/{okul['ayse']}", headers=b)  # RESTRICT
    assert yanit.status_code == 409 and "kullanılıyor" in yanit.json()["detail"]


# --- kısıt (çözücünün kayıt defteriyle doğrulanır) --------------------------------------------


@pytest.mark.parametrize("govde, durum, parca", [
    ({"tur": "gunluk_ders_siniri", "parametreler": {"n": 3}}, 201, None),
    ({"tur": "bos_gun", "zorunlu": False, "agirlik": 6, "parametreler": {"hedef_bos_gun": 1}}, 201, None),
    ({"tur": "uydurma"}, 422, "Bilinmeyen kısıt türü"),
    ({"tur": "tercih_etmez", "zorunlu": True}, 422, "yalnızca esnek"),
    ({"tur": "gunluk_ders_siniri", "parametreler": {"n": 0}}, 422, "geçersiz parametre"),
])
def test_kisit_cozucunun_kurallariyla_dogrulanir(istemci, okul, govde, durum, parca):
    yanit = istemci.post(f"{DP}/kisitlar", json=govde, headers=okul["baslik"])
    assert yanit.status_code == durum, yanit.text
    if parca:
        assert parca in yanit.json()["detail"]


def test_ayni_kural_iki_kez_tanimlanamaz(istemci, okul):
    govde = {"tur": "ogretmen_gunluk_siniri", "parametreler": {"m": 6}}
    assert istemci.post(f"{DP}/kisitlar", json=govde, headers=okul["baslik"]).status_code == 201
    assert istemci.post(f"{DP}/kisitlar", json=govde, headers=okul["baslik"]).status_code == 409


# --- seviye şablonu ---------------------------------------------------------------------------


def test_sablon_seviyedeki_subelere_uygulanir_ve_coğaltmaz(istemci, okul):
    b = okul["baslik"]
    for ders, saat in (("mat", 6), ("fiz", 3)):
        assert istemci.post(f"{DP}/seviye-sablonlari", json={"seviye": 9, "ders_id": okul[ders], "haftalik_saat": saat},
                            headers=b).status_code == 201
    atama_olustur(istemci, okul, sinif="9a", ders="mat", saat=5)  # elle girilmiş, şablondan farklı

    sonuc = istemci.post(f"{DP}/seviye-sablonlari/uygula", json={"seviye": 9}, headers=b).json()
    assert sonuc["sube_sayisi"] == 2 and sonuc["olusturulan"] == 3 and sonuc["zaten_var"] == 1
    assert [(f["sinif"], f["ders"], f["atamadaki_saat"], f["sablondaki_saat"]) for f in sonuc["farkli_saatli"]] == [
        ("9-A", "Matematik", 5, 6)]

    atamalar = istemci.get(f"{DP}/atamalar", headers=b).json()
    assert len(atamalar) == 4
    assert {a["sinif_id"] for a in atamalar} == {okul["9a"], okul["9b"]}  # 10-A'ya dokunulmadı
    yeni = [a for a in atamalar if not (a["sinif_id"] == okul["9a"] and a["ders_id"] == okul["mat"])]
    assert all(a["ogretmen_id"] is None for a in yeni)

    tekrar = istemci.post(f"{DP}/seviye-sablonlari/uygula", json={"seviye": 9}, headers=b).json()
    assert tekrar["olusturulan"] == 0 and tekrar["zaten_var"] == 4
    assert len(istemci.get(f"{DP}/atamalar", headers=b).json()) == 4


# --- program ve yerleşim: silme davranışları (veritabanı düzeyi) ------------------------------


def test_program_silme_davranislari(istemci, okul, oturum_fabrikasi):
    atama_id = uuid.UUID(atama_olustur(istemci, okul).json()["id"])
    okul_id = uuid.UUID(okul["okul"])
    with okul_oturumu(oturum_fabrikasi, okul_id) as oturum:
        p1 = Program(ad="Eylül")
        oturum.add(p1)
        oturum.flush()
        p2 = Program(ad="Ekim", temel_program_id=p1.id)
        oturum.add_all([p2, Yerlesim(program_id=p1.id, ders_atama_id=atama_id, gun=1, saat=0, kilitli=True)])
        oturum.commit()
        p1_id, p2_id = p1.id, p2.id

        oturum.delete(p1)
        oturum.commit()
        oturum.expire_all()
        p2 = oturum.get(Program, p2_id)
        assert p2.temel_program_id is None and p2.okul_id == okul_id  # SET NULL (temel_program_id)
        assert oturum.scalars(select(Yerlesim).where(Yerlesim.program_id == p1_id)).all() == []  # CASCADE

        oturum.add(Yerlesim(program_id=p2_id, ders_atama_id=atama_id, gun=2, saat=3))
        oturum.commit()
        oturum.delete(oturum.get(DersAtama, atama_id))
        oturum.commit()
        assert oturum.scalars(select(Yerlesim)).all() == []  # atama silinince yerleşimleri de

    yanit = istemci.get(f"{DP}/programlar/{p2_id}", headers=okul["baslik"])
    assert yanit.status_code == 200 and yanit.json()["durum"] == "bekliyor"
    assert istemci.get(f"{DP}/programlar/{p1_id}", headers=okul["baslik"]).status_code == 404


def test_baska_okulun_modul_kayitlari_gorunmez(istemci, okul, okul_olustur):
    atama_olustur(istemci, okul)
    b = okul_basligi(okul_olustur("B Lisesi"))
    assert istemci.get(f"{DP}/atamalar", headers=b).json() == []
    a_atama = istemci.get(f"{DP}/atamalar", headers=okul["baslik"]).json()[0]["id"]
    assert istemci.get(f"{DP}/atamalar/{a_atama}", headers=b).status_code == 404
