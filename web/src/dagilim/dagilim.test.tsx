/** Ders dağılımı sayfası: şube, öğretmen ve ders görünümleri; erken uyarılar; toplu atama. */
import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { uygulamayiCiz } from "../test/yardimcilar";

const durumKutusu = () => screen.findByRole("region", { name: "Ders dağılımının durumu" });
const sube = (ad: RegExp) => within(screen.getByRole("navigation", { name: "Şubeler" })).getByRole("button", { name: ad });

describe("öğretmeni seçilmemiş dersler", () => {
  it("sayısı sayfanın üstünde, şube listesinde ve satırda görünür", async () => {
    dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi");
    const durum = await durumKutusu();
    expect(durum).toHaveTextContent("2 dersin öğretmeni seçilmedi (2 şubede: 9-B, 9-C).");
    expect(sube(/^9-B/)).toHaveTextContent("1 öğretmensiz");
    expect(sube(/^9-A/)).not.toHaveTextContent("öğretmensiz");

    await kullanici.click(within(durum).getByRole("button", { name: "İlk eksik şubeyi aç" }));
    expect(sube(/^9-B/)).toHaveAttribute("aria-current", "true");
    const satir = screen.getByRole("row", { name: /Matematik/ });
    expect(satir).toHaveTextContent("Öğretmen seçilmedi");
    expect(within(satir).getByRole("combobox", { name: "9-B Matematik öğretmeni" })).toHaveValue("");
  });

  it("hepsi seçilince durum iyi olarak değişir", async () => {
    const api = dagilimApisiKur({
      ozetGuncelle: (d) => {
        d.ozet.ogretmensiz_atama = d.atamalar.filter((a) => !a.ogretmen_id).length;
        d.ozet.siniflar = d.ozet.siniflar.map((s) => ({
          ...s, ogretmensiz_atama: d.atamalar.filter((a) => a.sinif_id === s.sinif_id && !a.ogretmen_id).length,
        }));
      },
    });
    api.atamalar = api.atamalar.filter((a) => a.id !== "a-9c-mat");
    api.ozet.ogretmensiz_atama = 1;
    api.ozet.siniflar = api.ozet.siniflar.map((s) => (s.sinif_id === "s-9c" ? { ...s, ogretmensiz_atama: 0 } : s));
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-9b");
    await kullanici.selectOptions(await screen.findByRole("combobox", { name: "9-B Matematik öğretmeni" }), "o-sule");
    expect(await durumKutusu()).toHaveTextContent(/Bütün derslerin öğretmeni seçildi/);
  });
});

describe("öğretmen seçici", () => {
  it("branşı uyanlar üstte ayrı grupta, diğerleri altta seçilebilir; her öğretmenin yükü yazar", async () => {
    dagilimApisiKur();
    uygulamayiCiz("/ders-dagilimi?sinif=s-9b");
    const secici = await screen.findByRole("combobox", { name: "9-B Matematik öğretmeni" });
    const gruplar = within(secici).getAllByRole("group");
    expect(gruplar.map((g) => g.getAttribute("label"))).toEqual(["Branşı uyan: Matematik", "Diğer öğretmenler"]);
    expect(within(gruplar[0]!).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Ayşe Yılmaz (Matematik Öğretmeni) · 0 / 40 saat",
      "Şule Kaya (Matematik) · 6 / 40 saat",
    ]);
    expect(within(gruplar[1]!).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Ali Çelik (İngilizce) · 0 / 40 saat",
      "Zeynep Demir (Fizik) · 2 / 40 saat",
    ]);
  });

  it("seçim hemen kaydedilir; öğretmenin kapasitesi aşıldıysa sunucunun mesajı uyarı olarak gelir", async () => {
    const MESAJ = "Şule Kaya'nın 12 saat dersi var, müsait olduğu 10 saat var.";
    const api = dagilimApisiKur({
      ozetGuncelle: (d) => {
        d.ozet.ogretmenler = d.ozet.ogretmenler.map((o) =>
          o.ogretmen_id === "o-sule" ? { ...o, ders_saati: 12, kullanilabilir_saat: 10, asim: true, mesaj: MESAJ } : o,
        );
      },
    });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-9b");
    await kullanici.selectOptions(await screen.findByRole("combobox", { name: "9-B Matematik öğretmeni" }), "o-sule");

    await waitFor(() => expect(api.istekler).toEqual([{ yontem: "PATCH", yol: "atamalar/a-9b-mat", govde: { ogretmen_id: "o-sule" } }]));
    expect(await screen.findByText("9-B Matematik: Şule Kaya seçildi.")).toBeInTheDocument();
    expect(await screen.findByText(MESAJ)).toBeInTheDocument();
    // Seçicideki seçenek de aşımı söyler.
    const secenek = within(screen.getByRole("combobox", { name: "9-B Matematik öğretmeni" })).getByRole("option", { name: /Şule Kaya/ });
    expect(secenek).toHaveTextContent("Şule Kaya · 12 / 10 saat · kapasite aşıldı");
    // Seçili öğretmenin seçeneğinde branş yazmaz (kapalı seçiciye sığsın); tam metin title'da.
    expect(screen.getByRole("combobox", { name: "9-B Matematik öğretmeni" })).toHaveAttribute(
      "title", "Şule Kaya (Matematik) · 12 / 10 saat · kapasite aşıldı");
  });
});

