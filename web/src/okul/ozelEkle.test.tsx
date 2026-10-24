/** "Özel ayar ekle" (5.6): kural → geçerli kapsamlar → kayıt → değer; kapsam önceliğinin cümlesi. */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { ORNEK_KURALLAR, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";
import { gecerliKapsamlar } from "./OzelAyarEkle";

const N = "gunluk_ders_siniri";
const kural = (tur: string) => ORNEK_KURALLAR.find((k) => k.tur === tur)!;
const MAT_GRUP = {
  kapsam: { ders_id: "d-mat", sinif_id: null, sube_grubu_id: "g-fen", ogretmen_id: null },
  ad: "9 Fen grubu · Matematik",
  parametreler: { n: 3 },
};
const MAT = { kapsam: { ders_id: "d-mat", sinif_id: null, sube_grubu_id: null, ogretmen_id: null }, ad: "Matematik", parametreler: { n: 2 } };

function api() {
  const istekler: { yontem: string; yol: string; govde?: unknown; sorgu?: string }[] = [];
  let kurallar = ORNEK_KURALLAR.map((k) => (k.tur === N ? { ...k, ozel_ayarlar: [MAT_GRUP] } : k));
  sunucu.use(
    http.get("/api/ders-programi/kurallar", () => HttpResponse.json(kurallar)),
    http.get("/api/ogretmenler", () => HttpResponse.json([{ id: "o-ayse", ad: "Ayşe Yılmaz", brans: "Matematik" }])),
    http.get("/api/siniflar", () =>
      HttpResponse.json([
        { id: "s-9a", ad: "9-A", seviye: 9, sube_grubu_id: "g-fen" },
        { id: "s-9b", ad: "9-B", seviye: 9, sube_grubu_id: null },
      ]),
    ),
    http.get("/api/sube-gruplari", () => HttpResponse.json([{ id: "g-fen", ad: "9 Fen", seviye: 9 }])),
    http.get("/api/dersler", () => HttpResponse.json([{ id: "d-mat", ad: "Matematik", kisa_ad: "MAT" }])),
    http.get("/api/ders-programi/kurallar/:tur/ozel/etki", ({ request, params }) => {
      const sorgu = new URL(request.url).searchParams.toString();
      istekler.push({ yontem: "GET", yol: `${String(params.tur)}/etki`, sorgu });
      // 9-A · Matematik (6): gruptaki Matematik (5) ve Matematik (4) ayarlarının yerine geçer.
      return HttpResponse.json({ mevcut: null, ezdikleri: [MAT_GRUP, MAT], ezenler: [] });
    }),
    http.put("/api/ders-programi/kurallar/:tur/ozel", async ({ request, params }) => {
      const govde = (await request.json()) as { kapsam: Record<string, string>; parametreler: Record<string, number | number[]> };
      istekler.push({ yontem: "PUT", yol: String(params.tur), govde });
      const yeni = { kapsam: { ders_id: null, sinif_id: null, sube_grubu_id: null, ogretmen_id: null, ...govde.kapsam },
        ad: "9-A · Matematik", parametreler: govde.parametreler };
      kurallar = kurallar.map((k) => (k.tur === params.tur ? { ...k, ozel_ayarlar: [...k.ozel_ayarlar, yeni] } : k));
      return HttpResponse.json(kurallar.find((k) => k.tur === params.tur));
    }),
    http.delete("/api/ders-programi/kurallar/:tur/ozel", ({ request, params }) => {
      istekler.push({ yontem: "DELETE", yol: String(params.tur), sorgu: new URL(request.url).searchParams.toString() });
      kurallar = kurallar.map((k) => (k.tur === params.tur ? { ...k, ozel_ayarlar: [] } : k));
      return HttpResponse.json(kurallar.find((k) => k.tur === params.tur));
    }),
  );
  return istekler;
}

async function formuAc() {
  const istekler = api();
  const ciz = uygulamayiCiz("/okul");
  const bolum = await screen.findByRole("region", { name: "Özel ayarlar" });
  await ciz.kullanici.click(within(bolum).getByRole("button", { name: "Özel ayar ekle" }));
  const form = within(bolum).getByRole("form", { name: "Özel ayar ekle" });
  return { ...ciz, istekler, form: within(form) };
}

const secenekler = (kutu: HTMLElement) => within(kutu).getAllByRole("option").map((o) => o.textContent);

describe("özel ayar ekle", () => {
  it("yalnızca kuralın geçerli kapsamları: dağılım şekli ders ister, öğretmen sınırı yalnızca öğretmene", () => {
    expect(gecerliKapsamlar(kural(N)).map((s) => s.anahtar)).toEqual(["ders", "sube", "sube_grubu", "ders_sube", "ders_grup"]);
    expect(gecerliKapsamlar(kural("blok_deseni")).map((s) => s.anahtar)).toEqual(["ders", "ders_sube", "ders_grup"]);
    expect(gecerliKapsamlar(kural("ogretmen_gunluk_siniri")).map((s) => s.anahtar)).toEqual(["ogretmen"]);
    expect(gecerliKapsamlar(kural("sinif_boslugu"))).toEqual([]);
  });

  it("ders + şubeye özel günlük sınır: etkisini söyler ve kaydeder", async () => {
    const { kullanici, form, istekler } = await formuAc();
    const kuralKutusu = form.getByRole("combobox", { name: "Kural" });
    // Kapsamı olmayan kurallar (sınıf boşluğu gibi) listelenmez.
    expect(secenekler(kuralKutusu)).toEqual([
      "Seçin", "Aynı dersin günlük sınırı", "Öğretmenin günlük ders sınırı", "Dağılım şekli (blok dersler)", "Öğretmene boş gün",
    ]);
    await kullanici.selectOptions(kuralKutusu, N);
    const nerede = form.getByRole("combobox", { name: "Nerede geçerli" });
    expect(secenekler(nerede)).toEqual([
      "Seçin", "Bir ders (bütün şubelerde)", "Bir şube (bütün dersleri)", "Bir şube grubu (bütün dersleri)",
      "Bir şubede bir ders", "Bir şube grubunda bir ders",
    ]);
    await kullanici.selectOptions(nerede, "ders_sube");
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Şube" }), "s-9a");
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Ders" }), "d-mat");

    const etki = await form.findByRole("status", { name: "Bu ayarın etkisi" });
    expect(etki).toHaveTextContent("9-A · Matematik için okul geneli: 2 yerine bu değer geçerli olur.");
    expect(etki).toHaveTextContent(
      "Daha genel olan şu özel ayarların yerine geçer: 9 Fen grubu · Matematik (günde en çok 3 saat), Matematik (bir şubeye günde en çok 2 saat konur).",
    );
    expect(istekler).toContainEqual({ yontem: "GET", yol: `${N}/etki`, sorgu: "ders_id=d-mat&sinif_id=s-9a" });

    const deger = form.getByRole("spinbutton", { name: "Aynı ders günde en çok kaç saat" });
    expect(deger).toHaveValue(2); // okul değeriyle başlar
    await kullanici.clear(deger);
    await kullanici.type(deger, "3");
    await kullanici.click(form.getByRole("button", { name: "Özel ayarı kaydet" }));
    expect(await screen.findByText("Özel ayar kaydedildi: 9-A · Matematik, günde en çok 3 saat.")).toBeInTheDocument();
    expect(istekler.filter((i) => i.yontem === "PUT")).toEqual([
      { yontem: "PUT", yol: N, govde: { kapsam: { sinif_id: "s-9a", ders_id: "d-mat" }, parametreler: { n: 3 } } },
    ]);
    expect(await screen.findByText("9-A · Matematik")).toBeInTheDocument();
  });

  it("dağılım şekli: geçersiz yazım gönderilmez, geçerlisi bloklar olarak gider", async () => {
    const { kullanici, form, istekler } = await formuAc();
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Kural" }), "blok_deseni");
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Nerede geçerli" }), "ders_grup");
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Şube grubu" }), "g-fen");
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Ders" }), "d-mat");
    const alan = form.getByRole("textbox", { name: /Dağılım şekli/ });
    await kullanici.type(alan, "3-3");
    await kullanici.click(form.getByRole("button", { name: "Özel ayarı kaydet" }));
    expect(form.getByText(/2\+2\+1 biçiminde/)).toBeInTheDocument();
    expect(istekler.filter((i) => i.yontem === "PUT")).toEqual([]);
    await kullanici.clear(alan);
    await kullanici.type(alan, "3+3");
    await kullanici.click(form.getByRole("button", { name: "Özel ayarı kaydet" }));
    await screen.findByText(/Özel ayar kaydedildi/);
    expect(istekler.filter((i) => i.yontem === "PUT")).toEqual([
      { yontem: "PUT", yol: "blok_deseni", govde: { kapsam: { sube_grubu_id: "g-fen", ders_id: "d-mat" }, parametreler: { desen: [3, 3] } } },
    ]);
  });

  it("öğretmen kuralı yalnızca öğretmen sorar; aralık dışı değer gönderilmez", async () => {
    const { kullanici, form, istekler } = await formuAc();
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Kural" }), "ogretmen_gunluk_siniri");
    expect(secenekler(form.getByRole("combobox", { name: "Nerede geçerli" }))).toEqual(["Seçin", "Bir öğretmen"]);
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Nerede geçerli" }), "ogretmen");
    await kullanici.selectOptions(form.getByRole("combobox", { name: "Öğretmen" }), "o-ayse");
    const deger = form.getByRole("spinbutton", { name: "Günde en çok kaç saat derse girer" });
    await kullanici.clear(deger);
    await kullanici.type(deger, "99");
    await kullanici.click(form.getByRole("button", { name: "Özel ayarı kaydet" }));
    expect(form.getByText(/1 ile \d+ arasında bir sayı girin/)).toBeInTheDocument();
    expect(istekler.filter((i) => i.yontem === "PUT")).toEqual([]);
  });

  it("gruba özel ayar kaldırılırken grubun kimliği de gönderilir", async () => {
    const istekler = api();
    const { kullanici } = uygulamayiCiz("/okul");
    await kullanici.click(await screen.findByRole("button", { name: /9 Fen grubu · Matematik: .* özel ayarını kaldır/ }));
    await screen.findByText(/özel ayar kaldırıldı/);
    expect(istekler.filter((i) => i.yontem === "DELETE")).toEqual([{ yontem: "DELETE", yol: N, sorgu: "ders_id=d-mat&sube_grubu_id=g-fen" }]);
  });
});
