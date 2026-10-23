"""Ders renkleri: paletin tek tanımı.

Her derse bir renk verilir. Arayüz bu rengi dersin "çip"inde kullanır: ders listesinde, ders
dağılımında, seviye şablonunda ve ileride haftalık çizelgede; renk her yerde aynıdır.

- Renk yalnızca bu paletten seçilebilir. Böylece çipteki beyaz yazının okunaklılığı (WCAG AA,
  4.5:1) her renk için testle garanti edilir (tests/test_ders_renkleri.py). Serbest renk seçimi
  okunmaz bir çipe izin verirdi.
- Yeni derse okulda en az kullanılan renk verilir (eşitlikte palet sırası): ilk 20 ders hep farklı
  renkte olur. Kullanıcı sonra değiştirebilir. Ders sayısı paleti aşarsa renk tekrar eder; arayüz
  tekrar eden derslerin çipine ayırt edici küçük bir işaret koyar (◆ ▲ ●).
- Arayüz paleti bilmez; `GET /api/ders-renkleri` ile okur.
- Sıra, komşu renklerin birbirinden belirgin farklı olacağı şekilde seçildi. İlk 14 renk ilk
  sürümdür (var olan derslerin rengi değişmesin diye yerinde). Son 6, beyaz yazıyla 4.5:1'i geçen
  adaylar arasından var olanlara algısal uzaklığı (CIELAB ΔE) en büyük olan seçilerek eklendi. Test
  her iki rengin ΔE ≥ 15 olduğunu denetler (en yakın çift 18,8).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

# (renk, Türkçe adı). Renk küçük harfli #rrggbb.
DERS_RENKLERI: tuple[tuple[str, str], ...] = (
    ("#1d4ed8", "Lacivert"),
    ("#c2410c", "Kiremit"),
    ("#15803d", "Yeşil"),
    ("#7e22ce", "Mor"),
    ("#0e7490", "Camgöbeği"),
    ("#be123c", "Gül"),
    ("#a16207", "Hardal"),
    ("#0369a1", "Gök mavisi"),
    ("#a21caf", "Eflatun"),
    ("#4d7c0f", "Zeytin"),
    ("#7c2d12", "Kahve"),
    ("#0f766e", "Turkuaz"),
    ("#be185d", "Pembe"),
    ("#475569", "Arduvaz"),
    ("#312e81", "Çivit"),
    ("#701a75", "Mürdüm"),
    ("#365314", "Haki"),
    ("#4c1d95", "Patlıcan"),
    ("#831843", "Bordo"),
    ("#dc2626", "Kırmızı"),
)
RENK_KODLARI = frozenset(r for r, _ in DERS_RENKLERI)
CIP_METNI = "#ffffff"  # çipteki yazının rengi; her palet rengiyle en az 4.5:1


def siradaki_renk(kullanilanlar: Iterable[str]) -> str:
    """Okulda en az kullanılan palet rengi; eşitlikte palet sırasındaki ilk."""
    sayilar = Counter(kullanilanlar)
    return min((r for r, _ in DERS_RENKLERI), key=lambda r: sayilar[r])
