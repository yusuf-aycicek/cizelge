import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { useId } from "react";
import { turkceSirala } from "../metin";
import { dersKaynagi } from "./kaynaklar";
import stil from "./Liste.module.css";

/**
 * Öğretmenin branşı: okulun derslerinden çoklu seçim (ADR 0029). Değer yine tek bir metindir,
 * seçilen derslerin adları virgülle: "Matematik, Fizik". Böylece sütun ve API değişmez, eski
 * serbest metin bozulmaz.
 *
 * Bir ders adıyla eşleşmeyen eski parça ("Fen Bilimleri Öğretmeni") listede işaretli bir seçenek
 * olarak kalır; kaldırılmak istenirse işareti kaldırılır. Eşleşme büyük/küçük harf duyarsızdır
 * (Türkçe kurallarıyla).
 */

const sade = (s: string) => s.trim().toLocaleLowerCase("tr");

/** "Matematik, Fizik" -> ["Matematik", "Fizik"] (boş parçalar atılır). */
export function bransParcalari(brans: string | null | undefined): string[] {
  return (brans ?? "").split(",").map((p) => p.trim()).filter(Boolean);
}

/**
 * Seçimi metne çevirir: okulun ders sırasıyla (Türkçe alfabetik) seçilen dersler, ardından
 * eşleşmeyen eski parçalar yazıldıkları sırayla.
 */
export function bransMetni(dersAdlari: readonly string[], secili: readonly string[]): string {
  const secim = new Set(secili.map(sade));
  const dersler = dersAdlari.filter((d) => secim.has(sade(d)));
  const bilinen = new Set(dersAdlari.map(sade));
  return [...dersler, ...secili.filter((p) => !bilinen.has(sade(p)))].join(", ");
}

type Props = {
  etiket: string;
  deger: string;
  onDegistir: (yeni: string) => void;
  hata?: string;
  /** Tablo satırında düzenlerken: etiket görünmez (erişilebilir adda kalır), kutu küçük. */
  satirda?: boolean;
};

export function BransSecici({ etiket, deger, onDegistir, hata, satirda = false }: Props) {
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const id = useId();
  const adlar = turkceSirala(dersler.data ?? [], (d) => d.ad).map((d) => d.ad);
  const parcalar = bransParcalari(deger);
  const secim = new Set(parcalar.map(sade));
  const bilinen = new Set(adlar.map(sade));
  const eskiler = parcalar.filter((p) => !bilinen.has(sade(p)));

  function degistir(ad: string, secili: boolean) {
    const kalan = parcalar.filter((p) => sade(p) !== sade(ad));
    onDegistir(bransMetni(adlar, secili ? [...kalan, ad] : kalan));
  }

  const secenek = (ad: string, ek?: string) => (
    <label key={`${ad}-${ek ?? ""}`} className={stil.bransSecenegi}>
      <input type="checkbox" checked={secim.has(sade(ad))} onChange={(o) => degistir(ad, o.target.checked)} />
      {ad}
      {ek && <span className={stil.soluk}> {ek}</span>}
    </label>
  );

  return (
    <div className={satirda ? stil.duzenAlani : stil.bransAlani}>
      {!satirda && (
        <span id={`${id}-etiket`} className={stil.bransEtiketi}>
          {etiket}
        </span>
      )}
      <details className={stil.bransSecici}>
        <summary
          className={satirda ? stil.satirDenetimi : stil.bransOzeti}
          aria-label={`${satirda ? `${etiket} (düzenleme)` : etiket}: ${deger || "seçilmedi"}`}
          aria-invalid={hata ? true : undefined}>
          <span className={deger ? undefined : stil.soluk}>{deger || "Ders seçin"}</span>
          <ChevronDown aria-hidden="true" />
        </summary>
        <fieldset className={stil.bransListesi}>
          <legend className="gorunmez">{etiket}</legend>
          {adlar.length === 0 && <p className={stil.soluk}>Önce Dersler sayfasından ders ekleyin.</p>}
          {adlar.map((ad) => secenek(ad))}
          {eskiler.map((p) => secenek(p, "(eski yazım)"))}
        </fieldset>
      </details>
      {hata && <span className={stil.satirHatasi}>⚠ {hata}</span>}
    </div>
  );
}
