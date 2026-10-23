/** Öğretmen detay sayfası: kişisel ayarlar ve müsaitlik çizelgesi (K2 + 5.5). */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "../api/sema";
import { BEN_ORNEK, ORNEK_KURALLAR, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";
import { degisiklikler, durumHaritasi, komsu, sonrakiDurum, topluHedef, uygula } from "./musaitlik";

type Cizelge = components["schemas"]["MusaitlikCizelgesi"];
type Degisiklik = components["schemas"]["MusaitlikDegisikligi"];

const OGRETMENLER = [
  { id: "o2", ad: "Mehmet Kaya", brans: "Türk Dili" },
  { id: "o1", ad: "Ayşe Yılmaz", brans: "Matematik" },
  { id: "o3", ad: "Zeynep Demir", brans: "Fizik" },
];
const YUK = { ders_saati: 18, musait_saat: 40, kullanilabilir_saat: 40, asim: false, mesaj: null };

/**
 * Sahte API. Müsaitlik PUT'u değişiklikleri uygular ve kaydeder; `yanit` ile cevap değiştirilebilir
 * (hata, gecikme, aşım). Kurallarda boş gün ve günlük sınır öğretmene özel ayarlanabilir.
 */
function apiKur(secenek: { yanit?: (d: Degisiklik[], c: Cizelge) => Promise<Response> | Response } = {}) {
  const cizelgeler = new Map<string, Cizelge>();
  const istekler: Degisiklik[][] = [];
  const ozelIstekleri: { yontem: string; yol: string; govde?: unknown }[] = [];
  let ozelBosGun: { kapsam: { ogretmen_id: string; ders_id: null; sinif_id: null }; ad: string; parametreler: Record<string, number> }[] = [];
  const cizelge = (id: string) => cizelgeler.get(id) ?? { ogretmen_id: id, hucreler: [], yuk: YUK };
  sunucu.use(
    http.get("/api/ogretmenler", () => HttpResponse.json(OGRETMENLER)),
    http.get("/api/ders-programi/kurallar", () =>
      HttpResponse.json(ORNEK_KURALLAR.map((k) =>
        k.tur === "bos_gun" ? { ...k, kapsamlar: ["ogretmen"], ozel_ayarlar: ozelBosGun }
          : k.tur === "ogretmen_gunluk_siniri" ? { ...k, kapsamlar: ["ogretmen"] } : k))),
    http.put("/api/ders-programi/kurallar/:tur/ozel", async ({ request, params }) => {
      const govde = (await request.json()) as { kapsam: { ogretmen_id: string }; parametreler: Record<string, number> };
      ozelIstekleri.push({ yontem: "PUT", yol: String(params.tur), govde });
      if (params.tur === "bos_gun") {
        ozelBosGun = [{ kapsam: { ogretmen_id: govde.kapsam.ogretmen_id, ders_id: null, sinif_id: null }, ad: "Ayşe Yılmaz", parametreler: govde.parametreler }];
      }
      return HttpResponse.json(ORNEK_KURALLAR[0]);
    }),
    http.delete("/api/ders-programi/kurallar/:tur/ozel", ({ request, params }) => {
      ozelIstekleri.push({ yontem: "DELETE", yol: `${String(params.tur)}?${new URL(request.url).searchParams}` });
      ozelBosGun = [];
      return HttpResponse.json(ORNEK_KURALLAR[0]);
    }),
    http.get("/api/ders-programi/ogretmenler/:id/musaitlik", ({ params }) => HttpResponse.json(cizelge(String(params.id)))),
    http.put("/api/ders-programi/ogretmenler/:id/musaitlik", async ({ request, params }) => {
      const { degisiklikler: d } = (await request.json()) as { degisiklikler: Degisiklik[] };
      istekler.push(d);
      const eski = cizelge(String(params.id));
      if (secenek.yanit) return secenek.yanit(d, eski);
      const yeni = { ...eski, hucreler: uygula(eski.hucreler, d) };
      cizelgeler.set(String(params.id), yeni);
      return HttpResponse.json(yeni);
    }),
  );
  return { istekler, ozelIstekleri };
}

const hucre = (etiket: string) => screen.getByRole("button", { name: new RegExp(`^${etiket}:`) });

async function ac(id = "o1") {
  const s = uygulamayiCiz(`/ogretmenler/${id}`);
  await screen.findByRole("table", { name: /müsaitlik çizelgesi/ });
  await waitFor(() => expect(hucre("Pazartesi, 1. saat")).toBeEnabled());
  return s;
}

describe("müsaitlik mantığı", () => {
  it("durum döngüsü, toplu hedef, değişiklik listesi, iyimser uygulama, klavye komşusu", () => {
    expect(["musait", "gelemez", "tercih_etmez"].map((d) => sonrakiDurum(d as never))).toEqual(["gelemez", "tercih_etmez", "musait"]);
    const harita = durumHaritasi([{ gun: 0, saat: 0, durum: "gelemez" }]);
    const gun = [0, 1, 2].map((saat) => ({ gun: 0, saat }));
    expect(topluHedef(harita, gun)).toBe("tercih_etmez"); // ilk hücrenin bir sonraki durumu
    // Zaten hedefte olan ve tekrar eden hücre atlanır.
    expect(degisiklikler(harita, [...gun, { gun: 0, saat: 1 }], "gelemez")).toEqual([
      { gun: 0, saat: 1, durum: "gelemez" }, { gun: 0, saat: 2, durum: "gelemez" }]);
    expect(uygula([{ gun: 0, saat: 0, durum: "gelemez" }], [{ gun: 0, saat: 0, durum: "musait" }, { gun: 1, saat: 0, durum: "tercih_etmez" }]))
      .toEqual([{ gun: 1, saat: 0, durum: "tercih_etmez" }]);
    expect(komsu({ gun: 0, saat: 0 }, "ArrowLeft", 5, 8)).toEqual({ gun: 0, saat: 0 });
    expect(komsu({ gun: 0, saat: 0 }, "ArrowDown", 5, 8)).toEqual({ gun: 0, saat: 1 });
    expect(komsu({ gun: 1, saat: 3 }, "End", 5, 8)).toEqual({ gun: 4, saat: 3 });
    expect(komsu({ gun: 1, saat: 3 }, "a", 5, 8)).toBeNull();
    // Kısa gün (cuma 5 saat): oklar ve End olmayan hücreyi atlar.
    const var_ = (k: { gun: number; saat: number }) => k.gun < 4 || k.saat < 5;
    expect(komsu({ gun: 3, saat: 6 }, "ArrowRight", 5, 8, var_)).toEqual({ gun: 3, saat: 6 });
    expect(komsu({ gun: 1, saat: 6 }, "End", 5, 8, var_)).toEqual({ gun: 3, saat: 6 });
    expect(komsu({ gun: 4, saat: 4 }, "ArrowDown", 5, 8, var_)).toEqual({ gun: 4, saat: 4 });
  });
});

describe("öğretmen sayfası", () => {
  it("öğretmen listesinde ad, öğretmenin sayfasına bağlantıdır", async () => {
    apiKur();
    uygulamayiCiz("/ogretmenler");
    // Üst çubuktaki "Hesabım" bağlantısı da (giriş yapan müdürün adı) Ayşe Yılmaz: tablonun içine bakılır.
    const tablo = await screen.findByRole("table", { name: "Öğretmenler" });
    expect(await within(tablo).findByRole("link", { name: /Ayşe Yılmaz/ })).toHaveAttribute("href", "/ogretmenler/o1");
  });

  it("menüde ayrı müsaitlik sayfası yok; eski adres ilk öğretmenin sayfasına gider", async () => {
    apiKur();
    uygulamayiCiz("/musaitlik");
    expect(await screen.findByRole("heading", { level: 1, name: "Ayşe Yılmaz" })).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Ana menü" })).queryByText("Öğretmen müsaitliği")).toBeNull();
  });

  it("öğretmenler arasında hızlı geçiş: önceki, sonraki, seçim kutusu (ada göre sıralı)", async () => {
    apiKur();
    const { kullanici } = await ac("o1");
    const gecis = screen.getByRole("navigation", { name: "Öğretmenler arasında geçiş" });
    expect(within(gecis).queryByRole("link", { name: /Önceki öğretmen/ })).toBeNull(); // Ayşe ilk
    expect(within(gecis).getByText("1 / 3")).toBeInTheDocument();
    await kullanici.click(within(gecis).getByRole("link", { name: "Sonraki öğretmen: Mehmet Kaya" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Mehmet Kaya" })).toBeInTheDocument();
    // Sayfa her adreste yeniden kurulur: geçiş çubuğu yeniden bulunur.
    const yeniGecis = screen.getByRole("navigation", { name: "Öğretmenler arasında geçiş" });
    await kullanici.selectOptions(within(yeniGecis).getByRole("combobox", { name: "Öğretmen" }), "Zeynep Demir");
    expect(await screen.findByRole("heading", { level: 1, name: "Zeynep Demir" })).toBeInTheDocument();
  });
});

describe("kişisel ayarlar", () => {
  it("okul varsayılanı seçili başlar; özel değer kaydedilir, 'özel' rozeti çıkar; varsayılana dönülür", async () => {
    const { ozelIstekleri } = apiKur();
    const { kullanici } = await ac();
    const bosGun = screen.getByRole("combobox", { name: "Boş gün hedefi" });
    expect(bosGun).toHaveDisplayValue("Okul varsayılanı (1 gün)");
    expect(screen.getByRole("combobox", { name: "Günde en çok ders" })).toHaveDisplayValue("Okul varsayılanı (8 saat)");
    expect(screen.queryByText("özel")).toBeNull();

    await kullanici.selectOptions(bosGun, "0 (boş gün istemiyor)");
    expect(await screen.findByText("Boş gün hedefi: 0 (boş gün istemiyor) kaydedildi.")).toBeInTheDocument();
    expect(ozelIstekleri).toEqual([{ yontem: "PUT", yol: "bos_gun", govde: { kapsam: { ogretmen_id: "o1" }, parametreler: { hedef_bos_gun: 0 } } }]);
    expect(await screen.findByText("özel")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /Boş gün hedefi/ })).toHaveDisplayValue("0 (boş gün istemiyor)");

    await kullanici.selectOptions(screen.getByRole("combobox", { name: /Boş gün hedefi/ }), "Okul varsayılanı (1 gün)");
    await waitFor(() => expect(ozelIstekleri.at(-1)).toEqual({ yontem: "DELETE", yol: "bos_gun?ogretmen_id=o1" }));
    await waitFor(() => expect(screen.queryByText("özel")).toBeNull());
  });
});

describe("müsaitlik çizelgesi", () => {
  it("lejant: üç durum, renk dışında ikonla", async () => {
    apiKur();
    await ac();
    const lejant = screen.getByRole("list", { name: "Lejant" });
    expect(within(lejant).getAllByRole("listitem").map((l) => l.textContent)).toEqual([
      "Müsait (boş)", "Gelemez: bu saate ders konmaz", "Tercih etmez: mümkünse konmaz"]);
    expect(lejant.querySelectorAll("svg")).toHaveLength(2); // gelemez ve tercih etmez ikonlu
  });

  it("tıklandıkça döner; iyimser: sunucu cevap vermeden hücre değişir", async () => {
    let birak: () => void = () => {};
    const { istekler } = apiKur({
      yanit: async (d, c) => {
        await new Promise<void>((r) => (birak = r));
        return HttpResponse.json({ ...c, hucreler: uygula(c.hucreler, d) });
      },
    });
    const { kullanici } = await ac();
    await kullanici.click(hucre("Pazartesi, 1. saat"));
    // Cevap gelmeden ekranda değişti.
    expect(hucre("Pazartesi, 1. saat")).toHaveAccessibleName("Pazartesi, 1. saat: gelemez");
    expect(hucre("Pazartesi, 1. saat")).toHaveAttribute("data-durum", "gelemez");
    birak();
    await waitFor(() => expect(istekler).toEqual([[{ gun: 0, saat: 0, durum: "gelemez" }]]));
  });

  it("sunucu reddederse hücre eski haline döner ve neden söylenir", async () => {
    apiKur({ yanit: async () => { await delay(20); return HttpResponse.json({ detail: "Sunucu hatası" }, { status: 422 }); } });
    const { kullanici } = await ac();
    await kullanici.click(hucre("Salı, 2. saat"));
    expect(hucre("Salı, 2. saat")).toHaveAttribute("data-durum", "gelemez");
    expect(await screen.findByText("Sunucu hatası Değişiklik geri alındı.")).toBeInTheDocument();
    expect(hucre("Salı, 2. saat")).toHaveAttribute("data-durum", "musait");
  });

  it("klavye: tek sekme durağı, oklarla gezinme, Enter ve boşlukla değiştirme", async () => {
    const { istekler } = apiKur();
    const { kullanici } = await ac();
    const tablo = screen.getByRole("table", { name: /müsaitlik çizelgesi/ });
    const sekmeDuraklari = within(tablo).getAllByRole("button").filter((b) => b.closest("td") && b.tabIndex === 0);
    expect(sekmeDuraklari).toHaveLength(1);
    hucre("Pazartesi, 1. saat").focus();
    await kullanici.keyboard("{ArrowRight}{ArrowDown}");
    expect(hucre("Salı, 2. saat")).toHaveFocus();
    expect(hucre("Salı, 2. saat").tabIndex).toBe(0);
    await kullanici.keyboard("{Enter}");
    await waitFor(() => expect(hucre("Salı, 2. saat")).toHaveAttribute("data-durum", "gelemez"));
    await kullanici.keyboard(" ");
    await waitFor(() => expect(hucre("Salı, 2. saat")).toHaveAttribute("data-durum", "tercih_etmez"));
    expect(istekler).toEqual([[{ gun: 1, saat: 1, durum: "gelemez" }], [{ gun: 1, saat: 1, durum: "tercih_etmez" }]]);
  });

  it("gün başlığı bütün günü tek istekte değiştirir", async () => {
    const { istekler } = apiKur();
    const { kullanici } = await ac();
    await kullanici.click(screen.getByRole("button", { name: "Cuma: bütün günü birlikte değiştir" }));
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]).toEqual(Array.from({ length: 8 }, (_, saat) => ({ gun: 4, saat, durum: "gelemez" })));
    expect(hucre("Cuma, 8. saat")).toHaveAttribute("data-durum", "gelemez");
  });

  it("saat başlığı o saati bütün günlerde değiştirir", async () => {
    const { istekler } = apiKur();
    const { kullanici } = await ac();
    await kullanici.click(screen.getByRole("button", { name: "8. saat: bütün günlerde birlikte değiştir" }));
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]).toEqual(Array.from({ length: 5 }, (_, gun) => ({ gun, saat: 7, durum: "gelemez" })));
  });

  it("sürükleyerek geçilen hücreler tek istekte işaretlenir", async () => {
    const { istekler } = apiKur();
    await ac();
    fireEvent.pointerDown(hucre("Pazartesi, 3. saat"), { pointerId: 1 });
    fireEvent.pointerEnter(hucre("Pazartesi, 4. saat"));
    fireEvent.pointerEnter(hucre("Salı, 4. saat"));
    // Sürüklerken geçilen hücre hemen yeni durumunu gösterir.
    expect(hucre("Salı, 4. saat")).toHaveAttribute("data-durum", "gelemez");
    fireEvent.pointerUp(window);
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]).toEqual([
      { gun: 0, saat: 2, durum: "gelemez" }, { gun: 0, saat: 3, durum: "gelemez" }, { gun: 1, saat: 3, durum: "gelemez" }]);
  });

  it("müsait saat ders yükünün altına düşünce sunucunun mesajıyla anında uyarı", async () => {
    const mesaj = "Ayşe Yılmaz'ın 18 saat dersi var, müsait olduğu 16 saat var.";
    apiKur({
      yanit: (d, c) => HttpResponse.json({
        ...c, hucreler: uygula(c.hucreler, d), yuk: { ...YUK, musait_saat: 16, kullanilabilir_saat: 16, asim: true, mesaj },
      }),
    });
    const { kullanici } = await ac();
    expect(screen.getByText(/Müsait/, { selector: "p" })).toHaveTextContent("Müsait 40 saat; ders yükü 18 saat.");
    expect(screen.queryByText(/Program bu haliyle üretilemez/)).toBeNull();
    await kullanici.click(screen.getByRole("button", { name: "Pazartesi: bütün günü birlikte değiştir" }));
    const uyari = await screen.findByText(/Program bu haliyle üretilemez/);
    expect(uyari).toHaveAttribute("role", "alert");
    expect(uyari).toHaveTextContent(`${mesaj} Program bu haliyle üretilemez.`);
  });
});

