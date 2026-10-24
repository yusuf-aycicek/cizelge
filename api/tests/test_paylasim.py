"""Paylaşım linkleri (8b-2, ADR 0022): yönetici işlemleri ve girişsiz okumanın güvenlik kuralları.

Güvenlik kuralları (mutasyon denemesi bunlarda yapıldı, plan 8b-2):
- iptal edilen ya da yenilenen link çalışmaz;
- başka okulun programına link üzerinden erişilemez;
- öğretmen linki başka öğretmenin, şube linki başka şubenin programını göstermez;
- girişsiz istek okul bağlamı açmaz; fonksiyon dar yetkili bir rolle çalışır.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import func, select, text

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okulsuz_oturum
from test_cikti import hazir_program  # noqa: F401  (fikstür)
from test_program_uretimi import okul, uret, worker_calistir  # noqa: F401

LINK = f"{DP}/paylasim-linkleri"
ACIK = f"{DP}/paylasim"


def link(istemci, okul, tur, **kapsam):
    yanit = istemci.post(LINK, json={"tur": tur, **kapsam}, headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def ac(istemci, jeton, yol=""):
    istemci.cookies.clear()
    return istemci.get(f"{ACIK}/{jeton}{yol}")  # çerez yok: girişsiz


def adlar(icerik, tur):
    return [c["ad"] for c in icerik[tur]]


@pytest.fixture
def yayinda(istemci, okul, hazir_program):
    assert istemci.put(f"{DP}/yayin", json={"program_id": hazir_program}, headers=okul["baslik"]).status_code == 200
    return hazir_program


def test_ogretmen_linki_yalnizca_o_ogretmenin_programini_gosterir(istemci, okul, yayinda):
    ayse = link(istemci, okul, "ogretmen", ogretmen_id=okul["harita"]["o-ayse"])
    assert ayse["hedef_adi"] == "Ayşe Yılmaz" and len(ayse["jeton"]) >= 43
    yanit = ac(istemci, ayse["jeton"])
    assert yanit.status_code == 200, yanit.text
    icerik = yanit.json()
    assert icerik["yayinda"] is True and icerik["okul"] == "Mini Lisesi" and icerik["program"] == "Eylül Programı"
    assert adlar(icerik, "ogretmenler") == ["Ayşe Yılmaz"] and icerik["subeler"] == []
    assert all(h["ogretmen"] == "Ayşe Yılmaz" for h in icerik["ogretmenler"][0]["hucreler"])
    assert "kimlik" not in icerik["ogretmenler"][0]  # veritabanı kimliği dışarı verilmez
    assert yanit.headers["cache-control"] == "no-store" and yanit.headers["referrer-policy"] == "no-referrer"
    # PDF: yalnızca Ayşe; başka öğretmen adıyla istemek de bir şey vermez.
    pdf = ac(istemci, ayse["jeton"], "/program.pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    metin = [s.extract_text() for s in PdfReader(BytesIO(pdf.content)).pages]
    assert len(metin) == 1 and "Ayşe Yılmaz haftalık ders programı" in metin[0]
    assert ac(istemci, ayse["jeton"], "/program.pdf?ogretmen=Ali%20%C3%87elik").status_code == 404
    assert ac(istemci, ayse["jeton"], "/program.pdf?sube=9-A").status_code == 404


def test_sube_linki_yalnizca_o_subeyi_okul_linki_hepsini_gosterir(istemci, okul, yayinda):
    sube = ac(istemci, link(istemci, okul, "sube", sinif_id=okul["harita"]["s-9b"])["jeton"]).json()
    assert adlar(sube, "subeler") == ["9-B"] and sube["ogretmenler"] == []
    hepsi = ac(istemci, link(istemci, okul, "okul")["jeton"]).json()
    assert adlar(hepsi, "subeler") == ["9-A", "9-B", "10-A"] and len(hepsi["ogretmenler"]) == 5
    pdf = ac(istemci, link(istemci, okul, "okul")["jeton"], "/program.pdf?ogretmen=Ali%20%C3%87elik")
    assert pdf.status_code == 200 and len(PdfReader(BytesIO(pdf.content)).pages) == 1


def test_iptal_ve_yenilenen_link_calismaz(istemci, okul, yayinda):
    ayse = link(istemci, okul, "ogretmen", ogretmen_id=okul["harita"]["o-ayse"])
    yeni = istemci.post(f"{LINK}/{ayse['id']}/yenile", headers=okul["baslik"]).json()
    assert yeni["id"] == ayse["id"] and yeni["jeton"] != ayse["jeton"]
    for yol in ("", "/program.pdf"):
        eski = ac(istemci, ayse["jeton"], yol)
        assert eski.status_code == 404 and eski.json()["detail"] == "Paylaşım linki bulunamadı"
    assert ac(istemci, yeni["jeton"]).status_code == 200
    assert istemci.delete(f"{LINK}/{ayse['id']}", headers=okul["baslik"]).status_code == 204
    for yol in ("", "/program.pdf"):
        assert ac(istemci, yeni["jeton"], yol).status_code == 404
    assert ac(istemci, "uydurma-" + "x" * 40).status_code == 404


def test_baska_okulun_programina_link_uzerinden_erisilemez(istemci, okul, yayinda, okul_olustur):
    """B okulunun linki yalnızca B'nin yayınını görür; B, A'nın linklerini yönetemez, A'nın
    öğretmenine link açamaz."""
    b = {"baslik": okul_basligi(okul_olustur("Başka Lise"))}
    b_okul = link(istemci, b, "okul")
    icerik = ac(istemci, b_okul["jeton"]).json()
    assert icerik["yayinda"] is False and icerik["subeler"] == [] and icerik["ogretmenler"] == []
    assert ac(istemci, b_okul["jeton"], "/program.pdf").status_code == 404
    # A'nın öğretmeni ve şubesi B'de yok.
    assert istemci.post(LINK, json={"tur": "ogretmen", "ogretmen_id": okul["harita"]["o-ayse"]},
                        headers=b["baslik"]).status_code == 404
    assert istemci.post(LINK, json={"tur": "sube", "sinif_id": okul["harita"]["s-9a"]},
                        headers=b["baslik"]).status_code == 404
    a_link = link(istemci, okul, "okul")
    assert istemci.get(LINK, headers=b["baslik"]).json() == [b_okul]
    assert istemci.post(f"{LINK}/{a_link['id']}/yenile", headers=b["baslik"]).status_code == 404
    assert istemci.delete(f"{LINK}/{a_link['id']}", headers=b["baslik"]).status_code == 404
    assert ac(istemci, a_link["jeton"]).json()["okul"] == "Mini Lisesi"
    # Linkler varken uydurma ya da eksik jeton hiçbirini açmaz.
    for uydurma in ("uydurma-" + "x" * 40, a_link["jeton"][:-1], a_link["jeton"].upper(), "%25", "' OR '1'='1"):
        assert ac(istemci, uydurma).status_code == 404, uydurma


def test_yonetici_uclari_oturum_ister(istemci, okul):
    istemci.cookies.clear()
    assert istemci.get(LINK).status_code == 401
    assert istemci.post(LINK, json={"tur": "okul"}).status_code in (401, 403)


def test_kapsam_tekil_toplu_ve_silinen_ogretmenin_linki(istemci, okul, yayinda):
    ilk = link(istemci, okul, "okul")
    assert link(istemci, okul, "okul") == ilk  # kapsam başına tek link
    yanit = istemci.post(LINK, json={"tur": "ogretmen"}, headers=okul["baslik"])
    assert yanit.status_code == 422 and "için öğretmen" in yanit.json()["detail"]
    hepsi = istemci.post(f"{LINK}/toplu", json={"tur": "ogretmen"}, headers=okul["baslik"]).json()
    assert len(hepsi) == 5 and len({h["jeton"] for h in hepsi}) == 5
    assert istemci.post(f"{LINK}/toplu", json={"tur": "ogretmen"}, headers=okul["baslik"]).json() == hepsi
    subeler = istemci.post(f"{LINK}/toplu", json={"tur": "sube"}, headers=okul["baslik"]).json()
    assert sorted(s["hedef_adi"] for s in subeler) == ["10-A", "9-A", "9-B"]


def test_yeniden_yayinlaninca_link_ayni_kalir_yayin_kalkinca_bos(istemci, okul, yayinda, kuyruk, oturum_fabrikasi):
    okul_linki = link(istemci, okul, "okul")["jeton"]
    yeni = uret(istemci, okul, ad="Ekim Programı").json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, yeni)
    istemci.put(f"{DP}/yayin", json={"program_id": yeni}, headers=okul["baslik"])
    assert ac(istemci, okul_linki).json()["program"] == "Ekim Programı"
    istemci.delete(f"{DP}/yayin", headers=okul["baslik"])
    assert ac(istemci, okul_linki).json()["yayinda"] is False


def test_girissiz_okuma_okul_baglami_acmaz_fonksiyon_dar_yetkili(istemci, okul, yayinda, oturum_fabrikasi,
                                                                  sahip_motor):
    """Uygulama rolü okulsuz oturumda tablolardan hiçbir satır görmez; içerik yalnızca fonksiyondan.
    Fonksiyonun sahibi süper kullanıcı değildir, RLS'yi atlayamaz; arama yolu sabit; PUBLIC
    çalıştıramaz."""
    jeton = link(istemci, okul, "ogretmen", ogretmen_id=okul["harita"]["o-ayse"])["jeton"]
    with okulsuz_oturum(oturum_fabrikasi) as o:
        for tablo in ("paylasim_linki", "yayin", "ogretmen", "yerlesim"):
            assert o.scalar(text(f"SELECT count(*) FROM {tablo}")) == 0
        icerik = o.scalar(select(func.paylasim_icerigi(jeton)))
        assert [c["ad"] for c in icerik["icerik"]["ogretmenler"]] == ["Ayşe Yılmaz"]
        assert o.scalar(select(func.paylasim_icerigi("yok"))) is None
    with sahip_motor.connect() as b:
        sahip, ayar, super_mi, atlar = b.execute(text(
            "SELECT r.rolname, p.proconfig, r.rolsuper, r.rolbypassrls FROM pg_proc p "
            "JOIN pg_roles r ON r.oid = p.proowner WHERE p.proname = 'paylasim_icerigi'")).one()
        assert sahip == "okul_paylasim" and not super_mi and not atlar
        assert ayar == ["search_path=pg_catalog, public"]
        assert b.scalar(text("SELECT rolcanlogin FROM pg_roles WHERE rolname = 'okul_paylasim'")) is False
        assert b.scalar(text(
            "SELECT bool_or(acl::text LIKE '=X/%') FROM pg_proc p, unnest(coalesce(p.proacl, '{}')) acl "
            "WHERE p.proname = 'paylasim_icerigi'")) in (False, None)
        # Rolün okuma yetkisi yalnızca iki tablodadır.
        tablolar = set(b.scalars(text(
            "SELECT DISTINCT table_name FROM information_schema.column_privileges WHERE grantee = 'okul_paylasim'")))
        assert tablolar == {"paylasim_linki", "yayin"}
