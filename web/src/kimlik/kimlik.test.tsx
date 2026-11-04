/**
 * Kimlik akışları: giriş, kayıt, çıkış, korumalı sayfalar, oturum süresinin dolması, hesabım.
 * Sahte API (MSW) ile; istek gövdeleri de denetlenir.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { BEN_ORNEK, oturumGerekli, oturumYok, sunucu } from "../test/sunucu";
import { cikisYap, hesapMenusunuAc, uygulamayiCiz } from "../test/yardimcilar";
import { SURE_DOLDU_MESAJI } from "./KorumaliAlan";
import { SELAM_DESENI } from "../sayfalar/selam";

const PAROLA = "dogru-at-pil-zimba";

/** Girişi kabul eden sahte sunucu: başarılı girişten sonra /api/ben de kullanıcıyı döner. */
function girisiKabulEt() {
  let girisYapildi = false;
  const govdeler: unknown[] = [];
  sunucu.use(
    http.get("/api/ben", () => (girisYapildi ? HttpResponse.json(BEN_ORNEK) : oturumGerekli())),
    http.post("/api/giris", async ({ request }) => {
      govdeler.push(await request.json());
      girisYapildi = true;
      return HttpResponse.json(BEN_ORNEK);
    }),
  );
  return govdeler;
}

