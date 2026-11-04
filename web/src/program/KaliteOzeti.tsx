import { CircleAlert, CircleCheck } from "lucide-react";
import { cozumAciklamasi, kaliteMaddeleri, sureMetni, type Program } from "./aciklama";
import stil from "./Program.module.css";

/** Programın kalite özeti, sade Türkçe: iyi olanlar yeşil onaylı, iyileştirilebilecekler sarı. */
export function KaliteOzeti({ program, baslikDuzeyi = 2 }: { program: Program; baslikDuzeyi?: 2 | 3 }) {
  const maddeler = kaliteMaddeleri(program.olcumler, Boolean(program.temel_program_id));
  if (maddeler.length === 0) return null;
  const Baslik = baslikDuzeyi === 2 ? "h2" : "h3";
  // Elle düzeltilmiş programda çözücünün "en iyisi" sözü artık geçerli değil; ölçüler düzeltilmiş hâlin.
  const aciklama = program.elle_duzeltme
    ? `Program elle düzeltildi (${program.elle_duzeltme} değişiklik); ölçüler düzeltilmiş hâline göredir.`
    : cozumAciklamasi(program.cozum_durumu);
  return (
    <section aria-labelledby={`kalite-${program.id}`} className={stil.kalite}>
      <Baslik id={`kalite-${program.id}`}>Programın kalitesi</Baslik>
      {aciklama && (
        <p className={stil.kaliteAciklama}>
          {aciklama}
          {program.sure_sn != null && !program.elle_duzeltme && ` Üretim ${sureMetni(program.sure_sn)} sürdü.`}
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
      <BosGunNotlari notlar={(program.notlar ?? []).filter((n) => n.tur === "bos_gun")} />
    </section>
  );
}

/**
 * Boş gün hedefi tutmayan öğretmenler, kişi kişi ve nedeniyle ("Hasan Şahin: hedef 4 boş gündü,
 * 3 verilebildi. ..."). Notlar üretim anında çözücünün `kalite.bos_gun_notlari`ndan gelir. Çoksa
 * (gerçekçi okulda öğretmenlerin yarısı) kapalı başlar, başlığı sayıyı söyler.
 */
function BosGunNotlari({ notlar }: { notlar: readonly { mesaj: string }[] }) {
  if (notlar.length === 0) return null;
  return (
    <details className={stil.kaliteNotlari} open={notlar.length <= 5}>
      <summary>Boş gün hedefi tutmayan {notlar.length} öğretmen</summary>
      <ul>
        {notlar.map((n) => (
          <li key={n.mesaj}>{n.mesaj}</li>
        ))}
      </ul>
      <p className={stil.kaliteAciklama}>
        Boş gün esnek bir kuraldır; önemini Okul ayarları &gt; Kurallar bölümünden artırabilirsiniz.
      </p>
    </details>
  );
}
