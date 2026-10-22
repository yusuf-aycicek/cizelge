import stil from "./OgretmenRozeti.module.css";

export const ROZET_RENGI_SAYISI = 8; // belirtecler.css: --renk-rozet-1..8

/**
 * Baş harfler: ilk ve son kelimenin ilk harfi, Türkçe büyük harfle ("ismail er" → "İE",
 * "Ayşe Gülşen Yılmaz" → "AY"). Tek kelimede tek harf.
 */
export function basHarfler(ad: string): string {
  const kelimeler = ad.trim().split(/\s+/).filter(Boolean);
  if (kelimeler.length === 0) return "?";
  const ilk = kelimeler[0]!;
  const son = kelimeler.length > 1 ? kelimeler[kelimeler.length - 1]! : "";
  return (ilk.charAt(0) + son.charAt(0)).toLocaleUpperCase("tr");
}

/** Kimlikten kararlı bir renk sırası (1..8): aynı öğretmen her ekranda aynı renkte. */
export function rozetRengi(kimlik: string): number {
  let ozet = 0;
  for (const harf of kimlik) ozet = (ozet * 31 + harf.charCodeAt(0)) >>> 0;
  return (ozet % ROZET_RENGI_SAYISI) + 1;
}

type Props = {
  id: string;
  ad: string;
  boyut?: "kucuk" | "normal";
};

/**
 * Öğretmen rozeti: baş harfli renkli yuvarlak. Yalnızca süstür: öğretmenin adı her zaman yanında
 * yazılıdır. Baş harfler CSS ile (`::before { content: attr(data-harfler) }`) çizilir, DOM'da metin
 * değildir: hücrenin metni "AÇAli Çelik" olmaz, ekran okuyucu da ayrıca okumaz.
 */
export function OgretmenRozeti({ id, ad, boyut = "normal" }: Props) {
  return (
    <span
      aria-hidden="true"
      className={`${stil.rozet} ${boyut === "kucuk" ? stil.kucuk : ""}`}
      data-harfler={basHarfler(ad)}
      style={{ background: `var(--renk-rozet-${rozetRengi(id)})` }}
    />
  );
}

/** Rozet ve ad yan yana (listeler, kartlar). */
export function OgretmenAdi({ id, ad }: { id: string; ad: string }) {
  return (
    <span className={stil.adli}>
      <OgretmenRozeti id={id} ad={ad} boyut="kucuk" />
      {ad}
    </span>
  );
}

/** Seçilmemiş öğretmen için boş, kesik çizgili yuvarlak (aynı yer tutulsun, satırlar kaymasın). */
export function BosRozet({ boyut = "normal" }: { boyut?: "kucuk" | "normal" }) {
  return <span aria-hidden="true" className={`${stil.rozet} ${stil.bos} ${boyut === "kucuk" ? stil.kucuk : ""}`} />;
}
