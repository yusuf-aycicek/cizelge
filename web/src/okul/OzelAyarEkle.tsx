/**
 * "Özel ayar ekle" (5.6): okul ayarlarındaki özel ayarlar bölümünden her kapsamda özel ayar verilir.
 * Öğretmene özel ayarlar öğretmen sayfasında, derse özel dağılım şekli ders listesinde de verilebilir;
 * gruba ve ders + şubeye / ders + gruba özel ayarların arayüzdeki tek yeri burasıdır.
 *
 * Akış: kural → kapsam (yalnızca o kural için geçerli olanlar; sunucunun `kapsamlar` ve
 * `zorunlu_eksenler` alanlarından) → kayıt seçimi → değer. Kaydetmeden önce sunucu, kapsam
 * önceliğine göre bu ayarın hangi özel ayarları ezdiğini ve hangilerinin altında kaldığını söyler
 * (`/ozel/etki`, çözücüyle aynı hesap); arayüz yalnızca cümleye çevirir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi } from "../bilesenler/form";
import { SEKILLER_ANAHTARI, desenOku } from "../dersler/desen";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi } from "../listeler/kaynaklar";
import { useSubeGruplari } from "../listeler/SubeGruplari";
import { turkceSirala } from "../metin";
import { okulDegeri as okulDegerMetni, ozelAyarMetni } from "./OzelAyarlarOzeti";
import stil from "./Okul.module.css";

type Kural = components["schemas"]["KuralYanit"];
type Etki = components["schemas"]["OzelAyarEtkisi"];
type OzelAyar = components["schemas"]["OzelAyarYanit"];
type Eksen = Kural["kapsamlar"][number];
type KapsamSozlugu = { ders_id?: string; sinif_id?: string; sube_grubu_id?: string; ogretmen_id?: string };

export type KapsamSecenegi = { anahtar: string; eksenler: Eksen[]; etiket: string };

/** Kapsam seçenekleri, kullanıcının diliyle; hangilerinin listeleneceğini kural belirler. */
export const KAPSAM_SECENEKLERI: KapsamSecenegi[] = [
  { anahtar: "ogretmen", eksenler: ["ogretmen"], etiket: "Bir öğretmen" },
  { anahtar: "ders", eksenler: ["ders"], etiket: "Bir ders (bütün şubelerde)" },
  { anahtar: "sube", eksenler: ["sube"], etiket: "Bir şube (bütün dersleri)" },
  { anahtar: "sube_grubu", eksenler: ["sube_grubu"], etiket: "Bir şube grubu (bütün dersleri)" },
  { anahtar: "ders_sube", eksenler: ["ders", "sube"], etiket: "Bir şubede bir ders" },
  { anahtar: "ders_grup", eksenler: ["ders", "sube_grubu"], etiket: "Bir şube grubunda bir ders" },
];

/** Kuralın desteklediği eksenlerden oluşan ve zorunlu eksenlerini (ör. dağılım şekli: ders) içeren seçenekler. */
export function gecerliKapsamlar(kural: Pick<Kural, "kapsamlar" | "zorunlu_eksenler">): KapsamSecenegi[] {
  return KAPSAM_SECENEKLERI.filter(
    (s) => s.eksenler.every((e) => kural.kapsamlar.includes(e)) && kural.zorunlu_eksenler.every((e) => s.eksenler.includes(e)),
  );
}

