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
import { ozelAyarMetni } from "./OzelAyarlarOzeti";
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
const DEGERLER: Record<string, { parametre: string; etiket: string; tip: "sayi" | "bos_gun" | "desen" }> = {
  gunluk_ders_siniri: { parametre: "n", etiket: "Aynı ders günde en çok kaç saat", tip: "sayi" },
  ogretmen_gunluk_siniri: { parametre: "m", etiket: "Günde en çok kaç saat derse girer", tip: "sayi" },
  bos_gun: { parametre: "hedef_bos_gun", etiket: "Haftada kaç boş gün", tip: "bos_gun" },
  blok_deseni: { parametre: "desen", etiket: "Dağılım şekli", tip: "desen" },
};

const EKSEN_SUTUNU = { ders: "ders_id", sube: "sinif_id", sube_grubu: "sube_grubu_id", ogretmen: "ogretmen_id" } as const;

/** Okul geneli değer, cümle içinde: "okul geneli 2" ya da dağılım şeklinde "okulun önerisi". */
function okulDegeri(kural: Kural): string {
  if (kural.tur === "blok_deseni") return "okulun önerdiği dağılım şekli";
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

export function OzelAyarEkle({ kurallar, gunlukDersSaati, onKapat }: { kurallar: Kural[]; gunlukDersSaati: number; onKapat: () => void }) {
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
    mutationFn: (parametreler: Record<string, number | number[]>) =>
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
            onChange={(o) => setDeger(o.target.value)} />
        )}
        {d?.tip === "bos_gun" && (
          <SecimAlani etiket={d.etiket} value={deger} onChange={(o) => setDeger(o.target.value)}>
            <option value="0">Boş günü olmasın (0)</option>
            <option value="1">1 boş gün</option>
            <option value="2">2 boş gün</option>
          </SecimAlani>
        )}
        {d?.tip === "desen" && (
          <MetinAlani etiket={d.etiket} placeholder="2+2+1 ya da blok yok" value={deger}
            aciklama="Toplamı dersin haftalık saatine eşit olmalı; uymayan şube program sayfasında söylenir."
            onChange={(o) => setDeger(o.target.value)} />
        )}
      </div>
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

