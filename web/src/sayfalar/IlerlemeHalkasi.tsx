import type { CSSProperties } from "react";
import stil from "./Pano.module.css";

const YARICAP = 52;
const CEVRE = 2 * Math.PI * YARICAP;

type Props = { yuzde: number; tamamlanan: number; gereken: number };

/**
 * Kurulum ilerleme halkası. SVG çember; dolu kısmı `stroke-dashoffset` ile çizilir ve açılışta
 * boştan dolarak gelir (CSS animasyonu; hareket azaltılmışsa doğrudan son hali).
 *
 * Ekran okuyucu için tek bir resimdir (`role="img"`) ve adı sonucu söyler: "Kurulum: 5 adımdan 4'ü
 * tamam". Ortadaki yüzde yalnızca görseldir.
 */
export function IlerlemeHalkasi({ yuzde, tamamlanan, gereken }: Props) {
  const hedef = CEVRE * (1 - yuzde / 100);
  const degiskenler = { "--cevre": `${CEVRE}`, "--hedef": `${hedef}` } as CSSProperties;
  return (
    <div className={stil.halka} role="img" aria-label={`Kurulum: ${gereken} adımdan ${tamamlanan} tanesi tamam`}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className={stil.halkaZemin} cx="60" cy="60" r={YARICAP} />
        <circle
          className={yuzde === 100 ? `${stil.halkaDolu} ${stil.halkaTamam}` : stil.halkaDolu}
          cx="60"
          cy="60"
          r={YARICAP}
          strokeDasharray={CEVRE}
          strokeDashoffset={hedef}
          style={degiskenler}
        />
      </svg>
      <span className={stil.halkaMetni} aria-hidden="true">
        <strong>%{yuzde}</strong>
        <span>
          {tamamlanan}/{gereken} adım
        </span>
      </span>
    </div>
  );
}
