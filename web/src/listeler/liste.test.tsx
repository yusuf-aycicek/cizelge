/** Öğretmen, sınıf ve ders listeleri (ortak liste bileşeni), sahte API ile. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type Ogretmen = { id: string; ad: string; brans: string };

/** Bellekte tutan sahte öğretmen API'si: ekleme, güncelleme, silme listeye yansır. */
function ogretmenApisi(baslangic: Ogretmen[]) {
  let kayitlar = [...baslangic];
  const istekler: { yontem: string; govde?: unknown }[] = [];
  sunucu.use(
    http.get("/api/ogretmenler", () => HttpResponse.json(kayitlar)),
    http.post("/api/ogretmenler", async ({ request }) => {
      const govde = (await request.json()) as Omit<Ogretmen, "id">;
      istekler.push({ yontem: "POST", govde });
      if (kayitlar.some((k) => k.ad === govde.ad)) {
        return HttpResponse.json({ detail: "Bu okulda bu adla bir öğretmen zaten var" }, { status: 409 });
      }
      const yeni = { id: `o${kayitlar.length + 1}`, ...govde };
      kayitlar = [...kayitlar, yeni];
      return HttpResponse.json(yeni, { status: 201 });
    }),
    http.patch("/api/ogretmenler/:id", async ({ request, params }) => {
      const govde = (await request.json()) as Partial<Ogretmen>;
      istekler.push({ yontem: "PATCH", govde });
      kayitlar = kayitlar.map((k) => (k.id === params.id ? { ...k, ...govde } : k));
      return HttpResponse.json(kayitlar.find((k) => k.id === params.id));
    }),
    http.delete("/api/ogretmenler/:id", ({ params }) => {
      istekler.push({ yontem: "DELETE" });
      kayitlar = kayitlar.filter((k) => k.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return istekler;
}

const satirAdlari = () =>
  within(screen.getByRole("table", { name: "Öğretmenler" }))
    .getAllByRole("row")
    .slice(1)
    .map((s) => within(s).getAllByRole("cell")[0]?.textContent);

describe("boş liste", () => {
  it("ne yapılacağını anlatır; düğme ekleme formuna götürür", async () => {
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    const bos = await screen.findByRole("region", { name: "Henüz öğretmen eklenmedi" });
    expect(within(bos).getByText(/Ders dağılımı yapabilmek için önce öğretmenlerinizi ekleyin/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await kullanici.click(within(bos).getByRole("button", { name: "İlk öğretmeni ekle" }));
    expect(screen.getByLabelText(/Adı soyadı/)).toHaveFocus();
  });

  it.each([
    ["/siniflar", "Henüz sınıf eklenmedi", "İlk sınıfı ekle"],
    ["/dersler", "Henüz ders eklenmedi", "İlk dersi ekle"],
  ])("%s boşken de anlatır", async (adres, baslik, dugme) => {
    uygulamayiCiz(adres);
    const bos = await screen.findByRole("region", { name: baslik });
    expect(within(bos).getByRole("button", { name: dugme })).toBeInTheDocument();
  });
});

describe("liste, sıralama, arama", () => {
  const OGRETMENLER = ["Zeynep Demir", "Ümit Kara", "Şule Kaya", "Ömer Can", "İsmail Er", "Irmak Su", "Çağla Öz", "Cem Ak", "Gül Ay"]
    .map((ad, i) => ({ id: `o${i}`, ad, brans: "" }));

  it("Türkçe sırayla gösterir", async () => {
    ogretmenApisi(OGRETMENLER);
    uygulamayiCiz("/ogretmenler");
    await screen.findByRole("table", { name: "Öğretmenler" });
    expect(satirAdlari()).toEqual([
      "Cem Ak", "Çağla Öz", "Gül Ay", "Irmak Su", "İsmail Er", "Ömer Can", "Şule Kaya", "Ümit Kara", "Zeynep Demir",
    ]);
    expect(screen.getByLabelText("Ara")).toHaveAccessibleDescription("9 öğretmen");
  });

  it("arar (Türkçe büyük/küçük harf); sonuç yoksa söyler", async () => {
    ogretmenApisi(OGRETMENLER);
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    await kullanici.type(await screen.findByLabelText("Ara"), "ismail");
    expect(satirAdlari()).toEqual(["İsmail Er"]);
    await kullanici.clear(screen.getByLabelText("Ara"));
    await kullanici.type(screen.getByLabelText("Ara"), "ŞULE");
    expect(satirAdlari()).toEqual(["Şule Kaya"]);
    await kullanici.clear(screen.getByLabelText("Ara"));
    await kullanici.type(screen.getByLabelText("Ara"), "xyz");
    expect(screen.getByRole("heading", { name: '"xyz" ile eşleşen öğretmen yok.' })).toBeInTheDocument();
    // Boş sonuçta arama tek tıkla temizlenir, liste geri gelir.
    await kullanici.click(screen.getByRole("button", { name: "Aramayı temizle" }));
    expect(screen.getByLabelText("Ara")).toHaveValue("");
    expect(satirAdlari()).toContain("Şule Kaya");
  });

  it("şubeler sayıyla sıralanır (9-A, 10-A)", async () => {
    sunucu.use(http.get("/api/siniflar", () => HttpResponse.json(
      ["10-A", "9-B", "11-A", "9-A"].map((ad, i) => ({ id: `s${i}`, ad, seviye: Number(ad.split("-")[0]) })))));
    uygulamayiCiz("/siniflar");
    const tablo = await screen.findByRole("table", { name: "Sınıflar" });
    const adlar = within(tablo).getAllByRole("row").slice(1).map((s) => within(s).getAllByRole("cell")[0]?.textContent);
    expect(adlar).toEqual(["9-A", "9-B", "10-A", "11-A"]);
  });
});

describe("ekleme", () => {
  it("ekler, bildirir, formu boşaltır ve odağı ilk alana döndürür", async () => {
    const istekler = ogretmenApisi([]);
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    await kullanici.type(await screen.findByLabelText(/Adı soyadı/), "  Şule Kaya ");
    await kullanici.type(screen.getByLabelText("Branşı"), "Kimya");
    await kullanici.click(screen.getByRole("button", { name: "Ekle" }));

    expect(await screen.findByText("Şule Kaya eklendi.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "POST", govde: { ad: "Şule Kaya", brans: "Kimya" } }]);
    expect(screen.getByLabelText(/Adı soyadı/)).toHaveValue("");
    expect(screen.getByLabelText(/Adı soyadı/)).toHaveFocus();
    expect(await screen.findByRole("cell", { name: "Şule Kaya" })).toBeInTheDocument();
  });

  it("boş ad ve geçersiz seviye sunucuya gitmez", async () => {
    let istek = 0;
    sunucu.use(http.post("/api/siniflar", () => { istek++; return HttpResponse.json({}, { status: 201 }); }));
    const { kullanici } = uygulamayiCiz("/siniflar");
    await kullanici.type(await screen.findByLabelText(/Sınıf seviyesi/), "13");
    await kullanici.click(screen.getByRole("button", { name: "Ekle" }));
    expect(screen.getByRole("textbox", { name: /^Şube/ })).toHaveAccessibleDescription("Boş bırakılamaz");
    expect(screen.getByLabelText(/Sınıf seviyesi/)).toHaveAccessibleDescription("1 ile 12 arasında bir sayı girin");
    expect(screen.getByRole("textbox", { name: /^Şube/ })).toHaveFocus();
    expect(istek).toBe(0);
  });

  it("aynı adla ikinci kayıt: sunucunun mesajı ad alanının altında", async () => {
    ogretmenApisi([{ id: "o1", ad: "Ali Çelik", brans: "" }]);
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    await kullanici.type(await screen.findByLabelText(/Adı soyadı/), "Ali Çelik");
    await kullanici.click(screen.getByRole("button", { name: "Ekle" }));
    await waitFor(() =>
      expect(screen.getByLabelText(/Adı soyadı/)).toHaveAccessibleDescription("Bu okulda bu adla bir öğretmen zaten var"));
  });
});

describe("düzenleme", () => {
  it("satırda düzenlenir, Enter kaydeder; Esc vazgeçer", async () => {
    const istekler = ogretmenApisi([{ id: "o1", ad: "Ali Çelik", brans: "İngilizce" }]);
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    await kullanici.click(await screen.findByRole("button", { name: "Ali Çelik düzenle" }));
    const brans = screen.getByRole("textbox", { name: "Branşı (düzenleme)" });
    await kullanici.clear(brans);
    await kullanici.type(brans, "Almanca{Enter}");
    expect(await screen.findByText("Ali Çelik kaydedildi.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "PATCH", govde: { ad: "Ali Çelik", brans: "Almanca" } }]);
    expect(await screen.findByRole("cell", { name: "Almanca" })).toBeInTheDocument();

    await kullanici.click(screen.getByRole("button", { name: "Ali Çelik düzenle" }));
    await kullanici.type(screen.getByRole("textbox", { name: "Branşı (düzenleme)" }), "xxx{Escape}");
    expect(screen.queryByRole("textbox", { name: "Branşı (düzenleme)" })).not.toBeInTheDocument();
    expect(istekler).toHaveLength(1);
  });
});

describe("silme", () => {
  it("onaylanınca siler", async () => {
    const istekler = ogretmenApisi([{ id: "o1", ad: "Ali Çelik", brans: "" }]);
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    await kullanici.click(await screen.findByRole("button", { name: "Ali Çelik sil" }));
    const pencere = screen.getByRole("dialog", { name: "Ali Çelik silinsin mi?" });
    await kullanici.click(within(pencere).getByRole("button", { name: "Sil" }));
    expect(await screen.findByText("Ali Çelik silindi.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "DELETE" }]);
    expect(await screen.findByRole("region", { name: "Henüz öğretmen eklenmedi" })).toBeInTheDocument();
  });

  it("kullanımda olduğu için silinemezse sunucunun açıklaması kalıcı bir uyarı olarak gösterilir", async () => {
    const mesaj = "Ayşe Yılmaz silinemez: 2 derste öğretmen olarak seçili (9-A Matematik, 9-B Matematik). "
      + "Önce Ders dağılımı sayfasında bu derslere başka bir öğretmen seçin.";
    sunucu.use(
      http.get("/api/ogretmenler", () => HttpResponse.json([{ id: "o1", ad: "Ayşe Yılmaz", brans: "Matematik" }])),
      http.delete("/api/ogretmenler/:id", () => HttpResponse.json({ detail: mesaj }, { status: 409 })),
    );
    const { kullanici } = uygulamayiCiz("/ogretmenler");
    await kullanici.click(await screen.findByRole("button", { name: "Ayşe Yılmaz sil" }));
    await kullanici.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Sil" }));

    const uyari = await screen.findByText(mesaj);
    expect(uyari.closest('[role="alert"]')).not.toBeNull();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Ayşe Yılmaz" })).toBeInTheDocument(); // kayıt duruyor
  });
});
