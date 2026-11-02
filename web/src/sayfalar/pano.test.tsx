/** Ana sayfa panosu: ilerleme halkası, sayı kartları, kurulum adımları (aynı veriden). */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

const adimlar = () => within(screen.getByRole("region", { name: "Kurulum adımları" }));

describe("ana sayfa panosu", () => {
  it("\"Yeni program\" program sayfasındaki oluşturma kartına götürür, ad alanı odaklanır", async () => {
    dagilimApisiKur();
    const { kullanici } = uygulamayiCiz("/");
    const yeni = await screen.findByRole("link", { name: "Yeni program" });
    expect(yeni).toHaveAttribute("href", "/program#olustur");
    await kullanici.click(yeni);
    expect(await screen.findByRole("textbox", { name: /Programın adı/ })).toHaveFocus();
  });

  it("halka, kartlar ve kontrol listesi aynı durumu söyler", async () => {
    dagilimApisiKur(); // 4 öğretmen, 4 şube, 3 ders, 4 atama (2'si öğretmensiz, toplam 20 saat)
    uygulamayiCiz("/");

    const halka = await screen.findByRole("img", { name: "Kurulum: 6 adımdan 4 tanesi tamam" });
    expect(halka).toHaveTextContent("%67");

    const sayilar = screen.getByRole("list", { name: "Okulunuz sayılarla" });
    expect(within(sayilar).getAllByRole("link").map((k) => k.textContent)).toEqual([
      "4Öğretmen", "4Şube", "3Ders", "20Haftalık ders saati",
    ]);

    const dagilim = adimlar().getByRole("link", { name: /Ders dağılımı/ });
    expect(dagilim).toHaveTextContent("2 dersin öğretmeni seçilmedi");
    expect(dagilim).toHaveTextContent("(Eksik)");
    expect(dagilim).toHaveAttribute("href", "/ders-dagilimi");
    expect(adimlar().getByRole("link", { name: /Öğretmenler/ })).toHaveTextContent("4 öğretmen(Tamam)");
    expect(adimlar().getByRole("link", { name: /Öğretmen müsaitliği/ })).toHaveTextContent("(İsteğe bağlı)");
  });

  it("boş okulda halka %17, adımlar ne yapılacağını söyler", async () => {
    uygulamayiCiz("/");
    expect(await screen.findByRole("img", { name: "Kurulum: 6 adımdan 1 tanesi tamam" })).toHaveTextContent("%17");
    expect(adimlar().getByRole("link", { name: /Öğretmenler/ })).toHaveTextContent("Henüz öğretmen yok(Bekliyor)");
    expect(screen.getByText(/Aşağıdaki adımları tamamlayınca programı üretebilirsiniz/)).toBeInTheDocument();
  });

  it("yük kartı en yüklü öğretmenleri sırayla gösterir; yayın yoksa ne yapılacağını söyler", async () => {
    dagilimApisiKur(); // Şule 6, Zeynep 2, Ali ve Ayşe 0 saat
    uygulamayiCiz("/");
    const yuk = within(await screen.findByRole("region", { name: "Haftalık ders saatleri" }));
    expect(yuk.getAllByRole("listitem").map((l) => l.textContent)).toEqual(["Şule Kaya6 / 40 saat", "Zeynep Demir2 / 40 saat"]);
    expect(screen.getByRole("heading", { name: "Yayında program yok" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Haftalık program" })).toBeInTheDocument();
  });

  it("yayındaki programın ilk şubesi küçük çizelgede; yayın kartı programı ve tarihini söyler", async () => {
    dagilimApisiKur();
    sunucu.use(
      http.get("/api/ders-programi/yayin", () =>
        HttpResponse.json({ program_id: "p1", program_adi: "Güz programı", yayin_zamani: "2026-10-30T09:00:00Z", uyarilar: [], eski_veri: false, program_degisti: false }),
      ),
      http.get("/api/ders-programi/programlar/p1/yerlesimler", () =>
        HttpResponse.json([
          { id: "y1", ders_atama_id: "a-9a-mat", gun: 0, saat: 0, kilitli: false },
          { id: "y2", ders_atama_id: "a-9a-fiz", gun: 1, saat: 2, kilitli: false },
          { id: "y3", ders_atama_id: "a-9b-mat", gun: 0, saat: 1, kilitli: false }, // başka şube: görünmez
        ]),
      ),
    );
    uygulamayiCiz("/");
    expect(await screen.findByRole("heading", { level: 2, name: "Güz programı" })).toBeInTheDocument();
    const mini = await screen.findByRole("img", { name: /9-A şubesinin haftası: 2 ders saati/ });
    expect(mini).toHaveTextContent("MAT");
    expect(mini).toHaveTextContent("FİZ");
    expect(screen.getByRole("link", { name: /Tamamını aç/ })).toHaveAttribute("href", "/program/p1");
  });
});
