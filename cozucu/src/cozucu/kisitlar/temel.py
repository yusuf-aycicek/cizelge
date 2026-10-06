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
# Çelişki analizinde bir kısıt grubunu adlandırır: ("gelemez", "o-ayse"), ("kilit", atama, gun, saat)
GrupAnahtari = tuple[str | int, ...]


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
    # Çelişki analizi kipinde: grup anahtarı -> varsayım literali. Normal çözümde None.
    gruplar: dict[GrupAnahtari, cp_model.IntVar] | None = None

    def grupla(self, kisit: cp_model.Constraint, *anahtar: str | int) -> None:
        """Zorunlu bir kısıtı anlamlı bir gruba bağlar (ör. "gelemez", öğretmen_id).

        Normal çözümde hiçbir şey yapmaz. Analiz kipinde kısıt, grubun varsayım literali
        doğruysa geçerli olur; CP-SAT böylece hangi grupların birlikte çeliştiğini söyleyebilir.
        """
        if self.gruplar is None:
            return
        if anahtar not in self.gruplar:
            self.gruplar[anahtar] = self.model.new_bool_var(f"grup{anahtar}")
        kisit.only_enforce_if(self.gruplar[anahtar])

    @classmethod
    def kur(cls, girdi: CozumGirdisi, analiz: bool = False) -> Baglam:
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
            gruplar={} if analiz else None,
        )

    def hucre(self, atama_id: str, gun: int, saat: int) -> cp_model.IntVar:
        """Değişkeni döner; atama ya da gün/saat geçersizse anlaşılır bir GirdiHatasi fırlatır."""
        if atama_id not in self.atama:
            raise GirdiHatasi(f"Bilinmeyen ders ataması: {atama_id}")
        if gun not in self.gunler or saat not in self.saatler:
            raise GirdiHatasi(f"Gün/saat okul ayarının dışında: gun={gun}, saat={saat}")
        return self.x[atama_id, gun, saat]


    def dolu(self, atamalar: list[DersAtama], gun: int, saat: int) -> cp_model.LinearExprT:
        """Bu atamalardan biri o saatte var mı (0/1). Çakışma kuralları toplamı en fazla 1 tutar."""
        return sum(self.x[a.id, gun, saat] for a in atamalar)


class KisitKurali(ABC):
    """Bir kural = bir sınıf. Yeni kural eklemek mevcut kodu değiştirmez.

    `zorunlu` ve `agirlik` örneğe `kural_olustur` tarafından `kisit` tanımından aktarılır.
    Sınıf, hangi kipte çalışabildiğini `zorunlu_olabilir` / `esnek_olabilir` ile bildirir.
    """

    tur: ClassVar[str]
    zorunlu_olabilir: ClassVar[bool] = True
    esnek_olabilir: ClassVar[bool] = False

    zorunlu: bool = True
    agirlik: int = 1

    @abstractmethod
    def uygula(self, baglam: Baglam) -> list[CezaTerimi]:
        """Zorunlu kipte modele kısıt ekler ve [] döner; esnek kipte ceza terimleri döner."""


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
    if tanim.zorunlu and not sinif.zorunlu_olabilir:
        raise GirdiHatasi(f"'{tanim.tur}' yalnızca esnek olabilir (zorunlu=false verin)")
    if not tanim.zorunlu and not sinif.esnek_olabilir:
        raise GirdiHatasi(f"'{tanim.tur}' yalnızca zorunlu olabilir")
    if tanim.agirlik < 0:
        raise GirdiHatasi(f"'{tanim.tur}' için ağırlık negatif olamaz: {tanim.agirlik}")
    try:
        kural = sinif(**tanim.parametreler)
    except (TypeError, ValueError) as hata:
        raise GirdiHatasi(f"'{tanim.tur}' için geçersiz parametreler: {tanim.parametreler}") from hata
    kural.zorunlu = tanim.zorunlu
    kural.agirlik = tanim.agirlik
    return kural
