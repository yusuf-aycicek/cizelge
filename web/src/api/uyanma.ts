/**
 * Yavaş yanıt takibi: "sunucu uyanıyor" bildirimi için.
 *
 * Yayında API ücretsiz bir sunucuda çalışır. Bir süre kullanılmayınca uyur, ilk istek onu
 * uyandırırken 30-60 sn bekletebilir. Herhangi bir API isteği GECIKME_ESIGI_MS'den uzun
 * sürerse bildirim görünür; bekleyen bütün yavaş istekler bitince kaybolur. Yerelde de çalışır,
 * ama orada istekler eşiği aşmadığı için görünmez.
 */
import { useSyncExternalStore } from "react";

export const GECIKME_ESIGI_MS = 3000;

let yavasSayisi = 0;
const dinleyiciler = new Set<() => void>();

function degisti(fark: number) {
  yavasSayisi += fark;
  dinleyiciler.forEach((d) => d());
}

/** `fetch`'i sarar: istek eşikten uzun sürerse bittiği ana kadar "yavaş" sayılır. */
export async function izle<T>(is: Promise<T>): Promise<T> {
  let yavas = false;
  const zamanlayici = setTimeout(() => {
    yavas = true;
    degisti(1);
  }, GECIKME_ESIGI_MS);
  try {
    return await is;
  } finally {
    clearTimeout(zamanlayici);
    if (yavas) degisti(-1);
  }
}

function abone(dinleyici: () => void) {
  dinleyiciler.add(dinleyici);
  return () => dinleyiciler.delete(dinleyici);
}

/** Şu an eşiği aşmış bekleyen istek var mı. */
export function useSunucuGecikiyor(): boolean {
  return useSyncExternalStore(abone, () => yavasSayisi > 0);
}
