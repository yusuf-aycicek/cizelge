"""Kimlik servisleri (okulapi.cekirdek.kimlik): parola, kayıt, giriş, oturum, kaba kuvvet,
kullanıcı yönetimi, oturumların geçersiz kılınması, son müdür kuralı, `parola-sifirla` komutu.

API uçları 3. alt adımda; burada servisler doğrudan çağrılır.
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from conftest import HIZLI_OZETLEYICI
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.cekirdek.kimlik import parola
from okulapi.cekirdek.kimlik.servis import (
    CokFazlaDeneme,
    EpostaKullaniliyor,
    GirisHatasi,
    KimlikServisi,
    KullaniciServisi,
    OturumBilgisi,
    SonMudur,
    YetkiYok,
    jeton_ozeti,
)
from okulapi.cekirdek.modeller import Base, Kullanici, Okul, Oturum
from okulapi.cekirdek.servisler import GecersizVeri, KayitBulunamadi
from okulapi.cekirdek.veritabani import oturum_fabrikasi as fabrika_olustur

PAROLA = "dogru-at-pil-zimba"  # 18 karakter
YENI = "yepyeni-parola-2026"


@pytest.fixture
def kimlik(oturum_fabrikasi):
    return KimlikServisi(oturum_fabrikasi, Ayarlar())


def kayit(kimlik, okul="A Lisesi", email="ayse@a.test", ad="Ayşe Yılmaz"):
    """(okul_id, müdürün oturum bilgisi, jeton)"""
    okul_, mudur, jeton = kimlik.kayit({"ad": okul}, ad, email, PAROLA)
    return okul_.id, kimlik.oturum_coz(jeton), jeton


@contextmanager
def kullanicilar(kimlik, istek: OturumBilgisi):
    with okul_oturumu(kimlik.fabrika, istek.okul_id) as o:
        yield KullaniciServisi(o, istek)


def yardimci(kimlik, mudur: OturumBilgisi, email="mehmet@a.test", ad="Mehmet Kaya") -> uuid.UUID:
    with kullanicilar(kimlik, mudur) as k:
        return k.yardimci_ekle(ad, email, PAROLA).id


# --- parola -----------------------------------------------------------------------------------

def test_parola_ozeti_argon2id_ve_varsayilan_parametreler():
    from argon2 import PasswordHasher

    varsayilan = PasswordHasher()
    assert parola._OZETLEYICI is HIZLI_OZETLEYICI  # testlerde hızlı; üretimdeki değil:
    ozet = varsayilan.hash(PAROLA)
    assert ozet.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert varsayilan.verify(ozet, PAROLA)
    # Üretim modülü varsayılan nesneyle başlar (fikstür onu yalnızca test süresince değiştirir).
    import importlib

    kaynak = importlib.util.find_spec("okulapi.cekirdek.kimlik.parola").origin
    assert "_OZETLEYICI = PasswordHasher()" in open(kaynak, encoding="utf-8").read()


def test_parola_ozeti_tuzlu_ve_dogrulanir():
    a, b = parola.ozetle(PAROLA), parola.ozetle(PAROLA)
    assert a != b and a.startswith("$argon2id$")  # her özetin kendi tuzu var
    assert parola.dogrula(a, PAROLA) and not parola.dogrula(a, PAROLA + "x")
    assert not parola.dogrula("bozuk-ozet", PAROLA)


@pytest.mark.parametrize(("uzunluk", "gecerli"), [(11, False), (12, True), (256, True), (257, False)])
def test_parola_uzunluk_kurali(uzunluk, gecerli):
    if gecerli:
        parola.ozetle("a" * uzunluk)
    else:
        with pytest.raises(parola.ParolaGecersiz):
            parola.ozetle("a" * uzunluk)


# --- kayıt --------------------------------------------------------------------------------------

def test_kayit_okul_mudur_ve_oturum_olusturur(kimlik):
    okul_id, bilgi, jeton = kayit(kimlik, email="  Ayse@A.Test ")
    assert bilgi is not None and bilgi.okul_id == okul_id
    with okul_oturumu(kimlik.fabrika, okul_id) as o:
        mudur = o.get(Kullanici, bilgi.kullanici_id)
        assert (mudur.email, mudur.rol, mudur.ad) == ("ayse@a.test", "mudur", "Ayşe Yılmaz")
        assert mudur.sifre_hash.startswith("$argon2id$") and PAROLA not in mudur.sifre_hash
        oturum = o.get(Oturum, bilgi.oturum_id)
        assert oturum.jeton_ozeti == jeton_ozeti(jeton) and jeton not in oturum.jeton_ozeti  # jeton düz durmaz
        assert o.get(Okul, okul_id).ad == "A Lisesi"


@pytest.mark.parametrize("ikinci", ["ayse@a.test", "AYSE@a.test", " ayse@A.TEST"])
def test_kayitta_baska_okulda_kullanilan_eposta_anlasilir_hata(kimlik, ikinci):
    kayit(kimlik, "A Lisesi", "ayse@a.test")
    with pytest.raises(EpostaKullaniliyor, match="Bu e-posta adresi başka bir hesapta kullanılıyor"):
        kimlik.kayit({"ad": "B Lisesi"}, "Ayşe", ikinci, PAROLA)


def test_kayitta_kisa_parola_reddedilir_ve_hicbir_sey_olusmaz(kimlik):
    with pytest.raises(parola.ParolaGecersiz):
        kimlik.kayit({"ad": "A Lisesi"}, "Ayşe", "ayse@a.test", "kisa")
    assert not kimlik._eposta_kullaniliyor_mu("ayse@a.test")


@pytest.fixture
def kalici_kimlik(motor, sahip_motor):
    """Gerçekten commit eden fabrika (tek işlem testi için); oluşan okullar sonunda silinir."""
    servis = KimlikServisi(fabrika_olustur(motor), Ayarlar())
    yield servis
    with sahip_motor.begin() as b:
        okullar = [r[0] for r in b.execute(select(Okul.id).where(Okul.ad.like("Tek İşlem%")))]
        for tablo in reversed(Base.metadata.sorted_tables):
            if "okul_id" in tablo.c:
                b.execute(delete(tablo).where(tablo.c.okul_id.in_(okullar)))
        b.execute(delete(Okul.__table__).where(Okul.id.in_(okullar)))


def test_kayit_tek_islemdir(kalici_kimlik, sahip_motor, monkeypatch):
    """Oturum oluşturulurken hata olursa ne okul ne müdür kalır."""
    from okulapi.cekirdek.kimlik import servis

    def patla():
        raise RuntimeError("jeton üretilemedi")

    monkeypatch.setattr(servis, "jeton_uret", patla)
    with pytest.raises(RuntimeError):
        kalici_kimlik.kayit({"ad": "Tek İşlem Lisesi"}, "Ayşe", "tek-islem@a.test", PAROLA)
    with sahip_motor.connect() as b:  # tablo sahibi: RLS'ye takılmadan bakar
        assert b.execute(select(Okul.id).where(Okul.ad == "Tek İşlem Lisesi")).all() == []
        assert b.execute(select(Kullanici.id).where(Kullanici.email == "tek-islem@a.test")).all() == []


# --- giriş, oturum, çıkış ---------------------------------------------------------------------

def test_giris_buyuk_kucuk_harf_duyarsiz_ve_oturum_acar(kimlik):
    okul_id, mudur, _ = kayit(kimlik)
    bilgi, jeton = kimlik.giris("AYSE@a.test ", PAROLA)
    assert (bilgi.okul_id, bilgi.kullanici_id) == (okul_id, mudur.kullanici_id)
    assert kimlik.oturum_coz(jeton) == bilgi


def test_yanlis_parola_ve_bilinmeyen_eposta_ayni_hatayi_alir(kimlik, monkeypatch):
    kayit(kimlik)
    dogrulamalar = []
    gercek = parola.dogrula
    monkeypatch.setattr(parola, "dogrula", lambda o, p: dogrulamalar.append(o) or gercek(o, p))

    with pytest.raises(GirisHatasi) as yanlis:
        kimlik.giris("ayse@a.test", "yanlis-parola-12345")
    with pytest.raises(GirisHatasi) as bilinmeyen:
        kimlik.giris("kimse@a.test", "yanlis-parola-12345")
    assert str(yanlis.value) == str(bilinmeyen.value) == "E-posta ya da parola hatalı"
    # Bilinmeyen e-postada da bir argon2 doğrulaması yapıldı (süre e-postanın varlığını söylemez).
    assert len(dogrulamalar) == 2


def test_cikistan_sonra_jeton_gecersiz(kimlik):
    _, _, jeton = kayit(kimlik)
    assert kimlik.oturum_coz(jeton) is not None
    kimlik.cikis(jeton)
    assert kimlik.oturum_coz(jeton) is None
    kimlik.cikis(jeton)  # ikinci çıkış hata vermez


@pytest.mark.parametrize("jeton", [None, "", "uydurma-jeton", "x" * 1000])
def test_gecersiz_jeton_cozulmez(kimlik, jeton):
    kayit(kimlik)
    assert kimlik.oturum_coz(jeton) is None


def test_hareketsiz_kalan_oturum_gecersiz(kimlik):
    okul_id, bilgi, jeton = kayit(kimlik)
    with okul_oturumu(kimlik.fabrika, okul_id) as o:
        o.execute(update(Oturum).where(Oturum.id == bilgi.oturum_id)
                  .values(son_kullanim=Oturum.son_kullanim - Oturum.hareketsizlik_siniri))
        o.commit()
    assert kimlik.oturum_coz(jeton) is None


# --- kaba kuvvet ------------------------------------------------------------------------------

def test_bes_hatali_denemeden_sonra_dogru_parola_da_kilitli(kimlik):
    kayit(kimlik)
    for _ in range(5):
        with pytest.raises(GirisHatasi):
            kimlik.giris("ayse@a.test", "yanlis-parola-12345")
    with pytest.raises(CokFazlaDeneme, match="15 dakika sonra"):
        kimlik.giris("ayse@a.test", PAROLA)


def test_kayitli_olmayan_eposta_da_ayni_sekilde_kilitlenir(kimlik):
    for _ in range(5):
        with pytest.raises(GirisHatasi):
            kimlik.giris("kimse@a.test", "yanlis-parola-12345")
    with pytest.raises(CokFazlaDeneme):
        kimlik.giris("kimse@a.test", "yanlis-parola-12345")


def test_basarili_giris_sayaci_sifirlar(kimlik):
    kayit(kimlik)
    for _ in range(4):
        with pytest.raises(GirisHatasi):
            kimlik.giris("ayse@a.test", "yanlis-parola-12345")
    kimlik.giris("ayse@a.test", PAROLA)
    for _ in range(4):
        with pytest.raises(GirisHatasi):
            kimlik.giris("ayse@a.test", "yanlis-parola-12345")
    kimlik.giris("ayse@a.test", PAROLA)  # 8 hata ama hiçbir pencerede 5 değil


# --- kullanıcı yönetimi ve oturumların geçersiz kılınması -------------------------------------

def test_mudur_yardimci_ekler_ve_yardimci_giris_yapar(kimlik):
    _, mudur, _ = kayit(kimlik)
    yardimci(kimlik, mudur, email="Mehmet@A.test")
    bilgi, _ = kimlik.giris("mehmet@a.test", PAROLA)
    with kullanicilar(kimlik, bilgi) as k:
        assert [(x.ad, x.rol) for x in k.listele()] == [("Ayşe Yılmaz", "mudur"), ("Mehmet Kaya", "mudur_yardimcisi")]


def test_yardimci_eklerken_baska_okulda_kullanilan_eposta_anlasilir_hata(kimlik):
    _, mudur_a, _ = kayit(kimlik, "A Lisesi", "ayse@a.test")
    kayit(kimlik, "B Lisesi", "bora@b.test")
    with kullanicilar(kimlik, mudur_a) as k, pytest.raises(EpostaKullaniliyor):
        k.yardimci_ekle("Bora", "BORA@b.test", PAROLA)


def test_yardimci_yonetim_islerini_yapamaz(kimlik):
    _, mudur, _ = kayit(kimlik)
    yardimci_id = yardimci(kimlik, mudur)
    bilgi, _ = kimlik.giris("mehmet@a.test", PAROLA)
    with kullanicilar(kimlik, bilgi) as k:
        for islem in (lambda: k.yardimci_ekle("X", "x@a.test", PAROLA),
                      lambda: k.parola_belirle(mudur.kullanici_id, YENI),
                      lambda: k.sil(mudur.kullanici_id),
                      lambda: k.rol_degistir(yardimci_id, "mudur")):
            with pytest.raises(YetkiYok):
                islem()


def test_mudur_parola_belirleyince_kullanicinin_butun_oturumlari_kapanir(kimlik):
    _, mudur, mudur_jetonu = kayit(kimlik)
    yardimci_id = yardimci(kimlik, mudur)
    _, j1 = kimlik.giris("mehmet@a.test", PAROLA)
    _, j2 = kimlik.giris("mehmet@a.test", PAROLA)  # ikinci bilgisayar

    with kullanicilar(kimlik, mudur) as k:
        k.parola_belirle(yardimci_id, YENI)

    assert kimlik.oturum_coz(j1) is None and kimlik.oturum_coz(j2) is None
    assert kimlik.oturum_coz(mudur_jetonu) is not None  # başkasının oturumu etkilenmez
    with pytest.raises(GirisHatasi):
        kimlik.giris("mehmet@a.test", PAROLA)
    kimlik.giris("mehmet@a.test", YENI)


def test_kendi_parolasini_degistiren_kullanicinin_yalnizca_o_anki_oturumu_kalir(kimlik):
    _, mudur, simdiki = kayit(kimlik)
    _, baska = kimlik.giris("ayse@a.test", PAROLA)

    with kullanicilar(kimlik, mudur) as k:
        k.kendi_parolasini_degistir(PAROLA, YENI)

    assert kimlik.oturum_coz(simdiki) is not None
    assert kimlik.oturum_coz(baska) is None
    kimlik.giris("ayse@a.test", YENI)


def test_kendi_parolasini_degistirirken_eski_parola_dogru_olmali(kimlik):
    _, mudur, _ = kayit(kimlik)
    _, baska = kimlik.giris("ayse@a.test", PAROLA)
    with kullanicilar(kimlik, mudur) as k, pytest.raises(GecersizVeri, match="Mevcut parola hatalı"):
        k.kendi_parolasini_degistir("yanlis-parola-12345", YENI)
    assert kimlik.oturum_coz(baska) is not None  # hiçbir şey değişmedi


def test_yeni_parola_da_uzunluk_kuralina_uymali(kimlik):
    _, mudur, _ = kayit(kimlik)
    yardimci_id = yardimci(kimlik, mudur)
    with kullanicilar(kimlik, mudur) as k:
        with pytest.raises(parola.ParolaGecersiz):
            k.parola_belirle(yardimci_id, "kisa")
        with pytest.raises(parola.ParolaGecersiz):
            k.kendi_parolasini_degistir(PAROLA, "kisa")
        with pytest.raises(parola.ParolaGecersiz):
            k.yardimci_ekle("X", "x@a.test", "kisa")


def test_silinen_kullanicinin_oturumlari_gecersiz(kimlik):
    _, mudur, _ = kayit(kimlik)
    yardimci_id = yardimci(kimlik, mudur)
    _, jeton = kimlik.giris("mehmet@a.test", PAROLA)

    with kullanicilar(kimlik, mudur) as k:
        k.sil(yardimci_id)

    assert kimlik.oturum_coz(jeton) is None
    with okul_oturumu(kimlik.fabrika, mudur.okul_id) as o:  # satırlar da gitti (ON DELETE CASCADE)
        assert o.scalars(select(Oturum).where(Oturum.kullanici_id == yardimci_id)).all() == []
    with pytest.raises(GirisHatasi):
        kimlik.giris("mehmet@a.test", PAROLA)


def test_baska_okulun_kullanicisi_bulunamaz(kimlik):
    _, mudur_a, _ = kayit(kimlik, "A Lisesi", "ayse@a.test")
    _, mudur_b, _ = kayit(kimlik, "B Lisesi", "bora@b.test")
    with kullanicilar(kimlik, mudur_a) as k:
        for islem in (lambda: k.sil(mudur_b.kullanici_id), lambda: k.parola_belirle(mudur_b.kullanici_id, YENI),
                      lambda: k.rol_degistir(mudur_b.kullanici_id, "mudur_yardimcisi")):
            with pytest.raises(KayitBulunamadi):
                islem()
        assert [x.email for x in k.listele()] == ["ayse@a.test"]


# --- son müdür ----------------------------------------------------------------------------------

def test_son_mudur_silinemez_ve_rolu_dusurulemez(kimlik):
    _, mudur, jeton = kayit(kimlik)
    with kullanicilar(kimlik, mudur) as k:
        with pytest.raises(SonMudur, match="Okulun son müdürü silinemez"):
            k.sil(mudur.kullanici_id)
        with pytest.raises(SonMudur, match="Okulun son müdürü rolü düşürülemez"):
            k.rol_degistir(mudur.kullanici_id, "mudur_yardimcisi")
    assert kimlik.oturum_coz(jeton) is not None


def test_baska_mudur_varsa_mudur_rolunu_birakabilir_ve_silinebilir(kimlik):
    _, ayse, _ = kayit(kimlik)
    mehmet_id = yardimci(kimlik, ayse)
    with kullanicilar(kimlik, ayse) as k:
        k.rol_degistir(mehmet_id, "mudur")
        k.rol_degistir(ayse.kullanici_id, "mudur_yardimcisi")  # artık Mehmet de müdür
    mehmet, _ = kimlik.giris("mehmet@a.test", PAROLA)
    with kullanicilar(kimlik, mehmet) as k:
        with pytest.raises(SonMudur):
            k.rol_degistir(mehmet_id, "mudur_yardimcisi")  # şimdi son müdür Mehmet
        k.sil(ayse.kullanici_id)
        assert [(x.ad, x.rol) for x in k.listele()] == [("Mehmet Kaya", "mudur")]


def test_gecersiz_rol_reddedilir(kimlik):
    _, mudur, _ = kayit(kimlik)
    mehmet_id = yardimci(kimlik, mudur)
    with kullanicilar(kimlik, mudur) as k, pytest.raises(GecersizVeri):
        k.rol_degistir(mehmet_id, "ogretmen")


def test_iki_mudur_ayni_anda_birbirinin_rolunu_dusururse_okul_mudursuz_kalmaz(kalici_kimlik, monkeypatch):
    """FOR UPDATE: iki işlem de "başka müdür var" görüp birbirini düşürseydi okul müdürsüz kalırdı."""
    kimlik = kalici_kimlik
    okul, ayse_k, _ = kimlik.kayit({"ad": "Tek İşlem Eşzamanlı"}, "Ayşe", "es-ayse@a.test", PAROLA)
    ayse = OturumBilgisi(uuid.uuid4(), ayse_k.id, okul.id)
    with kullanicilar(kimlik, ayse) as k:
        mehmet_id = k.yardimci_ekle("Mehmet", "es-mehmet@a.test", PAROLA).id
        k.rol_degistir(mehmet_id, "mudur")
    mehmet = OturumBilgisi(uuid.uuid4(), mehmet_id, okul.id)

    # Her işlem rolü değiştirip commit etmeden önce biraz bekler: ikisi aynı anda "içeride" olsun.
    gercek_commit = Session.commit

    def yavas_commit(self):
        time.sleep(0.4)
        gercek_commit(self)

    sonuclar = []
    engel = threading.Barrier(2)

    def dusur(istek, hedef):
        engel.wait()
        with kullanicilar(kimlik, istek) as k:
            monkeypatch.setattr(k.oturum, "commit", yavas_commit.__get__(k.oturum))
            try:
                k.rol_degistir(hedef, "mudur_yardimcisi")
                sonuclar.append("düşürüldü")
            except SonMudur:
                sonuclar.append("son müdür")

    is_parcaciklari = [threading.Thread(target=dusur, args=(ayse, mehmet_id)),
                       threading.Thread(target=dusur, args=(mehmet, ayse.kullanici_id))]
    for t in is_parcaciklari:
        t.start()
    for t in is_parcaciklari:
        t.join(15)

    assert sorted(sonuclar) == ["düşürüldü", "son müdür"]
    with kullanicilar(kimlik, ayse) as k:
        assert sum(1 for x in k.listele() if x.rol == "mudur") == 1


# --- sunucudaki parola-sifirla komutu ---------------------------------------------------------

def test_parola_sifirla_komutu_parolayi_degistirir_oturumlari_ve_kilidi_kaldirir(kimlik, monkeypatch, capsys):
    from okulapi.__main__ import main

    _, mudur, j1 = kayit(kimlik)
    _, j2 = kimlik.giris("ayse@a.test", PAROLA)
    for _ in range(5):  # müdür kendini kilitledi
        with pytest.raises(GirisHatasi):
            kimlik.giris("ayse@a.test", "unuttum-parolami-1")
    girdiler = iter([YENI, YENI])
    monkeypatch.setattr("getpass.getpass", lambda _istem="": next(girdiler))

    assert main(["parola-sifirla", "AYSE@a.test"], fabrika=kimlik.fabrika) == 0

    assert kimlik.oturum_coz(j1) is None and kimlik.oturum_coz(j2) is None  # bütün oturumlar
    kimlik.giris("ayse@a.test", YENI)  # kilit de kalktı
    cikti = capsys.readouterr().out
    assert "Ayşe Yılmaz" in cikti and YENI not in cikti  # elle girilen parola yazdırılmaz


def test_parola_sifirla_rastgele_parolayi_bir_kez_gosterir(kimlik, capsys):
    from okulapi.__main__ import main

    kayit(kimlik)
    assert main(["parola-sifirla", "ayse@a.test", "--rastgele"], fabrika=kimlik.fabrika) == 0
    yeni = capsys.readouterr().out.strip().rsplit(": ", 1)[1]
    assert len(yeni) >= 12
    kimlik.giris("ayse@a.test", yeni)


@pytest.mark.parametrize(("email", "girdiler", "kod"), [
    ("kimse@a.test", [YENI, YENI], 1),
    ("ayse@a.test", [YENI, YENI + "x"], 2),
    ("ayse@a.test", ["kisa", "kisa"], 2),
])
def test_parola_sifirla_hatalarda_hicbir_sey_degismez(kimlik, monkeypatch, capsys, email, girdiler, kod):
    from okulapi.__main__ import main

    _, _, jeton = kayit(kimlik)
    it = iter(girdiler)
    monkeypatch.setattr("getpass.getpass", lambda _istem="": next(it))
    assert main(["parola-sifirla", email], fabrika=kimlik.fabrika) == kod
    assert capsys.readouterr().err
    assert kimlik.oturum_coz(jeton) is not None
    kimlik.giris("ayse@a.test", PAROLA)


def test_parola_sifirlamanin_api_karsiligi_yok(ayarlar):
    from okulapi.main import uygulama_olustur

    yollar = [getattr(r, "path", "") for r in uygulama_olustur(ayarlar).routes]
    assert yollar and not any("sifirla" in y or "parolayi" in y for y in yollar)
