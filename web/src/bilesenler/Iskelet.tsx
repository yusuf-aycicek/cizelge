import stil from "./Iskelet.module.css";

type Props = {
  /** Kaç satırlık yer tutucu. */
  satir?: number;
  /** Kart görünümünde mi (ör. okul ayarları bölümleri) yoksa düz mü (tablo yerine). */
  kart?: boolean;
  /** Ekran okuyucunun duyacağı metin. */
  etiket?: string;
};

/**
 * İskelet görünüm: veri gelene kadar sayfanın yerleşimini gri, hafifçe parlayan çizgilerle
 * gösterir. "Yükleniyor..." yazısından farkı: içerik gelince sayfa zıplamaz, kullanıcı neyin
 * geleceğini önceden görür. Çizgiler yalnızca görseldir (aria-hidden); ekran okuyucu
 * `role="status"` içindeki metni duyar.
 */
export function Iskelet({ satir = 4, kart = false, etiket = "Yükleniyor..." }: Props) {
  return (
    <div role="status" className={kart ? `${stil.iskelet} ${stil.kart}` : stil.iskelet}>
      <span className="gorunmez">{etiket}</span>
      <div className={`${stil.cizgi} ${stil.baslik}`} aria-hidden="true" />
      {Array.from({ length: satir }, (_, i) => (
        <div key={i} className={stil.cizgi} style={{ width: `${92 - (i % 3) * 14}%` }} aria-hidden="true" />
      ))}
    </div>
  );
}
