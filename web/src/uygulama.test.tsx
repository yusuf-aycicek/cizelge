/** Uygulamanın tamamı: çerçeve, menü, ana sayfa (sahte API ile). */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { BAGLANTI_HATASI } from "./api/hata";
import { MENU } from "./cerceve/Cerceve";
import { sunucu } from "./test/sunucu";
import { uygulamayiCiz } from "./test/yardimcilar";

describe("ana sayfa ve sistem durumu", () => {
  it("API çalışıyorsa durum iyi görünür", async () => {
    uygulamayiCiz("/");
    expect(screen.getByRole("heading", { level: 1, name: "Hoş geldiniz" })).toBeInTheDocument();
    expect(await screen.findByText("✓ Çalışıyor")).toBeInTheDocument();
    expect(screen.getByText("✓ Bağlı")).toBeInTheDocument();
  });

  it("veritabanı yoksa sunucunun mesajı, yeniden denenince düzelir", async () => {
    sunucu.use(http.get("/api/saglik", () => HttpResponse.json({ detail: "Veritabanına ulaşılamıyor" }, { status: 503 }), { once: true }));
    const { kullanici } = uygulamayiCiz("/");
    const metin = await screen.findByText("Veritabanına ulaşılamıyor");
    const uyari = metin.closest<HTMLElement>('[role="alert"]');
    expect(uyari).not.toBeNull();
    await kullanici.click(within(uyari!).getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByText("✓ Çalışıyor")).toBeInTheDocument();
  });

  it("sunucuya hiç ulaşılamazsa anlaşılır bağlantı mesajı", async () => {
    sunucu.use(http.get("/api/saglik", () => HttpResponse.error()));
    uygulamayiCiz("/");
    expect(await screen.findByText(BAGLANTI_HATASI)).toBeInTheDocument();
  });
});

describe("çerçeve", () => {
  it("menüde bütün sayfalar var, geçerli sayfa işaretli", async () => {
    uygulamayiCiz("/ogretmenler");
    const menu = screen.getByRole("navigation", { name: "Ana menü" });
    expect(within(menu).getAllByRole("link").map((b) => b.textContent)).toEqual(MENU.map((m) => m.ad));
    expect(within(menu).getByRole("link", { name: "Öğretmenler" })).toHaveAttribute("aria-current", "page");
    expect(within(menu).getByRole("link", { name: "Ana sayfa" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("heading", { level: 1, name: "Öğretmenler" })).toBeInTheDocument();
  });

  it("menü bağlantısıyla sayfa değişir", async () => {
    const { kullanici } = uygulamayiCiz("/");
    await kullanici.click(screen.getByRole("link", { name: "Sınıflar" }));
    expect(screen.getByRole("heading", { level: 1, name: "Sınıflar" })).toBeInTheDocument();
  });

  it("ilk Tab 'İçeriğe geç' bağlantısına gider", async () => {
    const { kullanici } = uygulamayiCiz("/");
    await kullanici.tab();
    expect(screen.getByRole("link", { name: "İçeriğe geç" })).toHaveFocus();
    expect(screen.getByRole("main")).toHaveAttribute("id", "icerik");
  });

  it("menü düğmesi açık/kapalı durumunu bildirir, sayfa değişince menü kapanır", async () => {
    const { kullanici } = uygulamayiCiz("/");
    const dugme = screen.getByRole("button", { name: /Menü/ });
    expect(dugme).toHaveAttribute("aria-expanded", "false");
    await kullanici.click(dugme);
    expect(dugme).toHaveAttribute("aria-expanded", "true");
    await kullanici.click(screen.getByRole("link", { name: "Dersler" }));
    expect(dugme).toHaveAttribute("aria-expanded", "false");
  });

  it("bilinmeyen adres anlaşılır sayfa gösterir", () => {
    uygulamayiCiz("/yok-boyle-sayfa");
    expect(screen.getByRole("heading", { level: 1, name: "Sayfa bulunamadı" })).toBeInTheDocument();
  });
});
