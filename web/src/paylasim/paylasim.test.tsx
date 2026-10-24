/** Paylaşım sayfası (8b): girişsiz açılır; gün gün ve haftalık; seçim ve PDF; geçersiz link; yayın yok. */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "../api/sema";
import { oturumYok, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type Icerik = components["schemas"]["PaylasimYanit"];
const YOL = "/api/ders-programi/paylasim/:jeton";

const hucre = (gun: number, saat: number, ders: string, sube: string, uzunluk = 1) => ({
  gun, saat, uzunluk, ders, kisa_ad: ders.slice(0, 3), renk: "#2563eb", sube, ogretmen: "Ayşe Yılmaz",
});

const ICERIK: Icerik = {
  tur: "ogretmen", yayinda: true, yayin_zamani: "2026-10-24T09:00:00Z", okul: "Atatürk Anadolu Lisesi",
  program: "Güz Programı",
  hafta: { gun_adlari: ["Pazartesi", "Salı"], gun_saatleri: [3, 3], saat_sayisi: 3, ogle_arasi_sonra: null, zil: null,
    ogle_zili: null },
  subeler: [],
  ogretmenler: [{ ad: "Ayşe Yılmaz", tur: "ogretmen",
    hucreler: [hucre(0, 0, "Matematik", "9-A", 2), hucre(1, 1, "Matematik", "9-B")] }],
};

describe("Paylaşım sayfası", () => {
  it("girişsiz açılır: öğretmenin programı, şube adı her hücrede, PDF bağlantısı", async () => {
    oturumYok();
    sunucu.use(http.get(YOL, () => HttpResponse.json(ICERIK)));
    uygulamayiCiz("/p/abc");
    expect(await screen.findByRole("heading", { name: /Ayşe Yılmaz/ })).toBeInTheDocument();
    expect(screen.getByText(/haftada 3 ders saati/)).toBeInTheDocument();
    const tablo = screen.getByRole("table", { name: "Ayşe Yılmaz haftalık ders programı" });
    expect(within(tablo).getByText("9-A")).toBeInTheDocument();
    expect(within(tablo).getByText("9-B")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /PDF indir/ })).toHaveAttribute("href", "/api/ders-programi/paylasim/abc/program.pdf");
    // Menü ya da giriş sayfası yok.
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("gün gün: gün seçilince o günün dersleri; blok tek satır", async () => {
    oturumYok();
    sunucu.use(http.get(YOL, () => HttpResponse.json(ICERIK)));
    const { kullanici } = uygulamayiCiz("/p/abc");
    await kullanici.click(await screen.findByRole("button", { name: "Pazartesi" }));
    const liste = screen.getByRole("list", { name: "Pazartesi dersleri" });
    expect(within(liste).getByText("1.-2. saat")).toBeInTheDocument();
    await kullanici.click(screen.getByRole("button", { name: "Salı" }));
    const sali = screen.getByRole("list", { name: "Salı dersleri" });
    expect(within(sali).getAllByText("Boş")).toHaveLength(2);
    expect(within(sali).getByText("9-B")).toBeInTheDocument();
  });

  it("okul linkinde şube ya da öğretmen seçilir; PDF seçilenin", async () => {
    sunucu.use(http.get(YOL, () => HttpResponse.json({
      ...ICERIK, tur: "okul",
      subeler: [{ ad: "9-A", tur: "sube", hucreler: [hucre(0, 0, "Matematik", "9-A", 2)] }],
    })));
    const { kullanici } = uygulamayiCiz("/p/abc");
    expect(await screen.findByRole("heading", { name: /9-A/ })).toBeInTheDocument();
    await kullanici.selectOptions(screen.getByLabelText("Şube ya da öğretmen"), "ogretmen:Ayşe Yılmaz");
    expect(screen.getByRole("heading", { name: /Ayşe Yılmaz/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /PDF indir/ }).getAttribute("href")).toContain("?ogretmen=Ay%C5%9Fe+Y%C4%B1lmaz");
  });

  it("geçersiz ya da iptal edilmiş link; yayın yok", async () => {
    sunucu.use(http.get(YOL, () => HttpResponse.json({ detail: "Paylaşım linki bulunamadı" }, { status: 404 })));
    uygulamayiCiz("/p/eski");
    expect(await screen.findByRole("heading", { name: "Bu link geçerli değil" })).toBeInTheDocument();
    expect(screen.getByText(/iptal edilmiş ya da yenilenmiş/)).toBeInTheDocument();
  });

  it("yayında program yoksa söyler", async () => {
    sunucu.use(http.get(YOL, () => HttpResponse.json({ ...ICERIK, yayinda: false, hafta: null, ogretmenler: [] })));
    uygulamayiCiz("/p/abc");
    expect(await screen.findByRole("heading", { name: "Yayında program yok" })).toBeInTheDocument();
  });
});
