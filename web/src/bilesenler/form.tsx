import { useEffect, useRef, useState, type ChangeEvent, type RefObject } from "react";
import { ApiHatasi, hataMetni } from "../api/hata";
import stil from "./form.module.css";

/**
 * Kontrollü form için özel kanca (custom hook). Alanların değerleri React state'inde durur;
 * input'un gösterdiği değer her zaman state'tir ("kontrollü bileşen"). Böylece değeri okumak,
 * sıfırlamak ya da doğrulamak için DOM'a bakmaya gerek kalmaz.
 *
 *     const form = useFormDegerleri({ email: "", sifre: "" });
 *     <MetinAlani etiket="E-posta" {...form.alan("email")} />
 */
export function useFormDegerleri<T extends Record<string, string>>(baslangic: T) {
  const [degerler, setDegerler] = useState<T>(baslangic);

  function alan(ad: keyof T & string) {
    return {
      name: ad,
      value: degerler[ad],
      onChange: (olay: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
        // Önceki değerden yeni nesne: state asla yerinde değiştirilmez (React değişikliği görmez).
        setDegerler((onceki) => ({ ...onceki, [ad]: olay.target.value })),
    };
  }

  return { degerler, alan, sifirla: () => setDegerler(baslangic) };
}

export type AlanHatalari = Record<string, string>;

/**
 * Sunucu hatasını form alanlarına dağıtır. `ozel`, alanlar listesi olmayan bilinen hataları bir
 * alana bağlar (ör. 409 "e-posta kullanılıyor" -> email). Hiçbir alana düşmeyen hata `genel`
 * olarak formun üstünde gösterilir.
 */
export function sunucuHatalari(
  hata: unknown,
  ozel?: (hata: ApiHatasi) => string | undefined,
): { alanlar: AlanHatalari; genel?: string } {
  if (!hata) return { alanlar: {} };
  if (!(hata instanceof ApiHatasi)) return { alanlar: {}, genel: hataMetni(hata) };
  if (Object.keys(hata.alanlar).length > 0) return { alanlar: hata.alanlar };
  const alan = ozel?.(hata);
  if (alan) return { alanlar: { [alan]: hata.message } };
  return { alanlar: {}, genel: hata.message };
}

/**
 * Gönderimden sonra ilk hatalı alana odaklanır: ekran okuyucu ve klavye kullanıcısı hatayı
 * aramak zorunda kalmaz. `deneme` her gönderimde artan bir sayıdır; effect yalnızca o değişince
 * (yeni gönderim) çalışır, kullanıcı yazarken odak kaymaz.
 */
export function useIlkHatayaOdaklan(form: RefObject<HTMLFormElement | null>, deneme: number) {
  const ilk = useRef(true);
  useEffect(() => {
    if (ilk.current) {
      ilk.current = false;
      return;
    }
    const hatali = form.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
    hatali?.focus();
  }, [form, deneme]);
}

/** Formun üstündeki genel hata (alanlara bağlanamayan sunucu hatası). */
export function FormHatasi({ mesaj }: { mesaj?: string }) {
  if (!mesaj) return null;
  return (
    <div role="alert" className={stil.formHatasi}>
      {mesaj}
    </div>
  );
}
