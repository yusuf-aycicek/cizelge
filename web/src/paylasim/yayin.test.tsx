/** Yayın ve paylaşım sayfası (8b): yayınla, güncel olmama uyarıları, linkler (oluştur, yenile, iptal). */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "../api/sema";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type Program = components["schemas"]["ProgramYanit"];
type Link = components["schemas"]["PaylasimLinkiYanit"];
const DP = "/api/ders-programi";

const program = { id: "p1", ad: "Güz Programı", durum: "hazir" } as Program;
const ayseLinki: Link = { id: "l1", tur: "ogretmen", ogretmen_id: "o1", sinif_id: null, hedef_adi: "Ayşe Yılmaz",
  jeton: "jeton-ayse", olusturma: "2026-10-24T09:00:00Z" };

describe("Yayın ve paylaşım", () => {
  it("yayın yokken programı yayınlar", async () => {
    let yayinlanan: unknown = null;
    sunucu.use(
      http.get(`${DP}/programlar`, () => HttpResponse.json([program])),
      http.get(`${DP}/yayin`, () => HttpResponse.json(null)),
      http.get(`${DP}/paylasim-linkleri`, () => HttpResponse.json([])),
      http.put(`${DP}/yayin`, async ({ request }) => {
        yayinlanan = await request.json();
        return HttpResponse.json({ program_id: "p1", program_adi: "Güz Programı", yayin_zamani: "2026-10-24T10:00:00Z",
          eski_veri: false, program_degisti: false, uyarilar: [] });
      }),
    );
    const { kullanici } = uygulamayiCiz("/yayin");
    expect(await screen.findByText(/Henüz yayınlanmış program yok/)).toBeInTheDocument();
    await kullanici.click(await screen.findByRole("button", { name: "Yayınla" }));
    expect(await screen.findByText(/“Güz Programı” yayınlandı/)).toBeInTheDocument();
    expect(yayinlanan).toEqual({ program_id: "p1" });
    expect(await screen.findByRole("button", { name: "Yeniden yayınla" })).toBeInTheDocument();
  });

  it("güncel olmayan yayının nedenleri; öğretmen linki kopyalanır, yenilenir", async () => {
    let yenilenen = "";
    sunucu.use(
      http.get(`${DP}/programlar`, () => HttpResponse.json([program])),
      http.get(`${DP}/yayin`, () => HttpResponse.json({ program_id: "p1", program_adi: "Güz Programı",
        yayin_zamani: "2026-10-24T10:00:00Z", eski_veri: true, program_degisti: false,
        uyarilar: ["Yayınlanan program eski verilerle üretildi: öğretmen, ders, dağılım ya da kurallar yayından sonra değişti."] })),
      http.get(`${DP}/paylasim-linkleri`, () => HttpResponse.json([ayseLinki])),
      http.post(`${DP}/paylasim-linkleri/:id/yenile`, ({ params }) => {
        yenilenen = String(params.id);
        return HttpResponse.json({ ...ayseLinki, jeton: "yeni" });
      }),
    );
    const { kullanici } = uygulamayiCiz("/yayin");
    const uyarilar = await screen.findByRole("list", { name: "Yayın güncel değil" });
    expect(uyarilar).toHaveTextContent("eski verilerle üretildi");
    // Kartta programın iç adı yok, yalnızca tarih (öğretmen ve veli için anlamlı olan).
    const yayinda = screen.getByText(/tarihinde yayınlandı/);
    expect(yayinda).toHaveTextContent("24.10.2026 tarihinde yayınlandı.");
    expect(yayinda).not.toHaveTextContent("Güz Programı");
    const adres = await screen.findByLabelText("Ayşe Yılmaz linki");
    expect(adres).toHaveValue(`${location.origin}/p/jeton-ayse`);
    await kullanici.click(screen.getByRole("button", { name: "Ayşe Yılmaz linkini kopyala" }));
    expect(await navigator.clipboard.readText()).toBe(`${location.origin}/p/jeton-ayse`);
    await kullanici.click(screen.getByRole("button", { name: "Ayşe Yılmaz linkini yenile" }));
    const pencere = await screen.findByRole("dialog", { name: "Link yenilensin mi?" });
    await kullanici.click(within(pencere).getByRole("button", { name: "Yenile" }));
    await waitFor(() => expect(yenilenen).toBe("l1"));
    expect(await screen.findByText(/eski link artık açılmıyor/)).toBeInTheDocument();
  });
});
