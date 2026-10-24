import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { useState } from "react";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi } from "../bilesenler/form";
import { desenMetni } from "../dersler/desen";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Okul.module.css";
import { OzelAyarEkle } from "./OzelAyarEkle";

type Kural = components["schemas"]["KuralYanit"];
type OzelAyar = components["schemas"]["OzelAyarYanit"];

/**
 * Özel ayarın kullanıcı diliyle değeri: "günde en çok 6 saat derse girer". Kapsamın adı ("Ayşe
 * Yılmaz", "9-A · Matematik") API'den gelir; burada yalnızca değer söylenir.
 */
export function ozelAyarMetni(tur: string, ozel: OzelAyar): string {
  const p = ozel.parametreler;
  const k = ozel.kapsam;
  if (tur === "ogretmen_gunluk_siniri") return `günde en çok ${p.m} saat derse girer`;
  if (tur === "gunluk_ders_siniri") {
    if (k.ders_id && (k.sinif_id || k.sube_grubu_id)) return `günde en çok ${p.n} saat`;
    if (k.ders_id) return `bir şubeye günde en çok ${p.n} saat konur`;
    return `aynı ders günde en çok ${p.n} saat konur`;
  }
  if (tur === "bos_gun") return `haftada ${p.hedef_bos_gun} boş gün hedeflenir`;
  if (tur === "blok_deseni" && Array.isArray(p.desen)) return `dağılım şekli ${desenMetni(p.desen)}`;
  if (tur === "ders_saat_tercihi") return saatTercihiMetni(p.saatler, p.kacin);
  if (tur === "gunluk_en_az_ders") return Number(p.k) <= 1 ? "bir saat için de gelebilir" : `geldiği günde en az ${p.k} ders`;
  if (tur === "ders_yayilimi") return p.yayilsin ? "art arda günlere konmasın" : "art arda günlere konabilir";
  if (tur === "haftalik_yuk") return esikMetni(Number(p.alt ?? 0), Number(p.ust ?? 0));
  return Object.entries(p).map(([ad, deger]) => `${ad} = ${deger}`).join(", ");
}

const saatListesi = (saatler: number[]) => saatler.map((s) => `${s + 1}.`).join(", ");

/** "1., 2. ve 3. saatlerde olsun; 5. saatte olmasın" (saatler 0'dan başlar). */
export function saatTercihiMetni(saatler: unknown, kacin: unknown): string {
  const parcalar: string[] = [];
  if (Array.isArray(saatler) && saatler.length) parcalar.push(`${saatListesi(saatler)} saatlerde olsun`);
  if (Array.isArray(kacin) && kacin.length) parcalar.push(`${saatListesi(kacin)} saatlerde olmasın`);
  return parcalar.join("; ") || "saat tercihi yok";
}

/** Haftalık yük eşikleri: "en az 15, en çok 30 saat" ya da "eşik yok". */
export function esikMetni(alt: number, ust: number): string {
  if (alt && ust) return `haftada en az ${alt}, en çok ${ust} saat`;
  if (alt) return `haftada en az ${alt} saat`;
  if (ust) return `haftada en çok ${ust} saat`;
  return "yük eşiği yok";
}

/** İkincil kurallar (K6): okul değeri de özel ayarla aynı cümleyle söylenir. */
const CUMLELI_KURALLAR = new Set(["ders_saat_tercihi", "gunluk_en_az_ders", "ders_yayilimi", "haftalik_yuk"]);

/** Okul değeri, aynı dilde: "(okul geneli: 8)". */
export function okulDegeri(kural: Kural): string {
  if (CUMLELI_KURALLAR.has(kural.tur))
    return `okul geneli: ${ozelAyarMetni(kural.tur, { ad: "", kapsam: {}, parametreler: kural.parametreler } as OzelAyar)}`;
  const degerler = Object.values(kural.parametreler);
  return degerler.length === 1 ? `okul geneli: ${degerler[0]}` : "";
}

