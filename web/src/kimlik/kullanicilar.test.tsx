/** Kullanıcılar sayfası (5.6): liste, yardımcı ekleme, parola, rol, silme ve son müdür kuralı. */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { BEN_ORNEK, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";

type K = { id: string; ad: string; email: string; rol: string };

const AYSE: K = { ...BEN_ORNEK.kullanici };
const MEHMET: K = { id: "k2", ad: "Mehmet Kaya", email: "mehmet@okul.test", rol: "mudur_yardimcisi" };

function api(kullanicilar: K[]) {
  const istekler: { yontem: string; yol: string; govde?: unknown }[] = [];
  sunucu.use(
    http.get("/api/kullanicilar", () => HttpResponse.json(kullanicilar)),
    http.post("/api/kullanicilar", async ({ request }) => {
      const govde = (await request.json()) as { ad: string; email: string; sifre: string };
      istekler.push({ yontem: "POST", yol: "kullanicilar", govde });
      if (govde.email === "mehmet@okul.test")
        return HttpResponse.json({ detail: "Bu e-posta adresi başka bir hesapta kullanılıyor" }, { status: 409 });
      const yeni = { id: "k3", ad: govde.ad, email: govde.email, rol: "mudur_yardimcisi" };
      kullanicilar = [...kullanicilar, yeni];
      return HttpResponse.json(yeni, { status: 201 });
    }),
    http.put("/api/kullanicilar/:id/rol", async ({ request, params }) => {
      const govde = (await request.json()) as { rol: string };
      istekler.push({ yontem: "PUT", yol: `${params.id}/rol`, govde });
      kullanicilar = kullanicilar.map((k) => (k.id === params.id ? { ...k, rol: govde.rol } : k));
      return HttpResponse.json(kullanicilar.find((k) => k.id === params.id));
    }),
    http.put("/api/kullanicilar/:id/sifre", async ({ request, params }) => {
      istekler.push({ yontem: "PUT", yol: `${params.id}/sifre`, govde: await request.json() });
      return new HttpResponse(null, { status: 204 });
    }),
    http.delete("/api/kullanicilar/:id", ({ params }) => {
      istekler.push({ yontem: "DELETE", yol: String(params.id) });
      kullanicilar = kullanicilar.filter((k) => k.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return istekler;
}

describe("kullanıcılar sayfası", () => {
  it("listeyi gösterir; tek müdürün rolü düşürülemez ve silinemez, nedeni yazar", async () => {
    const istekler = api([MEHMET, AYSE]);
    uygulamayiCiz("/kullanicilar");
    const tablo = await screen.findByRole("table", { name: "Yöneticiler" });
    const satirlar = within(tablo).getAllByRole("row").slice(1);
    // Müdür önce, sonra yardımcılar; kendi satırında "(siz)".
    expect(satirlar.map((s) => within(s).getAllByRole("cell")[0]?.textContent)).toEqual(["Ayşe Yılmaz (siz)", "Mehmet Kaya"]);
    expect(screen.getByRole("button", { name: "Ayşe Yılmaz: yardımcı yap" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Ayşe Yılmaz: sil" })).toBeDisabled();
    expect(screen.getByText(/Okulda tek müdür var: Ayşe Yılmaz\. .*Önce başka bir kullanıcıyı müdür yapın\./)).toBeInTheDocument();
    // Kendi parolası buradan değil, Hesabım'dan.
    expect(screen.queryByRole("button", { name: "Ayşe Yılmaz: parolasını yeniden belirle" })).toBeNull();
    expect(screen.getByRole("button", { name: "Mehmet Kaya: sil" })).toBeEnabled();
    expect(istekler).toEqual([]);
  });

  it("yardımcıyı müdür yapınca son müdür kuralı kalkar", async () => {
    const istekler = api([AYSE, MEHMET]);
    const { kullanici } = uygulamayiCiz("/kullanicilar");
    await kullanici.click(await screen.findByRole("button", { name: "Mehmet Kaya: müdür yap" }));
    expect(await screen.findByText("Mehmet Kaya artık müdür.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "PUT", yol: "k2/rol", govde: { rol: "mudur" } }]);
    expect(await screen.findByRole("button", { name: "Ayşe Yılmaz: yardımcı yap" })).toBeEnabled();
    expect(screen.queryByText(/Okulda tek müdür var/)).toBeNull();
  });

  it("sunucunun son müdür mesajı (aynı anda başka değişiklik) bildirimde görünür", async () => {
    api([AYSE, { ...MEHMET, rol: "mudur" }]);
    sunucu.use(
      http.put("/api/kullanicilar/:id/rol", () =>
        HttpResponse.json({ detail: "Okulun son müdürü rolü düşürülemez. Önce başka bir kullanıcıyı müdür yapın." }, { status: 409 }),
      ),
    );
    const { kullanici } = uygulamayiCiz("/kullanicilar");
    await kullanici.click(await screen.findByRole("button", { name: "Mehmet Kaya: yardımcı yap" }));
    expect(await screen.findByText(/Okulun son müdürü rolü düşürülemez/)).toBeInTheDocument();
  });

  it("müdür yardımcısı ekler; istemci denetimi ve sunucunun e-posta hatası alanın altında", async () => {
    const istekler = api([AYSE, MEHMET]);
    const { kullanici } = uygulamayiCiz("/kullanicilar");
    const bolum = await screen.findByRole("region", { name: "Müdür yardımcısı ekle" });
    await kullanici.click(within(bolum).getByRole("button", { name: "Müdür yardımcısı ekle" }));
    expect(within(bolum).getByRole("textbox", { name: /Ad soyad/ })).toHaveAccessibleDescription(/Adını yazın/);
    expect(istekler).toEqual([]);

    await kullanici.type(within(bolum).getByRole("textbox", { name: /Ad soyad/ }), "Zeynep Demir");
    await kullanici.type(within(bolum).getByRole("textbox", { name: /E-posta/ }), "mehmet@okul.test");
    await kullanici.type(within(bolum).getByLabelText(/İlk parola/), "uzun-bir-parola-1");
    await kullanici.click(within(bolum).getByRole("button", { name: "Müdür yardımcısı ekle" }));
    expect(await within(bolum).findByText("Bu e-posta adresi başka bir hesapta kullanılıyor")).toBeInTheDocument();

    const eposta = within(bolum).getByRole("textbox", { name: /E-posta/ });
    await kullanici.clear(eposta);
    await kullanici.type(eposta, "zeynep@okul.test");
    await kullanici.click(within(bolum).getByRole("button", { name: "Müdür yardımcısı ekle" }));
    expect(await screen.findByText(/Zeynep Demir müdür yardımcısı olarak eklendi/)).toBeInTheDocument();
    expect(await screen.findByRole("cell", { name: "zeynep@okul.test" })).toBeInTheDocument();
    expect(istekler.at(-1)).toEqual({
      yontem: "POST",
      yol: "kullanicilar",
      govde: { ad: "Zeynep Demir", email: "zeynep@okul.test", sifre: "uzun-bir-parola-1" },
    });
  });

  it("parolayı yeniden belirler: eşleşmeyen tekrar gönderilmez", async () => {
    const istekler = api([AYSE, MEHMET]);
    const { kullanici } = uygulamayiCiz("/kullanicilar");
    await kullanici.click(await screen.findByRole("button", { name: "Mehmet Kaya: parolasını yeniden belirle" }));
    const pencere = screen.getByRole("dialog", { name: "Mehmet Kaya için yeni parola" });
    expect(pencere).toHaveTextContent("Açık oturumları kapanacak");
    await kullanici.type(within(pencere).getByLabelText("Yeni parola"), "yeni-uzun-parola-1");
    await kullanici.type(within(pencere).getByLabelText("Yeni parola (tekrar)"), "baska");
    await kullanici.click(within(pencere).getByRole("button", { name: "Parolayı belirle" }));
    expect(within(pencere).getByText("Parolalar eşleşmiyor")).toBeInTheDocument();
    expect(istekler).toEqual([]);
    await kullanici.clear(within(pencere).getByLabelText("Yeni parola (tekrar)"));
    await kullanici.type(within(pencere).getByLabelText("Yeni parola (tekrar)"), "yeni-uzun-parola-1");
    await kullanici.click(within(pencere).getByRole("button", { name: "Parolayı belirle" }));
    expect(await screen.findByText(/Mehmet Kaya için yeni parola belirlendi/)).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "PUT", yol: "k2/sifre", govde: { sifre: "yeni-uzun-parola-1" } }]);
  });

  it("onaydan sonra siler", async () => {
    const istekler = api([AYSE, MEHMET]);
    const { kullanici } = uygulamayiCiz("/kullanicilar");
    await kullanici.click(await screen.findByRole("button", { name: "Mehmet Kaya: sil" }));
    const pencere = screen.getByRole("dialog", { name: "Mehmet Kaya silinsin mi?" });
    await kullanici.click(within(pencere).getByRole("button", { name: "Sil" }));
    expect(await screen.findByText("Mehmet Kaya silindi.")).toBeInTheDocument();
    expect(istekler).toEqual([{ yontem: "DELETE", yol: "k2" }]);
  });

  it("yardımcı listeyi düğmeler ve ekleme formu olmadan görür", async () => {
    api([{ ...AYSE, id: "k9", ad: "Ali Veli", email: "ali@okul.test", rol: "mudur" }, { ...AYSE, rol: "mudur_yardimcisi" }]);
    sunucu.use(http.get("/api/ben", () => HttpResponse.json({ ...BEN_ORNEK, kullanici: { ...AYSE, rol: "mudur_yardimcisi" } })));
    uygulamayiCiz("/kullanicilar");
    await screen.findByRole("table", { name: "Yöneticiler" });
    expect(screen.getByText(/yalnızca okul müdürü yapabilir/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /sil$/ })).toBeNull();
    expect(screen.queryByRole("region", { name: "Müdür yardımcısı ekle" })).toBeNull();
    expect(screen.queryByText(/Okulda tek müdür var/)).toBeNull();
  });
});
