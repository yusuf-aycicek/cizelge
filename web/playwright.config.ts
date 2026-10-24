import { defineConfig, devices } from "@playwright/test";

/**
 * Uçtan uca testler (5.6): çalışan gerçek sisteme karşı (docker compose + Vite, localhost:5173).
 * Sunucuyu test başlatmaz; önce `docker compose up` gerekir. Tarayıcı bilgisayardaki Microsoft
 * Edge'dir (Playwright'ın ayrı tarayıcı indirmesine gerek yok; ekran görüntüsü betiğiyle aynı).
 *
 *   npm run e2e
 *
 * Masaüstü ve telefon projeleri **sırayla** çalışır (workers: 1): ikisi de örnek okulda program
 * üretir ve bir okulun aynı anda tek üretimi olabilir (API 409 verir).
 */
export default defineConfig({
  testDir: "e2e",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  // Program üretimi ("Hızlı", 30 sn) ve kuyruk beklemesi dahil.
  timeout: 180_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: {
    baseURL: process.env.WEB_ADRES ?? "http://localhost:5173",
    channel: "msedge",
    locale: "tr-TR",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "masaustu", use: { viewport: { width: 1366, height: 820 } } },
    // Telefon: dokunmatik (tap) ve dar ekran; haftalık çizelge gün gün görünür.
    { name: "telefon", use: { ...devices["Pixel 7"], channel: "msedge" } },
  ],
});
