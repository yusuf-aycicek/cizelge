"""Amaç fonksiyonu teşhisi: her esnek kuralın amaca eklediği katsayılar, sabit ve alan sınırları.

Soru: CP-SAT'ın alt sınırı neden negatif? Her kural için ayrı bir model kurulur (zorunlu kurallar +
yalnızca o kuralın cezaları) ve CP-SAT'ın modele yazdığı amaç fonksiyonu (proto) incelenir:
- katsayıların işaretleri ve sabit (offset),
- amaçtaki değişkenlerin alanları (domain),
- "alan sınırı": her değişken kendi alanının en elverişli ucunda olsaydı amacın alacağı en küçük
  değer. CP-SAT gevşetilmiş modelden bir şey öğrenmeden önce elindeki sınır budur.

Kullanım: cozucu/.venv/Scripts/python.exe scripts/amac_teshisi.py veri/gercekci.json
"""

from __future__ import annotations

import sys

from cozucu.kisitlar import Baglam, kurallari_hazirla
from cozucu.veri_io import girdi_oku


def amac_ozeti(model):
    amac = model.proto.objective
    degiskenler = model.proto.variables
    pozitif = negatif = 0
    alan_siniri = amac.offset
    negatif_alanli = 0
    for ref, katsayi in zip(amac.vars, amac.coeffs):
        indeks = ref if ref >= 0 else -ref - 1
        d = degiskenler[indeks].domain
        alt, ust = d[0], d[len(d) - 1]  # bu bağlamada d[-1] son eleman değil, ilk elemanı döner
        if ref < 0:  # negatif referans: değişkenin tümleyeni
            alt, ust = -ust, -alt
        if alt < 0:
            negatif_alanli += 1
        if katsayi > 0:
            pozitif += 1
            alan_siniri += katsayi * alt
        else:
            negatif += 1
            alan_siniri += katsayi * ust
    return {
        "terim": len(amac.vars),
        "pozitif katsayı": pozitif,
        "negatif katsayı": negatif,
        "sabit": amac.offset,
        "alanı negatif değişken": negatif_alanli,
        "alan sınırı": alan_siniri,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    girdi = girdi_oku(sys.argv[1])
    print("| Kural | Ceza terimi | Amaçtaki değişken | Pozitif katsayı | Negatif katsayı | Sabit | "
          "Alanı negatif değişken | Alan sınırı |")
    print("|---|---|---|---|---|---|---|---|")
    kurallar = kurallari_hazirla(girdi)
    for hedef in [k for k in kurallar if not k.zorunlu] + [None]:
        b = Baglam.kur(girdi)
        cezalar = []
        for k in kurallar:
            terimler = k.uygula(b)
            if hedef is None or k is hedef:
                cezalar.extend(terimler)
        if not cezalar:
            continue
        b.model.minimize(sum(a * i for i, a in cezalar))
        o = amac_ozeti(b.model)
        ad = "HEPSİ" if hedef is None else hedef.tur
        print(f"| {ad} | {len(cezalar)} | {o['terim']} | {o['pozitif katsayı']} | {o['negatif katsayı']} | "
              f"{o['sabit']:g} | {o['alanı negatif değişken']} | {o['alan sınırı']:g} |", flush=True)


if __name__ == "__main__":
    main()
