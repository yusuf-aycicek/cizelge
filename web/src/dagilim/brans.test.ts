import { describe, expect, it } from "vitest";
import { bransaGoreGrupla, bransUyar } from "./brans";

const MAT = { ad: "Matematik", kisa_ad: "MAT" };
const EDB = { ad: "Türk Dili ve Edebiyatı", kisa_ad: "TDE" };
const ING = { ad: "İngilizce", kisa_ad: "İNG" };

describe("bransUyar", () => {
  it.each([
    ["Matematik", MAT],
    ["matematik", MAT], // büyük/küçük harf
    ["MATEMATİK", MAT], // Türkçe büyük İ -> i
    ["  Matematik ", MAT], // boşluklar
    ["Matematik Öğretmeni", MAT], // branş dersin adını içerir
    ["Edebiyat", EDB], // dersin adı branşı içerir
    ["Türk Dili ve Edebiyatı", EDB],
    ["İngilizce", ING],
    ["ingilizce", ING], // küçük i -> büyük İ ile eşleşir
    ["MAT", MAT], // kısa adla birebir
    ["Yabancı Dil (İngilizce)", ING], // işaretler boşluk sayılır
  ])("%s ↔ %s", (brans, ders) => {
    expect(bransUyar(brans, ders)).toBe(true);
  });

  it.each([
    ["", MAT],
    [null, MAT],
    ["Fizik", MAT],
    ["INGILIZCE", ING], // noktasız büyük I küçülünce ı olur: "ıngılızce" (Türkçe kuralı)
    ["MA", MAT], // kısa adın parçası sayılmaz
    ["matik", MAT], // kelimenin ortası sayılmaz (yalnızca kelime başı)
    // Bilinen sınır: 3 harfli branş eşleşmez. Yalnızca sıralamayı etkiler; öğretmen alttaki grupta seçilebilir.
    ["Din", { ad: "Din Kültürü ve Ahlak Bilgisi", kisa_ad: "DKAB" }],
  ])("%s ↮ %s", (brans, ders) => {
    expect(bransUyar(brans, ders)).toBe(false);
  });
});

describe("bransaGoreGrupla", () => {
  const ogretmenler = [
    { ad: "Zeynep Demir", brans: "Fizik" },
    { ad: "Şule Kaya", brans: "Matematik" },
    { ad: "Ali Çelik", brans: "" },
    { ad: "Çağla Öz", brans: "Matematik Öğretmeni" },
    { ad: "Ümit Kara", brans: "Kimya" },
  ];

  it("branşı uyanlar ayrı grupta, iki grup da Türkçe sıralı; kimse gizlenmez", () => {
    const { uyan, diger } = bransaGoreGrupla(ogretmenler, MAT);
    expect(uyan.map((o) => o.ad)).toEqual(["Çağla Öz", "Şule Kaya"]);
    expect(diger.map((o) => o.ad)).toEqual(["Ali Çelik", "Ümit Kara", "Zeynep Demir"]);
    expect(uyan.length + diger.length).toBe(ogretmenler.length);
  });

  it("ders yoksa herkes tek grupta", () => {
    const { uyan, diger } = bransaGoreGrupla(ogretmenler, undefined);
    expect(uyan).toEqual([]);
    expect(diger.map((o) => o.ad)).toEqual(["Ali Çelik", "Çağla Öz", "Şule Kaya", "Ümit Kara", "Zeynep Demir"]);
  });
});
