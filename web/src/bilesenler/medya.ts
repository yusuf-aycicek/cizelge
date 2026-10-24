import { useSyncExternalStore } from "react";

/** Telefon genişliği: haftalık çizelge bu genişlikte gün gün görünür (5.6). */
export const TELEFON = "(max-width: 40rem)";

/**
 * Bir CSS medya sorgusunun o anki sonucu; pencere boyutu değişince bileşen yeniden çizilir.
 *
 * `useSyncExternalStore`: React'in dışındaki bir değere (tarayıcının matchMedia'sı) abone olmanın
 * doğru yolu. `useEffect` + `useState` ile de yapılabilirdi, ama o zaman ilk çizim yanlış değerle
 * yapılıp hemen düzeltilirdi (bir kare masaüstü düzeni görünürdü). matchMedia olmayan ortamda
 * (testteki jsdom) sonuç `false`: masaüstü düzeni.
 *
 * Gün gün görünüm CSS'le de gizlenip gösterilebilirdi; ama o zaman iki görünüm birden DOM'da ve
 * ekran okuyucunun ağacında olurdu (aynı ders iki kez okunurdu). Kanca yalnızca birini çizer.
 */
export function useMedya(sorgu: string): boolean {
  return useSyncExternalStore(
    (degisti) => {
      if (typeof window.matchMedia !== "function") return () => {};
      const m = window.matchMedia(sorgu);
      m.addEventListener("change", degisti);
      return () => m.removeEventListener("change", degisti);
    },
    () => typeof window.matchMedia === "function" && window.matchMedia(sorgu).matches,
  );
}
