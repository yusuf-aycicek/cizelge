// Ekran görüntüleri: çalışan arayüzün (http://localhost:5173) belirli görünümlerini PNG olarak
// docs/ekranlar/<adım>/ altına kaydeder. Tarayıcı olarak bilgisayardaki Microsoft Edge kullanılır
// (Playwright'ın ayrı tarayıcı indirmesine gerek kalmaz).
//
//   node scripts/ekran-goruntusu.mjs 5.1
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const ADRES = process.env.WEB_ADRES ?? "http://localhost:5173";
const adim = process.argv[2] ?? "taslak";
const hedef = resolve("..", "docs", "ekranlar", adim);
mkdirSync(hedef, { recursive: true });

const MASAUSTU = { width: 1366, height: 820 };
const TELEFON = { width: 390, height: 844 };

const GORUNUMLER = {
  "5.1": [
    { dosya: "1-ana-sayfa.png", yol: "/", boyut: MASAUSTU, bekle: "text=✓ Çalışıyor" },
    { dosya: "2-tasarim-temeli.png", yol: "/tasarim", boyut: MASAUSTU, tamSayfa: true },
    {
      dosya: "3-form-hatasi-ve-bildirim.png",
      yol: "/tasarim",
      boyut: MASAUSTU,
      eylem: async (s) => {
        await s.getByRole("button", { name: "Gönder" }).click();
        await s.getByRole("button", { name: "Hata bildirimi" }).click();
        await s.getByRole("heading", { name: "Form alanları" }).scrollIntoViewIfNeeded();
      },
    },
    {
      dosya: "4-onay-penceresi.png",
      yol: "/tasarim",
      boyut: MASAUSTU,
      eylem: async (s) => {
        await s.getByRole("button", { name: "Öğretmeni sil..." }).click();
      },
    },
    {
      dosya: "5-klavye-odagi.png",
      yol: "/tasarim",
      boyut: MASAUSTU,
      eylem: async (s) => {
        await s.getByRole("heading", { name: "Düğmeler" }).scrollIntoViewIfNeeded();
        await s.getByRole("button", { name: "Ayrıntılar" }).focus();
        await s.keyboard.press("Shift+Tab"); // klavyeyle gelindi: odak halkası görünür
      },
    },
    {
      dosya: "6-telefon-menu.png",
      yol: "/",
      boyut: TELEFON,
      bekle: "text=✓ Çalışıyor",
      eylem: async (s) => {
        await s.getByRole("button", { name: /Menü/ }).click();
      },
    },
    { dosya: "7-telefon-tasarim.png", yol: "/tasarim", boyut: TELEFON, tamSayfa: true },
  ],
};

const liste = GORUNUMLER[adim];
if (!liste) {
  console.error(`Bilinmeyen adım: ${adim}. Seçenekler: ${Object.keys(GORUNUMLER).join(", ")}`);
  process.exit(2);
}

const tarayici = await chromium.launch({ channel: "msedge" });
try {
  for (const g of liste) {
    const sayfa = await tarayici.newPage({ viewport: g.boyut, locale: "tr-TR" });
    await sayfa.goto(ADRES + g.yol, { waitUntil: "networkidle" });
    if (g.bekle) await sayfa.waitForSelector(g.bekle);
    if (g.eylem) await g.eylem(sayfa);
    await sayfa.waitForTimeout(300);
    await sayfa.screenshot({ path: resolve(hedef, g.dosya), fullPage: Boolean(g.tamSayfa) });
    console.log(`docs/ekranlar/${adim}/${g.dosya}`);
    await sayfa.close();
  }
} finally {
  await tarayici.close();
}
