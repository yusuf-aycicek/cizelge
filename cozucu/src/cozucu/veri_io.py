"""CozumGirdisi / CozumSonucu ile JSON arasında dönüşüm.

Veri setleri (/veri) ve komut satırı bu formatı kullanır. Worker ise girdiyi doğrudan
veritabanından kurar; bu modül ona gerekli değildir.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cozucu.model import (
    Celiski,
    CozumDurumu,
    CozumGirdisi,
    CozumSonucu,
    Ders,
    DersAtama,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Ogretmen,
    Sinif,
    Yerlesim,
)


def girdi_to_dict(girdi: CozumGirdisi) -> dict[str, Any]:
    return json.loads(json.dumps(asdict(girdi), default=_enum_degeri))


def girdi_from_dict(veri: dict[str, Any]) -> CozumGirdisi:
    return CozumGirdisi(
        ayar=OkulAyari(**veri["ayar"]),
        ogretmenler=[Ogretmen(**o) for o in veri.get("ogretmenler", [])],
        siniflar=[Sinif(**s) for s in veri.get("siniflar", [])],
        dersler=[Ders(**d) for d in veri.get("dersler", [])],
        atamalar=[DersAtama(**a) for a in veri.get("atamalar", [])],
        musaitlikler=[
            Musaitlik(**{**m, "durum": MusaitlikDurumu(m["durum"])})
            for m in veri.get("musaitlikler", [])
        ],
        kisitlar=[KisitTanimi(**k) for k in veri.get("kisitlar", [])],
        kilitli_yerlesimler=[Yerlesim(**y) for y in veri.get("kilitli_yerlesimler", [])],
    )


def sonuc_to_dict(sonuc: CozumSonucu) -> dict[str, Any]:
    return json.loads(json.dumps(asdict(sonuc), default=_enum_degeri))


def sonuc_from_dict(veri: dict[str, Any]) -> CozumSonucu:
    return CozumSonucu(
        durum=CozumDurumu(veri["durum"]),
        yerlesimler=[Yerlesim(**y) for y in veri.get("yerlesimler", [])],
        toplam_ceza=veri.get("toplam_ceza"),
        mesajlar=list(veri.get("mesajlar", [])),
        sure_sn=veri.get("sure_sn", 0.0),
        celiskiler=[
            Celiski(tur=c["tur"], mesaj=c["mesaj"], ilgili=tuple(c.get("ilgili", ())))
            for c in veri.get("celiskiler", [])
        ],
    )


def girdi_oku(yol: str | Path) -> CozumGirdisi:
    return girdi_from_dict(json.loads(Path(yol).read_text(encoding="utf-8")))


def girdi_yaz(girdi: CozumGirdisi, yol: str | Path) -> None:
    metin = json.dumps(girdi_to_dict(girdi), ensure_ascii=False, indent=1)
    Path(yol).write_text(metin + "\n", encoding="utf-8")


def _enum_degeri(nesne: Any) -> Any:
    if isinstance(nesne, MusaitlikDurumu | CozumDurumu):
        return nesne.value
    raise TypeError(f"JSON'a çevrilemiyor: {nesne!r}")
