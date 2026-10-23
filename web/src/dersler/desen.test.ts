/** Dağılım şekli: metin ↔ blok listesi, hazır seçenekler (saf fonksiyonlar). */
import { describe, expect, it } from "vitest";
import { ayniDesen, bolunusler, desenMetni, desenOku, otomatikDesen } from "./desen";

describe("dağılım şekli", () => {
  it("otomatik öneri sunucudakiyle aynı: 1, 2, 2+1, 2+2, 2+2+1, 2+2+2", () => {
    expect([1, 2, 3, 4, 5, 6].map((s) => desenMetni(otomatikDesen(s)))).toEqual(["1", "2", "2+1", "2+2", "2+2+1", "2+2+2"]);
    expect(desenMetni([])).toBe("blok yok");
  });

  it("yazılan şekil okunur, büyükten küçüğe sıralanır; geçersizse null", () => {
    expect(desenOku("2+2+1")).toEqual([2, 2, 1]);
    expect(desenOku(" 1 + 2 +2 ")).toEqual([2, 2, 1]);
    expect(desenOku("Blok yok")).toEqual([]);
    expect(desenOku("")).toEqual([]);
    for (const kotu of ["2+", "2,2", "0+2", "9", "iki", "2++1"]) expect(desenOku(kotu)).toBeNull();
  });

  it("hazır seçenekler: blok boyu ve blok sayısı sınırlı, büyük bloklar önce", () => {
    expect(bolunusler(5, 2, 5).map(desenMetni)).toEqual(["2+2+1", "2+1+1+1", "1+1+1+1+1"]);
    expect(bolunusler(5, 3, 3).map(desenMetni)).toEqual(["3+2", "3+1+1", "2+2+1"]);
    expect(bolunusler(1, 3, 5)).toEqual([[1]]);
  });

  it("şekil karşılaştırma", () => {
    expect(ayniDesen([2, 1], [2, 1])).toBe(true);
    expect(ayniDesen([2, 1], [2, 1, 1])).toBe(false);
  });
});
