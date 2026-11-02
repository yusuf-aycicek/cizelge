/** Uygulamanın tamamı: çerçeve, menü, ana sayfa (sahte API ile). */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { BAGLANTI_HATASI } from "./api/hata";
import { MENU } from "./cerceve/menu";
import { oturumYok, sunucu } from "./test/sunucu";
import { uygulamayiCiz } from "./test/yardimcilar";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { SEKME_BASLIGI, UYGULAMA_ACIKLAMASI, UYGULAMA_ADI } from "./urun";

describe("uygulamanın adı", () => {
  it("adı Çizelge: üst çubukta, giriş sayfasında ve sekme başlığında", async () => {
    expect(UYGULAMA_ADI).toBe("Çizelge");
    expect(SEKME_BASLIGI).toBe("Çizelge – Okul Ders Programı Oluşturma Sistemi");
    expect(readFileSync(resolve("index.html"), "utf-8")).toContain(`<title>${SEKME_BASLIGI}</title>`);

    uygulamayiCiz("/");
    expect(await screen.findByRole("banner")).toHaveTextContent(UYGULAMA_ADI);
  });

  it("giriş sayfasında ad ve açıklaması", async () => {
    oturumYok();
    uygulamayiCiz("/giris");
    expect(await screen.findByText(UYGULAMA_ADI)).toBeInTheDocument();
    expect(screen.getByText(UYGULAMA_ACIKLAMASI)).toBeInTheDocument();
  });
});

describe("ana sayfa ve sistem durumu", () => {
  it("API çalışıyorsa durum iyi görünür", async () => {
    uygulamayiCiz("/");
    expect(await screen.findByRole("heading", { level: 1, name: "Hoş geldiniz" })).toBeInTheDocument();
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
    const menu = await screen.findByRole("navigation", { name: "Ana menü" });
    expect(within(menu).getAllByRole("link").map((b) => b.textContent)).toEqual(MENU.map((m) => m.ad));
    expect(within(menu).getByRole("link", { name: "Öğretmenler" })).toHaveAttribute("aria-current", "page");
    expect(within(menu).getByRole("link", { name: "Ana sayfa" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("heading", { level: 1, name: "Öğretmenler" })).toBeInTheDocument();
  });

  it("menü bağlantısıyla sayfa değişir", async () => {
    const { kullanici } = uygulamayiCiz("/");
    await kullanici.click(await screen.findByRole("link", { name: "Sınıflar" }));
    expect(screen.getByRole("heading", { level: 1, name: "Sınıflar" })).toBeInTheDocument();
  });

  it("ilk Tab 'İçeriğe geç' bağlantısına gider", async () => {
    const { kullanici } = uygulamayiCiz("/");
    await screen.findByRole("main");
    await kullanici.tab();
    expect(screen.getByRole("link", { name: "İçeriğe geç" })).toHaveFocus();
    expect(screen.getByRole("main")).toHaveAttribute("id", "icerik");
  });

  it("menü düğmesi açık/kapalı durumunu bildirir, sayfa değişince menü kapanır", async () => {
    const { kullanici } = uygulamayiCiz("/");
    const dugme = await screen.findByRole("button", { name: /Menü/ });
    expect(dugme).toHaveAttribute("aria-expanded", "false");
    await kullanici.click(dugme);
    expect(dugme).toHaveAttribute("aria-expanded", "true");
    await kullanici.click(screen.getByRole("link", { name: "Dersler" }));
    expect(dugme).toHaveAttribute("aria-expanded", "false");
  });

  it("menü OKUL, DAĞITIM ve PROGRAM bölümlerine ayrılır; sayfa başlığının etiketi bölümdür", async () => {
    uygulamayiCiz("/ders-dagilimi");
    const menu = await screen.findByRole("navigation", { name: "Ana menü" });
    const okul = within(menu).getByRole("list", { name: "OKUL" });
    expect(within(okul).getAllByRole("link").map((b) => b.textContent)).toEqual(["Okul ayarları", "Öğretmenler", "Sınıflar", "Dersler", "Excel'den aktar"]);
    expect(within(within(menu).getByRole("list", { name: "DAĞITIM" })).getAllByRole("link")).toHaveLength(2);
    expect(within(within(menu).getByRole("list", { name: "PROGRAM" })).getAllByRole("link")).toHaveLength(2);
    // Ana sayfa en üstte, Kullanıcılar en altta
    const baglantilar = within(menu).getAllByRole("link");
    expect(baglantilar[0]).toHaveTextContent("Ana sayfa");
    expect(baglantilar[baglantilar.length - 1]).toHaveTextContent("Kullanıcılar");
    const baslik = await screen.findByRole("heading", { level: 1, name: "Ders dağılımı" });
    expect(baslik.previousElementSibling).toHaveTextContent("DAĞITIM");
  });

  it("hesap menüsü baş harfli düğmeyle açılır, Esc kapatır ve odağı düğmeye geri verir", async () => {
    const { kullanici } = uygulamayiCiz("/");
    const avatar = await screen.findByRole("button", { name: "Hesap: Ayşe Yılmaz" });
    expect(avatar).toHaveTextContent("AY");
    expect(screen.queryByRole("link", { name: "Hesabım" })).not.toBeInTheDocument();
    await kullanici.click(avatar);
    expect(avatar).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Hesabım" })).toHaveFocus();
    expect(screen.getByRole("button", { name: "Çıkış" })).toBeInTheDocument();
    await kullanici.keyboard("{Escape}");
    expect(avatar).toHaveAttribute("aria-expanded", "false");
    expect(avatar).toHaveFocus();
    expect(screen.queryByRole("link", { name: "Hesabım" })).not.toBeInTheDocument();
  });

  it("bilinmeyen adres anlaşılır sayfa gösterir", async () => {
    uygulamayiCiz("/yok-boyle-sayfa");
    expect(await screen.findByRole("heading", { level: 1, name: "Sayfa bulunamadı" })).toBeInTheDocument();
  });
});
