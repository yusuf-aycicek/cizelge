import type { CSSProperties, ReactNode } from "react";
import { useDarAlan } from "../bilesenler/darAlan";
import stil from "./Ders.module.css";
import { isaretKarakteri } from "./isaret";

type Props = {
  ad: string;
  /** Dersin rengi (#rrggbb, API'nin paletinden). Yoksa nötr çip. */
  renk?: string | null;
  /**
   * Dar alanda (ör. çizelge hücresi) ad sığmazsa gösterilecek kısa ad ("TDE"). Verilirse çip
   * bulunduğu alanın genişliğini ölçer; tam ad üzerine gelince ve ekran okuyucuda kalır.
   */
  kisaAd?: string | null;
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
export function DersCipi({ ad, renk, kisaAd, isaret = 0 }: Props) {
  if (kisaAd && kisaAd !== ad) return <SigdirilanCip ad={ad} kisaAd={kisaAd} renk={renk} isaret={isaret} />;
  return <Cip renk={renk} isaret={isaret}>{ad}</Cip>;
}

function Cip({ renk, isaret, title, children }: { renk?: string | null; isaret: number; title?: string; children: ReactNode }) {
  const ozel = renk ? ({ "--ders-rengi": renk } as CSSProperties) : undefined;
  return (
    <span className={stil.cip} style={ozel} title={title}>
      {isaret > 0 && (
        <span aria-hidden="true" className={stil.isaret}>
          {isaretKarakteri(isaret)}
        </span>
      )}
      {children}
    </span>
  );
}

/** Çip bir kutunun içinde: kutu alanın genişliğini verir, çip ise adın doğal genişliğini. */
function SigdirilanCip({ ad, kisaAd, renk, isaret }: { ad: string; kisaAd: string; renk?: string | null; isaret: number }) {
  const { kutu, metin, dar } = useDarAlan<HTMLSpanElement>(ad);
  return (
    <span ref={kutu} className={stil.cipKutusu}>
      <span ref={metin} className={dar ? stil.olcuSinirli : stil.olcu}>
        <Cip renk={renk} isaret={isaret} title={dar ? ad : undefined}>
          {dar ? (
            <>
              <span aria-hidden="true">{kisaAd}</span>
              <span className="gorunmez">{ad}</span>
            </>
          ) : (
            ad
          )}
        </Cip>
      </span>
    </span>
  );
}
