import { useRef, type KeyboardEvent, type ReactNode } from "react";
import stil from "./Sekmeler.module.css";

export type Sekme<A extends string> = { anahtar: A; ad: string };

type Props<A extends string> = {
  /** Sekme grubunun erişilebilir adı, ör. "Görünüm". */
  etiket: string;
  sekmeler: readonly Sekme<A>[];
  secili: A;
  onSec: (anahtar: A) => void;
  /** Sayfada benzersiz önek: sekme ve panel kimlikleri bundan üretilir. */
  idOneki: string;
  /** "cizgi": altı çizili sekmeler (varsayılan); "segment": hap biçimli bölümlü anahtar. */
  bicim?: "cizgi" | "segment";
  /** Seçili sekmenin paneli. */
  children: ReactNode;
};

/**
 * Sekmeler (WAI-ARIA "tabs" deseni):
 * - `role="tablist"` içinde `role="tab"` düğmeleri; seçili olan `aria-selected="true"`;
 * - panel `role="tabpanel"`, seçili sekmenin adıyla adlandırılır (`aria-labelledby`);
 * - klavye: Tab ile sekme grubuna bir kez girilir (yalnızca seçili sekme odaklanabilir,
 *   `tabIndex`), sol/sağ ok, Home ve End ile sekmeler arasında geçilir ve geçilen sekme seçilir.
 *
 * Bileşen hangi sekmenin seçili olduğunu kendisi tutmaz: `secili` ve `onSec` dışarıdan gelir
 * (kontrollü bileşen). Böylece seçimi sayfa tutar ve başka yerden de değiştirebilir (ör. "bu
 * öğretmenin dersleri" bağlantısı şube sekmesine geçer).
 */
export function Sekmeler<A extends string>({ etiket, sekmeler, secili, onSec, idOneki, bicim = "cizgi", children }: Props<A>) {
  const dugmeler = useRef<Map<A, HTMLButtonElement>>(new Map());

  function tus(olay: KeyboardEvent, sira: number) {
    const hedef = { ArrowRight: sira + 1, ArrowLeft: sira - 1, Home: 0, End: sekmeler.length - 1 }[olay.key];
    if (hedef === undefined) return;
    olay.preventDefault();
    const yeni = sekmeler[(hedef + sekmeler.length) % sekmeler.length];
    if (!yeni) return;
    onSec(yeni.anahtar);
    dugmeler.current.get(yeni.anahtar)?.focus();
  }

  return (
    <>
      <div role="tablist" aria-label={etiket} className={bicim === "segment" ? stil.segment : stil.liste}>
        {sekmeler.map((s, sira) => (
          <button
            key={s.anahtar}
            ref={(d) => {
              if (d) dugmeler.current.set(s.anahtar, d);
              else dugmeler.current.delete(s.anahtar);
            }}
            type="button"
            role="tab"
            id={`${idOneki}-${s.anahtar}`}
            aria-selected={s.anahtar === secili}
            aria-controls={`${idOneki}-panel`}
            tabIndex={s.anahtar === secili ? 0 : -1}
            className={stil.sekme}
            onClick={() => onSec(s.anahtar)}
            onKeyDown={(o) => tus(o, sira)}
          >
            {s.ad}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${idOneki}-panel`} aria-labelledby={`${idOneki}-${secili}`} className={stil.panel}>
        {/* key: sekme değişince içerik yeniden kurulur ve solarak gelir (CSS). */}
        <div key={secili} className={stil.icerik}>
          {children}
        </div>
      </div>
    </>
  );
}
