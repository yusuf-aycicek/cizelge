/**
 * Renk kontrastı (WCAG 2.2): belirteç dosyasındaki renkleri okur ve birlikte kullanılan çiftlerin
 * kontrastını hesaplar. Bir rengi değiştiren kişi okunaklılığı bozarsa test kırılır.
 *
 * - Metin: en az 4.5:1 (AA, normal boyutlu yazı).
 * - Arayüz sınırları (form alanı kenarı, odak halkası): en az 3:1 (WCAG 1.4.11).
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve("src/stil/belirtecler.css"), "utf-8");
function renk(ad: string): string {
  const eslesme = css.match(new RegExp(`--${ad}:\\s*(#[0-9a-fA-F]{6})`));
  if (!eslesme?.[1]) throw new Error(`Belirteç bulunamadı ya da #rrggbb değil: --${ad}`);
  return eslesme[1];
}

function goreliParlaklik(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function kontrast(on: string, arka: string): number {
  const [a, b] = [goreliParlaklik(on), goreliParlaklik(arka)].sort((x, y) => y - x) as [number, number];
  return (a + 0.05) / (b + 0.05);
}

const METIN_CIFTLERI: [string, string][] = [
  ["renk-metin", "renk-zemin"],
  ["renk-metin", "renk-yuzey"],
  ["renk-metin", "renk-yuzey-vurgu"],
  ["renk-metin-ikincil", "renk-zemin"],
  ["renk-metin-ikincil", "renk-yuzey"],
  ["renk-birincil", "renk-zemin"], // bağlantılar, metin düğme
  ["renk-birincil-metin", "renk-birincil"],
  ["renk-birincil-metin", "renk-birincil-koyu"],
  ["renk-tehlike-metin", "renk-tehlike"],
  ["renk-tehlike-metin", "renk-tehlike-koyu"],
  ["renk-hata-metin", "renk-zemin"], // alan altındaki hata metni
  ["renk-basari-metin", "renk-zemin"],
  ["renk-basari-metin", "renk-basari-zemin"],
  ["renk-hata-metin", "renk-hata-zemin"],
  ["renk-uyari-metin", "renk-uyari-zemin"],
  ["renk-bilgi-metin", "renk-bilgi-zemin"],
  ["renk-metin", "renk-sayfa"],
  ["renk-metin-ikincil", "renk-sayfa"],
  ["renk-birincil", "renk-sayfa"],
  ["renk-ust-metin", "renk-ust-zemin"],
  ["renk-ust-metin", "renk-ust-vurgu"],
  ["renk-menu-metin", "renk-menu-zemin"],
  ["renk-menu-metin", "renk-menu-vurgu"],
  ["renk-menu-aktif-metin", "renk-menu-aktif-zemin"],
  ...[1, 2, 3, 4, 5, 6, 7, 8].map((i): [string, string] => ["renk-cip-metin", `renk-rozet-${i}`]),
];

const SINIR_CIFTLERI: [string, string][] = [
  ["renk-kenar-alan", "renk-zemin"],
  ["renk-odak", "renk-zemin"],
  ["renk-tehlike", "renk-zemin"], // hatalı alanın kenarı
];

describe("renk kontrastı", () => {
  it.each(METIN_CIFTLERI)("metin %s / %s en az 4.5:1", (on, arka) => {
    expect(kontrast(renk(on), renk(arka))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(SINIR_CIFTLERI)("sınır %s / %s en az 3:1", (on, arka) => {
    expect(kontrast(renk(on), renk(arka))).toBeGreaterThanOrEqual(3);
  });
});

describe("kontrast hesabı", () => {
  it("hesap bilinen değerleri verir", () => {
    expect(kontrast("#000000", "#ffffff")).toBeCloseTo(21, 1);
    expect(kontrast("#777777", "#ffffff")).toBeCloseTo(4.48, 2);
  });
});
