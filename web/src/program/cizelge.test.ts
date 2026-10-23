import { describe, expect, it } from "vitest";
import { cizelgeBoyutu, cizelgeHucreleri, hucreAnahtari, yerlesmeGecikmesiMs, type Atama, type Yerlesim } from "./cizelge";

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
