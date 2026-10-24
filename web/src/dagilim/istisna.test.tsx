/** Şube istisnaları (K5): "bu şube bu dersi almaz", ek ders, şubeye özel liste. */
import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { dagilimApisiKur } from "../test/dagilimApisi";
import { uygulamayiCiz } from "../test/yardimcilar";

// 9. sınıfların şablonu: Matematik 6 (Fizik şablonda yok).
const SABLON = [{ id: "ss-mat", seviye: 9, sube_grubu_id: null, ders_id: "d-mat", haftalik_saat: 6 }];

describe("şube istisnaları", () => {
  it("şablondaki ders kaldırılırken 'hiç almasın' işaretli gelir; istisna yazılır, ders kalkar, listede görünür", async () => {
    const api = dagilimApisiKur({ sablon: SABLON });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9b");
    await kullanici.click(await screen.findByRole("button", { name: "Matematik dersini kaldır" }));
    const pencere = await screen.findByRole("dialog");
    const kutu = within(pencere).getByRole("checkbox", { name: /9-B bu dersi hiç almasın/ });
    expect(kutu).toBeChecked();
    await kullanici.click(within(pencere).getByRole("button", { name: "Kaldır" }));

    expect(await screen.findByText("9-B artık Matematik almıyor; şablon yeniden uygulansa da eklenmez.")).toBeInTheDocument();
    expect(api.istekler).toEqual([{ yontem: "POST", yol: "istisnalar", govde: { sinif_id: "s-9b", ders_id: "d-mat", tur: "almaz" } }]);
    const ozel = await screen.findByRole("heading", { name: "Bu şubeye özel" });
    expect(ozel.parentElement).toHaveTextContent("Matematik almaz");
    expect(screen.queryByRole("row", { name: /Matematik/ })).toBeNull();
  });

  it("'hiç almasın' kaldırılırsa yalnızca ders silinir", async () => {
    const api = dagilimApisiKur({ sablon: SABLON });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9b");
    await kullanici.click(await screen.findByRole("button", { name: "Matematik dersini kaldır" }));
    const pencere = await screen.findByRole("dialog");
    await kullanici.click(within(pencere).getByRole("checkbox", { name: /hiç almasın/ }));
    await kullanici.click(within(pencere).getByRole("button", { name: "Kaldır" }));
    await waitFor(() => expect(api.istekler).toEqual([{ yontem: "DELETE", yol: "atamalar/a-9b-mat" }]));
  });

  it("şablonda olmayan ders için 'hiç almasın' sorulmaz", async () => {
    dagilimApisiKur({ sablon: SABLON });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9a");
    await kullanici.click(await screen.findByRole("button", { name: "Fizik dersini kaldır" }));
    expect(within(await screen.findByRole("dialog")).queryByRole("checkbox")).toBeNull();
  });

  it("şablonda olmayan ders ek ders olarak eklenir ve rozetle gösterilir", async () => {
    const api = dagilimApisiKur({ sablon: SABLON });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9b");
    await kullanici.selectOptions(await screen.findByRole("combobox", { name: "Ders" }), "d-fiz");
    expect(screen.getByRole("checkbox", { name: /ek ders olarak kaydet/ })).toBeChecked();
    await kullanici.type(screen.getByRole("spinbutton", { name: "Haftalık saat" }), "2");
    await kullanici.click(screen.getByRole("button", { name: "Ekle" }));
    expect(await screen.findByText("Fizik, 9-B şubesine ek ders olarak eklendi. Öğretmenini seçin.")).toBeInTheDocument();
    expect(api.istekler).toEqual([
      { yontem: "POST", yol: "istisnalar", govde: { sinif_id: "s-9b", ders_id: "d-fiz", tur: "ek", haftalik_saat: 2 } },
    ]);
    expect(await within(screen.getByRole("row", { name: /Fizik/ })).findByText("Ek ders")).toBeInTheDocument();
  });

  it("şablondaki ders eklenirken ek ders sorulmaz", async () => {
    const api = dagilimApisiKur({ sablon: SABLON, atamalar: [] });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9b");
    await kullanici.selectOptions(await screen.findByRole("combobox", { name: "Ders" }), "d-mat");
    expect(screen.queryByRole("checkbox", { name: /ek ders/ })).toBeNull();
    await kullanici.type(screen.getByRole("spinbutton", { name: "Haftalık saat" }), "6");
    await kullanici.click(screen.getByRole("button", { name: "Ekle" }));
    await waitFor(() => expect(api.istekler[0]).toMatchObject({ yontem: "POST", yol: "atamalar" }));
  });

  it("istisna geri alınır; uyarısı varsa gösterilir", async () => {
    const api = dagilimApisiKur({
      sablon: SABLON,
      istisnalar: [{
        id: "i-1", sinif_id: "s-9b", ders_id: "d-mat", tur: "almaz", haftalik_saat: null, sinif_adi: "9-B",
        ders_adi: "Matematik", sablonda: true, atanmis: true,
        uyari: "9-B için \"Matematik almaz\" istisnası var, ama 9-B'ye Matematik atanmış.",
      }],
    });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9b");
    expect(await screen.findByText(/istisnası var, ama 9-B'ye Matematik atanmış/)).toBeInTheDocument();
    await kullanici.click(screen.getByRole("button", { name: "Matematik: “almaz” işaretini kaldır" }));
    expect(await screen.findByText("9-B için “Matematik almaz” işareti kaldırıldı.")).toBeInTheDocument();
    expect(api.istekler).toEqual([{ yontem: "DELETE", yol: "istisnalar/i-1" }]);
  });

  it("şubenin grubunun şablonu varsa o kullanılır", async () => {
    // 9-B "9 Fen" grubunda; grubun şablonunda Fizik var, Matematik yok.
    dagilimApisiKur({
      sablon: [...SABLON, { id: "ss-g-fiz", seviye: 9, sube_grubu_id: "g-fen", ders_id: "d-fiz", haftalik_saat: 4 }],
      siniflar: [{ id: "s-9b", ad: "9-B", seviye: 9, sube_grubu_id: "g-fen" }],
      gruplar: [{ id: "g-fen", ad: "9 Fen", seviye: 9 }],
    });
    const { kullanici } = uygulamayiCiz("/ders-dagilimi?gorunum=sube&sinif=s-9b");
    await kullanici.click(await screen.findByRole("button", { name: "Matematik dersini kaldır" }));
    expect(within(await screen.findByRole("dialog")).queryByRole("checkbox")).toBeNull(); // grubun şablonunda yok
  });
});