/**
 * Okul ayarları > Özel ayarlar: okuldaki bütün özel ayarlar tek listede (docs/kisisellestirme-
 * plani.md bölüm 8). Amaç şeffaflık: bir öğretmenin ya da dersin ayarı okul değerinden farklıysa
 * burada görünür, hiçbir istisna gizli kalmaz. Her biri buradan kaldırılabilir; kaldırılınca o yerde
 * okul değeri geçerli olur.
 */
export function OzelAyarlarOzeti({ kurallar, gunlukDersSaati, ogleArasiSonra }: {
  kurallar: Kural[]; gunlukDersSaati: number; ogleArasiSonra?: number | null;
}) {
  const istemci = useQueryClient();
  const [ekleniyor, setEkleniyor] = useState(false);
  const bildirim = useBildirim();
  const satirlar = kurallar.flatMap((kural) => kural.ozel_ayarlar.map((ozel) => ({ kural, ozel })));

  const kaldir = useMutation({
    mutationFn: ({ kural, ozel }: { kural: Kural; ozel: OzelAyar }) => {
      const { ders_id, sinif_id, sube_grubu_id, ogretmen_id } = ozel.kapsam;
      return cagir(api.DELETE("/api/ders-programi/kurallar/{tur}/ozel", {
        params: {
          path: { tur: kural.tur },
          // Boş eksen sorguya hiç konmaz: "ders_id=null" gibi bir değer gitmesin.
          query: {
            ...(ders_id && { ders_id }), ...(sinif_id && { sinif_id }),
            ...(sube_grubu_id && { sube_grubu_id }), ...(ogretmen_id && { ogretmen_id }),
          },
        },
      }));
    },
    onSuccess: (_yanit, { kural, ozel }) =>
      bildirim("basari", `${ozel.ad} için özel ayar kaldırıldı; okul değeri geçerli (${okulDegeri(kural)}).`),
    onSettled: () => istemci.invalidateQueries({ queryKey: ["kurallar"] }),
  });

  return (
    <section className={sayfaStili.kart} aria-labelledby="ozel-ayarlar">
      <h2 id="ozel-ayarlar">Özel ayarlar</h2>
      <p className={stil.aciklama}>
        Bir öğretmene, derse, şubeye ya da şube grubuna okul genelinden farklı bir değer verildiyse burada listelenir.
      </p>
      <FormHatasi mesaj={kaldir.error ? hataMetni(kaldir.error) : undefined} />
      {satirlar.length === 0 ? (
        <p className={stil.bosOzet}>Özel ayar yok: bütün kurallar okul genelinde aynı.</p>
      ) : (
        <ul className={stil.ozelListe} aria-label="Özel ayarlar">
          {satirlar.map(({ kural, ozel }) => (
            <li key={`${kural.tur}-${ozel.kapsam.ogretmen_id}-${ozel.kapsam.ders_id}-${ozel.kapsam.sinif_id}-${ozel.kapsam.sube_grubu_id}`}>
              <span>
                <strong>{ozel.ad}</strong>: {ozelAyarMetni(kural.tur, ozel)}
                <span className={stil.ozelKural}>
                  {kural.ad} ({okulDegeri(kural)})
                </span>
              </span>
              <Dugme tur="metin" ikon={<X />} disabled={kaldir.isPending} aria-label={`${ozel.ad}: ${kural.ad} özel ayarını kaldır`}
                onClick={() => kaldir.mutate({ kural, ozel })}>
                Kaldır
              </Dugme>
            </li>
          ))}
        </ul>
      )}
      {ekleniyor ? (
        <OzelAyarEkle kurallar={kurallar} gunlukDersSaati={gunlukDersSaati} ogleArasiSonra={ogleArasiSonra} onKapat={() => setEkleniyor(false)} />
      ) : (
        <Dugme tur="ikincil" ikon={<Plus />} className={stil.ozelEkleDugmesi} onClick={() => setEkleniyor(true)}>
          Özel ayar ekle
        </Dugme>
      )}
    </section>
  );
}
