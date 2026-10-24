/** Programların yönetimi (6.3): liste, adlandırma, silme, temel alarak üretme, fark, eski veri. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "../api/sema";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type Program = components["schemas"]["ProgramYanit"];

const OLCUM = { sinif_boslugu: 0, ogretmen_penceresi: 3, eksik_bos_gun: 1, tercih_etmez: 0, bolunmus_ders: 0, degisen_yerlesim: 0 };
function program(d: Partial<Program>): Program {
  return {
    id: "p1", ad: "Eylül", durum: "hazir", hata_mesaji: null, temel_program_id: null, sure_siniri_sn: 120,
    olusturma: "2026-10-24T09:00:00Z", baslama: "2026-10-24T09:00:01Z", bitis: "2026-10-24T09:02:01Z",
    cozum_durumu: "uygun", toplam_ceza: 10, olcumler: OLCUM, celiskiler: [], sure_sn: 12, eski_veri: false, ...d,
  };
}
const EYLUL = program({});
const EKIM = program({ id: "p2", ad: "Ekim", temel_program_id: "p1", olusturma: "2026-10-24T10:00:00Z", olcumler: { ...OLCUM, degisen_yerlesim: 3 } });
const FARK = {
  ile_id: "p1", ile_ad: "Eylül", degisen: 3,
  subeler: [{ sinif_id: "s-9a", ad: "9-A", sayi: 2 }, { sinif_id: "s-9b", ad: "9-B", sayi: 1 }],
  hucreler: [{ ders_atama_id: "a-9a-mat", gun: 0, saat: 0 }, { ders_atama_id: "a-9a-fiz", gun: 1, saat: 2 }, { ders_atama_id: "a-9b-mat", gun: 2, saat: 0 }],
};

function api(programlar: Program[]) {
  const istekler: { yontem: string; yol: string; govde?: unknown }[] = [];
  const veri = dagilimApisiKur();
  veri.ozet.ogretmensiz_atama = 0;
  sunucu.use(
    http.get("/api/ders-programi/programlar", () => HttpResponse.json(programlar)),
    http.get("/api/ders-programi/programlar/:id", ({ params }) => HttpResponse.json(programlar.find((p) => p.id === params.id))),
    http.get("/api/ders-programi/programlar/:id/fark", () => HttpResponse.json(FARK)),
    http.patch("/api/ders-programi/programlar/:id", async ({ request, params }) => {
      const govde = (await request.json()) as { ad: string };
      istekler.push({ yontem: "PATCH", yol: String(params.id), govde });
      programlar = programlar.map((p) => (p.id === params.id ? { ...p, ad: govde.ad } : p));
      return HttpResponse.json(programlar.find((p) => p.id === params.id));
    }),
    http.delete("/api/ders-programi/programlar/:id", ({ params }) => {
      istekler.push({ yontem: "DELETE", yol: String(params.id) });
      programlar = programlar.filter((p) => p.id !== params.id).map((p) => (p.temel_program_id === params.id ? { ...p, temel_program_id: null } : p));
      return new HttpResponse(null, { status: 204 });
    }),
    http.post("/api/ders-programi/programlar", async ({ request }) => {
      const govde = await request.json();
      istekler.push({ yontem: "POST", yol: "programlar", govde });
      return HttpResponse.json(program({ id: "p3", durum: "bekliyor", ...(govde as object) }), { status: 202 });
    }),
  );
  return istekler;
}

describe("programlar listesi", () => {
  it("durum, kısa kalite, temel ve eski veri; ad değiştirilir; onayla silinir", async () => {
    const istekler = api([EYLUL, { ...EKIM, eski_veri: true }]);
    const { kullanici } = uygulamayiCiz("/program");
    const tablo = await screen.findByRole("table", { name: "Programlar" });
    const ekim = within(tablo).getByRole("row", { name: /^Ekim/ });
    expect(ekim).toHaveTextContent("Temel: Eylül");
    expect(ekim).toHaveTextContent("3 konu iyileştirilebilir");
    expect(ekim).toHaveTextContent("Eski verilerle");
    expect(within(tablo).getByRole("row", { name: /^Eylül/ })).not.toHaveTextContent("Eski verilerle");

    await kullanici.click(within(tablo).getByRole("button", { name: "Eylül: adını değiştir" }));
    const kutu = within(tablo).getByRole("textbox", { name: "Programın adı (düzenleme)" });
    await kullanici.clear(kutu);
    await kullanici.type(kutu, "Güz dönemi{Enter}");
    expect(await screen.findByText("Programın yeni adı: Güz dönemi.")).toBeInTheDocument();

    await kullanici.click(within(tablo).getByRole("button", { name: "Güz dönemi: sil" }));
    const pencere = screen.getByRole("dialog", { name: "“Güz dönemi” silinsin mi?" });
    expect(pencere).toHaveTextContent("temel alan programlar silinmez");
    await kullanici.click(within(pencere).getByRole("button", { name: "Programı sil" }));
    expect(await screen.findByText("“Güz dönemi” silindi.")).toBeInTheDocument();
    expect(istekler).toEqual([
      { yontem: "PATCH", yol: "p1", govde: { ad: "Güz dönemi" } },
      { yontem: "DELETE", yol: "p1" },
    ]);
  });

  it("temel alarak yeniden üretme: oluşturma kartında temel, istekte temel_program_id", async () => {
    const istekler = api([EYLUL]);
    const { kullanici } = uygulamayiCiz("/program");
    await kullanici.click(await screen.findByRole("button", { name: "Bu programı temel alarak yeniden üret" }));
    const kart = screen.getByRole("region", { name: "Yeni program oluştur" });
    expect(within(kart).getByRole("status")).toHaveTextContent("“Eylül” temel alınıyor.");
    expect(within(kart).getByRole("textbox", { name: "Programın adı" })).toHaveValue("Eylül (güncel)");
    await waitFor(() => expect(within(kart).getByRole("button", { name: "Programı oluştur" })).toBeEnabled());
    await kullanici.click(within(kart).getByRole("button", { name: "Programı oluştur" }));
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]).toEqual({ yontem: "POST", yol: "programlar",
      govde: { ad: "Eylül (güncel)", sure_siniri_sn: 120, temel_program_id: "p1" } });
  });

  it("temel almaktan vazgeçilebilir", async () => {
    api([EYLUL]);
    const { kullanici } = uygulamayiCiz("/program");
    await kullanici.click(await screen.findByRole("button", { name: "Eylül: temel alarak yeniden üret" }));
    await kullanici.click(screen.getByRole("button", { name: "Temel almadan üret" }));
    expect(screen.queryByText(/temel alınıyor/)).toBeNull();
    expect(screen.getByRole("textbox", { name: "Programın adı" })).toHaveValue("Program 2");
  });
});

describe("hazır program: fark ve eski veri", () => {
  it("temel programa göre kaç ders saatinin hangi şubelerde değiştiğini söyler", async () => {
    api([EYLUL, EKIM]);
    uygulamayiCiz("/program");
    const fark = await screen.findByRole("status", { name: "Temel programa göre değişiklik" });
    expect(fark).toHaveTextContent("“Eylül” programına göre 3 ders saati yer değiştirdi: 9-A (2), 9-B (1).");
    expect(within(fark).getByRole("link", { name: "Değişenleri çizelgede göster" })).toHaveAttribute("href", "/program/p2?fark=1");
  });

  it("veri değiştiyse eski veri uyarısı ve tek tıkla temel alarak yeniden üretme", async () => {
    api([{ ...EYLUL, eski_veri: true }]);
    const { kullanici } = uygulamayiCiz("/program");
    const not = await screen.findByText("Bu program eski verilerle üretildi.");
    await kullanici.click(within(not.closest("[role=note]") as HTMLElement).getByRole("button", { name: "Temel alarak yeniden üret" }));
    expect(screen.getByText(/“Eylül” temel alınıyor/)).toBeInTheDocument();
  });

  it("çizelgede ?fark=1 ile değişen hücreler vurgulanır, ekran okuyucuya söylenir", async () => {
    api([EYLUL, EKIM]);
    sunucu.use(http.get("/api/ders-programi/programlar/p2/yerlesimler", () => HttpResponse.json([
      { id: "y1", ders_atama_id: "a-9a-mat", gun: 0, saat: 0, kilitli: false },
      { id: "y2", ders_atama_id: "a-9a-fiz", gun: 1, saat: 2, kilitli: false },
      { id: "y3", ders_atama_id: "a-9a-mat", gun: 3, saat: 0, kilitli: false },
    ])));
    const { kullanici } = uygulamayiCiz("/program/p2?gorunum=sube&sinif=s-9a&fark=1");
    const tablo = await screen.findByRole("table", { name: "9-A haftalık programı" });
    await waitFor(() => expect(tablo.querySelectorAll("[data-degisti]")).toHaveLength(2));
    expect(screen.getAllByText("Temel programa göre değişti:")).toHaveLength(2);
    const secim = screen.getByRole("checkbox", { name: "Temel programdan değişen dersleri vurgula" });
    expect(secim).toBeChecked();
    await kullanici.click(secim);
    expect(tablo.querySelectorAll("[data-degisti]")).toHaveLength(0);
  });
});
