import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Settings } from "lucide-react";
import { Iskelet } from "../bilesenler/Iskelet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiHatasi, cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, type AlanHatalari } from "../bilesenler/form";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { BEN_ANAHTARI, type Ben } from "../kimlik/oturum";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Okul.module.css";

type Okul = components["schemas"]["OkulYanit"];
type Kural = components["schemas"]["KuralYanit"];
type Seviye = "onemsiz" | "onemli" | "cok_onemli";

export const OKUL_ANAHTARI = ["okul"] as const;
export const KURALLAR_ANAHTARI = ["kurallar"] as const;

const SEVIYELER: { deger: Seviye; ad: string }[] = [
  { deger: "onemsiz", ad: "Önemsiz" },
  { deger: "onemli", ad: "Önemli" },
  { deger: "cok_onemli", ad: "Çok önemli" },
];

/** Kurallar bölümünde sayıyla ayarlanan kurallar: tür → parametre adı. */
const SAYI_AYARLARI: Record<string, string> = {
  gunluk_ders_siniri: "n",
  ogretmen_gunluk_siniri: "m",
  bos_gun: "hedef_bos_gun",
};

/**
 * Okul ayarları: okul bilgileri, kurallar ve (Gelişmiş) kuralların önemi.
 *
 * Sayfa veriyi yükler; her bölüm ayrı bir bileşendir ve kendi formunu yönetir. Bölümlere
 * `key` verilir: sunucudaki değer değişince (kaydedince) bölüm yeni değerle baştan kurulur.
 */
export function OkulAyarlariSayfasi() {
  const okul = useQuery({ queryKey: OKUL_ANAHTARI, queryFn: () => cagir(api.GET("/api/okul")) });
  const kurallar = useQuery({ queryKey: KURALLAR_ANAHTARI, queryFn: () => cagir(api.GET("/api/ders-programi/kurallar")) });

  return (
    <>
      <SayfaBasligi ikon={Settings} baslik="Okul ayarları">
        Okulunuzun haftalık düzeni ve program hazırlanırken uyulacak kurallar.
      </SayfaBasligi>
      {(okul.isPending || kurallar.isPending) && <Iskelet satir={4} kart />}
      {(okul.isError || kurallar.isError) && (
        <div className={sayfaStili.hataKutusu} role="alert">
          {hataMetni(okul.error ?? kurallar.error)}
        </div>
      )}
      {okul.data && <OkulBilgileri key={JSON.stringify(okul.data)} okul={okul.data} />}
      {okul.data && kurallar.data && (
        <>
          <KurallarBolumu key={JSON.stringify(kurallar.data)} okul={okul.data} kurallar={kurallar.data} />
          <OnemBolumu key={`onem-${JSON.stringify(kurallar.data)}`} kurallar={kurallar.data} />
        </>
      )}
    </>
  );
}

// --- okul bilgileri ---------------------------------------------------------------------------

