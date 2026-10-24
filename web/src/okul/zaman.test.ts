/** Okulun haftası: zil saatleri, öğle arası, kısa günler (saf fonksiyonlar). */
import { describe, expect, it } from "vitest";
import { kisaliyor, ogleArasiSonrasi, saatVar, zilMetni } from "./zaman";

const HAFTA = { gun_saatleri: [8, 8, 8, 8, 5] };

describe("zil metni", () => {
  // Zil saatlerinin hesabı sunucudadır (api cekirdek/zil.py, testleri test_okul_zamani.py).
  it("aralık kısa çizgiyle", () => {
    expect(zilMetni({ baslangic: "08:30", bitis: "09:10" })).toBe("08:30–09:10");
  });
});

describe("hafta", () => {
  it("kısa günün sonundaki saat yoktur", () => {
    expect(saatVar(HAFTA.gun_saatleri, 4, 4)).toBe(true);
    expect(saatVar(HAFTA.gun_saatleri, 4, 5)).toBe(false);
    expect(saatVar(HAFTA.gun_saatleri, 0, 7)).toBe(true);
    expect(saatVar(HAFTA.gun_saatleri, 5, 0)).toBe(false); // olmayan gün
  });

  it("öğle arası ayracı n. dersten sonra", () => {
    expect(ogleArasiSonrasi(4, 3)).toBe(true);
    expect(ogleArasiSonrasi(4, 4)).toBe(false);
    expect(ogleArasiSonrasi(null, 3)).toBe(false);
  });

  it("kısalma: bir gün kısalırsa ya da gün azalırsa", () => {
    expect(kisaliyor([8, 8, 8, 8, 8], [8, 8, 8, 8, 5])).toBe(true);
    expect(kisaliyor([8, 8, 8, 8, 8], [8, 8, 8, 8])).toBe(true);
    expect(kisaliyor([8, 8, 8, 8, 5], [8, 8, 8, 8, 8])).toBe(false);
    expect(kisaliyor([8, 8, 8, 8, 5], [8, 8, 8, 8, 5, 8])).toBe(false);
  });
});
