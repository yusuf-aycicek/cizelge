import type { ReactNode } from "react";
import stil from "./Tablo.module.css";

export type Sutun<T> = {
  baslik: string;
  hucre: (satir: T) => ReactNode;
  hizala?: "sol" | "sag";
  /** Sütun başlığı yalnızca ekran okuyucuya görünsün (ör. işlem düğmeleri sütunu). */
  baslikGizli?: boolean;
  /** Başlık hücresinde metin yerine bir öğe (ör. "tümünü seç" kutusu). `baslik` yine anahtardır. */
  baslikIcerik?: ReactNode;
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
  /** Satıra CSS sınıfı (ör. öğretmeni seçilmemiş satırı vurgulamak için). */
  satirSinifi?: (satir: T) => string | undefined;
  /** Silinmekte olan satırların anahtarları: kalkmadan önce çıkış animasyonu oynar. */
  cikanlar?: ReadonlySet<string>;
};

/**
 * Ortak tablo. Doğal <table>: ekran okuyucular satır ve sütun başlıklarını okur.
 *
 * Genel (generic) bir bileşendir: `T` satırın tipidir. `<Tablo<Ogretmen> ... />` yazıldığında
 * TypeScript, `hucre` fonksiyonlarının bir öğretmen aldığını bilir.
 *
 * Dar kutuda (telefon) her satır bir karta dönüşür: hücre alt alta, solunda sütunun adı
 * (`data-etiket`, CSS). Kartta tablo öğeleri `display: block` olur; bazı tarayıcılar o zaman tablo
 * anlamını ekran okuyucudan siler, bu yüzden roller (`role="row"`, `"cell"`) açıkça yazılır.
 */
export function Tablo<T>({
  baslik,
  baslikGorunur = false,
  sutunlar,
  satirlar,
  satirAnahtari,
  bosMesaj,
  satirSinifi,
  cikanlar,
}: Props<T>) {
  return (
    <div className={stil.kutu}>
      <table className={stil.tablo} role="table">
        <caption className={baslikGorunur ? stil.baslik : "gorunmez"}>{baslik}</caption>
        <thead>
          <tr role="row">
            {sutunlar.map((s) => (
              <th key={s.baslik} scope="col" role="columnheader" className={s.hizala === "sag" ? stil.sag : undefined}>
                {s.baslikIcerik ?? <span className={s.baslikGizli ? "gorunmez" : undefined}>{s.baslik}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {satirlar.length === 0 ? (
            <tr role="row">
              <td colSpan={sutunlar.length} role="cell" className={stil.bos}>
                {bosMesaj ?? "Henüz kayıt yok."}
              </td>
            </tr>
          ) : (
            // `key`: React'in her satırı tanıması için. Dizin (index) değil, kalıcı kimlik
            // kullanılır; yoksa satır silinince ya da sıralanınca durum yanlış satıra kayar.
            satirlar.map((satir) => (
              <tr
                key={satirAnahtari(satir)}
                role="row"
                className={[satirSinifi?.(satir), cikanlar?.has(satirAnahtari(satir)) ? stil.cikiyor : ""]
                  .filter(Boolean)
                  .join(" ") || undefined}
              >
                {sutunlar.map((s) => (
                  <td key={s.baslik} role="cell" data-etiket={s.baslikGizli ? undefined : s.baslik}
                    className={s.hizala === "sag" ? stil.sag : undefined}>
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
