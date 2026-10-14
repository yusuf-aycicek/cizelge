"""docs/diyagramlar/*.puml -> docs/diyagramlar/cikti/*.svg ve *.png (PlantUML, Docker ile).

Kullanım (depo kökünden, herhangi bir Python ile):
    python scripts/diyagramlari_uret.py            # SVG ve PNG
    python scripts/diyagramlari_uret.py --bicim svg

PlantUML imajı sürümüyle sabitlenmiştir: aynı kaynak her makinede aynı çıktıyı verir. Kod
değiştiğinde önce `api/tests/test_diyagramlar.py` (diyagram-kod tutarlılığı), sonra bu betik.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

IMAJ = "plantuml/plantuml:1.2026.8"
DIZIN = Path(__file__).resolve().parents[1] / "docs" / "diyagramlar"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bicim", nargs="+", default=["svg", "png"], choices=["svg", "png"])
    a = p.parse_args()
    kaynaklar = sorted(DIZIN.glob("*.puml"))
    if not kaynaklar:
        print(f"{DIZIN} altında .puml yok", file=sys.stderr)
        return 1
    for bicim in a.bicim:
        # Joker (*.puml) kabukta değil, PlantUML'in kendisinde açılır; /data konteyner içindeki dizin.
        komut = ["docker", "run", "--rm", "-v", f"{DIZIN}:/data", "-w", "/data", IMAJ,
                 f"-t{bicim}", "-charset", "UTF-8", "-o", "cikti", "*.puml"]
        sonuc = subprocess.run(komut)
        if sonuc.returncode != 0:
            print(f"PlantUML hatası ({bicim}); yukarıdaki çıktıya bakın.", file=sys.stderr)
            return sonuc.returncode
    for bicim in a.bicim:
        for kaynak in kaynaklar:
            cikti = DIZIN / "cikti" / f"{kaynak.stem}.{bicim}"
            print(f"{cikti.relative_to(DIZIN.parents[1])}  {cikti.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
