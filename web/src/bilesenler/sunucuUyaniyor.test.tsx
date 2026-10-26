import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GECIKME_ESIGI_MS, izle } from "../api/uyanma";
import { SunucuUyaniyor } from "./SunucuUyaniyor";

afterEach(() => vi.useRealTimers());

it("istek eşikten uzun sürünce bildirim görünür, bitince kaybolur; kısa istekte hiç görünmez", async () => {
  vi.useFakeTimers();
  render(<SunucuUyaniyor />);

  let bitir!: (deger: string) => void;
  const yavas = izle(new Promise<string>((r) => (bitir = r)));
  const hizli = izle(Promise.resolve("tamam"));
  await act(async () => {
    await hizli;
    vi.advanceTimersByTime(GECIKME_ESIGI_MS - 1);
  });
  expect(screen.queryByRole("status")).toBeNull();

  act(() => vi.advanceTimersByTime(1));
  expect(screen.getByRole("status")).toHaveTextContent("Sunucu uyanıyor");

  await act(async () => {
    bitir("tamam");
    await yavas;
  });
  expect(screen.queryByRole("status")).toBeNull();
});
