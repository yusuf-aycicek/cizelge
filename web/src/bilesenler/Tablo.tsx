import type { ReactNode } from "react";
import stil from "./Tablo.module.css";

export type Sutun<T> = {
  baslik: string;
  hucre: (satir: T) => ReactNode;
  hizala?: "sol" | "sag";
  /** Sütun başlığı yalnızca ekran okuyucuya görünsün (ör. işlem düğmeleri sütunu). */
  baslikGizli?: boolean;
};

type Props<T> = {
  /** Tablonun adı. Ekran okuyucular tabloyu bu adla duyurur; `baslikGorunur` değilse gizlidir. */
  baslik: string;
  baslikGorunur?: boolean;
  sutunlar: Sutun<T>[];
  satirlar: T[];
  /** Her satırın kalıcı anahtarı (genellikle kimlik). React satırları bununla tanır. */
  satirAnahtari: (satir: T) => string;
  bosMesaj?: ReactNode;
};

/**
 * Ortak tablo. Doğal <table>: ekran okuyucular satır ve sütun başlıklarını okur.
 *
 * Genel (generic) bir bileşendir: `T` satırın tipidir. `<Tablo<Ogretmen> ... />` yazıldığında
 * TypeScript, `hucre` fonksiyonlarının bir öğretmen aldığını bilir.
 *
 * Dar ekranda tablo kendi kutusunda yatay kayar; sayfa kaymaz.
 */
export function Tablo<T>({ baslik, baslikGorunur = false, sutunlar, satirlar, satirAnahtari, bosMesaj }: Props<T>) {
  return (
    <div className={stil.kutu}>
      <table className={stil.tablo}>
        <caption className={baslikGorunur ? stil.baslik : "gorunmez"}>{baslik}</caption>
        <thead>
          <tr>
            {sutunlar.map((s) => (
              <th key={s.baslik} scope="col" className={s.hizala === "sag" ? stil.sag : undefined}>
                <span className={s.baslikGizli ? "gorunmez" : undefined}>{s.baslik}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {satirlar.length === 0 ? (
            <tr>
              <td colSpan={sutunlar.length} className={stil.bos}>
                {bosMesaj ?? "Henüz kayıt yok."}
              </td>
            </tr>
          ) : (
            // `key`: React'in her satırı tanıması için. Dizin (index) değil, kalıcı kimlik
            // kullanılır; yoksa satır silinince ya da sıralanınca durum yanlış satıra kayar.
            satirlar.map((satir) => (
              <tr key={satirAnahtari(satir)}>
                {sutunlar.map((s) => (
                  <td key={s.baslik} className={s.hizala === "sag" ? stil.sag : undefined}>
                    {s.hucre(satir)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