describe("şube görünümü", () => {
  it("şubenin toplamı kapasiteyi aşınca kırmızı uyarı ve sunucunun mesajı", async () => {
    const api = dagilimApisiKur();
    const MESAJ = "9-A sınıfının haftada 42 saat dersi var, haftalık kapasite 40 saat (5 gün × 8 saat).";
    api.ozet.siniflar = api.ozet.siniflar.map((s) =>
      s.sinif_id === "s-9a" ? { ...s, ders_saati: 42, asim: true, mesaj: MESAJ } : s,
    );
    uygulamayiCiz("/ders-dagilimi?sinif=s-9a");
    expect(await screen.findByText(MESAJ)).toBeInTheDocument();
    expect(sube(/^9-A/)).toHaveTextContent("42/40 saat, kapasite aşıldı");
    expect(await durumKutusu()).toHaveTextContent("1 şubenin ders saati haftalık kapasiteyi aşıyor (9-A).");
  });

  it("aşım yoksa toplam ve kapasite yazar", async () => {
    dagilimApisiKur();
    uygulamayiCiz("/ders-dagilimi?sinif=s-9a");
    expect(await screen.findByText(/Toplam/)).toHaveTextContent("Toplam 8 saat; haftalık kapasite 40 saat.");
  });

  it("haftalık saat Enter ile bir kez kaydedilir", async () => {
    const api = dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-9a");
    const saat = await screen.findByRole("spinbutton", { name: "9-A Matematik haftalık saat" });
    await kullanici.clear(saat);
    await kullanici.type(saat, "5{Enter}");
    await waitFor(() => expect(api.istekler).toHaveLength(1));
    expect(api.istekler[0]).toEqual({ yontem: "PATCH", yol: "atamalar/a-9a-mat", govde: { haftalik_saat: 5 } });
    await kullanici.tab(); // alandan çıkmak ikinci bir istek göndermez
    expect(api.istekler).toHaveLength(1);
  });

  it("geçersiz saat kaydedilmez, eski değer geri gelir", async () => {
    const api = dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-9a");
    const saat = await screen.findByRole("spinbutton", { name: "9-A Matematik haftalık saat" });
    await kullanici.clear(saat);
    await kullanici.type(saat, "0{Enter}");
    expect(saat).toHaveValue(6);
    expect(api.istekler).toEqual([]);
  });

  it("ders onayla kaldırılır", async () => {
    const api = dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-9a");
    await kullanici.click(await screen.findByRole("button", { name: "Fizik dersini kaldır" }));
    const pencere = screen.getByRole("dialog", { name: "Fizik dersi kaldırılsın mı?" });
    await kullanici.click(within(pencere).getByRole("button", { name: "Kaldır" }));
    await waitFor(() => expect(api.istekler).toEqual([{ yontem: "DELETE", yol: "atamalar/a-9a-fiz", govde: undefined }]));
    expect(await screen.findByText("Fizik, 9-A şubesinden kaldırıldı.")).toBeInTheDocument();
  });

  it("dersi olmayan şube: şablona yönlendirir, aşağıdan ders eklenir", async () => {
    const api = dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-10a");
    expect(await screen.findByText("10-A şubesine henüz ders eklenmedi.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "10. sınıf şablonunu aç" })).toHaveAttribute("href", "/seviye-sablonu?seviye=10");

    await kullanici.selectOptions(screen.getByRole("combobox", { name: "Ders" }), "d-kim");
    await kullanici.type(screen.getByRole("spinbutton", { name: "Haftalık saat" }), "3");
    await kullanici.click(screen.getByRole("button", { name: "Ekle" }));
    await waitFor(() =>
      expect(api.istekler).toEqual([{ yontem: "POST", yol: "atamalar",
        govde: { sinif_id: "s-10a", ders_id: "d-kim", haftalik_saat: 3, ogretmen_id: null } }]),
    );
    expect(await screen.findByRole("row", { name: /Kimya/ })).toHaveTextContent("Öğretmen seçilmedi");
  });
});

describe("öğretmen görünümü", () => {
  it("kapasitesi aşılan öğretmen en üstte, mesajıyla; dersinden şubesine gidilir", async () => {
    const api = dagilimApisiKur();
    const MESAJ = "Zeynep Demir'in 2 saat dersi var, müsait olduğu 0 saat var.";
    api.ozet.ogretmenler = api.ozet.ogretmenler.map((o) =>
      o.ogretmen_id === "o-zeynep" ? { ...o, kullanilabilir_saat: 0, musait_saat: 0, asim: true, mesaj: MESAJ } : o,
    );
    // Önce 9-C seçili: "9-A şubesine git" seçimi gerçekten değiştirmeli (varsayılan şube de 9-A'dır).
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=ogretmen&sinif=s-9c");
    const basliklar = await screen.findAllByRole("heading", { level: 3 });
    expect(basliklar.map((b) => b.textContent)).toEqual([
      "Zeynep Demir · Fizik", "Ali Çelik · İngilizce", "Ayşe Yılmaz · Matematik Öğretmeni", "Şule Kaya · Matematik",
    ]);
    expect(screen.getByText(MESAJ)).toBeInTheDocument();
    expect(await durumKutusu()).toHaveTextContent("1 öğretmenin ders yükü kapasitesini aşıyor.");

    const sule = basliklar[3]!.closest("li")!;
    expect(sule).toHaveTextContent("6 / 40 saat");
    await kullanici.click(within(sule).getByRole("button", { name: "Derslerini göster (1)" }));
    await kullanici.click(within(sule).getByRole("button", { name: "9-A şubesine git" }));

    // Durum yukarıda: sayfa şube sekmesine 9-A seçili geçer.
    expect(screen.getByRole("tab", { name: "Şubelere göre" })).toHaveAttribute("aria-selected", "true");
    expect(sube(/^9-A/)).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("heading", { name: "9-A şubesinin dersleri" })).toBeInTheDocument();
  });
});

describe("öğretmen görünümü: haftalık yük uyarısı (K6)", () => {
  it("eşiğin dışındaki öğretmenin kartında uyarı, kapasite aşımından ayrı", async () => {
    const api = dagilimApisiKur();
    const UYARI = "Şule Kaya haftada 6 saat derse giriyor, alt eşik 15 saat (9 saat eksik).";
    api.ozet.ogretmenler = api.ozet.ogretmenler.map((o) => (o.ogretmen_id === "o-sule" ? { ...o, yuk_uyarisi: UYARI } : o));
    uygulamayiCiz("/ders-dagilimi?gorunum=ogretmen");
    const basliklar = await screen.findAllByRole("heading", { level: 3 });
    const sule = basliklar.find((b) => b.textContent?.startsWith("Şule"))!.closest("li")!;
    expect(sule).toHaveTextContent(UYARI);
    expect(await durumKutusu()).not.toHaveTextContent("kapasitesini aşıyor");
  });
});

describe("ders görünümü: birden fazla şubeye aynı öğretmen", () => {
  it("öğretmensizleri işaretle, öğretmeni seç, tek istekle ver", async () => {
    const api = dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=ders&ders=d-mat");
    const ver = await screen.findByRole("button", { name: /İşaretli 0 şubeye ver/ });
    expect(ver).toBeDisabled();

    await kullanici.click(screen.getByRole("button", { name: "Öğretmeni seçilmemişleri işaretle" }));
    expect(screen.getByRole("checkbox", { name: "9-B işaretle" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "9-C işaretle" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "9-A işaretle" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Bütün şubeleri işaretle" })).toHaveProperty("indeterminate", true);
    expect(screen.getByRole("button", { name: "İşaretli 2 şubeye ver" })).toBeDisabled(); // öğretmen seçilmedi

    await kullanici.selectOptions(screen.getByRole("combobox", { name: "İşaretli şubelere verilecek öğretmen" }), "o-ayse");
    await kullanici.click(screen.getByRole("button", { name: "İşaretli 2 şubeye ver" }));

    await waitFor(() =>
      expect(api.istekler).toEqual([{ yontem: "POST", yol: "atamalar/toplu-ogretmen",
        govde: { atama_idleri: ["a-9b-mat", "a-9c-mat"], ogretmen_id: "o-ayse" } }]),
    );
    expect(await screen.findByText(
      "Matematik dersinin öğretmeni 2 şubede (9-B, 9-C) Ayşe Yılmaz olarak kaydedildi.",
    )).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "9-B Matematik öğretmeni" })).toHaveValue("o-ayse");
    expect(screen.getByRole("checkbox", { name: "9-B işaretle" })).not.toBeChecked(); // işaretler temizlendi
  });

  it("tümünü işaretle kutusu bütün şubeleri seçer ve kaldırır", async () => {
    dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=ders&ders=d-mat");
    const tumu = await screen.findByRole("checkbox", { name: "Bütün şubeleri işaretle" });
    await kullanici.click(tumu);
    expect(screen.getAllByRole("checkbox", { name: /^9-. işaretle$/ }).every((k) => (k as HTMLInputElement).checked)).toBe(true);
    await kullanici.click(tumu);
    expect(screen.getAllByRole("checkbox", { name: /^9-. işaretle$/ }).some((k) => (k as HTMLInputElement).checked)).toBe(false);
  });

  it("şube görünümündeki 'Bütün şubeler' o dersin görünümünü açar", async () => {
    dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?sinif=s-9a");
    await kullanici.click(await screen.findByRole("button", { name: "Matematik dersini bütün şubelerde göster" }));
    expect(screen.getByRole("tab", { name: "Derslere göre" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("table", { name: "Matematik dersinin şubeleri" })).toBeInTheDocument();
  });
});

describe("sekmeler", () => {
  it("ok tuşlarıyla geçilir; seçili sekme panelin adıdır", async () => {
    dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/ders-dagilimi");
    const sube = await screen.findByRole("tab", { name: "Şubelere göre" });
    expect(screen.getByRole("tabpanel", { name: "Şubelere göre" })).toBeInTheDocument();
    sube.focus();
    await kullanici.keyboard("{ArrowRight}");
    const ogretmen = screen.getByRole("tab", { name: "Öğretmenlere göre" });
    expect(ogretmen).toHaveFocus();
    expect(ogretmen).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Öğretmenlere göre" })).toBeInTheDocument();
    await kullanici.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Derslere göre" })).toHaveFocus();
    await kullanici.keyboard("{ArrowRight}"); // sondan başa döner
    expect(screen.getByRole("tab", { name: "Şubelere göre" })).toHaveFocus();
  });
});

describe("ön koşullar", () => {
  it("öğretmen yoksa ne yapılacağını söyler", async () => {
    dagilimApisiKur({ ogretmenler: [] });
    uygulamayiCiz("/ders-dagilimi");
    expect(await screen.findByRole("heading", { name: "Ders dağılımı için önce listeleri doldurun" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Öğretmenleri ekleyin" })).toHaveAttribute("href", "/ogretmenler");
    expect(screen.queryByRole("link", { name: "Sınıfları ekleyin" })).not.toBeInTheDocument();
  });

  it("hiç ders ataması yoksa şablona yönlendirir", async () => {
    dagilimApisiKur({ atamalar: [] });
    uygulamayiCiz("/ders-dagilimi");
    expect(await durumKutusu()).toHaveTextContent(/Henüz hiçbir şubeye ders eklenmedi/);
  });
});