function OkulBilgileri({ okul }: { okul: Okul }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  // State'in başlangıç değeri props'tan: yalnızca ilk çizimde okunur. Sunucudaki değer değişince
  // üst bileşen `key`'i değiştirir ve bu bileşen yeni değerle baştan kurulur.
  const [d, setD] = useState({ ad: okul.ad, gun: String(okul.gun_sayisi), saat: String(okul.gunluk_ders_saati) });
  const [hatalar, setHatalar] = useState<AlanHatalari>({});
  const [etkiler, setEtkiler] = useState<string[] | null>(null);

  const yeniGun = Number(d.gun);
  const yeniSaat = Number(d.saat);
  const azaliyor = yeniGun < okul.gun_sayisi || yeniSaat < okul.gunluk_ders_saati;

  const kaydet = useMutation({
    mutationFn: (etkileriOnayla: boolean) =>
      cagir(api.PATCH("/api/okul", {
        body: { ad: d.ad.trim(), gun_sayisi: yeniGun, gunluk_ders_saati: yeniSaat, etkileri_onayla: etkileriOnayla },
      })),
    onSuccess: (yeni, etkileriOnayla) => {
      setEtkiler(null);
      istemci.setQueryData(OKUL_ANAHTARI, yeni);
      istemci.setQueryData<Ben | null>(BEN_ANAHTARI, (ben) => (ben ? { ...ben, okul: yeni } : ben));
      if (etkileriOnayla) istemci.invalidateQueries(); // silinen kayıtlar başka sayfalarda da görünmesin
      bildirim("basari", "Okul bilgileri kaydedildi.");
    },
    onError: (hata) => {
      // Önizlemeden sonra başka biri veri eklediyse sunucu yine etkileri listeler (409).
      const govde = hata instanceof ApiHatasi ? (hata.govde as { etkiler?: unknown }) : undefined;
      if (hata instanceof ApiHatasi && hata.durum === 409 && Array.isArray(govde?.etkiler)) {
        setEtkiler(govde.etkiler as string[]);
      }
    },
  });

  // Önizleme: azaltma varsa kaydetmeden önce etkiler sorulur.
  const onizle = useMutation({
    mutationFn: () => cagir(api.POST("/api/okul/ayar-etkisi", { body: { gun_sayisi: yeniGun, gunluk_ders_saati: yeniSaat } })),
    onSuccess: ({ etkiler: liste }) => (liste.length > 0 ? setEtkiler(liste) : kaydet.mutate(false)),
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const h: AlanHatalari = {};
    if (!d.ad.trim()) h.ad = "Okulun adını girin";
    if (!Number.isInteger(yeniSaat) || yeniSaat < 1 || yeniSaat > 16) h.gunluk_ders_saati = "1 ile 16 arasında bir sayı girin";
    setHatalar(h);
    if (Object.keys(h).length > 0) return;
    if (azaliyor) onizle.mutate();
    else kaydet.mutate(false);
  }

  const sunucu = sunucuHatalari(etkiler ? null : (kaydet.error ?? onizle.error));
  const hata = (alan: string) => hatalar[alan] ?? sunucu.alanlar[alan];
  const gunSecenekleri = [...new Set([5, 6, okul.gun_sayisi])].sort();

  return (
    <section className={sayfaStili.kart} aria-labelledby="okul-bilgileri">
      <h2 id="okul-bilgileri">Okul bilgileri</h2>
      <FormHatasi mesaj={sunucu.genel} />
      <form noValidate onSubmit={gonder}>
        <MetinAlani etiket="Okulun adı" gerekli value={d.ad} onChange={(o) => setD({ ...d, ad: o.target.value })} hata={hata("ad")} />
        <div className={stil.ikili}>
          <SecimAlani etiket="Haftada kaç gün ders var" value={d.gun} onChange={(o) => setD({ ...d, gun: o.target.value })}
            hata={hata("gun_sayisi")}>
            {gunSecenekleri.map((g) => (
              <option key={g} value={g}>{g} gün</option>
            ))}
          </SecimAlani>
          <MetinAlani etiket="Günde kaç ders saati var" type="number" inputMode="numeric" min={1} max={16}
            value={d.saat} onChange={(o) => setD({ ...d, saat: o.target.value })} hata={hata("gunluk_ders_saati")} />
        </div>
        {azaliyor && (
          <p className={stil.uyari} role="note">
            Gün ya da ders saati sayısını azaltıyorsunuz. Yeni ayarların dışında kalan müsaitlik kayıtları
            silinir; daha önce üretilmiş programlar değişmez ama yeniden üretilmeleri gerekir. Kaydetmeden önce
            okulunuzda tam olarak neyin etkileneceği size gösterilecek.
          </p>
        )}
        <Dugme type="submit" yukleniyor={kaydet.isPending || onizle.isPending} yukleniyorMetni="Kaydediliyor...">
          Kaydet
        </Dugme>
      </form>

      <OnayPenceresi
        acik={etkiler !== null}
        baslik="Bu değişiklik mevcut kayıtları etkileyecek"
        mesaj="Kaydederseniz şunlar olacak:"
        onaylaMetni="Kaydet ve uygula"
        tehlikeli
        yukleniyor={kaydet.isPending}
        onVazgec={() => setEtkiler(null)}
        onOnayla={() => kaydet.mutate(true)}
      >
        <ul className={stil.etkiler}>
          {(etkiler ?? []).map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      </OnayPenceresi>
    </section>
  );
}

// --- kurallar (sayıyla ayarlananlar) ---------------------------------------------------------

function KurallarBolumu({ okul, kurallar }: { okul: Okul; kurallar: Kural[] }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const sayili = kurallar.filter((k) => SAYI_AYARLARI[k.tur]);
  const [d, setD] = useState<Record<string, string>>(
    Object.fromEntries(sayili.map((k) => [k.tur, String(k.parametreler[SAYI_AYARLARI[k.tur]!] ?? "")])),
  );
  const [hatalar, setHatalar] = useState<AlanHatalari>({});

  const sinirlar: Record<string, [number, number]> = {
    gunluk_ders_siniri: [1, okul.gunluk_ders_saati],
    ogretmen_gunluk_siniri: [1, okul.gunluk_ders_saati],
    bos_gun: [0, okul.gun_sayisi - 1],
  };

  const kaydet = useMutation({
    mutationFn: async () => {
      for (const k of sayili) {
        const ad = SAYI_AYARLARI[k.tur]!;
        if (Number(d[k.tur]) !== k.parametreler[ad]) {
          await cagir(api.PUT("/api/ders-programi/kurallar/{tur}", {
            params: { path: { tur: k.tur } },
            body: { parametreler: { [ad]: Number(d[k.tur]) } },
          }));
        }
      }
    },
    onSuccess: () => bildirim("basari", "Kurallar kaydedildi."),
    onSettled: () => istemci.invalidateQueries({ queryKey: KURALLAR_ANAHTARI }),
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const h: AlanHatalari = {};
    for (const k of sayili) {
      const [alt, ust] = sinirlar[k.tur]!;
      const n = Number(d[k.tur]);
      if (!Number.isInteger(n) || n < alt || n > ust) h[k.tur] = `${alt} ile ${ust} arasında bir sayı girin`;
    }
    setHatalar(h);
    if (Object.keys(h).length === 0) kaydet.mutate();
  }

  return (
    <section className={sayfaStili.kart} aria-labelledby="kurallar">
      <h2 id="kurallar">Kurallar</h2>
      <FormHatasi mesaj={kaydet.error ? hataMetni(kaydet.error) : undefined} />
      <form noValidate onSubmit={gonder}>
        {sayili.map((k) => {
          const ad = SAYI_AYARLARI[k.tur]!;
          const varsayilan = k.varsayilan_parametreler[ad];
          return (
            <MetinAlani key={k.tur} etiket={k.ad} type="number" inputMode="numeric" value={d[k.tur] ?? ""}
              onChange={(o) => setD({ ...d, [k.tur]: o.target.value })} hata={hatalar[k.tur]}
              aciklama={`${k.aciklama} Varsayılan: ${varsayilan}.`} />
          );
        })}
        <Dugme type="submit" yukleniyor={kaydet.isPending} yukleniyorMetni="Kaydediliyor...">
          Kuralları kaydet
        </Dugme>
      </form>
    </section>
  );
}

// --- gelişmiş: esnek kuralların önemi ---------------------------------------------------------

function OnemBolumu({ kurallar }: { kurallar: Kural[] }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const esnek = kurallar.filter((k) => !k.zorunlu);
  const [secim, setSecim] = useState<Record<string, string>>(Object.fromEntries(esnek.map((k) => [k.tur, k.seviye ?? "onemli"])));
  const degisen = esnek.filter((k) => secim[k.tur] !== k.seviye && secim[k.tur] !== "ozel");

  const kaydet = useMutation({
    mutationFn: async () => {
      for (const k of degisen) {
        await cagir(api.PUT("/api/ders-programi/kurallar/{tur}", {
          params: { path: { tur: k.tur } },
          body: { seviye: secim[k.tur] as Seviye },
        }));
      }
    },
    onSuccess: () => bildirim("basari", "Kuralların önemi kaydedildi."),
    onSettled: () => istemci.invalidateQueries({ queryKey: KURALLAR_ANAHTARI }),
  });

  return (
    <details className={`${sayfaStili.kart} ${stil.gelismis}`}>
      <summary>
        <h2>Gelişmiş: kuralların önemi</h2>
      </summary>
      <p className={stil.aciklama}>
        Program bu kurallara olabildiğince uyar. İki kural çatıştığında daha önemli olan seçilir.
        Varsayılan ayarlar çoğu okul için uygundur.
      </p>
      <FormHatasi mesaj={kaydet.error ? hataMetni(kaydet.error) : undefined} />
      <form noValidate onSubmit={(o) => { o.preventDefault(); kaydet.mutate(); }}>
        {esnek.map((k) => (
          // fieldset + legend: ekran okuyucu her seçeneği kuralın adıyla birlikte okur.
          <fieldset key={k.tur} className={stil.kural} aria-describedby={`${k.tur}-aciklama`}>
            <legend>{k.ad}</legend>
            <p id={`${k.tur}-aciklama`} className={stil.aciklama}>
              {k.aciklama}
            </p>
            <div className={stil.secenekler}>
              {SEVIYELER.map((s) => (
                <label key={s.deger} className={stil.secenek}>
                  <input type="radio" name={k.tur} value={s.deger} checked={secim[k.tur] === s.deger}
                    onChange={() => setSecim({ ...secim, [k.tur]: s.deger })} />
                  {s.ad}
                  {s.deger === k.varsayilan_seviye && <span className={stil.varsayilan}> (varsayılan)</span>}
                </label>
              ))}
            </div>
            {k.seviye === "ozel" && secim[k.tur] === "ozel" && (
              <p className={stil.uyari}>Bu kural için elle girilmiş özel bir değer var ({k.agirlik}). Bir seviye seçerseniz değişir.</p>
            )}
          </fieldset>
        ))}
        <div className={stil.dugmeler}>
          <Dugme type="submit" disabled={degisen.length === 0} yukleniyor={kaydet.isPending} yukleniyorMetni="Kaydediliyor...">
            Önemleri kaydet
          </Dugme>
          <Dugme tur="ikincil"
            onClick={() => setSecim(Object.fromEntries(esnek.map((k) => [k.tur, k.varsayilan_seviye ?? "onemli"])))}>
            Varsayılanlara dön
          </Dugme>
        </div>
      </form>
    </details>
  );
}
