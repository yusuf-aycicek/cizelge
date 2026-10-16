"""Okul geneli kurallar, kullanıcının diliyle (docs/arayuz-plani.md bölüm 2.3).

- Varsayılan kurallar çözücüden gelir (`cozucu.kisitlar.VARSAYILAN_KISITLAR`); okul bir kuralı
  değiştirince `kisit` tablosuna aynı türde bir kayıt yazılır ve varsayılanın yerini alır.
  "Varsayılana dön" o kaydı siler. Arayüz varsayılanları kendisi bilmez, buradan okur.
- Esnek kuralların ağırlığı arayüzde sayı olarak değil, **önem seviyesi** olarak seçilir:
  Önemsiz / Önemli / Çok önemli. Her kuralın kendi üç sayısı vardır (varsayılan ağırlıklar
  kurala göre farklıdır) ve **"Önemli" = çözücünün varsayılan ağırlığı**. Karşılıklar yalnızca
  `ONEM_KARSILIKLARI`'nda tanımlıdır; okul müdürünün cevaplarına göre burada ayarlanacak
  (CLAUDE.md bölüm 10). Eşitliği test_kurallar.py denetler.
"""

from __future__ import annotations

from typing import Any

from cozucu.kisitlar import VARSAYILAN_KISITLAR, GirdiHatasi, kural_olustur
from cozucu.model import KisitTanimi
from sqlalchemy import select
from sqlalchemy.orm import Session

from okulapi.cekirdek.servisler import GecersizVeri, KayitBulunamadi
from okulapi.moduller.ders_programi.modeller import Kisit

ONEM_SEVIYELERI = ("onemsiz", "onemli", "cok_onemli")
OZEL = "ozel"  # kayıtlı ağırlık hiçbir seviyeye denk gelmiyorsa (ör. API ile elle girilmiş)

ONEM_KARSILIKLARI: dict[str, dict[str, int]] = {
    "sinif_boslugu": {"onemsiz": 10, "onemli": 30, "cok_onemli": 60},
    "degisiklik": {"onemsiz": 3, "onemli": 8, "cok_onemli": 20},
    "tercih_etmez": {"onemsiz": 2, "onemli": 5, "cok_onemli": 12},
    "bos_gun": {"onemsiz": 1, "onemli": 4, "cok_onemli": 10},
    "ogretmen_penceresi": {"onemsiz": 1, "onemli": 3, "cok_onemli": 8},
    "ardisik_ders": {"onemsiz": 1, "onemli": 2, "cok_onemli": 5},
}

# Arayüzde gösterim sırası ve metinler. Esnekler varsayılan önem sırasıyla (ağır olan önce).
KURAL_METINLERI: dict[str, tuple[str, str]] = {
    "gunluk_ders_siniri": (
        "Aynı dersin günlük sınırı",
        "Aynı ders bir sınıfa günde en fazla bu kadar saat konur.",
    ),
    "ogretmen_gunluk_siniri": (
        "Öğretmenin günlük ders sınırı",
        "Bir öğretmen günde en fazla bu kadar saat derse girer.",
    ),
    "sinif_boslugu": (
        "Sınıfların boş saati olmasın",
        "Dersler günün başından başlar; sınıfın gün ortasında boş saati kalmaz.",
    ),
    "degisiklik": (
        "Mevcut programa bağlılık",
        "Bir program temel alınarak yeniden üretilirken dersler olabildiğince yerinde kalır.",
    ),
    "tercih_etmez": (
        "Öğretmenin tercih etmediği saatler",
        "Öğretmenin \"tercih etmez\" işaretlediği saatlere ders konmamaya çalışılır.",
    ),
    "bos_gun": (
        "Öğretmene boş gün",
        "Her öğretmene haftada bu kadar boş gün kazandırılmaya çalışılır. Ders yükü buna izin "
        "vermeyen öğretmen için zorlanmaz.",
    ),
    "ogretmen_penceresi": (
        "Öğretmenin boş (pencere) saatleri",
        "Öğretmenin aynı gündeki iki dersi arasında boş saat kalmamaya çalışılır.",
    ),
    "ardisik_ders": (
        "Bir dersin saatleri arka arkaya",
        "Bir dersin aynı gündeki saatleri arka arkaya konmaya çalışılır.",
    ),
}

