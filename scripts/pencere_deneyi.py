"""Öğretmen penceresi formülasyonu deneyi: mevcut formül, varyant A ve varyant B.

Arka plan (docs/cozucu-plani.md, 6. alt adım): mevcut formülde `okulda >= once + sonra - 1`
kısıtı kesirli çözümlerde `okulda - dolu` ceza terimini negatife düşürebiliyor. CP-SAT'ın alt
sınırı bu yüzden -2229 çıktı. Varyantlar:
- A: mevcut formül + geçerli eşitsizlik `okulda >= dolu`.
- B: yardımcılar tam tanımlı: `mesgul == dolu`, `once`/`sonra` = max, `okulda` = min.
- C: ceza terimleri ayrı 0/1 değişken (pencere ve sınıf boşluğu), bkz. scripts/amac_teshisi.py.

Varyantlar asıl kodu değiştirmeden, kayıt defterindeki `ogretmen_penceresi` sınıfı değiştirilerek
denenir.

Sonuçlar ilerledikçe yazılır, böylece deney yarıda kalsa da kaybolmaz:
- `<cikti>/pencere_ham.csv`: her iyileşen çözüm bir satır (varyant, tohum, saniye, amaç, alt sınır).
- `<cikti>/pencere_varyantlari.md`: her (varyant, tohum) çalıştırması bitince güncellenen özet.

Kullanım (cozucu sanal ortamıyla, depo kökünden):
    cozucu/.venv/Scripts/python.exe scripts/pencere_deneyi.py veri/gercekci.json \
        --varyant mevcut A B --tohum 0 1 2 --sure 60 --cikti scripts/sonuclar
Ölçüm sırasında makinede işlemci kullanan başka bir iş çalıştırılmamalıdır.
"""

from __future__ import annotations

import argparse
import csv
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import ortools
from ortools.sat.python import cp_model

from cozucu.cpsat import _yerlesimler
from cozucu.dogrulama import dogrula
from cozucu.kalite import agirlikli_ceza, olc
from cozucu.kisitlar import KAYIT_DEFTERI, Baglam, etkin_agirliklar, kurallari_hazirla
from cozucu.kisitlar.esnek import OgretmenPenceresi, SinifBoslugu, _kumulatif
from cozucu.veri_io import girdi_oku

NOKTALAR = (10.0, 30.0, 60.0)


class PencereA(OgretmenPenceresi):
    """Mevcut formül + geçerli eşitsizlik okulda >= dolu (her tamsayı çözümde zaten doğru)."""

    def uygula(self, baglam):
        cezalar = []
        saatler = list(baglam.saatler)
        for atamalar in baglam.ogretmen_atamalari.values():
            for g in baglam.gunler:
                dolu = [baglam.dolu(atamalar, g, s) for s in saatler]
                once = _kumulatif(baglam, dolu)
                sonra = _kumulatif(baglam, dolu[::-1])[::-1]
                for s in saatler:
                    okulda = baglam.model.new_bool_var("")
                    baglam.model.add(okulda >= once[s] + sonra[s] - 1)
                    baglam.model.add(okulda >= dolu[s])
                    cezalar.append((okulda - dolu[s], self.agirlik))
        return cezalar


class PencereB(OgretmenPenceresi):
    """Tam tanım: mesgul == dolu, once/sonra = max(...), okulda = min(once, sonra)."""

    def uygula(self, baglam):
        m = baglam.model
        cezalar = []
        saatler = list(baglam.saatler)
        for atamalar in baglam.ogretmen_atamalari.values():
            for g in baglam.gunler:
                mesgul = []
                for s in saatler:
                    v = m.new_bool_var("")
                    m.add(v == baglam.dolu(atamalar, g, s))
                    mesgul.append(v)
                once: list = []
                for s in saatler:
                    v = m.new_bool_var("")
                    m.add_max_equality(v, [mesgul[s]] + ([once[s - 1]] if s else []))
                    once.append(v)
                sonra: list = [None] * len(saatler)
                for s in reversed(saatler):
                    v = m.new_bool_var("")
                    m.add_max_equality(v, [mesgul[s]] + ([sonra[s + 1]] if s + 1 < len(saatler) else []))
                    sonra[s] = v
                for s in saatler:
                    okulda = m.new_bool_var("")
                    m.add_min_equality(okulda, [once[s], sonra[s]])
                    cezalar.append((okulda - mesgul[s], self.agirlik))
        return cezalar


