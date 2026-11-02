import { useRef, type KeyboardEvent } from "react";
import stil from "./CipSecici.module.css";

export type CipSecenegi = { id: string; ad: string };

type Props = {
  /** Grubun erişilebilir adı, ör. "Şube". */
  etiket: string;
  secenekler: readonly CipSecenegi[];
  secili: string;
  onSec: (id: string) => void;
};

/**
 * Çiplerden tek seçim (WAI-ARIA "radio group" deseni): açılır liste yerine bütün seçenekler
 * görünür, biri seçilidir.
 * - `role="radiogroup"` içinde `role="radio"` düğmeler; seçili olan `aria-checked="true"`;
 * - klavye: Tab ile gruba bir kez girilir (yalnızca seçili çip odaklanabilir), oklar, Home ve
 *   End ile çipler arasında geçilir ve geçilen çip seçilir (radyo düğmeleri gibi).
 * Çok seçenekte (ör. 80 öğretmen) grup kendi içinde kayar; odaklanan çip görünür alana gelir.
 */
export function CipSecici({ etiket, secenekler, secili, onSec }: Props) {
  const dugmeler = useRef<Map<string, HTMLButtonElement>>(new Map());

  function tus(olay: KeyboardEvent, sira: number) {
    const son = secenekler.length - 1;
    const hedef = { ArrowRight: sira + 1, ArrowDown: sira + 1, ArrowLeft: sira - 1, ArrowUp: sira - 1, Home: 0, End: son }[olay.key];
    if (hedef === undefined) return;
    olay.preventDefault();
    const yeni = secenekler[(hedef + secenekler.length) % secenekler.length];
    if (!yeni) return;
    onSec(yeni.id);
    dugmeler.current.get(yeni.id)?.focus();
  }

  return (
    <div role="radiogroup" aria-label={etiket} className={stil.grup}>
      {secenekler.map((s, sira) => (
        <button
          key={s.id}
          ref={(d) => {
            if (d) dugmeler.current.set(s.id, d);
            else dugmeler.current.delete(s.id);
          }}
          type="button"
          role="radio"
          aria-checked={s.id === secili}
          tabIndex={s.id === secili ? 0 : -1}
          className={stil.cip}
          onClick={() => onSec(s.id)}
          onKeyDown={(o) => tus(o, sira)}
        >
          {s.ad}
        </button>
      ))}
    </div>
  );
}
