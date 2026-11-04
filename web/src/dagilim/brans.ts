/**
 * Öğretmen seçicide sıralama: dersin branşıyla eşleşen öğretmenler üstte, diğerleri altta.
 *
 * Branş serbest metindir ("Matematik", "Fizik Öğretmeni", "Türk Dili ve Edebiyatı"); kesin bir
 * eşleştirme yapılamaz. Bu yüzden eşleşme yalnızca **sıralamayı** belirler, hiçbir öğretmeni
 * gizlemez: yanlış eşleşen ya da eşleşmeyen öğretmen de alttaki grupta seçilebilir.
 *
 * Kural: büyük/küçük harf Türkçe kurallarıyla yok sayılır, harf ve rakam dışındaki işaretler
 * boşluk sayılır. Branş ile dersin adından kısa olanı uzun olanın içinde **bir kelimenin başında**
 * geçiyorsa ve en az 4 harfse eşleşir:
 * - "Fizik Öğretmeni" ↔ "Fizik", "Yabancı Dil (İngilizce)" ↔ "İngilizce";
 * - "Edebiyat" ↔ "Türk Dili ve Edebiyatı" (Türkçe ekler kelimenin sonuna gelir, başı aynı kalır);
 * - "Ma" ↮ "Matematik" (çok kısa: hemen her şeyin parçası olurdu).
 * Kısa ad yalnızca birebir eşitse sayılır ("MAT").
 */
import { turkceSirala } from "../metin";

const sade = (s: string | null | undefined) =>
  (s ?? "").toLocaleLowerCase("tr").replace(/[^\p{L}\p{N}]+/gu, " ").trim();

const EN_AZ_HARF = 4;

/** `kisa`, `uzun`un içinde bir kelimenin başında geçiyor mu? */
function kelimeBasindaGecer(uzun: string, kisa: string): boolean {
  return kisa.length >= EN_AZ_HARF && (uzun.startsWith(kisa) || uzun.includes(` ${kisa}`));
}

export function bransUyar(brans: string | null | undefined, ders: { ad: string; kisa_ad?: string | null }): boolean {
  // Branş derslerden çoklu seçimdir ("Matematik, Fizik"; ADR 0029): parçalardan biri uyarsa yeter.
  const parcalar = (brans ?? "").split(",");
  if (parcalar.length > 1) return parcalar.some((p) => bransUyar(p, ders));
  const b = sade(brans);
  if (!b) return false;
  const ad = sade(ders.ad);
  if (ad && (kelimeBasindaGecer(ad, b) || kelimeBasindaGecer(b, ad))) return true;
  return b === sade(ders.kisa_ad);
}

/** Öğretmenleri iki gruba ayırır; her grup kendi içinde Türkçe ada göre sıralıdır. */
export function bransaGoreGrupla<T extends { ad: string; brans?: string | null }>(
  ogretmenler: readonly T[],
  ders: { ad: string; kisa_ad?: string | null } | undefined,
): { uyan: T[]; diger: T[] } {
  const sirali = turkceSirala(ogretmenler, (o) => o.ad);
  if (!ders) return { uyan: [], diger: sirali };
  return {
    uyan: sirali.filter((o) => bransUyar(o.brans, ders)),
    diger: sirali.filter((o) => !bransUyar(o.brans, ders)),
  };
}