describe("korumalı sayfalar ve giriş", () => {
  it("girişsiz kullanıcı giriş sayfasına gider, girişten sonra istediği sayfaya döner", async () => {
    const govdeler = girisiKabulEt();
    const { kullanici } = uygulamayiCiz("/ogretmenler");

    expect(await screen.findByRole("heading", { level: 1, name: "Tekrar hoş geldiniz" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Ana menü" })).not.toBeInTheDocument();

    await kullanici.type(screen.getByLabelText(/E-posta/), "ayse@okul.test");
    await kullanici.type(screen.getByLabelText(/Parola/), PAROLA);
    await kullanici.click(screen.getByRole("button", { name: "Giriş yap" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Öğretmenler" })).toBeInTheDocument();
    expect(govdeler).toEqual([{ email: "ayse@okul.test", sifre: PAROLA }]);
    // Üst çubukta okul ve kullanıcı
    expect(screen.getByText("Çizelge Örnek Anadolu Lisesi")).toBeInTheDocument();
    await hesapMenusunuAc(kullanici);
    expect(screen.getByRole("link", { name: "Hesabım" })).toHaveAttribute("href", "/hesabim");
  });

  it("boş alanla sunucuya gidilmez: mesaj düğmenin üstünde, ilk boş alana odaklanılır", async () => {
    const govdeler = girisiKabulEt();
    const { kullanici } = uygulamayiCiz("/giris");
    const dugme = await screen.findByRole("button", { name: "Giriş yap" });
    await kullanici.click(dugme);
    const mesaj = screen.getByText("E-posta ve parolanızı yazın.");
    expect(mesaj).toHaveAttribute("role", "alert");
    // Mesaj düğmeden önce gelir (DOCUMENT_POSITION_FOLLOWING: düğme mesajın ardında).
    expect(mesaj.compareDocumentPosition(dugme) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByLabelText(/E-posta/)).toHaveFocus();

    // Yalnızca parola boşsa odak parolaya gider.
    await kullanici.type(screen.getByLabelText(/E-posta/), "ayse@okul.test");
    await kullanici.click(dugme);
    expect(screen.getByLabelText(/Parola/)).toHaveFocus();
    expect(govdeler).toEqual([]);
  });

  it("parolasını unutan kullanıcıya ne yapacağı söylenir", async () => {
    oturumYok();
    uygulamayiCiz("/giris");
    expect(await screen.findByLabelText(/Parola/)).toHaveAccessibleDescription("Parolanızı unuttuysanız okul yöneticinize başvurun.");
  });

  it("giriş sayfasında logo, tema düğmesi ve imza var", async () => {
    oturumYok();
    uygulamayiCiz("/giris");
    expect(await screen.findByRole("button", { name: /temaya geç/ })).toBeInTheDocument();
    expect(screen.getByText("Yusuf Ayçiçek tarafından geliştirildi")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Yusuf Ayçiçek/ })).not.toBeInTheDocument();
    // ">ya" imza logosu yalnızca imzada; ürünün logosu takvim ikonu.
    const imzaLogolari = [...document.querySelectorAll("svg text")].filter((t) => t.textContent === ">ya");
    expect(imzaLogolari).toHaveLength(1);
    expect(screen.getByText("Yusuf Ayçiçek tarafından geliştirildi")).toContainElement(imzaLogolari[0] as HTMLElement);
  });

  it("hareket açıksa başarılı girişte önce 'Hoş geldiniz' görünür, sonra yönlendirilir", async () => {
    girisiKabulEt();
    // jsdom matchMedia bilmez (hareket azaltılmış sayılır); burada hareket açık bir cihaz taklit edilir.
    vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }));
    try {
      const { kullanici } = uygulamayiCiz("/giris");
      await kullanici.type(await screen.findByLabelText(/E-posta/), "ayse@okul.test");
      await kullanici.type(screen.getByLabelText(/Parola/), PAROLA);
      await kullanici.click(screen.getByRole("button", { name: "Giriş yap" }));
      expect(await screen.findByRole("button", { name: "Hoş geldiniz" })).toBeInTheDocument();
      expect(screen.getByText("Giriş başarılı. Hoş geldiniz.")).toHaveAttribute("role", "status");
      expect(await screen.findByRole("heading", { level: 1, name: SELAM_DESENI }, { timeout: 3000 })).toBeInTheDocument();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it.each([
    [401, "E-posta ya da parola hatalı"],
    [429, "Çok fazla hatalı deneme. 15 dakika sonra yeniden deneyin."],
  ])("sunucu %i dönerse mesajı formun üstünde gösterilir", async (durum, mesaj) => {
    oturumYok();
    sunucu.use(http.post("/api/giris", () => HttpResponse.json({ detail: mesaj }, { status: durum })));
    const { kullanici } = uygulamayiCiz("/giris");
    await kullanici.type(await screen.findByLabelText(/E-posta/), "ayse@okul.test");
    await kullanici.type(screen.getByLabelText(/Parola/), "yanlis-parola-1234");
    await kullanici.click(screen.getByRole("button", { name: "Giriş yap" }));
    expect(await screen.findByText(mesaj)).toBeInTheDocument();
    expect(screen.getByText(mesaj).closest('[role="alert"]')).not.toBeNull();
    expect(screen.getByRole("heading", { level: 1, name: "Tekrar hoş geldiniz" })).toBeInTheDocument();
  });

  it("giriş yapmış kullanıcı giriş sayfasına gelirse ana sayfaya gider", async () => {
    uygulamayiCiz("/giris");
    expect(await screen.findByRole("heading", { level: 1, name: SELAM_DESENI })).toBeInTheDocument();
  });
});

describe("demo ile dene", () => {
  it("sunucuda demo kapalıysa düğme görünmez", async () => {
    oturumYok();
    uygulamayiCiz("/giris");
    expect(await screen.findByRole("button", { name: "Giriş yap" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("ya da")).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Demo ile dene" })).not.toBeInTheDocument();
  });

  it("demo açıksa tek tıkla, parolasız ve gövdesiz istekle demo okula girilir", async () => {
    let girisYapildi = false;
    const govdeler: string[] = [];
    sunucu.use(
      http.get("/api/ben", () => (girisYapildi ? HttpResponse.json(BEN_ORNEK) : oturumGerekli())),
      http.get("/api/oturum/demo", () => HttpResponse.json({ acik: true })),
      http.post("/api/oturum/demo", async ({ request }) => {
        govdeler.push(await request.text());
        girisYapildi = true;
        return HttpResponse.json(BEN_ORNEK);
      }),
    );
    const { kullanici } = uygulamayiCiz("/giris");
    const dugme = await screen.findByRole("button", { name: "Demo ile dene" });
    expect(dugme).toHaveAccessibleDescription("Örnek okulla açılır, parola gerekmez. Demo verileri düzenli olarak sıfırlanır.");
    await kullanici.click(dugme);
    expect(await screen.findByRole("heading", { level: 1, name: SELAM_DESENI })).toBeInTheDocument();
    expect(govdeler).toEqual([""]);
  });

  it("demo okul kurulmamışsa sunucunun mesajı gösterilir", async () => {
    oturumYok();
    sunucu.use(
      http.get("/api/oturum/demo", () => HttpResponse.json({ acik: true })),
      http.post("/api/oturum/demo", () => HttpResponse.json({ detail: "Demo okul bulunamadı" }, { status: 404 })),
    );
    const { kullanici } = uygulamayiCiz("/giris");
    await kullanici.click(await screen.findByRole("button", { name: "Demo ile dene" }));
    expect(await screen.findByText("Demo okul bulunamadı")).toHaveAttribute("role", "alert");
  });
});

describe("oturum süresinin dolması ve çıkış", () => {
  it("bir istek 401 alırsa giriş sayfasına gidilir ve neden söylenir", async () => {
    let girisVar = true;
    sunucu.use(
      http.get("/api/ben", () => (girisVar ? HttpResponse.json(BEN_ORNEK) : oturumGerekli())),
      http.get("/api/saglik", () => {
        girisVar = false; // sunucu tarafında oturum bu arada sona erdi
        return oturumGerekli();
      }),
    );
    uygulamayiCiz("/");
    expect(await screen.findByText(SURE_DOLDU_MESAJI)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Tekrar hoş geldiniz" })).toBeInTheDocument();
  });

  it("çıkış yapınca giriş sayfası ve 'Çıkış yaptınız'", async () => {
    let girisVar = true;
    sunucu.use(
      http.get("/api/ben", () => (girisVar ? HttpResponse.json(BEN_ORNEK) : oturumGerekli())),
      http.post("/api/cikis", () => {
        girisVar = false;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { kullanici } = uygulamayiCiz("/");
    await cikisYap(kullanici);
    expect(await screen.findByText("Çıkış yaptınız.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Tekrar hoş geldiniz" })).toBeInTheDocument();
  });

  it("sunucuya ulaşılamasa da çıkış yapılmış sayılır", async () => {
    sunucu.use(http.post("/api/cikis", () => HttpResponse.error()));
    const { kullanici } = uygulamayiCiz("/");
    await hesapMenusunuAc(kullanici);
    const cikis = screen.getByRole("button", { name: "Çıkış" });
    oturumYok(); // bundan sonra sunucu kullanıcıyı tanımıyor
    await kullanici.click(cikis);
    expect(await screen.findByRole("heading", { level: 1, name: "Tekrar hoş geldiniz" })).toBeInTheDocument();
  });
});

describe("kayıt", () => {
  async function formuDoldur(kullanici: ReturnType<typeof uygulamayiCiz>["kullanici"], degisen: Record<string, string> = {}) {
    const deger = { okul: "Çizelge Örnek Anadolu Lisesi", saat: "8", ad: "Ayşe Yılmaz", email: "ayse@okul.test", sifre: PAROLA, tekrar: PAROLA, ...degisen };
    await kullanici.type(await screen.findByLabelText(/Okulun adı/), deger.okul);
    const saat = screen.getByLabelText(/Günde kaç ders saati/);
    await kullanici.clear(saat);
    if (deger.saat) await kullanici.type(saat, deger.saat);
    await kullanici.type(screen.getByLabelText(/Adınız ve soyadınız/), deger.ad);
    await kullanici.type(screen.getByLabelText(/E-posta/), deger.email);
    await kullanici.type(screen.getByLabelText(/^Parola \*/), deger.sifre);
    await kullanici.type(screen.getByLabelText(/Parola \(tekrar\)/), deger.tekrar);
  }

  it("başarılı kayıt ana sayfaya götürür ve gövde doğru gider", async () => {
    oturumYok();
    const govdeler: unknown[] = [];
    sunucu.use(http.post("/api/kayit", async ({ request }) => {
      govdeler.push(await request.json());
      return HttpResponse.json(BEN_ORNEK, { status: 201 });
    }));
    const { kullanici } = uygulamayiCiz("/kayit");
    await formuDoldur(kullanici);
    await kullanici.selectOptions(screen.getByLabelText(/Haftada kaç gün/), "6");
    await kullanici.click(screen.getByRole("button", { name: "Okulu kaydet" }));

    expect(await screen.findByRole("heading", { level: 1, name: SELAM_DESENI })).toBeInTheDocument();
    expect(await screen.findByText("Çizelge Örnek Anadolu Lisesi kaydedildi. Hoş geldiniz!")).toBeInTheDocument();
    expect(govdeler).toEqual([{
      okul: { ad: "Çizelge Örnek Anadolu Lisesi", gun_sayisi: 6, gunluk_ders_saati: 8 },
      ad: "Ayşe Yılmaz", email: "ayse@okul.test", sifre: PAROLA,
    }]);
  });

  it("kısa parola, eşleşmeyen tekrar ve geçersiz saat sunucuya gitmeden yakalanır", async () => {
    oturumYok();
    let istek = 0;
    sunucu.use(http.post("/api/kayit", () => { istek++; return HttpResponse.json(BEN_ORNEK, { status: 201 }); }));
    const { kullanici } = uygulamayiCiz("/kayit");
    await formuDoldur(kullanici, { sifre: "kisa", tekrar: "baska", saat: "20" });
    await kullanici.click(screen.getByRole("button", { name: "Okulu kaydet" }));

    expect(screen.getByLabelText(/^Parola \*/)).toHaveAccessibleDescription(/Parola en az 12 karakter olmalı/);
    expect(screen.getByLabelText(/Parola \(tekrar\)/)).toHaveAccessibleDescription("Parolalar eşleşmiyor");
    expect(screen.getByLabelText(/Günde kaç ders saati/)).toHaveAccessibleDescription("1 ile 16 arasında bir sayı girin");
    expect(screen.getByLabelText(/Günde kaç ders saati/)).toHaveFocus(); // formdaki ilk hatalı alan
    expect(istek).toBe(0);
  });

  it("parola uzunluğu yazarken gösterilir", async () => {
    oturumYok();
    const { kullanici } = uygulamayiCiz("/kayit");
    const parola = await screen.findByLabelText(/^Parola \*/);
    expect(parola).toHaveAccessibleDescription("En az 12 karakter.");
    await kullanici.type(parola, "abcde");
    expect(parola).toHaveAccessibleDescription("En az 12 karakter. 7 karakter daha.");
    await kullanici.type(parola, "fghijkl");
    expect(parola).toHaveAccessibleDescription("Uzunluk yeterli ✓");
  });

  it("e-posta başka hesapta kullanılıyorsa (409) mesaj e-posta alanının altında", async () => {
    oturumYok();
    sunucu.use(http.post("/api/kayit", () =>
      HttpResponse.json({ detail: "Bu e-posta adresi başka bir hesapta kullanılıyor" }, { status: 409 })));
    const { kullanici } = uygulamayiCiz("/kayit");
    await formuDoldur(kullanici);
    await kullanici.click(screen.getByRole("button", { name: "Okulu kaydet" }));
    const eposta = screen.getByLabelText(/E-posta/);
    await waitFor(() => expect(eposta).toHaveAccessibleDescription(/Bu e-posta adresi başka bir hesapta kullanılıyor/));
    expect(eposta).toHaveAttribute("aria-invalid", "true");
  });

  it("sunucunun alan hataları (422) ilgili alanların altına yerleşir", async () => {
    oturumYok();
    sunucu.use(http.post("/api/kayit", () => HttpResponse.json(
      { detail: "Bazı alanlar hatalı", alanlar: { "okul.ad": "En fazla 200 karakter olabilir", email: "Geçerli bir e-posta adresi girin" } },
      { status: 422 })));
    const { kullanici } = uygulamayiCiz("/kayit");
    await formuDoldur(kullanici);
    await kullanici.click(screen.getByRole("button", { name: "Okulu kaydet" }));
    await waitFor(() => expect(screen.getByLabelText(/Okulun adı/)).toHaveAccessibleDescription("En fazla 200 karakter olabilir"));
    expect(screen.getByLabelText(/E-posta/)).toHaveAccessibleDescription(/Geçerli bir e-posta adresi girin/);
    expect(screen.queryByText("Bazı alanlar hatalı")).not.toBeInTheDocument(); // alanlara dağıldı
  });
});

describe("hesabım", () => {
  it("bilgiler görünür; parola değişir, başarı bildirilir ve form temizlenir", async () => {
    const govdeler: unknown[] = [];
    sunucu.use(http.put("/api/ben/sifre", async ({ request }) => {
      govdeler.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }));
    const { kullanici } = uygulamayiCiz("/hesabim");
    const bilgiler = await screen.findByRole("region", { name: "Bilgilerim" });
    expect(within(bilgiler).getByText("ayse@okul.test")).toBeInTheDocument();
    expect(within(bilgiler).getByText("Müdür")).toBeInTheDocument();

    await kullanici.type(screen.getByLabelText(/Mevcut parola/), PAROLA);
    await kullanici.type(screen.getByLabelText(/^Yeni parola \*/), "yepyeni-parola-2026");
    await kullanici.type(screen.getByLabelText(/Yeni parola \(tekrar\)/), "yepyeni-parola-2026");
    await kullanici.click(screen.getByRole("button", { name: "Parolayı değiştir" }));

    expect(await screen.findByText("Parolanız değiştirildi. Diğer cihazlardaki oturumlarınız kapatıldı.")).toBeInTheDocument();
    expect(govdeler).toEqual([{ eski: PAROLA, yeni: "yepyeni-parola-2026" }]);
    expect(screen.getByLabelText(/Mevcut parola/)).toHaveValue("");
  });

  it("mevcut parola yanlışsa mesaj o alanın altında", async () => {
    sunucu.use(http.put("/api/ben/sifre", () => HttpResponse.json({ detail: "Mevcut parola hatalı" }, { status: 422 })));
    const { kullanici } = uygulamayiCiz("/hesabim");
    await kullanici.type(await screen.findByLabelText(/Mevcut parola/), "yanlis-parola-1234");
    await kullanici.type(screen.getByLabelText(/^Yeni parola \*/), "yepyeni-parola-2026");
    await kullanici.type(screen.getByLabelText(/Yeni parola \(tekrar\)/), "yepyeni-parola-2026");
    await kullanici.click(screen.getByRole("button", { name: "Parolayı değiştir" }));
    await waitFor(() => expect(screen.getByLabelText(/Mevcut parola/)).toHaveAccessibleDescription("Mevcut parola hatalı"));
  });
});
