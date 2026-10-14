"""Okul izolasyonu, ORM katmanı (bkz. docs/adr/0009).

Okul bilgisi veritabanı oturumuna (Session) bağlıdır: `oturum.info["okul_id"]`. Bir oturum tek
bir okula aittir ve bir HTTP isteği boyunca yaşar. Okul bilgisi bir `ContextVar` ile değil oturumla
taşınır, çünkü FastAPI senkron bağımlılıkları ayrı bir iş parçacığında, bağlamın kopyasıyla
çalıştırır; bağımlılıkta yazılan bir ContextVar endpoint'e ulaşmayabilir. Oturum ise iş biriminin
kendisidir ve 4. alt adımdaki RLS ayarı (`SET LOCAL`) da işlem başına uygulanacaktır.

SQLAlchemy olayları (event) bütün oturumlar için bir kez kaydedilir:
- `do_orm_execute`: okula ait modellere dokunan her ORM SELECT/UPDATE/DELETE'e
  `okul_id = <oturumun okulu>` koşulu eklenir. Oturumun okulu yoksa hata fırlatılır.
- `before_flush`: yeni kayda `okul_id` otomatik yazılır; başka bir okulun okul_id'si verilmişse ya
  da var olan bir kaydın okul_id'si değiştirilmişse hata fırlatılır.

Endpoint ya da servis yazan kişinin okul filtresini hatırlaması gerekmez. Bu dosya filtrenin
uygulandığı tek yerdir. Ham SQL (`text(...)`) bu filtreden geçmez; onu 4. alt adımda veritabanı
düzeyindeki RLS korur.
"""

from __future__ import annotations

import uuid

from sqlalchemy import event, inspect
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria
from sqlalchemy.sql.util import find_tables

from okulapi.cekirdek.modeller import OkulaAitMixin
from okulapi.cekirdek.veritabani import Base

OKUL_ANAHTARI = "okul_id"


class OkulBaglamiYokHatasi(RuntimeError):
    """Okul bilgisi olmayan bir oturumla okula ait bir tabloya erişildi (programlama hatası)."""


class OkulIhlaliHatasi(RuntimeError):
    """Bir kayıt, oturumun okulundan başka bir okula yazılmaya ya da taşınmaya çalışıldı."""


def okul_oturumu(fabrika: sessionmaker, okul_id: uuid.UUID) -> Session:
    """Yalnızca verilen okulun verisini gören ve yazan bir oturum."""
    oturum = fabrika()
    oturum.info[OKUL_ANAHTARI] = okul_id
    return oturum


def okulsuz_oturum(fabrika: sessionmaker) -> Session:
    """Okula ait tablolara erişemeyen oturum (ör. okul kaydı oluşturmak için)."""
    oturum = fabrika()
    oturum.info[OKUL_ANAHTARI] = None
    return oturum


def oturumun_okulu(oturum: Session) -> uuid.UUID | None:
    return oturum.info.get(OKUL_ANAHTARI)


def _okula_ait_tablolar() -> set:
    return {m.local_table for m in Base.registry.mappers if issubclass(m.class_, OkulaAitMixin)}


def _okula_ait_mi(durum: ORMExecuteState) -> bool:
    """Sorgu okula ait bir tabloya dokunuyor mu?

    Yalnızca `all_mappers`'a bakmak yetmez: `select(func.count()).select_from(Ogretmen)` gibi bir
    sorguda seçilen sütunlarda model yoktur ve `all_mappers` boştur, ama sorgu yine de ogretmen
    tablosunu okur (testle yakalanan bir açık). Bu yüzden FROM'daki tablolara da bakılır.
    """
    if any(issubclass(mapper.class_, OkulaAitMixin) for mapper in durum.all_mappers):
        return True
    okula_ait = _okula_ait_tablolar()
    for tablo in find_tables(durum.statement, include_aliases=True, include_joins=True, check_columns=True):
        while hasattr(tablo, "element"):  # takma ad (alias) -> asıl tablo
            tablo = tablo.element
        if tablo in okula_ait:
            return True
    return False


@event.listens_for(Session, "do_orm_execute")
def _okul_filtresi(durum: ORMExecuteState) -> None:
    if not (durum.is_select or durum.is_update or durum.is_delete):
        return
    # İlişki ve sütun yüklemeleri ana sorgunun koşulunu zaten taşır (propagate_to_loaders).
    if durum.is_column_load or durum.is_relationship_load:
        return
    if not _okula_ait_mi(durum):
        return
    okul_id = oturumun_okulu(durum.session)
    if okul_id is None:
        raise OkulBaglamiYokHatasi("Okul bilgisi olmayan bir oturumla okula ait tabloya erişilemez")
    durum.statement = durum.statement.options(
        with_loader_criteria(OkulaAitMixin, lambda sinif: sinif.okul_id == okul_id, include_aliases=True)
    )


@event.listens_for(Session, "before_flush")
def _okul_yaz_ve_denetle(oturum: Session, _baglam, _nesneler) -> None:
    okul_id = oturumun_okulu(oturum)
    for nesne in oturum.new:
        if not isinstance(nesne, OkulaAitMixin):
            continue
        if okul_id is None:
            raise OkulBaglamiYokHatasi(f"Okul bilgisi olmayan bir oturumla {type(nesne).__name__} eklenemez")
        if nesne.okul_id is None:
            nesne.okul_id = okul_id
        elif nesne.okul_id != okul_id:
            raise OkulIhlaliHatasi(f"{type(nesne).__name__} başka bir okula yazılamaz")
    for nesne in oturum.dirty:
        if isinstance(nesne, OkulaAitMixin) and inspect(nesne).attrs.okul_id.history.has_changes():
            raise OkulIhlaliHatasi(f"{type(nesne).__name__} kaydının okulu değiştirilemez")
