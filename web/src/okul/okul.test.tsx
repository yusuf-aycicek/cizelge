/** Okul ayarları: okul bilgileri (azaltmanın etkileri), kurallar, özel ayarların özeti, kuralların önemi. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { BEN_ORNEK, ORNEK_KURALLAR, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

const ETKILER = [
  "3 müsaitlik kaydı yeni ayarların dışında kalıyor ve silinecek (2 öğretmen; ör. Ayşe Yılmaz, Cuma 1. saat).",
  "1 programda (Güz dönemi) yeni ayarların dışında kalan 4 ders saati var. Programlar silinmez, eski ayarlarla "
    + "üretilmiş olarak kalır; yeni ayarlarla programı yeniden üretmeniz gerekir.",
];

/** Okul uçları: önizleme ve kaydetme istekleri kaydedilir. */
const ZIL_BITIS: Record<string, string> = {
  "08:30": "09:10", "09:20": "10:00", "10:10": "10:50", "11:00": "11:40", "12:30": "13:10", "13:20": "14:00",
  "14:10": "14:50", "15:00": "15:40",
};

function okulApisi(etkiler: string[] = []) {
  const istekler: { yol: string; govde: unknown }[] = [];
  let okul = { ...BEN_ORNEK.okul };
  sunucu.use(
    http.get("/api/okul", () => HttpResponse.json(okul)),
    // Zil hesabı sunucudadır (api cekirdek/zil.py); sahte sunucu 50 dk öğle arası taslağına yanıt verir.
    http.post("/api/okul/zil-onizleme", async ({ request }) => {
      const govde = (await request.json()) as { ogle_arasi_dk: number; ogle_arasi_sonra: number | null };
      istekler.push({ yol: "zil-onizleme", govde });
      const baslar = ["08:30", "09:20", "10:10", "11:00", "12:30", "13:20", "14:10", "15:00"];
      return HttpResponse.json({
        zil_saatleri: baslar.map((b) => ({ baslangic: b, bitis: ZIL_BITIS[b]! })),
        ogle_arasi_zili: govde.ogle_arasi_sonra === 4 && govde.ogle_arasi_dk === 50 ? { baslangic: "11:40", bitis: "12:30" } : null,
      });
    }),
    http.post("/api/okul/ayar-etkisi", async ({ request }) => {
      istekler.push({ yol: "ayar-etkisi", govde: await request.json() });
      return HttpResponse.json({ etkiler });
    }),
    http.patch("/api/okul", async ({ request }) => {
      const govde = (await request.json()) as Record<string, unknown>;
      istekler.push({ yol: "okul", govde });
      if (etkiler.length && !govde.etkileri_onayla) {
        return HttpResponse.json({ detail: "Bu değişiklik mevcut kayıtları etkiliyor; devam etmek için etkileri onaylayın.", etkiler },
          { status: 409 });
      }
      // Sunucunun tek gösterimi: liste verilirse en uzun gün günlük ders saati olur.
      const gunSayisi = govde.gun_sayisi as number;
      const liste = (govde.gun_saatleri as number[] | null) ?? Array(gunSayisi).fill(govde.gunluk_ders_saati);
      okul = { ...okul, ...(govde as object), gun_sayisi: gunSayisi, gun_saatleri: liste, gunluk_ders_saati: Math.max(...liste) };
      return HttpResponse.json(okul);
    }),
  );
  return istekler;
}

/** Varsayılan okulda (her gün 8 saat, öğle arası ve zil saatleri yok) formun hafta alanları. */
const HAFTA_VARSAYILAN = {
  gun_saatleri: null, ogle_arasi_sonra: null, ilk_ders_baslangic: null, ders_suresi_dk: 40, teneffus_dk: 10,
  ogle_arasi_dk: 40,
};

async function ac() {
  const s = uygulamayiCiz("/okul");
  await screen.findByRole("region", { name: "Okul bilgileri" });
  return s;
}

