import { CircleAlert, CircleCheck, Info, TriangleAlert, X, type LucideIcon } from "lucide-react";
import { cikistanSonra } from "./hareket";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import stil from "./Bildirim.module.css";

export type BildirimTuru = "basari" | "hata" | "uyari" | "bilgi";
type Bildirim = { id: number; tur: BildirimTuru; mesaj: string; cikiyor?: boolean };
type Goster = (tur: BildirimTuru, mesaj: string) => void;

/**
 * Context (bağlam): bir değeri bileşen ağacında aşağıya, aradaki her bileşene props olarak
 * geçirmeden ulaştırır. Burada değer `goster` fonksiyonudur: herhangi bir sayfa
 * `useBildirim()` ile bildirim gösterebilir.
 */
type Baglam = { goster: Goster; temizle: () => void };
const BildirimBaglami = createContext<Baglam | null>(null);

export const KAYBOLMA_MS = 6000;

/**
 * Bildirimler ekranın köşesinde görünür:
 * - başarı ve bilgi 6 sn sonra kendiliğinden kaybolur;
 * - hata ve uyarı kullanıcı kapatana kadar kalır (okumaya vakit olsun).
 *
 * Ekran okuyucular yeni bildirimi duyurur ("canlı bölge", aria-live): başarı sırası gelince
 * (role="status"), hata hemen (role="alert").
 */
export function BildirimSaglayici({ children }: { children: ReactNode }) {
  const [bildirimler, setBildirimler] = useState<Bildirim[]>([]);
  const sonraki = useRef(1);

  // Kapatma iki adımdır: önce "çıkıyor" (kayarak gider, CSS), sonra listeden kalkar. Hareket
  // azaltılmışsa hemen kalkar (hareket.ts).
  const kapat = useCallback((id: number) => {
    setBildirimler((b) => b.map((x) => (x.id === id ? { ...x, cikiyor: true } : x)));
    cikistanSonra(() => setBildirimler((b) => b.filter((x) => x.id !== id)));
  }, []);

  const goster = useCallback<Goster>(
    (tur, mesaj) => {
      const id = sonraki.current++;
      setBildirimler((b) => [...b, { id, tur, mesaj }]);
      if (tur === "basari" || tur === "bilgi") {
        setTimeout(() => kapat(id), KAYBOLMA_MS);
      }
    },
    [kapat],
  );

  // Çıkışta çağrılır: bir kullanıcının bildirimi sonraki kullanıcının ekranında kalmasın.
  const temizle = useCallback(() => setBildirimler([]), []);
  const baglam = useMemo(() => ({ goster, temizle }), [goster, temizle]);

  const sakin = useMemo(() => bildirimler.filter((b) => b.tur === "basari" || b.tur === "bilgi"), [bildirimler]);
  const acil = useMemo(() => bildirimler.filter((b) => b.tur === "hata" || b.tur === "uyari"), [bildirimler]);

  return (
    <BildirimBaglami.Provider value={baglam}>
      {children}
      <div className={stil.alan}>
        <div role="alert" className={stil.liste}>
          {acil.map((b) => (
            <Kart key={b.id} bildirim={b} kapat={kapat} />
          ))}
        </div>
        <div role="status" className={stil.liste}>
          {sakin.map((b) => (
            <Kart key={b.id} bildirim={b} kapat={kapat} />
          ))}
        </div>
      </div>
    </BildirimBaglami.Provider>
  );
}

const IKONLAR: Record<BildirimTuru, LucideIcon> = { basari: CircleCheck, hata: CircleAlert, uyari: TriangleAlert, bilgi: Info };

/**
 * Bildirim kartı: türün ikonu renkli dairede, mesaj ana metin renginde. Kendiliğinden kaybolan
 * bildirimin altında kalan süreyi gösteren ince bir çubuk kısalır (yalnızca süs; hareket
 * azaltılmışsa görünmez).
 */
function Kart({ bildirim, kapat }: { bildirim: Bildirim; kapat: (id: number) => void }) {
  const Ikon = IKONLAR[bildirim.tur];
  const gecici = bildirim.tur === "basari" || bildirim.tur === "bilgi";
  return (
    <div className={[stil.kart, stil[bildirim.tur], bildirim.cikiyor ? stil.cikiyor : ""].join(" ")}>
      <span className={stil.ikon} aria-hidden="true">
        <Ikon />
      </span>
      <p className={stil.mesaj}>{bildirim.mesaj}</p>
      <button type="button" className={stil.kapat} onClick={() => kapat(bildirim.id)} aria-label="Bildirimi kapat">
        <X aria-hidden="true" />
      </button>
      {gecici && <span className={stil.sure} style={{ animationDuration: `${KAYBOLMA_MS}ms` }} aria-hidden="true" />}
    </div>
  );
}

/** Bir kanca (hook): adı `use` ile başlayan, React'in özelliklerini kullanan fonksiyon. */
export function useBildirim(): Goster {
  return useBaglam().goster;
}

/** Ekrandaki bütün bildirimleri kaldırır (ör. çıkışta). */
export function useBildirimleriTemizle(): () => void {
  return useBaglam().temizle;
}

function useBaglam(): Baglam {
  const baglam = useContext(BildirimBaglami);
  if (!baglam) {
    throw new Error("useBildirim, BildirimSaglayici içinde kullanılmalı");
  }
  return baglam;
}
