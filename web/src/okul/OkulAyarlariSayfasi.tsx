import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Settings } from "lucide-react";
import { Iskelet } from "../bilesenler/Iskelet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState, type FormEvent } from "react";
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
import { GUN_ADLARI } from "../program/aciklama";
import { BlokBolumu } from "./BlokBolumu";
import { OzelAyarlarOzeti } from "./OzelAyarlarOzeti";
import { kisaliyor, ogleArasiSonrasi, ogleArasiZili, zilMetni, zilSaatleri } from "./zaman";

type Okul = components["schemas"]["OkulYanit"];
type Kural = components["schemas"]["KuralYanit"];
type Seviye = "onemsiz" | "onemli" | "cok_onemli";

export const OKUL_ANAHTARI = ["okul"] as const;
export const KURALLAR_ANAHTARI = ["kurallar"] as const;

/** Zil saatleri ilk açıldığında önerilen başlangıç (CLAUDE.md bölüm 10). */
const VARSAYILAN_BASLANGIC = "08:30";

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
 * Okul ayarları: okul bilgileri, kurallar, özel ayarların özeti ve (Gelişmiş) kuralların önemi.
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
          <BlokBolumu key={`blok-${JSON.stringify(kurallar.data)}`} kurallar={kurallar.data} okul={okul.data}
            onKaydet={() => kurallar.refetch()} />
          <OzelAyarlarOzeti kurallar={kurallar.data} />
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
  const [d, setD] = useState({
    ad: okul.ad,
    gun: String(okul.gun_sayisi),
    saat: String(okul.gunluk_ders_saati),
    farkli: new Set(okul.gun_saatleri).size > 1,
    gunler: okul.gun_saatleri.map(String),
    ogle: okul.ogle_arasi_sonra == null ? "" : String(okul.ogle_arasi_sonra),
    zil: okul.ilk_ders_baslangic != null,
    baslangic: okul.ilk_ders_baslangic?.slice(0, 5) ?? VARSAYILAN_BASLANGIC,
    ders: String(okul.ders_suresi_dk),
    teneffus: String(okul.teneffus_dk),
    ogleDk: String(okul.ogle_arasi_dk),
  });
  const [hatalar, setHatalar] = useState<AlanHatalari>({});
  const [etkiler, setEtkiler] = useState<string[] | null>(null);

  const yeniGun = Number(d.gun);
  // Gün sayısı değişince günlere göre liste kısalır ya da yeni günler ilk günün uzunluğuyla eklenir.
  const gunler = Array.from({ length: yeniGun }, (_, g) => d.gunler[g] ?? d.gunler[0] ?? d.saat);
  const yeniSaatler = d.farkli ? gunler.map(Number) : Array<number>(yeniGun).fill(Number(d.saat));
  const enUzun = Math.max(...yeniSaatler.filter(Number.isFinite), 1);
  const azaliyor = kisaliyor(okul.gun_saatleri, yeniSaatler);
  const hafta = {
    gun_saatleri: yeniSaatler,
    ogle_arasi_sonra: d.ogle ? Number(d.ogle) : null,
    ilk_ders_baslangic: d.zil ? d.baslangic : null,
    ders_suresi_dk: Number(d.ders),
    teneffus_dk: Number(d.teneffus),
    ogle_arasi_dk: Number(d.ogleDk),
  };
  // Hafta: "her gün aynı" ise tek sayı, değilse günlere göre liste gider (sunucu tek gösterime getirir).
  const haftaGovdesi = d.farkli
    ? { gun_sayisi: yeniGun, gun_saatleri: yeniSaatler }
    : { gun_sayisi: yeniGun, gunluk_ders_saati: Number(d.saat), gun_saatleri: null };

  const kaydet = useMutation({
    mutationFn: (etkileriOnayla: boolean) =>
      cagir(api.PATCH("/api/okul", {
        body: {
          ad: d.ad.trim(),
          ...haftaGovdesi,
          ogle_arasi_sonra: hafta.ogle_arasi_sonra,
          ilk_ders_baslangic: hafta.ilk_ders_baslangic,
          ders_suresi_dk: hafta.ders_suresi_dk,
          teneffus_dk: hafta.teneffus_dk,
          ogle_arasi_dk: hafta.ogle_arasi_dk,
          etkileri_onayla: etkileriOnayla,
        },
      })),
    onSuccess: (yeni) => {
      setEtkiler(null);
      istemci.setQueryData(OKUL_ANAHTARI, yeni);
      istemci.setQueryData<Ben | null>(BEN_ANAHTARI, (ben) => (ben ? { ...ben, okul: yeni } : ben));
      // Silinen kayıtlar başka sayfalarda görünmesin; gün uzunluğu ön kontrolü ve özetleri de değiştirir.
      istemci.invalidateQueries({ predicate: (s) => s.queryKey[0] !== OKUL_ANAHTARI[0] && s.queryKey[0] !== BEN_ANAHTARI[0] });
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

  // Önizleme: bir gün kısalıyorsa ya da gün azalıyorsa kaydetmeden önce etkiler sorulur (ADR 0014).
  const onizle = useMutation({
    mutationFn: () => cagir(api.POST("/api/okul/ayar-etkisi", { body: haftaGovdesi })),
    onSuccess: ({ etkiler: liste }) => (liste.length > 0 ? setEtkiler(liste) : kaydet.mutate(false)),
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const h: AlanHatalari = {};
    const saatGecersiz = (s: string) => !Number.isInteger(Number(s)) || Number(s) < 1 || Number(s) > 16;
    if (!d.ad.trim()) h.ad = "Okulun adını girin";
    if (!d.farkli && saatGecersiz(d.saat)) h.gunluk_ders_saati = "1 ile 16 arasında bir sayı girin";
    if (d.farkli) gunler.forEach((s, g) => saatGecersiz(s) && (h[`gun-${g}`] = "1 ile 16 arasında"));
    if (hafta.ogle_arasi_sonra != null && hafta.ogle_arasi_sonra >= enUzun) h.ogle_arasi_sonra = "Öğle arası son dersten önce olmalı";
    if (d.zil) {
      if (!/^\d{2}:\d{2}$/.test(d.baslangic)) h.ilk_ders_baslangic = "Saati 08:30 biçiminde girin";
      const dk = (s: string, alt: number, ust: number, alan: string) =>
        (!Number.isInteger(Number(s)) || Number(s) < alt || Number(s) > ust) && (h[alan] = `${alt} ile ${ust} arasında bir sayı girin`);
      dk(d.ders, 10, 120, "ders_suresi_dk");
      dk(d.teneffus, 0, 60, "teneffus_dk");
      if (d.ogle) dk(d.ogleDk, 0, 180, "ogle_arasi_dk");
    }
    setHatalar(h);
    if (Object.keys(h).length > 0) return;
    if (azaliyor) onizle.mutate();
    else kaydet.mutate(false);
  }

  const sunucu = sunucuHatalari(etkiler ? null : (kaydet.error ?? onizle.error));
  const hata = (alan: string) => hatalar[alan] ?? sunucu.alanlar[alan];
  const gunSecenekleri = [...new Set([5, 6, okul.gun_sayisi])].sort();
  const zil = d.zil ? zilSaatleri(hafta, enUzun) : null;
  const ogleZili = ogleArasiZili(hafta, zil);

  function farkliyiDegistir(acik: boolean) {
    // Açılınca her gün bugünkü tek değerle başlar; kapanınca en uzun gün "her gün" değeri olur.
    if (acik) setD({ ...d, farkli: true, gunler: Array<string>(yeniGun).fill(d.saat) });
    else setD({ ...d, farkli: false, saat: String(enUzun) });
  }

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
          {!d.farkli && (
            <MetinAlani etiket="Günde kaç ders saati var" type="number" inputMode="numeric" min={1} max={16}
              value={d.saat} onChange={(o) => setD({ ...d, saat: o.target.value })} hata={hata("gunluk_ders_saati")} />
          )}
        </div>
        <label className={stil.secenek}>
          <input type="checkbox" checked={d.farkli} onChange={(o) => farkliyiDegistir(o.target.checked)} />
          Günlere göre farklı (ör. cuma daha kısa)
        </label>
        {d.farkli && (
          <fieldset className={stil.grup}>
            <legend>Her gün kaç ders saati var</legend>
            <div className={stil.gunler}>
              {gunler.map((s, g) => (
                <MetinAlani key={g} etiket={GUN_ADLARI[g] ?? `${g + 1}. gün`} type="number" inputMode="numeric" min={1} max={16}
                  value={s} hata={hata(`gun-${g}`)}
                  onChange={(o) => setD({ ...d, gunler: gunler.map((x, i) => (i === g ? o.target.value : x)) })} />
              ))}
            </div>
          </fieldset>
        )}

        <div className={stil.ikili}>
          <SecimAlani etiket="Öğle arası" value={d.ogle} onChange={(o) => setD({ ...d, ogle: o.target.value })}
            hata={hata("ogle_arasi_sonra")} aciklama="Haftalık çizelgede iki ders arasında ayraç olarak görünür.">
            <option value="">Öğle arası yok</option>
            {Array.from({ length: Math.max(0, enUzun - 1) }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>{n}. dersten sonra</option>
            ))}
          </SecimAlani>
        </div>

        <label className={stil.secenek}>
          <input type="checkbox" checked={d.zil} onChange={(o) => setD({ ...d, zil: o.target.checked })} />
          Zil saatlerini göster (çizelgede "1. saat" altında 08:30–09:10 gibi)
        </label>
        {d.zil && (
          <fieldset className={stil.grup}>
            <legend>Zil saatleri</legend>
            <div className={stil.dortlu}>
              <MetinAlani etiket="İlk ders başlıyor" type="time" value={d.baslangic} hata={hata("ilk_ders_baslangic")}
                onChange={(o) => setD({ ...d, baslangic: o.target.value })} />
              <MetinAlani etiket="Ders süresi (dk)" type="number" inputMode="numeric" value={d.ders} hata={hata("ders_suresi_dk")}
                onChange={(o) => setD({ ...d, ders: o.target.value })} />
              <MetinAlani etiket="Teneffüs (dk)" type="number" inputMode="numeric" value={d.teneffus} hata={hata("teneffus_dk")}
                onChange={(o) => setD({ ...d, teneffus: o.target.value })} />
              {d.ogle && (
                <MetinAlani etiket="Öğle arası (dk)" type="number" inputMode="numeric" value={d.ogleDk} hata={hata("ogle_arasi_dk")}
                  onChange={(o) => setD({ ...d, ogleDk: o.target.value })} />
              )}
            </div>
            {zil && (
              <ol className={stil.zilOnizleme} aria-label="Zil saatleri önizlemesi">
                {zil.map((z, s) => (
                  <Fragment key={s}>
                    <li>
                      <span>{s + 1}. ders</span> {zilMetni(z)}
                    </li>
                    {ogleArasiSonrasi(hafta.ogle_arasi_sonra, s) && ogleZili && (
                      <li className={stil.zilOgle} aria-label={`Öğle arası ${zilMetni(ogleZili)}`}>
                        Öğle arası {zilMetni(ogleZili)}
                      </li>
                    )}
                  </Fragment>
                ))}
              </ol>
            )}
          </fieldset>
        )}

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