describe("okul bilgileri", () => {
  it("ad değişikliği doğrudan kaydedilir; üst çubuktaki okul adı da değişir", async () => {
    const istekler = okulApisi();
    const { kullanici } = await ac();
    const ad = screen.getByLabelText(/Okulun adı/);
    await kullanici.clear(ad);
    await kullanici.type(ad, "Cumhuriyet Lisesi");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));

    expect(await screen.findByText("Okul bilgileri kaydedildi.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yol: "okul", govde: { ad: "Cumhuriyet Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8,
      ...HAFTA_VARSAYILAN, etkileri_onayla: false } }]);
    expect(within(screen.getByRole("banner")).getByText("Cumhuriyet Lisesi")).toBeInTheDocument();
  });

  it("azaltırken kaydetmeden önce uyarır; etkiler pencerede listelenir; Vazgeç hiçbir şey değiştirmez", async () => {
    const istekler = okulApisi(ETKILER);
    const { kullanici } = await ac();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
    const saat = screen.getByLabelText(/Günde kaç ders saati/);
    await kullanici.clear(saat);
    await kullanici.type(saat, "6");
    expect(screen.getByRole("note")).toHaveTextContent(/müsaitlik kayıtları silinir; daha önce üretilmiş programlar değişmez/);

    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    const pencere = await screen.findByRole("dialog", { name: "Bu değişiklik mevcut kayıtları etkileyecek" });
    expect(within(pencere).getAllByRole("listitem").map((l) => l.textContent)).toEqual(ETKILER);
    expect(istekler).toEqual([{ yol: "ayar-etkisi", govde: { gun_sayisi: 5, gunluk_ders_saati: 6, gun_saatleri: null } }]);

    await kullanici.click(within(pencere).getByRole("button", { name: "Vazgeç" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(istekler).toHaveLength(1); // kaydedilmedi
  });

  it("onaylanınca etkileri onaylayarak kaydeder", async () => {
    const istekler = okulApisi(ETKILER);
    const { kullanici } = await ac();
    await kullanici.selectOptions(screen.getByLabelText(/Haftada kaç gün/), "6");
    await kullanici.selectOptions(screen.getByLabelText(/Haftada kaç gün/), "5"); // değişmedi
    const saat = screen.getByLabelText(/Günde kaç ders saati/);
    await kullanici.clear(saat);
    await kullanici.type(saat, "7");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    await kullanici.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Kaydet ve uygula" }));

    expect(await screen.findByText("Okul bilgileri kaydedildi.")).toBeInTheDocument();
    expect(istekler.at(-1)).toEqual({ yol: "okul", govde: { ad: BEN_ORNEK.okul.ad, gun_sayisi: 5, gunluk_ders_saati: 7,
      ...HAFTA_VARSAYILAN, etkileri_onayla: true } });
  });

  it("azaltmanın etkisi yoksa pencere açılmadan kaydeder", async () => {
    const istekler = okulApisi([]);
    const { kullanici } = await ac();
    const saat = screen.getByLabelText(/Günde kaç ders saati/);
    await kullanici.clear(saat);
    await kullanici.type(saat, "7");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    expect(await screen.findByText("Okul bilgileri kaydedildi.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(istekler.map((i) => i.yol)).toEqual(["ayar-etkisi", "okul"]);
  });

  it("sunucu önizlemeden sonra etki bulursa (409) etkiler yine pencerede gösterilir", async () => {
    okulApisi(ETKILER);
    sunucu.use(http.post("/api/okul/ayar-etkisi", () => HttpResponse.json({ etkiler: [] }))); // önizleme boş döndü
    const { kullanici } = await ac();
    const saat = screen.getByLabelText(/Günde kaç ders saati/);
    await kullanici.clear(saat);
    await kullanici.type(saat, "6");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    const pencere = await screen.findByRole("dialog", { name: "Bu değişiklik mevcut kayıtları etkileyecek" });
    expect(within(pencere).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("günlere göre ders saati, öğle arası, zil saatleri (K3)", () => {
  it("varsayılan sade: tek 'günde kaç ders saati' alanı; gün kutuları ve zil alanları kapalı", async () => {
    okulApisi();
    await ac();
    expect(screen.getByLabelText(/Günde kaç ders saati/)).toHaveValue(8);
    expect(screen.getByRole("checkbox", { name: /Günlere göre farklı/ })).not.toBeChecked();
    expect(screen.queryByLabelText("Cuma")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("İlk ders başlıyor")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Öğle arası")).toHaveValue("");
  });

  it("'günlere göre farklı' açılınca her gün bugünkü değerle başlar; cumayı kısaltmak önce etkileri sorar", async () => {
    const istekler = okulApisi(ETKILER);
    const { kullanici } = await ac();
    await kullanici.click(screen.getByRole("checkbox", { name: /Günlere göre farklı/ }));
    expect(screen.queryByLabelText(/Günde kaç ders saati/)).not.toBeInTheDocument();
    const gunler = within(screen.getByRole("group", { name: "Her gün kaç ders saati var" }));
    expect(["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"].map((g) => (gunler.getByLabelText(g) as HTMLInputElement).value))
      .toEqual(["8", "8", "8", "8", "8"]);
    expect(screen.queryByRole("note")).not.toBeInTheDocument(); // henüz hiçbir gün kısalmadı

    await kullanici.clear(gunler.getByLabelText("Cuma"));
    await kullanici.type(gunler.getByLabelText("Cuma"), "5");
    expect(screen.getByRole("note")).toHaveTextContent(/müsaitlik kayıtları silinir/);
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));

    const pencere = await screen.findByRole("dialog", { name: "Bu değişiklik mevcut kayıtları etkileyecek" });
    expect(istekler).toEqual([{ yol: "ayar-etkisi", govde: { gun_sayisi: 5, gun_saatleri: [8, 8, 8, 8, 5] } }]);
    await kullanici.click(within(pencere).getByRole("button", { name: "Kaydet ve uygula" }));
    expect(await screen.findByText("Okul bilgileri kaydedildi.")).toBeInTheDocument();
    expect(istekler.at(-1)?.govde).toMatchObject({ gun_sayisi: 5, gun_saatleri: [8, 8, 8, 8, 5], etkileri_onayla: true });
    expect(istekler.at(-1)?.govde).not.toHaveProperty("gunluk_ders_saati");
  });

  it("öğle arası ve zil saatleri: önizleme öğle arasını sayar, kaydedince gönderilir", async () => {
    const istekler = okulApisi();
    const { kullanici } = await ac();
    await kullanici.selectOptions(screen.getByLabelText("Öğle arası"), "4");
    await kullanici.click(screen.getByRole("checkbox", { name: /Zil saatlerini göster/ }));
    expect(screen.getByLabelText("İlk ders başlıyor")).toHaveValue("08:30");
    const ogleDk = screen.getByLabelText("Öğle arası (dk)");
    await kullanici.clear(ogleDk);
    await kullanici.type(ogleDk, "50");

    const onizleme = screen.getByRole("list", { name: "Zil saatleri önizlemesi" });
    const satirlar = within(onizleme).getAllByRole("listitem").map((l) => l.textContent);
    expect(satirlar.slice(0, 6)).toEqual([
      "1. ders 08:30–09:10", "2. ders 09:20–10:00", "3. ders 10:10–10:50", "4. ders 11:00–11:40",
      "Öğle arası 11:40–12:30", "5. ders 12:30–13:10",
    ]);

    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    expect(await screen.findByText("Okul bilgileri kaydedildi.")).toBeInTheDocument();
    // Kısalma yok: ayar etkisi sorulmadı. Zil önizlemesi sunucudan, son taslakla istendi.
    expect(istekler.filter((i) => i.yol !== "zil-onizleme").map((i) => i.yol)).toEqual(["okul"]);
    expect(istekler.filter((i) => i.yol === "zil-onizleme").at(-1)?.govde).toEqual({
      ilk_ders_baslangic: "08:30", saat_sayisi: 8, ders_suresi_dk: 40, teneffus_dk: 10, ogle_arasi_dk: 50, ogle_arasi_sonra: 4,
    });
    expect(istekler.find((i) => i.yol === "okul")!.govde).toMatchObject({ ogle_arasi_sonra: 4, ilk_ders_baslangic: "08:30", ogle_arasi_dk: 50 });
  });

  it("öğle arası son dersten sonra seçilemez; zil saati biçimi denetlenir", async () => {
    const istekler = okulApisi();
    const { kullanici } = await ac();
    // Seçenekler en uzun günün son dersinden öncesine kadar: 8 saatte 7.
    const secenekler = within(screen.getByLabelText("Öğle arası")).getAllByRole("option").map((o) => o.textContent);
    expect(secenekler.at(-1)).toBe("7. dersten sonra");
    await kullanici.selectOptions(screen.getByLabelText("Öğle arası"), "7");
    const saat = screen.getByLabelText(/Günde kaç ders saati/);
    await kullanici.clear(saat);
    await kullanici.type(saat, "7");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    expect(screen.getByLabelText("Öğle arası")).toHaveAccessibleDescription(/Öğle arası son dersten önce olmalı/);
    expect(istekler).toEqual([]);
  });
});

describe("dağılım şekli (K4)", () => {
  it("okul önerisi açık; saate göre şekil değiştirilir, yalnızca öneriden farklı olan gönderilir", async () => {
    const govdeler: unknown[] = [];
    sunucu.use(http.put("/api/ders-programi/kurallar/:tur", async ({ request, params }) => {
      govdeler.push({ tur: params.tur, govde: await request.json() });
      return HttpResponse.json(ORNEK_KURALLAR[0]);
    }));
    const { kullanici } = await ac();
    const bolum = within(await screen.findByRole("region", { name: "Dağılım şekli (blok dersler)" }));
    expect(bolum.getByRole("checkbox", { name: /Dersleri bloklara böl/ })).toBeChecked();
    expect(bolum.getByRole("combobox", { name: "5 saatlik ders" })).toHaveDisplayValue("2+2+1 (önerilen)");
    await kullanici.selectOptions(bolum.getByRole("combobox", { name: "4 saatlik ders" }), "2+1+1");
    await kullanici.click(bolum.getByRole("button", { name: "Dağılım şeklini kaydet" }));
    await waitFor(() => expect(govdeler).toEqual([
      { tur: "blok_deseni", govde: { parametreler: { otomatik: true, varsayilanlar: { "4": [2, 1, 1] } } } }]));
  });

  it("bloklar kapatılabilir; tablo gizlenir", async () => {
    const govdeler: unknown[] = [];
    sunucu.use(http.put("/api/ders-programi/kurallar/:tur", async ({ request }) => {
      govdeler.push(await request.json());
      return HttpResponse.json(ORNEK_KURALLAR[0]);
    }));
    const { kullanici } = await ac();
    const bolum = within(await screen.findByRole("region", { name: "Dağılım şekli (blok dersler)" }));
    await kullanici.click(bolum.getByRole("checkbox", { name: /Dersleri bloklara böl/ }));
    expect(bolum.queryByRole("combobox")).not.toBeInTheDocument();
    await kullanici.click(bolum.getByRole("button", { name: "Dağılım şeklini kaydet" }));
    await waitFor(() => expect(govdeler).toEqual([{ parametreler: { otomatik: false, varsayilanlar: {} } }]));
  });
});

describe("kurallar", () => {
  it("değişen kural kaydedilir; aralık dışı değer sunucuya gitmez", async () => {
    const govdeler: { tur: string; govde: unknown }[] = [];
    sunucu.use(http.put("/api/ders-programi/kurallar/:tur", async ({ request, params }) => {
      govdeler.push({ tur: params.tur as string, govde: await request.json() });
      return HttpResponse.json(ORNEK_KURALLAR[0]);
    }));
    const { kullanici } = await ac();
    const n = await screen.findByLabelText("Aynı dersin günlük sınırı");
    expect(n).toHaveValue(2);
    expect(n).toHaveAccessibleDescription("Aynı ders bir sınıfa günde en fazla bu kadar saat konur. Varsayılan: 2.");

    await kullanici.clear(n);
    await kullanici.type(n, "0");
    await kullanici.click(screen.getByRole("button", { name: "Kuralları kaydet" }));
    expect(n).toHaveAccessibleDescription(/1 ile 8 arasında bir sayı girin/);
    expect(govdeler).toEqual([]);

    await kullanici.clear(n);
    await kullanici.type(n, "3");
    await kullanici.click(screen.getByRole("button", { name: "Kuralları kaydet" }));
    expect(await screen.findByText("Kurallar kaydedildi.")).toBeInTheDocument();
    expect(govdeler).toEqual([{ tur: "gunluk_ders_siniri", govde: { parametreler: { n: 3 } } }]);
  });
});

describe("gelişmiş: kuralların önemi", () => {
  it("üç seviyeli seçim; varsayılan işaretli; yalnızca değişen kaydedilir", async () => {
    const govdeler: { tur: string; govde: unknown }[] = [];
    sunucu.use(http.put("/api/ders-programi/kurallar/:tur", async ({ request, params }) => {
      govdeler.push({ tur: params.tur as string, govde: await request.json() });
      return HttpResponse.json(ORNEK_KURALLAR[5]);
    }));
    const { kullanici } = await ac();
    await kullanici.click(await screen.findByText("Gelişmiş: kuralların önemi ve ikincil kurallar"));
    const bosGun = screen.getByRole("group", { name: "Öğretmene boş gün" });
    expect(within(bosGun).getByRole("radio", { name: /^Önemli/ })).toBeChecked();
    expect(within(bosGun).getByText("(varsayılan)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gelişmiş ayarları kaydet" })).toBeDisabled();

    await kullanici.click(within(bosGun).getByRole("radio", { name: "Çok önemli" }));
    await kullanici.click(screen.getByRole("button", { name: "Gelişmiş ayarları kaydet" }));
    expect(await screen.findByText("Gelişmiş ayarlar kaydedildi.")).toBeInTheDocument();
    expect(govdeler).toEqual([{ tur: "bos_gun", govde: { seviye: "cok_onemli" } }]);
  });

  it("ikincil kurallar (K6): günde en az ders, yayılım ve yük eşikleri kaydedilir", async () => {
    const govdeler: { tur: string; govde: unknown }[] = [];
    sunucu.use(http.put("/api/ders-programi/kurallar/:tur", async ({ request, params }) => {
      govdeler.push({ tur: params.tur as string, govde: await request.json() });
      return HttpResponse.json(ORNEK_KURALLAR[5]);
    }));
    const { kullanici } = await ac();
    await kullanici.click(await screen.findByText("Gelişmiş: kuralların önemi ve ikincil kurallar"));
    const enAz = screen.getByRole("group", { name: "Öğretmen bir iki saat için gelmesin" });
    const k = within(enAz).getByRole("spinbutton", { name: "Geldiği günde en az kaç ders" });
    expect(k).toHaveValue(2);
    await kullanici.clear(k);
    await kullanici.type(k, "3");
    // Yayılım okul genelinde açılamaz (ADR 0024): onay kutusu yok, yalnızca yönlendirme.
    const yayilim = screen.getByRole("group", { name: "Aynı ders günlere yayılsın" });
    expect(within(yayilim).queryByRole("checkbox")).not.toBeInTheDocument();
    expect(within(yayilim).getByText(/Hangi derste açık olacağı/)).toBeInTheDocument();
    const yuk = screen.getByRole("group", { name: "Öğretmenin haftalık ders yükü" });
    const alt = within(yuk).getByRole("spinbutton", { name: "Alt eşik (saat)" });
    await kullanici.clear(alt);
    await kullanici.type(alt, "15");
    await kullanici.click(screen.getByRole("button", { name: "Gelişmiş ayarları kaydet" }));
    expect(await screen.findByText("Gelişmiş ayarlar kaydedildi.")).toBeInTheDocument();
    expect(govdeler).toEqual([
      { tur: "gunluk_en_az_ders", govde: { parametreler: { k: 3 } } },
      { tur: "haftalik_yuk", govde: { parametreler: { alt: 15, ust: 0 } } },
    ]);
  });

  it("elle girilmiş özel değer açıklanır", async () => {
    const ozel = ORNEK_KURALLAR.map((k) => (k.tur === "tercih_etmez" ? { ...k, seviye: "ozel" as const, agirlik: 7, varsayilan: false } : k));
    sunucu.use(http.get("/api/ders-programi/kurallar", () => HttpResponse.json(ozel)));
    const { kullanici } = await ac();
    await kullanici.click(await screen.findByText("Gelişmiş: kuralların önemi ve ikincil kurallar"));
    const grup = screen.getByRole("group", { name: "Öğretmenin tercih etmediği saatler" });
    expect(within(grup).getByText(/elle girilmiş özel bir değer var \(7\)/)).toBeInTheDocument();
    expect(within(grup).getAllByRole("radio").some((r) => (r as HTMLInputElement).checked)).toBe(false);
  });
});

describe("özel ayarların özeti", () => {
  const AYSE = "11111111-1111-1111-1111-111111111111";
  const MAT = "22222222-2222-2222-2222-222222222222";
  const SUBE = "33333333-3333-3333-3333-333333333333";

  /** Kurallar: öğretmene özel M ve şube + derse özel N. DELETE istekleri kaydedilir ve listeden düşer. */
  function ozelApi() {
    let ozelM = [{ kapsam: { ogretmen_id: AYSE, ders_id: null, sinif_id: null }, ad: "Ayşe Yılmaz", parametreler: { m: 6 } }];
    const ozelN = [{ kapsam: { ogretmen_id: null, ders_id: MAT, sinif_id: SUBE }, ad: "9-A · Matematik", parametreler: { n: 3 } }];
    const silinen: string[] = [];
    sunucu.use(
      http.get("/api/ders-programi/kurallar", () =>
        HttpResponse.json(ORNEK_KURALLAR.map((k) =>
          k.tur === "ogretmen_gunluk_siniri" ? { ...k, ozel_ayarlar: ozelM }
            : k.tur === "gunluk_ders_siniri" ? { ...k, ozel_ayarlar: ozelN } : k))),
      http.delete("/api/ders-programi/kurallar/:tur/ozel", ({ request, params }) => {
        silinen.push(`${String(params.tur)}?${new URL(request.url).searchParams}`);
        ozelM = [];
        return HttpResponse.json(ORNEK_KURALLAR[1]);
      }),
    );
    return silinen;
  }

  it("özel ayar yoksa söyler", async () => {
    await ac();
    const bolum = screen.getByRole("region", { name: "Özel ayarlar" });
    expect(within(bolum).getByText("Özel ayar yok: bütün kurallar okul genelinde aynı.")).toBeInTheDocument();
  });

  it("bütün özel ayarlar adlarıyla ve okul değeriyle tek listede", async () => {
    ozelApi();
    await ac();
    const liste = await screen.findByRole("list", { name: "Özel ayarlar" });
    const maddeler = within(liste).getAllByRole("listitem").map((m) => m.textContent);
    expect(maddeler).toEqual([
      expect.stringContaining("9-A · Matematik: günde en çok 3 saatAynı dersin günlük sınırı (okul geneli: 2)"),
      expect.stringContaining("Ayşe Yılmaz: günde en çok 6 saat derse girerÖğretmenin günlük ders sınırı (okul geneli: 8)"),
    ]);
  });

  it("kaldırınca yalnızca o kapsam sorguya konur; liste tazelenir", async () => {
    const silinen = ozelApi();
    const { kullanici } = await ac();
    await kullanici.click(await screen.findByRole("button", { name: "Ayşe Yılmaz: Öğretmenin günlük ders sınırı özel ayarını kaldır" }));
    expect(await screen.findByText("Ayşe Yılmaz için özel ayar kaldırıldı; okul değeri geçerli (okul geneli: 8).")).toBeInTheDocument();
    expect(silinen).toEqual([`ogretmen_gunluk_siniri?ogretmen_id=${AYSE}`]);
    await waitFor(() => expect(screen.queryByText(/Ayşe Yılmaz: günde en çok/)).toBeNull());
    expect(screen.getByText(/9-A · Matematik/)).toBeInTheDocument();
  });
});

describe("çıkışta bildirimler temizlenir", () => {
  it("önceki kullanıcının bildirimi giriş sayfasında kalmaz", async () => {
    okulApisi();
    const { kullanici } = await ac();
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    expect(await screen.findByText("Okul bilgileri kaydedildi.")).toBeInTheDocument();
    await kullanici.click(screen.getByRole("button", { name: "Çıkış" }));
    await waitFor(() => expect(screen.queryByText("Okul bilgileri kaydedildi.")).not.toBeInTheDocument());
  });
});
