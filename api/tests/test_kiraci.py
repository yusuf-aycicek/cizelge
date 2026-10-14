"""Okul filtresi (ORM düzeyi): her sorgu türünde yalnızca oturumun okulu görünür ve yazılır."""

from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select, text, update

from okulapi.cekirdek.kiraci import OkulBaglamiYokHatasi, OkulIhlaliHatasi, okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.modeller import Okul, Ogretmen, Sinif
from okulapi.cekirdek.servisler import GecersizVeri, OkulServisi, SinifServisi


@pytest.fixture
def iki_okul(oturum_fabrikasi):
    """A ve B okulları; her birinde iki öğretmen ve bir sınıf."""
    # Okul, servis üzerinden oluşturulur: RLS, okul satırının yalnızca kendi bağlamında
    # eklenmesine izin verir ve servis bu bağlamı kurar.
    with okulsuz_oturum(oturum_fabrikasi) as oturum:
        a, b = OkulServisi(oturum).olustur({"ad": "A Lisesi"}), OkulServisi(oturum).olustur({"ad": "B Lisesi"})
    for okul, onek in ((a, "A"), (b, "B")):
        with okul_oturumu(oturum_fabrikasi, okul.id) as oturum:
            oturum.add_all([Ogretmen(ad=f"{onek} Öğretmen 1"), Ogretmen(ad=f"{onek} Öğretmen 2"),
                            Sinif(ad="9-A", seviye=9)])
            oturum.commit()
    return a.id, b.id


def adlar(oturum, model=Ogretmen) -> set[str]:
    return set(oturum.scalars(select(model.ad)))


def test_listeleme_yalnizca_kendi_okulu(oturum_fabrikasi, iki_okul):
    a, b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        assert adlar(oturum) == {"A Öğretmen 1", "A Öğretmen 2"}
    with okul_oturumu(oturum_fabrikasi, b) as oturum:
        assert adlar(oturum) == {"B Öğretmen 1", "B Öğretmen 2"}


# Her biri A'nın oturumunda 2 sonuç vermeli (A'da 2 öğretmen, 1 sınıf; B'de de aynı).
# Filtre kaçarsa 4 (ya da birleştirmede 8) çıkar.
SORGU_BICIMLERI = {
    "model": lambda: select(func.count()).select_from(select(Ogretmen).subquery()),
    "select_from ile sayım": lambda: select(func.count()).select_from(Ogretmen),
    "sütunla sayım": lambda: select(func.count(Ogretmen.id)),
    "tek sütun": lambda: select(func.count()).select_from(select(Ogretmen.ad).subquery()),
    "birleştirme": lambda: select(func.count()).select_from(Ogretmen).join(Sinif, Sinif.okul_id == Ogretmen.okul_id),
    "alt sorgu": lambda: select(func.count()).where(Ogretmen.id.in_(select(Ogretmen.id))),
}


@pytest.mark.parametrize("bicim", SORGU_BICIMLERI)
def test_her_sorgu_biciminde_filtre_uygulanir(oturum_fabrikasi, iki_okul, bicim):
    a, _b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        assert oturum.scalar(SORGU_BICIMLERI[bicim]()) == 2


def test_baska_okulun_kaydi_kimlikle_de_getirilemez(oturum_fabrikasi, iki_okul):
    a, b = iki_okul
    with okul_oturumu(oturum_fabrikasi, b) as oturum:
        b_ogretmen_id = oturum.scalars(select(Ogretmen.id)).first()
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        assert oturum.get(Ogretmen, b_ogretmen_id) is None
        assert oturum.scalars(select(Ogretmen).where(Ogretmen.id == b_ogretmen_id)).first() is None


def test_toplu_guncelleme_ve_silme_yalnizca_kendi_okulunu_etkiler(oturum_fabrikasi, iki_okul):
    a, b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        oturum.execute(update(Ogretmen).values(brans="Matematik"))
        oturum.execute(delete(Sinif))
        oturum.commit()
    with okul_oturumu(oturum_fabrikasi, b) as oturum:
        assert set(oturum.scalars(select(Ogretmen.brans))) == {""}
        assert adlar(oturum, Sinif) == {"9-A"}
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        assert set(oturum.scalars(select(Ogretmen.brans))) == {"Matematik"}
        assert adlar(oturum, Sinif) == set()


def test_yeni_kayda_okul_otomatik_yazilir(oturum_fabrikasi, iki_okul):
    a, _b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        ogretmen = Ogretmen(ad="Yeni")
        oturum.add(ogretmen)
        oturum.flush()
        assert ogretmen.okul_id == a


def test_baska_okula_kayit_eklenemez(oturum_fabrikasi, iki_okul):
    a, b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        oturum.add(Ogretmen(ad="Sızma", okul_id=b))
        with pytest.raises(OkulIhlaliHatasi):
            oturum.flush()


def test_kaydin_okulu_degistirilemez(oturum_fabrikasi, iki_okul):
    a, b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        ogretmen = oturum.scalars(select(Ogretmen)).first()
        ogretmen.okul_id = b
        with pytest.raises(OkulIhlaliHatasi):
            oturum.flush()


def test_okulsuz_oturum_okula_ait_tabloya_erisemez(oturum_fabrikasi, iki_okul):
    with okulsuz_oturum(oturum_fabrikasi) as oturum:
        with pytest.raises(OkulBaglamiYokHatasi):
            oturum.scalars(select(Ogretmen)).all()
        oturum.add(Ogretmen(ad="Okulsuz"))
        with pytest.raises(OkulBaglamiYokHatasi):
            oturum.flush()
        oturum.rollback()  # başarısız flush'tan sonra bekleyen kayıt oturumdan atılır
        # Okul tablosu ORM filtresine tabi değildir, ama RLS'ye tabidir: okulsuz oturum hiçbir
        # okulu görmez (RLS öncesinde bütün okulları görüyordu).
        assert set(oturum.scalars(select(Okul.ad))) == set()


@pytest.mark.parametrize("sorgu", [
    text("SELECT count(*) FROM ogretmen"),
    select(func.count()).select_from(Ogretmen.__table__),
], ids=["ham SQL", "Core tablo nesnesi"])
def test_orm_disi_sorgulari_rls_filtreler(oturum_fabrikasi, iki_okul, sorgu):
    """Ham SQL ve Core tablo nesneleri ORM filtresinden geçmez (bilinen sınırdı). 4. alt adımdan
    beri PostgreSQL'in satır düzeyi güvenliği (RLS) onları da filtreler: A'nın bağlamında yalnızca
    A'nın 2 öğretmeni görünür (RLS öncesinde 4'ü de görünüyordu). Okulsuz bağlamda hiçbiri."""
    a, _b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        assert oturum.scalar(sorgu) == 2
    with okulsuz_oturum(oturum_fabrikasi) as oturum:
        assert oturum.scalar(text("SELECT count(*) FROM ogretmen")) == 0


def test_veritabani_check_kisiti_anlasilir_hataya_cevrilir(oturum_fabrikasi, iki_okul):
    # API doğrulaması (Pydantic) atlanarak doğrudan servise geçersiz değer verilir: son güvence
    # veritabanının CHECK kısıtıdır, servis bunu anlaşılır bir hataya çevirir.
    a, _b = iki_okul
    with okul_oturumu(oturum_fabrikasi, a) as oturum:
        with pytest.raises(GecersizVeri, match="Sınıf: geçersiz değer"):
            SinifServisi(oturum).olustur({"ad": "13-A", "seviye": 13})
