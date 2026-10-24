/** Excel'den içe aktarma (8a): şablon bağlantısı, önizleme (hatalı / eklenecek), onayla ve kaydet. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "../api/sema";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";
import { SABLON_ADRESI } from "./IceAktarmaSayfasi";

type Onizleme = components["schemas"]["IceAktarmaOnizleme"];
const IA = "/api/ders-programi/ice-aktarma";

const sayfa = (s: Partial<Onizleme["sayfalar"][number]> & Pick<Onizleme["sayfalar"][number], "sayfa" | "baslik">) => ({
  eklenecek: [], guncellenecek: [], hatali: [], degismeyen: 0, atlanan_ornek: 0, ...s,
});

const TEMIZ: Onizleme = {
  sayfalar: [
    sayfa({ sayfa: "ogretmen", baslik: "Öğretmenler", eklenecek: [{ satir: 3, ad: "Ayşe Yılmaz", ayrinti: "Branş: Matematik" }],
      degismeyen: 2 }),
    sayfa({ sayfa: "dagilim", baslik: "Ders dağılımı", guncellenecek: [{ satir: 4, ad: "9-A · Matematik", ayrinti: "Saat: 6 → 5" }] }),
  ],
  eklenecek_sayisi: 1, guncellenecek_sayisi: 1, hata_sayisi: 0, ozet: "abc123",
};

const dosya = () => new File(["x"], "okul.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

describe("Excel'den içe aktarma", () => {
  it("şablon bağlantısı; önizleme gösterilir, onaylanınca özetle kaydedilir", async () => {
    let kaydedilen: string | null = null;
    sunucu.use(
      http.post(`${IA}/onizleme`, () => HttpResponse.json(TEMIZ)),
      http.post(IA, ({ request }) => {
        kaydedilen = new URL(request.url).searchParams.get("ozet");
        return HttpResponse.json({ eklenen: 1, guncellenen: 1 });
      }),
    );
    const { kullanici } = uygulamayiCiz("/ice-aktarma");
    expect(await screen.findByRole("link", { name: /Şablonu indir/ })).toHaveAttribute("href", SABLON_ADRESI);
    await kullanici.upload(screen.getByLabelText(/Excel dosyası/), dosya());
    expect(await screen.findByText(/1 kayıt eklenecek, 1 kayıt güncellenecek\./)).toBeInTheDocument();
    const ogretmenler = screen.getByRole("region", { name: "Öğretmenler" });
    expect(within(ogretmenler).getByRole("table", { name: /Eklenecek/ })).toHaveTextContent("Ayşe Yılmaz");
    expect(ogretmenler).toHaveTextContent("2 satır okulda zaten aynı");
    expect(kaydedilen).toBeNull(); // önizleme kaydetmez
    await kullanici.click(screen.getByRole("button", { name: "Onayla ve kaydet" }));
    expect(await screen.findByText(/1 kayıt eklendi, 1 kayıt güncellendi/)).toBeInTheDocument();
    expect(kaydedilen).toBe("abc123");
    await waitFor(() => expect(screen.queryByRole("heading", { name: "3. Önizleme" })).not.toBeInTheDocument());
  });

  it("hatalı satır varsa satır numarası ve neden; kaydet düğmesi yok", async () => {
    sunucu.use(http.post(`${IA}/onizleme`, () => HttpResponse.json({
      ...TEMIZ, hata_sayisi: 1,
      sayfalar: [sayfa({ sayfa: "sinif", baslik: "Sınıflar", hatali: [{ satir: 7, ad: "9-B", ayrinti: "Seviye 1 ile 12 arasında bir tam sayı olmalı" }] })],
    })));
    const { kullanici } = uygulamayiCiz("/ice-aktarma");
    await kullanici.upload(await screen.findByLabelText(/Excel dosyası/), dosya());
    const tablo = await screen.findByRole("table", { name: /Hatalı satırlar/ });
    expect(tablo).toHaveTextContent("7");
    expect(tablo).toHaveTextContent("Seviye 1 ile 12 arasında");
    expect(screen.queryByRole("button", { name: "Onayla ve kaydet" })).not.toBeInTheDocument();
    expect(screen.getByText(/Hatalı satır varken hiçbir satır kaydedilmez/)).toBeInTheDocument();
  });

  it("okunamayan dosyada sunucunun sade mesajı", async () => {
    sunucu.use(http.post(`${IA}/onizleme`, () =>
      HttpResponse.json({ detail: "Dosya bir Excel dosyası (.xlsx) değil. Şablonu indirip doldurun" }, { status: 422 })));
    const { kullanici } = uygulamayiCiz("/ice-aktarma");
    await kullanici.upload(await screen.findByLabelText(/Excel dosyası/), dosya());
    expect(await screen.findByText(/Excel dosyası \(\.xlsx\) değil/)).toHaveAttribute("role", "alert");
  });
});