VARSAYILANLAR: dict[str, KisitTanimi] = {t.tur: t for t in VARSAYILAN_KISITLAR}

# Parametrelerin en küçük değerleri: kullanıcının diliyle hata için (çözücü de ayrıca denetler).
PARAMETRE_ALT_SINIRLARI = {"n": 1, "m": 1, "hedef_bos_gun": 0}


def seviye(tur: str, agirlik: int) -> str:
    for ad, deger in ONEM_KARSILIKLARI[tur].items():
        if deger == agirlik:
            return ad
    return OZEL


class KurallarServisi:
    def __init__(self, oturum: Session) -> None:
        self.oturum = oturum

    def _kayit(self, tur: str) -> Kisit | None:
        return self.oturum.scalars(select(Kisit).where(Kisit.tur == tur)).one_or_none()

    def _kural(self, tur: str, kayit: Kisit | None) -> dict[str, Any]:
        v = VARSAYILANLAR[tur]
        parametreler = dict(kayit.parametreler) if kayit else dict(v.parametreler)
        agirlik = kayit.agirlik if kayit else v.agirlik
        ad, aciklama = KURAL_METINLERI[tur]
        return {
            "tur": tur,
            "ad": ad,
            "aciklama": aciklama,
            "zorunlu": v.zorunlu,
            "parametreler": parametreler,
            "varsayilan_parametreler": dict(v.parametreler),
            "agirlik": None if v.zorunlu else agirlik,
            "seviye": None if v.zorunlu else seviye(tur, agirlik),
            "varsayilan_seviye": None if v.zorunlu else seviye(tur, v.agirlik),
            "varsayilan": kayit is None,
        }

    def listele(self) -> list[dict[str, Any]]:
        kayitlar = {k.tur: k for k in self.oturum.scalars(select(Kisit))}
        return [self._kural(tur, kayitlar.get(tur)) for tur in KURAL_METINLERI]

    def ayarla(self, tur: str, parametreler: dict[str, int] | None, onem: str | None) -> dict[str, Any]:
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        v = VARSAYILANLAR[tur]
        if onem is not None and v.zorunlu:
            raise GecersizVeri("Zorunlu kuralların önem seviyesi yoktur")
        kayit = self._kayit(tur)
        yeni_parametreler = {**(kayit.parametreler if kayit else v.parametreler), **(parametreler or {})}
        if set(yeni_parametreler) != set(v.parametreler):
            raise GecersizVeri(f"Bu kuralın ayarları: {', '.join(v.parametreler) or 'yok'}")
        for ad, deger in yeni_parametreler.items():
            alt = PARAMETRE_ALT_SINIRLARI.get(ad, 0)
            if deger < alt:
                raise GecersizVeri(f"{KURAL_METINLERI[tur][0]}: en az {alt} olmalı")
        agirlik = ONEM_KARSILIKLARI[tur][onem] if onem else (kayit.agirlik if kayit else v.agirlik)
        try:
            kural_olustur(KisitTanimi(tur, yeni_parametreler, zorunlu=v.zorunlu, agirlik=agirlik))
        except GirdiHatasi as hata:
            raise GecersizVeri(str(hata)) from hata
        if kayit is None:
            kayit = Kisit(tur=tur, zorunlu=v.zorunlu, agirlik=agirlik, parametreler=yeni_parametreler)
            self.oturum.add(kayit)
        else:
            kayit.parametreler, kayit.agirlik = yeni_parametreler, agirlik
        self.oturum.commit()
        return self._kural(tur, kayit)

    def varsayilana_don(self, tur: str) -> dict[str, Any]:
        if tur not in VARSAYILANLAR:
            raise KayitBulunamadi("Kural")
        kayit = self._kayit(tur)
        if kayit is not None:
            self.oturum.delete(kayit)
            self.oturum.commit()
        return self._kural(tur, None)
