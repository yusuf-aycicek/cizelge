import { describe, expect, it } from "vitest";
import { ilkAd, selam, SELAM_DESENI, tarihMetni } from "./selam";

const saatte = (saat: number) => new Date(2026, 10, 2, saat, 15);

describe("ana sayfa selamı", () => {
  it.each([
    [4, "İyi geceler"],
    [5, "Günaydın"],
    [11, "Günaydın"],
    [12, "İyi günler"],
    [17, "İyi günler"],
    [18, "İyi akşamlar"],
    [22, "İyi akşamlar"],
    [23, "İyi geceler"],
  ])("saat %i: %s", (saat, beklenen) => {
    expect(selam(saatte(saat))).toBe(beklenen);
    expect(selam(saatte(saat))).toMatch(SELAM_DESENI);
  });

  it("tarih Türkçe, gün adıyla; ad ilk kelime", () => {
    expect(tarihMetni(saatte(9))).toBe("2 Kasım 2026, Pazartesi");
    expect(ilkAd("Ayşe Gülşen Yılmaz")).toBe("Ayşe");
  });
});
