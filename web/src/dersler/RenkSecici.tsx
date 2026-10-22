import { useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useRef, type CSSProperties } from "react";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import stil from "./Ders.module.css";

export const RENKLER_ANAHTARI = ["ders-renkleri"] as const;

/** API'nin ders renk paleti. Değişmez: önbellekte süresiz taze sayılır. */
export function useDersRenkleri() {
  return useQuery({
    queryKey: RENKLER_ANAHTARI,
    queryFn: () => cagir(api.GET("/api/ders-renkleri")),
    staleTime: Infinity,
  });
}

const renkStili = (renk: string) => ({ "--ders-rengi": renk }) as CSSProperties;

type Props = {
  /** Erişilebilir ad, ör. "Matematik dersinin rengi". */
  etiket: string;
  deger: string;
  onDegis: (renk: string) => void;
  disabled?: boolean;
};

/**
 * Ders rengi seçici. Düğme (`<summary>`) seçili rengi ve adını gösterir; açılınca palet bir
 * radyo grubu olarak gelir (her renk örneğinin adı ekran okuyucuya söylenir: "Kiremit"). Seçince
 * kapanır. `<details>`: açma/kapama, klavye (Enter, boşluk) ve `aria-expanded` tarayıcıdan gelir.
 */
export function RenkSecici({ etiket, deger, onDegis, disabled }: Props) {
  const renkler = useDersRenkleri().data ?? [];
  const kutu = useRef<HTMLDetailsElement>(null);
  const secili = renkler.find((r) => r.renk === deger);

  return (
    <details ref={kutu} className={stil.secici}>
      <summary aria-label={`${etiket}: ${secili?.ad ?? deger}`} aria-disabled={disabled || undefined}>
        <span className={stil.ornek} style={renkStili(deger)} aria-hidden="true" />
        <span aria-hidden="true">{secili?.ad ?? "Renk"}</span>
      </summary>
      <div role="radiogroup" aria-label={etiket} className={stil.pano}>
        {renkler.map((r) => (
          <button
            key={r.renk}
            type="button"
            role="radio"
            aria-checked={r.renk === deger}
            aria-label={r.ad}
            title={r.ad}
            disabled={disabled}
            className={stil.secenek}
            style={renkStili(r.renk)}
            onClick={() => {
              if (kutu.current) kutu.current.open = false;
              if (r.renk !== deger) onDegis(r.renk);
            }}
          >
            {r.renk === deger && <Check aria-hidden="true" />}
          </button>
        ))}
      </div>
    </details>
  );
}
