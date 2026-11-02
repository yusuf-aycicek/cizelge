import { Moon, Sun } from "lucide-react";
import { useTema } from "../stil/tema";
import stil from "./TemaDugmesi.module.css";

/**
 * Açık / koyu tema düğmesi. İkon temanın tersini gösterir (açıkta ay: "koyuya geç"); tema
 * değişince ikon dönerek yer değiştirir (`key` yeni ikonu yeniden takar, animasyonu o oynatır).
 * Adı yapacağı işi söyler; aria-pressed yok, çünkü iki durumlu bir anahtar değil, bir eylem.
 */
export function TemaDugmesi({ className }: { className?: string }) {
  const [tema, degistir] = useTema();
  const koyu = tema === "koyu";
  return (
    <button
      type="button"
      className={[stil.dugme, className].filter(Boolean).join(" ")}
      onClick={degistir}
      aria-label={koyu ? "Açık temaya geç" : "Koyu temaya geç"}
      title={koyu ? "Açık tema" : "Koyu tema"}
    >
      <span key={tema} className={stil.ikon} aria-hidden="true">
        {koyu ? <Sun /> : <Moon />}
      </span>
    </button>
  );
}
