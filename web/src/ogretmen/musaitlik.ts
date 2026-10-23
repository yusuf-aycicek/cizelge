/**
 * Müsaitlik çizelgesinin saf mantığı: durum döngüsü, toplu değişiklik, iyimser uygulama.
 * Bileşenden ayrı: React'siz test edilir.
 */
import type { components } from "../api/sema";

export type Durum = "musait" | "gelemez" | "tercih_etmez";
export type KayitliHucre = components["schemas"]["MusaitlikHucresi"];
export type Degisiklik = components["schemas"]["MusaitlikDegisikligi"];
export type Konum = { gun: number; saat: number };

/** Tıklandıkça: müsait → gelemez → tercih etmez → müsait. */
export const DURUM_SIRASI: readonly Durum[] = ["musait", "gelemez", "tercih_etmez"];

export const DURUM_ADLARI: Record<Durum, string> = {
  musait: "müsait",
  gelemez: "gelemez",
  tercih_etmez: "tercih etmez",
};

export function sonrakiDurum(d: Durum): Durum {
  return DURUM_SIRASI[(DURUM_SIRASI.indexOf(d) + 1) % DURUM_SIRASI.length]!;
}

export const anahtar = (k: Konum) => `${k.gun}-${k.saat}`;

/** Kayıtlı hücreler (yalnızca müsait olmayanlar) → her hücrenin durumu; kayıtsız hücre müsaittir. */
export function durumHaritasi(hucreler: readonly KayitliHucre[]): Map<string, Durum> {
  return new Map(hucreler.map((h) => [anahtar(h), h.durum]));
}

export const durumu = (harita: ReadonlyMap<string, Durum>, k: Konum): Durum => harita.get(anahtar(k)) ?? "musait";

/** Hücreleri `hedef` duruma getirmek için gereken değişiklikler (zaten o durumda olanlar atlanır). */
export function degisiklikler(harita: ReadonlyMap<string, Durum>, hucreler: readonly Konum[], hedef: Durum): Degisiklik[] {
  const gorulen = new Set<string>();
  const sonuc: Degisiklik[] = [];
  for (const k of hucreler) {
    const a = anahtar(k);
    if (gorulen.has(a)) continue;
    gorulen.add(a);
    if (durumu(harita, k) !== hedef) sonuc.push({ gun: k.gun, saat: k.saat, durum: hedef });
  }
  return sonuc;
}

/**
 * Bir satırı ya da sütunu birlikte döndürmek: hepsi ilk hücrenin bir sonraki durumuna geçer
 * ("pazartesi bütün gün gelemez"). Karışık bir satırda da sonuç öngörülebilir olsun diye tek bir
 * hedef seçilir.
 */
export function topluHedef(harita: ReadonlyMap<string, Durum>, hucreler: readonly Konum[]): Durum {
  return sonrakiDurum(durumu(harita, hucreler[0]!));
}

/** İyimser güncelleme: değişiklikler sunucu cevabından önce yerel listeye uygulanır. */
export function uygula(hucreler: readonly KayitliHucre[], degisen: readonly Degisiklik[]): KayitliHucre[] {
  const harita = new Map(hucreler.map((h) => [anahtar(h), h]));
  for (const d of degisen) {
    if (d.durum === "musait") harita.delete(anahtar(d));
    else harita.set(anahtar(d), { gun: d.gun, saat: d.saat, durum: d.durum });
  }
  return [...harita.values()].sort((a, b) => a.gun - b.gun || a.saat - b.saat);
}

/** Klavye: oklarla bir hücre ötesine, kenarda durur. */
export function komsu(k: Konum, tus: string, gunSayisi: number, saatSayisi: number): Konum | null {
  const yon: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  const d = yon[tus];
  if (tus === "Home") return { gun: 0, saat: k.saat };
  if (tus === "End") return { gun: gunSayisi - 1, saat: k.saat };
  if (!d) return null;
  const gun = Math.min(gunSayisi - 1, Math.max(0, k.gun + d[0]));
  const saat = Math.min(saatSayisi - 1, Math.max(0, k.saat + d[1]));
  return { gun, saat };
}
