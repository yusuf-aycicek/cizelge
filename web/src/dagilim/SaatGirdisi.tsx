import { useState } from "react";
import stil from "./Dagilim.module.css";

type Props = {
  /** Erişilebilir ad, ör. "9-A Matematik haftalık saat". */
  etiket: string;
  deger: number;
  onKaydet: (yeni: number) => void;
  disabled?: boolean;
};

/**
 * Tablo içinde haftalık saat. Yazarken kaydetmez; alandan çıkınca ya da Enter'a basınca kaydeder
 * (her tuşta bir istek gitmesin). Escape eski değere döner. Geçersiz değer (boş, 0, küsurat)
 * kaydedilmez, eski değer geri gelir.
 *
 * Yerel state yalnızca yazılmakta olan metindir. Sunucudan yeni değer gelince bileşeni çağıran
 * `key` değiştirir (ör. `key={atama.id + atama.haftalik_saat}`); React bileşeni sıfırdan kurar,
 * metin yeni değerle başlar. Böylece "prop değişince state'i güncelle" effect'i gerekmez.
 */
export function SaatGirdisi({ etiket, deger, onKaydet, disabled }: Props) {
  const [metin, setMetin] = useState(String(deger));

  function kaydet() {
    const yeni = Number(metin);
    if (!Number.isInteger(yeni) || yeni < 1 || yeni > 99) {
      setMetin(String(deger));
      return;
    }
    if (yeni !== deger) onKaydet(yeni);
  }

  return (
    <input
      type="number"
      inputMode="numeric"
      min={1}
      max={99}
      aria-label={etiket}
      className={stil.saat}
      value={metin}
      disabled={disabled}
      onChange={(o) => setMetin(o.target.value)}
      onBlur={kaydet}
      onKeyDown={(o) => {
        if (o.key === "Enter") {
          o.preventDefault();
          o.currentTarget.blur(); // kaydetmeyi onBlur yapar: Enter + çıkış iki istek göndermesin
        } else if (o.key === "Escape") {
          setMetin(String(deger));
        }
      }}
    />
  );
}
