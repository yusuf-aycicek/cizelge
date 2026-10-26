import { useSunucuGecikiyor } from "../api/uyanma";
import stil from "./SunucuUyaniyor.module.css";

/** Sunucu yanıt vermekte gecikirken sayfanın üstünde görünen bilgi (api/uyanma.ts). */
export function SunucuUyaniyor() {
  if (!useSunucuGecikiyor()) return null;
  return (
    <div className={stil.bant} role="status">
      <span className={stil.nokta} aria-hidden="true" />
      Sunucu uyanıyor, ilk açılış bir dakika kadar sürebilir. Sayfayı kapatmayın.
    </div>
  );
}
