import type { CSSProperties } from "react";

const PALET_KODU = /^#[0-9a-f]{6}$/i;

/**
 * Dersin palet rengini (API'den, ör. "#1d4ed8") çipin CSS değişkenlerine bağlar:
 * - `--ders-zemin` / `--ders-yazi`: temaya göre pastel zemin ve okunaklı yazı
 *   (stil/ders-renkleri.css; paletin her rengi orada tanımlı, kontrastı test edilir);
 * - `--ders-rengi`: rengin kendisi (ince çizgi, kenar gibi süsler için).
 * Palette olmayan bir renk gelirse (eski veri) rengin kendisi zemin, çip yazısı beyaz olur.
 * Biçimi bozuk değer CSS'e hiç yazılmaz.
 */
export function dersRenkStili(renk?: string | null): CSSProperties | undefined {
  if (!renk || !PALET_KODU.test(renk)) return undefined;
  const kod = renk.slice(1).toLowerCase();
  return {
    "--ders-rengi": renk,
    "--ders-zemin": `var(--ders-${kod}-zemin, ${renk})`,
    "--ders-yazi": `var(--ders-${kod}-yazi, var(--renk-cip-metin))`,
  } as CSSProperties;
}
