import { OgretmenRozeti } from "../bilesenler/OgretmenRozeti";
import { DersCipi } from "../dersler/DersCipi";
import { useState } from "react";
import { Dugme } from "../bilesenler/Dugme";
import { turkceKarsilastir, turkceSirala } from "../metin";
import stil from "./Dagilim.module.css";
import type { DagilimVerisi, Git } from "./DersDagilimiSayfasi";
import { yukMetni } from "./veri";

/**
 * Öğretmen görünümü: her öğretmenin toplam ders yükü, kullanılabilir saatiyle karşılaştırılarak.
 * Kapasitesi aşılan öğretmenler en üstte ve kırmızıdır; altlarında ön kontrolün mesajı yazar.
 * Satırdaki düğme öğretmenin derslerini açar; her ders şube görünümüne götürür.
 *
 * Hesap yok: sayılar ve mesaj sunucudan (ADR 0015).
 */
export function OgretmenGorunumu({ veri, git }: { veri: DagilimVerisi; git: Git }) {
  const [acik, setAcik] = useState<Set<string>>(new Set());

  const satirlar = veri.ogretmenler
    .map((o) => ({ ogretmen: o, yuk: veri.ogretmenYukleri.get(o.id) }))
    .sort((a, b) => Number(Boolean(b.yuk?.asim)) - Number(Boolean(a.yuk?.asim)) || turkceKarsilastir(a.ogretmen.ad, b.ogretmen.ad));

  function degistir(id: string) {
    // Set yerinde değiştirilmez; yeni bir Set ile state güncellenir (React farkı nesne kimliğinden anlar).
    setAcik((onceki) => {
      const yeni = new Set(onceki);
      if (yeni.has(id)) yeni.delete(id);
      else yeni.add(id);
      return yeni;
    });
  }

  return (
    <>
      <p className={stil.aciklama}>
        Kullanılabilir saat: öğretmenin "gelemez" işaretlemediği saatler, günde en fazla{" "}
        {veri.ozet.ogretmen_gunluk_siniri} saat derse girebilmesi sınırıyla. Yükü bunu aşan öğretmen için program
        üretilemez.
      </p>
      <ul className={stil.ogretmenListesi}>
        {satirlar.map(({ ogretmen, yuk }) => {
          const atamalar = turkceSirala(
            veri.atamalar.filter((a) => a.ogretmen_id === ogretmen.id),
            (a) => `${veri.sinif.get(a.sinif_id)?.ad} ${veri.ders.get(a.ders_id)?.ad}`,
          );
          const doluluk = !yuk ? 0 : yuk.kullanilabilir_saat === 0 ? (yuk.ders_saati > 0 ? 100 : 0)
            : Math.min(100, (yuk.ders_saati / yuk.kullanilabilir_saat) * 100);
          const listeId = `ogretmen-dersleri-${ogretmen.id}`;
          return (
            <li key={ogretmen.id} className={yuk?.asim ? `${stil.ogretmenKarti} ${stil.ogretmenAsim}` : stil.ogretmenKarti}>
              <div className={stil.ogretmenUst}>
                <OgretmenRozeti id={ogretmen.id} ad={ogretmen.ad} />
                <h3 className={stil.ogretmenAdi}>
                  {ogretmen.ad}
                  {ogretmen.brans && <span className={stil.ikincil}> · {ogretmen.brans}</span>}
                </h3>
                <span className={yuk?.asim ? stil.asimMetni : undefined}>
                  {yuk ? (yuk.ders_saati === 0 ? `Henüz dersi yok (kullanılabilir ${yuk.kullanilabilir_saat} saat)` : yukMetni(yuk)) : ""}
                </span>
              </div>
              {/* Çubuk yalnızca görseldir; aynı bilgi yanındaki metinde yazılıdır. */}
              <div className={stil.cubuk} aria-hidden="true">
                <div className={yuk?.asim ? stil.cubukAsim : stil.cubukDolgu} style={{ width: `${doluluk}%` }} />
              </div>
              {yuk?.asim && yuk.mesaj && (
                <p className={stil.asimMesaji}>
                  <span aria-hidden="true">⚠ </span>
                  {yuk.mesaj}
                </p>
              )}
              {atamalar.length > 0 && (
                <>
                  <Dugme tur="metin" aria-expanded={acik.has(ogretmen.id)} aria-controls={listeId}
                    onClick={() => degistir(ogretmen.id)}>
                    {acik.has(ogretmen.id) ? "Dersleri gizle" : `Derslerini göster (${atamalar.length})`}
                  </Dugme>
                  {acik.has(ogretmen.id) && (
                    <ul id={listeId} className={stil.dersListesi}>
                      {atamalar.map((a) => {
                        const sinif = veri.sinif.get(a.sinif_id)?.ad;
                        return (
                          <li key={a.id}>
                            <span>
                              {sinif} <DersCipi ad={veri.ders.get(a.ders_id)?.ad ?? ""} renk={veri.ders.get(a.ders_id)?.renk} isaret={veri.dersIsareti.get(a.ders_id)} /> ·{" "}
                              {a.haftalik_saat} saat
                            </span>
                            <Dugme tur="metin" onClick={() => git({ gorunum: "sube", sinif: a.sinif_id })}>
                              {sinif} şubesine git
                            </Dugme>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
