/**
 * Elle düzeltmenin çubuğu (7.1): seçili dersin işlemleri (taşı, kilitle), taşıma modu bilgisi
 * (hangi ders taşınıyor, üzerine gelinen saatin durumu ve nedeni), geri alma ve uyarı onayı.
 *
 * Akış iki yoldan aynı duruma varır: masaüstünde dersi sürükleyip bırakmak, ya da (telefonda ve
 * klavyede) derse dokunup "Taşı"yı seçmek ve hedef saate dokunmak. İkisinde de taşıma başlarken
 * sunucudan bir kez harita istenir; her hedef hücre "uygun / uyarı / engel" olarak boyanır.
 */
import { Lock, LockOpen, Move, Undo2, X } from "lucide-react";
import { useState } from "react";
import { hataMetni } from "../api/hata";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { GUN_ADLARI } from "./aciklama";
import { hucreAnahtari } from "./cizelge";
import stil from "./Cizelge.module.css";
import { useGeriAl, useKilit, useTasi, useTasimaHaritasi, type Hedef } from "./duzeltme";

export type SeciliDers = { ders_atama_id: string; gun: number; saat: number; ad: string; kilitli: boolean };

/** Hedefin sade açıklaması: taşınabilir mi, kimle yer değiştirir, neyi kötüleştirir ya da neden olmaz. */
export function hedefMetni(h: Hedef | undefined): string {
  if (!h) return "";
  if (h.durum === "engel") return `Buraya taşınamaz: ${h.nedenler.join("; ")}`;
  const takas = h.takas ?? [];
  const bas = takas.length ? `Buraya taşınabilir; ${takas.join(", ")} ile yer değiştirir.` : "Buraya taşınabilir.";
  return h.durum === "uyari" ? `${bas} Programı biraz kötüleştirir: ${h.nedenler.join("; ")}` : bas;
}

type Props = {
  secili: SeciliDers | null;
  tasiniyor: boolean;
  haritaYukleniyor: boolean;
  /** Üzerine gelinen ya da odaklanan hedefin açıklaması (aria-live). */
  hedefAciklamasi: string;
  degisiklikSayisi: number;
  mesgul: boolean;
  onTasi: () => void;
  onKilit: () => void;
  onVazgec: () => void;
  onGeriAl: () => void;
};

export function DuzeltmeCubugu({
  secili, tasiniyor, haritaYukleniyor, hedefAciklamasi, degisiklikSayisi, mesgul, onTasi, onKilit, onVazgec, onGeriAl,
}: Props) {
  return (
    <div className={stil.duzeltme} role="region" aria-label="Elle düzeltme">
      <div className={stil.duzeltmeSatiri}>
        {secili ? (
          <p className={stil.duzeltmeBaslik}>
            {tasiniyor ? (
              <>
                <strong>{secili.ad}</strong> taşınıyor: hedef saati seçin.
                {haritaYukleniyor && " Uygun saatler hesaplanıyor..."}
              </>
            ) : (
              <>
                Seçili: <strong>{secili.ad}</strong>
                {secili.kilitli && " (kilitli)"}
              </>
            )}
          </p>
        ) : (
          <p className={stil.duzeltmeIpucu}>
            Bir dersi başka bir saate sürükleyin ya da derse dokunup “Taşı”yı seçin. Kilitli dersler yeniden üretimde yerinde kalır.
          </p>
        )}
        <span className={stil.duzeltmeDugmeleri}>
          {secili && !tasiniyor && (
            <>
              <Dugme tur="ikincil" ikon={<Move />} onClick={onTasi} disabled={secili.kilitli || mesgul}>
                Taşı
              </Dugme>
              <Dugme tur="ikincil" ikon={secili.kilitli ? <LockOpen /> : <Lock />} onClick={onKilit} disabled={mesgul}>
                {secili.kilitli ? "Kilidi aç" : "Kilitle"}
              </Dugme>
            </>
          )}
          {secili && (
            <Dugme tur="metin" ikon={<X />} onClick={onVazgec}>
              {tasiniyor ? "Vazgeç" : "Kapat"}
            </Dugme>
          )}
          {degisiklikSayisi > 0 && !tasiniyor && (
            <Dugme tur="metin" ikon={<Undo2 />} onClick={onGeriAl} disabled={mesgul}>
              Geri al ({degisiklikSayisi})
            </Dugme>
          )}
        </span>
      </div>
      {tasiniyor && (
        <p className={stil.duzeltmeLejant}>
          <span className={stil.lejantUygun} aria-hidden="true" /> uygun
          <span className={stil.lejantUyari} aria-hidden="true" /> programı kötüleştirir
          <span className={stil.lejantEngel} aria-hidden="true" /> taşınamaz
        </p>
      )}
      <p className={stil.hedefAciklamasi} aria-live="polite">
        {hedefAciklamasi}
      </p>
    </div>
  );
}

