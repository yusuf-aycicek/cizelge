"""Çıktı modelinin JSON'u: yayının dondurulmuş içeriği (8b, ADR 0022).

Yayınlanan program `ProgramCiktisi`'nin kendisidir; böylece paylaşım sayfası ve onun PDF'i
yayının içeriğinden, yönetici çıktısıyla aynı kodla (`pdf.py`) üretilir. JSON yalnızca düz
değerler taşır (ad, renk, gün, saat); veritabanındaki hiçbir kayda bağlı değildir.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import date
from typing import Any

from okulapi.cekirdek.zil import Zil
from okulapi.moduller.ders_programi.cikti.model import Cizelge, Hafta, Hucre, ProgramCiktisi

SURUM = 1  # içerik biçimi değişirse eski yayınlar okunabilsin diye


def _cizelge(c: Cizelge) -> dict[str, Any]:
    return {"ad": c.ad, "tur": c.tur, "kimlik": str(c.kimlik) if c.kimlik else None,
            "hucreler": [asdict(h) for h in c.hucreler]}


def jsona(cikti: ProgramCiktisi) -> dict[str, Any]:
    h = cikti.hafta
    return {
        "surum": SURUM,
        "okul": cikti.okul,
        "program": cikti.program,
        "tarih": cikti.tarih.isoformat(),
        "hafta": {"gun_adlari": h.gun_adlari, "gun_saatleri": h.gun_saatleri, "saat_sayisi": h.saat_sayisi,
                  "ogle_arasi_sonra": h.ogle_arasi_sonra, "zil": [asdict(z) for z in h.zil] if h.zil else None,
                  "ogle_zili": asdict(h.ogle_zili) if h.ogle_zili else None},
        "subeler": [_cizelge(c) for c in cikti.subeler],
        "ogretmenler": [_cizelge(c) for c in cikti.ogretmenler],
    }


def _cizelgeden(d: dict[str, Any]) -> Cizelge:
    return Cizelge(ad=d["ad"], tur=d["tur"], kimlik=uuid.UUID(d["kimlik"]) if d.get("kimlik") else None,
                   hucreler=[Hucre(**h) for h in d["hucreler"]])


def jsondan(d: dict[str, Any]) -> ProgramCiktisi:
    h = d["hafta"]
    return ProgramCiktisi(
        okul=d["okul"], program=d["program"], tarih=date.fromisoformat(d["tarih"]),
        hafta=Hafta(gun_adlari=h["gun_adlari"], gun_saatleri=h["gun_saatleri"], saat_sayisi=h["saat_sayisi"],
                    ogle_arasi_sonra=h["ogle_arasi_sonra"], zil=[Zil(**z) for z in h["zil"]] if h["zil"] else None,
                    ogle_zili=Zil(**h["ogle_zili"]) if h["ogle_zili"] else None),
        subeler=[_cizelgeden(c) for c in d.get("subeler", [])],
        ogretmenler=[_cizelgeden(c) for c in d.get("ogretmenler", [])],
    )


def hucre_imzasi(d: dict[str, Any]) -> list:
    """İki içeriğin programca aynı olup olmadığını karşılaştırmak için (tarih ve zil hariç)."""
    return [[c["kimlik"], c["ad"], c["hucreler"]] for c in d["subeler"] + d["ogretmenler"]]
