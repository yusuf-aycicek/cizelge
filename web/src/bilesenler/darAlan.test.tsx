/** Dar alanda kısa ad: kısaltma kuralı, ölçüme göre geçiş, erişilebilirlik. */
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DersCipi } from "../dersler/DersCipi";
import { darMi, kisaKisiAdi } from "./darAlan";
import { SigdirilanMetin } from "./SigdirilanMetin";

describe("kısaltma", () => {
  it("öğretmen adı: ad baş harfleri, soyadı tam", () => {
    expect(kisaKisiAdi("Zeynep Demir")).toBe("Z. Demir");
    expect(kisaKisiAdi("Ayşe Nur Yılmaz")).toBe("A. N. Yılmaz");
    expect(kisaKisiAdi("  ismail  Çelik ")).toBe("İ. Çelik"); // Türkçe büyük harf
    expect(kisaKisiAdi("Cem")).toBe("Cem");
  });

  it("yarım piksel taşma sayılmaz", () => {
    expect(darMi(100.4, 100)).toBe(false);
    expect(darMi(101, 100)).toBe(true);
  });
});

/**
 * jsdom yerleşim yapmaz: genişlikler sıfırdır, ResizeObserver yoktur. Test ikisini taklit eder:
 * metnin doğal genişliği karakter başına 8 px, alanın genişliği `alan` değişkeni.
 */
describe("ölçüme göre kısa ya da uzun", () => {
  let alan = 200;
  let gozlemciler: (() => void)[] = [];

  beforeEach(() => {
    gozlemciler = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(private geri: () => void) {}
        observe() {
          gozlemciler.push(this.geri);
        }
        disconnect() {}
      },
    );
    vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockImplementation(function (this: HTMLElement) {
      return (this.textContent ?? "").length * 8;
    });
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(() => alan);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  const yenidenBoyutla = (genislik: number) =>
    act(() => {
      alan = genislik;
      gozlemciler.forEach((g) => g());
    });

  it("öğretmen adı sığmazsa kısalır; tam ad üzerine gelince ve ekran okuyucuda; alan genişleyince geri döner", () => {
    alan = 200; // "Zeynep Demir" 12 karakter = 96 px: sığar
    render(<SigdirilanMetin uzun="Zeynep Demir" kisa="Z. Demir" />);
    expect(screen.getByText("Zeynep Demir")).not.toHaveAttribute("title");

    yenidenBoyutla(80);
    const kisa = screen.getByText("Z. Demir");
    expect(kisa).toHaveAttribute("aria-hidden", "true");
    expect(kisa.parentElement).toHaveAttribute("title", "Zeynep Demir");
    expect(screen.getByText("Zeynep Demir")).toHaveClass("gorunmez");

    yenidenBoyutla(200);
    expect(screen.queryByText("Z. Demir")).toBeNull();
  });

  it("ders çipi dar alanda kısa adı gösterir, rengi ve işareti korur", () => {
    alan = 100; // "Türk Dili ve Edebiyatı" 22 karakter = 176 px: sığmaz
    render(<DersCipi ad="Türk Dili ve Edebiyatı" kisaAd="TDE" renk="#1d4ed8" isaret={1} />);
    const kisa = screen.getByText("TDE");
    expect(kisa).toHaveAttribute("aria-hidden", "true");
    const cip = kisa.parentElement!;
    expect(cip).toHaveAttribute("title", "Türk Dili ve Edebiyatı");
    expect(cip.style.getPropertyValue("--ders-rengi")).toBe("#1d4ed8");
    expect(cip).toHaveTextContent("◆TDETürk Dili ve Edebiyatı");
    expect(screen.getByText("Türk Dili ve Edebiyatı")).toHaveClass("gorunmez");
  });

  it("sığan çipte kısa ad yok", () => {
    alan = 300;
    render(<DersCipi ad="Fizik" kisaAd="FİZ" />);
    expect(screen.queryByText("FİZ")).toBeNull();
    expect(screen.getByText("Fizik")).not.toHaveAttribute("title");
  });
});
