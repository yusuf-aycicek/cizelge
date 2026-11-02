/**
 * Ana sayfanın karşılaması: günün saatine göre selam ve bugünün tarihi. Saf fonksiyonlar;
 * zaman dışarıdan verilir (test edilebilir).
 */

/** Ana sayfa başlığının deseni (testler ve ekran görüntüsü betiği bununla bekler). */
export const SELAM_DESENI = /^(Günaydın|İyi günler|İyi akşamlar|İyi geceler)\b/;

export function selam(tarih: Date): string {
  const saat = tarih.getHours();
  if (saat >= 5 && saat < 12) return "Günaydın";
  if (saat >= 12 && saat < 18) return "İyi günler";
  if (saat >= 18 && saat < 23) return "İyi akşamlar";
  return "İyi geceler";
}

/** "2 Kasım 2026, Pazartesi" */
export function tarihMetni(tarih: Date): string {
  const gun = tarih.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
  const hafta = tarih.toLocaleDateString("tr-TR", { weekday: "long" });
  return `${gun}, ${hafta}`;
}

/** Adın ilk kelimesi: "Ayşe Gülşen Yılmaz" -> "Ayşe". */
export const ilkAd = (ad: string) => ad.trim().split(/\s+/)[0] ?? ad;
