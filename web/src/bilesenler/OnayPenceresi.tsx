import { useEffect, useId, useRef, type ReactNode } from "react";
import { Dugme } from "./Dugme";
import stil from "./OnayPenceresi.module.css";

type Props = {
  acik: boolean;
  baslik: string;
  mesaj: string;
  onaylaMetni?: string;
  vazgecMetni?: string;
  /** Geri alınamayan işlemler (silme) için kırmızı onay düğmesi. */
  tehlikeli?: boolean;
  yukleniyor?: boolean;
  onOnayla: () => void;
  onVazgec: () => void;
  /** Mesajın altında ek içerik (ör. etkilerin listesi). */
  children?: ReactNode;
};

/**
 * Onay penceresi: doğal <dialog> öğesi `showModal()` ile açılır. Tarayıcı şunları hazır verir:
 * arkadaki sayfa tıklanamaz, odak pencerenin içinde kalır, Esc pencereyi kapatır, kapanınca
 * odak pencereyi açan düğmeye döner.
 *
 * Güvenli varsayılan: açılınca odak "Vazgeç"tedir; yanlışlıkla Enter'a basmak silmez.
 */
export function OnayPenceresi({
  acik,
  baslik,
  mesaj,
  onaylaMetni = "Onayla",
  vazgecMetni = "Vazgeç",
  tehlikeli = false,
  yukleniyor = false,
  onOnayla,
  onVazgec,
  children,
}: Props) {
  // useRef: çizimler arasında kalıcı bir kutu; burada DOM'daki <dialog> öğesini tutar.
  // Değeri değişince bileşen yeniden çizilmez (useState'ten farkı).
  const pencere = useRef<HTMLDialogElement>(null);
  const vazgec = useRef<HTMLButtonElement>(null);
  const baslikId = useId();
  const mesajId = useId();

  // useEffect: React'in dışındaki bir şeyi (tarayıcının dialog API'si) state ile eşitler.
  // Bağımlılık listesindeki `acik` değiştiğinde çalışır.
  useEffect(() => {
    const p = pencere.current;
    if (!p) return;
    if (acik && !p.open) {
      p.showModal();
      vazgec.current?.focus();
    } else if (!acik && p.open) {
      p.close();
    }
  }, [acik]);

  return (
    <dialog
      ref={pencere}
      className={stil.pencere}
      aria-labelledby={baslikId}
      aria-describedby={mesajId}
      // Esc: tarayıcı "cancel" olayı gönderir. Kapanmayı state yönetsin diye engellenir.
      onCancel={(olay) => {
        olay.preventDefault();
        onVazgec();
      }}
    >
      <h2 id={baslikId} className={stil.baslik}>
        {baslik}
      </h2>
      <div id={mesajId}>
        <p>{mesaj}</p>
        {children}
      </div>
      <div className={stil.dugmeler}>
        <Dugme ref={vazgec} tur="ikincil" onClick={onVazgec} disabled={yukleniyor}>
          {vazgecMetni}
        </Dugme>
        <Dugme tur={tehlikeli ? "tehlike" : "birincil"} onClick={onOnayla} yukleniyor={yukleniyor}>
          {onaylaMetni}
        </Dugme>
      </div>
    </dialog>
  );
}
