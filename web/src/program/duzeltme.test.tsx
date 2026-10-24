/** Elle düzeltme (7.1): seçme, taşıma haritası, engel / uyarı / onay, kilit, geri alma, sürükle bırak, telefon. */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

const PROGRAM = {
  id: "p1", ad: "Güz programı", durum: "hazir", hata_mesaji: null, temel_program_id: null, sure_siniri_sn: 120,
  olusturma: "2026-10-24T09:00:00Z", baslama: "2026-10-24T09:00:01Z", bitis: "2026-10-24T09:02:00Z",
  cozum_durumu: "optimal", toplam_ceza: 0, sure_sn: 4.2, celiskiler: [], eski_veri: false, elle_duzeltme: 0,
  olcumler: { sinif_boslugu: 0, ogretmen_penceresi: 0, eksik_bos_gun: 0, tercih_etmez: 0, bolunmus_ders: 0, degisen_yerlesim: 0 },
};
// 9-A: Matematik pazartesi 1. saat, Fizik salı 3. saat (Fizik kilitli olabilir).
const YERLESIMLER = [
  { id: "y1", ders_atama_id: "a-9a-mat", gun: 0, saat: 0, kilitli: false },
  { id: "y2", ders_atama_id: "a-9a-fiz", gun: 1, saat: 2, kilitli: false },
];
const HARITA = {
  hucreler: [{ gun: 0, saat: 0 }],
  hedefler: [
    { gun: 1, saat: 0, durum: "uygun", nedenler: [], takas: [] },
    { gun: 1, saat: 2, durum: "uygun", nedenler: [], takas: ["9-A Fizik"] },
    { gun: 2, saat: 0, durum: "uyari", nedenler: ["Öğretmenlerin pencere saati 0 → 2"], takas: [] },
    { gun: 3, saat: 0, durum: "engel", nedenler: ["Şule Kaya Perşembe 1. saat gelemez"], takas: [] },
  ],
};

function kur(degisiklik: Partial<typeof PROGRAM> = {}, yerlesimler = YERLESIMLER) {
  const api = dagilimApisiKur();
  const istekler: { yontem: string; yol: string; govde?: unknown; sorgu?: string }[] = [];
  let program = { ...PROGRAM, ...degisiklik };
  sunucu.use(
    http.get("/api/ders-programi/programlar/p1", () => HttpResponse.json(program)),
    http.get("/api/ders-programi/programlar/p1/yerlesimler", () => HttpResponse.json(yerlesimler)),
    http.get("/api/ders-programi/programlar/p1/tasima", ({ request }) => {
      istekler.push({ yontem: "GET", yol: "tasima", sorgu: new URL(request.url).searchParams.toString() });
      return HttpResponse.json(HARITA);
    }),
    http.post("/api/ders-programi/programlar/p1/tasi", async ({ request }) => {
      istekler.push({ yontem: "POST", yol: "tasi", govde: await request.json() });
      program = { ...program, elle_duzeltme: program.elle_duzeltme + 1 };
      return HttpResponse.json(program);
    }),
    http.put("/api/ders-programi/programlar/p1/kilit", async ({ request }) => {
      istekler.push({ yontem: "PUT", yol: "kilit", govde: await request.json() });
      return HttpResponse.json(program);
    }),
    http.post("/api/ders-programi/programlar/p1/geri-al", () => {
      istekler.push({ yontem: "POST", yol: "geri-al" });
      return HttpResponse.json({ ...program, elle_duzeltme: 0 });
    }),
  );
  return { api, istekler };
}

/** Tablodaki hücre: gün sütunu ve saat satırı başlıklarından. */
function hucre(tablo: HTMLElement, gun: string, saat: string) {
  const satirlar = within(tablo).getAllByRole("row");
  const basliklar = within(satirlar[0]!).getAllByRole("columnheader").map((h) => h.textContent);
  const satir = satirlar.find((r) => within(r).queryByRole("rowheader")?.textContent === saat)!;
  return within(satir).getAllByRole("cell")[basliklar.indexOf(gun) - 1]!;
}

async function ac() {
  const ciz = uygulamayiCiz("/program/p1?gorunum=sube&sinif=s-9a");
  const tablo = await screen.findByRole("table", { name: "9-A haftalık programı" });
  return { ...ciz, tablo };
}

async function tasimayaBasla(kullanici: ReturnType<typeof uygulamayiCiz>["kullanici"], tablo: HTMLElement) {
  await kullanici.click(within(hucre(tablo, "Pazartesi", "1. saat")).getByRole("button"));
  const cubuk = screen.getByRole("region", { name: "Elle düzeltme" });
  expect(cubuk).toHaveTextContent("Seçili: 9-A Matematik");
  await kullanici.click(within(cubuk).getByRole("button", { name: "Taşı" }));
  await waitFor(() => expect(hucre(tablo, "Salı", "1. saat")).toHaveAttribute("data-hedef", "uygun"));
  return cubuk;
}

