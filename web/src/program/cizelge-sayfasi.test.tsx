/** Haftalık çizelge sayfası: şube ve öğretmen görünümü, hücre içeriği, boş saat, kalite özeti. */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { BEN_ORNEK, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

const PROGRAM = {
  id: "p1", ad: "Güz programı", durum: "hazir", hata_mesaji: null, temel_program_id: null, sure_siniri_sn: 120,
  olusturma: "2026-10-24T09:00:00Z", baslama: "2026-10-24T09:00:01Z", bitis: "2026-10-24T09:02:00Z",
  cozum_durumu: "optimal", toplam_ceza: 0, sure_sn: 4.2, celiskiler: [],
  olcumler: { sinif_boslugu: 0, ogretmen_penceresi: 0, eksik_bos_gun: 0, tercih_etmez: 0, bolunmus_ders: 0, degisen_yerlesim: 0 },
};
// dagilimApisi: a-9a-mat (9-A Matematik, Şule), a-9a-fiz (9-A Fizik, Zeynep), a-9b-mat (9-B Matematik).
const YERLESIMLER = [
  { id: "y1", ders_atama_id: "a-9a-mat", gun: 0, saat: 0, kilitli: false },
  { id: "y2", ders_atama_id: "a-9a-mat", gun: 0, saat: 1, kilitli: false },
  { id: "y3", ders_atama_id: "a-9a-fiz", gun: 1, saat: 2, kilitli: false },
  { id: "y4", ders_atama_id: "a-9b-mat", gun: 2, saat: 0, kilitli: false },
];

function kur(program = PROGRAM) {
  const api = dagilimApisiKur();
  api.atamalar = api.atamalar.map((a) => (a.id === "a-9b-mat" ? { ...a, ogretmen_id: "o-sule" } : a));
  sunucu.use(
    http.get("/api/ders-programi/programlar/p1", () => HttpResponse.json(program)),
    http.get("/api/ders-programi/programlar/p1/yerlesimler", () => HttpResponse.json(YERLESIMLER)),
  );
}

/** Tablodaki hücre: gün sütunu ve saat satırı başlıklarından. */
function hucre(tablo: HTMLElement, gun: string, saat: string) {
  const satirlar = within(tablo).getAllByRole("row");
  const basliklar = within(satirlar[0]!).getAllByRole("columnheader").map((h) => h.textContent);
  const satir = satirlar.find((r) => within(r).queryByRole("rowheader")?.textContent === saat)!;
  return within(satir).getAllByRole("cell")[basliklar.indexOf(gun) - 1]!;
}

describe("haftalık çizelge", () => {
  it("şube görünümü: hücrede ders ve öğretmen, boş saat sade", async () => {
    kur();
    uygulamayiCiz("/program/p1?gorunum=sube&sinif=s-9a");
    const tablo = await screen.findByRole("table", { name: "9-A haftalık programı" });
    expect(hucre(tablo, "Pazartesi", "1. saat")).toHaveTextContent("MatematikŞule Kaya");
    expect(hucre(tablo, "Salı", "3. saat")).toHaveTextContent("FizikZeynep Demir");
    expect(hucre(tablo, "Cuma", "8. saat")).toHaveTextContent("Boş");
    expect(screen.getByText("3 ders saati")).toBeInTheDocument();
    // Okulun 5 günü ve 8 saati: başlık satırı + 8 satır, 1 + 5 sütun.
    expect(within(tablo).getAllByRole("row")).toHaveLength(9);
    expect(within(tablo).getAllByRole("columnheader")).toHaveLength(6);
  });

  it("öğretmen görünümü: hücrede şube adı", async () => {
    kur();
    const { kullanici } = uygulamayiCiz("/program/p1");
    await screen.findByRole("table", { name: /haftalık programı/ });
    await kullanici.click(screen.getByRole("tab", { name: "Öğretmene göre" }));
    await kullanici.selectOptions(screen.getByRole("combobox", { name: "Öğretmen" }), "o-sule");
    const tablo = await screen.findByRole("table", { name: "Şule Kaya haftalık programı" });
    expect(hucre(tablo, "Pazartesi", "1. saat")).toHaveTextContent("Matematik9-A");
    expect(hucre(tablo, "Çarşamba", "1. saat")).toHaveTextContent("Matematik9-B");
    expect(hucre(tablo, "Salı", "3. saat")).toHaveTextContent("Boş");
  });

  it("dolu hücreler sırayla yerleşir (gecikme artar)", async () => {
    kur();
    uygulamayiCiz("/program/p1?sinif=s-9a");
    const tablo = await screen.findByRole("table", { name: "9-A haftalık programı" });
    const ilk = parseInt(hucre(tablo, "Pazartesi", "1. saat").style.animationDelay);
    const sonra = parseInt(hucre(tablo, "Salı", "3. saat").style.animationDelay);
    expect(ilk).toBe(0);
    expect(sonra).toBeGreaterThan(ilk);
  });

  it("kalite özeti çizelgenin altında", async () => {
    kur();
    uygulamayiCiz("/program/p1");
    expect(await screen.findByText("Şubelerde gün ortasında boş saat yok.")).toBeInTheDocument();
    expect(screen.getByText(/Bu kurallarla bulunabilecek en iyi program/)).toBeInTheDocument();
  });

  it("hazır olmayan program için yönlendirme", async () => {
    kur({ ...PROGRAM, durum: "basarisiz" });
    uygulamayiCiz("/program/p1");
    expect(await screen.findByText(/henüz hazır değil ya da oluşturulamadı/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Program sayfasına dönün." })).toHaveAttribute("href", "/program");
  });
});

/** Cuma 5 saat, öğle arası 4. dersten sonra, zil saatleri 08:30'da (K3). */
function kisaCumaliOkul() {
  sunucu.use(http.get("/api/ben", () => HttpResponse.json({
    ...BEN_ORNEK,
    okul: { ...BEN_ORNEK.okul, gun_saatleri: [8, 8, 8, 8, 5], ogle_arasi_sonra: 4, ilk_ders_baslangic: "08:30:00" },
  })));
}

describe("haftalık çizelge: kısa gün, öğle arası, zil saatleri (K3)", () => {
  it("öğle arası iki ders arasında ince ayraç; satır başlığında saat aralığı; cumanın 6. saati yok", async () => {
    kisaCumaliOkul();
    kur();
    uygulamayiCiz("/program/p1?gorunum=sube&sinif=s-9a");
    const tablo = await screen.findByRole("table", { name: "9-A haftalık programı" });
    const basliklar = within(tablo).getAllByRole("rowheader").map((h) => h.textContent);
    expect(basliklar.slice(0, 6)).toEqual([
      "1. saat08:30–09:10", "2. saat09:20–10:00", "3. saat10:10–10:50", "4. saat11:00–11:40",
      "Öğle arası · 11:40–12:20", "5. saat12:20–13:00",
    ]);
    // Ayraç satırının hücresi yok: ekran okuyucu onu ders saati sanmaz.
    const ayrac = within(tablo).getByRole("rowheader", { name: /Öğle arası/ }).closest("tr")!;
    expect(within(ayrac).queryAllByRole("cell")).toHaveLength(0);
    const satir = (basliga: string) => within(tablo).getAllByRole("row").find((r) => within(r).queryByRole("rowheader")?.textContent?.startsWith(basliga))!;
    expect(within(satir("6. saat")).getAllByRole("cell")[4]).toHaveTextContent("Bu saatte ders yok");
    expect(within(satir("5. saat")).getAllByRole("cell")[4]).toHaveTextContent("Boş");
  });

  it("zil saati ve öğle arası yoksa eskisi gibi: yalnızca '1. saat'", async () => {
    kur();
    uygulamayiCiz("/program/p1?gorunum=sube&sinif=s-9a");
    const tablo = await screen.findByRole("table", { name: "9-A haftalık programı" });
    expect(within(tablo).getAllByRole("rowheader").map((h) => h.textContent)).toEqual(
      Array.from({ length: 8 }, (_, s) => `${s + 1}. saat`));
  });
});
