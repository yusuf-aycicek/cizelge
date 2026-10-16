/**
 * Türkçe sıralama ve arama. Türk alfabesi: A B C Ç D E F G Ğ H I İ J K L M N O Ö P R S Ş T U Ü V Y Z.
 * JavaScript'in varsayılan sıralaması (harf kodu) bunların çoğunu yanlış sıraya koyar; testler
 * hem doğru sırayı hem de varsayılanın neden yetmediğini gösterir.
 */
import { describe, expect, it } from "vitest";
import { turkceIcerir, turkceKarsilastir, turkceSirala } from "./metin";

const kendisi = (s: string) => s;

describe("Türkçe sıralama", () => {
  it("Ç, Ğ, I/İ, Ö, Ş, Ü kendi yerlerinde", () => {
    const karisik = ["Zeynep", "Ümit", "Şule", "Ömer", "İsmail", "Irmak", "Ğ harfli Doğan", "Gül", "Çağla", "Cem",
      "Uğur", "Selin", "Osman", "Can"];
    expect(turkceSirala(karisik, kendisi)).toEqual([
      "Can", "Cem", "Çağla", "Gül", "Ğ harfli Doğan", "Irmak", "İsmail", "Osman", "Ömer", "Selin", "Şule", "Uğur",
      "Ümit", "Zeynep",
    ]);
  });

  it("varsayılan JavaScript sıralaması bu listede yanlış olurdu", () => {
    const liste = ["Zeynep", "Çağla", "İsmail", "Irmak", "Ömer", "Osman"];
    expect([...liste].sort()).not.toEqual(turkceSirala(liste, kendisi)); // ["Irmak","Osman","Zeynep","Çağla","Ömer","İsmail"]
  });

  it("sözcük içinde de: G < Ğ, I < İ, O < Ö, S < Ş, U < Ü, C < Ç", () => {
    expect(turkceKarsilastir("Dogru", "Doğan")).toBeLessThan(0); // g < ğ, sonrasına bakılmaz
    expect(turkceKarsilastir("Kılıç", "Kilit")).toBeLessThan(0); // ı < i
    expect(turkceKarsilastir("Kose", "Köse")).toBeLessThan(0);
    expect(turkceKarsilastir("Pasa", "Paşa")).toBeLessThan(0);
    expect(turkceKarsilastir("Kus", "Kuş")).toBeLessThan(0);
    expect(turkceKarsilastir("Uzum", "Üzüm")).toBeLessThan(0);
    expect(turkceKarsilastir("Ac", "Aç")).toBeLessThan(0);
  });

  it("şubeler sayıyla doğru sıralanır: 9-A < 10-A", () => {
    expect(turkceSirala(["11-B", "10-A", "9-B", "12-A", "9-A"], kendisi)).toEqual(["9-A", "9-B", "10-A", "11-B", "12-A"]);
  });

  it("girdiyi değiştirmez", () => {
    const liste = ["Şule", "Ali"];
    turkceSirala(liste, kendisi);
    expect(liste).toEqual(["Şule", "Ali"]);
  });
});

describe("Türkçe arama", () => {
  it.each([
    ["Şule Kaya", "şule", true],
    ["İsmail Demir", "ismail", true],
    ["Irmak Su", "ırmak", true],
    ["ÇAĞLA ÖZ", "çağla öz", true],
    ["Ümit Gül", "GÜL", true],
    ["İsmail", "ısmail", false], // İ küçülünce i olur, ı değil
    ["Selin", "şelin", false],
  ])("%s içinde '%s' → %s", (metin, aranan, beklenen) => {
    expect(turkceIcerir(metin, aranan)).toBe(beklenen);
  });
});
