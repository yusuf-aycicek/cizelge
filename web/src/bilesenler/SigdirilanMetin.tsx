import { useDarAlan } from "./darAlan";
import stil from "./SigdirilanMetin.module.css";

/**
 * Alana sığarsa uzun, sığmazsa kısa metin (ör. öğretmen adı: "Zeynep Demir" / "Z. Demir"). Kısa
 * biçim gösterilirken tam ad kaybolmaz: üzerine gelince `title` ile görünür, ekran okuyucu ise
 * yalnızca tam adı okur (kısa biçim aria-hidden).
 */
export function SigdirilanMetin({ uzun, kisa }: { uzun: string; kisa: string }) {
  const { kutu, dar } = useDarAlan<HTMLSpanElement>(uzun);
  const kisalt = dar && kisa !== uzun;
  return (
    <span ref={kutu} className={stil.metin} title={kisalt ? uzun : undefined}>
      {kisalt ? (
        <>
          <span aria-hidden="true">{kisa}</span>
          <span className="gorunmez">{uzun}</span>
        </>
      ) : (
        uzun
      )}
    </span>
  );
}
