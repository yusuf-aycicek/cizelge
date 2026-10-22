/** Ders renkleri: çip, renk seçici, API paletiyle tutarlılık. */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { sunucu } from "../test/sunucu";
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