/** Yalnızca esnek kuralları kötüleştiren taşıma için onay. */
export function UyariOnayi({ hedef, ad, yukleniyor, onOnayla, onVazgec }: {
  hedef: Hedef | null; ad: string; yukleniyor: boolean; onOnayla: () => void; onVazgec: () => void;
}) {
  return (
    <OnayPenceresi
      acik={hedef !== null}
      baslik={`${ad} yine de taşınsın mı?`}
      mesaj="Taşıma kurallara uyuyor ama programı biraz kötüleştiriyor:"
      onaylaMetni="Yine de taşı"
      yukleniyor={yukleniyor}
      onVazgec={onVazgec}
      onOnayla={onOnayla}
    >
      <ul className={stil.uyariListesi}>
        {hedef?.nedenler.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </OnayPenceresi>
  );
}

/**
 * Elle düzeltmenin durumu: seçili ders, taşıma modu, harita, onay; işlemler sunucuya gider. Çizelge
 * (masaüstü ve gün gün) ve çubuk aynı durumu paylaşır.
 */
export function useElleDuzeltme(programId: string) {
  const bildirim = useBildirim();
  const [secili, setSecili] = useState<SeciliDers | null>(null);
  const [tasiniyor, setTasiniyor] = useState(false);
  const [uzerinde, setUzerinde] = useState<string | null>(null);
  const [onaylanacak, setOnaylanacak] = useState<Hedef | null>(null);
  const kaynak = tasiniyor && secili ? { ders_atama_id: secili.ders_atama_id, gun: secili.gun, saat: secili.saat } : null;
  const harita = useTasimaHaritasi(programId, kaynak);
  const tasiIslemi = useTasi(programId);
  const kilitIslemi = useKilit(programId);
  const geriAlIslemi = useGeriAl(programId);
  const hedefler = tasiniyor && harita.data ? new Map(harita.data.hedefler.map((h) => [hucreAnahtari(h.gun, h.saat), h])) : null;

  const birak = () => {
    setSecili(null);
    setTasiniyor(false);
    setUzerinde(null);
    setOnaylanacak(null);
  };

  function tasi(h: Hedef, uyarilariKabul: boolean) {
    if (!secili) return;
    const ad = secili.ad;
    tasiIslemi.mutate(
      { ders_atama_id: secili.ders_atama_id, gun: secili.gun, saat: secili.saat, hedef_gun: h.gun, hedef_saat: h.saat, uyarilari_kabul: uyarilariKabul },
      {
        onSuccess: () => bildirim("basari", `${ad} ${GUN_ADLARI[h.gun]} ${h.saat + 1}. saate taşındı.`),
        onError: (hata) => bildirim("hata", hataMetni(hata)),
        onSettled: birak,
      },
    );
  }

  /** Taşıma modunda bir hedef hücre seçildi (tıklama, dokunma ya da bırakma). */
  function hedefSec(gun: number, saat: number) {
    if (!secili || !hedefler) return;
    const h = hedefler.get(hucreAnahtari(gun, saat));
    if (!h) return; // kendi yeri ya da blok sığmıyor
    if (h.durum === "engel") bildirim("hata", hedefMetni(h));
    else if (h.durum === "uyari") setOnaylanacak(h);
    else tasi(h, false);
  }

  return {
    secili,
    tasiniyor,
    hedefler,
    haritaYukleniyor: harita.isFetching,
    onaylanacak,
    uzerinde: uzerinde && hedefler ? hedefMetni(hedefler.get(uzerinde)) : "",
    mesgul: tasiIslemi.isPending || kilitIslemi.isPending || geriAlIslemi.isPending,
    tasiYukleniyor: tasiIslemi.isPending,
    sec: (d: SeciliDers) => {
      setSecili(d);
      setTasiniyor(false);
    },
    surukle: (d: SeciliDers) => {
      setSecili(d);
      setTasiniyor(true);
    },
    tasimayaBasla: () => setTasiniyor(true),
    hedefSec,
    hedefUzerinde: (gun: number, saat: number) => setUzerinde(hucreAnahtari(gun, saat)),
    birak,
    onayla: () => onaylanacak && tasi(onaylanacak, true),
    onayVazgec: () => setOnaylanacak(null),
    kilit: () => {
      if (!secili) return;
      const { ad, kilitli } = secili;
      kilitIslemi.mutate(
        { ders_atama_id: secili.ders_atama_id, gun: secili.gun, saat: secili.saat, kilitli: !kilitli },
        {
          onSuccess: () => {
            bildirim("basari", kilitli ? `${ad} kilidi açıldı.` : `${ad} kilitlendi; yeniden üretimde yerinde kalır.`);
            setSecili((s) => s && { ...s, kilitli: !kilitli });
          },
          onError: (hata) => bildirim("hata", hataMetni(hata)),
        },
      );
    },
    geriAl: () =>
      geriAlIslemi.mutate(undefined, {
        onSuccess: () => {
          bildirim("basari", "Son değişiklik geri alındı.");
          birak();
        },
        onError: (hata) => bildirim("hata", hataMetni(hata)),
      }),
  };
}