/** Kuralın özel değeri: hangi parametre, nasıl sorulur. Burada olmayan kural listelenmez. */
type DegerTipi = "sayi" | "bos_gun" | "desen" | "saat_tercihi" | "acik_kapali" | "esikler";
/** Her değer alanı: etiketi ve altında ne işe yaradığını kısa bir örnekle anlatan cümle. */
const DEGERLER: Record<string, { parametre: string; etiket: string; tip: DegerTipi; aciklama?: string }> = {
  gunluk_ders_siniri: {
    parametre: "n", etiket: "Aynı ders günde en çok kaç saat", tip: "sayi",
    aciklama: "Bu ders bir şubeye bir günde en fazla bu kadar saat konur. Ör. 2: Matematik bir günde en çok 2 saat.",
  },
  ogretmen_gunluk_siniri: {
    parametre: "m", etiket: "Günde en çok kaç saat derse girer", tip: "sayi",
    aciklama: "Öğretmen bir günde bundan fazla derse girmez. Ör. 6: 8 saatlik günde en az 2 saati boş kalır.",
  },
  bos_gun: {
    parametre: "hedef_bos_gun", etiket: "Haftada kaç boş gün", tip: "bos_gun",
    aciklama: "Okula gelmeyeceği gün sayısı (hedef). Ör. 1: 5 günlük okulda haftada 4 gün gelir. Esnek kuraldır.",
  },
  blok_deseni: {
    parametre: "desen", etiket: "Dağılım şekli", tip: "desen",
    aciklama: "Dersin haftalık saatleri art arda bloklara bölünür, her blok ayrı bir günde. Ör. 5 saatlik derste "
      + "2+2+1: iki gün ikişer saat art arda, bir gün tek saat. “blok yok”: saatler serbestçe dağılır. Toplamı dersin "
      + "haftalık saatine eşit olmalı; uymayan şube program sayfasında söylenir.",
  },
  // İkincil kurallar (K6).
  ders_saat_tercihi: { parametre: "saatler", etiket: "Saatler", tip: "saat_tercihi" },
  gunluk_en_az_ders: {
    parametre: "k", etiket: "Geldiği günde en az kaç ders (1: sınır yok)", tip: "sayi",
    aciklama: "Öğretmen okula geldiği günde en az bu kadar derse girer. Ör. 2: bir saatlik ders için gelmez.",
  },
  ders_yayilimi: {
    parametre: "yayilsin", etiket: "Art arda günler", tip: "acik_kapali",
    aciklama: "Ör. haftada 2 saatlik Fizik pazartesi ve salıya değil, pazartesi ve perşembeye konmaya çalışılır.",
  },
  haftalik_yuk: { parametre: "alt", etiket: "Haftalık ders yükü", tip: "esikler" },
};

const EKSEN_SUTUNU = { ders: "ders_id", sube: "sinif_id", sube_grubu: "sube_grubu_id", ogretmen: "ogretmen_id" } as const;

/** Okul geneli değer, cümle içinde: "okul geneli 2" ya da dağılım şeklinde "okulun önerisi". */
function okulDegeri(kural: Kural): string {
  if (kural.tur === "blok_deseni") return "okulun önerdiği dağılım şekli";
  if (DEGERLER[kural.tur]?.tip !== "sayi" && DEGERLER[kural.tur]?.tip !== "bos_gun") return okulDegerMetni(kural);
  const d = DEGERLER[kural.tur];
  return d ? `okul geneli: ${String(kural.parametreler[d.parametre])}` : "okul geneli";
}

const liste = (ayarlar: OzelAyar[], tur: string) => ayarlar.map((o) => `${o.ad} (${ozelAyarMetni(tur, o)})`).join(", ");

/**
 * Kapsam önceliğinin sade cümlesi: bu ayar nerede geçerli olur, neyin yerine geçer, nerede daha
 * özel bir ayarın altında kalır. Hesap sunucudan (`etki`); burada yalnızca dil.
 */
export function etkiCumleleri(kural: Kural, kapsamAdi: string, etki: Etki): string[] {
  const cumleler = [`${kapsamAdi} için ${okulDegeri(kural)} yerine bu değer geçerli olur.`];
  if (etki.mevcut) cumleler.push(`${kapsamAdi} için zaten bir özel ayar var (${ozelAyarMetni(kural.tur, etki.mevcut)}); kaydedince değişir.`);
  if (etki.ezdikleri.length) cumleler.push(`Daha genel olan şu özel ayarların yerine geçer: ${liste(etki.ezdikleri, kural.tur)}.`);
  if (etki.ezenler.length)
    cumleler.push(`Daha özel olan şu ayarlar kendi yerlerinde geçerli kalır: ${liste(etki.ezenler, kural.tur)}.`);
  return cumleler;
}

