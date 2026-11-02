// Ekran görüntüleri: çalışan arayüzün (http://localhost:5173) belirli görünümlerini PNG olarak
// docs/ekranlar/<adım>/ altına kaydeder. Tarayıcı olarak bilgisayardaki Microsoft Edge kullanılır
// (Playwright'ın ayrı tarayıcı indirmesine gerek kalmaz).
//
//   node scripts/ekran-goruntusu.mjs 5.1
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "playwright-core";
import { denemeOkullariniTemizle } from "./deneme-temizle.mjs";

const ADRES = process.env.WEB_ADRES ?? "http://localhost:5173";
const adim = process.argv[2] ?? "taslak";
// İkinci argüman "koyu" ise cihaz koyu temada sayılır (prefers-color-scheme: dark); görüntüler
// docs/ekranlar/<adım>-koyu/ altına gider.
const koyu = process.argv[3] === "koyu";
const klasor = koyu ? `${adim}-koyu` : adim;
const hedef = resolve("..", "docs", "ekranlar", klasor);
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
    await s.getByRole("heading", { name: "Tekrar hoş geldiniz" }).waitFor();
    await kaydet(s, "1-giris.png");

    await s.getByLabel("E-posta").fill("kimse@ornek.test");
    await s.getByLabel("Parola").fill("yanlis-parola-1234");
    await s.getByRole("button", { name: "Giriş yap" }).click();
    await s.getByText("E-posta ya da parola hatalı").waitFor();
    await kaydet(s, "2-giris-hatali.png");

    await s.getByRole("link", { name: "Okulunuzu kaydedin" }).click();
    await s.getByLabel(/Okulun adı/).fill("Çizelge Örnek Anadolu Lisesi");
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
    await s.getByRole("heading", { name: "Hoş geldiniz", exact: true }).waitFor();
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

