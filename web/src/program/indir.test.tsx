/** "İndir" menüsü (7.2): çıktı bağlantıları, seçili şube/öğretmen, imza alanı seçeneği, kapanma. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { IndirMenusu } from "./IndirMenusu";

const KOK = "/api/ders-programi/programlar/p1/cikti";

const baglanti = (ad: RegExp) => screen.getByRole("link", { name: ad }).getAttribute("href");

describe("İndir menüsü", () => {
  it("kapalı başlar; açılınca bütün çıktılar indirme bağlantısı", async () => {
    const kullanici = userEvent.setup();
    render(<IndirMenusu programId="p1" />);
    const dugme = screen.getByRole("button", { name: /İndir/ });
    expect(dugme).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();

    await kullanici.click(dugme);
    expect(dugme).toHaveAttribute("aria-expanded", "true");
    expect(baglanti(/^Şube programları/)).toBe(`${KOK}/subeler.pdf`);
    expect(baglanti(/^Öğretmen programları/)).toBe(`${KOK}/ogretmenler.pdf`);
    expect(baglanti(/^Çarşaf liste \(öğretmenler\)/)).toBe(`${KOK}/carsaf.pdf?satir=ogretmen`);
    expect(baglanti(/^Çarşaf liste \(şubeler\)/)).toBe(`${KOK}/carsaf.pdf?satir=sube`);
    expect(baglanti(/^Excel/)).toBe(`${KOK}/program.xlsx`);
    expect(screen.getAllByRole("link").every((a) => a.hasAttribute("download"))).toBe(true);
  });

  it("seçili şubenin tek sayfası; imza seçeneği şube ve öğretmen PDF'lerine eklenir", async () => {
    const kullanici = userEvent.setup();
    render(<IndirMenusu programId="p1" secili={{ tur: "sube", id: "s9", ad: "9-A" }} />);
    await kullanici.click(screen.getByRole("button", { name: /İndir/ }));
    expect(baglanti(/^9-A programı/)).toBe(`${KOK}/subeler.pdf?sinif_id=s9`);
    await kullanici.click(screen.getByRole("checkbox", { name: /Okul Müdürü/ }));
    expect(baglanti(/^9-A programı/)).toBe(`${KOK}/subeler.pdf?sinif_id=s9&imza=true`);
    expect(baglanti(/^Öğretmen programları/)).toBe(`${KOK}/ogretmenler.pdf?imza=true`);
    expect(baglanti(/^Çarşaf liste \(şubeler\)/)).toBe(`${KOK}/carsaf.pdf?satir=sube`);
  });

  it("seçili öğretmen; Escape kapatır ve odağı düğmeye verir", async () => {
    const kullanici = userEvent.setup();
    render(<IndirMenusu programId="p1" secili={{ tur: "ogretmen", id: "o1", ad: "Ayşe Yılmaz" }} />);
    const dugme = screen.getByRole("button", { name: /İndir/ });
    await kullanici.click(dugme);
    expect(baglanti(/^Ayşe Yılmaz programı/)).toBe(`${KOK}/ogretmenler.pdf?ogretmen_id=o1`);
    await kullanici.keyboard("{Escape}");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(dugme).toHaveFocus();
  });
});
