import type { CSSProperties } from "react";
import stil from "./Ders.module.css";

type Props = {
  ad: string;
  /** Dersin rengi (#rrggbb, API'nin paletinden). Yoksa nötr çip. */
  renk?: string | null;
  /** Kısa adı göstermek için (ör. çizelge hücresi): "MAT". */
  kisa?: boolean;
};

/**
 * Ders çipi: dersin rengi zemin, yazı beyaz. Aynı ders her ekranda aynı renkte görünür (ders
 * listesi, ders dağılımı, şablon, ileride çizelge). Paletteki her rengin beyaz yazıyla en az 4.5:1
 * kontrastlı olduğunu API testi denetler (api/tests/test_ders_renkleri.py).
 *
 * Renk bir CSS değişkeni olarak verilir (`--ders-rengi`); stil yalnızca belirteçleri ve bu
 * değişkeni kullanır.
 */
export function DersCipi({ ad, renk, kisa = false }: Props) {
  const ozel = renk ? ({ "--ders-rengi": renk } as CSSProperties) : undefined;
  return (
    <span className={stil.cip} style={ozel} title={kisa ? ad : undefined}>
      {ad}
    </span>
  );
}
