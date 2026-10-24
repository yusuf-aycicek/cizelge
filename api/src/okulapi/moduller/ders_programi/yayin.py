"""Yayın (8b, ADR 0022): okulun yayınlanan programı.

Yayınlamak programın o anki çıktısını (`program_ciktisi`) dondurur ve `yayin` satırına yazar.
Yayından sonra veri ya da program değişirse yayın kendiliğinden değişmez; yöneticiye neden güncel
olmadığı söylenir ve yeniden yayınlaması önerilir.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from okulapi.cekirdek.servisler import KayitBulunamadi
from okulapi.moduller.ders_programi.cikti import anlik
from okulapi.moduller.ders_programi.cikti.veri import program_ciktisi
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.depo import ProgramDeposu
from okulapi.moduller.ders_programi.modeller import Yayin
from okulapi.moduller.ders_programi.uretim import veri_ozeti


class YayinServisi:
    def __init__(self, oturum) -> None:
        self.oturum = oturum

    def _yayin(self, kilitle: bool = False) -> Yayin | None:
        sorgu = select(Yayin)
        return self.oturum.scalars(sorgu.with_for_update() if kilitle else sorgu).first()

    def yayinla(self, program_id: uuid.UUID) -> dict[str, Any]:
        """404: program bu okulda yok. 409: program hazır değil."""
        cikti = program_ciktisi(self.oturum, program_id)
        program = ProgramDeposu(self.oturum).getir(program_id)
        yayin = self._yayin(kilitle=True) or Yayin()
        yayin.program_id = program.id
        yayin.program_adi = program.ad
        yayin.yayin_zamani = datetime.now(timezone.utc)
        yayin.icerik = anlik.jsona(cikti)
        yayin.veri_ozeti = program.veri_ozeti
        self.oturum.add(yayin)
        self.oturum.commit()
        return self.durum()

    def kaldir(self) -> None:
        """Yayını kaldırır; paylaşım linkleri kalır ama "yayında program yok" gösterir."""
        yayin = self._yayin(kilitle=True)
        if yayin is None:
            raise KayitBulunamadi("Yayın")
        self.oturum.delete(yayin)
        self.oturum.commit()

    def durum(self) -> dict[str, Any] | None:
        """Yayın ve güncel olmama nedenleri (`uyarilar`, kullanıcının diliyle)."""
        yayin = self._yayin()
        if yayin is None:
            return None
        uyarilar = []
        eski_veri = None
        if yayin.veri_ozeti is not None:
            eski_veri = yayin.veri_ozeti != veri_ozeti(cozum_girdisi_olustur(self.oturum))
            if eski_veri:
                uyarilar.append("Yayınlanan program eski verilerle üretildi: öğretmen, ders, dağılım ya da kurallar "
                                "yayından sonra değişti. Programı yeniden üretip yayınlayabilirsiniz.")
        program_degisti = False
        program = ProgramDeposu(self.oturum).getir(yayin.program_id) if yayin.program_id else None
        if program is None:
            uyarilar.append("Yayınlanan programın kendisi silindi; paylaşılan içerik yayın anındaki gibi kalıyor.")
        elif program.durum == "hazir":
            simdiki = anlik.jsona(program_ciktisi(self.oturum, program.id))
            program_degisti = anlik.hucre_imzasi(simdiki) != anlik.hucre_imzasi(yayin.icerik)
            if program_degisti:
                uyarilar.append("Programda yayından sonra değişiklik var (elle düzeltme ya da ad değişikliği); "
                                "paylaşılan sayfalarda görünmesi için yeniden yayınlayın.")
        return {
            "program_id": yayin.program_id,
            "program_adi": yayin.program_adi,
            "yayin_zamani": yayin.yayin_zamani,
            "eski_veri": eski_veri,
            "program_degisti": program_degisti,
            "uyarilar": uyarilar,
        }

    def icerik(self):
        """Yayının çıktı modeli (yönetici önizlemesi ve PDF için). 404: yayın yok."""
        yayin = self._yayin()
        if yayin is None:
            raise KayitBulunamadi("Yayın")
        return anlik.jsondan(yayin.icerik)
