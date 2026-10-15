import type { ComponentPropsWithRef } from "react";
import stil from "./Dugme.module.css";

type DugmeTuru = "birincil" | "ikincil" | "tehlike" | "metin";

// Bileşenin "props"u: dışarıdan verilen değerler. Doğal <button>'ın bütün özelliklerini
// (onClick, disabled, aria-*, ve React 19'da sıradan bir prop olan ref) alır, üstüne üç tane ekler.
type Props = ComponentPropsWithRef<"button"> & {
  tur?: DugmeTuru;
  /** İşlem sürerken düğme kilitlenir ve bu metni gösterir: çift tıklama ikinci isteği göndermez. */
  yukleniyor?: boolean;
  yukleniyorMetni?: string;
};

/**
 * Ortak düğme. Doğal <button> öğesidir: klavyede Enter ve boşlukla çalışır, odaklanabilir,
 * ekran okuyucu "düğme" der. Varsayılan `type="button"`: formun içinde yanlışlıkla formu
 * göndermesin (göndermesi gereken düğmeye açıkça `type="submit"` yazılır).
 */
export function Dugme({
  tur = "birincil",
  yukleniyor = false,
  yukleniyorMetni = "Lütfen bekleyin...",
  type = "button",
  disabled,
  className,
  children,
  ...diger
}: Props) {
  return (
    <button
      type={type}
      className={[stil.dugme, stil[tur], className].filter(Boolean).join(" ")}
      disabled={disabled || yukleniyor}
      aria-busy={yukleniyor || undefined}
      {...diger}
    >
      {yukleniyor ? yukleniyorMetni : children}
    </button>
  );
}
