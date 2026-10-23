/** Ana sayfa panosu: ilerleme halkası, sayı kartları, kurulum adımları (aynı veriden). */
import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { uygulamayiCiz } from "../test/yardimcilar";

const adimlar = () => within(screen.getByRole("region", { name: "Kurulum adımları" }));

describe("ana sayfa panosu", () => {
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
});
