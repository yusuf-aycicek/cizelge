"""Veritabanı bağlantısı: motor (engine), oturum (session) ve bütün modellerin ortak tabanı.

Kavramlar (SQLAlchemy 2.0):
- **Engine:** veritabanına bağlantıları yöneten nesne. İçinde bir bağlantı havuzu (pool) vardır:
  bağlantılar her istekte yeniden açılmaz, havuzdan alınıp geri verilir.
- **Session:** bir iş biriminin (unit of work) nesnelerini izler ve `commit` ile tek bir
  veritabanı işleminde (transaction) yazar. Her HTTP isteği kendi oturumunu kullanır.
- **Base:** bütün tablo sınıflarının türediği taban. Tablolar `Base.metadata`'da toplanır;
  Alembic farkları bu metadata ile veritabanını karşılaştırarak bulur.
"""

from __future__ import annotations

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Kısıt ve indeks adlandırma kuralı. PostgreSQL adsız kısıtlara kendisi ad verir; adı bilmeden
# bir migration o kısıtı silemez ya da değiştiremez. Kuralla adlar öngörülebilir olur:
# ör. uq_sinif_okul_id_ad, fk_ders_atama_okul_id_ogretmen_id_ogretmen, ck_okul_gun_sayisi.
ADLANDIRMA_KURALI = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}


class Base(DeclarativeBase):
    """Çekirdek ve bütün modüllerin modelleri bu tabandan türer (tek metadata)."""

    metadata = MetaData(naming_convention=ADLANDIRMA_KURALI)


BAGLANTI_ZAMAN_ASIMI_SN = 3


def motor_olustur(url: str, **secenekler) -> Engine:
    # pool_pre_ping: havuzdan alınan bağlantı ölmüşse (ör. veritabanı yeniden başladıysa) fark edip
    # yenisini açar. connect_timeout: veritabanı yanıt vermezse sonsuza kadar beklenmez (varsayılan
    # yoktur; bazı ağlarda kapalı porta bağlanma reddedilmez, zaman aşımına kadar bekler).
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": BAGLANTI_ZAMAN_ASIMI_SN},
                         **secenekler)


def oturum_fabrikasi(motor: Engine) -> sessionmaker:
    return sessionmaker(bind=motor, expire_on_commit=False)
