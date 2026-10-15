"""Kimlik doğrulamanın veritabanı tarafı (migration cekirdek_0004, ADR 0012, ADR 0009).

- RLS altında e-postayla arama: uygulama rolü okul bağlamı olmadan `kullanici` ve `oturum`
  tablolarını göremez, ama `giris_bilgisi` / `oturum_coz` fonksiyonlarıyla tam olarak bir
  kullanıcıyı / oturumu bulabilir.
- Fonksiyonların güvenli tanımı: SECURITY DEFINER, sahibi `okul_giris`, arama yolu sabit,
  `PUBLIC` çağıramaz.
- `okul_giris` rolü: bağlanılamaz, süper kullanıcı değil, yalnızca gereken sütunlarda yetkili.
- Kaba kuvvet sayacı: eşik, pencere, kilit süresi, eski kayıtların silinmesi.
- E-posta: bütün sistemde, büyük/küçük harf ayrımsız tek.

Testler doğrudan SQL kullanır: veritabanının kendi başına ne garanti ettiği sınanıyor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from okulapi.cekirdek.kiraci import okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.modeller import Kullanici, Oturum
from okulapi.cekirdek.servisler import OkulServisi

FONKSIYONLAR = ["giris_bilgisi", "oturum_coz", "giris_kilitli_mi", "giris_hatasi_kaydet", "giris_denemelerini_sil"]


def okul_ve_kullanici(fabrika, okul_adi: str, email: str, sifre_hash: str = "ozet") -> tuple[uuid.UUID, uuid.UUID]:
    with okulsuz_oturum(fabrika) as o:
        okul_id = OkulServisi(o).olustur({"ad": okul_adi}).id
    with okul_oturumu(fabrika, okul_id) as o:
        k = Kullanici(email=email, sifre_hash=sifre_hash, ad="Müdür", rol="mudur")
        o.add(k)
        o.commit()
        return okul_id, k.id


def okulsuz_sorgu(fabrika, sql: str, **parametreler) -> list[tuple]:
    """Okul bağlamı olmayan (girişteki gibi) uygulama rolü oturumuyla sorgu."""
    with okulsuz_oturum(fabrika) as o:
        sonuc = [tuple(r) for r in o.execute(text(sql), parametreler)]
        o.commit()
        return sonuc


# --- RLS altında arama ------------------------------------------------------------------------

def test_okul_baglami_olmadan_kullanici_ve_oturum_gorunmez(oturum_fabrikasi):
    okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "mudur@a.test")
    assert okulsuz_sorgu(oturum_fabrikasi, "SELECT count(*) FROM kullanici") == [(0,)]
    assert okulsuz_sorgu(oturum_fabrikasi, "SELECT count(*) FROM oturum") == [(0,)]


def test_giris_bilgisi_okulu_bilmeden_dogru_kullaniciyi_bulur(oturum_fabrikasi):
    a_okul, a_kullanici = okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "ayse@a.test", "ozet-a")
    b_okul, b_kullanici = okul_ve_kullanici(oturum_fabrikasi, "B Lisesi", "mehmet@b.test", "ozet-b")
    sorgu = "SELECT kullanici_id, okul_id, sifre_hash FROM giris_bilgisi(:e)"
    assert okulsuz_sorgu(oturum_fabrikasi, sorgu, e="ayse@a.test") == [(a_kullanici, a_okul, "ozet-a")]
    assert okulsuz_sorgu(oturum_fabrikasi, sorgu, e="mehmet@b.test") == [(b_kullanici, b_okul, "ozet-b")]


@pytest.mark.parametrize(
    ("girdi", "bulunur"),
    [
        ("ayse@a.test", True),
        ("AYSE@A.Test", True),     # büyük/küçük harf ayrımı yok
        ("%", False),              # joker değil, düz metin
        ("%@a.test", False),
        ("_yse@a.test", False),
        ("ayse@a.tes", False),     # önek eşleşmez
        ("", False),
        ("yok@a.test", False),
    ],
)
def test_giris_bilgisi_yalnizca_tam_eslesen_epostayi_doner(oturum_fabrikasi, girdi, bulunur):
    okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "ayse@a.test")
    okul_ve_kullanici(oturum_fabrikasi, "B Lisesi", "bora@a.test")
    satirlar = okulsuz_sorgu(oturum_fabrikasi, "SELECT kullanici_id FROM giris_bilgisi(:e)", e=girdi)
    assert len(satirlar) == (1 if bulunur else 0)


def test_giris_bilgisi_parola_ozeti_disinda_kisisel_bilgi_donmez(oturum_fabrikasi):
    okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "ayse@a.test")
    with okulsuz_oturum(oturum_fabrikasi) as o:
        sutunlar = list(o.execute(text("SELECT * FROM giris_bilgisi('ayse@a.test')")).keys())
    assert sutunlar == ["kullanici_id", "okul_id", "sifre_hash"]


# --- fonksiyonların ve rolün güvenli tanımı ---------------------------------------------------

@pytest.mark.parametrize("ad", FONKSIYONLAR)
def test_fonksiyon_guvenli_tanimli(sahip_motor, ad):
    with sahip_motor.connect() as b:
        sahip, guvenli, ayarlar, yetkiler = b.execute(text("""
            SELECT pg_get_userbyid(p.proowner), p.prosecdef, p.proconfig, p.proacl::text[]
            FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.proname = :ad"""), {"ad": ad}).one()
        uygulama = b.execute(text("SELECT has_function_privilege('okul_uygulama', p.oid, 'EXECUTE') "
                                  "FROM pg_proc p WHERE p.proname = :ad"), {"ad": ad}).scalar()
    assert sahip == "okul_giris"
    assert guvenli is True  # SECURITY DEFINER
    assert ayarlar == ["search_path=pg_catalog, public"]
    # ACL'de "=X/..." PUBLIC'in çalıştırma yetkisi demektir; olmamalı.
    assert not any(y.startswith("=") for y in yetkiler), yetkiler
    assert uygulama is True


def test_okul_giris_rolu_baglanamaz_ve_dar_yetkili(sahip_motor):
    with sahip_motor.connect() as b:
        giris, super_, rls_atlar = b.execute(text(
            "SELECT rolcanlogin, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'okul_giris'")).one()
        yetki = lambda sql: b.execute(text(sql)).scalar()  # noqa: E731
        assert (giris, super_, rls_atlar) == (False, False, False)
        for tablo in ("okul", "ogretmen", "sinif", "ders", "ders_atama", "program", "yerlesim"):
            assert not yetki(f"SELECT has_table_privilege('okul_giris', '{tablo}', 'SELECT')"), tablo
        # kullanici: yalnızca girişte gereken dört sütun, yalnızca okuma
        assert yetki("SELECT has_column_privilege('okul_giris', 'kullanici', 'sifre_hash', 'SELECT')")
        for sutun in ("ad", "rol"):
            assert not yetki(f"SELECT has_column_privilege('okul_giris', 'kullanici', '{sutun}', 'SELECT')"), sutun
        for islem in ("INSERT", "UPDATE", "DELETE"):
            assert not yetki(f"SELECT has_table_privilege('okul_giris', 'kullanici', '{islem}')"), islem
        # oturum: yalnızca son kullanım zamanı güncellenebilir
        assert yetki("SELECT has_column_privilege('okul_giris', 'oturum', 'son_kullanim', 'UPDATE')")
        assert not yetki("SELECT has_column_privilege('okul_giris', 'oturum', 'okul_id', 'UPDATE')")


def test_uygulama_rolu_giris_denemesi_tablosuna_dogrudan_erisemez(motor):
    for sql in ("SELECT * FROM giris_denemesi",
                "INSERT INTO giris_denemesi (email, hata_sayisi, pencere_basi) VALUES ('x', 0, now())",
                "DELETE FROM giris_denemesi"):
        with motor.connect() as b, pytest.raises(ProgrammingError, match="permission denied"):
            b.execute(text(sql))


# --- oturum çözme -----------------------------------------------------------------------------

def oturum_ekle(fabrika, okul_id, kullanici_id, jeton_ozeti, son_kullanim=None, bitis_mutlak=None,
                hareketsizlik=timedelta(hours=12)) -> uuid.UUID:
    simdi = datetime.now(timezone.utc)
    with okul_oturumu(fabrika, okul_id) as o:
        oturum = Oturum(kullanici_id=kullanici_id, jeton_ozeti=jeton_ozeti, hareketsizlik_siniri=hareketsizlik,
                        bitis_mutlak=bitis_mutlak or simdi + timedelta(days=7))
        if son_kullanim is not None:
            oturum.son_kullanim = son_kullanim
        o.add(oturum)
        o.commit()
        return oturum.id


@pytest.mark.parametrize(
    ("durum", "cozulur"),
    [
        ("gecerli", True),
        ("hareketsizlik_doldu", False),
        ("mutlak_sure_doldu", False),
        ("yanlis_jeton", False),
    ],
)
def test_oturum_coz_yalnizca_gecerli_oturumu_doner(oturum_fabrikasi, durum, cozulur):
    okul_id, kullanici_id = okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "ayse@a.test")
    simdi = datetime.now(timezone.utc)
    oturum_id = oturum_ekle(
        oturum_fabrikasi, okul_id, kullanici_id, "a" * 64,
        son_kullanim=simdi - timedelta(hours=13) if durum == "hareketsizlik_doldu" else None,
        bitis_mutlak=simdi - timedelta(seconds=1) if durum == "mutlak_sure_doldu" else None,
    )
    jeton = "b" * 64 if durum == "yanlis_jeton" else "a" * 64
    satirlar = okulsuz_sorgu(oturum_fabrikasi, "SELECT oturum_id, kullanici_id, okul_id FROM oturum_coz(:j)", j=jeton)
    assert satirlar == ([(oturum_id, kullanici_id, okul_id)] if cozulur else [])


def test_oturum_coz_son_kullanimi_en_cok_dakikada_bir_gunceller(motor, oturum_fabrikasi):
    okul_id, kullanici_id = okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "ayse@a.test")
    simdi = datetime.now(timezone.utc)
    eski_id = oturum_ekle(oturum_fabrikasi, okul_id, kullanici_id, "e" * 64, son_kullanim=simdi - timedelta(minutes=5))
    yeni_id = oturum_ekle(oturum_fabrikasi, okul_id, kullanici_id, "f" * 64, son_kullanim=simdi - timedelta(seconds=10))
    okulsuz_sorgu(oturum_fabrikasi, "SELECT * FROM oturum_coz(:j)", j="e" * 64)
    okulsuz_sorgu(oturum_fabrikasi, "SELECT * FROM oturum_coz(:j)", j="f" * 64)
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        eski, yeni = o.get(Oturum, eski_id), o.get(Oturum, yeni_id)
        o.refresh(eski)
        o.refresh(yeni)
    assert eski.son_kullanim > simdi - timedelta(minutes=1)  # ilerledi
    assert yeni.son_kullanim < simdi - timedelta(seconds=5)  # yazma yapılmadı


# --- kaba kuvvet sayacı (gerçek commit'li, ayrı bağlantılar: zaman ilerlesin) -----------------

@pytest.fixture
def sayac(motor, sahip_motor):
    """Fonksiyonları uygulama rolüyle (okul bağlamı yok) çağırır; zamanı sahip rolüyle oynatır."""
    kullanilanlar: list[str] = []

    class Sayac:
        def eposta(self) -> str:
            e = f"deneme-{uuid.uuid4().hex[:8]}@kaba.test"
            kullanilanlar.append(e)
            return e

        def hata(self, email, esik=5, pencere="15 minutes", kilit="15 minutes") -> bool:
            with motor.begin() as b:
                return b.execute(text("SELECT giris_hatasi_kaydet(:e, :n, CAST(:p AS interval), CAST(:k AS interval))"),
                                 {"e": email, "n": esik, "p": pencere, "k": kilit}).scalar()

        def kilitli(self, email) -> bool:
            with motor.begin() as b:
                return b.execute(text("SELECT giris_kilitli_mi(:e)"), {"e": email}).scalar()

        def sil(self, email) -> None:
            with motor.begin() as b:
                b.execute(text("SELECT giris_denemelerini_sil(:e)"), {"e": email})

        def sahip(self, sql, **p):
            with sahip_motor.begin() as b:
                return b.execute(text(sql), p).all() if sql.lstrip().upper().startswith("SELECT") else b.execute(text(sql), p)

    yield Sayac()
    with sahip_motor.begin() as b:
        b.execute(text("DELETE FROM giris_denemesi WHERE email = ANY(:e) OR email LIKE '%@eski.test'"),
                  {"e": kullanilanlar})


def test_besinci_hatada_kilitlenir_ve_kilit_suresi_dolunca_acilir(sayac):
    email = sayac.eposta()
    assert [sayac.hata(email) for _ in range(4)] == [False] * 4
    assert sayac.kilitli(email) is False
    assert sayac.hata(email) is True  # beşinci hata kilitler
    assert sayac.kilitli(email) is True
    assert sayac.kilitli(email.upper()) is True  # büyük/küçük harf ayrımı yok

    sayac.sahip("UPDATE giris_denemesi SET kilit_bitis = now() - interval '1 second' WHERE email = :e", e=email)
    assert sayac.kilitli(email) is False
    # Kilitlenince sayaç sıfırlandı: açıldıktan sonraki ilk hata yeniden kilitlemez.
    assert sayac.hata(email) is False


def test_pencere_dolunca_sayac_sifirdan_baslar(sayac):
    email = sayac.eposta()
    for _ in range(4):
        sayac.hata(email)
    sayac.sahip("UPDATE giris_denemesi SET pencere_basi = now() - interval '16 minutes' WHERE email = :e", e=email)
    assert sayac.hata(email) is False  # 5. hata ama pencere dolmuştu: sayaç 1
    assert sayac.sahip("SELECT hata_sayisi FROM giris_denemesi WHERE email = :e", e=email) == [(1,)]


def test_basarili_giris_ve_sifirlama_sayaci_siler(sayac):
    email = sayac.eposta()
    for _ in range(5):
        sayac.hata(email)
    assert sayac.kilitli(email)
    sayac.sil(email)
    assert sayac.kilitli(email) is False
    assert sayac.sahip("SELECT count(*) FROM giris_denemesi WHERE email = :e", e=email) == [(0,)]


def test_eski_kayitlar_temizlenir(sayac):
    eski = f"eski-{uuid.uuid4().hex[:8]}@eski.test"
    sayac.sahip("INSERT INTO giris_denemesi VALUES (:e, 2, now() - interval '2 days', NULL)", e=eski)
    sayac.hata(sayac.eposta())  # herhangi bir hata kaydı eski kayıtları temizler
    assert sayac.sahip("SELECT count(*) FROM giris_denemesi WHERE email = :e", e=eski) == [(0,)]


# --- e-posta benzersizliği --------------------------------------------------------------------

def test_eposta_buyuk_kucuk_harf_farkiyla_bile_iki_okulda_kullanilamaz(oturum_fabrikasi):
    okul_ve_kullanici(oturum_fabrikasi, "A Lisesi", "ayse@okul.test")
    with okulsuz_oturum(oturum_fabrikasi) as o:
        b_okul = OkulServisi(o).olustur({"ad": "B Lisesi"}).id
    with okul_oturumu(oturum_fabrikasi, b_okul) as o:
        # Uygulama küçük harfe çevirmeyi unutsa bile: CHECK büyük harfi, indeks tekrarı reddeder.
        o.add(Kullanici(email="Ayse@Okul.test", sifre_hash="x", ad="Ayşe", rol="mudur"))
        with pytest.raises(IntegrityError, match="ck_kullanici_email_kucuk_harf"):
            o.flush()
        o.rollback()
        o.add(Kullanici(email="ayse@okul.test", sifre_hash="x", ad="Ayşe", rol="mudur"))
        with pytest.raises(IntegrityError, match="uq_kullanici_email_kucuk"):
            o.flush()


def test_check_kaldirilsa_bile_benzersizlik_buyuk_kucuk_harf_ayrimsiz(sahip_motor):
    """İkinci savunma hattı: benzersizlik `lower(email)` üzerindedir. CHECK bir gün kaldırılsa ya
    da devre dışı kalsa bile "Ayse@" ile "ayse@" iki hesap olamaz. PostgreSQL'de DDL de işleme
    dahildir: CHECK yalnızca bu işlem içinde kaldırılır, sonunda geri alınır."""
    with sahip_motor.connect() as b:
        islem = b.begin()
        try:
            b.execute(text("ALTER TABLE kullanici DROP CONSTRAINT ck_kullanici_email_kucuk_harf"))
            a, c = uuid.uuid4(), uuid.uuid4()
            b.execute(text("INSERT INTO okul (id, ad) VALUES (:a, 'A'), (:c, 'C')"), {"a": a, "c": c})
            b.execute(text("INSERT INTO kullanici (id, okul_id, email, sifre_hash, ad, rol) "
                           "VALUES (:i, :o, 'Ayse@Okul.test', 'x', 'Ayşe', 'mudur')"), {"i": uuid.uuid4(), "o": a})
            with pytest.raises(IntegrityError, match="uq_kullanici_email_kucuk"):
                b.execute(text("INSERT INTO kullanici (id, okul_id, email, sifre_hash, ad, rol) "
                               "VALUES (:i, :o, 'ayse@okul.test', 'x', 'Ayşe', 'mudur')"), {"i": uuid.uuid4(), "o": c})
        finally:
            islem.rollback()
