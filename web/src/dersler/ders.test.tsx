/** Ders renkleri: çip, renk seçici, API paletiyle tutarlılık. */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { ORNEK_KURALLAR, sunucu } from "../test/sunucu";
import { uygulamayiCiz } from "../test/yardimcilar";
import { DersCipi } from "./DersCipi";

describe("ders çipi", () => {
  it("dersin rengini CSS değişkeniyle zemine verir, adı yazar", () => {
    render(<DersCipi ad="Matematik" renk="#1d4ed8" />);
    const cip = screen.getByText("Matematik");
    expect(cip.style.getPropertyValue("--ders-rengi")).toBe("#1d4ed8");
  });

  it("rengi yoksa nötr çip", () => {
    render(<DersCipi ad="Fizik" />);
    expect(screen.getByText("Fizik").style.getPropertyValue("--ders-rengi")).toBe("");
  });

  it("çip yazısının rengi, API'nin kontrastı denetlediği renkle aynı", () => {
    // API: her palet rengi CIP_METNI ile en az 4.5:1 (api/tests/test_ders_renkleri.py). Arayüz
    // çipte --renk-cip-metin kullanır. İkisi ayrılırsa kontrast güvencesi boşa çıkar.
    const belirtecler = readFileSync(resolve("src/stil/belirtecler.css"), "utf-8");
    const api = readFileSync(resolve("../api/src/okulapi/cekirdek/ders_renkleri.py"), "utf-8");
    const arayuzde = belirtecler.match(/--renk-cip-metin:\s*(#[0-9a-f]{6})/)?.[1];
    const apide = api.match(/CIP_METNI = "(#[0-9a-f]{6})"/)?.[1];
    expect(arayuzde).toBeDefined();
    expect(arayuzde).toBe(apide);
  });
});

describe("dersler sayfasında renk", () => {
  it("ders adı çip olarak görünür; renk seçilince hemen kaydedilir", async () => {
    let ders = { id: "d1", ad: "Matematik", kisa_ad: "MAT", renk: "#1d4ed8" };
    const govdeler: unknown[] = [];
    sunucu.use(
      http.get("/api/dersler", () => HttpResponse.json([ders])),
      http.patch("/api/dersler/:id", async ({ request }) => {
        const govde = (await request.json()) as { renk: string };
        govdeler.push(govde);
        ders = { ...ders, ...govde };
        return HttpResponse.json(ders);
      }),
    );
    const { kullanici } = uygulamayiCiz("/dersler");
    const tablo = await screen.findByRole("table", { name: "Dersler" });
    expect(within(tablo).getByText("Matematik").style.getPropertyValue("--ders-rengi")).toBe("#1d4ed8");

    const secici = await within(tablo).findByText("Lacivert");
    await kullanici.click(secici);
    const palet = within(tablo).getByRole("radiogroup", { name: "Matematik dersinin rengi" });
    expect(within(palet).getByRole("radio", { name: "Lacivert" })).toHaveAttribute("aria-checked", "true");
    await kullanici.click(within(palet).getByRole("radio", { name: "Kiremit" }));

    await waitFor(() => expect(govdeler).toEqual([{ renk: "#c2410c" }]));
    expect(await screen.findByText("Matematik dersinin rengi değiştirildi.")).toBeInTheDocument();
    await waitFor(() => expect(within(tablo).getByText("Matematik").style.getPropertyValue("--ders-rengi")).toBe("#c2410c"));
  });

  it("aynı rengi seçmek istek göndermez", async () => {
    const govdeler: unknown[] = [];
    sunucu.use(
      http.get("/api/dersler", () => HttpResponse.json([{ id: "d1", ad: "Fizik", kisa_ad: "FİZ", renk: "#c2410c" }])),
      http.patch("/api/dersler/:id", async ({ request }) => {
        govdeler.push(await request.json());
        return HttpResponse.json({});
      }),
    );
    const { kullanici } = uygulamayiCiz("/dersler");
    await kullanici.click(await screen.findByText("Kiremit"));
    await kullanici.click(screen.getByRole("radio", { name: "Kiremit" }));
    expect(govdeler).toEqual([]);
  });
});

describe("renk tekrar edince işaret", () => {
  it("aynı rengi paylaşan derslerden ilki işaretsiz, sonrakiler sırayla", async () => {
    const { dersIsaretleri, isaretKarakteri } = await import("./isaret");
    const isaretler = dersIsaretleri([
      { id: "d1", renk: "#1d4ed8" },
      { id: "d2", renk: "#c2410c" },
      { id: "d3", renk: "#1d4ed8" },
      { id: "d4", renk: "#1d4ed8" },
    ]);
    expect([...isaretler.entries()]).toEqual([["d1", 0], ["d2", 0], ["d3", 1], ["d4", 2]]);
    expect([1, 2, 3, 5, 6].map(isaretKarakteri)).toEqual(["◆", "▲", "●", "★", "7"]);
  });

  it("çipte işaret görünür; ekran okuyucudan gizlidir (aria-hidden)", () => {
    render(<DersCipi ad="Fizik" renk="#1d4ed8" isaret={1} />);
    const cip = screen.getByText("Fizik");
    const isaret = cip.querySelector("[aria-hidden='true']");
    expect(isaret).toHaveTextContent("◆");
    expect(cip).toHaveTextContent("◆Fizik");
  });

  it("işaretsiz çipte işaret yok", () => {
    render(<DersCipi ad="Kimya" renk="#15803d" />);
    expect(screen.getByText("Kimya").querySelector("[aria-hidden='true']")).toBeNull();
  });
});

describe("dersler sayfasında dağılım şekli (K4)", () => {
  type Sekil = { atama_id: string; ders_id: string; sinif_id: string; sinif_adi: string; haftalik_saat: number;
    desen: number[] | null; metin: string; kaynak: string; dusen_oneri: string | null; nedenler: string[]; sorunlar: string[] };
  const sekil = (s: Partial<Sekil>): Sekil => ({
    atama_id: "a1", ders_id: "d1", sinif_id: "s1", sinif_adi: "9-A", haftalik_saat: 5, desen: [2, 2, 1], metin: "2+2+1",
    kaynak: "okul", dusen_oneri: null, nedenler: [], sorunlar: [], ...s,
  });

  function kur(sekiller: Sekil[], ozel: number[] | null = null) {
    const istekler: { yontem: string; govde?: unknown; adres: string }[] = [];
    sunucu.use(
      http.get("/api/dersler", () => HttpResponse.json([{ id: "d1", ad: "Matematik", kisa_ad: "MAT", renk: "#1d4ed8" }])),
      http.get("/api/ders-programi/dagilim-sekilleri", () => HttpResponse.json(sekiller)),
      http.get("/api/ders-programi/kurallar", () => HttpResponse.json(ORNEK_KURALLAR.map((k) =>
        k.tur === "blok_deseni" && ozel
          ? { ...k, ozel_ayarlar: [{ kapsam: { ders_id: "d1", sinif_id: null, ogretmen_id: null }, ad: "Matematik", parametreler: { desen: ozel } }] }
          : k))),
      http.put("/api/ders-programi/kurallar/:tur/ozel", async ({ request }) => {
        istekler.push({ yontem: "PUT", govde: await request.json(), adres: request.url });
        return HttpResponse.json(ORNEK_KURALLAR[0]);
      }),
      http.delete("/api/ders-programi/kurallar/:tur/ozel", ({ request }) => {
        istekler.push({ yontem: "DELETE", adres: request.url });
        return HttpResponse.json(ORNEK_KURALLAR[0]);
      }),
    );
    return istekler;
  }

  it("okul önerisi görünür; hazır şekil seçilince derse özel kaydedilir", async () => {
    const istekler = kur([sekil({})]);
    const { kullanici } = uygulamayiCiz("/dersler");
    const secim = await screen.findByRole("combobox", { name: "Matematik dersinin dağılım şekli" });
    expect(secim).toHaveDisplayValue("Okul önerisi (2+2+1)");
    // 5 saat, günlük sınır 2: hazır seçenekler 2'lik bloklarla.
    expect(within(secim).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Okul önerisi (2+2+1)", "Blok yok", "2+2+1", "2+1+1+1", "1+1+1+1+1", "Başka bir şekil…"]);
    await kullanici.selectOptions(secim, "2+1+1+1");
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]!.govde).toEqual({ kapsam: { ders_id: "d1" }, parametreler: { desen: [2, 1, 1, 1] } });
    expect(await screen.findByText("Matematik: dağılım şekli 2+1+1+1.")).toBeInTheDocument();
  });

  it("özel şekil 'özel' rozetiyle; okul önerisine dönmek özel ayarı siler", async () => {
    const istekler = kur([sekil({ desen: [2, 1, 1, 1], metin: "2+1+1+1", kaynak: "ders" })], [2, 1, 1, 1]);
    const { kullanici } = uygulamayiCiz("/dersler");
    const secim = await screen.findByRole("combobox", { name: "Matematik dersinin dağılım şekli" });
    await waitFor(() => expect(secim).toHaveDisplayValue("2+1+1+1"));
    expect(screen.getByText("özel")).toBeInTheDocument();
    await kullanici.selectOptions(secim, "");
    await waitFor(() => expect(istekler.map((i) => i.yontem)).toEqual(["DELETE"]));
    expect(istekler[0]!.adres).toContain("ders_id=d1");
  });

  it("başka bir şekil elle yazılır; geçersiz yazım sunucuya gitmez", async () => {
    const istekler = kur([sekil({})]);
    const { kullanici } = uygulamayiCiz("/dersler");
    await kullanici.selectOptions(await screen.findByRole("combobox", { name: "Matematik dersinin dağılım şekli" }), "baska");
    const kutu = screen.getByRole("textbox", { name: /dağılım şekli \(ör\. 2\+2\+1\)/ });
    await kullanici.type(kutu, "2,2");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    expect(screen.getByText("Şekli 2+2+1 gibi yazın; her blok 1-8 saat.")).toHaveAttribute("role", "alert");
    expect(istekler).toEqual([]);
    await kullanici.clear(kutu);
    await kullanici.type(kutu, "1+2+2");
    await kullanici.click(screen.getByRole("button", { name: "Kaydet" }));
    await waitFor(() => expect(istekler).toHaveLength(1));
    expect(istekler[0]!.govde).toEqual({ kapsam: { ders_id: "d1" }, parametreler: { desen: [2, 2, 1] } });
  });

  it("uygulanamayan özel şekil ve düşen öneri nedeniyle görünür", async () => {
    kur([
      sekil({ kaynak: "ders", sorunlar: ["öğretmenin müsaitliğine sığmıyor"] }),
      sekil({ atama_id: "a2", sinif_id: "s2", sinif_adi: "9-B", desen: null, metin: "blok yok", kaynak: "yok",
        dusen_oneri: "2+2+1", nedenler: ["blok sayısı gün sayısından fazla"] }),
    ], [2, 2, 1]);
    uygulamayiCiz("/dersler");
    expect(await screen.findByText("9-A: öğretmenin müsaitliğine sığmıyor")).toBeInTheDocument();
    expect(screen.getByText("Öneri uygulanamadı, blok yok: 9-B (blok sayısı gün sayısından fazla).")).toBeInTheDocument();
  });

  it("henüz atanmamış ders", async () => {
    kur([]);
    uygulamayiCiz("/dersler");
    expect(await screen.findByText("Henüz bir şubeye atanmadı.")).toBeInTheDocument();
  });
});
