/**
 * Türkçe metin işlemleri.
 *
 * JavaScript'in varsayılan sıralaması harf kodlarına göredir: "Çağla", "Zeynep"ten sonra gelir;
 * "İ" ile "I" karışır. `Intl.Collator("tr")` Türk alfabesinin sırasını bilir:
 * A B C Ç D E F G Ğ H I İ J K L M N O Ö P R S Ş T U Ü V Y Z.
 * `numeric: true`: "9-A" < "10-A" (sayılar sayı olarak karşılaştırılır).
 */
const harmanlayici = new Intl.Collator("tr", { numeric: true, sensitivity: "base" });

export function turkceKarsilastir(a: string, b: string): number {
  return harmanlayici.compare(a, b);
}

/** Yeni bir dizi döner; girdiyi değiştirmez. */
export function turkceSirala<T>(ogeler: readonly T[], metin: (oge: T) => string): T[] {
  return [...ogeler].sort((a, b) => turkceKarsilastir(metin(a), metin(b)));
}

/**
 * Arama: büyük/küçük harf duyarsız, Türkçe kurallarla ("İ" küçülünce "i", "I" küçülünce "ı").
 * "şule" → "Şule", "ismail" → "İsmail" bulunur.
 */
export function turkceIcerir(metin: string, aranan: string): boolean {
  return metin.toLocaleLowerCase("tr").includes(aranan.trim().toLocaleLowerCase("tr"));
}