class PencereC(OgretmenPenceresi):
    """Mevcut formül; ceza `okulda - dolu` yerine ayrı bir 0/1 değişken: bosluk >= okulda - dolu.

    Amaçta ders değişkenleri negatif katsayıyla yer almaz (amac_teshisi.py), alan sınırı 0 olur.
    """

    def uygula(self, baglam):
        cezalar = []
        saatler = list(baglam.saatler)
        for atamalar in baglam.ogretmen_atamalari.values():
            for g in baglam.gunler:
                dolu = [baglam.dolu(atamalar, g, s) for s in saatler]
                once = _kumulatif(baglam, dolu)
                sonra = _kumulatif(baglam, dolu[::-1])[::-1]
                for s in saatler:
                    okulda = baglam.model.new_bool_var("")
                    baglam.model.add(okulda >= once[s] + sonra[s] - 1)
                    bosluk = baglam.model.new_bool_var("")
                    baglam.model.add(bosluk >= okulda - dolu[s])
                    cezalar.append((bosluk, self.agirlik))
        return cezalar


class SinifBosluguC(SinifBoslugu):
    """Aynı düzeltme sınıf boşluğu için: bosluk >= sonra - dolu."""

    def uygula(self, baglam):
        cezalar = []
        saatler = list(baglam.saatler)
        for atamalar in baglam.sinif_atamalari.values():
            for g in baglam.gunler:
                dolu = [baglam.dolu(atamalar, g, s) for s in saatler]
                sonra = _kumulatif(baglam, dolu[::-1])[::-1]
                for s in saatler:
                    bosluk = baglam.model.new_bool_var("")
                    baglam.model.add(bosluk >= sonra[s] - dolu[s])
                    cezalar.append((bosluk, self.agirlik))
        return cezalar


# varyant -> {kural türü: sınıf}. Listede olmayan türler asıl sınıfla kalır.
VARYANTLAR = {
    "mevcut": {},
    "A": {"ogretmen_penceresi": PencereA},
    "B": {"ogretmen_penceresi": PencereB},
    "C": {"ogretmen_penceresi": PencereC, "sinif_boslugu": SinifBosluguC},
}


def model_kur(girdi, varyant):
    asil = dict(KAYIT_DEFTERI)
    KAYIT_DEFTERI.update(VARYANTLAR[varyant])
    try:
        b = Baglam.kur(girdi)
        cezalar = []
        for kural in kurallari_hazirla(girdi):
            cezalar.extend(kural.uygula(b))
    finally:
        KAYIT_DEFTERI.update(asil)
    b.model.minimize(sum(a * i for i, a in cezalar))
    return b


class _Kaydedici(cp_model.CpSolverSolutionCallback):
    """Her iyileşen çözümü belleğe alır ve ham CSV'ye hemen yazar."""

    def __init__(self, b, yazici, dosya, etiket):
        super().__init__()
        self.b, self.yazici, self.dosya, self.etiket = b, yazici, dosya, etiket
        self.kayitlar = []

    def on_solution_callback(self):
        t, amac, alt = self.wall_time, self.objective_value, self.best_objective_bound
        self.kayitlar.append((t, amac, alt, _yerlesimler(self.b, self.boolean_value)))
        self.yazici.writerow([*self.etiket, f"{t:.2f}", f"{amac:.0f}", f"{alt:.0f}"])
        self.dosya.flush()


def calistir(girdi, varyant, tohum, sure, yazici, dosya):
    b = model_kur(girdi, varyant)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = sure
    solver.parameters.num_workers = 8  # CpSatCozucu'nun varsayılanı
    solver.parameters.random_seed = tohum
    alt_sinirlar = []  # (saniye, alt sınır): çözüm bulunmasa da sınır ilerledikçe kaydedilir
    baslangic = time.perf_counter()
    solver.best_bound_callback = lambda sinir: alt_sinirlar.append((time.perf_counter() - baslangic, sinir))
    kaydedici = _Kaydedici(b, yazici, dosya, (varyant, tohum))
    solver.solve(b.model, kaydedici)
    agirliklar = etkin_agirliklar(girdi)
    satirlar = []
    for n in NOKTALAR:
        sinir = max([s for t, s in alt_sinirlar if t <= n], default=None)
        onceki = [k for k in kaydedici.kayitlar if k[0] <= n]
        if not onceki:
            satirlar.append((varyant, tohum, n, None, None, sinir, None))
            continue
        _t, amac, _alt, y = onceki[-1]
        hatalar = dogrula(girdi, y)
        if hatalar:
            raise AssertionError(f"{varyant} tohum {tohum}: geçersiz program: {hatalar[0]}")
        o = olc(girdi, y)
        satirlar.append((varyant, tohum, n, agirlikli_ceza(o, agirliklar), round(amac), sinir, o))
    ilk = kaydedici.kayitlar[0][0] if kaydedici.kayitlar else None
    return satirlar, ilk, solver.best_objective_bound


