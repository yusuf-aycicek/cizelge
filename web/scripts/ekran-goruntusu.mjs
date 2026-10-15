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

// Akışlar: tek bir tarayıcı oturumunda (çerez korunur) sırayla ilerleyen görünümler.
const AKISLAR = {
  "5.2": async (tarayici, kaydet) => {
    const email = `ekran-${Date.now()}@ornek.test`;
    const parola = "ekran-goruntusu-parolasi";
    const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
    const s = await baglam.newPage();

    await s.goto(ADRES + "/ogretmenler");
    await s.getByRole("heading", { name: "Giriş yap" }).waitFor();
    await kaydet(s, "1-giris.png");

    await s.getByLabel("E-posta").fill("kimse@ornek.test");
    await s.getByLabel("Parola").fill("yanlis-parola-1234");
    await s.getByRole("button", { name: "Giriş yap" }).click();
    await s.getByText("E-posta ya da parola hatalı").waitFor();
    await kaydet(s, "2-giris-hatali.png");

    await s.getByRole("link", { name: "Okulunuzu kaydedin" }).click();
    await s.getByLabel(/Okulun adı/).fill("Atatürk Anadolu Lisesi");
    await s.getByLabel(/Adınız ve soyadınız/).fill("Ayşe Yılmaz");
    await s.getByLabel(/^Parola/).first().fill("kisa");
    await s.getByLabel(/Parola \(tekrar\)/).fill("baska");
    await s.getByRole("button", { name: "Okulu kaydet" }).click();
    await kaydet(s, "3-kayit-hatalari.png", true);

    await s.getByLabel(/E-posta/).fill(email);
    await s.getByLabel(/^Parola/).first().fill(parola);
    await s.getByLabel(/Parola \(tekrar\)/).fill(parola);
    await kaydet(s, "4-kayit-dolu.png", true);
    await s.getByRole("button", { name: "Okulu kaydet" }).click();
    await s.getByRole("heading", { name: "Hoş geldiniz" }).waitFor();
    await s.getByText("✓ Çalışıyor").waitFor();
    await kaydet(s, "5-kayit-sonrasi-ana-sayfa.png");

    await s.getByRole("link", { name: /Ayşe Yılmaz/ }).click();
    await s.getByRole("heading", { name: "Hesabım" }).waitFor();
    await s.getByLabel("Mevcut parola").fill("yanlis-parola-1234");
    await s.getByLabel(/^Yeni parola/).first().fill("yepyeni-parola-2026");
    await s.getByLabel(/Yeni parola \(tekrar\)/).fill("yepyeni-parola-2026");
    await s.getByRole("button", { name: "Parolayı değiştir" }).click();
    await s.getByText("Mevcut parola hatalı").waitFor();
    await kaydet(s, "6-hesabim-hatali-parola.png", true);

    await s.getByRole("button", { name: "Çıkış" }).click();
    await s.getByText("Çıkış yaptınız.").waitFor();
    await kaydet(s, "7-cikis.png");

    const telefon = await baglam.newPage();
    await telefon.setViewportSize(TELEFON);
    await telefon.goto(ADRES + "/giris");
    await telefon.getByLabel("E-posta").fill(email);
    await telefon.getByLabel("Parola").fill(parola);
    await telefon.getByRole("button", { name: "Giriş yap" }).click();
    await telefon.getByText("✓ Çalışıyor").waitFor();
    await kaydet(telefon, "8-telefon-giris-sonrasi.png");
    await baglam.close();
  },
};

const liste = GORUNUMLER[adim];
const akis = AKISLAR[adim];
if (!liste && !akis) {
  console.error(`Bilinmeyen adım: ${adim}. Seçenekler: ${[...Object.keys(GORUNUMLER), ...Object.keys(AKISLAR)].join(", ")}`);
  process.exit(2);
}

const tarayici = await chromium.launch({ channel: "msedge" });
if (akis) {
  try {
    await akis(tarayici, async (sayfa, dosya, tamSayfa = false) => {
      await sayfa.waitForTimeout(300);
      await sayfa.screenshot({ path: resolve(hedef, dosya), fullPage: tamSayfa });
      console.log(`docs/ekranlar/${adim}/${dosya}`);
    });
  } finally {
    await tarayici.close();
  }
  process.exit(0);
}
try {
  // Sayfalar giriş ister (5.2'den beri): görüntüler için geçici bir okul kaydedilir; oturum
  // çerezi bu tarayıcı bağlamındaki bütün sayfalarda geçerlidir.
  const baglam = await tarayici.newContext({ locale: "tr-TR" });
  const kayit = await baglam.request.post(ADRES + "/api/kayit", {
    headers: { Origin: ADRES },
    data: { okul: { ad: "Atatürk Anadolu Lisesi" }, ad: "Ayşe Yılmaz", email: `ekran-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi" },
  });
  if (!kayit.ok()) throw new Error(`Ekran görüntüsü için kayıt başarısız: ${kayit.status()} ${await kayit.text()}`);
  for (const g of liste) {
    const sayfa = await baglam.newPage();
    await sayfa.setViewportSize(g.boyut);
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
