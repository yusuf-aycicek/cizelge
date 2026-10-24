/** Sınıflar sayfasında şube grupları (K5): şube satırında grup seçimi, grup ekleme ve silme. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type Sinif = { id: string; ad: string; seviye: number; sube_grubu_id: string | null };
type Grup = { id: string; ad: string; seviye: number };

function api(siniflar: Sinif[], gruplar: Grup[]) {
  const istekler: { yontem: string; yol: string; govde?: unknown }[] = [];
  sunucu.use(
    http.get("/api/siniflar", () => HttpResponse.json(siniflar)),
    http.get("/api/sube-gruplari", () => HttpResponse.json(gruplar)),
    http.patch("/api/siniflar/:id", async ({ request, params }) => {
      const govde = (await request.json()) as Partial<Sinif>;
      istekler.push({ yontem: "PATCH", yol: `siniflar/${params.id}`, govde });
      siniflar = siniflar.map((s) => (s.id === params.id ? { ...s, ...govde } : s));
      return HttpResponse.json(siniflar.find((s) => s.id === params.id));
    }),
    http.post("/api/sube-gruplari", async ({ request }) => {
      const govde = (await request.json()) as Omit<Grup, "id">;
      istekler.push({ yontem: "POST", yol: "sube-gruplari", govde });
      const yeni = { id: `g${gruplar.length + 1}`, ...govde };
      gruplar = [...gruplar, yeni];
      return HttpResponse.json(yeni, { status: 201 });
    }),
    http.delete("/api/sube-gruplari/:id", ({ params }) => {
      istekler.push({ yontem: "DELETE", yol: `sube-gruplari/${params.id}` });
      gruplar = gruplar.filter((g) => g.id !== params.id);
      siniflar = siniflar.map((s) => (s.sube_grubu_id === params.id ? { ...s, sube_grubu_id: null } : s));
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return istekler;
}

const SINIFLAR: Sinif[] = [
  { id: "s-11a", ad: "11-A", seviye: 11, sube_grubu_id: "g-say" },
  { id: "s-11b", ad: "11-B", seviye: 11, sube_grubu_id: null },
  { id: "s-9a", ad: "9-A", seviye: 9, sube_grubu_id: null },
];
const GRUPLAR: Grup[] = [{ id: "g-say", ad: "11 Sayısal", seviye: 11 }, { id: "g-soz", ad: "11 Sözel", seviye: 11 }];

describe("şube grupları", () => {
  it("şube satırında yalnızca kendi seviyesinin grupları; seçince kaydedilir", async () => {
    const istekler = api(SINIFLAR, GRUPLAR);
    const { kullanici } = uygulamayiCiz("/siniflar");
    const secim = await screen.findByRole("combobox", { name: "11-B şubesinin grubu" });
    expect(within(secim).getAllByRole("option").map((o) => o.textContent)).toEqual(["Grup yok", "11 Sayısal", "11 Sözel"]);
    expect(screen.getByRole("combobox", { name: "11-A şubesinin grubu" })).toHaveValue("g-say");
    // 9. sınıf grubu yok: seçim kutusu yerine çizgi.
    expect(screen.queryByRole("combobox", { name: "9-A şubesinin grubu" })).toBeNull();
    await kullanici.selectOptions(secim, "g-soz");
    expect(await screen.findByText("11-B artık 11 Sözel grubunda.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "PATCH", yol: "siniflar/s-11b", govde: { sube_grubu_id: "g-soz" } }]);
  });

  it("grup listesinde şubeleri yazar; grup eklenir", async () => {
    const istekler = api(SINIFLAR, GRUPLAR);
    const { kullanici } = uygulamayiCiz("/siniflar");
    const bolum = await screen.findByRole("region", { name: "Şube grupları" });
    const tablo = await within(bolum).findByRole("table", { name: "Şube grupları" });
    expect(within(tablo).getByRole("row", { name: /11 Sayısal/ })).toHaveTextContent("11-A");
    expect(within(tablo).getByRole("row", { name: /11 Sözel/ })).toHaveTextContent("Henüz şube yok");
    await kullanici.type(within(bolum).getByRole("textbox", { name: "Grubun adı" }), "9 Fen");
    await kullanici.selectOptions(within(bolum).getByRole("combobox", { name: "Seviye" }), "9");
    await kullanici.click(within(bolum).getByRole("button", { name: "Grup ekle" }));
    expect(await screen.findByText(/9 Fen grubu eklendi/)).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "POST", yol: "sube-gruplari", govde: { ad: "9 Fen", seviye: 9 } }]);
  });

  it("ad ve seviye girilmeden grup eklenmez", async () => {
    const istekler = api(SINIFLAR, []);
    const { kullanici } = uygulamayiCiz("/siniflar");
    const bolum = await screen.findByRole("region", { name: "Şube grupları" });
    await kullanici.click(within(bolum).getByRole("button", { name: "Grup ekle" }));
    expect(within(bolum).getByRole("textbox", { name: "Grubun adı" })).toHaveAccessibleDescription("Grubun adını yazın (ör. 11 Sayısal).");
    await kullanici.type(within(bolum).getByRole("textbox", { name: "Grubun adı" }), "9 Fen");
    await kullanici.click(within(bolum).getByRole("button", { name: "Grup ekle" }));
    expect(within(bolum).getByRole("textbox", { name: "Grubun adı" })).toHaveAccessibleDescription("Grubun seviyesini seçin.");
    expect(istekler).toEqual([]);
  });

  it("grup onayla silinir; ne olacağı söylenir", async () => {
    const istekler = api(SINIFLAR, GRUPLAR);
    const { kullanici } = uygulamayiCiz("/siniflar");
    await kullanici.click(await screen.findByRole("button", { name: "11 Sayısal grubunu sil" }));
    const pencere = await screen.findByRole("dialog");
    expect(pencere).toHaveTextContent("Şubeler silinmez, grupsuz kalır");
    await kullanici.click(within(pencere).getByRole("button", { name: "Grubu sil" }));
    await waitFor(() => expect(istekler).toEqual([{ yontem: "DELETE", yol: "sube-gruplari/g-say" }]));
    expect(await screen.findByText(/11 Sayısal grubu silindi/)).toBeInTheDocument();
  });
});
