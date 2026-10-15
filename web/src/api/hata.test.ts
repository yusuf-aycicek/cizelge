import { describe, expect, it } from "vitest";
import { ApiHatasi, BAGLANTI_HATASI, cagir, govdedenHata, hataMetni } from "./hata";

function yanit(durum: number) {
  return new Response(null, { status: durum });
}

describe("govdedenHata", () => {
  it("servis hatası: sunucunun Türkçe metni", () => {
    const h = govdedenHata(409, { detail: "Bu e-posta adresi başka bir hesapta kullanılıyor" });
    expect([h.durum, h.message, h.alanlar]).toEqual([409, "Bu e-posta adresi başka bir hesapta kullanılıyor", {}]);
  });

  it("doğrulama hatası: alan mesajları", () => {
    const h = govdedenHata(422, { detail: "Bazı alanlar hatalı", alanlar: { "okul.ad": "Boş bırakılamaz", email: "Geçerli bir e-posta adresi girin" } });
    expect(h.message).toBe("Bazı alanlar hatalı");
    expect(h.alanlar).toEqual({ "okul.ad": "Boş bırakılamaz", email: "Geçerli bir e-posta adresi girin" });
  });

  it.each([
    [502, BAGLANTI_HATASI],
    [504, BAGLANTI_HATASI],
    [401, "Oturum açmanız gerekiyor."],
    [500, "Sunucuda beklenmeyen bir hata oluştu. Biraz sonra yeniden deneyin."],
    [418, "İstek tamamlanamadı."],
  ])("metinsiz %i yanıtı anlaşılır mesaja çevrilir", (durum, mesaj) => {
    expect(govdedenHata(durum, "<html>Bad Gateway</html>").message).toBe(mesaj);
  });

  it("sunucunun 503 metni varsa o kullanılır (ör. kuyruk)", () => {
    expect(govdedenHata(503, { detail: "Program üretim kuyruğuna ulaşılamadı." }).message).toBe("Program üretim kuyruğuna ulaşılamadı.");
  });
});

describe("cagir", () => {
  it("başarıda veriyi döner", async () => {
    expect(await cagir(Promise.resolve({ data: { a: 1 }, response: yanit(200) }))).toEqual({ a: 1 });
  });

  it("hata yanıtında ApiHatasi fırlatır", async () => {
    const istek = cagir(Promise.resolve({ error: { detail: "Kayıt yok" }, response: yanit(404) }));
    await expect(istek).rejects.toEqual(new ApiHatasi(404, "Kayıt yok"));
  });

  it("bağlantı hiç kurulamazsa durum 0 ve bağlantı mesajı", async () => {
    const hata = await cagir(Promise.reject(new TypeError("Failed to fetch"))).catch((h: unknown) => h);
    expect(hata).toBeInstanceOf(ApiHatasi);
    expect((hata as ApiHatasi).durum).toBe(0);
    expect((hata as ApiHatasi).baglantiHatasi).toBe(true);
    expect(hataMetni(hata)).toBe(BAGLANTI_HATASI);
    expect(hataMetni(new Error("x"))).not.toContain("x");  // iç hata metni kullanıcıya sızmaz
  });
});
