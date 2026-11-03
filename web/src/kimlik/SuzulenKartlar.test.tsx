import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KART_SAYISI, KART_YAZILARI, SuzulenKartlar } from "./SuzulenKartlar";

describe("SuzulenKartlar", () => {
  it("22 kart çizer, ekran okuyucudan gizlidir, bütün yazılar en az bir kez görünür", () => {
    render(<SuzulenKartlar />);
    const katman = screen.getByTestId("suzulen-kartlar");
    expect(katman).toHaveAttribute("aria-hidden", "true");
    const kartlar = [...katman.children] as HTMLElement[];
    expect(kartlar).toHaveLength(KART_SAYISI);
    const yazilar = new Set(kartlar.map((k) => k.textContent));
    for (const y of KART_YAZILARI) expect(yazilar).toContain(y);
  });

  it("yatay yerler ve gecikmeler dağılmıştır: hiçbir iki kart aynı yerde ya da aynı anda değildir", () => {
    render(<SuzulenKartlar />);
    const kartlar = [...screen.getByTestId("suzulen-kartlar").children] as HTMLElement[];
    const xler = new Set(kartlar.map((k) => k.style.getPropertyValue("--x")));
    const pler = kartlar.map((k) => Number(k.style.getPropertyValue("--p")));
    expect(xler.size).toBe(KART_SAYISI);
    expect(new Set(pler).size).toBe(KART_SAYISI);
    for (const p of pler) {
      expect(p).toBeGreaterThan(0);
      expect(p).toBeLessThan(1);
    }
    // İlk 10 kart (telefon) da yolun her yerine eşit aralıkla dağılır.
    const telefon = kartlar.slice(0, 10).map((k) => Number(k.style.getPropertyValue("--p-tel")));
    expect(new Set(telefon).size).toBe(10);
  });
});
