/**
 * Tema: ilk açılışta cihazın ayarı, düğmeyle değiştirme, seçimin hatırlanması.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TemaDugmesi } from "../bilesenler/TemaDugmesi";
import { TEMA_ANAHTARI, temayiBaslat } from "./tema";

function cihazKoyu(koyu: boolean) {
  vi.stubGlobal("matchMedia", (sorgu: string) => ({
    matches: koyu && sorgu.includes("dark"),
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
  delete document.documentElement.dataset.tema;
});

describe("tema", () => {
  it("kayıtlı seçim yoksa cihazın ayarını izler", () => {
    cihazKoyu(true);
    temayiBaslat();
    expect(document.documentElement.dataset.tema).toBe("koyu");
  });

  it("kayıtlı seçim cihazın ayarından önce gelir", () => {
    cihazKoyu(true);
    window.localStorage.setItem(TEMA_ANAHTARI, "acik");
    temayiBaslat();
    expect(document.documentElement.dataset.tema).toBe("acik");
  });

  it("düğme temayı değiştirir, seçimi kaydeder ve adı yapacağı işi söyler", async () => {
    const kullanici = userEvent.setup();
    cihazKoyu(false);
    temayiBaslat();
    render(<TemaDugmesi />);
    await kullanici.click(screen.getByRole("button", { name: "Koyu temaya geç" }));
    expect(document.documentElement.dataset.tema).toBe("koyu");
    expect(window.localStorage.getItem(TEMA_ANAHTARI)).toBe("koyu");
    const dugme = screen.getByRole("button", { name: "Açık temaya geç" });
    dugme.focus();
    await kullanici.keyboard("{Enter}");
    expect(document.documentElement.dataset.tema).toBe("acik");
    expect(window.localStorage.getItem(TEMA_ANAHTARI)).toBe("acik");
  });

  it("localStorage kullanılamazsa tema yine değişir", async () => {
    cihazKoyu(false);
    temayiBaslat();
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("kapalı");
    });
    render(<TemaDugmesi />);
    await userEvent.click(screen.getByRole("button", { name: "Koyu temaya geç" }));
    expect(document.documentElement.dataset.tema).toBe("koyu");
    vi.restoreAllMocks();
  });
});