describe("elle düzeltme", () => {
  it("dersi seçip Taşı: harita istenir, hedefler boyanır, uygun hedefe taşınır", async () => {
    const { istekler } = kur();
    const { kullanici, tablo } = await ac();
    const cubuk = await tasimayaBasla(kullanici, tablo);
    expect(istekler[0]).toEqual({ yontem: "GET", yol: "tasima", sorgu: "ders_atama_id=a-9a-mat&gun=0&saat=0" });
    expect(cubuk).toHaveTextContent("9-A Matematik taşınıyor: hedef saati seçin.");
    expect(hucre(tablo, "Çarşamba", "1. saat")).toHaveAttribute("data-hedef", "uyari");
    expect(hucre(tablo, "Perşembe", "1. saat")).toHaveAttribute("data-hedef", "engel");
    expect(hucre(tablo, "Perşembe", "1. saat")).toHaveTextContent("Hedef: Buraya taşınamaz: Şule Kaya Perşembe 1. saat gelemez");

    await kullanici.click(within(hucre(tablo, "Salı", "1. saat")).getByRole("button"));
    expect(await screen.findByText("9-A Matematik Salı 1. saate taşındı.")).toBeInTheDocument();
    expect(istekler.at(-1)).toEqual({ yontem: "POST", yol: "tasi", govde: {
      ders_atama_id: "a-9a-mat", gun: 0, saat: 0, hedef_gun: 1, hedef_saat: 0, uyarilari_kabul: false } });
    // Kalite özetinin üstünde not ve geri alma düğmesi.
    expect(await within(cubuk).findByRole("button", { name: "Geri al (1)" })).toBeInTheDocument();
    // Çözücünün "en iyi program" sözü elle düzeltilmiş programda söylenmez.
    expect(await screen.findByText("Program elle düzeltildi (1 değişiklik); ölçüler düzeltilmiş hâline göredir.")).toBeInTheDocument();
    expect(screen.queryByText(/kanıtlandı/)).toBeNull();
  });

  it("dolu hücre takas hedefidir: üzerine gelince kimle yer değiştireceği söylenir", async () => {
    kur();
    const { kullanici, tablo } = await ac();
    await tasimayaBasla(kullanici, tablo);
    const fizik = hucre(tablo, "Salı", "3. saat");
    expect(fizik).toHaveAttribute("data-hedef", "uygun");
    await kullanici.hover(within(fizik).getByRole("button"));
    expect(screen.getByText("Buraya taşınabilir; 9-A Fizik ile yer değiştirir.")).toBeInTheDocument();
  });

  it("engelli hedefe taşınmaz, nedeni söylenir", async () => {
    const { istekler } = kur();
    const { kullanici, tablo } = await ac();
    await tasimayaBasla(kullanici, tablo);
    await kullanici.click(within(hucre(tablo, "Perşembe", "1. saat")).getByRole("button"));
    const hata = await screen.findByRole("alert");
    await waitFor(() => expect(hata).toHaveTextContent("Buraya taşınamaz: Şule Kaya Perşembe 1. saat gelemez"));
    expect(istekler.filter((i) => i.yontem === "POST")).toEqual([]);
  });

  it("yalnızca esnek kuralı kötüleştiren taşıma onayla yapılır", async () => {
    const { istekler } = kur();
    const { kullanici, tablo } = await ac();
    await tasimayaBasla(kullanici, tablo);
    await kullanici.click(within(hucre(tablo, "Çarşamba", "1. saat")).getByRole("button"));
    const pencere = screen.getByRole("dialog", { name: "9-A Matematik yine de taşınsın mı?" });
    expect(pencere).toHaveTextContent("Öğretmenlerin pencere saati 0 → 2");
    expect(istekler.filter((i) => i.yontem === "POST")).toEqual([]);
    await kullanici.click(within(pencere).getByRole("button", { name: "Yine de taşı" }));
    await waitFor(() => expect(istekler.at(-1)).toMatchObject({ yol: "tasi", govde: { hedef_gun: 2, hedef_saat: 0, uyarilari_kabul: true } }));
  });

  it("sürükleyip bırakmak taşır; bırakmadan biterse iptal", async () => {
    const { istekler } = kur();
    const { tablo } = await ac();
    const dataTransfer = { setData: vi.fn(), effectAllowed: "" };
    const kaynak = within(hucre(tablo, "Pazartesi", "1. saat")).getByRole("button");
    expect(kaynak).toHaveAttribute("draggable", "true");
    fireEvent.dragStart(kaynak, { dataTransfer });
    await waitFor(() => expect(hucre(tablo, "Salı", "1. saat")).toHaveAttribute("data-hedef", "uygun"));
    fireEvent.dragEnd(kaynak);
    await waitFor(() => expect(hucre(tablo, "Salı", "1. saat")).not.toHaveAttribute("data-hedef"));

    fireEvent.dragStart(kaynak, { dataTransfer });
    await waitFor(() => expect(hucre(tablo, "Salı", "1. saat")).toHaveAttribute("data-hedef", "uygun"));
    fireEvent.dragOver(hucre(tablo, "Salı", "1. saat"), { dataTransfer });
    fireEvent.drop(hucre(tablo, "Salı", "1. saat"), { dataTransfer });
    fireEvent.dragEnd(kaynak);
    await waitFor(() => expect(istekler.at(-1)).toMatchObject({ yol: "tasi", govde: { hedef_gun: 1, hedef_saat: 0 } }));
  });

  it("kilitle: kilitli ders belirgin, taşınamaz; kilit açılır; geri alınır", async () => {
    const { istekler } = kur({ elle_duzeltme: 2 }, [YERLESIMLER[0]!, { ...YERLESIMLER[1]!, kilitli: true }]);
    const { kullanici, tablo } = await ac();
    const fizik = hucre(tablo, "Salı", "3. saat");
    expect(fizik).toHaveAttribute("data-kilitli", "true");
    expect(fizik).toHaveTextContent("Kilitli:");
    expect(within(fizik).getByRole("button")).toHaveAttribute("draggable", "false");
    await kullanici.click(within(fizik).getByRole("button"));
    const cubuk = screen.getByRole("region", { name: "Elle düzeltme" });
    expect(cubuk).toHaveTextContent("Seçili: 9-A Fizik (kilitli)");
    expect(within(cubuk).getByRole("button", { name: "Taşı" })).toBeDisabled();
    await kullanici.click(within(cubuk).getByRole("button", { name: "Kilidi aç" }));
    expect(await screen.findByText("9-A Fizik kilidi açıldı.")).toBeInTheDocument();
    expect(istekler.at(-1)).toEqual({ yontem: "PUT", yol: "kilit", govde: { ders_atama_id: "a-9a-fiz", gun: 1, saat: 2, kilitli: false } });

    await kullanici.click(within(cubuk).getByRole("button", { name: "Geri al (2)" }));
    expect(await screen.findByText("Son değişiklik geri alındı.")).toBeInTheDocument();
    expect(istekler.at(-1)).toEqual({ yontem: "POST", yol: "geri-al" });
  });

  it("kilitlenmemiş dersi kilitler", async () => {
    const { istekler } = kur();
    const { kullanici, tablo } = await ac();
    await kullanici.click(within(hucre(tablo, "Pazartesi", "1. saat")).getByRole("button"));
    await kullanici.click(screen.getByRole("button", { name: "Kilitle" }));
    expect(await screen.findByText("9-A Matematik kilitlendi; yeniden üretimde yerinde kalır.")).toBeInTheDocument();
    expect(istekler.at(-1)).toMatchObject({ yol: "kilit", govde: { kilitli: true } });
  });
});

