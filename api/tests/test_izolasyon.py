"""Yapım sırası 2'nin kabul testi: iki okul, biri diğerinin verisine erişemez (docs/adr/0009).

Bu dosyadaki veri gerçekten commit edilir (dış işlem düzeneği kullanılmaz). Çünkü bağlantı havuzu
testi farklı bağlantıları ve gerçek işlem sınırlarını görmelidir. Veri, modül sonunda tablo
sahibi bağlantısıyla silinir.

Okula ait tablolar `Base.metadata`'dan otomatik bulunur. Yeni bir modül tablo eklediğinde
`test_her_okula_ait_tablo_kapsamda` kırılır ve test verisine o tablonun da eklenmesini ister: yeni
tablo kabul testinin dışında kalamaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError

from conftest import TEST_UYGULAMA_URL, okul_basligi, oturum_kaydet
from okulapi.cekirdek.kimlik.servis import jeton_ozeti, jeton_uret
from okulapi.cekirdek.kiraci import okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.modeller import Ders, Kullanici, Ogretmen, Oturum, Sinif
from okulapi.cekirdek.servisler import OkulServisi
from okulapi.cekirdek.veritabani import Base, motor_olustur, oturum_fabrikasi as fabrika_olustur
from okulapi.main import uygulama_olustur
from okulapi.moduller.ders_programi.modeller import (
    DersAtama, Kisit, Musaitlik, Program, SeviyeSablonu, Yerlesim,
)

RLS_IHLALI = "42501"  # insufficient_privilege: "new row violates row-level security policy"


def okula_ait_tablolar() -> list[str]:
    import okulapi.moduller.ders_programi  # noqa: F401  (modül tabloları metadata'ya kaydolur)

    return sorted(t.name for t in Base.metadata.sorted_tables if "okul_id" in t.c)


def _okul_verisi(fabrika, ad: str) -> tuple[uuid.UUID, dict[str, set[uuid.UUID]]]:
    """Bir okul ve okula ait **her tabloda** en az bir satır. Tablo -> satır kimlikleri döner."""
    with okulsuz_oturum(fabrika) as oturum:
        okul_id = OkulServisi(oturum).olustur({"ad": ad}).id
    with okul_oturumu(fabrika, okul_id) as o:
        ogretmen, ogretmen2 = Ogretmen(ad=f"{ad} Öğretmen 1"), Ogretmen(ad=f"{ad} Öğretmen 2")
        sinif, ders = Sinif(ad="9-A", seviye=9), Ders(ad="Matematik", kisa_ad="MAT")
        mudur = Kullanici(email=f"mudur@{uuid.uuid4().hex}.test", sifre_hash="x", ad="Müdür", rol="mudur")
        o.add_all([ogretmen, ogretmen2, sinif, ders, mudur])
        o.flush()
        jeton = jeton_uret()  # API testleri bu okul adına bu oturumla istek atar (okul_basligi)
        oturum_kaydet(okul_id, jeton)
        o.add(Oturum(kullanici_id=mudur.id, jeton_ozeti=jeton_ozeti(jeton),
                     hareketsizlik_siniri=timedelta(hours=12), bitis_mutlak=datetime.now(timezone.utc) + timedelta(days=7)))
        atama = DersAtama(sinif_id=sinif.id, ders_id=ders.id, ogretmen_id=ogretmen.id, haftalik_saat=6)
        program = Program(ad="Eylül")
        o.add_all([atama, program, SeviyeSablonu(seviye=9, ders_id=ders.id, haftalik_saat=6),
                   Musaitlik(ogretmen_id=ogretmen.id, gun=0, saat=0, durum="gelemez"),
                   Kisit(tur="gunluk_ders_siniri", parametreler={"n": 2}, zorunlu=True)])
        o.flush()
        o.add(Yerlesim(program_id=program.id, ders_atama_id=atama.id, gun=1, saat=0, kilitli=True))
        o.commit()
        satirlar = {t: set(o.scalars(text(f"SELECT id FROM {t}"))) for t in okula_ait_tablolar()}
    return okul_id, satirlar


@pytest.fixture(scope="module")
def iki_okul(motor, sahip_motor):
    fabrika = fabrika_olustur(motor)
    a, a_satir = _okul_verisi(fabrika, "A Lisesi")
    b, b_satir = _okul_verisi(fabrika, "B Lisesi")
    yield {"a": a, "b": b, "a_satir": a_satir, "b_satir": b_satir}
    # Temizlik (tablo sahibi, RLS'yi atlar): yabancı anahtar sırasının tersiyle.
    with sahip_motor.begin() as baglanti:
        for tablo in reversed(Base.metadata.sorted_tables):
            if "okul_id" not in tablo.c and tablo.name != "okul":
                continue  # okula ait olmayan tablolar (ör. giris_denemesi)
            sutun = tablo.c.okul_id if "okul_id" in tablo.c else tablo.c.id
            baglanti.execute(delete(tablo).where(sutun.in_([a, b])))


# --- veritabanı düzeyi -------------------------------------------------------------------


def test_her_okula_ait_tablo_kapsamda(iki_okul):
    tablolar = okula_ait_tablolar()
    assert {"ogretmen", "ders_atama", "yerlesim"} <= set(tablolar)  # makul bir alt sınır
    for okul in ("a_satir", "b_satir"):
        bos = [t for t in tablolar if not iki_okul[okul][t]]
        assert bos == [], f"Test verisi şu tabloları doldurmuyor (_okul_verisi'ne ekleyin): {bos}"


@pytest.mark.parametrize("tablo", okula_ait_tablolar())
def test_rls_tablo_basina(motor, sahip_motor, iki_okul, tablo):
    fabrika = fabrika_olustur(motor)
    a, b = iki_okul["a"], iki_okul["b"]
    a_satir, b_satir = iki_okul["a_satir"][tablo], iki_okul["b_satir"][tablo]
    model = next(m.class_ for m in Base.registry.mappers if m.local_table.name == tablo)

    with okul_oturumu(fabrika, a) as o:
        # Okuma: ORM ve ham SQL yalnızca A'nın satırlarını görür.
        assert set(o.scalars(select(model.id))) == a_satir
        assert set(o.scalars(text(f"SELECT id FROM {tablo}"))) == a_satir
        assert o.scalar(text(f"SELECT count(*) FROM {tablo} WHERE okul_id = :b"), {"b": b}) == 0
        # B'nin satırlarını güncelleme ve silme denemesi: etkilenen satır yok.
        assert o.execute(text(f"UPDATE {tablo} SET guncelleme = now() WHERE okul_id = :b"), {"b": b}).rowcount == 0
        assert o.execute(text(f"DELETE FROM {tablo} WHERE okul_id = :b"), {"b": b}).rowcount == 0
        o.rollback()
        # Kendi satırını B'ye taşıma denemesi: WITH CHECK reddeder.
        with pytest.raises(DBAPIError) as hata:
            o.execute(text(f"UPDATE {tablo} SET okul_id = :b WHERE id = :id"), {"b": b, "id": next(iter(a_satir))})
        assert hata.value.orig.sqlstate == RLS_IHLALI
        o.rollback()

    with okulsuz_oturum(fabrika) as o:
        assert o.scalar(text(f"SELECT count(*) FROM {tablo}")) == 0

    # Tablo sahibi (süper kullanıcı) RLS'yi atlar ve ikisini de görür: filtreyi RLS yapıyor.
    with sahip_motor.connect() as baglanti:
        hepsi = set(baglanti.scalars(text(f"SELECT id FROM {tablo} WHERE okul_id IN (:a, :b)"), {"a": a, "b": b}))
    assert hepsi == a_satir | b_satir


def test_rls_okul_tablosu(motor, iki_okul):
    fabrika = fabrika_olustur(motor)
    a, b = iki_okul["a"], iki_okul["b"]
    with okul_oturumu(fabrika, a) as o:
        assert set(o.scalars(text("SELECT id FROM okul"))) == {a}
        assert o.execute(text("UPDATE okul SET ad = 'Ele geçirildi' WHERE id = :b"), {"b": b}).rowcount == 0
    with okulsuz_oturum(fabrika) as o:
        assert o.scalar(text("SELECT count(*) FROM okul")) == 0


# --- API düzeyi ------------------------------------------------------------------------------

LISTE_YOLLARI = {
    "ogretmen": "/api/ogretmenler",
    "sinif": "/api/siniflar",
    "ders": "/api/dersler",
    "seviye_sablonu": "/api/ders-programi/seviye-sablonlari",
    "ders_atama": "/api/ders-programi/atamalar",
    "musaitlik": "/api/ders-programi/musaitlikler",
    "kisit": "/api/ders-programi/kisitlar",
    "program": "/api/ders-programi/programlar",
}


@pytest.fixture(scope="module")
def api(ayarlar, iki_okul):
    from fastapi.testclient import TestClient

    uygulama = uygulama_olustur(ayarlar)
    with TestClient(uygulama) as istemci:
        yield istemci
    uygulama.state.motor.dispose()


@pytest.mark.parametrize("tablo", LISTE_YOLLARI)
def test_api_listeleme_ve_tek_kayit(api, iki_okul, tablo):
    yol, a, b = LISTE_YOLLARI[tablo], iki_okul["a"], iki_okul["b"]
    yanit = api.get(yol, headers=okul_basligi(a))
    assert yanit.status_code == 200
    assert {uuid.UUID(k["id"]) for k in yanit.json()} == iki_okul["a_satir"][tablo]
    for b_kayit in iki_okul["b_satir"][tablo]:
        assert api.get(f"{yol}/{b_kayit}", headers=okul_basligi(a)).status_code == 404
    if tablo != "program":  # program yalnızca okunur (üretimi yapım sırası 3'te)
        for b_kayit in iki_okul["b_satir"][tablo]:
            assert api.delete(f"{yol}/{b_kayit}", headers=okul_basligi(a)).status_code == 404
        # B'nin kayıtları yerinde.
        assert {uuid.UUID(k["id"]) for k in api.get(yol, headers=okul_basligi(b)).json()} == iki_okul["b_satir"][tablo]


def test_api_yerlesimler_ve_okul(api, iki_okul):
    a, b = iki_okul["a"], iki_okul["b"]
    b_program = next(iter(iki_okul["b_satir"]["program"]))
    assert api.get(f"/api/ders-programi/programlar/{b_program}/yerlesimler", headers=okul_basligi(a)).status_code == 404
    assert api.get("/api/okul", headers=okul_basligi(a)).json()["id"] == str(a)


def test_okullar_arasi_iliski_kurulamaz(api, iki_okul):
    """A'nın atamasına B'nin öğretmeni: API 422, veritabanı (bileşik FK + RLS) da reddeder."""
    a, b = iki_okul["a"], iki_okul["b"]
    a_atama = next(iter(iki_okul["a_satir"]["ders_atama"]))
    b_ogretmen = next(iter(iki_okul["b_satir"]["ogretmen"]))
    yanit = api.patch(f"/api/ders-programi/atamalar/{a_atama}", json={"ogretmen_id": str(b_ogretmen)},
                      headers=okul_basligi(a))
    assert yanit.status_code == 422 and yanit.json()["detail"] == "Öğretmen bu okulda bulunamadı"


# --- bağlantı havuzu: okul bilgisi bir istekten diğerine taşmaz -------------------------------


@pytest.fixture
def tek_baglantili_fabrika(veritabani):
    """Havuzda tek bir bağlantı: her "istek" aynı fiziksel bağlantıyı kullanmak zorunda."""
    m = motor_olustur(TEST_UYGULAMA_URL, pool_size=1, max_overflow=0)
    yield m, fabrika_olustur(m)
    m.dispose()


def _istek(fabrika, okul_id):
    """Bir HTTP isteğinin veritabanı tarafı: bir oturum, bir işlem; ne gördüğünü raporlar.

    İstek **commit ederek** biter, servislerin yaptığı gibi. Bu önemli: geri alınan (rollback) bir
    işlemde bağlantı düzeyindeki SET de geri alınır ve taşma görünmez; taşma commit edilen
    isteklerde olur. (Testin ilk sürümü yalnızca geri alınan istekler kullanıyordu ve SET LOCAL
    yerine SET kullanılmasını yakalayamıyordu; mutasyon denemesiyle bulundu.)
    """
    oturum = okul_oturumu(fabrika, okul_id) if okul_id else okulsuz_oturum(fabrika)
    with oturum:
        sonuc = {
            "pid": oturum.scalar(text("SELECT pg_backend_pid()")),  # PostgreSQL sunucu sürecinin kimliği
            "ayar": oturum.scalar(text("SELECT current_setting('app.okul_id', true)")),
            "okullar": set(oturum.scalars(text("SELECT DISTINCT okul_id FROM ogretmen"))),
        }
        oturum.commit()
        return sonuc


def test_havuzdaki_ayni_baglanti_okul_bilgisini_tasimaz(iki_okul, tek_baglantili_fabrika):
    motor, fabrika = tek_baglantili_fabrika
    a, b = iki_okul["a"], iki_okul["b"]
    sonuclar = [_istek(fabrika, okul) for okul in (a, b, None, a, None, b)]

    assert len({s["pid"] for s in sonuclar}) == 1, "her istek aynı fiziksel bağlantıyı kullanmalı"
    assert [s["okullar"] for s in sonuclar] == [{a}, {b}, set(), {a}, set(), {b}]
    assert [s["ayar"] for s in sonuclar] == [str(a), str(b), "", str(a), "", str(b)]

    # İstekler bittikten sonra aynı bağlantıda, işlem dışında: ayar kalmamış (SET LOCAL'ın süresi
    # işlemle bitti). Bu bağlantı oturum olaylarından geçmez; yalnızca PostgreSQL'in durumuna bakar.
    with motor.connect() as baglanti:
        assert baglanti.scalar(text("SELECT pg_backend_pid()")) == sonuclar[0]["pid"]
        assert baglanti.scalar(text("SELECT current_setting('app.okul_id', true)")) in ("", None)
        assert baglanti.scalar(text("SELECT count(*) FROM ogretmen")) == 0


def test_hatayla_biten_istekten_sonra_da_tasmaz(iki_okul, tek_baglantili_fabrika):
    _motor, fabrika = tek_baglantili_fabrika
    a = iki_okul["a"]
    with okul_oturumu(fabrika, a) as oturum:
        with pytest.raises(DBAPIError):
            oturum.execute(text("SELECT 1/0"))  # istek ortasında hata; oturum geri alınır
        oturum.rollback()
    assert _istek(fabrika, None)["okullar"] == set()


def test_karsi_ornek_oturum_duzeyi_ayar_tasardi(iki_okul, tek_baglantili_fabrika):
    """Neden SET LOCAL: işlem değil **bağlantı** düzeyinde ayar (`set_config(..., false)` = `SET`)
    bağlantı havuza döndüğünde de kalır ve bir sonraki kullanıcıya A'nın verisini gösterirdi.
    Uygulama bunu hiç yapmaz; bu test yalnızca tehlikeyi ve korumanın ikinci katmanını gösterir."""
    motor, fabrika = tek_baglantili_fabrika
    a = iki_okul["a"]
    with motor.connect() as baglanti:
        baglanti.execute(text("SELECT set_config('app.okul_id', :a, false)"), {"a": str(a)})
        baglanti.commit()
    try:
        with motor.connect() as baglanti:  # aynı fiziksel bağlantı, oturum olayları yok
            assert baglanti.scalar(text("SELECT count(*) FROM ogretmen")) == 2, "bağlantı düzeyi ayar taştı"
        # Uygulamanın okulsuz oturumu yine hiçbir şey görmez: her işlemin başında ayar açıkça
        # boşaltılır (kiraci._veritabanina_okulu_bildir), önceki değere güvenilmez.
        assert _istek(fabrika, None)["okullar"] == set()
    finally:
        with motor.connect() as baglanti:
            baglanti.execute(text("RESET app.okul_id"))
            baglanti.commit()


def test_api_tek_baglantili_havuzla_sirali_istekler(ayarlar, iki_okul, tek_baglantili_fabrika):
    from fastapi.testclient import TestClient

    motor, fabrika = tek_baglantili_fabrika
    uygulama = uygulama_olustur(ayarlar)
    uygulama.state.motor, uygulama.state.oturum_fabrikasi = motor, fabrika
    a, b = iki_okul["a"], iki_okul["b"]
    with TestClient(uygulama) as istemci:
        for okul in (a, b, a, b, a):
            ids = {uuid.UUID(k["id"]) for k in istemci.get("/api/ogretmenler", headers=okul_basligi(okul)).json()}
            satirlar = iki_okul["a_satir" if okul == a else "b_satir"]["ogretmen"]
            assert ids == satirlar
