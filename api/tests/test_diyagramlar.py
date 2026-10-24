"""Diyagram-kod tutarlılığı: docs/diyagramlar/*.puml içindeki adlar kodda gerçekten var mı?

Denetlenenler:
- Sınıf diyagramları: "' @kod <python.modulu>" satırından sonraki paket bloğundaki her sınıf o
  modülde vardır; her üye (alan, metot, enum değeri) sınıfta vardır; metotlarda yazılan parametre
  adları gerçek imzada vardır. <<modül>> sınıfı Python modülünün kendisidir (üyeleri modülün
  fonksiyon ve değişkenleri). <<harici>> sınıflar (SQLAlchemy, OR-Tools, FastAPI) denetlenmez.
- Genel bakış: "' @paket <python.paketi>" ile işaretli paketler içe aktarılabilir.
- Nesne diyagramları: her nesnenin sınıfı bir sınıf diyagramında vardır; nesnenin her alanı hem
  koddaki sınıfta hem de sınıf diyagramında (o sınıfın ya da diyagramdaki bir atasının üyesi
  olarak) vardır.

Veritabanı gerekmez. Ayrıştırıcı yalnızca bu projedeki diyagramların kullandığı PlantUML
alt kümesini anlar; bir şey bulamazsa sessizce geçmesin diye sayılar da denetlenir.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import pytest

DIZIN = Path(__file__).resolve().parents[2] / "docs" / "diyagramlar"

SINIF_SATIRI = re.compile(
    r'^\s*(?:abstract\s+class|abstract|class|interface|enum)\s+'
    r'(?:"[^"]+"\s+as\s+(?P<takma>\w+)|(?P<ad>\w+))'
    r'(?:\s*<<(?P<stereotip>[^>]+)>>)?[^{]*(?P<ac>\{)?\s*$'
)
NESNE_SATIRI = re.compile(r'^\s*object\s+"\s*\w+\s*:\s*(?P<sinif>\w+)\s*"\s+as\s+\w+\s*(?P<ac>\{)?\s*$')
PAKET_SATIRI = re.compile(r"^\s*package\b.*\{\s*(\})?\s*$")
UYE_ADI = re.compile(r"^(?:\{(?:static|abstract)\}\s*)*[+\-#~]?\s*(?P<ad>\w+)\s*(?P<parantez>\()?")


@dataclass
class DiyagramSinifi:
    ad: str
    modul: str | None
    stereotip: str | None
    uyeler: list[str] = field(default_factory=list)
    dosya: str = ""


@dataclass
class DiyagramNesnesi:
    sinif: str
    alanlar: list[str]
    dosya: str


@dataclass
class Ayristirma:
    siniflar: list[DiyagramSinifi] = field(default_factory=list)
    nesneler: list[DiyagramNesnesi] = field(default_factory=list)
    paketler: list[str] = field(default_factory=list)


def ayristir(metin: str, dosya: str = "") -> Ayristirma:
    sonuc = Ayristirma()
    bekleyen_kod: str | None = None
    paket_yigini: list[str | None] = []  # her açık paket bloğunun @kod modülü
    govde: DiyagramSinifi | DiyagramNesnesi | None = None
    not_icinde = False

    for ham in metin.splitlines():
        satir = ham.strip()
        if not_icinde:
            not_icinde = not (satir.startswith("end note") or satir.startswith("endlegend"))
            continue
        if govde is not None:
            if satir == "}":
                govde = None
            elif satir and not satir.startswith("'"):
                if isinstance(govde, DiyagramNesnesi):
                    govde.alanlar.append(satir.split("=", 1)[0].strip())
                else:
                    govde.uyeler.append(satir)
            continue
        if satir.startswith("' @kod "):
            bekleyen_kod = satir.removeprefix("' @kod ").strip()
            continue
        if satir.startswith("' @paket "):
            sonuc.paketler.append(satir.removeprefix("' @paket ").strip())
            continue
        if satir.startswith("'") or not satir:
            continue
        if re.match(r"^(note|legend)\b", satir) and not re.match(r"^note\b.*:", satir):
            not_icinde = True
            continue
        if m := PAKET_SATIRI.match(satir):
            if not m.group(1):  # "{ }" aynı satırda kapanmıyorsa
                paket_yigini.append(bekleyen_kod)
            bekleyen_kod = None
            continue
        if satir == "}":
            if paket_yigini:
                paket_yigini.pop()
            continue
        if m := SINIF_SATIRI.match(satir):
            modul = next((k for k in reversed(paket_yigini) if k), None)
            sinif = DiyagramSinifi(m["takma"] or m["ad"], modul, m["stereotip"], dosya=dosya)
            sonuc.siniflar.append(sinif)
            if m["ac"]:
                govde = sinif
            continue
        if m := NESNE_SATIRI.match(satir):
            nesne = DiyagramNesnesi(m["sinif"], [], dosya)
            sonuc.nesneler.append(nesne)
            if m["ac"]:
                govde = nesne
    return sonuc


def _ust_duzey_bol(metin: str) -> list[str]:
    """'a : dict[str, int], b' -> ['a : dict[str, int]', 'b'] (köşeli/normal parantez içini bölmez)."""
    parcalar, derinlik, simdiki = [], 0, ""
    for c in metin:
        if c in "([":
            derinlik += 1
        elif c in ")]":
            derinlik -= 1
        if c == "," and derinlik == 0:
            parcalar.append(simdiki)
            simdiki = ""
        else:
            simdiki += c
    if simdiki.strip():
        parcalar.append(simdiki)
    return [p.strip() for p in parcalar]


def _parametreler(uye: str) -> list[str]:
    ic = uye[uye.index("(") + 1 : uye.rindex(")")]
    adlar = []
    for parca in _ust_duzey_bol(ic):
        ad = re.split(r"[\s:=]", parca.lstrip("*"), maxsplit=1)[0]
        if ad and ad != "...":
            adlar.append(ad)
    return adlar


def _ornek_niteligi_var_mi(sinif: type, ad: str) -> bool:
    """__init__ içinde atanan nitelik (self.ad = ...) ya da sınıf düzeyi tip bildirimi."""
    for ata in inspect.getmro(sinif):
        if ad in getattr(ata, "__annotations__", {}):
            return True
        if ata.__module__ == "builtins":
            continue
        try:
            kaynak = inspect.getsource(ata)
        except (OSError, TypeError):
            continue
        if ad in _self_atamalari(kaynak):
            return True
    return False


def _self_atamalari(kaynak: str) -> set[str]:
    """`self.x = ...`, `self.x: T = ...` ve `self.x, self.y = ...` ile atanan nitelik adları."""
    adlar = set()
    for dugum in ast.walk(ast.parse(textwrap.dedent(kaynak))):
        if isinstance(dugum, ast.Assign):
            hedefler = dugum.targets
        elif isinstance(dugum, ast.AnnAssign):
            hedefler = [dugum.target]
        else:
            continue
        for hedef in hedefler:
            for h in hedef.elts if isinstance(hedef, ast.Tuple) else [hedef]:
                if isinstance(h, ast.Attribute) and isinstance(h.value, ast.Name) and h.value.id == "self":
                    adlar.add(h.attr)
    return adlar


def uye_hatalari(sinif: DiyagramSinifi) -> list[str]:
    yer = f"{sinif.dosya}: {sinif.ad}"
    if not sinif.modul:
        return [f"{yer}: '@kod' işareti yok, hangi modülde aranacağı bilinmiyor"]
    try:
        modul = importlib.import_module(sinif.modul)
    except ImportError as e:
        return [f"{yer}: modül içe aktarılamadı: {sinif.modul} ({e})"]
    if sinif.stereotip == "modül":
        if modul.__name__.rsplit(".", 1)[-1] != sinif.ad:
            return [f"{yer}: <<modül>> sınıfının adı modülün adı olmalı ({sinif.modul})"]
        hedef = modul
    else:
        hedef = getattr(modul, sinif.ad, None)
        if not isinstance(hedef, type):
            return [f"{yer}: {sinif.modul} içinde böyle bir sınıf yok"]

    hatalar = []
    enum_mu = hasattr(hedef, "__members__")
    for uye in sinif.uyeler:
        m = UYE_ADI.match(uye)
        if not m:
            hatalar.append(f"{yer}: üye ayrıştırılamadı: {uye!r}")
            continue
        ad = m["ad"]
        if enum_mu:
            var = ad in hedef.__members__
        elif inspect.ismodule(hedef):
            var = hasattr(hedef, ad)
        else:
            var = (
                # Önce sınıf sözlükleri: eşlenmemiş mixin'de hasattr SQLAlchemy uyarısı verir.
                any(ad in vars(ata) for ata in inspect.getmro(hedef))
                or hasattr(hedef, ad)
                or (dataclasses.is_dataclass(hedef) and ad in {f.name for f in dataclasses.fields(hedef)})
                or _ornek_niteligi_var_mi(hedef, ad)
            )
        if not var:
            hatalar.append(f"{yer}.{ad}: kodda yok")
            continue
        if m["parantez"]:
            fonksiyon = getattr(hedef, ad)
            try:
                imza = inspect.signature(fonksiyon)
            except (TypeError, ValueError):
                continue
            for p in _parametreler(uye):
                if p not in imza.parameters:
                    hatalar.append(f"{yer}.{ad}({p}): parametre gerçek imzada yok {imza}")
    return hatalar


def _tum_diyagramlar() -> dict[str, Ayristirma]:
    return {
        yol.name: ayristir(yol.read_text(encoding="utf-8"), yol.name)
        for yol in sorted(DIZIN.glob("*.puml"))
    }


DIYAGRAMLAR = _tum_diyagramlar()
SINIFLAR = [s for a in DIYAGRAMLAR.values() for s in a.siniflar if s.stereotip != "harici"]
NESNELER = [n for a in DIYAGRAMLAR.values() for n in a.nesneler]
PAKETLER = [p for a in DIYAGRAMLAR.values() for p in a.paketler]


def test_ayristirici_diyagramlarda_yeterince_sey_buldu():
    # Ayrıştırıcı bozulursa testler boş listeyle "geçmesin".
    assert len(DIYAGRAMLAR) >= 9
    assert len(SINIFLAR) >= 60
    assert sum(len(s.uyeler) for s in SINIFLAR) >= 150
    assert len(NESNELER) >= 15
    assert len(PAKETLER) >= 5


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: f"{s.dosya}:{s.ad}")
def test_siniflar_ve_uyeleri_kodda_var(sinif):
    assert uye_hatalari(sinif) == []


@pytest.mark.parametrize("paket", PAKETLER)
def test_genel_bakistaki_paketler_var(paket):
    importlib.import_module(paket)


def _diyagram_siniflari_adla() -> dict[str, DiyagramSinifi]:
    # Aynı sınıf birden çok diyagramda görünebilir (ör. Okul 02'de ayrıntılı, 04'te yalnızca adla);
    # üyeleri birleştirilir.
    sonuc: dict[str, DiyagramSinifi] = {}
    for s in SINIFLAR:
        if s.stereotip == "modül":
            continue
        if s.ad in sonuc:
            sonuc[s.ad].uyeler += s.uyeler
        else:
            sonuc[s.ad] = DiyagramSinifi(s.ad, s.modul, s.stereotip, list(s.uyeler), s.dosya)
    return sonuc


@pytest.mark.parametrize("nesne", NESNELER, ids=lambda n: f"{n.dosya}:{n.sinif}")
def test_nesneler_sinif_diyagramiyla_ve_kodla_tutarli(nesne):
    siniflar = _diyagram_siniflari_adla()
    assert nesne.sinif in siniflar, f"{nesne.sinif} hiçbir sınıf diyagramında yok"
    ds = siniflar[nesne.sinif]
    kod_sinifi = getattr(importlib.import_module(ds.modul), nesne.sinif)
    # Diyagramda gösterilen alanlar: sınıfın kendisi ve diyagramda bulunan atalarının üyeleri
    # (ör. id ve okul_id OkulaAitMixin'den gelir).
    diyagram_alanlari = set()
    for ata in inspect.getmro(kod_sinifi):
        if ata.__name__ in siniflar:
            diyagram_alanlari |= {UYE_ADI.match(u)["ad"] for u in siniflar[ata.__name__].uyeler}
    # Varsayılanı olmayan dataclass alanı sınıf niteliği değildir (ör. KaliteOlcumu.sinif_boslugu).
    dataclass_alanlari = {f.name for f in dataclasses.fields(kod_sinifi)} if dataclasses.is_dataclass(kod_sinifi) else set()
    for alan in nesne.alanlar:
        assert hasattr(kod_sinifi, alan) or alan in dataclass_alanlari, f"{nesne.sinif}.{alan}: kodda yok"
        assert alan in diyagram_alanlari, f"{nesne.sinif}.{alan}: sınıf diyagramında yok"


def test_denetleyici_yanlis_adlari_yakalar():
    # Denetleyicinin kendisi: kodda olmayan sınıf, üye ve parametre yakalanır.
    metin = """
' @kod okulapi.cekirdek.depo
package "depo" {
  class OkulaAitDepo {
    +listele() : list
    +yok_boyle_metot()
    +getir(kayit_id : UUID, uydurma : int)
  }
  class UydurmaDepo
}
"""
    siniflar = ayristir(metin, "deneme").siniflar
    hatalar = [h for s in siniflar for h in uye_hatalari(s)]
    assert any("yok_boyle_metot" in h for h in hatalar)
    assert any("(uydurma)" in h for h in hatalar)
    assert any("UydurmaDepo" in h for h in hatalar)
    assert not any("listele" in h for h in hatalar)
