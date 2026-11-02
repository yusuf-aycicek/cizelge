import type { ReactNode } from "react";
import stil from "./Illustrasyon.module.css";

export type IllustrasyonTuru = "ogretmen" | "sinif" | "ders" | "takvim" | "arama" | "yayin";

/**
 * Boş durumlar için sade çizimler. Dışarıdan görsel yok: satır içi SVG. Renkler SVG özniteliğinde
 * değil CSS sınıflarındadır, yani belirteçlerden gelir (öznitelikte CSS değişkeni güvenilir
 * çalışmaz). Yalnızca süstür (aria-hidden): yanındaki başlık ve metin ne yapılacağını söyler.
 */
export function Illustrasyon({ tur, kucuk = false }: { tur: IllustrasyonTuru; kucuk?: boolean }) {
  return (
    <svg className={kucuk ? `${stil.cizim} ${stil.kucuk}` : stil.cizim} viewBox="0 0 200 140" aria-hidden="true" focusable="false">
      {/* yumuşak zemin lekesi ve süs noktaları (hepsinde ortak) */}
      <path className={stil.zemin} d="M38 104c-22-14-20-52 6-68 24-15 44-4 66-12 24-8 52 0 60 24 9 26-4 52-30 62-30 12-74 8-102-6z" />
      <circle className={stil.vurgu} cx="34" cy="30" r="4" />
      <circle className={stil.ikincil} cx="172" cy="26" r="3" />
      <circle className={stil.ikincil} cx="180" cy="104" r="5" />
      {CIZIMLER[tur]}
    </svg>
  );
}

const CIZIMLER: Record<IllustrasyonTuru, ReactNode> = {
  // Kara tahta önünde bir öğretmen.
  ogretmen: (
    <>
      <rect className={stil.koyu} x="92" y="34" width="70" height="46" rx="6" />
      <path className={stil.tebesir} d="M102 48h34M102 58h46M102 68h24" />
      <circle className={stil.acik} cx="64" cy="58" r="15" />
      <circle className={stil.vurgu} cx="64" cy="56" r="11" />
      <path className={stil.vurgu} d="M40 112c0-18 11-30 24-30s24 12 24 30z" />
      <path className={stil.cizgi} d="M84 92l14-12" />
    </>
  ),
  // Sıralar ve kapı: bir şube.
  sinif: (
    <>
      <rect className={stil.acik} x="46" y="30" width="108" height="78" rx="8" />
      <rect className={stil.koyu} x="58" y="40" width="44" height="16" rx="3" />
      <rect className={stil.vurgu} x="58" y="66" width="18" height="10" rx="3" />
      <rect className={stil.vurgu} x="84" y="66" width="18" height="10" rx="3" />
      <rect className={stil.ikincil} x="58" y="84" width="18" height="10" rx="3" />
      <rect className={stil.ikincil} x="84" y="84" width="18" height="10" rx="3" />
      <rect className={stil.zeminKoyu} x="118" y="54" width="24" height="54" rx="3" />
      <circle className={stil.vurgu} cx="136" cy="82" r="2.5" />
    </>
  ),
  // Açık kitap ve ayraç.
  ders: (
    <>
      <path className={stil.acik} d="M100 46c-18-10-38-10-54-4v62c16-6 36-6 54 4z" />
      <path className={stil.acik} d="M100 46c18-10 38-10 54-4v62c-16-6-36-6-54 4z" />
      <path className={stil.cizgi} d="M100 46v62" />
      <path className={stil.satir} d="M58 58c10-3 22-3 32 1M58 70c10-3 22-3 32 1M58 82c10-3 22-3 32 1" />
      <path className={stil.satir} d="M110 59c10-4 22-4 32-1M110 71c10-4 22-4 32-1" />
      <path className={stil.vurgu} d="M126 40h12v26l-6-5-6 5z" />
    </>
  ),
  // Haftalık çizelge: birkaç dolu hücre.
  takvim: (
    <>
      <rect className={stil.acik} x="44" y="30" width="112" height="84" rx="8" />
      <rect className={stil.vurgu} x="44" y="30" width="112" height="16" rx="8" />
      <rect className={stil.vurgu} x="44" y="38" width="112" height="8" />
      <circle className={stil.acikDolgu} cx="64" cy="38" r="3" />
      <circle className={stil.acikDolgu} cx="136" cy="38" r="3" />
      {[0, 1, 2, 3].map((satir) =>
        [0, 1, 2, 3, 4].map((sutun) => (
          <rect
            key={`${satir}-${sutun}`}
            className={(satir * 5 + sutun) % 4 === 1 ? stil.vurgu : (satir * 5 + sutun) % 6 === 2 ? stil.koyu : stil.hucre}
            x={54 + sutun * 19}
            y={54 + satir * 14}
            width="14"
            height="9"
            rx="2"
          />
        )),
      )}
    </>
  ),
  // Büyüteç bir listenin üzerinde: aramada sonuç yok.
  arama: (
    <>
      <rect className={stil.acik} x="40" y="32" width="88" height="80" rx="8" />
      <path className={stil.satir} d="M54 50h44M54 64h56M54 78h36M54 92h48" />
      <circle className={stil.zeminKoyu} cx="132" cy="74" r="24" />
      <circle className={stil.cerceve} cx="132" cy="74" r="24" />
      <path className={stil.sap} d="M150 92l18 18" />
      <path className={stil.cizgi} d="M124 74h16" />
    </>
  ),
  // Telefona giden bir link: yayın ve paylaşım.
  yayin: (
    <>
      <rect className={stil.acik} x="116" y="28" width="46" height="84" rx="9" />
      <rect className={stil.hucre} x="123" y="40" width="32" height="8" rx="2" />
      <rect className={stil.vurgu} x="123" y="54" width="14" height="9" rx="2" />
      <rect className={stil.ikincil} x="141" y="54" width="14" height="9" rx="2" />
      <rect className={stil.ikincil} x="123" y="67" width="14" height="9" rx="2" />
      <rect className={stil.vurgu} x="141" y="67" width="14" height="9" rx="2" />
      <rect className={stil.hucre} x="123" y="80" width="32" height="9" rx="2" />
      <path className={stil.cizgi} d="M60 90c14-30 34-40 50-40" strokeDasharray="4 6" />
      <path className={stil.koyu} d="M38 78l40-16-14 38-8-14z" />
      <path className={stil.vurgu} d="M56 86l22-24-14 38z" />
    </>
  ),
};