def mini_dogrulama(varyant, mini_yolu):
    """Varyant programı doğru ölçüyor mu? Mini sette en iyi çözümde amaç == bağımsız ölçüm."""
    girdi = girdi_oku(mini_yolu)
    b = model_kur(girdi, varyant)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_workers = 8
    durum = solver.solve(b.model)
    y = _yerlesimler(b, solver.boolean_value)
    gercek = agirlikli_ceza(olc(girdi, y), etkin_agirliklar(girdi))
    return solver.status_name(durum), round(solver.objective_value), gercek, dogrula(girdi, y) == []


def ozet_yaz(yol, baslik, satirlar, ilkler, son_sinirlar):
    s = [baslik, "", "| Varyant | Tohum | Saniye | Gerçek ceza | Model ceza | Alt sınır | Sınıf boşluğu | "
         "Pencere | Bölünmüş | Tercih etmez | Eksik boş gün |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v, t, n, gercek, model, sinir, o in satirlar:
        sinir_metni = "–" if sinir is None else f"{sinir:.0f}"
        if o is None:
            s.append(f"| {v} | {t} | {n:g} | çözüm yok | | {sinir_metni} | | | | | |")
        else:
            s.append(f"| {v} | {t} | {n:g} | {gercek} | {model} | {sinir_metni} | {o.sinif_boslugu} | "
                     f"{o.ogretmen_penceresi} | {o.bolunmus_ders} | {o.tercih_etmez} | {o.eksik_bos_gun} |")
    s += ["", "| Varyant | Tohum | İlk çözüm (sn) | Son alt sınır |", "|---|---|---|---|"]
    for (v, t), ilk in ilkler.items():
        s.append(f"| {v} | {t} | {'–' if ilk is None else f'{ilk:.1f}'} | {son_sinirlar[(v, t)]:.0f} |")
    yol.write_text("\n".join(s) + "\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("veri")
    p.add_argument("--varyant", nargs="+", default=["mevcut", "A", "B"], choices=list(VARYANTLAR))
    p.add_argument("--tohum", type=int, nargs="+", default=[0, 1, 2])
    p.add_argument("--sure", type=float, default=60.0)
    p.add_argument("--cikti", default="scripts/sonuclar")
    p.add_argument("--mini", default="veri/mini.json")
    a = p.parse_args()

    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    ozet = cikti / "pencere_varyantlari.md"
    baslik = (
        f"# Pencere formülasyonu deneyi\n\n{datetime.now():%Y-%m-%d %H:%M}, {a.veri}, süre {a.sure:g} sn, "
        f"8 iş parçacığı, OR-Tools {ortools.__version__}, Python {platform.python_version()}, "
        f"{platform.processor() or platform.machine()}.\n\nGerçek ceza: bağımsız ölçümlerin ağırlıklı "
        f"toplamı. Alt sınır: CP-SAT'ın o ana kadar kanıtladığı en iyi alt sınır (gerçek alt sınır en az 0)."
    )

    # 1) Mini sette doğruluk denetimi
    denetim = ["", "## Mini sette doğruluk denetimi", "", "| Varyant | Durum | Model ceza | Gerçek ceza | Doğrulama |",
               "|---|---|---|---|---|"]
    for v in a.varyant:
        durum, model, gercek, gecerli = mini_dogrulama(v, a.mini)
        denetim.append(f"| {v} | {durum} | {model} | {gercek} | {'geçti' if gecerli else 'HATA'} |")
        print(denetim[-1], flush=True)
    baslik += "\n" + "\n".join(denetim) + f"\n\n## Ölçüm: {a.veri}"
    ozet.write_text(baslik + "\n", encoding="utf-8")

    # 2) Ölçüm: her çalıştırmadan sonra özet yeniden yazılır, ham CSV her çözümde.
    satirlar, ilkler, son_sinirlar = [], {}, {}
    ham_yol = cikti / "pencere_ham.csv"
    yeni = not ham_yol.exists()
    with ham_yol.open("a", newline="", encoding="utf-8") as dosya:
        yazici = csv.writer(dosya)
        if yeni:
            yazici.writerow(["varyant", "tohum", "saniye", "amac", "alt_sinir"])
        for v in a.varyant:
            for t in a.tohum:
                r, ilk, son = calistir(girdi_oku(a.veri), v, t, a.sure, yazici, dosya)
                satirlar += r
                ilkler[(v, t)], son_sinirlar[(v, t)] = ilk, son
                ozet_yaz(ozet, baslik, satirlar, ilkler, son_sinirlar)
                print(f"{v} tohum {t} bitti: {a.sure:g} sn gerçek ceza {r[-1][3]}, son alt sınır {son:.0f}", flush=True)


if __name__ == "__main__":
    main()
