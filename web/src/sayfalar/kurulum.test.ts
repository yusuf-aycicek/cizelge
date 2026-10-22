import { describe, expect, it } from "vitest";
import { kurulumDurumu, type KurulumGirdisi } from "./kurulum";

const BOS: KurulumGirdisi = { gunSayisi: 5, gunlukDersSaati: 8, ogretmen: 0, sinif: 0, ders: 0, atama: 0, ogretmensizAtama: 0 };
const durumlar = (g: KurulumGirdisi) => Object.fromEntries(kurulumDurumu(g).adimlar.map((a) => [a.anahtar, a.durum]));

describe("kurulum durumu", () => {
  it("yeni okul: yalnızca okul ayarları tamam (5 adımdan 1'i, %20)", () => {
    const d = kurulumDurumu(BOS);
    expect([d.tamamlanan, d.gereken, d.yuzde]).toEqual([1, 5, 20]);
    expect(d.adimlar.map((a) => a.ayrinti)).toEqual([
      "5 gün, günde 8 ders", "Henüz öğretmen yok", "Henüz şube yok", "Henüz ders yok", "Henüz ders atanmadı", "İsteğe bağlı",
    ]);
  });

  it("öğretmeni seçilmemiş ders varsa dağılım eksik, sayısı yazar", () => {
    const g = { ...BOS, ogretmen: 5, sinif: 3, ders: 7, atama: 18, ogretmensizAtama: 3 };
    expect(durumlar(g).dagilim).toBe("eksik");
    const d = kurulumDurumu(g);
    expect(d.adimlar.find((a) => a.anahtar === "dagilim")?.ayrinti).toBe("3 dersin öğretmeni seçilmedi");
    expect([d.tamamlanan, d.yuzde]).toEqual([4, 80]);
  });

  it("hepsi tamam: %100; müsaitlik isteğe bağlı olarak sayılmaz", () => {
    const d = kurulumDurumu({ ...BOS, ogretmen: 5, sinif: 3, ders: 7, atama: 18 });
    expect([d.tamamlanan, d.gereken, d.yuzde]).toEqual([5, 5, 100]);
    expect(d.adimlar.find((a) => a.anahtar === "musaitlik")?.durum).toBe("istege-bagli");
    expect(d.adimlar.find((a) => a.anahtar === "ogretmen")?.ayrinti).toBe("5 öğretmen");
  });
});
