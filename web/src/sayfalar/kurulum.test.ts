import { describe, expect, it } from "vitest";
import { kurulumDurumu, type KurulumGirdisi } from "./kurulum";

const BOS: KurulumGirdisi = { gunSayisi: 5, gunlukDersSaati: 8, ogretmen: 0, sinif: 0, ders: 0, atama: 0, ogretmensizAtama: 0 };
const durumlar = (g: KurulumGirdisi) => Object.fromEntries(kurulumDurumu(g).adimlar.map((a) => [a.anahtar, a.durum]));

describe("kurulum durumu", () => {
  it("yeni okul: yalnızca okul ayarları tamam (6 adımdan 1'i, %17)", () => {
    const d = kurulumDurumu(BOS);
    expect([d.tamamlanan, d.gereken, d.yuzde]).toEqual([1, 6, 17]);
    expect(d.adimlar.map((a) => a.ayrinti)).toEqual([
      "5 gün, günde 8 ders", "Henüz öğretmen yok", "Henüz şube yok", "Henüz ders yok", "Henüz ders atanmadı", "İsteğe bağlı", "Önceki adımlar bitince",
    ]);
  });

  it("öğretmeni seçilmemiş ders varsa dağılım eksik, sayısı yazar", () => {
    const g = { ...BOS, ogretmen: 5, sinif: 3, ders: 7, atama: 18, ogretmensizAtama: 3 };
    expect(durumlar(g).dagilim).toBe("eksik");
    const d = kurulumDurumu(g);
    expect(d.adimlar.find((a) => a.anahtar === "dagilim")?.ayrinti).toBe("3 dersin öğretmeni seçilmedi");
    expect([d.tamamlanan, d.yuzde]).toEqual([4, 67]);
  });

  it("veri tamam, program yok: program adımı sırada", () => {
    const d = kurulumDurumu({ ...BOS, ogretmen: 5, sinif: 3, ders: 7, atama: 18 });
    expect([d.tamamlanan, d.gereken, d.yuzde]).toEqual([5, 6, 83]);
    expect(d.adimlar.at(-1)).toMatchObject({ anahtar: "program", durum: "bekliyor", ayrinti: "Hazırsınız: programı oluşturun" });
  });

  it("program durumları: hazırlanıyor, başarısız, hazır (son hazıra bağlantı)", () => {
    const tam = { ...BOS, ogretmen: 5, sinif: 3, ders: 7, atama: 18 };
    const adim = (g: KurulumGirdisi) => kurulumDurumu(g).adimlar.at(-1);
    expect(adim({ ...tam, sonProgram: { id: "p2", ad: "Program 2", durum: "uretiliyor" } })).toMatchObject({ durum: "bekliyor", ayrinti: "Program hazırlanıyor..." });
    expect(adim({ ...tam, sonProgram: { id: "p2", ad: "Program 2", durum: "basarisiz" } })).toMatchObject({ durum: "eksik", yol: "/program" });
    // Son deneme başarısız olsa da daha önce hazır bir program varsa adım tamamdır.
    expect(adim({ ...tam, sonProgram: { id: "p2", ad: "Program 2", durum: "basarisiz" }, sonHazirProgram: { id: "p1", ad: "Program 1" } }))
      .toMatchObject({ durum: "tamam", yol: "/program/p1", ayrinti: "Son program: Program 1" });
  });

  it("hepsi tamam: %100; müsaitlik isteğe bağlı olarak sayılmaz", () => {
    const d = kurulumDurumu({ ...BOS, ogretmen: 5, sinif: 3, ders: 7, atama: 18, sonHazirProgram: { id: "p1", ad: "Program 1" } });
    expect([d.tamamlanan, d.gereken, d.yuzde]).toEqual([6, 6, 100]);
    expect(d.adimlar.find((a) => a.anahtar === "musaitlik")?.durum).toBe("istege-bagli");
    expect(d.adimlar.find((a) => a.anahtar === "ogretmen")?.ayrinti).toBe("5 öğretmen");
  });
});
