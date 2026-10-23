import { CircleAlert, CircleCheck } from "lucide-react";
import { cozumAciklamasi, kaliteMaddeleri, type Program } from "./aciklama";
import stil from "./Program.module.css";

/** Programın kalite özeti, sade Türkçe: iyi olanlar yeşil onaylı, iyileştirilebilecekler sarı. */
export function KaliteOzeti({ program, baslikDuzeyi = 2 }: { program: Program; baslikDuzeyi?: 2 | 3 }) {
  const maddeler = kaliteMaddeleri(program.olcumler, Boolean(program.temel_program_id));
  if (maddeler.length === 0) return null;
  const Baslik = baslikDuzeyi === 2 ? "h2" : "h3";
  const aciklama = cozumAciklamasi(program.cozum_durumu);
  return (
    <section aria-labelledby={`kalite-${program.id}`} className={stil.kalite}>
      <Baslik id={`kalite-${program.id}`}>Programın kalitesi</Baslik>
      {aciklama && (
        <p className={stil.kaliteAciklama}>
          {aciklama}
          {program.sure_sn != null && ` Üretim ${Math.round(program.sure_sn)} saniye sürdü.`}
        </p>
      )}
      <ul className={stil.kaliteListesi}>
        {maddeler.map((m) => (
          <li key={m.anahtar} className={m.iyi ? stil.kaliteIyi : stil.kaliteUyari}>
            {m.iyi ? <CircleCheck aria-hidden="true" /> : <CircleAlert aria-hidden="true" />}
            <span>{m.metin}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
