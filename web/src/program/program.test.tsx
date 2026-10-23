/** Program sayfası: oluşturma, engeller, bekleme, sorgulama, sonuç ve başarısızlık. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "../api/sema";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type Program = components["schemas"]["ProgramYanit"];

function program(degisiklik: Partial<Program> = {}): Program {
  return {
    id: "p1", ad: "Program 1", durum: "bekliyor", hata_mesaji: null, temel_program_id: null, sure_siniri_sn: 120,
    olusturma: "2026-10-24T09:00:00Z", baslama: null, bitis: null, cozum_durumu: null, toplam_ceza: null,
    olcumler: null, celiskiler: null, sure_sn: null, ...degisiklik,
  };
}

const HAZIR = program({
  durum: "hazir", baslama: "2026-10-24T09:00:01Z", bitis: "2026-10-24T09:02:01Z", cozum_durumu: "uygun", sure_sn: 120.4,
  olcumler: { sinif_boslugu: 0, ogretmen_penceresi: 3, eksik_bos_gun: 1, tercih_etmez: 0, bolunmus_ders: 0, degisen_yerlesim: 0 },
});

/** Sahte program API'si: `yanitlar` sırayla döner (sonuncusu tekrarlanır); POST gövdeleri kaydedilir. */
function programApisi(yanitlar: Program[][], postYaniti = program()) {
  const govdeler: unknown[] = [];
  let sira = 0;
  sunucu.use(
    http.get("/api/ders-programi/programlar", () => HttpResponse.json(yanitlar[Math.min(sira++, yanitlar.length - 1)])),
    http.post("/api/ders-programi/programlar", async ({ request }) => {
      govdeler.push(await request.json());
      return HttpResponse.json(postYaniti, { status: 202 });
    }),
  );
  return govdeler;
}

/** Engel yok: bütün derslerin öğretmeni seçili, aşım yok. */
function hazirVeri() {
  const api = dagilimApisiKur();
  api.ozet.ogretmensiz_atama = 0;
  return api;
}

describe("program oluşturma", () => {
  it("öğretmensiz ders varsa düğme pasif ve neden söylenir", async () => {
    dagilimApisiKur(); // 2 öğretmensiz ders
    programApisi([[]]);
    uygulamayiCiz("/program");
    const not = await screen.findByRole("note");
    expect(not).toHaveTextContent("Bu sorunlar düzeltilmeden program oluşturulamaz:");
    expect(not).toHaveTextContent("2 dersin öğretmeni seçilmedi.");
    expect(within(not).getByRole("link", { name: "Öğretmenleri seç" })).toHaveAttribute("href", "/ders-dagilimi");
    expect(screen.getByRole("button", { name: "Programı oluştur" })).toBeDisabled();
  });

  it("engel yoksa oluşturulur; seçilen süre ve ad gönderilir; bekleme ekranı açılır", async () => {
    hazirVeri();
    const govdeler = programApisi([[], [program()]]);
    const { kullanici } = uygulamayiCiz("/program");
    expect(await screen.findByText(/Ders dağılımı tamam/)).toBeInTheDocument();
    await kullanici.click(screen.getByRole("radio", { name: /Hızlı/ }));
    await kullanici.click(screen.getByRole("button", { name: "Programı oluştur" }));

    await waitFor(() => expect(govdeler).toEqual([{ ad: "Program 1", sure_siniri_sn: 30 }]));
    expect(await screen.findByRole("heading", { name: "Program hazırlanıyor" })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { current: "step" })).toHaveTextContent("Sırada");
  });

  it("üretim sürerken aşama ve ilerleme gösterilir", async () => {
    hazirVeri();
    const baslama = new Date(Date.now() - 30_000).toISOString(); // 30 sn önce başladı
    programApisi([[program({ durum: "uretiliyor", baslama })]]);
    uygulamayiCiz("/program");
    expect(await screen.findByRole("heading", { name: "Program hazırlanıyor" })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { current: "step" })).toHaveTextContent("Program iyileştiriliyor");
    const cubuk = screen.getByRole("progressbar", { name: "Ayrılan sürenin kullanılan kısmı" });
    expect(Number(cubuk.getAttribute("aria-valuenow"))).toBeGreaterThanOrEqual(24);
    expect(screen.getByText(/en fazla \d+ saniye kaldı/)).toBeInTheDocument();
  });

  it("sorgulama sürer, program hazır olunca sonuç ve kalite özeti gelir", async () => {
    hazirVeri();
    programApisi([[program({ durum: "uretiliyor", baslama: new Date().toISOString() })], [HAZIR]]);
    uygulamayiCiz("/program");
    expect(await screen.findByRole("heading", { name: "Program hazırlanıyor" })).toBeInTheDocument();

    const baslik = await screen.findByRole("heading", { name: "“Program 1” hazır" }, { timeout: 5000 });
    expect(baslik).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Haftalık çizelgeyi aç" })).toHaveAttribute("href", "/program/p1");
    expect(screen.getByText("Şubelerde gün ortasında boş saat yok.")).toBeInTheDocument();
    expect(screen.getByText("Öğretmenlerin toplam 3 pencere saati var (iki dersi arasında boş bekledikleri saat).")).toBeInTheDocument();
    expect(screen.getByText(/Süre sınırı dolduğunda bulunan en iyi program/)).toHaveTextContent("Üretim 2 dakika sürdü.");
    // Yeniden oluşturmak mümkün; liste programı gösterir.
    expect(screen.getByRole("heading", { name: "Yeni program oluştur" })).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Programlar" })).getByText("Hazır")).toBeInTheDocument();
  });

  it("başarısızlıkta çelişkiler türüne göre gruplanır, ilgili şubeye bağlantı verilir", async () => {
    hazirVeri();
    programApisi([[program({
      durum: "basarisiz", cozum_durumu: "on_kontrol_hatasi",
      hata_mesaji: "9-A sınıfının haftada 42 saat dersi var...",
      celiskiler: [
        { tur: "sinif_kapasitesi", mesaj: "9-A sınıfının haftada 42 saat dersi var, haftalık kapasite 40 saat.", ilgili: ["s-9a", "a-9a-mat"] },
        { tur: "ogretmen_kapasitesi", mesaj: "Şule Kaya'nın 12 saat dersi var, müsait olduğu 10 saat var.", ilgili: ["o-sule"] },
      ],
    })]]);
    uygulamayiCiz("/program");
    const panel = await screen.findByRole("region", { name: "“Program 1” oluşturulamadı" });
    expect(within(panel).getByRole("heading", { name: "Haftalık kapasiteyi aşan şubeler" })).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { name: "Müsait saatinden fazla dersi olan öğretmenler" })).toBeInTheDocument();
    expect(await within(panel).findByRole("link", { name: "9-A" })).toHaveAttribute("href", "/ders-dagilimi?gorunum=sube&sinif=s-9a");
    expect(within(panel).getByRole("link", { name: "Şule Kaya" })).toHaveAttribute("href", "/ders-dagilimi?gorunum=ogretmen");
  });

  it("çelişki listesi yoksa sunucunun mesajı satır satır gösterilir", async () => {
    hazirVeri();
    programApisi([[program({ durum: "basarisiz", hata_mesaji: "Süre yetmedi.\nDaha uzun süre deneyin." })]]);
    uygulamayiCiz("/program");
    const panel = await screen.findByRole("region", { name: "“Program 1” oluşturulamadı" });
    expect(within(panel).getAllByRole("listitem").map((l) => l.textContent)).toEqual(["Süre yetmedi.", "Daha uzun süre deneyin."]);
  });
});
