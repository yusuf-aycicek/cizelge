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

/**
 * Bir CSS dosyasının iki temasını okur: `:root { … }` açık tema, `:root[data-tema="koyu"] { … }`
 * koyu tema. Koyu temada tanımlı olmayan belirteç açık temadakini kullanır (CSS'teki gibi).
 */
function temalariOku(dosya: string): Record<"acik" | "koyu", (ad: string) => string> {
  const css = readFileSync(resolve(dosya), "utf-8");
  const koyuBasi = css.search(/^:root\[data-tema="koyu"\] \{/m);
  if (koyuBasi === -1) throw new Error(`${dosya}: koyu tema bloğu yok`);
  const okuyucu = (parca: string) => (ad: string) =>
    parca.match(new RegExp(`--${ad}:\\s*(#[0-9a-fA-F]{6})`))?.[1];
  const acik = okuyucu(css.slice(0, koyuBasi));
  const koyu = okuyucu(css.slice(koyuBasi));
  const zorunlu = (bul: (ad: string) => string | undefined) => (ad: string) => {
    const r = bul(ad);
    if (!r) throw new Error(`Belirteç bulunamadı ya da #rrggbb değil: --${ad}`);
    return r;
  };
  return { acik: zorunlu(acik), koyu: zorunlu((ad) => koyu(ad) ?? acik(ad)) };
}

const TEMALAR = temalariOku("src/stil/belirtecler.css");

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
  ["renk-uyari-metin", "renk-yuzey"], // süre seçeneğindeki ve şube istisnasındaki uyarı satırı
  ["renk-uyari-metin", "renk-zemin"],
  ["renk-bilgi-metin", "renk-bilgi-zemin"],
  ["renk-metin", "renk-sayfa"],
  ["renk-metin-ikincil", "renk-sayfa"],
  ["renk-birincil", "renk-sayfa"],
  ["renk-ust-metin", "renk-ust-zemin"],
  ["renk-ust-metin", "renk-ust-vurgu"],
  ["renk-menu-metin", "renk-menu-zemin"],
  ["renk-menu-metin", "renk-menu-zemin-alt"],
  ["renk-menu-metin", "renk-menu-vurgu"],
  ["renk-menu-aktif-metin", "renk-menu-aktif-zemin"],
  ["renk-menu-aktif-metin", "renk-menu-aktif-zemin-2"],
  // Sayfa başlığı bandı: geçişin her durağında beyaz yazı okunaklı.
  ...["baslangic", "orta", "bitis"].flatMap((d): [string, string][] => [
    ["renk-bant-metin", `renk-bant-${d}`],
    ["renk-bant-metin-ikincil", `renk-bant-${d}`],
  ]),
  ["renk-birincil-koyu", "renk-zemin"], // bandın üstündeki beyaz düğmenin yazısı
  // Sayı kartları: pastel zeminde sayı, ad ve ikon.
  ...[1, 2, 3, 4].flatMap((i): [string, string][] => [
    ["renk-metin", `renk-kart-${i}`],
    ["renk-metin-ikincil", `renk-kart-${i}`],
    [`renk-kart-${i}-vurgu`, `renk-kart-${i}`],
  ]),
  ...[1, 2, 3, 4, 5, 6, 7, 8].map((i): [string, string] => ["renk-cip-metin", `renk-rozet-${i}`]),
  // Giriş sayfasının tanıtım paneli ve örnek çizelgesi.
  ["renk-tanitim-metin", "renk-tanitim-zemin"],
  ["renk-tanitim-ikincil", "renk-tanitim-zemin"],
  ["renk-tanitim-metin", "renk-tanitim-ikon-zemin"],
  ...["mat", "fizik", "turkce", "tarih", "ing", "kimya"].map((d): [string, string] => [`renk-ders-${d}-metin`, `renk-ders-${d}`]),
];

const SINIR_CIFTLERI: [string, string][] = [
  ["renk-kenar-alan", "renk-zemin"],
  ["renk-odak", "renk-zemin"],
  ["renk-tehlike", "renk-zemin"], // hatalı alanın kenarı
];

describe.each(["acik", "koyu"] as const)("renk kontrastı, %s tema", (tema) => {
  const renk = TEMALAR[tema];
  it.each(METIN_CIFTLERI)("metin %s / %s en az 4.5:1", (on, arka) => {
    expect(kontrast(renk(on), renk(arka))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(SINIR_CIFTLERI)("sınır %s / %s en az 3:1", (on, arka) => {
    expect(kontrast(renk(on), renk(arka))).toBeGreaterThanOrEqual(3);
  });
});

/*
 * Ders çipleri: API'nin paletindeki her renk (api/.../ders_renkleri.py, yalnızca okunur) için
 * ders-renkleri.css iki temada da pastel zemin ve okunaklı yazı tanımlar. Palete renk eklenip
 * burası unutulursa test kırılır.
 */
const PALET = [
  ...readFileSync(resolve("../api/src/okulapi/cekirdek/ders_renkleri.py"), "utf-8").matchAll(/\("(#[0-9a-f]{6})", "([^"]+)"\)/g),
].map((m): [string, string] => [m[1] as string, m[2] as string]);
const DERS_TEMALARI = temalariOku("src/stil/ders-renkleri.css");

describe.each(["acik", "koyu"] as const)("ders renkleri, %s tema", (tema) => {
  it("palet okundu", () => {
    expect(PALET.length).toBeGreaterThanOrEqual(20);
  });
  it.each(PALET)("%s (%s) yazı / zemin en az 4.5:1", (hex) => {
    const kod = hex.slice(1);
    const renk = DERS_TEMALARI[tema];
    expect(kontrast(renk(`ders-${kod}-yazi`), renk(`ders-${kod}-zemin`))).toBeGreaterThanOrEqual(4.5);
  });
});

describe("kontrast hesabı", () => {
  it("hesap bilinen değerleri verir", () => {
    expect(kontrast("#000000", "#ffffff")).toBeCloseTo(21, 1);
    expect(kontrast("#777777", "#ffffff")).toBeCloseTo(4.48, 2);
  });
});
