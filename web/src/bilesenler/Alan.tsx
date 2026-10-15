import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import stil from "./Alan.module.css";

/** Form denetimine (input, select, textarea) verilecek erişilebilirlik özellikleri. */
export type DenetimOzellikleri = {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
  "aria-required"?: true;
};

type Props = {
  etiket: string;
  /** Alanın altında kısa yardım metni, ör. "En az 12 karakter". */
  aciklama?: string;
  /** Sunucudan ya da arayüzden gelen hata; varsa alan kırmızı çerçeveli olur. */
  hata?: string;
  gerekli?: boolean;
  /**
   * Denetimi çizen fonksiyon ("render prop"): Alan, etiketi ve hatayı denetime bağlayan
   * özellikleri üretir, denetimin kendisini çağıran bileşen seçer (input, select...).
   */
  children: (ozellikler: DenetimOzellikleri) => ReactNode;
};

/**
 * Form alanı: etiket + denetim + açıklama + hata.
 *
 * Erişilebilirlik:
 * - <label htmlFor> denetime bağlıdır: etikete tıklamak denetime odaklanır, ekran okuyucu
 *   denetimin adını okur;
 * - açıklama ve hata `aria-describedby` ile bağlıdır: ekran okuyucu alana gelince onları da okur;
 * - `aria-invalid` hatalı alanı işaretler; hata metni yalnızca renkle değil yazıyla verilir.
 */
export function Alan({ etiket, aciklama, hata, gerekli = false, children }: Props) {
  // useId: her Alan örneği için sayfada benzersiz, sunucu ve istemcide aynı bir kimlik üretir.
  const id = useId();
  const aciklamaId = aciklama ? `${id}-aciklama` : undefined;
  const hataId = hata ? `${id}-hata` : undefined;
  const aciklayanlar = [hataId, aciklamaId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={stil.alan}>
      <label htmlFor={id} className={stil.etiket}>
        {etiket}
        {gerekli && <span aria-hidden="true"> *</span>}
      </label>
      {children({
        id,
        "aria-describedby": aciklayanlar,
        "aria-invalid": hata ? true : undefined,
        "aria-required": gerekli ? true : undefined,
      })}
      {hata && (
        <p id={hataId} className={stil.hata}>
          {hata}
        </p>
      )}
      {aciklama && (
        <p id={aciklamaId} className={stil.aciklama}>
          {aciklama}
        </p>
      )}
    </div>
  );
}

/** En sık kullanılan durum: metin kutusu. */
export function MetinAlani({
  etiket,
  aciklama,
  hata,
  gerekli,
  ...input
}: Omit<Props, "children"> & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Alan etiket={etiket} aciklama={aciklama} hata={hata} gerekli={gerekli}>
      {(ozellikler) => <input className={stil.denetim} required={gerekli} {...input} {...ozellikler} />}
    </Alan>
  );
}

/** Seçim kutusu. */
export function SecimAlani({
  etiket,
  aciklama,
  hata,
  gerekli,
  children,
  ...select
}: Omit<Props, "children"> & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <Alan etiket={etiket} aciklama={aciklama} hata={hata} gerekli={gerekli}>
      {(ozellikler) => (
        <select className={stil.denetim} required={gerekli} {...select} {...ozellikler}>
          {children}
        </select>
      )}
    </Alan>
  );
}
