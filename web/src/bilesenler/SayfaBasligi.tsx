import type { ReactNode } from "react";
import { useLocation } from "react-router";
import { sayfaEtiketi } from "../cerceve/menu";
import stil from "./SayfaBasligi.module.css";

type Props = {
  baslik: string;
  /** Başlığın altındaki kısa açıklama. */
  children?: ReactNode;
  /** Sağdaki eylemler (düğmeler); dar ekranda başlığın altına iner. */
  eylemler?: ReactNode;
  /** Başlığın üstündeki küçük etiket. Verilmezse adresin menü grubu ("OKUL", "PROGRAM" …). */
  etiket?: string;
};

/**
 * Sayfa başlığı: ince ve sade. Üstte küçük, soluk bir etiket (sayfanın menüdeki bölümü), altında
 * sayfanın tek <h1>'i ve kısa açıklama, sağda varsa eylemler. Bant ya da renkli kutu yok: sayfanın
 * asıl içeriği öne çıkar.
 */
export function SayfaBasligi({ baslik, children, eylemler, etiket }: Props) {
  const yol = useLocation().pathname;
  const ust = etiket ?? sayfaEtiketi(yol);
  return (
    <div className={stil.alan}>
      <div className={stil.metin}>
        {ust && <p className={stil.etiket}>{ust}</p>}
        <h1 className={stil.baslik}>{baslik}</h1>
        {children && <p className={stil.aciklama}>{children}</p>}
      </div>
      {eylemler && <div className={stil.eylemler}>{eylemler}</div>}
    </div>
  );
}
