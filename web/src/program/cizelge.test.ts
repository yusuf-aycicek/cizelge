import { describe, expect, it } from "vitest";
import { birlesikHucreler, cizelgeBoyutu, cizelgeHucreleri, hucreAnahtari, yerlesmeGecikmesiMs, type Atama, type Yerlesim } from "./cizelge";

const ATAMALAR: Atama[] = [
  { id: "a1", sinif_id: "s-9a", ders_id: "d-mat", ogretmen_id: "o-sule", haftalik_saat: 2 },
  { id: "a2", sinif_id: "s-9b", ders_id: "d-mat", ogretmen_id: "o-sule", haftalik_saat: 1 },
  { id: "a3", sinif_id: "s-9a", ders_id: "d-fiz", ogretmen_id: "o-zeynep", haftalik_saat: 1 },
];
const y = (id: string, ders_atama_id: string, gun: number, saat: number): Yerlesim => ({ id, ders_atama_id, gun, saat, kilitli: false });
const YERLESIMLER = [y("y1", "a1", 0, 0), y("y2", "a1", 0, 1), y("y3", "a2", 1, 0), y("y4", "a3", 2, 3), y("y5", "silinmis", 4, 4)];

describe("çizelge hücreleri", () => {
  it("şubenin hücreleri", () => {
    const h = cizelgeHucreleri(YERLESIMLER, ATAMALAR, "sube", "s-9a");
    expect([...h.keys()].sort()).toEqual(["0-0", "0-1", "2-3"]);
    expect(h.get(hucreAnahtari(2, 3))?.ders_id).toBe("d-fiz");
  });

  it("öğretmenin hücreleri, şubeleri ayrı", () => {
    const h = cizelgeHucreleri(YERLESIMLER, ATAMALAR, "ogretmen", "o-sule");
    expect([...h.entries()].map(([k, a]) => [k, a.sinif_id]).sort()).toEqual([["0-0", "s-9a"], ["0-1", "s-9a"], ["1-0", "s-9b"]]);
  });

  it("silinmiş atamanın yerleşimi atlanır", () => {
    const h = cizelgeHucreleri(YERLESIMLER, ATAMALAR, "sube", "s-9a");
    expect(h.has("4-4")).toBe(false);
  });
});

describe("çizelge boyutu", () => {
  it("okul ayarı; program daha büyükse program", () => {
    expect(cizelgeBoyutu(YERLESIMLER, 5, 8)).toEqual({ gun: 5, saat: 8 });
    expect(cizelgeBoyutu(YERLESIMLER, 3, 2)).toEqual({ gun: 5, saat: 5 });
    expect(cizelgeBoyutu([], 5, 6)).toEqual({ gun: 5, saat: 6 });
  });
});

describe("yerleşme sırası", () => {
  it("gün gün artar, 0,6 sn'yi geçmez", () => {
    expect(yerlesmeGecikmesiMs(0, 0, 8)).toBe(0);
    expect(yerlesmeGecikmesiMs(0, 1, 8)).toBeLessThan(yerlesmeGecikmesiMs(1, 0, 8));
    expect(yerlesmeGecikmesiMs(6, 15, 16)).toBe(600);
  });
});

describe("blok: aynı dersin art arda saatleri tek hücre", () => {
  const atama = (id: string) => ({ id, sinif_id: "s1", ders_id: id, ogretmen_id: "o1", haftalik_saat: 2 }) as Atama;
  const harita = (liste: [number, number, string][]) => new Map(liste.map(([g, s, a]) => [hucreAnahtari(g, s), atama(a)]));

  it("art arda aynı atama birleşir; farklı atama ya da öğle arası böler", () => {
    const h = harita([[0, 0, "mat"], [0, 1, "mat"], [0, 2, "fiz"], [0, 3, "mat"], [0, 4, "mat"], [1, 1, "mat"], [1, 2, "mat"], [1, 3, "mat"]]);
    const { uzunluk, ortulen } = birlesikHucreler(h, 2, 6, 4);
    // Pazartesi: 1.-2. saat matematik (blok), 3. fizik, 4. ve 5. matematik ama arada öğle arası.
    expect(Object.fromEntries(uzunluk)).toEqual({ "0-0": 2, "1-1": 3 });
    expect([...ortulen].sort()).toEqual(["0-1", "1-2", "1-3"]);
  });

  it("öğle arası 4. dersten sonra: 4. ve 5. saat birleşmez", () => {
    const h = harita([[0, 3, "mat"], [0, 4, "mat"]]);
    const { uzunluk, ortulen } = birlesikHucreler(h, 1, 6, 4);
    expect(uzunluk.size).toBe(0);
    expect(ortulen.size).toBe(0);
  });
});
