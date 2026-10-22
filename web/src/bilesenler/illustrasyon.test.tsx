import { render } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { Illustrasyon, type IllustrasyonTuru } from "./Illustrasyon";

const TURLER: IllustrasyonTuru[] = ["ogretmen", "sinif", "ders", "takvim"];

describe("boş durum çizimleri", () => {
  it.each(TURLER)("%s: yalnızca süs (ekran okuyucudan gizli), renk sabitlemez", (tur) => {
    const { container } = render(<Illustrasyon tur={tur} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg?.querySelectorAll("*").length).toBeGreaterThan(4);
    // Renkler CSS sınıflarından (belirteçler) gelir; öznitelikte sabit renk yok.
    for (const oge of svg?.querySelectorAll("*") ?? []) {
      expect(oge.getAttribute("fill")).toBeNull();
      expect(oge.getAttribute("stroke")).toBeNull();
    }
  });

  it("stil dosyası yalnızca belirteç kullanır (sabit renk yok)", () => {
    const css = readFileSync(resolve("src/bilesenler/Illustrasyon.module.css"), "utf-8");
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,6}\b|rgb\(/);
  });
});
