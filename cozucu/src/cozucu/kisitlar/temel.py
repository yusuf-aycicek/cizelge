"""Kısıt kurallarının ortak altyapısı: taban sınıf, bağlam ve kayıt defteri (bkz. docs/adr/0002)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import ClassVar

from ortools.sat.python import cp_model

from cozucu.model import CozumGirdisi, DersAtama, KisitTanimi

# (atama_id, gun, saat) -> "bu atama bu saatte yapılıyor mu"
Anahtar = tuple[str, int, int]
# Esnek kuralların döndürdüğü (ceza ifadesi, ağırlık) çiftleri. Zorunlu kurallar boş liste döner.
CezaTerimi = tuple[cp_model.LinearExprT, int]


class GirdiHatasi(Exception):
    """Model kurulamayacak kadar tutarsız girdi (ör. var olmayan atamaya kilit).

    Çözücü bunu yakalayıp `on_kontrol_hatasi` durumuna çevirir; dışarı istisna sızmaz.
    """


@dataclass
class Baglam:
    """Kuralların üzerinde çalıştığı ortak durum. Dizinler bir kez kurulur, tüm kurallar paylaşır."""

    girdi: CozumGirdisi
    model: cp_model.CpModel
    x: dict[Anahtar, cp_model.IntVar]
    gunler: range
    saatler: range
    atama: dict[str, DersAtama]
    sinif_atamalari: dict[str, list[DersAtama]] = field(default_factory=dict)
    ogretmen_atamalari: dict[str, list[DersAtama]] = field(default_factory=dict)

    @classmethod
    def kur(cls, girdi: CozumGirdisi) -> Baglam:
        model = cp_model.CpModel()
        gunler = range(girdi.ayar.gun_sayisi)
        saatler = range(girdi.ayar.gunluk_ders_saati)
        x = {
            (a.id, g, s): model.new_bool_var(f"x[{a.id},{g},{s}]")
            for a in girdi.atamalar
            for g in gunler
            for s in saatler
        }
        sinif_atamalari: dict[str, list[DersAtama]] = defaultdict(list)
        ogretmen_atamalari: dict[str, list[DersAtama]] = defaultdict(list)
        for a in girdi.atamalar:
            sinif_atamalari[a.sinif_id].append(a)
            if a.ogretmen_id is not None:
                ogretmen_atamalari[a.ogretmen_id].append(a)
        return cls(
            girdi=girdi,
            model=model,
            x=x,
            gunler=gunler,
            saatler=saatler,
            atama={a.id: a for a in girdi.atamalar},
            sinif_atamalari=dict(sinif_atamalari),
            ogretmen_atamalari=dict(ogretmen_atamalari),
        )

    def hucre(self, atama_id: str, gun: int, saat: int) -> cp_model.IntVar:
        """Değişkeni döner; atama ya da gün/saat geçersizse anlaşılır bir GirdiHatasi fırlatır."""
        if atama_id not in self.atama:
            raise GirdiHatasi(f"Bilinmeyen ders ataması: {atama_id}")
        if gun not in self.gunler or saat not in self.saatler:
            raise GirdiHatasi(f"Gün/saat okul ayarının dışında: gun={gun}, saat={saat}")
        return self.x[atama_id, gun, saat]


class KisitKurali(ABC):
    """Bir kural = bir sınıf. Yeni kural eklemek mevcut kodu değiştirmez."""

    tur: ClassVar[str]

    @abstractmethod
    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        """Zorunlu kural modele kısıt ekler ve [] döner; esnek kural ceza terimleri döner."""


# tur adı -> kural sınıfı. `kisit` tablosundaki satırlar bu yolla nesneye dönüşür.
KAYIT_DEFTERI: dict[str, type[KisitKurali]] = {}


def kaydet(sinif: type[KisitKurali]) -> type[KisitKurali]:
    if sinif.tur in KAYIT_DEFTERI:
        raise ValueError(f"Aynı tur iki kez kaydedildi: {sinif.tur}")
    KAYIT_DEFTERI[sinif.tur] = sinif
    return sinif


def kural_olustur(tanim: KisitTanimi) -> KisitKurali:
    sinif = KAYIT_DEFTERI.get(tanim.tur)
    if sinif is None:
        raise GirdiHatasi(f"Bilinmeyen kısıt türü: {tanim.tur}")
    try:
        return sinif(**tanim.parametreler)
    except (TypeError, ValueError) as hata:
        raise GirdiHatasi(f"'{tanim.tur}' için geçersiz parametreler: {tanim.parametreler}") from hata
