import { useLayoutEffect, useRef, useState } from "react";

/**
 * Uzun metin bulunduğu alana sığıyor mu? Sığmıyorsa `dar` true olur; bileşen o zaman kısa biçimi
 * (ör. "TDE", "Z. Demir") gösterir.
 *
 * Neden ölçüm: CSS bir metnin kutuya sığıp sığmadığını bilemez; genişlik eşiği ("hücre 9rem'den
 * darsa") kısa adları da gereksiz yere kısaltır, uzun adları ise yine keser.
 *
 * - `kutu`: alanın genişliğini veren öğe (kendisi taşmaz, genişliği alana eşittir).
 * - `metin`: uzun metni taşıyan öğe; uzun haliyle görünürken doğal genişliği (`scrollWidth`) ölçülür
 *   ve saklanır. Kısa biçim gösterilirken yeniden ölçülmez: alan genişleyince saklı değerle
 *   karşılaştırılıp uzun biçime dönülür.
 *
 * `useLayoutEffect`: ölçüm tarayıcı ekrana çizmeden önce yapılır, kesik metin bir an bile görünmez.
 * ResizeObserver yoksa (eski tarayıcı, test ortamı) metin uzun haliyle kalır.
 */
export function useDarAlan<K extends HTMLElement, M extends HTMLElement = K>(uzun: string) {
  const kutu = useRef<K>(null);
  const metin = useRef<M>(null);
  const dogal = useRef<number | null>(null);
  const [dar, setDar] = useState(false);
  const [oncekiUzun, setOncekiUzun] = useState(uzun);
  if (oncekiUzun !== uzun) {
    // Metin değişti: saklı ölçü geçersiz, uzun haliyle yeniden ölçülür (render sırasında state
    // ayarlamak, effect'te ayarlamaktan bir çizim daha erken düzeltir).
    setOncekiUzun(uzun);
    setDar(false);
  }

  useLayoutEffect(() => {
    const k = kutu.current;
    const m = metin.current ?? k;
    if (!k || !m || typeof ResizeObserver === "undefined") return;
    const karar = () => {
      if (!dar) dogal.current = m.scrollWidth;
      setDar(darMi(dogal.current ?? 0, k.clientWidth));
    };
    karar();
    const gozlemci = new ResizeObserver(karar);
    gozlemci.observe(k);
    return () => gozlemci.disconnect();
  }, [dar, uzun]);

  return { kutu, metin, dar };
}

/** Yarım piksellik yuvarlama farkı taşma sayılmaz. */
export const darMi = (dogalGenislik: number, alan: number) => dogalGenislik > alan + 0.5;

/** "Zeynep Demir" -> "Z. Demir"; "Ayşe Nur Yılmaz" -> "A. N. Yılmaz"; tek kelime aynen kalır. */
export function kisaKisiAdi(ad: string): string {
  const parcalar = ad.trim().split(/\s+/);
  if (parcalar.length < 2) return ad.trim();
  const soyad = parcalar.at(-1)!;
  return [...parcalar.slice(0, -1).map((p) => `${p.charAt(0).toLocaleUpperCase("tr-TR")}.`), soyad].join(" ");
}
