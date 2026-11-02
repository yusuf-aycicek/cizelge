import { useEffect, useState } from "react";
import { hareketAzaltilmis } from "../bilesenler/hareket";

const SURE_MS = 800;

/**
 * Sıfırdan hedefe sayan sayı (sayı kartları). Hareket azaltılmışsa ya da ortam bildiremiyorsa
 * (testler) doğrudan hedef görünür. Yavaşlayarak durur (ease-out).
 */
export function SayacSayi({ hedef }: { hedef: number }) {
  const [deger, setDeger] = useState(0);
  useEffect(() => {
    if (hareketAzaltilmis()) return;
    let kare = 0;
    const bas = performance.now();
    const adim = (simdi: number) => {
      const t = Math.min(1, (simdi - bas) / SURE_MS);
      setDeger(Math.round(hedef * (1 - (1 - t) ** 3)));
      if (t < 1) kare = requestAnimationFrame(adim);
    };
    kare = requestAnimationFrame(adim);
    return () => cancelAnimationFrame(kare);
  }, [hedef]);
  return <>{hareketAzaltilmis() ? hedef : deger}</>;
}
