import type { CSSProperties } from "react";
import stil from "./Ders.module.css";
import { isaretKarakteri } from "./isaret";

type Props = {
  ad: string;
  /** Dersin rengi (#rrggbb, API'nin paletinden). Yoksa nötr çip. */
  renk?: string | null;
  /** Kısa adı göstermek için (ör. çizelge hücresi): "MAT". */
  kisa?: boolean;
  /** Aynı rengi paylaşan derslerdeki sırası (`dersIsaretleri`); 0 ya da yoksa işaret yok. */
  isaret?: number;
};

/**
 * Ders çipi: dersin rengi zemin, yazı beyaz. Aynı ders her ekranda aynı renkte görünür (ders
 * listesi, ders dağılımı, şablon, çizelge). Paletteki her rengin beyaz yazıyla en az 4.5:1
 * kontrastlı olduğunu API testi denetler (api/tests/test_ders_renkleri.py).
 *
 * Renk tekrar ediyorsa (ör. 20'den fazla ders) çipin başında küçük bir işaret (◆ ▲ ●) aynı renkli
 * dersleri ayırır. İşaret yalnızca görseldir; ders adı zaten yazılıdır.
 *
 * Renk bir CSS değişkeni olarak verilir (`--ders-rengi`); stil yalnızca belirteçleri ve bu
 * değişkeni kullanır.
 */
export function DersCipi({ ad, renk, kisa = false, isaret = 0 }: Props) {
  const ozel = renk ? ({ "--ders-rengi": renk } as CSSProperties) : undefined;
  return (
    <span className={stil.cip} style={ozel} title={kisa ? ad : undefined}>
      {isaret > 0 && (
        <span aria-hidden="true" className={stil.isaret}>
          {isaretKarakteri(isaret)}
        </span>
      )}
      {ad}
    </span>
  );
}
