"""Çekirdek: okul, kullanıcı, öğretmen, sınıf, ders ve bütün modüllerin kullandığı altyapı.

Kural: çekirdek `okulapi.moduller` altındaki hiçbir paketi içe aktarmaz (testle denetlenir).
"""

from pathlib import Path

CEKIRDEK_MIGRATION_DIZINI = Path(__file__).parent / "migrations"
