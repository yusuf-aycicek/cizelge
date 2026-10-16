// Yatay taşma denetimi: çalışan arayüzün (http://localhost:5173) her sayfası masaüstü ve telefon
// genişliğinde açılır, belgenin genişliği pencereyi aşıyor mu bakılır. Aşan sayfa varsa çıkış
// kodu 1'dir.
//
// Neden ayrı bir betik: jsdom (Vitest) düzeni hesaplamaz; "sayfa telefonda yana kayıyor" gibi
// hatalar ancak gerçek bir tarayıcıda görülür. 5.4'te iki eski hata böyle bulundu (çerçeve ızgarası
// ve tablodaki görünmez başlık).
//
//   node scripts/tasma-denetimi.mjs
import { chromium } from "playwright-core";

const ADRES = process.env.WEB_ADRES ?? "http://localhost:5173";
const BOYUTLAR = [["masaüstü", { width: 1366, height: 820 }], ["telefon", { width: 390, height: 844 }]];
const SAYFALAR = ["/", "/hesabim", "/okul", "/ogretmenler", "/siniflar", "/dersler", "/seviye-sablonu",
  "/ders-dagilimi", "/ders-dagilimi?gorunum=ogretmen", "/ders-dagilimi?gorunum=ders"];

const tarayici = await chromium.launch({ channel: "msedge" });
let tasan = 0;
try {
  const baglam = await tarayici.newContext({ locale: "tr-TR" });
  const istek = async (yontem, yol, data) => {
    const y = await baglam.request.fetch(ADRES + yol, { method: yontem, headers: { Origin: ADRES }, data });
    if (!y.ok()) throw new Error(`${yontem} ${yol}: ${y.status()} ${await y.text()}`);
    return y.json();
  };
  // Uzun adlı kayıtlar: taşma en çok uzun metinle ortaya çıkar.
  await istek("POST", "/api/kayit", {
    okul: { ad: "Mustafa Kemal Atatürk Fen ve Teknoloji Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
    ad: "Denetim", email: `tasma-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi",
  });
  const sinif = await istek("POST", "/api/siniflar", { ad: "9-A", seviye: 9 });
  await istek("POST", "/api/ogretmenler", { ad: "Ayşe Gülşen Yılmaz-Karaosmanoğlu", brans: "Matematik Öğretmeni ve Rehberlik" });
  for (const ad of ["Matematik", "Türk Dili ve Edebiyatı", "Din Kültürü ve Ahlak Bilgisi"]) {
    const ders = await istek("POST", "/api/dersler", { ad, kisa_ad: ad.slice(0, 3) });
    await istek("POST", "/api/ders-programi/atamalar", { sinif_id: sinif.id, ders_id: ders.id, haftalik_saat: 4 });
    await istek("POST", "/api/ders-programi/seviye-sablonlari", { seviye: 9, ders_id: ders.id, haftalik_saat: 4 });
  }

  for (const [ad, boyut] of BOYUTLAR) {
    const sayfa = await baglam.newPage();
    await sayfa.setViewportSize(boyut);
    for (const yol of SAYFALAR) {
      await sayfa.goto(ADRES + yol);
      await sayfa.waitForLoadState("networkidle");
      await sayfa.waitForTimeout(300);
      const [belge, pencere] = await sayfa.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
      if (belge > pencere) tasan++;
      console.log(`${belge > pencere ? "TAŞIYOR" : "tamam  "} ${ad.padEnd(8)} ${yol}  (${belge}/${pencere} px)`);
    }
  }
} finally {
  await tarayici.close();
}
process.exit(tasan ? 1 : 0);
