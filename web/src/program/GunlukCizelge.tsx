import { useState, type CSSProperties } from "react";
import { kisaKisiAdi } from "../bilesenler/darAlan";
import { OgretmenRozeti } from "../bilesenler/OgretmenRozeti";
import { SigdirilanMetin } from "../bilesenler/SigdirilanMetin";
import { DersCipi } from "../dersler/DersCipi";
import { ogleArasiSonrasi, saatVar, zilMetni } from "../okul/zaman";
import { GUN_ADLARI, GUN_KISA_ADLARI } from "./aciklama";
import type { CizelgeProps } from "./CizelgeSayfasi";
import { birlesikHucreler, hucreAnahtari } from "./cizelge";
import stil from "./Cizelge.module.css";

/** Bugün okul günüyse o gün (pazartesi 0), değilse pazartesi. */
function bugun(gunSayisi: number): number {
  const g = (new Date().getDay() + 6) % 7;
  return g < gunSayisi ? g : 0;
}

/**
 * Telefonda haftalık çizelge (5.6): yana kayan geniş tablo yerine bir gün seçilir, o günün dersleri
 * alt alta listelenir. Bloklar (art arda saatler) tek satırdır: "1.-2. saat". Boş saat "Boş",
 * öğle arası ayraç olarak görünür; kısa günün sonundaki saatler listelenmez.
 */
export function GunlukCizelge({
  baslik, gunSayisi, saatSayisi, gunSaatleri, ogleArasiSonra, zil, ogleZili, hucreler, gorunum, ders, dersIsareti, sinif,
  ogretmen,
}: CizelgeProps) {
  const [gun, setGun] = useState(() => bugun(gunSayisi));
  const birlesik = birlesikHucreler(hucreler, gunSayisi, saatSayisi, ogleArasiSonra);
  const gunler = Array.from({ length: gunSayisi }, (_, g) => GUN_ADLARI[g] ?? `${g + 1}. gün`);
  const gunAdi = gunler[gun] ?? "";

  const satirlar = [];
  for (let s = 0; s < saatSayisi; s++) {
    const k = hucreAnahtari(gun, s);
    if (birlesik.ortulen.has(k)) continue;
    const a = hucreler.get(k);
    if (!a && !saatVar(gunSaatleri, gun, s)) continue;
    const uzunluk = birlesik.uzunluk.get(k) ?? 1;
    const saatMetni = uzunluk > 1 ? `${s + 1}.-${s + uzunluk}. saat` : `${s + 1}. saat`;
    const bas = zil?.[s];
    const son = zil?.[s + uzunluk - 1];
    const d = a && ders.get(a.ders_id);
    const o = a?.ogretmen_id ? ogretmen.get(a.ogretmen_id) : undefined;
    satirlar.push(
      <li key={s} className={a ? stil.gunDolu : stil.gunBos} style={{ animationDelay: `${s * 40}ms` } as CSSProperties}>
        <span className={stil.gunSaat}>
          {saatMetni}
          {bas && son && <span className={stil.zil}>{zilMetni({ baslangic: bas.baslangic, bitis: son.bitis })}</span>}
        </span>
        {a ? (
          <span className={stil.gunDers}>
            <DersCipi ad={d?.ad ?? "?"} kisaAd={d?.kisa_ad} renk={d?.renk} isaret={dersIsareti.get(a.ders_id)} />
            <span className={stil.ikinci}>
              {gorunum === "sube" ? (
                o && (
                  <>
                    <OgretmenRozeti id={o.id} ad={o.ad} boyut="kucuk" />
                    <SigdirilanMetin uzun={o.ad} kisa={kisaKisiAdi(o.ad)} />
                  </>
                )
              ) : (
                sinif.get(a.sinif_id)?.ad
              )}
            </span>
          </span>
        ) : (
          <span className={stil.gunBosMetin}>Boş</span>
        )}
      </li>,
    );
    if (ogleArasiSonrasi(ogleArasiSonra, s + uzunluk - 1) && s + uzunluk < saatSayisi) {
      satirlar.push(
        <li key={`ogle-${s}`} className={stil.gunOgle}>
          <span>Öğle arası{ogleZili && ` · ${zilMetni(ogleZili)}`}</span>
        </li>,
      );
    }
  }

  return (
    <div className={stil.gunluk}>
      <div className={stil.gunSecici} role="group" aria-label="Gün">
        {gunler.map((g, i) => (
          <button key={g} type="button" aria-pressed={i === gun} aria-label={g} onClick={() => setGun(i)}>
            {GUN_KISA_ADLARI[i] ?? g}
          </button>
        ))}
      </div>
      {/* key: gün değişince liste yeniden kurulur, satırlar kısa bir sırayla yerleşir. */}
      <ol key={gun} className={stil.gunListesi} aria-label={`${baslik}, ${gunAdi}`}>
        {satirlar}
      </ol>
    </div>
  );
}