export function OzelAyarEkle({ kurallar, gunlukDersSaati, ogleArasiSonra, onKapat }: {
  kurallar: Kural[]; gunlukDersSaati: number; ogleArasiSonra?: number | null; onKapat: () => void;
}) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const gruplar = useSubeGruplari();
  const kayitlar: Record<Eksen, { id: string; ad: string }[]> = {
    ogretmen: turkceSirala(ogretmenler.data ?? [], (o) => o.ad),
    sube: turkceSirala(siniflar.data ?? [], (s) => s.ad),
    sube_grubu: turkceSirala(gruplar.data ?? [], (g) => g.ad).map((g) => ({ id: g.id, ad: `${g.ad} grubu` })),
    ders: turkceSirala(dersler.data ?? [], (d) => d.ad),
  };
  const EKSEN_ETIKETI: Record<Eksen, string> = { ogretmen: "Öğretmen", ders: "Ders", sube: "Şube", sube_grubu: "Şube grubu" };

  const uygunKurallar = kurallar.filter((k) => DEGERLER[k.tur] && gecerliKapsamlar(k).length > 0);
  const [tur, setTur] = useState("");
  const [kapsamAnahtari, setKapsamAnahtari] = useState("");
  const [secim, setSecim] = useState<Partial<Record<Eksen, string>>>({});
  const [deger, setDeger] = useState("");
  // Saat tercihi: istenen ya da istenmeyen saatler (0'dan başlar). Yük eşikleri: alt ve üst.
  const [saatTuru, setSaatTuru] = useState<"saatler" | "kacin">("saatler");
  const [saatler, setSaatler] = useState<number[]>([]);
  const [esik, setEsik] = useState({ alt: "0", ust: "0" });
  const [hata, setHata] = useState<string>();

  const kural = uygunKurallar.find((k) => k.tur === tur);
  // Kaydı olmayan eksenin seçeneği gösterilmez (ör. okulda hiç şube grubu yoksa grup seçenekleri).
  const kapsamSecenekleri = kural ? gecerliKapsamlar(kural).filter((s) => s.eksenler.every((e) => kayitlar[e].length > 0)) : [];
  const kapsamSecenegi = kapsamSecenekleri.find((s) => s.anahtar === kapsamAnahtari);
  const tamam = kapsamSecenegi?.eksenler.every((e) => secim[e]) ?? false;
  const kapsam: KapsamSozlugu = Object.fromEntries((kapsamSecenegi?.eksenler ?? []).map((e) => [EKSEN_SUTUNU[e], secim[e]]));
  // Sunucunun ad biçimiyle aynı sırada: şube, grup, ders, öğretmen ("9-A · Matematik").
  const kapsamAdi = (["sube", "sube_grubu", "ders", "ogretmen"] as const)
    .filter((e) => kapsamSecenegi?.eksenler.includes(e))
    .map((e) => kayitlar[e].find((k) => k.id === secim[e])?.ad)
    .filter(Boolean)
    .join(" · ");

  const etki = useQuery({
    queryKey: ["ozel-etki", tur, kapsam],
    queryFn: () => cagir(api.GET("/api/ders-programi/kurallar/{tur}/ozel/etki", { params: { path: { tur }, query: kapsam } })),
    enabled: Boolean(kural && tamam),
  });

  const kaydet = useMutation({
    mutationFn: (parametreler: Record<string, number | number[] | boolean>) =>
      cagir(api.PUT("/api/ders-programi/kurallar/{tur}/ozel", { params: { path: { tur } }, body: { kapsam, parametreler } })),
    onSuccess: async (yanit) => {
      await istemci.invalidateQueries({ queryKey: ["kurallar"] });
      await istemci.invalidateQueries({ queryKey: SEKILLER_ANAHTARI });
      const yeni = yanit.ozel_ayarlar.find((o) => (Object.keys(EKSEN_SUTUNU) as Eksen[]).every(
        (e) => (o.kapsam[EKSEN_SUTUNU[e]] ?? undefined) === kapsam[EKSEN_SUTUNU[e]]));
      bildirim("basari", yeni ? `Özel ayar kaydedildi: ${yeni.ad}, ${ozelAyarMetni(tur, yeni)}.` : "Özel ayar kaydedildi.");
      onKapat();
    },
    onError: (h) => setHata(hataMetni(h)),
  });

  function kuralSec(yeniTur: string) {
    setTur(yeniTur);
    const k = uygunKurallar.find((x) => x.tur === yeniTur);
    const d = DEGERLER[yeniTur];
    setDeger(k && d && d.tip !== "desen" ? String(k.parametreler[d.parametre]) : "");
    setSaatTuru("saatler");
    setSaatler([]);
    setEsik({ alt: String(k?.parametreler.alt ?? 0), ust: String(k?.parametreler.ust ?? 0) });
    setKapsamAnahtari("");
    setSecim({});
    setHata(undefined);
  }

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const d = kural && DEGERLER[kural.tur];
    if (!kural || !d) return setHata("Bir kural seçin.");
    if (!kapsamSecenegi || !tamam) return setHata("Ayarın nerede geçerli olacağını seçin.");
    if (d.tip === "desen") {
      const desen = desenOku(deger);
      if (desen === null) return setHata("Dağılım şeklini 2+2+1 biçiminde ya da \"blok yok\" olarak yazın.");
      return kaydet.mutate({ [d.parametre]: desen });
    }
    if (d.tip === "saat_tercihi") {
      if (saatler.length === 0) return setHata("En az bir saat seçin.");
      return kaydet.mutate({ [saatTuru]: saatler });
    }
    if (d.tip === "acik_kapali") return kaydet.mutate({ yayilsin: deger !== "false" });
    if (d.tip === "esikler") {
      const alt = Number(esik.alt), ust = Number(esik.ust);
      if (![alt, ust].every((x) => Number.isInteger(x) && x >= 0 && x <= 60)) return setHata("Eşikler 0 ile 60 arasında olmalı (0: eşik yok).");
      if (alt && ust && alt > ust) return setHata("Alt eşik üst eşikten büyük olamaz.");
      return kaydet.mutate({ alt, ust });
    }
    const sayi = Number(deger);
    const enCok = d.tip === "bos_gun" ? 2 : gunlukDersSaati;
    const enAz = d.tip === "bos_gun" ? 0 : 1;
    if (deger === "" || !Number.isInteger(sayi) || sayi < enAz || sayi > enCok) return setHata(`${enAz} ile ${enCok} arasında bir sayı girin.`);
    kaydet.mutate({ [d.parametre]: sayi });
  }

  const d = kural && DEGERLER[kural.tur];
  return (
    <form className={stil.ozelEkle} onSubmit={gonder} noValidate aria-labelledby="ozel-ekle-baslik">
      <h3 id="ozel-ekle-baslik">Özel ayar ekle</h3>
      <FormHatasi mesaj={hata} />
      <div className={stil.ikili}>
        <SecimAlani etiket="Kural" value={tur} onChange={(o) => kuralSec(o.target.value)}>
          <option value="">Seçin</option>
          {uygunKurallar.map((k) => (
            <option key={k.tur} value={k.tur}>
              {k.ad}
            </option>
          ))}
        </SecimAlani>
        {kural && (
          <SecimAlani etiket="Nerede geçerli" value={kapsamAnahtari}
            onChange={(o) => { setKapsamAnahtari(o.target.value); setSecim({}); }}>
            <option value="">Seçin</option>
            {kapsamSecenekleri.map((s) => (
              <option key={s.anahtar} value={s.anahtar}>
                {s.etiket}
              </option>
            ))}
          </SecimAlani>
        )}
        {kapsamSecenegi?.eksenler.map((e) => (
          <SecimAlani key={e} etiket={EKSEN_ETIKETI[e]} value={secim[e] ?? ""} onChange={(o) => setSecim({ ...secim, [e]: o.target.value })}>
            <option value="">Seçin</option>
            {kayitlar[e].map((k) => (
              <option key={k.id} value={k.id}>
                {k.ad}
              </option>
            ))}
          </SecimAlani>
        ))}
        {d?.tip === "sayi" && (
          <MetinAlani etiket={d.etiket} type="number" inputMode="numeric" min={1} max={gunlukDersSaati} value={deger}
            aciklama={d.aciklama} onChange={(o) => setDeger(o.target.value)} />
        )}
        {d?.tip === "bos_gun" && (
          <SecimAlani etiket={d.etiket} value={deger} aciklama={d.aciklama} onChange={(o) => setDeger(o.target.value)}>
            <option value="0">Boş günü olmasın (0)</option>
            <option value="1">1 boş gün</option>
            <option value="2">2 boş gün</option>
          </SecimAlani>
        )}
        {d?.tip === "acik_kapali" && (
          <SecimAlani etiket={d.etiket} value={deger} aciklama={d.aciklama} onChange={(o) => setDeger(o.target.value)}>
            <option value="true">Art arda günlere konmasın (günlere yayılsın)</option>
            <option value="false">Art arda günlere konabilir</option>
          </SecimAlani>
        )}
        {d?.tip === "esikler" && (
          <>
            <MetinAlani etiket="Alt eşik (saat, 0: yok)" type="number" inputMode="numeric" min={0} max={60} value={esik.alt}
              aciklama="Ör. maaş karşılığı" onChange={(o) => setEsik({ ...esik, alt: o.target.value })} />
            <MetinAlani etiket="Üst eşik (saat, 0: yok)" type="number" inputMode="numeric" min={0} max={60} value={esik.ust}
              aciklama="Ör. ek ders sınırı" onChange={(o) => setEsik({ ...esik, ust: o.target.value })} />
          </>
        )}
        {d?.tip === "desen" && (
          <MetinAlani etiket={d.etiket} placeholder="2+2+1 ya da blok yok" value={deger}
            aciklama={d.aciklama}
            onChange={(o) => setDeger(o.target.value)} />
        )}
      </div>
      {d?.tip === "saat_tercihi" && (
        <fieldset className={stil.saatTercihi}>
          <legend>Dersin saatleri</legend>
          <div className={stil.secenekler}>
            <label className={stil.secenek}>
              <input type="radio" name="saat-turu" checked={saatTuru === "saatler"} onChange={() => setSaatTuru("saatler")} />
              Yalnızca seçilen saatlerde olsun
            </label>
            <label className={stil.secenek}>
              <input type="radio" name="saat-turu" checked={saatTuru === "kacin"} onChange={() => setSaatTuru("kacin")} />
              Seçilen saatlerde olmasın
            </label>
          </div>
          <div className={stil.saatKutulari}>
            {Array.from({ length: gunlukDersSaati }, (_, s) => (
              <label key={s} className={stil.secenek}>
                <input type="checkbox" checked={saatler.includes(s)}
                  onChange={(o) => setSaatler(o.target.checked ? [...saatler, s].sort((a, b) => a - b) : saatler.filter((x) => x !== s))} />
                {s + 1}. ders{ogleArasiSonra && s === ogleArasiSonra ? " (öğle arasından hemen sonra)" : ""}
              </label>
            ))}
          </div>
          {ogleArasiSonra ? (
            <Dugme tur="metin" type="button" onClick={() => { setSaatTuru("saatler"); setSaatler(Array.from({ length: ogleArasiSonra }, (_, s) => s)); }}>
              Sabah saatlerini seç (öğle arasından önce)
            </Dugme>
          ) : null}
          <p className={stil.aciklama}>Esnek kuraldır: program olabildiğince uyar, başka bir zorunluluk varsa ayrılabilir.</p>
        </fieldset>
      )}
      {kural && tamam && etki.data && (
        <div className={stil.etkiKutusu} role="status" aria-label="Bu ayarın etkisi">
          {etkiCumleleri(kural, kapsamAdi, etki.data).map((c) => (
            <p key={c}>{c}</p>
          ))}
        </div>
      )}
      {etki.isError && <FormHatasi mesaj={hataMetni(etki.error)} />}
      <div className={stil.dugmeler}>
        <Dugme ikon={<Check />} type="submit" yukleniyor={kaydet.isPending} yukleniyorMetni="Kaydediliyor...">
          Özel ayarı kaydet
        </Dugme>
        <Dugme ikon={<X />} tur="ikincil" type="button" onClick={onKapat}>
          Vazgeç
        </Dugme>
      </div>
    </form>
  );
}

