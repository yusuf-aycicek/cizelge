"""Paylaşım linkleri (8b, ADR 0022): yayınlanan programı girişsiz, salt okunur gösterir.

İki taraf var:
- **Yönetici** (oturumlu, okul bağlamında): linkleri oluşturur, yeniler, iptal eder. Sıradan okul
  tablosudur; okul filtresi ve RLS her yerdeki gibi.
- **Linkle gelen** (oturumsuz): `icerik(jeton)` okulsuz bir oturumla `paylasim_icerigi` veritabanı
  fonksiyonunu çağırır. Fonksiyon jetonun kapsamına göre süzülmüş içeriği döner; uygulama başka
  hiçbir satıra erişmez (okul bağlamı açılmaz, bütün tablolar RLS ile kapalıdır).
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from okulapi.cekirdek.depo import OgretmenDeposu, SinifDeposu
from okulapi.cekirdek.servisler import GecersizVeri, KayitBulunamadi
from okulapi.moduller.ders_programi.cikti import anlik
from okulapi.moduller.ders_programi.modeller import PaylasimLinki

JETON_BAYT = 32  # 256 bit; token_urlsafe ile 43 karakter


def yeni_jeton() -> str:
    return secrets.token_urlsafe(JETON_BAYT)


class PaylasimServisi:
    """Yöneticinin link işlemleri (oturumun okulunda)."""

    def __init__(self, oturum) -> None:
        self.oturum = oturum

    def _hedef_adlari(self) -> tuple[dict, dict]:
        return ({o.id: o.ad for o in OgretmenDeposu(self.oturum).listele()},
                {s.id: s.ad for s in SinifDeposu(self.oturum).listele()})

    def _yanit(self, link: PaylasimLinki, ogretmenler: dict, siniflar: dict) -> dict[str, Any]:
        hedef = {"okul": "Bütün okul", "ogretmen": ogretmenler.get(link.ogretmen_id, ""),
                 "sube": siniflar.get(link.sinif_id, "")}[link.tur]
        return {"id": link.id, "tur": link.tur, "ogretmen_id": link.ogretmen_id, "sinif_id": link.sinif_id,
                "hedef_adi": hedef, "jeton": link.jeton, "olusturma": link.olusturma}

    def listele(self) -> list[dict[str, Any]]:
        ogretmenler, siniflar = self._hedef_adlari()
        linkler = self.oturum.scalars(select(PaylasimLinki).order_by(PaylasimLinki.olusturma, PaylasimLinki.id))
        return [self._yanit(link, ogretmenler, siniflar) for link in linkler]

    def _getir(self, link_id: uuid.UUID) -> PaylasimLinki:
        link = self.oturum.get(PaylasimLinki, link_id)
        if link is None:
            raise KayitBulunamadi("Paylaşım linki")
        return link

    def _mevcut(self, tur: str, ogretmen_id, sinif_id) -> PaylasimLinki | None:
        return self.oturum.scalars(select(PaylasimLinki).where(
            PaylasimLinki.tur == tur, PaylasimLinki.ogretmen_id.is_not_distinct_from(ogretmen_id),
            PaylasimLinki.sinif_id.is_not_distinct_from(sinif_id))).first()

    def olustur(self, tur: str, ogretmen_id: uuid.UUID | None = None, sinif_id: uuid.UUID | None = None) -> dict[str, Any]:
        """Kapsamın linki; zaten varsa o döner (kapsam başına tek link)."""
        if (tur == "ogretmen") != (ogretmen_id is not None) or (tur == "sube") != (sinif_id is not None):
            raise GecersizVeri("Öğretmen linki için öğretmen, şube linki için şube seçilmeli; okul linki ikisini de almaz")
        if ogretmen_id is not None and OgretmenDeposu(self.oturum).getir(ogretmen_id) is None:
            raise KayitBulunamadi("Öğretmen")
        if sinif_id is not None and SinifDeposu(self.oturum).getir(sinif_id) is None:
            raise KayitBulunamadi("Sınıf")
        link = self._mevcut(tur, ogretmen_id, sinif_id)
        if link is None:
            link = PaylasimLinki(tur=tur, ogretmen_id=ogretmen_id, sinif_id=sinif_id, jeton=yeni_jeton())
            self.oturum.add(link)
            try:
                self.oturum.commit()
            except IntegrityError:  # aynı anda iki istek: ötekinin linki kullanılır
                self.oturum.rollback()
                link = self._mevcut(tur, ogretmen_id, sinif_id)
        return self._yanit(link, *self._hedef_adlari())

    def toplu_olustur(self, tur: str) -> list[dict[str, Any]]:
        """Linki olmayan bütün öğretmenlere (ya da şubelere) link; hepsinin listesi döner."""
        if tur == "ogretmen":
            hedefler = [{"ogretmen_id": o.id} for o in OgretmenDeposu(self.oturum).listele()]
        elif tur == "sube":
            hedefler = [{"sinif_id": s.id} for s in SinifDeposu(self.oturum).listele()]
        else:
            raise GecersizVeri("Toplu link yalnızca öğretmenler ya da şubeler için")
        for h in hedefler:
            if self._mevcut(tur, h.get("ogretmen_id"), h.get("sinif_id")) is None:
                self.oturum.add(PaylasimLinki(tur=tur, jeton=yeni_jeton(), **h))
        self.oturum.commit()
        return [link for link in self.listele() if link["tur"] == tur]

    def yenile(self, link_id: uuid.UUID) -> dict[str, Any]:
        """Yeni jeton: eski link o anda çalışmaz olur."""
        link = self._getir(link_id)
        link.jeton = yeni_jeton()
        self.oturum.commit()
        return self._yanit(link, *self._hedef_adlari())

    def iptal(self, link_id: uuid.UUID) -> None:
        self.oturum.delete(self._getir(link_id))
        self.oturum.commit()


def icerik(okulsuz_oturum, jeton: str) -> dict[str, Any] | None:
    """Linkle gelenin göreceği: `{"tur", "yayin_zamani", "icerik"}` (yayın yoksa `icerik` boş);
    link yoksa ya da iptal edildiyse None. Okulsuz oturumla çağrılır (ADR 0022)."""
    if not jeton or len(jeton) > 100:
        return None
    return okulsuz_oturum.scalar(select(func.paylasim_icerigi(jeton)))


def cikti_modeli(veri: dict[str, Any]):
    return anlik.jsondan(veri["icerik"])
