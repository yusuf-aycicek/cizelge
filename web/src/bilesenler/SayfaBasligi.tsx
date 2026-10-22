import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import stil from "./SayfaBasligi.module.css";

type Props = {
  /** Menüdeki ikonun aynısı: kullanıcı sayfayı menüdeki işaretinden de tanır. */
  ikon: LucideIcon;
  baslik: string;
  /** Başlığın altındaki kısa açıklama. */
  children?: ReactNode;
};

/**
 * Sayfa başlık alanı: renkli ikon kutusu, sayfanın tek <h1>'i ve kısa açıklama. Zemin temanın vurgu
 * renginden türeyen hafif bir geçiştir (belirteçlerden, color-mix ile).
 */
export function SayfaBasligi({ ikon: Ikon, baslik, children }: Props) {
  return (
    <div className={stil.alan}>
      <span className={stil.ikon} aria-hidden="true">
        <Ikon />
      </span>
      <div className={stil.metin}>
        <h1 className={stil.baslik}>{baslik}</h1>
        {children && <p className={stil.aciklama}>{children}</p>}
      </div>
    </div>
  );
}
