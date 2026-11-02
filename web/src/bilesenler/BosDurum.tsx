import { useId, type ReactNode } from "react";
import stil from "./BosDurum.module.css";
import { Illustrasyon, type IllustrasyonTuru } from "./Illustrasyon";

type Props = {
  cizim: IllustrasyonTuru;
  baslik: string;
  /** Başlığın düzeyi: sayfanın tek içeriğiyse 1, bölüm başlığıysa 2, bir kartın içindeyse 3. */
  baslikDuzeyi?: 1 | 2 | 3;
  /** "kucuk": kartın ya da tablonun içinde, çerçevesiz ve küçük çizimle. */
  boyut?: "normal" | "kucuk";
  /** Açıklama metni. */
  children?: ReactNode;
  /** Ne yapılacağı: düğme ya da bağlantı. */
  eylem?: ReactNode;
};

/**
 * Boş durum: çizim (yalnızca süs), ne olduğunu söyleyen başlık, açıklama ve sıradaki adım.
 * Kullanıcı boş bir ekranda kalmaz; ne yapacağını bilir.
 */
export function BosDurum({ cizim, baslik, baslikDuzeyi = 2, boyut = "normal", children, eylem }: Props) {
  const id = useId();
  const Baslik = (["h1", "h2", "h3"] as const)[baslikDuzeyi - 1]!;
  const icerik = (
    <>
      <Illustrasyon tur={cizim} kucuk={boyut === "kucuk"} />
      <Baslik id={id} className={stil.baslik}>
        {baslik}
      </Baslik>
      {children && <div className={stil.aciklama}>{children}</div>}
      {eylem && <div className={stil.eylem}>{eylem}</div>}
    </>
  );
  // Sayfadaki boş durum kendi başına bir bölümdür (başlığıyla adlanır); kartın içindeki değil.
  return boyut === "kucuk" ? (
    <div className={`${stil.bos} ${stil.kucuk}`}>{icerik}</div>
  ) : (
    <section aria-labelledby={id} className={stil.bos}>
      {icerik}
    </section>
  );
}
