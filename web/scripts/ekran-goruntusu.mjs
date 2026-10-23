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

AKISLAR["5.3"] = async (tarayici, kaydet) => {
  const baglam = await tarayici.newContext({ viewport: MASAUSTU, locale: "tr-TR" });
  const istek = async (yontem, yol, data) => {
    const y = await baglam.request.fetch(ADRES + yol, { method: yontem, headers: { Origin: ADRES }, data });
    if (!y.ok()) throw new Error(`${yontem} ${yol}: ${y.status()} ${await y.text()}`);
    return y.json();
  };
  await istek("POST", "/api/kayit", {
    okul: { ad: "Atatürk Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
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
    okul: { ad: "Atatürk Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
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
    await s.getByRole("heading", { name: "Giriş yap" }).waitFor();
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
  await s.getByRole("heading", { name: "Giriş yap" }).waitFor();
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
      // Tam sayfa görüntüsünde yapışkan üst çubuk o anki kaydırma yerinde çizilir: önce başa dön.
      if (tamSayfa) await sayfa.evaluate(() => window.scrollTo(0, 0));
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
