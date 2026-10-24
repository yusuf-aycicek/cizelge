// Yatay taşma denetimi: çalışan arayüzün (http://localhost:5173) her sayfası masaüstü, 800 px ve
// telefon genişliğinde açılır; belgenin genişliği pencereyi aşıyor mu, masaüstü ve 800 px'te ayrıca
// bir kutu kendi içinde yana kayıyor mu bakılır. Sorun varsa çıkış kodu 1'dir.
//
// Neden ayrı bir betik: jsdom (Vitest) düzeni hesaplamaz; "sayfa telefonda yana kayıyor" gibi
// hatalar ancak gerçek bir tarayıcıda görülür. 5.4'te iki eski hata böyle bulundu (çerçeve ızgarası
// ve tablodaki görünmez başlık).
//
//   node scripts/tasma-denetimi.mjs
import { chromium } from "playwright-core";
import { denemeOkullariniTemizle } from "./deneme-temizle.mjs";

const ADRES = process.env.WEB_ADRES ?? "http://localhost:5173";
// 800 px: küçük dizüstü ya da yarım ekran pencere; menü hâlâ yanda, içerik alanı en dar halinde
// (programlar tablosu burada taşıyordu, kullanıcı bildirdi).
const BOYUTLAR = [["masaüstü", { width: 1366, height: 820 }], ["800 px", { width: 800, height: 900 }],
  ["telefon", { width: 390, height: 844 }]];
const SAYFALAR = ["/", "/hesabim", "/okul", "/ogretmenler", "/siniflar", "/dersler", "/seviye-sablonu", "/kullanicilar",
  "/ders-dagilimi", "/ders-dagilimi?gorunum=ogretmen", "/ders-dagilimi?gorunum=ders", "/program"];
