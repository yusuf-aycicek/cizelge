import { describe, expect, it } from "vitest";
import { asamaBul, celiskileriGrupla, cozumAciklamasi, kaliteMaddeleri, sureMetni } from "./aciklama";

const BASLAMA = "2026-10-24T10:00:00Z";
const t = (sn: number) => Date.parse(BASLAMA) + sn * 1000;

describe("bekleme aşaması", () => {
  it("bekliyor: sırada", () => {
    expect(asamaBul({ durum: "bekliyor", baslama: null, sure_siniri_sn: 120 }, t(5))).toEqual({ sira: 0, ilerleme: 0, gecenSn: 0 });
  });
  it.each([
    [1, 1],
    [5, 2],
    [30, 3],
  ])("üretiliyor, %i sn: aşama %i", (sn, sira) => {
    expect(asamaBul({ durum: "uretiliyor", baslama: BASLAMA, sure_siniri_sn: 120 }, t(sn)).sira).toBe(sira);
  });
  it("ilerleme süre sınırına oranlanır, dolmadan %100 görünmez", () => {
    expect(asamaBul({ durum: "uretiliyor", baslama: BASLAMA, sure_siniri_sn: 120 }, t(60)).ilerleme).toBeCloseTo(0.5);
    expect(asamaBul({ durum: "uretiliyor", baslama: BASLAMA, sure_siniri_sn: 120 }, t(500)).ilerleme).toBe(0.97);
  });
  it("hazır: son aşama, tam", () => {
    expect(asamaBul({ durum: "hazir", baslama: BASLAMA, sure_siniri_sn: 120 }, t(5))).toMatchObject({ sira: 4, ilerleme: 1 });
  });
});

describe("çelişki grupları", () => {
  it("türe göre gruplar, sırayı korur, başlıkları Türkçe", () => {
    const gruplar = celiskileriGrupla([
      { tur: "ogretmen_secilmemis", mesaj: "9-A Fizik dersine öğretmen seçilmemiş." },
      { tur: "sinif_kapasitesi", mesaj: "9-A sınıfının haftada 42 saat dersi var..." },
      { tur: "ogretmen_secilmemis", mesaj: "9-B Fizik dersine öğretmen seçilmemiş." },
      { tur: "bilinmeyen_tur", mesaj: "?" },
    ]);
    expect(gruplar.map((g) => [g.baslik, g.maddeler.length])).toEqual([
      ["Öğretmeni seçilmemiş dersler", 2],
      ["Haftalık kapasiteyi aşan şubeler", 1],
      ["Diğer sorunlar", 1],
    ]);
  });
});

describe("süre metni", () => {
  it.each([
    [0.4, "1 saniyeden kısa"],
    [12.4, "12 saniye"],
    [120.4, "2 dakika"],
    [125, "2 dakika 5 saniye"],
  ])("%s sn → %s", (sn, metin) => {
    expect(sureMetni(sn)).toBe(metin);
  });
});

describe("kalite maddeleri", () => {
  const OLCUM = { sinif_boslugu: 0, ogretmen_penceresi: 7, eksik_bos_gun: 2, tercih_etmez: 0, bolunmus_ders: 1, degisen_yerlesim: 4 };

  it("sıfır olan iyi, olmayan sayısıyla söylenir", () => {
    const m = kaliteMaddeleri(OLCUM);
    expect(m.map((x) => [x.anahtar, x.iyi])).toEqual([
      ["sinif_boslugu", true], ["ogretmen_penceresi", false], ["eksik_bos_gun", false], ["tercih_etmez", true], ["bolunmus_ders", false],
    ]);
    expect(m[0]!.metin).toBe("Şubelerde gün ortasında boş saat yok.");
    expect(m[1]!.metin).toBe("Öğretmenlerin toplam 7 pencere saati var (iki dersi arasında boş bekledikleri saat).");
  });

  it("değişen hücre yalnızca temel program varsa söylenir", () => {
    expect(kaliteMaddeleri(OLCUM).some((x) => x.anahtar === "degisen_yerlesim")).toBe(false);
    expect(kaliteMaddeleri(OLCUM, true).at(-1)?.metin).toBe("Temel programa göre 4 hücre değişti.");
  });

  it("ölçü yoksa boş", () => {
    expect(kaliteMaddeleri(null)).toEqual([]);
  });

  it("çözüm açıklaması", () => {
    expect(cozumAciklamasi("optimal")).toMatch(/en iyi program \(kanıtlandı\)/);
    expect(cozumAciklamasi("uygun")).toMatch(/Süre sınırı dolduğunda/);
    expect(cozumAciklamasi(null)).toBe("");
  });
});

describe("öğretmene özel boş gün ölçüsü", () => {
  it("yalnızca sıfırdan büyükse listelenir", () => {
    const temel = { sinif_boslugu: 0, ogretmen_penceresi: 0, eksik_bos_gun: 0, tercih_etmez: 0, bolunmus_ders: 0, degisen_yerlesim: 0 };
    expect(kaliteMaddeleri(temel).some((m) => m.anahtar === "fazla_bos_gun")).toBe(false);
    const madde = kaliteMaddeleri({ ...temel, fazla_bos_gun: 2 }).find((m) => m.anahtar === "fazla_bos_gun");
    expect(madde).toEqual({ anahtar: "fazla_bos_gun", iyi: false, metin: "Kendine özel boş gün hedefi olan öğretmenler hedeften toplam 2 gün az geldi." });
  });
});