AKISLAR["5.3"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const istek = async (yontem, yol, data) => {
    const y = await baglam.request.fetch(ADRES + yol, { method: yontem, headers: { Origin: ADRES }, data });
    if (!y.ok()) throw new Error(`${yontem} ${yol}: ${y.status()} ${await y.text()}`);
    return y.json();
  };
  await istek("POST", "/api/kayit", {
    okul: { ad: "Çizelge Örnek Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
    ad: "Ayşe Yılmaz", email: `ekran-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi",
  });
  const s = await baglam.newPage();

  await s.goto(ADRES + "/ogretmenler");
  await s.getByRole("heading", { name: "Henüz öğretmen eklenmedi" }).waitFor();
  await kaydet(s, "1-ogretmenler-bos.png");

  const ogretmenler = {};
  for (const [ad, brans] of [["Zeynep Demir", "Fizik"], ["Çağla Öz", "Kimya"], ["Şule Kaya", "Matematik"],
    ["İsmail Er", "Tarih"], ["Ömer Can", "Coğrafya"], ["Ali Çelik", "İngilizce"], ["Ümit Kara", "Biyoloji"],
    ["Gül Ay", "Türk Dili ve Edebiyatı"], ["Irmak Su", "Beden Eğitimi"]]) {
    ogretmenler[ad] = (await istek("POST", "/api/ogretmenler", { ad, brans })).id;
  }
  const siniflar = {};
  for (const ad of ["10-A", "9-B", "9-A", "11-A"]) siniflar[ad] = (await istek("POST", "/api/siniflar", { ad, seviye: Number(ad.split("-")[0]) })).id;
  const mat = (await istek("POST", "/api/dersler", { ad: "Matematik", kisa_ad: "MAT" })).id;
  for (const sinif of ["9-A", "9-B"]) {
    await istek("POST", "/api/ders-programi/atamalar", { sinif_id: siniflar[sinif], ders_id: mat, ogretmen_id: ogretmenler["Şule Kaya"], haftalik_saat: 6 });
  }
  for (const [gun, saat] of [[4, 7], [0, 7], [2, 7]]) {
    await istek("POST", "/api/ders-programi/musaitlikler", { ogretmen_id: ogretmenler["Ali Çelik"], gun, saat, durum: "gelemez" });
  }

  await s.reload();
  await s.getByRole("table", { name: "Öğretmenler" }).waitFor();
  await kaydet(s, "2-ogretmenler-turkce-sirali.png", true);

  await s.getByRole("button", { name: "Ali Çelik düzenle" }).click();
  await kaydet(s, "3-satirda-duzenleme.png");
  await s.keyboard.press("Escape");

  await s.getByRole("button", { name: "Şule Kaya sil" }).click();
  await kaydet(s, "4-silme-onayi.png");
  await s.getByRole("dialog").getByRole("button", { name: "Sil" }).click();
  await s.getByText(/Şule Kaya silinemez/).waitFor();
  await kaydet(s, "5-silinemez-aciklamasi.png");

  await s.goto(ADRES + "/siniflar");
  await s.getByRole("table", { name: "Sınıflar" }).waitFor();
  await kaydet(s, "6-siniflar.png");

  await s.goto(ADRES + "/okul");
  await s.getByRole("heading", { name: "Kurallar", exact: true }).waitFor();
  await kaydet(s, "7-okul-ayarlari.png", true);

  await s.getByLabel(/Günde kaç ders saati/).fill("7");
  await s.getByRole("note").waitFor();
  await kaydet(s, "8-azaltma-uyarisi.png");
  await s.getByRole("button", { name: "Kaydet", exact: true }).click();
  await s.getByRole("dialog", { name: "Bu değişiklik mevcut kayıtları etkileyecek" }).waitFor();
  await kaydet(s, "9-azaltma-etkileri.png");
  await s.getByRole("dialog").getByRole("button", { name: "Vazgeç" }).click();

  await s.getByText("Gelişmiş: kuralların önemi").click();
  await s.getByRole("group", { name: "Öğretmene boş gün" }).getByRole("radio", { name: "Çok önemli" }).check();
  await s.getByRole("heading", { name: "Gelişmiş: kuralların önemi" }).scrollIntoViewIfNeeded();
  await kaydet(s, "10-kurallarin-onemi.png", true);

  const telefon = await baglam.newPage();
  await telefon.setViewportSize(TELEFON);
  await telefon.goto(ADRES + "/ogretmenler");
  await telefon.getByRole("table", { name: "Öğretmenler" }).waitFor();
  await kaydet(telefon, "11-telefon-ogretmenler.png", true);
  await baglam.close();
};

AKISLAR["5.4"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const istek = async (yontem, yol, data) => {
    const y = await baglam.request.fetch(ADRES + yol, { method: yontem, headers: { Origin: ADRES }, data });
    if (!y.ok()) throw new Error(`${yontem} ${yol}: ${y.status()} ${await y.text()}`);
    return y.json();
  };
  await istek("POST", "/api/kayit", {
    okul: { ad: "Çizelge Örnek Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
    ad: "Ayşe Yılmaz", email: `ekran-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi",
  });
  const o = {};
  for (const [ad, brans] of [["Zeynep Demir", "Fizik"], ["Çağla Öz", "Kimya"], ["Şule Kaya", "Matematik"],
    ["Ayşe Yılmaz", "Matematik Öğretmeni"], ["Ali Çelik", "İngilizce"], ["Gül Ay", "Edebiyat"],
    ["Ömer Can", "Coğrafya"], ["Irmak Su", "Beden Eğitimi"]]) {
    o[ad] = (await istek("POST", "/api/ogretmenler", { ad, brans })).id;
  }
  const s = {};
  for (const ad of ["9-A", "9-B", "9-C", "10-A", "10-B"]) s[ad] = (await istek("POST", "/api/siniflar", { ad, seviye: Number(ad.split("-")[0]) })).id;
  const d = {};
  for (const [ad, kisa_ad] of [["Matematik", "MAT"], ["Fizik", "FİZ"], ["Kimya", "KİM"], ["İngilizce", "İNG"],
    ["Türk Dili ve Edebiyatı", "TDE"], ["Coğrafya", "COĞ"], ["Beden Eğitimi", "BED"]]) {
    d[ad] = (await istek("POST", "/api/dersler", { ad, kisa_ad })).id;
  }
  const DP = "/api/ders-programi";
  // Şablondan önce elle eklenmiş, saati şablondan farklı bir ders: rapor bunu gösterecek.
  await istek("POST", `${DP}/atamalar`, { sinif_id: s["9-B"], ders_id: d["Matematik"], haftalik_saat: 6 });
  for (const [ders, saat] of [["Matematik", 5], ["Fizik", 3], ["Kimya", 2], ["İngilizce", 4],
    ["Türk Dili ve Edebiyatı", 5], ["Coğrafya", 2], ["Beden Eğitimi", 2]]) {
    await istek("POST", `${DP}/seviye-sablonlari`, { seviye: 9, ders_id: d[ders], haftalik_saat: saat });
  }
  // Zeynep yalnızca cuma müsait: 8 saat.
  for (let gun = 0; gun < 4; gun++) for (let saat = 0; saat < 8; saat++) {
    await istek("POST", `${DP}/musaitlikler`, { ogretmen_id: o["Zeynep Demir"], gun, saat, durum: "gelemez" });
  }
  // 10-A: kapasiteyi aşan şube (42 saat > 40).
  await istek("POST", `${DP}/atamalar`, { sinif_id: s["10-A"], ders_id: d["Matematik"], ogretmen_id: o["Ayşe Yılmaz"], haftalik_saat: 22 });
  await istek("POST", `${DP}/atamalar`, { sinif_id: s["10-A"], ders_id: d["Türk Dili ve Edebiyatı"], ogretmen_id: o["Gül Ay"], haftalik_saat: 20 });

  const p = await baglam.newPage();
  await p.goto(ADRES + "/seviye-sablonu?seviye=9");
  await p.getByRole("table", { name: "9. sınıf şablonu" }).waitFor();
  await kaydet(p, "1-seviye-sablonu.png", true);

  await p.getByRole("button", { name: "9. sınıf şubelerine uygula" }).click();
  await p.getByRole("heading", { name: "Şablon uygulandı" }).waitFor();
  await p.getByRole("heading", { name: "Şubelere uygula" }).evaluate((e) => e.scrollIntoView({ block: "start" }));
  await kaydet(p, "2-sablon-raporu.png");

  await p.goto(ADRES + "/ders-dagilimi");
  await p.getByRole("heading", { name: "9-A şubesinin dersleri" }).waitFor();
  await kaydet(p, "3-sube-gorunumu.png", true);

  // Açık <select> listesi işletim sisteminin penceresidir, ekran görüntüsüne girmez. Görüntü için
  // seçici geçici olarak liste kutusu (size) yapılır; gruplar ve yükler aynen görünür.
  // Rolle değil öznitelikle bulunur: size verilince rol combobox'tan listbox'a döner.
  const secici = p.locator('select[aria-label="9-A Matematik öğretmeni"]');
  await secici.evaluate((e) => e.scrollIntoView({ block: "center" }));
  await secici.evaluate((e) => { e.size = 11; e.style.position = "relative"; e.style.zIndex = "5"; e.style.background = "white"; });
  await kaydet(p, "4-ogretmen-secici.png");
  await secici.evaluate((e) => { e.size = 0; e.removeAttribute("style"); });
  await secici.selectOption(o["Şule Kaya"]);
  await p.getByText("9-A Matematik: Şule Kaya seçildi.").waitFor();

  await p.getByRole("tab", { name: "Derslere göre" }).click();
  await p.getByRole("combobox", { name: "Ders" }).selectOption(d["Fizik"]);
  await p.getByRole("checkbox", { name: "Bütün şubeleri işaretle" }).check();
  await p.getByRole("combobox", { name: "İşaretli şubelere verilecek öğretmen" }).selectOption(o["Zeynep Demir"]);
  await kaydet(p, "5-derse-gore-toplu-secim.png");
  await p.getByRole("button", { name: "İşaretli 3 şubeye ver" }).click();
  await p.getByText(/Fizik dersinin öğretmeni 3 şubede/).waitFor();
  await p.getByText("Zeynep Demir'in 9 saat dersi var, müsait olduğu 8 saat var.").first().waitFor();
  await kaydet(p, "6-toplu-atama-ve-asim-uyarisi.png");

  await p.getByRole("tab", { name: "Öğretmenlere göre" }).click();
  await p.getByRole("button", { name: /Derslerini göster/ }).first().click();
  await kaydet(p, "7-ogretmen-yukleri.png", true);

  await p.goto(ADRES + `/ders-dagilimi?gorunum=sube&sinif=${s["10-A"]}`);
  await p.getByRole("heading", { name: "10-A şubesinin dersleri" }).waitFor();
  await kaydet(p, "8-sube-kapasite-asimi.png");

  const telefon = await baglam.newPage();
  await telefon.setViewportSize(TELEFON);
  await telefon.goto(ADRES + `/ders-dagilimi?gorunum=sube&sinif=${s["9-B"]}`);
  await telefon.getByRole("heading", { name: "9-B şubesinin dersleri" }).waitFor();
  await kaydet(telefon, "9-telefon-ders-dagilimi.png", true);
  await baglam.close();
};

// Örnek okulla (python -m okulapi ornek-okul) ana ekranlar. İki tasarım yönü karşılaştırılırken
// kullanıldı (docs/ekranlar/tasarim/); seçimden sonra tek tasarımla.
// Önce: cd api && OKULAPI_ORTAM=gelistirme .venv/Scripts/python -m okulapi ornek-okul --evet
AKISLAR["tasarim"] = async (tarayici, kaydet) => {
  for (const tema of ["a"]) {
    const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
    const s = await baglam.newPage();
    await s.goto(ADRES + "/giris");
    await s.getByRole("heading", { name: "Tekrar hoş geldiniz" }).waitFor();
    await kaydet(s, `${tema}-1-giris.png`);
    await s.getByLabel("E-posta").fill("mudur@ornek.test");
    await s.getByLabel("Parola").fill("ornek-okul-parolasi");
    await s.getByRole("button", { name: "Giriş yap" }).click();
    await s.getByText("✓ Çalışıyor").waitFor();
    await kaydet(s, `${tema}-2-ana-sayfa.png`);
    await s.goto(ADRES + "/ogretmenler");
    await s.getByRole("table", { name: "Öğretmenler" }).waitFor();
    await kaydet(s, `${tema}-3-ogretmenler.png`);
    await s.goto(ADRES + "/okul");
    await s.getByRole("heading", { name: "Kurallar", exact: true }).waitFor();
    await kaydet(s, `${tema}-4-okul-ayarlari.png`);
    await s.goto(ADRES + "/ders-dagilimi");
    await s.getByRole("tab", { name: "Şubelere göre" }).waitFor();
    await s.getByRole("table").first().waitFor();
    await kaydet(s, `${tema}-5-ders-dagilimi.png`);
    await baglam.close();
  }
};

// Seçilen tasarım (A, sıcak ve yumuşak) bütün ekranlarda, masaüstü ve telefon. Örnek okulla.
// Önce: cd api && OKULAPI_ORTAM=gelistirme .venv/Scripts/python -m okulapi ornek-okul --evet
AKISLAR["tasarim-a"] = async (tarayici, kaydet) => {
  const girisYap = async (s) => {
    await s.goto(ADRES + "/giris");
    await s.getByLabel("E-posta").fill("mudur@ornek.test");
    await s.getByLabel("Parola").fill("ornek-okul-parolasi");
    await s.getByRole("button", { name: "Giriş yap" }).click();
    await s.getByRole("img", { name: /Kurulum:/ }).waitFor();
  };
  const bekle = (s, ms = 1000) => s.waitForTimeout(ms); // giriş animasyonları otursun

  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const s = await baglam.newPage();
  await s.goto(ADRES + "/giris");
  await s.getByRole("heading", { name: "Tekrar hoş geldiniz" }).waitFor();
  await kaydet(s, "01-giris.png");
  await girisYap(s);
  await bekle(s);
  await kaydet(s, "02-ana-sayfa.png", true);

  for (const [yol, dosya, hazir] of [
    ["/ogretmenler", "03-ogretmenler.png", () => s.getByRole("table", { name: "Öğretmenler" })],
    ["/siniflar", "04-siniflar.png", () => s.getByRole("table", { name: "Sınıflar" })],
    ["/dersler", "05-dersler.png", () => s.getByRole("table", { name: "Dersler" })],
  ]) {
    await s.goto(ADRES + yol);
    await hazir().waitFor();
    await bekle(s, 600);
    await kaydet(s, dosya, true);
  }
  await s.getByText("Lacivert").first().click();
  await s.getByRole("radiogroup").first().waitFor();
  await kaydet(s, "06-ders-rengi-secici.png");
  await s.keyboard.press("Escape");

  await s.goto(ADRES + "/okul");
  await s.getByRole("heading", { name: "Kurallar", exact: true }).waitFor();
  await bekle(s, 600);
  await kaydet(s, "07-okul-ayarlari.png");
  await s.goto(ADRES + "/seviye-sablonu");
  await s.getByRole("table").first().waitFor();
  await bekle(s, 600);
  await kaydet(s, "08-seviye-sablonu.png", true);
  await s.goto(ADRES + "/ders-dagilimi");
  await s.getByRole("table").first().waitFor();
  await bekle(s, 600);
  await kaydet(s, "09-ders-dagilimi-subeler.png", true);
  await s.getByRole("tab", { name: "Öğretmenlere göre" }).click();
  await s.getByRole("button", { name: /Derslerini göster/ }).first().click();
  await bekle(s, 600);
  await kaydet(s, "10-ders-dagilimi-ogretmenler.png", true);
  await s.getByRole("tab", { name: "Derslere göre" }).click();
  await s.getByRole("table").first().waitFor();
  await bekle(s, 600);
  await kaydet(s, "11-ders-dagilimi-dersler.png");

  // Boş durum: yeni, boş bir okul.
  const bos = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const kayit = await bos.request.post(ADRES + "/api/kayit", {
    headers: { Origin: ADRES },
    data: { okul: { ad: "Yeni Ortaokul" }, ad: "Deneme Müdür", email: `bos-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi" },
  });
  if (!kayit.ok()) throw new Error(`Boş okul kaydı: ${kayit.status()}`);
  const b = await bos.newPage();
  await b.goto(ADRES + "/ogretmenler");
  await b.getByRole("heading", { name: "Henüz öğretmen eklenmedi" }).waitFor();
  await bekle(b, 600);
  await kaydet(b, "12-bos-ogretmenler.png");
  await bos.close();

  const telefon = await baglam.newPage();
  await telefon.setViewportSize(TELEFON);
  for (const [yol, dosya] of [["/", "13-telefon-ana-sayfa.png"], ["/ogretmenler", "14-telefon-ogretmenler.png"],
    ["/dersler", "15-telefon-dersler.png"], ["/ders-dagilimi", "16-telefon-ders-dagilimi.png"]]) {
    await telefon.goto(ADRES + yol);
    await telefon.waitForLoadState("networkidle");
    await bekle(telefon);
    await kaydet(telefon, dosya, true);
  }
  await baglam.close();
};

// Yapım sırası 6.1-6.2: örnek okulda gerçek bir program üretimi, bekleme ekranı, çizelge, hata örneği.
// Önce: cd api && OKULAPI_ORTAM=gelistirme .venv/Scripts/python -m okulapi ornek-okul --evet
AKISLAR["6"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const s = await baglam.newPage();
  await s.goto(ADRES + "/giris");
  await s.getByLabel("E-posta").fill("mudur@ornek.test");
  await s.getByLabel("Parola").fill("ornek-okul-parolasi");
  await s.getByRole("button", { name: "Giriş yap" }).click();
  await s.getByRole("img", { name: /Kurulum:/ }).waitFor();
  await s.waitForTimeout(1200);
  await kaydet(s, "01-ana-sayfa-program-oncesi.png", true);

  await s.goto(ADRES + "/program");
  await s.getByRole("button", { name: "Programı oluştur" }).waitFor();
  await s.waitForTimeout(600);
  await kaydet(s, "02-program-olustur.png");
  await s.getByRole("textbox", { name: "Programın adı" }).fill("Güz dönemi programı");
  await s.getByRole("button", { name: "Programı oluştur" }).click();
  // Mini sette çözücü en iyi sonucu bir saniyeden kısa sürede kanıtlar; bekleme ekranı için "6-bekleme".
  await s.getByRole("heading", { name: "“Güz dönemi programı” hazır" }).waitFor({ timeout: 240_000 });
  await s.waitForTimeout(800);
  await kaydet(s, "05-program-hazir.png", true);

  await s.getByRole("link", { name: "Haftalık çizelgeyi aç" }).click();
  await s.getByRole("table", { name: /haftalık programı/ }).waitFor();
  await s.waitForTimeout(400);
  await kaydet(s, "06-cizelge-yerlesiyor.png"); // hücreler sırayla yerleşirken
  await s.waitForTimeout(1200);
  await kaydet(s, "07-cizelge-sube.png", true);
  await s.getByRole("tab", { name: "Öğretmene göre" }).click();
  await s.getByRole("table", { name: /haftalık programı/ }).waitFor();
  await s.waitForTimeout(1200);
  await kaydet(s, "08-cizelge-ogretmen.png", true);

  await s.goto(ADRES + "/");
  await s.getByRole("img", { name: /Kurulum:/ }).waitFor();
  await s.waitForTimeout(1200);
  await kaydet(s, "09-ana-sayfa-program-sonrasi.png");

  const telefon = await baglam.newPage();
  await telefon.setViewportSize(TELEFON);
  await telefon.goto(ADRES + "/program");
  await telefon.getByRole("link", { name: "Haftalık çizelgeyi aç" }).click();
  await telefon.getByRole("table", { name: /haftalık programı/ }).waitFor();
  await telefon.waitForTimeout(1500);
  await kaydet(telefon, "10-telefon-cizelge.png", true);
  await telefon.close();

  // Hata örneği: günlük ders sınırı geçici olarak 1 (6 saatlik Matematik 5 güne sığmaz).
  const istek = async (yontem, yol, data) => {
    const y = await baglam.request.fetch(ADRES + yol, { method: yontem, headers: { Origin: ADRES }, data });
    if (!y.ok()) throw new Error(`${yontem} ${yol}: ${y.status()} ${await y.text()}`);
  };
  await istek("PUT", "/api/ders-programi/kurallar/gunluk_ders_siniri", { parametreler: { n: 1 } });
  try {
    await s.goto(ADRES + "/program");
    await s.getByRole("radio", { name: /Hızlı/ }).check();
    await s.getByRole("textbox", { name: "Programın adı" }).fill("Deneme");
    await s.getByRole("button", { name: "Programı oluştur" }).click();
    await s.getByRole("heading", { name: "“Deneme” oluşturulamadı" }).waitFor({ timeout: 120_000 });
    await s.waitForTimeout(800);
    await kaydet(s, "11-program-olusturulamadi.png", true);
  } finally {
    await istek("DELETE", "/api/ders-programi/kurallar/gunluk_ders_siniri");
  }
  await baglam.close();
};

// Bekleme ekranı: gerçekçi sette (24 şube) çözücü süre sınırını kullanır.
// Önce: cd api && OKULAPI_ORTAM=gelistirme .venv/Scripts/python -m okulapi ornek-okul --evet --set gercekci
AKISLAR["6-bekleme"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const s = await baglam.newPage();
  await s.goto(ADRES + "/giris");
  await s.getByLabel("E-posta").fill("mudur@ornek.test");
  await s.getByLabel("Parola").fill("ornek-okul-parolasi");
  await s.getByRole("button", { name: "Giriş yap" }).click();
  await s.getByRole("img", { name: /Kurulum:/ }).waitFor();
  await s.goto(ADRES + "/program");
  await s.getByRole("button", { name: "Programı oluştur" }).waitFor();
  await s.getByRole("textbox", { name: "Programın adı" }).fill("Güz dönemi programı");
  await s.getByRole("button", { name: "Programı oluştur" }).click();
  await s.getByRole("heading", { name: "Program hazırlanıyor" }).waitFor();
  await s.waitForTimeout(3000);
  await kaydet(s, "12-bekleme-yerlestirme.png");
  await s.waitForTimeout(30_000);
  await kaydet(s, "13-bekleme-iyilestirme.png");
  const basla = Date.now();
  await s.getByRole("heading", { name: "“Güz dönemi programı” hazır" }).waitFor({ timeout: 300_000 });
  console.log(`program hazır (${Math.round((Date.now() - basla) / 1000) + 33} sn civarı)`);
  await s.waitForTimeout(800);
  await kaydet(s, "14-buyuk-okul-program-hazir.png");
  await s.getByRole("link", { name: "Haftalık çizelgeyi aç" }).click();
  await s.getByRole("table", { name: /haftalık programı/ }).waitFor();
  await s.waitForTimeout(1500);
  await kaydet(s, "15-buyuk-okul-cizelge.png", true);
  await baglam.close();
};

// K1: okul ayarlarında özel ayarların özeti. Örnek okula birkaç özel ayar eklenmiş olmalı
// (öğretmene özel M, derse ve şube + derse özel N).
AKISLAR["k1"] = async (tarayici, kaydet) => {
  for (const [ad, viewport] of [["masaustu", MASAUSTU], ["telefon", TELEFON]]) {
    const baglam = await tarayici.newContext({ viewport, locale: "tr-TR" });
    const s = await baglam.newPage();
    await s.goto(ADRES + "/giris");
    await s.getByLabel("E-posta").fill("mudur@ornek.test");
    await s.getByLabel("Parola").fill("ornek-okul-parolasi");
    await s.getByRole("button", { name: "Giriş yap" }).click();
    await s.getByRole("img", { name: /Kurulum:/ }).waitFor();
    await s.goto(ADRES + "/okul");
    const bolum = s.getByRole("region", { name: "Özel ayarlar" });
    await bolum.waitFor();
    await bolum.scrollIntoViewIfNeeded();
    await s.waitForTimeout(500);
    await kaydet(s, `${ad}-ozel-ayarlar.png`);
    await baglam.close();
  }
};

// Yeniden tasarlanan giriş sayfası: masaüstü, tablet, telefon; çizelge dolu anda. Hareket
// azaltılmış görünüm de kaydedilir (animasyon yerine dolu, durağan çizelge).
AKISLAR["giris"] = async (tarayici, kaydet) => {
  const boyutlar = [
    ["1-masaustu.png", { width: 1440, height: 900 }, {}],
    ["2-tablet.png", { width: 768, height: 1024 }, {}],
    ["3-telefon.png", TELEFON, {}],
    ["4-hareket-azaltilmis.png", { width: 1440, height: 900 }, { reducedMotion: "reduce" }],
  ];
  for (const [dosya, viewport, secenek] of boyutlar) {
    const baglam = await tarayici.newContext({ viewport, locale: "tr-TR", ...secenek });
    const s = await baglam.newPage();
    await s.goto(ADRES + "/giris");
    await s.getByRole("heading", { name: "Tekrar hoş geldiniz" }).waitFor();
    if (!secenek.reducedMotion) await s.waitForTimeout(6000); // kartlar yerleşsin, solmadan önce
    await kaydet(s, dosya, viewport === TELEFON);
    await baglam.close();
  }
};

// Giriş sonrası bütün ekranlar, demo okulla dolu, masaüstü genişliğinde (yeniden tasarım öncesi
// kayıt). "Demo ile dene" ile girilir; program yoksa üretilir, yayın ve okul linki açılır. Demo
// okul zaten düzenli sıfırlandığı için geri alınmaz. Sunucuda OKULAPI_DEMO_PAROLA tanımlı olmalı.
AKISLAR["giris-sonrasi"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: { width: 1440, height: 900 }, locale: "tr-TR" });
  const s = await baglam.newPage();
  const koken = { Origin: ADRES };
  const DP = ADRES + "/api/ders-programi";
  const al = async (yol) => {
    const yanit = await s.request.get(yol);
    if (!yanit.ok()) throw new Error(`${yol}: ${yanit.status()} ${await yanit.text()}`);
    return yanit.json();
  };
  await s.goto(ADRES + "/giris");
  await s.getByRole("button", { name: "Demo ile dene" }).click();
  await s.getByRole("heading", { name: "Hoş geldiniz", exact: true }).waitFor();

  let program = (await al(DP + "/programlar")).find((p) => p.durum === "hazir");
  if (!program) {
    const yeni = await (await s.request.post(DP + "/programlar", { headers: koken, data: { ad: "Demo programı", sure_siniri_sn: 20 } })).json();
    for (let i = 0; i < 90 && (await al(`${DP}/programlar/${yeni.id}`)).durum !== "hazir"; i++) await s.waitForTimeout(1000);
    program = await al(`${DP}/programlar/${yeni.id}`);
    if (program.durum !== "hazir") throw new Error(`Program üretilemedi: ${program.durum} ${program.hata_mesaji ?? ""}`);
  }
  if ((await al(DP + "/yayin")) === null) await s.request.put(DP + "/yayin", { headers: koken, data: { program_id: program.id } });
  if ((await al(DP + "/paylasim-linkleri")).length === 0) {
    await s.request.post(DP + "/paylasim-linkleri", { headers: koken, data: { tur: "okul" } });
  }
  const ogretmen = (await al(ADRES + "/api/ogretmenler"))[0];

  const ekranlar = [
    ["01-ana-sayfa.png", "/"],
    ["02-okul-ayarlari.png", "/okul"],
    ["03-ogretmenler.png", "/ogretmenler"],
    ["04-ogretmen-ayrintisi.png", `/ogretmenler/${ogretmen.id}`],
    ["05-siniflar.png", "/siniflar"],
    ["06-dersler.png", "/dersler"],
    ["07-seviye-sablonu.png", "/seviye-sablonu"],
    ["08-ders-dagilimi.png", "/ders-dagilimi"],
    ["09-excelden-aktar.png", "/ice-aktarma"],
    ["10-programlar.png", "/program"],
    ["11-haftalik-cizelge.png", `/program/${program.id}`],
    ["12-yayin-ve-paylasim.png", "/yayin"],
    ["13-kullanicilar.png", "/kullanicilar"],
    ["14-hesabim.png", "/hesabim"],
  ];
  for (const [dosya, yol] of ekranlar) {
    await s.goto(ADRES + yol, { waitUntil: "networkidle" });
    await s.getByRole("heading", { level: 1 }).first().waitFor();
    await s.waitForTimeout(500);
    // Görünmez tarayıcıda gecikmeli giriş animasyonları (çizelge hücreleri) ilerlemeyebiliyor:
    // "disabled" sonlu animasyonları bitmiş haline atlatır, sayfa gerçekte nasıl duruyorsa öyle çekilir.
    await s.evaluate(() => window.scrollTo(0, 0));
    await s.screenshot({ path: resolve(hedef, dosya), fullPage: true, animations: "disabled" });
    console.log(`docs/ekranlar/${klasor}/${dosya}`);
  }
  await baglam.close();
};

// K1 sonrası düzeltmeler (D1-D6). Örnek okulda hazır bir program olmalı.
// Önce: cd api && OKULAPI_ORTAM=gelistirme .venv/Scripts/python -m okulapi ornek-okul --evet --set gercekci
// ve bir program üretilmiş olmalı.
async function ornekGiris(tarayici, viewport) {
  const baglam = await tarayici.newContext({ viewport, locale: "tr-TR" });
  const s = await baglam.newPage();
  await s.goto(ADRES + "/giris");
  await s.getByLabel("E-posta").fill("mudur@ornek.test");
  await s.getByLabel("Parola").fill("ornek-okul-parolasi");
  await s.getByRole("button", { name: "Giriş yap" }).click();
  await s.getByRole("img", { name: /Kurulum:/ }).waitFor();
  return { baglam, s };
}

AKISLAR["duzeltmeler"] = async (tarayici, kaydet) => {
  for (const [ad, viewport] of [["1366", MASAUSTU], ["800", { width: 800, height: 900 }]]) {
    const { baglam, s } = await ornekGiris(tarayici, viewport);
    await s.goto(ADRES + "/program");
    await s.getByRole("heading", { name: "Programlar" }).waitFor();
    await s.waitForTimeout(800);
    await kaydet(s, `${ad}-program.png`, true);
    await s.getByRole("link", { name: /Çizelgeyi aç|Çizelge/ }).first().click();
    await s.getByRole("table", { name: /haftalık programı/ }).waitFor();
    await s.waitForTimeout(1500);
    await kaydet(s, `${ad}-cizelge-sube.png`);
    await s.getByRole("tab", { name: "Öğretmene göre" }).click();
    await s.waitForTimeout(1500);
    await kaydet(s, `${ad}-cizelge-ogretmen.png`);
    await s.getByRole("tab", { name: "Şubeye göre" }).click();
    await s.mouse.wheel(0, 600);
    await s.waitForTimeout(600);
    await kaydet(s, `${ad}-kaydirilmis.png`);
    await baglam.close();
  }
};

// K2 + 5.5: öğretmen detay sayfası. Örnek okulla (mini). Deneme değişiklikleri sonunda geri alınır.
AKISLAR["k2"] = async (tarayici, kaydet) => {
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  await s.goto(ADRES + "/ogretmenler");
  await s.getByRole("table", { name: "Öğretmenler" }).waitFor();
  await s.waitForTimeout(600);
  await kaydet(s, "01-ogretmen-listesi.png");
  await s.getByRole("table", { name: "Öğretmenler" }).getByRole("link", { name: /Zeynep Demir/ }).click();
  const tablo = s.getByRole("table", { name: /müsaitlik çizelgesi/ });
  await tablo.waitFor();
  // Geri almak için başlangıçtaki müsaitlik (API).
  const ogretmenId = s.url().split("/").pop();
  const musaitlikYolu = `${ADRES}/api/ders-programi/ogretmenler/${ogretmenId}/musaitlik`;
  const baslangic = await (await s.request.get(musaitlikYolu)).json();
  await s.waitForTimeout(800);
  await kaydet(s, "02-ogretmen-sayfasi.png", true);
  // Sürükleyerek işaretleme: perşembe 1-4. saat. Bırakmadan önce görüntü.
  const hucre = (ad) => s.getByRole("button", { name: new RegExp("^" + ad + ":") });
  await hucre("Perşembe, 4. saat").scrollIntoViewIfNeeded();
  const kutu = async (ad) => { const b = await hucre(ad).boundingBox(); return [b.x + b.width / 2, b.y + b.height / 2]; };
  await s.mouse.move(...(await kutu("Perşembe, 1. saat")));
  await s.mouse.down();
  for (const saat of [2, 3, 4]) await s.mouse.move(...(await kutu(`Perşembe, ${saat}. saat`)), { steps: 4 });
  await kaydet(s, "03-surukleme.png");
  await s.mouse.up();
  await s.waitForTimeout(600);
  // Bir günü tamamen "gelemez": kapasite uyarısı.
  for (const gun of ["Pazartesi", "Salı", "Çarşamba"]) {
    await s.getByRole("button", { name: `${gun}: bütün günü birlikte değiştir` }).click();
    await s.waitForTimeout(400);
  }
  await s.getByText(/Program bu haliyle üretilemez/).waitFor();
  await s.getByText(/Program bu haliyle üretilemez/).scrollIntoViewIfNeeded();
  await s.waitForTimeout(400);
  await kaydet(s, "04-kapasite-uyarisi.png");
  // Kişisel ayar: boş gün hedefi 2.
  await s.getByRole("combobox", { name: /Boş gün hedefi/ }).selectOption({ label: "2 gün" });
  await s.getByText("özel", { exact: true }).waitFor();
  await s.evaluate(() => window.scrollTo(0, 0));
  await s.waitForTimeout(400);
  await kaydet(s, "05-ozel-ayar.png");
  // Telefonda aynı sayfa.
  const tel = await baglam.newPage();
  await tel.setViewportSize(TELEFON);
  await tel.goto(s.url());
  await tel.getByRole("table", { name: /müsaitlik çizelgesi/ }).waitFor();
  await tel.waitForTimeout(800);
  await kaydet(tel, "06-telefon.png", true);
  // Geri al: özel ayar okul varsayılanına, müsaitlik başlangıçtaki haline (tek istek).
  await s.getByRole("combobox", { name: /Boş gün hedefi/ }).selectOption({ index: 0 });
  await s.getByText("özel", { exact: true }).waitFor({ state: "detached" });
  const eski = new Map(baslangic.hucreler.map((h) => [`${h.gun}-${h.saat}`, h.durum]));
  const degisiklikler = [];
  for (let gun = 0; gun < 5; gun++) {
    for (let saat = 0; saat < 6; saat++) degisiklikler.push({ gun, saat, durum: eski.get(`${gun}-${saat}`) ?? "musait" });
  }
  const geri = await s.request.put(musaitlikYolu, { headers: { Origin: ADRES }, data: { degisiklikler } });
  if (!geri.ok()) throw new Error(`Müsaitlik geri alınamadı: ${geri.status()}`);
  const son = await geri.json();
  if (JSON.stringify(son.hucreler) !== JSON.stringify(baslangic.hucreler)) throw new Error("Müsaitlik eski haline dönmedi");
  console.log("Deneme değişiklikleri geri alındı (müsaitlik ve boş gün hedefi).");
  await baglam.close();
};

// K3: günlere göre ders saati, öğle arası, zil saatleri. Örnek okul önceden deneme ayarına getirilmiş
// olmalı (cuma kısa, öğle arası, zil) ve K3_PROGRAM o ayarla üretilmiş programın kimliği olmalı.
// Akış hiçbir şeyi kaydetmez: kısaltma penceresinde "Vazgeç" seçilir.
AKISLAR["k3"] = async (tarayici, kaydet) => {
  const program = process.env.K3_PROGRAM;
  if (!program) throw new Error("K3_PROGRAM verilmeli");
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  await s.goto(ADRES + "/okul");
  await s.getByRole("group", { name: "Her gün kaç ders saati var" }).waitFor();
  await s.waitForTimeout(600);
  await kaydet(s, "01-okul-ayarlari.png", true);
  // Bir günü daha kısaltmak: kaydetmeden önce etkiler (ADR 0014). Vazgeçilir.
  const persembe = s.getByRole("group", { name: "Her gün kaç ders saati var" }).getByLabel("Perşembe");
  await persembe.fill("4");
  await s.getByRole("button", { name: "Kaydet", exact: true }).click();
  await s.getByRole("dialog", { name: "Bu değişiklik mevcut kayıtları etkileyecek" }).waitFor();
  await s.waitForTimeout(500);
  await kaydet(s, "02-kisaltma-onayi.png");
  await s.getByRole("button", { name: "Vazgeç" }).click();
  for (const [ad, viewport] of [["1366", MASAUSTU], ["800", { width: 800, height: 900 }]]) {
    const sayfa = ad === "1366" ? s : await baglam.newPage();
    if (ad !== "1366") await sayfa.setViewportSize(viewport);
    await sayfa.goto(`${ADRES}/program/${program}`);
    await sayfa.getByRole("table", { name: /haftalık programı/ }).waitFor();
    await sayfa.waitForTimeout(1500);
    await kaydet(sayfa, `03-cizelge-${ad}.png`, true);
  }
  await s.goto(ADRES + "/ogretmenler");
  await s.getByRole("table", { name: "Öğretmenler" }).getByRole("link", { name: /Fatma Şahin/ }).click();
  await s.getByRole("table", { name: /müsaitlik çizelgesi/ }).waitFor();
  await s.getByRole("table", { name: /müsaitlik çizelgesi/ }).scrollIntoViewIfNeeded();
  await s.waitForTimeout(800);
  await kaydet(s, "04-musaitlik.png");
  await baglam.close();
};

// K4: blok dersler. K4_PROGRAM okul önerisiyle üretilmiş bir program. Akış derse özel şekilleri API ile
// geçici olarak kurar ve sonunda kaldırır (özel ayar sayısı başlangıçtakine döndüğü denetlenir).
AKISLAR["k4"] = async (tarayici, kaydet) => {
  const program = process.env.K4_PROGRAM;
  if (!program) throw new Error("K4_PROGRAM verilmeli");
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  const api = (yol) => `${ADRES}/api/ders-programi${yol}`;
  const basla = (await (await s.request.get(api("/kurallar"))).json()).find((k) => k.tur === "blok_deseni");
  const dersler = await (await s.request.get(`${ADRES}/api/dersler`)).json();
  const ders = (ad) => dersler.find((d) => d.ad === ad).id;
  const ozel = (ad, desen) =>
    s.request.put(api("/kurallar/blok_deseni/ozel"), {
      headers: { Origin: ADRES }, data: { kapsam: { ders_id: ders(ad) }, parametreler: { desen } },
    });
  const kaldir = (ad) => s.request.delete(api(`/kurallar/blok_deseni/ozel?ders_id=${ders(ad)}`), { headers: { Origin: ADRES } });
  try {
    await s.goto(`${ADRES}/program/${program}`);
    await s.getByRole("table", { name: /haftalık programı/ }).waitFor();
    await s.waitForTimeout(1500);
    await kaydet(s, "01-cizelge-bloklar.png", true);
    await s.getByRole("tab", { name: "Öğretmene göre" }).click();
    await s.waitForTimeout(1500);
    await kaydet(s, "02-cizelge-ogretmen.png", true);
    await s.goto(ADRES + "/okul");
    const bolum = s.getByRole("region", { name: "Dağılım şekli (blok dersler)" });
    await bolum.waitFor();
    await bolum.scrollIntoViewIfNeeded();
    await s.waitForTimeout(500);
    await kaydet(s, "03-okul-ayari.png");
    await ozel("Türk Dili ve Edebiyatı", [2, 1, 1, 1]);
    await ozel("Matematik", []);
    await s.goto(ADRES + "/dersler");
    await s.getByRole("combobox", { name: "Matematik dersinin dağılım şekli" }).waitFor();
    await s.waitForTimeout(800);
    await kaydet(s, "04-ders-listesi.png", true);
    await ozel("Türk Dili ve Edebiyatı", [3, 2]);
    await s.goto(ADRES + "/program");
    await s.getByText(/3 saatlik blok istiyor/).first().waitFor();
    await s.waitForTimeout(600);
    await kaydet(s, "05-on-kontrol.png", true);
  } finally {
    await kaldir("Türk Dili ve Edebiyatı");
    await kaldir("Matematik");
    const son = (await (await s.request.get(api("/kurallar"))).json()).find((k) => k.tur === "blok_deseni");
    if (son.ozel_ayarlar.length !== basla.ozel_ayarlar.length) throw new Error("Özel ayarlar geri alınamadı");
    console.log("Deneme özel ayarları geri alındı.");
    await baglam.close();
  }
};

// P1: süre yetmedi. Geçici bir deneme okulu (36 şube, "Hızlı" uyarısı) ve ona veritabanından elle
// yazılmış "bilinmiyor" sonuçlu bir deneme. Okul, betik bitince deneme temizliğiyle silinir.
AKISLAR["p1"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const kayit = await baglam.request.post(ADRES + "/api/kayit", {
    headers: { Origin: ADRES },
    data: { okul: { ad: "Büyük Anadolu Lisesi" }, ad: "Deneme Müdür", email: `ekran-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi" },
  });
  if (!kayit.ok()) throw new Error(`Deneme okulu kaydı: ${kayit.status()}`);
  for (let i = 0; i < 36; i++) {
    const sv = 9 + (i % 4);
    await baglam.request.post(ADRES + "/api/siniflar", { headers: { Origin: ADRES }, data: { ad: `${sv}-${String.fromCharCode(65 + Math.floor(i / 4))}`, seviye: sv } });
  }
  const okul = await (await baglam.request.get(ADRES + "/api/okul")).json();
  const sql = `INSERT INTO program (id, okul_id, ad, durum, hata_mesaji, sure_siniri_sn, baslama, bitis, cozum_durumu, celiskiler, sure_sn)
    VALUES (gen_random_uuid(), '${okul.id}', 'Program 1', 'basarisiz',
      'Kurallara uyan bir program var, ama 30 sn içinde bulunamadı. Daha uzun bir süre sınırıyla yeniden deneyin.',
      30, now() - interval '2 minutes', now() - interval '1 minute', 'bilinmiyor', '[]', 101.5)`;
  const psql = spawnSync("docker", ["exec", "-i", "ders-programi-db-1", "psql", "-U", "okul_sahip", "-d", "okul", "-v", "ON_ERROR_STOP=1"],
    { input: sql, encoding: "utf-8" });
  if (psql.status !== 0) throw new Error(`Deneme programı yazılamadı: ${psql.stderr}`);
  const s = await baglam.newPage();
  await s.goto(ADRES + "/program");
  await s.getByText("Bu süre okulunuz için yetmedi.").waitFor();
  await s.getByText(/36 şube var/).waitFor();
  await s.waitForTimeout(800);
  await kaydet(s, "01-sure-yetmedi.png", true);
  await baglam.close();
};

// K5: şube grupları ve istisnalar, örnek okulda. Önce: docker compose up -d --build api worker.
// Akış her değişikliği API ile yapar ve sonunda tersini uygular; başlangıçtaki durumla aynı
// olduğu denetlenir (şubeler, gruplar, şablon, istisnalar, atamalar, özel ayarlar). Üretilen
// deneme programının kimliği yazdırılır (program silme ucu yok; veritabanından silinir).
AKISLAR["k5"] = async (tarayici, kaydet) => {
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  const yaz = { headers: { Origin: ADRES } };
  const al = async (yol) => (await s.request.get(ADRES + yol)).json();
  const gonder = async (yontem, yol, data) => {
    const y = await s.request.fetch(ADRES + yol, { method: yontem, ...yaz, ...(data ? { data } : {}) });
    if (!y.ok()) throw new Error(`${yontem} ${yol}: ${y.status()} ${await y.text()}`);
    return y.status() === 204 ? null : y.json();
  };
  const DP = "/api/ders-programi";
  const durum = async () => {
    const kurallar = await al(`${DP}/kurallar`);
    return JSON.stringify({
      siniflar: (await al("/api/siniflar")).map((x) => [x.ad, x.sube_grubu_id]),
      gruplar: await al("/api/sube-gruplari"),
      sablon: (await al(`${DP}/seviye-sablonlari`)).map((x) => [x.id, x.haftalik_saat]).sort(),
      istisnalar: await al(`${DP}/istisnalar`),
      atamalar: (await al(`${DP}/atamalar`)).map((x) => [x.id, x.ogretmen_id, x.haftalik_saat]).sort(),
      ozel: kurallar.map((k) => [k.tur, k.ozel_ayarlar.length]),
    });
  };
  const baslangic = await durum();
  const sinif = Object.fromEntries((await al("/api/siniflar")).map((x) => [x.ad, x]));
  const ders = Object.fromEntries((await al("/api/dersler")).map((x) => [x.ad, x.id]));
  const ogretmen = Object.fromEntries((await al("/api/ogretmenler")).map((x) => [x.ad, x.id]));
  const seviye9 = (await al(`${DP}/seviye-sablonlari`)).filter((x) => x.seviye === 9 && !x.sube_grubu_id);
  const eklenenSablon = [];
  let grup;
  try {
    // 1. Grup: "9 Fen", 9-A grupta. Grubun şablonu: 9. sınıflarınki + Coğrafya 2.
    grup = await gonder("POST", "/api/sube-gruplari", { ad: "9 Fen", seviye: 9 });
    await gonder("PATCH", `/api/siniflar/${sinif["9-A"].id}`, { sube_grubu_id: grup.id });
    for (const x of [...seviye9, { ders_id: ders["Coğrafya"], haftalik_saat: 2 }]) {
      eklenenSablon.push(await gonder("POST", `${DP}/seviye-sablonlari`, { seviye: 9, sube_grubu_id: grup.id, ders_id: x.ders_id, haftalik_saat: x.haftalik_saat }));
    }
    // Gruba özel kurallar: 9 Fen'de Matematik günde en çok 3 saat ve 3+3 dağılım.
    await gonder("PUT", `${DP}/kurallar/gunluk_ders_siniri/ozel`, { kapsam: { ders_id: ders["Matematik"], sube_grubu_id: grup.id }, parametreler: { n: 3 } });
    await gonder("PUT", `${DP}/kurallar/blok_deseni/ozel`, { kapsam: { ders_id: ders["Matematik"], sube_grubu_id: grup.id }, parametreler: { desen: [3, 3] } });

    await s.goto(ADRES + "/siniflar");
    await s.getByRole("region", { name: "Şube grupları" }).waitFor();
    await s.waitForTimeout(800);
    await kaydet(s, "01-siniflar-gruplar.png", true);

    // 2. Grubun şablonunu arayüzden uygula.
    await s.goto(`${ADRES}/seviye-sablonu?seviye=9&grup=${grup.id}`);
    await s.getByRole("heading", { name: "9 Fen grubunun dersleri" }).waitFor();
    await s.getByRole("button", { name: "9 Fen şubelerine uygula" }).click();
    await s.getByRole("heading", { name: "Şablon uygulandı" }).waitFor();
    await s.waitForTimeout(600);
    await kaydet(s, "02-grup-sablonu-uygulandi.png", true);
    // 9-A'nın yeni Coğrafya dersine öğretmen.
    const cog9a = (await al(`${DP}/atamalar`)).find((a) => a.sinif_id === sinif["9-A"].id && a.ders_id === ders["Coğrafya"]);
    await gonder("PATCH", `${DP}/atamalar/${cog9a.id}`, { ogretmen_id: ogretmen["Fatma Şahin"] });

    // 3. 9. sınıfların şablonuna Coğrafya 2: uygulanınca 9-B'ye eklenir (9-A kendi grubunda).
    eklenenSablon.push(await gonder("POST", `${DP}/seviye-sablonlari`, { seviye: 9, ders_id: ders["Coğrafya"], haftalik_saat: 2 }));
    await gonder("POST", `${DP}/seviye-sablonlari/uygula`, { seviye: 9 });

    // 4. Ders dağılımında 9-B'den Coğrafya'yı "bu şube almaz" ile kaldır (pencere).
    await s.goto(`${ADRES}/ders-dagilimi?gorunum=sube&sinif=${sinif["9-B"].id}`);
    await s.getByRole("button", { name: "Coğrafya dersini kaldır" }).click();
    await s.getByText("9-B bu dersi hiç almasın").waitFor();
    await s.waitForTimeout(500);
    await kaydet(s, "03-kaldirma-penceresi.png");
    await s.getByRole("dialog").getByRole("button", { name: "Kaldır" }).click();
    await s.getByText(/9-B artık Coğrafya almıyor/).waitFor();
    await s.getByRole("heading", { name: "Bu şubeye özel" }).scrollIntoViewIfNeeded();
    await s.waitForTimeout(600);
    await kaydet(s, "04-sube-istisnasi.png", true);

    // 5. Şablonu yeniden uygula: Coğrafya 9-B'ye geri gelmez, raporda görünür.
    await s.goto(`${ADRES}/seviye-sablonu?seviye=9`);
    await s.getByRole("button", { name: "9. sınıf şubelerine uygula" }).click();
    await s.getByText(/Şubenin almadığı 1 ders eklenmedi/).waitFor();
    await s.waitForTimeout(600);
    await kaydet(s, "05-yeniden-uygulama-raporu.png", true);
    const cog9b = (await al(`${DP}/atamalar`)).filter((a) => a.sinif_id === sinif["9-B"].id && a.ders_id === ders["Coğrafya"]);
    if (cog9b.length) throw new Error("İstisna korunmadı: 9-B'ye Coğrafya geri geldi");
    console.log("İstisna korundu: yeniden uygulamada 9-B'ye Coğrafya eklenmedi.");

    // 6. Özel ayarların özeti ve program üretimi (Hızlı).
    await s.goto(ADRES + "/okul");
    await s.getByText("9 Fen grubu · Matematik").first().scrollIntoViewIfNeeded();
    await s.waitForTimeout(500);
    await kaydet(s, "06-ozel-ayarlar.png");
    await s.goto(ADRES + "/program");
    await s.getByText(/Ön kontrol tamam/).waitFor();
    await s.getByLabel("Programın adı").fill("K5 deneme");
    await s.getByRole("radio", { name: /Hızlı/ }).check();
    await s.getByRole("button", { name: "Programı oluştur" }).click();
    await s.getByRole("heading", { name: "“K5 deneme” hazır" }).waitFor({ timeout: 120_000 });
    const program = (await al(`${DP}/programlar`)).find((p) => p.ad === "K5 deneme");
    console.log(`DENEME_PROGRAMI=${program.id} durum=${program.cozum_durumu} ceza=${program.toplam_ceza}`);
    await s.goto(`${ADRES}/program/${program.id}?sinif=${sinif["9-A"].id}`);
    await s.getByRole("table", { name: /haftalık programı/ }).waitFor();
    await s.waitForTimeout(1500);
    await kaydet(s, "07-cizelge-9a.png", true);
  } finally {
    // Geri al: önce şablon satırları (istisna kaldırılınca ders şablondan geri eklenmesin).
    for (const x of eklenenSablon.reverse()) await gonder("DELETE", `${DP}/seviye-sablonlari/${x.id}`);
    for (const i of await al(`${DP}/istisnalar`)) await gonder("DELETE", `${DP}/istisnalar/${i.id}`);
    const ilk = JSON.parse(baslangic).atamalar.map((a) => a[0]);
    for (const a of await al(`${DP}/atamalar`)) if (!ilk.includes(a.id)) await gonder("DELETE", `${DP}/atamalar/${a.id}`);
    if (grup) {
      await gonder("PATCH", `/api/siniflar/${sinif["9-A"].id}`, { sube_grubu_id: null });
      await gonder("DELETE", `/api/sube-gruplari/${grup.id}`); // gruba özel ayarlar da silinir
    }
    if ((await durum()) !== baslangic) throw new Error("Deneme verisi geri alınamadı: durum başlangıçtakinden farklı");
    console.log("Deneme verisi geri alındı: şubeler, gruplar, şablon, istisnalar, atamalar ve özel ayarlar başlangıçtaki gibi.");
    await baglam.close();
  }
};

// 5.6: kullanıcılar, özel ayar ekleme, telefonda "Toplu seç", gün gün çizelge, kart tablo.
// Örnek okulda hazır bir program olmalı. Özel ayar ekranının etkisini göstermek için geçici bir
// "Matematik" özel ayarı açılır ve iş bitince kaldırılır (hiçbir şey kaydedilmez).
AKISLAR["5.6"] = async (tarayici, kaydet) => {
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  const koken = { Origin: ADRES };
  const dersler = await (await s.request.get(ADRES + "/api/dersler")).json();
  const siniflar = await (await s.request.get(ADRES + "/api/siniflar")).json();
  const mat = dersler.find((d) => d.ad === "Matematik");
  const sinif = siniflar.find((x) => x.ad === "9-A");
  const N = ADRES + "/api/ders-programi/kurallar/gunluk_ders_siniri/ozel";
  await s.request.put(N, { headers: koken, data: { kapsam: { ders_id: mat.id }, parametreler: { n: 3 } } });
  try {
    await s.goto(ADRES + "/kullanicilar");
    await s.getByText(/Okulda tek müdür var/).waitFor();
    await kaydet(s, "01-kullanicilar.png", true);

    await s.goto(ADRES + "/okul");
    await s.getByRole("button", { name: "Özel ayar ekle" }).click();
    const form = s.getByRole("form", { name: "Özel ayar ekle" });
    await form.getByLabel("Kural").selectOption("gunluk_ders_siniri");
    await form.getByLabel("Nerede geçerli").selectOption("ders_sube");
    await form.getByLabel("Şube", { exact: true }).selectOption(sinif.id);
    await form.getByLabel("Ders", { exact: true }).selectOption(mat.id);
    await form.getByRole("status", { name: "Bu ayarın etkisi" }).waitFor();
    await s.getByRole("region", { name: "Özel ayarlar" }).scrollIntoViewIfNeeded();
    await s.evaluate(() => document.querySelector("#ozel-ayarlar")?.scrollIntoView({ block: "start" }));
    await kaydet(s, "02-ozel-ayar-ekle.png");
  } finally {
    await s.request.delete(`${N}?ders_id=${mat.id}`, { headers: koken });
    await baglam.close();
  }

  // Telefon: dokunmatik bağlam ("Toplu seç" düğmesi yalnızca dokunmatik ekranda görünür).
  const tb = await tarayici.newContext({ viewport: TELEFON, locale: "tr-TR", hasTouch: true, isMobile: true });
  const t = await tb.newPage();
  await t.goto(ADRES + "/giris");
  await t.getByLabel("E-posta").fill("mudur@ornek.test");
  await t.getByLabel("Parola").fill("ornek-okul-parolasi");
  await t.getByRole("button", { name: "Giriş yap" }).tap();
  await t.getByRole("img", { name: /Kurulum:/ }).waitFor();
  const ogretmenler = await (await t.request.get(ADRES + "/api/ogretmenler")).json();
  await t.goto(ADRES + "/ogretmenler/" + ogretmenler[0].id);
  await t.getByRole("button", { name: "Toplu seç" }).tap();
  await t.getByText(/Toplu seçim açık/).scrollIntoViewIfNeeded();
  await t.evaluate(() => window.scrollBy(0, -80));
  await kaydet(t, "03-telefon-toplu-sec.png");

  await t.goto(ADRES + "/program");
  await t.getByRole("link", { name: "Haftalık çizelgeyi aç" }).first().tap();
  const gunler = t.getByRole("group", { name: "Gün" });
  await gunler.getByRole("button", { name: "Salı" }).tap();
  await gunler.evaluate((e) => e.scrollIntoView({ block: "start" }));
  await t.evaluate(() => window.scrollBy(0, -140));
  await t.waitForTimeout(700);
  await kaydet(t, "04-telefon-gun-gun.png");

  await t.goto(ADRES + "/ders-dagilimi");
  await t.getByRole("table").first().waitFor();
  await t.getByRole("heading", { name: /şubesinin dersleri/ }).evaluate((e) => e.scrollIntoView({ block: "start" }));
  await t.evaluate(() => window.scrollBy(0, -80));
  await kaydet(t, "05-telefon-ders-dagilimi.png");
  await tb.close();
};

// 6.3 + 7.1: programlar listesi, fark, elle düzeltme. Geçici veri API ile açılır ve iş bitince
// silinir: bir öğretmene bir günlük "gelemez", o veriyle mevcut programı temel alan ikinci program.
// Elle düzeltme yalnızca bu geçici programda yapılır (silinince taşımaları ve kilitleri de gider).
AKISLAR["7.1"] = async (tarayici, kaydet) => {
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  const koken = { Origin: ADRES };
  const DP = ADRES + "/api/ders-programi";
  const al = async (yol) => (await s.request.get(DP + yol)).json();
  const programlar = await al("/programlar");
  const temel = programlar.find((p) => p.durum === "hazir");
  const atamalar = await al("/atamalar");
  const yerlesimler = await al(`/programlar/${temel.id}/yerlesimler`);
  // Bir öğretmenin ders verdiği ilk gün: o gün bütün gün gelemez olsun.
  const ilk = yerlesimler.find((y) => atamalar.find((a) => a.id === y.ders_atama_id)?.ogretmen_id);
  const ogretmen = atamalar.find((a) => a.id === ilk.ders_atama_id).ogretmen_id;
  const musaitlik = await al(`/ogretmenler/${ogretmen}/musaitlik`);
  const eklenen = Array.from({ length: 6 }, (_, saat) => ({ gun: ilk.gun, saat, durum: "gelemez" }))
    .filter((h) => !musaitlik.hucreler.some((m) => m.gun === h.gun && m.saat === h.saat));
  await s.request.put(`${DP}/ogretmenler/${ogretmen}/musaitlik`, { headers: koken, data: { degisiklikler: eklenen } });
  let yeni;
  try {
    yeni = await (await s.request.post(`${DP}/programlar`, { headers: koken,
      data: { ad: "Kasım (güncel)", sure_siniri_sn: 30, temel_program_id: temel.id } })).json();
    for (let i = 0; i < 60 && (await al(`/programlar/${yeni.id}`)).durum !== "hazir"; i++) await s.waitForTimeout(1000);

    await s.goto(ADRES + "/program");
    await s.getByRole("status", { name: "Temel programa göre değişiklik" }).waitFor();
    await s.waitForTimeout(600);
    await kaydet(s, "01-programlar.png", true);

    await s.goto(`${ADRES}/program/${yeni.id}?fark=1`);
    await s.locator("[data-degisti]").first().waitFor();
    await s.waitForTimeout(900);
    await s.locator("[data-degisti]").first().scrollIntoViewIfNeeded();
    await s.evaluate(() => window.scrollBy(0, -260));
    await kaydet(s, "02-fark-cizelge.png");

    await s.goto(`${ADRES}/program/${yeni.id}`);
    const tablo = s.getByRole("table").first();
    await tablo.waitFor();
    await s.waitForTimeout(900);
    // Uyarılı hedefi olan ilk ders seçilir.
    const dugmeler = tablo.locator("td[data-kilitli], td").filter({ has: s.locator("button") });
    let secildi = false;
    for (let i = 0; i < (await dugmeler.count()) && !secildi; i++) {
      const td = dugmeler.nth(i);
      if (!(await td.textContent())?.trim()) continue;
      await td.locator("button").click();
      await s.getByRole("button", { name: "Taşı" }).click();
      await s.locator('td[data-hedef]').first().waitFor();
      await s.waitForTimeout(300);
      if ((await s.locator('td[data-hedef="uyari"], td[data-hedef="uygun"]').count()) > 0) secildi = true;
      else await s.getByRole("button", { name: "Vazgeç" }).click();
    }
    const hedef = s.locator('td[data-hedef="uyari"]').first();
    await hedef.locator("button").hover();
    await s.getByRole("region", { name: "Elle düzeltme" }).scrollIntoViewIfNeeded();
    await s.evaluate(() => window.scrollBy(0, -60));
    await kaydet(s, "03-tasima-haritasi.png");

    await hedef.locator("button").click();
    await s.getByRole("dialog").waitFor();
    await kaydet(s, "04-uyari-onayi.png");
    await s.getByRole("button", { name: "Yine de taşı" }).click();
    await s.getByText(/saate taşındı/).waitFor();
    // Bir dersi kilitle: kilit simgesi ve "Geri al (2)".
    const dolu = tablo.locator("td").filter({ hasText: /\S/ }).filter({ has: s.locator("button") }).nth(2);
    await dolu.locator("button").click();
    await s.getByRole("button", { name: "Kilitle" }).click();
    await s.getByText(/kilitlendi/).waitFor();
    await s.getByRole("button", { name: "Kapat", exact: true }).click();
    await s.waitForTimeout(400);
    await s.locator("[data-kilitli]").first().scrollIntoViewIfNeeded();
    await s.evaluate(() => window.scrollBy(0, -200));
    await kaydet(s, "05-kilitli-ve-geri-al.png");

    const tb = await tarayici.newContext({ viewport: TELEFON, locale: "tr-TR", hasTouch: true, isMobile: true });
    const t = await tb.newPage();
    await t.goto(ADRES + "/giris");
    await t.getByLabel("E-posta").fill("mudur@ornek.test");
    await t.getByLabel("Parola").fill("ornek-okul-parolasi");
    await t.getByRole("button", { name: "Giriş yap" }).tap();
    await t.getByRole("img", { name: /Kurulum:/ }).waitFor();
    await t.goto(`${ADRES}/program/${yeni.id}`);
    const gunler = t.getByRole("group", { name: "Gün" });
    await gunler.getByRole("button", { name: "Pazartesi" }).tap();
    const liste = t.getByRole("list", { name: /Pazartesi/ });
    await liste.getByRole("listitem").filter({ has: t.locator("button") }).first().locator("button").tap();
    await t.getByRole("button", { name: "Taşı" }).tap();
    await t.locator("li[data-hedef]").first().waitFor();
    await gunler.getByRole("button", { name: "Salı" }).tap();
    await t.waitForTimeout(500);
    await t.getByRole("region", { name: "Elle düzeltme" }).evaluate((e) => e.scrollIntoView({ block: "start" }));
    await t.evaluate(() => window.scrollBy(0, -70));
    await kaydet(t, "06-telefon-tasima.png");
    await tb.close();
  } finally {
    if (yeni) await s.request.delete(`${DP}/programlar/${yeni.id}`, { headers: koken });
    await s.request.put(`${DP}/ogretmenler/${ogretmen}/musaitlik`, { headers: koken,
      data: { degisiklikler: eklenen.map((h) => ({ ...h, durum: "musait" })) } });
    await baglam.close();
  }
};

// 7.2: "İndir" menüsü ve çıktılar. Örnek okula zil saatleri ve öğle arası geçici olarak açılır
// (çıktıda görünsünler), iş bitince eski ayar geri yazılır. Menüden gerçekten indirilir (dosya
// adı denetlenir); PDF'ler `CIKTI_DIZINI`ne yazılır, sayfaları PNG'ye çevirmek ayrı adımdır
// (api/.venv ile pypdfium2; bkz. docs/arayuz-plani.md 7.2g).
AKISLAR["7.2"] = async (tarayici, kaydet) => {
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  const koken = { Origin: ADRES };
  const DP = ADRES + "/api/ders-programi";
  const dizin = process.env.CIKTI_DIZINI ?? hedef;
  const okul = await (await s.request.get(ADRES + "/api/okul")).json();
  const eski = { ilk_ders_baslangic: okul.ilk_ders_baslangic, ogle_arasi_sonra: okul.ogle_arasi_sonra };
  try {
    await s.request.patch(ADRES + "/api/okul", { headers: koken, data: { ilk_ders_baslangic: "08:30", ogle_arasi_sonra: 4 } });
    const program = (await (await s.request.get(DP + "/programlar")).json()).find((p) => p.durum === "hazir");
    await s.goto(`${ADRES}/program/${program.id}`);
    await s.getByRole("table").first().waitFor();
    await s.getByRole("button", { name: /İndir/ }).click();
    await s.getByRole("link", { name: /^Şube programları/ }).waitFor();
    await kaydet(s, "01-indir-menusu.png");

    const indirme = s.waitForEvent("download");
    await s.getByRole("link", { name: /^Şube programları/ }).click();
    const dosya = await indirme;
    if (dosya.suggestedFilename() !== "Şube programları.pdf") throw new Error(`Dosya adı: ${dosya.suggestedFilename()}`);
    console.log("indirildi:", dosya.suggestedFilename());
    for (const [ad, yol] of [["subeler.pdf", "subeler.pdf?imza=true"], ["ogretmenler.pdf", "ogretmenler.pdf"],
      ["carsaf.pdf", "carsaf.pdf?satir=ogretmen"], ["program.xlsx", "program.xlsx"]]) {
      const yanit = await s.request.get(`${DP}/programlar/${program.id}/cikti/${yol}`);
      if (!yanit.ok()) throw new Error(`${yol}: ${yanit.status()}`);
      writeFileSync(resolve(dizin, ad), await yanit.body());
      console.log(resolve(dizin, ad));
    }
  } finally {
    await s.request.patch(ADRES + "/api/okul", { headers: koken, data: eski });
    await baglam.close();
  }
};

// 8b: yayın sayfası ve girişsiz paylaşım sayfası (telefon ve masaüstü). Örnek okulda yayın yoksa
// hazır program geçici olarak yayınlanır; açılan linkler ve geçici yayın iş bitince geri alınır.
AKISLAR["8"] = async (tarayici, kaydet) => {
  const { baglam, s } = await ornekGiris(tarayici, MASAUSTU);
  const koken = { Origin: ADRES };
  const DP = ADRES + "/api/ders-programi";
  const onceki = new Set((await (await s.request.get(DP + "/paylasim-linkleri")).json()).map((l) => l.id));
  const yayinVardi = (await (await s.request.get(DP + "/yayin")).json()) !== null;
  try {
    if (!yayinVardi) {
      const program = (await (await s.request.get(DP + "/programlar")).json()).find((p) => p.durum === "hazir");
      await s.request.put(DP + "/yayin", { headers: koken, data: { program_id: program.id } });
    }
    await s.request.post(DP + "/paylasim-linkleri", { headers: koken, data: { tur: "okul" } });
    const ogretmenler = await (await s.request.post(DP + "/paylasim-linkleri/toplu", { headers: koken, data: { tur: "ogretmen" } })).json();
    await s.goto(ADRES + "/yayin");
    await s.getByLabel(`${ogretmenler[0].hedef_adi} linki`, { exact: true }).waitFor();
    await kaydet(s, "01-yayin-sayfasi.png");

    const tel = await tarayici.newContext({ viewport: TELEFON, locale: "tr-TR", isMobile: true, hasTouch: true });
    const t = await tel.newPage();
    await t.goto(`${ADRES}/p/${ogretmenler[0].jeton}`);
    await t.getByRole("button", { name: "Salı" }).click();
    await t.getByRole("list", { name: "Salı dersleri" }).waitFor();
    await kaydet(t, "02-telefon-ogretmen.png", true);
    await tel.close();

    const okulLinki = (await (await s.request.get(DP + "/paylasim-linkleri")).json()).find((l) => l.tur === "okul");
    const m = await baglam.newPage();
    await m.goto(`${ADRES}/p/${okulLinki.jeton}`);
    await m.getByRole("table").first().waitFor();
    await kaydet(m, "03-masaustu-okul-linki.png");
  } finally {
    for (const l of await (await s.request.get(DP + "/paylasim-linkleri")).json()) {
      if (!onceki.has(l.id)) await s.request.delete(`${DP}/paylasim-linkleri/${l.id}`, { headers: koken });
    }
    if (!yayinVardi) await s.request.delete(DP + "/yayin", { headers: koken });
    await baglam.close();
  }
};

const liste = GORUNUMLER[adim];
const akis = AKISLAR[adim];
if (!liste && !akis) {
  console.error(`Bilinmeyen adım: ${adim}. Seçenekler: ${[...Object.keys(GORUNUMLER), ...Object.keys(AKISLAR)].join(", ")}`);
  process.exit(2);
}

const tarayici = await chromium.launch({ channel: "msedge" });
if (koyu) {
  const baglamAc = tarayici.newContext.bind(tarayici);
  tarayici.newContext = (secenek = {}) => baglamAc({ colorScheme: "dark", ...secenek });
}
if (akis) {
  try {
    await akis(tarayici, async (sayfa, dosya, tamSayfa = false) => {
      await sayfa.waitForTimeout(300);
      // Tam sayfa görüntüsünde yapışkan üst çubuk o anki kaydırma yerinde çizilir: önce başa dön.
      if (tamSayfa) await sayfa.evaluate(() => window.scrollTo(0, 0));
      await sayfa.screenshot({ path: resolve(hedef, dosya), fullPage: tamSayfa });
      console.log(`docs/ekranlar/${klasor}/${dosya}`);
    });
  } finally {
    await tarayici.close();
    denemeOkullariniTemizle();
  }
  process.exit(0);
}
try {
  // Sayfalar giriş ister (5.2'den beri): görüntüler için geçici bir okul kaydedilir; oturum
  // çerezi bu tarayıcı bağlamındaki bütün sayfalarda geçerlidir.
  const baglam = await tarayici.newContext({ locale: "tr-TR" });
  const kayit = await baglam.request.post(ADRES + "/api/kayit", {
    headers: { Origin: ADRES },
    data: { okul: { ad: "Çizelge Örnek Anadolu Lisesi" }, ad: "Ayşe Yılmaz", email: `ekran-${Date.now()}@ornek.test`, sifre: "ekran-goruntusu-parolasi" },
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
    console.log(`docs/ekranlar/${klasor}/${g.dosya}`);
    await sayfa.close();
  }
} finally {
  await tarayici.close();
  denemeOkullariniTemizle();
}
