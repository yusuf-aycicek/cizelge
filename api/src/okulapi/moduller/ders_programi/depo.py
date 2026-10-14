"""Ders programı depoları. Çekirdeğin `OkulaAitDepo`'sunu kullanır; okul filtresi otomatiktir."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from okulapi.cekirdek.depo import OkulaAitDepo
from okulapi.moduller.ders_programi.modeller import DersAtama, Kisit, Musaitlik, Program, SeviyeSablonu, Yerlesim


class SeviyeSablonuDeposu(OkulaAitDepo[SeviyeSablonu]):
    model = SeviyeSablonu

    def seviyenin(self, seviye: int) -> list[SeviyeSablonu]:
        return list(self.oturum.scalars(select(SeviyeSablonu).where(SeviyeSablonu.seviye == seviye)))


class DersAtamaDeposu(OkulaAitDepo[DersAtama]):
    model = DersAtama

    def siniflarin(self, sinif_idler: list[uuid.UUID]) -> list[DersAtama]:
        return list(self.oturum.scalars(select(DersAtama).where(DersAtama.sinif_id.in_(sinif_idler))))


class MusaitlikDeposu(OkulaAitDepo[Musaitlik]):
    model = Musaitlik


class KisitDeposu(OkulaAitDepo[Kisit]):
    model = Kisit


class ProgramDeposu(OkulaAitDepo[Program]):
    model = Program


class YerlesimDeposu(OkulaAitDepo[Yerlesim]):
    model = Yerlesim

    def programin(self, program_id: uuid.UUID, yalnizca_kilitli: bool = False) -> list[Yerlesim]:
        sorgu = select(Yerlesim).where(Yerlesim.program_id == program_id)
        if yalnizca_kilitli:
            sorgu = sorgu.where(Yerlesim.kilitli.is_(True))
        return list(self.oturum.scalars(sorgu.order_by(Yerlesim.gun, Yerlesim.saat)))
