/**
 * Çıkış animasyonları için ortak kural. Giriş animasyonları yalnızca CSS'tir; çıkışta ise öğe
 * DOM'dan kalkmadan önce kısa bir süre "çıkıyor" sınıfıyla kalmalıdır (React öğeyi hemen kaldırır,
 * CSS'in oynatacak bir şeyi kalmaz).
 *
 * Kullanıcı işletim sisteminde hareketi azaltmışsa (`prefers-reduced-motion`) ya da ortam bunu
 * bildiremiyorsa (ör. testlerdeki jsdom) beklenmez: öğe hemen kalkar.
 */
export const CIKIS_MS = 250; // belirtecler.css --sure-uzun ile aynı

export function hareketAzaltilmis(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** `is` işini çıkış animasyonundan sonra yapar; hareket azaltılmışsa hemen. */
export function cikistanSonra(is: () => void): void {
  if (hareketAzaltilmis()) is();
  else window.setTimeout(is, CIKIS_MS);
}
