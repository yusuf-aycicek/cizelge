import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { useBildirim } from "../bilesenler/Bildirim";
import { OZET } from "../dagilim/veri";
import { KURALLAR_ANAHTARI } from "../okul/OkulAyarlariSayfasi";
import { ON_KONTROL } from "../program/veri";
import stil from "./Ogretmen.module.css";
import { musaitlikAnahtari } from "./veri";

type Kural = components["schemas"]["KuralYanit"];

/** Öğretmene özel ayarlanabilen kurallar: parametresi, seçenekleri ve kullanıcı dili. */
type AyarTanimi = {
  tur: string;
  parametre: string;
  etiket: string;
  aciklama: string;
  secenekler: (okul: { gun_sayisi: number; gunluk_ders_saati: number }) => number[];
  deger: (n: number) => string;
};

export const OGRETMEN_AYARLARI: AyarTanimi[] = [
  {
    tur: "bos_gun",
    parametre: "hedef_bos_gun",
    etiket: "Boş gün hedefi",
    aciklama: "Haftada kaç gün okula gelmesin. Özel bir değer verilirse hedeften az gelmek de istenmez (0: her gün gelmek istiyor).",
    secenekler: (o) => Array.from({ length: o.gun_sayisi }, (_, i) => i),
    deger: (n) => (n === 0 ? "0 (boş gün istemiyor)" : `${n} gün`),
  },
  {
    tur: "ogretmen_gunluk_siniri",
    parametre: "m",
    etiket: "Günde en çok ders",
    aciklama: "Bir günde en fazla kaç saat derse girer.",
    secenekler: (o) => Array.from({ length: o.gunluk_ders_saati }, (_, i) => i + 1),
    deger: (n) => `${n} saat`,
  },
];

/**
 * Öğretmenin kişisel ayarları. Her alanın ilk seçeneği "Okul varsayılanı (…)": seçilirse özel
 * ayar silinir, okulun değeri geçerli olur. Özel değer verilmiş alanın yanında "özel" rozeti
 * görünür. Seçim anında kaydedilir.
 */
export function KisiselAyarlar({ ogretmenId, kurallar, okul }: {
  ogretmenId: string;
  kurallar: Kural[];
  okul: { gun_sayisi: number; gunluk_ders_saati: number };
}) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const kaydet = useMutation({
    mutationFn: ({ tanim, deger }: { tanim: AyarTanimi; deger: number | null }) =>
      deger === null
        ? cagir(api.DELETE("/api/ders-programi/kurallar/{tur}/ozel", {
            params: { path: { tur: tanim.tur }, query: { ogretmen_id: ogretmenId } },
          }))
        : cagir(api.PUT("/api/ders-programi/kurallar/{tur}/ozel", {
            params: { path: { tur: tanim.tur } },
            body: { kapsam: { ogretmen_id: ogretmenId }, parametreler: { [tanim.parametre]: deger } },
          })),
    onSuccess: (_y, { tanim, deger }) =>
      bildirim("basari", `${tanim.etiket}: ${deger === null ? "okul varsayılanı" : tanim.deger(deger)} kaydedildi.`),
    onError: (hata) => bildirim("hata", hataMetni(hata)),
    onSettled: () => {
      void istemci.invalidateQueries({ queryKey: KURALLAR_ANAHTARI });
      // Günlük sınır kullanılabilir saati değiştirir: kapasite uyarısı ve ön kontrol tazelensin.
      void istemci.invalidateQueries({ queryKey: musaitlikAnahtari(ogretmenId) });
      void istemci.invalidateQueries({ queryKey: OZET });
      void istemci.invalidateQueries({ queryKey: ON_KONTROL });
    },
  });

  return (
    <section aria-labelledby="kisisel-baslik" className={stil.kart}>
      <h2 id="kisisel-baslik">Kişisel ayarlar</h2>
      <div className={stil.ayarlar}>
        {OGRETMEN_AYARLARI.map((tanim) => {
          const kural = kurallar.find((k) => k.tur === tanim.tur);
          if (!kural || !kural.kapsamlar.includes("ogretmen")) return null;
          const okulDegeri = kural.parametreler[tanim.parametre]!;
          const ozel = kural.ozel_ayarlar.find((o) => o.kapsam.ogretmen_id === ogretmenId);
          const deger = ozel?.parametreler[tanim.parametre];
          const id = `ayar-${tanim.tur}`;
          return (
            <div key={tanim.tur} className={stil.ayar}>
              <label htmlFor={id} className={stil.ayarEtiketi}>
                {tanim.etiket}
                {ozel && <span className={stil.ozelRozeti}>özel</span>}
              </label>
              <select
                id={id}
                className={stil.secim}
                value={deger === undefined ? "" : String(deger)}
                disabled={kaydet.isPending}
                aria-describedby={`${id}-aciklama`}
                onChange={(o) => kaydet.mutate({ tanim, deger: o.target.value === "" ? null : Number(o.target.value) })}
              >
                <option value="">Okul varsayılanı ({tanim.deger(okulDegeri)})</option>
                {tanim.secenekler(okul).map((n) => (
                  <option key={n} value={n}>
                    {tanim.deger(n)}
                  </option>
                ))}
              </select>
              <p id={`${id}-aciklama`} className={stil.ayarAciklama}>
                {tanim.aciklama}
                {!kural.zorunlu && kural.agirlik === 0 && " Bu kural okulda kapalı (Okul ayarları > kuralların önemi)."}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
