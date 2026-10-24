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
    olcumler: null, celiskiler: null, sure_sn: null, elle_duzeltme: 0, ...degisiklik,
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
  it("ön kontrol sorun bulursa düğme pasif, sorunlar baştan gruplu gösterilir", async () => {
    dagilimApisiKur();
    programApisi([[]]);
    sunucu.use(http.get("/api/ders-programi/on-kontrol", () => HttpResponse.json({ celiskiler: [
      { tur: "ogretmen_secilmemis", mesaj: "9-A Fizik dersine öğretmen seçilmemiş.", ilgili: [] },
    ] })));
    uygulamayiCiz("/program");
    const not = await screen.findByRole("note");
    expect(not).toHaveTextContent("Bu sorunlar düzeltilmeden program oluşturulamaz:");
    expect(within(not).getByRole("heading", { name: "Öğretmeni seçilmemiş dersler" })).toBeInTheDocument();
    expect(not).toHaveTextContent("9-A Fizik dersine öğretmen seçilmemiş.");
    expect(screen.getByRole("button", { name: "Programı oluştur" })).toBeDisabled();
  });

  it("dağılım özeti temiz olsa da özel ayar yüzünden ön kontrol hata veriyorsa düğme pasif", async () => {
    // Kullanıcının gördüğü tutarsızlık: özet "aşım yok" diyordu, üretim ön kontrolde takıldı.
    // Artık engeller doğrudan üretimdeki ön kontrolden gelir.
    hazirVeri(); // dağılım özetinde öğretmensiz ders ya da aşım yok
    programApisi([[]]);
    const mesaj = "9-A Matematik haftada 6 saat, ama bu ders bu şubeye günde en fazla 1 saat konabildiği (özel ayar) için en fazla 5 saat yerleşebilir.";
    sunucu.use(http.get("/api/ders-programi/on-kontrol", () =>
      HttpResponse.json({ celiskiler: [{ tur: "ders_gun_kapasitesi", mesaj, ilgili: [] }] })));
    uygulamayiCiz("/program");
    expect(await screen.findByText(mesaj)).toBeInTheDocument();
    expect(screen.queryByText(/Ön kontrol tamam/)).toBeNull();
    expect(screen.getByRole("button", { name: "Programı oluştur" })).toBeDisabled();
  });

  it("engel yoksa oluşturulur; seçilen süre ve ad gönderilir; bekleme ekranı açılır", async () => {
    hazirVeri();
    const govdeler = programApisi([[], [program()]]);
    const { kullanici } = uygulamayiCiz("/program");
    expect(await screen.findByText(/Ön kontrol tamam/)).toBeInTheDocument();
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

  it("hazır program varsa o öne çıkar; sonraki başarısız deneme sade uyarı, nedeni açılınca görünür", async () => {
    hazirVeri();
    const basarisiz = program({
      id: "p2", ad: "Program 2", durum: "basarisiz", bitis: "2026-10-24T10:00:00Z",
      celiskiler: [{ tur: "ders_gun_kapasitesi", mesaj: "9-A Matematik günlere sığmıyor.", ilgili: [] }],
    });
    programApisi([[HAZIR, basarisiz]]);
    const { kullanici } = uygulamayiCiz("/program");
    const hazir = await screen.findByRole("region", { name: "“Program 1” hazır" });
    const uyari = screen.getByRole("region", { name: /Son deneme “Program 2” oluşturulamadı/ });
    // Hazır panel önce gelir; büyük kırmızı panel yok.
    expect(hazir.compareDocumentPosition(uyari) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByRole("region", { name: "“Program 2” oluşturulamadı" })).toBeNull();
    // Ayrıntı kapalı başlar, açılınca neden görünür.
    const ozet = within(uyari).getByText("Nedenini göster");
    expect(ozet.closest("details")).not.toHaveAttribute("open");
    await kullanici.click(ozet);
    expect(ozet.closest("details")).toHaveAttribute("open");
    expect(within(uyari).getByText("9-A Matematik günlere sığmıyor.")).toBeVisible();
  });

  it("hiç hazır program yoksa başarısız deneme büyük panelde", async () => {
    hazirVeri();
    programApisi([[program({ durum: "basarisiz", hata_mesaji: "Süre yetmedi." })]]);
    uygulamayiCiz("/program");
    expect(await screen.findByRole("region", { name: "“Program 1” oluşturulamadı" })).toBeInTheDocument();
    expect(screen.queryByText(/Son deneme/)).toBeNull();
  });

  it("süre yetmediyse (bilinmiyor) anlaşılır mesaj ve tek tıkla daha uzun süreyle yeniden deneme", async () => {
    hazirVeri();
    const govdeler = programApisi([[program({
      durum: "basarisiz", cozum_durumu: "bilinmiyor", sure_siniri_sn: 30, temel_program_id: "p0",
      hata_mesaji: "Kurallara uyan bir program var, ama 30 sn içinde bulunamadı.",
    })]]);
    const { kullanici } = uygulamayiCiz("/program");
    const panel = await screen.findByRole("region", { name: "“Program 1” oluşturulamadı" });
    expect(panel).toHaveTextContent("Seçilen süre yetmedi.");
    expect(panel).toHaveTextContent("Bu süre okulunuz için yetmedi. 30 saniye içinde kurallara uyan bir program bulunamadı");
    await kullanici.click(within(panel).getByRole("button", { name: "2 dakika ile yeniden dene" }));
    await waitFor(() => expect(govdeler).toEqual([{ ad: "Program 1", sure_siniri_sn: 120, temel_program_id: "p0" }]));
  });

  it("en uzun seçenek de yetmediyse 10 dakika önerilir; hazır program varken uyarı da süreyi söyler", async () => {
    hazirVeri();
    programApisi([[HAZIR, program({ id: "p2", ad: "Program 2", durum: "basarisiz", cozum_durumu: "bilinmiyor", sure_siniri_sn: 300 })]]);
    const { kullanici } = uygulamayiCiz("/program");
    const uyari = await screen.findByRole("region", { name: /Son deneme “Program 2” oluşturulamadı/ });
    expect(uyari).toHaveTextContent("seçilen süre yetmedi, daha uzun bir süreyle yeniden deneyebilirsiniz");
    await kullanici.click(within(uyari).getByText("Nedenini göster"));
    expect(within(uyari).getByRole("button", { name: "10 dakika ile yeniden dene" })).toBeVisible();
  });

  it("büyük okulda Hızlı seçeneğinin yanında yetmeyebileceği söylenir", async () => {
    hazirVeri();
    programApisi([[]]);
    const siniflar = Array.from({ length: 36 }, (_, i) => ({ id: `s${i}`, ad: `Şube ${i}`, seviye: 9, sube_grubu_id: null }));
    sunucu.use(http.get("/api/siniflar", () => HttpResponse.json(siniflar)));
    uygulamayiCiz("/program");
    const hizli = await screen.findByRole("radio", { name: /Hızlı/ });
    await waitFor(() => expect(hizli.closest("label")).toHaveTextContent("Okulunuzda 36 şube var; bu süre program bulmaya yetmeyebilir."));
    expect(screen.getByRole("radio", { name: /Dengeli/ }).closest("label")).not.toHaveTextContent("yetmeyebilir");
  });

  it("küçük okulda Hızlı için uyarı yok", async () => {
    hazirVeri();
    programApisi([[]]);
    uygulamayiCiz("/program");
    expect(await screen.findByText(/Ön kontrol tamam/)).toBeInTheDocument();
    expect(screen.queryByText(/yetmeyebilir/)).toBeNull();
  });

  it("çelişki listesi yoksa sunucunun mesajı satır satır gösterilir", async () => {
    hazirVeri();
    programApisi([[program({ durum: "basarisiz", hata_mesaji: "Süre yetmedi.\nDaha uzun süre deneyin." })]]);
    uygulamayiCiz("/program");
    const panel = await screen.findByRole("region", { name: "“Program 1” oluşturulamadı" });
    expect(within(panel).getAllByRole("listitem").map((l) => l.textContent)).toEqual(["Süre yetmedi.", "Daha uzun süre deneyin."]);
  });
});
