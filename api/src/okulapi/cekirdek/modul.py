"""Modül sözleşmesi ve modül yükleyici (bkz. docs/adr/0008).

Çekirdek modülleri adıyla yükler ama hiçbir modülü doğrudan içe aktarmaz: bağımlılık yalnızca
modülden çekirdeğe doğrudur. Bir modül, `okulapi.moduller.<ad>` paketinde `MODUL` adlı bir
`Modul` nesnesi tanımlar.

Kancalar (ADR 0014): çekirdeğin bir işi modül verisini etkilediğinde çekirdek modülü bilmeden ona
sorar. Modül, sözleşmeye isteğe bağlı fonksiyonlar koyarak kendini bildirir:
- `okul_ayari_etkisi(oturum, gun_sayisi, gunluk_ders_saati, uygula)`: okulun gün/saat ayarı
  değişirse modül verisine ne olacağını kullanıcının diliyle döner; `uygula=True` ise yapar.
- `kullanim_aciklamasi(oturum, tablo, kayit_id)`: çekirdekteki bir kayıt (öğretmen, sınıf,
  ders) silinemediğinde modülde nerede kullanıldığını kullanıcının diliyle döner.
"""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter
from sqlalchemy.orm import Session

OkulAyariEtkisi = Callable[[Session, int, int, bool], list[str]]
KullanimAciklamasi = Callable[[Session, str, uuid.UUID], list[str]]


@dataclass(frozen=True)
class Modul:
    ad: str  # paket adıyla aynı: "ders_programi"
    onek: str  # API yolu öneki: /api/<onek>
    router: APIRouter
    migration_dizini: Path  # Alembic sürüm klasörü; içindeki dalın etiketi `ad` olmalı
    modeller: ModuleType | None = None  # içe aktarılınca tabloları Base.metadata'ya kaydolur
    okul_ayari_etkisi: OkulAyariEtkisi | None = None
    kullanim_aciklamasi: KullanimAciklamasi | None = None


class ModulHatasi(Exception):
    pass


def modulleri_yukle(adlar: list[str]) -> list[Modul]:
    moduller: list[Modul] = []
    for ad in adlar:
        try:
            paket = importlib.import_module(f"okulapi.moduller.{ad}")
        except ModuleNotFoundError as hata:
            raise ModulHatasi(f"Modül bulunamadı: {ad} (okulapi/moduller/{ad}/ yok)") from hata
        modul = getattr(paket, "MODUL", None)
        if not isinstance(modul, Modul):
            raise ModulHatasi(f"okulapi.moduller.{ad} bir MODUL (Modul) tanımlamıyor")
        if modul.ad != ad:
            raise ModulHatasi(f"Modül adı paket adıyla aynı olmalı: {modul.ad} != {ad}")
        if not modul.migration_dizini.is_dir():
            raise ModulHatasi(f"{ad}: migration dizini yok: {modul.migration_dizini}")
        moduller.append(modul)
    if len({m.onek for m in moduller}) != len(moduller):
        raise ModulHatasi("İki modül aynı API önekini kullanıyor")
    return moduller
