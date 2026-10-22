import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { basHarfler, OgretmenAdi, rozetRengi, ROZET_RENGI_SAYISI } from "./OgretmenRozeti";

describe("baş harfler", () => {
  it.each([
    ["Ayşe Yılmaz", "AY"],
    ["ismail er", "İE"], // Türkçe büyük harf: i → İ
    ["ılgaz çelik", "IÇ"], // ı → I
    ["Ayşe Gülşen Yılmaz", "AY"], // ilk ve son kelime
    ["  Şule   Kaya  ", "ŞK"],
    ["Gül", "G"],
    ["", "?"],
  ])("%s → %s", (ad, beklenen) => {
    expect(basHarfler(ad)).toBe(beklenen);
  });
});

describe("rozet rengi", () => {
  it("aynı kimlik her zaman aynı renk, aralık içinde", () => {
    for (const kimlik of ["o1", "o-ayse", "3f2a9c1e-0000-4000-8000-000000000000"]) {
      const renk = rozetRengi(kimlik);
      expect(rozetRengi(kimlik)).toBe(renk);
      expect(renk).toBeGreaterThanOrEqual(1);
      expect(renk).toBeLessThanOrEqual(ROZET_RENGI_SAYISI);
    }
  });

  it("farklı kimlikler renklere yayılır", () => {
    const renkler = new Set(Array.from({ length: 40 }, (_, i) => rozetRengi(`ogretmen-${i}`)));
    expect(renkler.size).toBeGreaterThanOrEqual(6);
  });
});

describe("öğretmen adı", () => {
  it("baş harfler metne karışmaz (CSS ile çizilir), ad okunur", () => {
    render(<OgretmenAdi id="o1" ad="Ali Çelik" />);
    const kutu = screen.getByText("Ali Çelik");
    expect(kutu.textContent).toBe("Ali Çelik");
    const rozet = kutu.querySelector("[data-harfler]");
    expect(rozet).toHaveAttribute("data-harfler", "AÇ");
    expect(rozet).toHaveAttribute("aria-hidden", "true");
    expect(within(kutu).queryByText("AÇ")).not.toBeInTheDocument();
  });
});