/** Cuma 5 saat, öğle arası 4. dersten sonra, zil saatleri 08:30'da (K3). */
function kisaCumaliOkul() {
  sunucu.use(http.get("/api/ben", () => HttpResponse.json({
    ...BEN_ORNEK,
    okul: { ...BEN_ORNEK.okul, gun_saatleri: [8, 8, 8, 8, 5], ogle_arasi_sonra: 4, ilk_ders_baslangic: "08:30:00" },
  })));
}

describe("müsaitlik çizelgesi: kısa gün, öğle arası, zil saatleri (K3)", () => {
  it("cumanın 6.-8. saati hücre değil; gün başlığı yalnızca var olan saatleri değiştirir", async () => {
    kisaCumaliOkul();
    const { istekler } = apiKur();
    const { kullanici } = await ac();
    expect(hucre("Cuma, 5. saat")).toBeEnabled();
    expect(screen.queryByRole("button", { name: /^Cuma, 6\. saat:/ })).not.toBeInTheDocument();
    expect(screen.getByText("Cuma, 6. saat: bu saatte ders yok")).toBeInTheDocument();
    await kullanici.click(screen.getByRole("button", { name: "Cuma: bütün günü birlikte değiştir" }));
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]).toEqual(Array.from({ length: 5 }, (_, saat) => ({ gun: 4, saat, durum: "gelemez" })));
  });

  it("saat başlığında zil saati; 4. dersten sonra öğle arası ayracı", async () => {
    kisaCumaliOkul();
    apiKur();
    await ac();
    const tablo = screen.getByRole("table", { name: /müsaitlik çizelgesi/ });
    expect(within(tablo).getByRole("button", { name: "1. saat: bütün günlerde birlikte değiştir" })).toHaveTextContent("1. saat08:30–09:10");
    expect(within(tablo).getByRole("rowheader", { name: "Öğle arası · 11:40–12:20" })).toBeInTheDocument();
    // Öğle arasından sonraki ders öğle arası süresi kadar sonra başlar.
    expect(within(tablo).getByRole("button", { name: "5. saat: bütün günlerde birlikte değiştir" })).toHaveTextContent("12:20–13:00");
  });
});
