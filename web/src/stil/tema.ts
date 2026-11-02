/**
 * Açık ("mor") ve koyu ("mor gece") tema. Etkin tema <html data-tema="acik|koyu">'dadır;
 * belirtecler.css renkleri buna göre seçer.
 *
 * - İlk boyamadan önce index.html'deki küçük betik temayı koyar (yanlış temada bir kare görünmez).
 *   Mantığı buradakiyle aynıdır: kayıtlı seçim, yoksa cihazın ayarı (prefers-color-scheme).
 * - Kullanıcı düğmeyle değiştirirse seçim localStorage'a yazılır. Kayıtlı seçim yokken cihazın
 *   ayarı değişirse tema onu izler.
 * - localStorage kapalı ya da erişilemezse (gizli pencere, tarayıcı ayarı) hata vermez: tema yine
 *   değişir, yalnızca hatırlanmaz.
 * - Geçiş yumuşaktır (temel.css `.tema-gecisi`); hareket azaltılmışsa anında.
 */
import { useSyncExternalStore } from "react";
import { hareketAzaltilmis } from "../bilesenler/hareket";

export type Tema = "acik" | "koyu";

export const TEMA_ANAHTARI = "tema";
const KOYU_SORGUSU = "(prefers-color-scheme: dark)";
const GECIS_MS = 400;

const dinleyiciler = new Set<() => void>();

function kayitliTema(): Tema | null {
  try {
    const t = window.localStorage.getItem(TEMA_ANAHTARI);
    return t === "acik" || t === "koyu" ? t : null;
  } catch {
    return null;
  }
}

function cihazTemasi(): Tema {
  return typeof window.matchMedia === "function" && window.matchMedia(KOYU_SORGUSU).matches ? "koyu" : "acik";
}

export function etkinTema(): Tema {
  return document.documentElement.dataset.tema === "koyu" ? "koyu" : "acik";
}

function uygula(tema: Tema) {
  const kok = document.documentElement;
  if (kok.dataset.tema === tema) return;
  if (!hareketAzaltilmis()) {
    kok.classList.add("tema-gecisi");
    window.setTimeout(() => kok.classList.remove("tema-gecisi"), GECIS_MS);
  }
  kok.dataset.tema = tema;
  dinleyiciler.forEach((d) => d());
}

/** Kullanıcının seçimi: uygulanır ve hatırlanır. */
export function temaSec(tema: Tema) {
  try {
    window.localStorage.setItem(TEMA_ANAHTARI, tema);
  } catch {
    // hatırlanamıyor; tema yine de değişir
  }
  uygula(tema);
}

/** Uygulama açılırken bir kez (main.tsx): tema konmamışsa koyar, cihazın ayarını izler. */
export function temayiBaslat() {
  if (!document.documentElement.dataset.tema) document.documentElement.dataset.tema = kayitliTema() ?? cihazTemasi();
  if (typeof window.matchMedia !== "function") return;
  window.matchMedia(KOYU_SORGUSU).addEventListener("change", () => {
    if (!kayitliTema()) uygula(cihazTemasi());
  });
}

/** Etkin tema ve değiştirici. Tema her yerden değişebilir; bileşen yeniden çizilir. */
export function useTema(): [Tema, () => void] {
  const tema = useSyncExternalStore(
    (degisti) => {
      dinleyiciler.add(degisti);
      return () => dinleyiciler.delete(degisti);
    },
    etkinTema,
  );
  return [tema, () => temaSec(tema === "koyu" ? "acik" : "koyu")];
}
