import type { CSSProperties } from "react";
import stil from "./SuzulenKartlar.module.css";

/**
 * Giriş ekranının arka planı: alttan üste süzülen soluk ders kartları. Yalnızca süs: ekran
 * okuyucudan gizli, tıklanmaz. Hareket tamamen CSS'tir ve ekran kartında çalışır (transform ve
 * opaklık); yolun uzunluğu katmanın gerçek yüksekliğidir (SuzulenKartlar.module.css "ray").
 */

export const KART_YAZILARI = [
  "Matematik", "Veri Yapıları", "Fizik", "Amfi 2", "Türkçe", "Algoritmalar", "Kimya", "Lab 3",
  "Tarih", "İngilizce", "Diferansiyel", "Biyoloji", "9-A", "Yazılım Müh. 2", "Edebiyat", "Dr. Kaya",
];
export const KART_SAYISI = 22;
const TELEFON_KART_SAYISI = 10; // 720 px altında; fazlası CSS ile gizlenir

// Başlangıç açıları; kart yolun sonunda ters yöne döner. CSS'te her biri için sabit anahtar kare var.
const DONUSLER = [
  { aci: -10, sinif: stil.donEksi10 }, { aci: 6, sinif: stil.don6 }, { aci: -3, sinif: stil.donEksi3 },
  { aci: 10, sinif: stil.don10 }, { aci: -6, sinif: stil.donEksi6 }, { aci: 3, sinif: stil.don3 },
];

// i. kartın yatay yeri: 7, 22 ile aralarında asal olduğu için (i * 7) mod 22 her yeri bir kez verir;
// art arda gelen kartlar ekranın uzak yerlerine düşer.
export const KARTLAR = Array.from({ length: KART_SAYISI }, (_, i) => {
  const { aci, sinif } = DONUSLER[i % DONUSLER.length] ?? { aci: 0, sinif: "" };
  return {
    yazi: KART_YAZILARI[i % KART_YAZILARI.length],
    sinif,
    stil: {
      "--x": ((i * 7) % KART_SAYISI) / (KART_SAYISI - 1),
      "--a": `${aci}deg`,
      // Eşit aralıklı, negatif gecikme: sayfa açılır açılmaz yolun her yerinde bir kart vardır.
      "--p": (i + 0.5) / KART_SAYISI,
      "--p-tel": (Math.min(i, TELEFON_KART_SAYISI - 1) + 0.5) / TELEFON_KART_SAYISI,
    } as CSSProperties,
  };
});

export function SuzulenKartlar() {
  return (
    <div className={stil.katman} aria-hidden="true" data-testid="suzulen-kartlar">
      {KARTLAR.map((k, i) => (
        <div key={i} className={stil.ray} style={k.stil}>
          <span className={`${stil.kart} ${k.sinif}`}>{k.yazi}</span>
        </div>
      ))}
    </div>
  );
}
