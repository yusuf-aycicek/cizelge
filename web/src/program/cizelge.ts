/**
 * Haftalık çizelgenin hücreleri: bir programın yerleşimlerinden, seçilen şube ya da öğretmenin
 * (gün, saat) → atama haritası. Saf fonksiyon.
 */
import type { components } from "../api/sema";

type Sema = components["schemas"];
export type Yerlesim = Sema["YerlesimYanit"];
export type Atama = Sema["DersAtamaYanit"];
export type CizelgeTuru = "sube" | "ogretmen";

export const hucreAnahtari = (gun: number, saat: number) => `${gun}-${saat}`;

export function cizelgeHucreleri(
  yerlesimler: readonly Yerlesim[],
  atamalar: readonly Atama[],
  tur: CizelgeTuru,
  kimlik: string,
): Map<string, Atama> {
  const atama = new Map(atamalar.map((a) => [a.id, a]));
  const hucreler = new Map<string, Atama>();
  for (const y of yerlesimler) {
    const a = atama.get(y.ders_atama_id);
    // Program üretildikten sonra silinen atamanın yerleşimi gösterilmez.
    if (!a) continue;
    if ((tur === "sube" ? a.sinif_id : a.ogretmen_id) !== kimlik) continue;
    hucreler.set(hucreAnahtari(y.gun, y.saat), a);
  }
  return hucreler;
}

/**
 * Çizelgenin boyutu: okulun bugünkü ayarı ile programdaki en büyük gün ve saatin büyüğü. Ayar
 * program üretildikten sonra küçültülmüşse eski programın hücreleri kesilmesin.
 */
export function cizelgeBoyutu(yerlesimler: readonly Yerlesim[], gunSayisi: number, saatSayisi: number) {
  return {
    gun: Math.max(gunSayisi, ...yerlesimler.map((y) => y.gun + 1)),
    saat: Math.max(saatSayisi, ...yerlesimler.map((y) => y.saat + 1)),
  };
}

/** Hücrenin yerleşme animasyonundaki sırası: gün gün, yukarıdan aşağı; toplam ~0,6 sn. */
export function yerlesmeGecikmesiMs(gun: number, saat: number, saatSayisi: number): number {
  return Math.min(600, (gun * saatSayisi + saat) * 15);
}

/**
 * Bir günde aynı dersin art arda saatleri (blok) tek hücre gibi gösterilir: başlangıç hücresi →
 * kaç saat sürdüğü; bloğun öteki saatleri `ortulen`de (tabloda hücre çizilmez, `rowSpan` kapsar).
 * Öğle arasının iki yanı birleşmez (araya ayraç satırı girer).
 */
export function birlesikHucreler(
  hucreler: ReadonlyMap<string, Atama>,
  gunSayisi: number,
  saatSayisi: number,
  ogleArasiSonra: number | null | undefined,
): { uzunluk: Map<string, number>; ortulen: Set<string> } {
  const uzunluk = new Map<string, number>();
  const ortulen = new Set<string>();
  for (let g = 0; g < gunSayisi; g++) {
    let bas = -1;
    for (let s = 0; s < saatSayisi; s++) {
      const a = hucreler.get(hucreAnahtari(g, s));
      const onceki = s > 0 ? hucreler.get(hucreAnahtari(g, s - 1)) : undefined;
      const ogle = ogleArasiSonra != null && s === ogleArasiSonra;
      if (a && onceki && onceki.id === a.id && !ogle && bas >= 0) {
        ortulen.add(hucreAnahtari(g, s));
        uzunluk.set(hucreAnahtari(g, bas), (uzunluk.get(hucreAnahtari(g, bas)) ?? 1) + 1);
      } else {
        bas = a ? s : -1;
      }
    }
  }
  return { uzunluk, ortulen };
}