// Hazır bir programın çizelgesi de denetlenir; yolu program üretilince eklenir.

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
    okul: { ad: "Çizelge Örnek Fen ve Teknoloji Anadolu Lisesi Deneme Okulu", gun_sayisi: 5, gunluk_ders_saati: 8 },
    ad: "Denetim", email: `tasma-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi",
  });
  const sinif = await istek("POST", "/api/siniflar", { ad: "9-A", seviye: 9 });
  const ogretmen = await istek("POST", "/api/ogretmenler", { ad: "Ayşe Gülşen Yılmaz-Karaosmanoğlu", brans: "Matematik Öğretmeni ve Rehberlik" });
  for (const ad of ["Matematik", "Türk Dili ve Edebiyatı", "Din Kültürü ve Ahlak Bilgisi"]) {
    const ders = await istek("POST", "/api/dersler", { ad, kisa_ad: ad.slice(0, 3) });
    await istek("POST", "/api/ders-programi/atamalar", { sinif_id: sinif.id, ders_id: ders.id, ogretmen_id: ogretmen.id, haftalik_saat: 4 });
    await istek("POST", "/api/ders-programi/seviye-sablonlari", { seviye: 9, ders_id: ders.id, haftalik_saat: 4 });
  }

  // Şube grubu, grubun şablonu ve şube istisnası (K5): uzun adla. 9-B şablonu kullanır, 9-A grupta.
  const grup = await istek("POST", "/api/sube-gruplari", { ad: "9 Fen Bilimleri ve Matematik Ağırlıklı Grup", seviye: 9 });
  await istek("PATCH", `/api/siniflar/${sinif.id}`, { sube_grubu_id: grup.id });
  const sinifB = await istek("POST", "/api/siniflar", { ad: "9-B", seviye: 9 });
  const ekDers = await istek("POST", "/api/dersler", { ad: "Felsefe ve Mantık Bilimine Giriş", kisa_ad: "FEL" });
  await istek("POST", "/api/ders-programi/seviye-sablonlari", { seviye: 9, sube_grubu_id: grup.id, ders_id: ekDers.id, haftalik_saat: 2 });
  await istek("POST", "/api/ders-programi/istisnalar", { sinif_id: sinifB.id, ders_id: ekDers.id, tur: "ek", haftalik_saat: 2 });
  const sablonSatiri = (await istek("GET", "/api/ders-programi/seviye-sablonlari")).find((s) => !s.sube_grubu_id);
  await istek("POST", "/api/ders-programi/istisnalar", { sinif_id: sinifB.id, ders_id: sablonSatiri.ders_id, tur: "almaz" });
  const ekAtama = (await istek("GET", "/api/ders-programi/atamalar")).find((a) => a.sinif_id === sinifB.id);
  await istek("PATCH", `/api/ders-programi/atamalar/${ekAtama.id}`, { ogretmen_id: ogretmen.id });
  SAYFALAR.push(`/seviye-sablonu?seviye=9&grup=${grup.id}`, `/ders-dagilimi?gorunum=sube&sinif=${sinifB.id}`);

  // Programlar tablosunda "Çizelgeyi aç" bağlantısı yalnızca hazır programda çıkar: bir tane üretilir
  // (worker çalışıyor olmalı; bu küçük okul bir saniyede çözülür).
  const program = await istek("POST", "/api/ders-programi/programlar",
    { ad: "Güz dönemi programı (ikinci deneme, uzun adlı)", sure_siniri_sn: 5 });
  for (let i = 0; ; i++) {
    const durum = (await istek("GET", `/api/ders-programi/programlar/${program.id}`)).durum;
    if (durum === "hazir") break;
    if (durum === "basarisiz" || i > 60) throw new Error(`Denetim programı üretilemedi: ${durum}`);
    await new Promise((r) => setTimeout(r, 500));
  }
  SAYFALAR.push(`/program/${program.id}`, `/program/${program.id}?gorunum=ogretmen`);
  SAYFALAR.push(`/ogretmenler/${ogretmen.id}`);

  for (const [ad, boyut] of BOYUTLAR) {
    const sayfa = await baglam.newPage();
    await sayfa.setViewportSize(boyut);
    for (const yol of SAYFALAR) {
      await sayfa.goto(ADRES + yol);
      await sayfa.waitForLoadState("networkidle");
      await sayfa.waitForTimeout(300);
      const [belge, pencere] = await sayfa.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
      // Sayfa taşmasa da bir kutu kendi içinde yana kayabilir (ör. tablo kutusu: overflow-x auto).
      // Telefonda geniş tabloların kayması kabul edilir; masaüstü ve 800 px'te edilmez. Bilerek kayan
      // kutular (haftalık çizelge) data-kaydirilabilir ile işaretlidir.
      const kayanlar = ad === "telefon" ? [] : await sayfa.evaluate(() =>
        [...document.querySelectorAll("body *")]
          .filter((e) => ["auto", "scroll"].includes(getComputedStyle(e).overflowX))
          .filter((e) => !e.closest("[data-kaydirilabilir]") && e.scrollWidth > e.clientWidth + 1)
          .map((e) => `${e.tagName.toLowerCase()}.${[...e.classList].join(".")} ${e.scrollWidth}/${e.clientWidth}`));
      const sorun = belge > pencere || kayanlar.length > 0;
      if (sorun) tasan++;
      // TASMA_GORUNTU=klasör: sorunlu sayfanın tam görüntüsü oraya kaydedilir (nedeni görmek için).
      if (sorun && process.env.TASMA_GORUNTU) {
        const dosya = `${ad}-${yol}`.replace(/[^a-z0-9]+/gi, "_") + ".png";
        await sayfa.screenshot({ path: `${process.env.TASMA_GORUNTU}/${dosya}`, fullPage: true });
      }
      console.log(`${sorun ? "TAŞIYOR" : "tamam  "} ${ad.padEnd(8)} ${yol}  (${belge}/${pencere} px)`
        + (kayanlar.length ? `  iç kaydırma: ${kayanlar.join(", ")}` : ""));
    }
  }
} finally {
  await tarayici.close();
  denemeOkullariniTemizle();
}
process.exit(tasan ? 1 : 0);
