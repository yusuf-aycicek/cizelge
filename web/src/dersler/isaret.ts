/**
 * Renk tekrar edince ayırt edici işaret. Palet 20 renk (API: cekirdek/ders_renkleri.py); ders
 * sayısı bunu aşarsa ya da kullanıcı iki derse aynı rengi seçerse aynı renkli çipler karışmasın:
 * aynı rengi paylaşan derslerden ilki işaretsiz, sonrakiler ◆ ▲ ● ■ ★ alır.
 *
 * Sıra derslerin verildiği sıradır (API eklenme sırasıyla döner): yeni bir ders eklenince eski
 * derslerin işareti değişmez.
 */
export const ISARETLER = ["", "◆", "▲", "●", "■", "★"];

/** Ders kimliği -> işaret sırası (0 = işaretsiz). */
export function dersIsaretleri(dersler: readonly { id: string; renk: string }[]): Map<string, number> {
  const sayac = new Map<string, number>();
  const sonuc = new Map<string, number>();
  for (const d of dersler) {
    const sira = sayac.get(d.renk) ?? 0;
    sonuc.set(d.id, sira);
    sayac.set(d.renk, sira + 1);
  }
  return sonuc;
}

/** Sıradan işaret karakteri; beşten fazlası sayıyla (çok nadir). */
export function isaretKarakteri(sira: number): string {
  return ISARETLER[sira] ?? String(sira + 1);
}
