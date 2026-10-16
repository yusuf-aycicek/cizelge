"""Ders programı modülünün çekirdeğe verdiği kancalar (ADR 0014).

Çekirdek bu modülü bilmez. Okulun gün/saat ayarı değişirken ya da bir öğretmen, sınıf veya ders
silinemediğinde, modül sözleşmesindeki bu fonksiyonlarla "bu modülde ne olur / nerede
kullanılıyor" diye sorar. Cevaplar kullanıcının diliyle, kimlik değil ad kullanır.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from okulapi.cekirdek.modeller import Ders, Ogretmen, Sinif
from okulapi.moduller.ders_programi.modeller import DersAtama, Musaitlik, Program, SeviyeSablonu, Yerlesim

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
EN_COK_ORNEK = 5


def _dogal(metin: str):
    """"9-A" < "10-A": sayıları sayı olarak sırala."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", metin)]


def _liste(adlar: list[str]) -> str:
    adlar = sorted(adlar, key=_dogal)
    if len(adlar) <= EN_COK_ORNEK:
        return ", ".join(adlar)
    return ", ".join(adlar[:EN_COK_ORNEK]) + f" ve {len(adlar) - EN_COK_ORNEK} tane daha"


# --- okul ayarı değişikliği ---------------------------------------------------------------------

def okul_ayari_etkisi(oturum: Session, gun_sayisi: int, gunluk_ders_saati: int, uygula: bool) -> list[str]:
    """Gün ya da günlük ders saati azalırsa:

    - aralığın dışında kalan **müsaitlik kayıtları silinir** (artık var olmayan bir saat için
      "gelemez" anlamsızdır; bırakılsaydı sonraki program üretimi ön kontrolde hata verirdi);
    - **programlar değişmez**: eski ayarlarla üretilmiş birer kayıttır. Kullanıcıya hangi
      programların aralık dışında ders saati içerdiği ve yeniden üretilmesi gerektiği söylenir.
    """
    etkiler: list[str] = []
    disarida = or_(Musaitlik.gun >= gun_sayisi, Musaitlik.saat >= gunluk_ders_saati)
    musaitlikler = oturum.execute(
        select(Musaitlik.id, Ogretmen.ad, Musaitlik.gun, Musaitlik.saat)
        .join(Ogretmen, Ogretmen.id == Musaitlik.ogretmen_id)
        .where(disarida)
        .order_by(Ogretmen.ad, Musaitlik.gun, Musaitlik.saat)
    ).all()
    if musaitlikler:
        ornek = musaitlikler[0]
        ogretmenler = {m.ad for m in musaitlikler}
        etkiler.append(
            f"{len(musaitlikler)} müsaitlik kaydı yeni ayarların dışında kalıyor ve silinecek "
            f"({len(ogretmenler)} öğretmen; ör. {ornek.ad}, {GUNLER[ornek.gun]} {ornek.saat + 1}. saat)."
        )
        if uygula:
            oturum.execute(delete(Musaitlik).where(Musaitlik.id.in_([m.id for m in musaitlikler])))

    hucre_disarida = or_(Yerlesim.gun >= gun_sayisi, Yerlesim.saat >= gunluk_ders_saati)
    programlar = oturum.execute(
        select(Program.ad, func.count(Yerlesim.id))
        .join(Yerlesim, Yerlesim.program_id == Program.id)
        .where(hucre_disarida)
        .group_by(Program.id, Program.ad)
    ).all()
    if programlar:
        hucre = sum(p[1] for p in programlar)
        etkiler.append(
            f"{len(programlar)} programda ({_liste([p.ad for p in programlar])}) yeni ayarların dışında "
            f"kalan {hucre} ders saati var. Programlar silinmez, eski ayarlarla üretilmiş olarak "
            "kalır; yeni ayarlarla programı yeniden üretmeniz gerekir."
        )
    return etkiler


# --- silinemeyen kayıtlar -----------------------------------------------------------------------

def _atama_adlari(oturum: Session, kosul) -> list[str]:
    satirlar = oturum.execute(
        select(Sinif.ad, Ders.ad)
        .select_from(DersAtama)
        .join(Sinif, Sinif.id == DersAtama.sinif_id)
        .join(Ders, Ders.id == DersAtama.ders_id)
        .where(kosul)
    ).all()
    return [f"{s} {d}" for s, d in satirlar]


def kullanim_aciklamasi(oturum: Session, tablo: str, kayit_id: uuid.UUID) -> list[str]:
    if tablo == "ogretmen":
        atamalar = _atama_adlari(oturum, DersAtama.ogretmen_id == kayit_id)
        if atamalar:
            return [
                f"{len(atamalar)} derste öğretmen olarak seçili ({_liste(atamalar)}). Önce Ders "
                "dağılımı sayfasında bu derslere başka bir öğretmen seçin."
            ]
    if tablo == "sinif":
        atamalar = _atama_adlari(oturum, DersAtama.sinif_id == kayit_id)
        if atamalar:
            return [
                f"bu sınıfa {len(atamalar)} ders atanmış ({_liste(atamalar)}). Önce Ders dağılımı "
                "sayfasında bu sınıfın derslerini kaldırın."
            ]
    if tablo == "ders":
        metinler = []
        atamalar = _atama_adlari(oturum, DersAtama.ders_id == kayit_id)
        if atamalar:
            metinler.append(f"{len(atamalar)} sınıfa atanmış ({_liste(atamalar)}).")
        seviyeler = oturum.scalars(
            select(SeviyeSablonu.seviye).where(SeviyeSablonu.ders_id == kayit_id).order_by(SeviyeSablonu.seviye)
        ).all()
        if seviyeler:
            metinler.append(f"{', '.join(f'{s}. sınıf' for s in seviyeler)} seviye şablonunda var.")
        if metinler:
            metinler.append("Önce Ders dağılımı ve Seviye şablonu sayfalarında bu dersi kaldırın.")
        return metinler
    return []
