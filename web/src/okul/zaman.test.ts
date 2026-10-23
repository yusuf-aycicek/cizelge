/** Okulun haftası: zil saatleri, öğle arası, kısa günler (saf fonksiyonlar). */
import { describe, expect, it } from "vitest";
import { kisaliyor, ogleArasiSonrasi, ogleArasiZili, saatVar, zilMetni, zilSaatleri, type Hafta } from "./zaman";

const HAFTA: Hafta = {
  gun_saatleri: [8, 8, 8, 8, 5], ogle_arasi_sonra: null, ilk_ders_baslangic: "08:30:00", ders_suresi_dk: 40,
  teneffus_dk: 10, ogle_arasi_dk: 40,
};

describe("zil saatleri", () => {
  it("tanımsızsa null", () => {
    expect(zilSaatleri({ ...HAFTA, ilk_ders_baslangic: null }, 8)).toBeNull();
  });

  it("ders + teneffüs; sunucunun saniyeli biçimi de okunur", () => {
    expect(zilSaatleri(HAFTA, 3)!.map(zilMetni)).toEqual(["08:30–09:10", "09:20–10:00", "10:10–10:50"]);
  });

  it("öğle arasından sonra teneffüs yerine öğle arası süresi", () => {
    const hafta = { ...HAFTA, ogle_arasi_sonra: 2, ogle_arasi_dk: 45 };
    const zil = zilSaatleri(hafta, 3)!;
    expect(zil.map(zilMetni)).toEqual(["08:30–09:10", "09:20–10:00", "10:45–11:25"]);
    expect(zilMetni(ogleArasiZili(hafta, zil)!)).toBe("10:00–10:45");
    expect(ogleArasiZili({ ...hafta, ogle_arasi_sonra: null }, zil)).toBeNull();
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
