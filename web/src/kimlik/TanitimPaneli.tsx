import { CalendarCheck, ShieldCheck, Zap } from "lucide-react";
import type { CSSProperties } from "react";
import stil from "./Giris.module.css";

type Ders = "mat" | "fizik" | "turkce" | "tarih" | "ing" | "kimya";

const DERS_ADLARI: Record<Ders, string> = {
  mat: "Mat",
  fizik: "Fizik",
  turkce: "Türkçe",
  tarih: "Tarih",
  ing: "İng",
  kimya: "Kimya",
};

const GUNLER = ["PZT", "SAL", "ÇAR", "PER", "CUM"];

// Satır = ders saati, sütun = gün; null = boş saat (kesik çizgili).
const CIZELGE: (Ders | null)[][] = [
  ["mat", "turkce", "fizik", "mat", "ing"],
  ["mat", "turkce", "fizik", "kimya", "ing"],
  ["tarih", "ing", null, "kimya", "turkce"],
  ["fizik", "mat", "tarih", "turkce", null],
  [null, "kimya", "mat", null, "tarih"],
];

// Kartların düşme sırası karışık ama sabit: her yenilemede aynı görünsün, testte de aynı olsun.
// Hücre dizini (satır * 5 + sütun) -> kaçıncı düştüğü.
const SIRA = [11, 3, 17, 7, 0, 14, 5, 19, 9, 1, 13, 16, -1, 4, 20, 8, 2, 12, 18, -1, -1, 15, 6, -1, 10];
const ILK_DUSUS_SN = 0.3;
const DUSUS_ARALIGI_SN = 0.22;

const OZELLIKLER = [
  { ikon: ShieldCheck, baslik: "Çakışmasız program", metin: "Öğretmen ve şube asla iki derse aynı anda düşmez." },
  { ikon: Zap, baslik: "Saniyeler içinde hazır", metin: "Günlerce elle uğraşmak yerine tek tıkla üretin." },
  { ikon: CalendarCheck, baslik: "Öğretmenlere boş gün", metin: "Dersleri az güne toplayıp boş gün bırakın." },
];

/**
 * Giriş sayfasının sağındaki tanıtım. Örnek çizelgenin kartları sırayla yukarıdan düşüp
 * hücrelerine yerleşir, çizelge dolunca solar ve döngü baştan başlar. Bütün hareket CSS'tedir
 * (Giris.module.css, `--zaman`); kart başına yalnızca düşme anı (`--d`) verilir. Süstür: ekran
 * okuyucuya tablo yerine tek cümlelik açıklama okunur.
 */
export function TanitimPaneli() {
  return (
    <aside className={stil.panel} aria-label="Çizelge'nin tanıtımı">
      {/* İçerik grubu panelin içinde ortalanır; yazılar soldan hizalı kalır. */}
      <div className={stil.panelIcerik}>
        <p className={stil.etiket}>
          <span className={stil.nokta} aria-hidden="true" />
          PROGRAM HAZIRLANIYOR
        </p>
        <h2 className={stil.panelBasligi}>Dersleri girin, çakışmasız haftalık program saniyeler içinde yerleşsin.</h2>

        <figure className={stil.ornek}>
          <figcaption className={stil.ornekBasligi}>
            <span>
              <strong>9-A Şubesi</strong> · Haftalık program
            </span>
            <span className={stil.rozet}>Çakışma yok</span>
          </figcaption>
          <div className={stil.izgara} role="img" aria-label="Örnek haftalık program: 5 gün, günde 5 ders saati, çakışma yok">
            <span aria-hidden="true" />
            {GUNLER.map((g) => (
              <span key={g} className={stil.gun} aria-hidden="true">
                {g}
              </span>
            ))}
            {CIZELGE.map((satir, s) => [
              <span key={`s${s}`} className={stil.saat} aria-hidden="true">
                {s + 1}
              </span>,
              ...satir.map((ders, g) => {
                const hucre = s * 5 + g;
                if (!ders) return <span key={hucre} className={stil.bosHucre} aria-hidden="true" />;
                const d = ILK_DUSUS_SN + (SIRA[hucre] ?? 0) * DUSUS_ARALIGI_SN;
                return (
                  <span key={hucre} className={stil.hucre} aria-hidden="true">
                    <span
                      className={stil.dersKarti}
                      data-ders={ders}
                      style={{ "--d": d.toFixed(2) } as CSSProperties}
                    >
                      {DERS_ADLARI[ders]}
                    </span>
                  </span>
                );
              }),
            ])}
          </div>
        </figure>

        <ul className={stil.ozellikler}>
          {OZELLIKLER.map(({ ikon: Ikon, baslik, metin }) => (
            <li key={baslik}>
              <span className={stil.ozellikIkonu} aria-hidden="true">
                <Ikon strokeWidth={1.75} />
              </span>
              <strong>{baslik}</strong>
              <span>{metin}</span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