describe("telefonda elle düzeltme", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("derse dokunup Taşı, başka güne geçip hedefe dokunarak taşınır", async () => {
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("max-width"), addEventListener: () => {}, removeEventListener: () => {} }));
    const { istekler } = kur();
    const { kullanici } = uygulamayiCiz("/program/p1?gorunum=sube&sinif=s-9a");
    const gunler = await screen.findByRole("group", { name: "Gün" });
    await kullanici.click(within(gunler).getByRole("button", { name: "Pazartesi" }));
    const liste = screen.getByRole("list", { name: "9-A haftalık programı, Pazartesi" });
    await kullanici.click(within(within(liste).getAllByRole("listitem")[0]!).getByRole("button"));
    await kullanici.click(screen.getByRole("button", { name: "Taşı" }));
    await kullanici.click(within(gunler).getByRole("button", { name: "Salı" }));
    const sali = screen.getByRole("list", { name: "9-A haftalık programı, Salı" });
    const ilk = within(sali).getAllByRole("listitem")[0]!;
    await waitFor(() => expect(ilk).toHaveAttribute("data-hedef", "uygun"));
    await kullanici.click(within(ilk).getByRole("button"));
    await waitFor(() => expect(istekler.at(-1)).toMatchObject({ yol: "tasi", govde: { hedef_gun: 1, hedef_saat: 0 } }));
  });
});
