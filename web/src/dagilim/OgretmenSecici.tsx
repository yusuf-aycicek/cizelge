import { BosRozet, OgretmenRozeti } from "../bilesenler/OgretmenRozeti";
import type { SelectHTMLAttributes } from "react";
import type { Ders, Ogretmen } from "../listeler/kaynaklar";
import { bransaGoreGrupla } from "./brans";
import stil from "./Dagilim.module.css";
import { yukMetni, type OgretmenYuku } from "./veri";

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange"> & {
  /** Seçicinin erişilebilir adı, ör. "9-A Matematik öğretmeni". */
  etiket: string;
  /** Branş eşleşmesi bu derse göre yapılır. */
  ders: Ders | undefined;
  ogretmenler: readonly Ogretmen[];
  yukler: Map<string, OgretmenYuku>;
  deger: string | null;
  onDegis: (ogretmenId: string | null) => void;
  bosMetin?: string;
};

/**
 * Öğretmen seçici: doğal `<select>`, iki grup (`<optgroup>`):
 * - dersin branşıyla eşleşen öğretmenler üstte ("Branşı uyan: Matematik");
 * - diğerleri altta ("Diğer öğretmenler"). Branş serbest metin olduğu için kimse gizlenmez.
 *
 * Her seçenekte öğretmenin güncel yükü yazar: "Ayşe Yılmaz (Matematik) · 18 / 24 saat". Seçili
 * öğretmenin seçeneğinde branş yazmaz ("Ayşe Yılmaz · 18 / 24 saat"): doğal seçici kapalıyken seçili
 * seçeneğin metnini gösterir, branşla birlikte tablo sütununa sığmayıp kesiliyordu. Tam metin
 * seçicinin `title`'ında kalır (üzerine gelince). Yük,
 * sunucunun özetinden gelir (ön kontrolle aynı hesap). Kapasitesi aşılmış öğretmen için seçenek
 * metninde "kapasite aşıldı" yazar; seçmek yine serbesttir (uyarı, yasak değil).
 *
 * Neden doğal `<select>` (planda "aranabilir açılır liste" vardı): klavyede harf yazınca o harfle
 * başlayan öğretmene gider, telefonda işletim sisteminin kendi seçicisi açılır, ekran okuyucular
 * grupları okur. 45 öğretmenlik bir liste için bu yeterli; arama kutulu bir seçici (combobox)
 * kendi klavye ve erişilebilirlik kodunu gerektirirdi.
 */
export function OgretmenSecici({ etiket, ders, ogretmenler, yukler, deger, onDegis, bosMetin = "— Öğretmen seçilmedi —", className, ...diger }: Props) {
  // useMemo yok. Ölçüm: 45 öğretmeni gruplayıp sıralamak seçici başına ~0,14 ms, 15 dersli bir şubede
  // çizim başına ~2 ms. useMemo'nun da bir bedeli var (bağımlılık karşılaştırması, bellekte tutma,
  // okunabilirlik); ölçülen bir yavaşlık olmadan eklenmez.
  const { uyan, diger: digerleri } = bransaGoreGrupla(ogretmenler, ders);

  const metin = (o: Ogretmen, bransli: boolean) => {
    const yuk = yukler.get(o.id);
    const parcalar = [bransli && o.brans ? `${o.ad} (${o.brans})` : o.ad];
    if (yuk) parcalar.push(yukMetni(yuk));
    if (yuk?.asim) parcalar.push("kapasite aşıldı");
    return parcalar.join(" · ");
  };
  const secenek = (o: Ogretmen) => (
    <option key={o.id} value={o.id}>
      {metin(o, o.id !== deger)}
    </option>
  );

  // Seçili öğretmenin rozeti seçicinin solunda (doğal <option> içine resim konamaz).
  const secili = deger ? ogretmenler.find((o) => o.id === deger) : undefined;
  return (
    <span className={stil.seciciKutusu}>
      {secili ? <OgretmenRozeti id={secili.id} ad={secili.ad} boyut="kucuk" /> : <BosRozet boyut="kucuk" />}
      <select
        aria-label={etiket}
        className={[stil.secici, deger ? undefined : stil.seciciBos, className].filter(Boolean).join(" ")}
        value={deger ?? ""}
        title={secili ? metin(secili, true) : undefined}
        onChange={(o) => onDegis(o.target.value || null)}
        {...diger}
      >
        <option value="">{bosMetin}</option>
        {uyan.length > 0 ? (
          <>
            <optgroup label={`Branşı uyan: ${ders?.ad ?? ""}`}>{uyan.map(secenek)}</optgroup>
            {digerleri.length > 0 && <optgroup label="Diğer öğretmenler">{digerleri.map(secenek)}</optgroup>}
          </>
        ) : (
          <optgroup label="Öğretmenler">{digerleri.map(secenek)}</optgroup>
        )}
      </select>
    </span>
  );
}
