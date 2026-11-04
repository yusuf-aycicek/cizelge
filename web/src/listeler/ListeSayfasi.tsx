import { BosDurum } from "../bilesenler/BosDurum";
import type { IllustrasyonTuru } from "../bilesenler/Illustrasyon";
import type { ReactNode } from "react";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Check, Pencil, Plus, RotateCcw, Trash2, X } from "lucide-react";
import { cikistanSonra } from "../bilesenler/hareket";
import { Iskelet } from "../bilesenler/Iskelet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { hataMetni } from "../api/hata";
import { MetinAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, useIlkHatayaOdaklan, type AlanHatalari } from "../bilesenler/form";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { Tablo, type Sutun } from "../bilesenler/Tablo";
import { turkceIcerir, turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import type { Kaynak } from "./kaynaklar";
import stil from "./Liste.module.css";

export type ListeAlani = {
  /** API'deki alan adı: "ad", "brans", "seviye", "kisa_ad". */
  ad: string;
  etiket: string;
  tur?: "metin" | "sayi";
  gerekli?: boolean;
  min?: number;
  max?: number;
  /** Boş kutuda gösterilen örnek, ör. "9-A". */
  ornek?: string;
  /**
   * Metin kutusu yerine özel denetim (ör. branş: derslerden çoklu seçim). Değer yine metindir;
   * hem ekleme formunda hem satırda düzenlerken kullanılır.
   */
  secici?: (p: { etiket: string; deger: string; onDegistir: (yeni: string) => void; hata?: string; satirda: boolean }) => ReactNode;
};

type Degerler = Record<string, string>;

type Props<T extends { id: string }, G> = {
  baslik: string;
  aciklama: string;
  /** Mesajlarda: "Öğretmen" → "Yeni öğretmen", "12 öğretmen". */
  tekil: string;
  bos: { baslik: string; aciklama: string; dugme: string; cizim: IllustrasyonTuru };
  kaynak: Kaynak<T, G>;
  alanlar: ListeAlani[];
  /** Form değerlerini (hep metin) API'nin beklediği gövdeye çevirir (ör. seviye → sayı). */
  girdi: (degerler: Degerler) => G;
  /** Bir alanın tablodaki görünümü (düzenlenmiyorken), ör. ders adı yerine renkli çip. */
  gorunum?: (alan: string, satir: T) => ReactNode | undefined;
  /** İşlemler sütunundan önce eklenecek sütunlar, ör. dersin rengi. */
  ekSutunlar?: Sutun<T>[];
  /** Ekleme formundan sonra gösterilecek bölüm, ör. sınıflar sayfasında şube grupları. */
  ekBolum?: ReactNode;
};

const deger = (satir: object, ad: string) => String((satir as Record<string, unknown>)[ad] ?? "");

/** Bariz hatalar sunucuya gitmeden: boş zorunlu alan, aralık dışı sayı. */
function denetle(alanlar: ListeAlani[], d: Degerler): AlanHatalari {
  const h: AlanHatalari = {};
  for (const a of alanlar) {
    const v = (d[a.ad] ?? "").trim();
    if (a.gerekli && !v) h[a.ad] = "Boş bırakılamaz";
    else if (a.tur === "sayi" && v) {
      const n = Number(v);
      if (!Number.isInteger(n) || (a.min !== undefined && n < a.min) || (a.max !== undefined && n > a.max)) {
        h[a.ad] = `${a.min} ile ${a.max} arasında bir sayı girin`;
      }
    }
  }
  return h;
}

/**
 * Ortak liste sayfası: öğretmenler, sınıflar, dersler. Varlığa özel olan yalnızca `kaynak`
 * (API çağrıları) ve `alanlar`dır; davranış hepsinde aynıdır:
 *
 * - Türkçe sıralama ve arama;
 * - boşken ne yapılacağını anlatan bir kutu;
 * - altta hızlı ekleme formu (kaydedince form boşalır, odak ilk alana döner: uzun listeyi
 *   klavyeden ardı ardına girmek için);
 * - satırda düzenleme (Enter kaydeder, Esc vazgeçer);
 * - onaylı silme; silinemezse (409) sunucunun kaydın nerede kullanıldığını söyleyen mesajı.
 */
export function ListeSayfasi<T extends { id: string }, G>({
  baslik,
  aciklama,
  tekil,
  bos,
  kaynak,
  alanlar,
  girdi,
  gorunum,
  ekSutunlar = [],
  ekBolum,
}: Props<T, G>) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const liste = useQuery({ queryKey: kaynak.anahtar, queryFn: kaynak.listele });
  const tazele = () => istemci.invalidateQueries({ queryKey: kaynak.anahtar });

  const [arama, setArama] = useState("");
  // Türetilmiş değer: sıralı ve süzülmüş liste ayrı bir state değil, veriden hesaplanır.
  const gorunen = useMemo(() => {
    const sirali = turkceSirala(liste.data ?? [], (s) => deger(s, "ad"));
    return arama.trim() ? sirali.filter((s) => alanlar.some((a) => turkceIcerir(deger(s, a.ad), arama))) : sirali;
  }, [liste.data, arama, alanlar]);

  // --- ekleme --------------------------------------------------------------------------------
  const bosDegerler = useMemo(() => Object.fromEntries(alanlar.map((a) => [a.ad, ""])), [alanlar]);
  const [yeni, setYeni] = useState<Degerler>(bosDegerler);
  const [yeniHatalari, setYeniHatalari] = useState<AlanHatalari>({});
  const [deneme, setDeneme] = useState(0);
  const ekleFormu = useRef<HTMLFormElement>(null);
  useIlkHatayaOdaklan(ekleFormu, deneme);
  const ilkAlanaOdaklan = () => ekleFormu.current?.querySelector<HTMLInputElement>("input")?.focus();

  const ekle = useMutation({
    mutationFn: () => kaynak.olustur(girdi(yeni)),
    onSuccess: (kayit) => {
      bildirim("basari", `${deger(kayit, "ad")} eklendi.`);
      setYeni(bosDegerler);
      tazele();
      ilkAlanaOdaklan();
    },
  });
  const ekleSunucu = sunucuHatalari(ekle.error, (h) => (h.durum === 409 ? "ad" : undefined));

  function ekleGonder(olay: FormEvent) {
    olay.preventDefault();
    const h = denetle(alanlar, yeni);
    setYeniHatalari(h);
    setDeneme((n) => n + 1);
    if (Object.keys(h).length === 0) ekle.mutate();
  }

  // --- satırda düzenleme ---------------------------------------------------------------------
  const [duzenlenen, setDuzenlenen] = useState<{ id: string; degerler: Degerler } | null>(null);
  const [duzenHatalari, setDuzenHatalari] = useState<AlanHatalari>({});
  const guncelle = useMutation({
    mutationFn: (d: { id: string; degerler: Degerler }) => kaynak.guncelle(d.id, girdi(d.degerler) as Partial<G>),
    onSuccess: (kayit) => {
      bildirim("basari", `${deger(kayit, "ad")} kaydedildi.`);
      setDuzenlenen(null);
      tazele();
    },
    onError: (hata) => setDuzenHatalari(sunucuHatalari(hata, () => "ad").alanlar),
  });

  function duzenlemeyeBasla(satir: T) {
    setDuzenHatalari({});
    setDuzenlenen({ id: satir.id, degerler: Object.fromEntries(alanlar.map((a) => [a.ad, deger(satir, a.ad)])) });
  }

  function duzenlemeyiKaydet() {
    if (!duzenlenen) return;
    const h = denetle(alanlar, duzenlenen.degerler);
    setDuzenHatalari(h);
    if (Object.keys(h).length === 0) guncelle.mutate(duzenlenen);
  }

  function duzenTusu(olay: KeyboardEvent<HTMLInputElement>) {
    if (olay.key === "Enter") duzenlemeyiKaydet();
    if (olay.key === "Escape") setDuzenlenen(null);
  }

  // --- silme ---------------------------------------------------------------------------------
  const [silinecek, setSilinecek] = useState<T | null>(null);
  // Silinen satırlar liste tazelenmeden önce kısa bir çıkış animasyonu oynar.
  const [cikanlar, setCikanlar] = useState<ReadonlySet<string>>(new Set());
  const sil = useMutation({
    mutationFn: (satir: T) => kaynak.sil(satir.id),
    onSuccess: (_, satir) => {
      bildirim("basari", `${deger(satir, "ad")} silindi.`);
      setCikanlar((c) => new Set(c).add(satir.id));
      cikistanSonra(() => {
        void tazele();
        setCikanlar((c) => {
          const yeni = new Set(c);
          yeni.delete(satir.id);
          return yeni;
        });
      });
    },
    // Silinemezse (ör. ders dağılımında kullanılıyor) sunucunun mesajı nerede kullanıldığını ve
    // ne yapılacağını söyler; kullanıcı kapatana kadar ekranda kalır.
    onError: (hata) => bildirim("hata", hataMetni(hata)),
    onSettled: () => setSilinecek(null),
  });

  // --- tablo sütunları -----------------------------------------------------------------------
  const sutunlar: Sutun<T>[] = [
    ...alanlar.map((a): Sutun<T> => ({
      baslik: a.etiket,
      hizala: a.tur === "sayi" ? "sag" : undefined,
      hucre: (satir) => {
        if (duzenlenen?.id !== satir.id) return gorunum?.(a.ad, satir) ?? deger(satir, a.ad);
        const hata = duzenHatalari[a.ad];
        if (a.secici) {
          return a.secici({
            etiket: a.etiket, deger: duzenlenen.degerler[a.ad] ?? "", hata, satirda: true,
            onDegistir: (v) => setDuzenlenen({ ...duzenlenen, degerler: { ...duzenlenen.degerler, [a.ad]: v } }),
          });
        }
        return (
          <span className={stil.duzenAlani}>
            <input
              // Ekleme formundaki aynı adlı alandan ayırt edilsin (ekran okuyucu ve testler için).
              aria-label={`${a.etiket} (düzenleme)`}
              aria-invalid={hata ? true : undefined}
              className={stil.satirDenetimi}
              type={a.tur === "sayi" ? "number" : "text"}
              value={duzenlenen.degerler[a.ad] ?? ""}
              onChange={(o) => setDuzenlenen({ ...duzenlenen, degerler: { ...duzenlenen.degerler, [a.ad]: o.target.value } })}
              onKeyDown={duzenTusu}
            />
            {hata && <span className={stil.satirHatasi}>⚠ {hata}</span>}
          </span>
        );
      },
    })),
    ...ekSutunlar,
    {
      baslik: "İşlemler",
      baslikGizli: true,
      hizala: "sag",
      hucre: (satir) =>
        duzenlenen?.id === satir.id ? (
          <span className={stil.islemler}>
            <Dugme ikon={<Check />} tur="birincil" onClick={duzenlemeyiKaydet} yukleniyor={guncelle.isPending} yukleniyorMetni="Kaydediliyor...">
              Kaydet
            </Dugme>
            <Dugme tur="ikincil" onClick={() => setDuzenlenen(null)}>
              Vazgeç
            </Dugme>
          </span>
        ) : (
          <span className={stil.islemler}>
            <Dugme ikon={<Pencil />} tur="metin" aria-label={`${deger(satir, "ad")} düzenle`} onClick={() => duzenlemeyeBasla(satir)}>
              <span className={stil.islemMetni}>Düzenle</span>
            </Dugme>
            <Dugme ikon={<Trash2 />} tur="metin" aria-label={`${deger(satir, "ad")} sil`} onClick={() => setSilinecek(satir)}>
              <span className={stil.islemMetni}>Sil</span>
            </Dugme>
          </span>
        ),
    },
  ];

  const yeniHata = (ad: string) => yeniHatalari[ad] ?? ekleSunucu.alanlar[ad];
  const kucukTekil = tekil.toLocaleLowerCase("tr");

  return (
    <>
      <SayfaBasligi baslik={baslik}>
        {aciklama}
      </SayfaBasligi>

      {liste.isPending && <Iskelet satir={5} />}
      {liste.isError && (
        <div className={sayfaStili.hataKutusu} role="alert">
          <p>{hataMetni(liste.error)}</p>
          <Dugme ikon={<RotateCcw />} tur="ikincil" onClick={() => liste.refetch()}>
            Yeniden dene
          </Dugme>
        </div>
      )}

      {liste.isSuccess && liste.data.length === 0 && (
        <BosDurum cizim={bos.cizim} baslik={bos.baslik}
          eylem={<Dugme ikon={<Plus />} onClick={ilkAlanaOdaklan}>{bos.dugme}</Dugme>}>
          <p>{bos.aciklama}</p>
        </BosDurum>
      )}

      {liste.isSuccess && liste.data.length > 0 && (
        <>
          <div className={stil.araCubugu}>
            <MetinAlani etiket="Ara" type="search" value={arama} onChange={(o) => setArama(o.target.value)}
              aciklama={`${liste.data.length} ${kucukTekil}`} />
          </div>
          <Tablo<T>
            cikanlar={cikanlar}
            baslik={baslik}
            sutunlar={sutunlar}
            satirlar={gorunen}
            satirAnahtari={(s) => s.id}
            bosMesaj={
              <BosDurum cizim="arama" boyut="kucuk" baslikDuzeyi={3} baslik={`"${arama.trim()}" ile eşleşen ${kucukTekil} yok.`}
                eylem={<Dugme tur="metin" ikon={<X />} onClick={() => setArama("")}>Aramayı temizle</Dugme>}>
                <p>Adın ya da başka bir alanın bir kısmını yazmak yeter; büyük/küçük harf fark etmez.</p>
              </BosDurum>
            }
          />
        </>
      )}

      {liste.isSuccess && (
        <section className={`${sayfaStili.kart} ${stil.ekle}`} aria-labelledby="yeni-baslik">
          <h2 id="yeni-baslik">Yeni {kucukTekil}</h2>
          <FormHatasi mesaj={ekleSunucu.genel} />
          <form ref={ekleFormu} noValidate onSubmit={ekleGonder} className={stil.ekleFormu}>
            {alanlar.map((a) => a.secici ? (
              <div key={a.ad}>
                {a.secici({ etiket: a.etiket, deger: yeni[a.ad] ?? "", hata: yeniHata(a.ad), satirda: false,
                  onDegistir: (v) => setYeni({ ...yeni, [a.ad]: v }) })}
              </div>
            ) : (
              <MetinAlani
                key={a.ad}
                etiket={a.etiket}
                gerekli={a.gerekli}
                type={a.tur === "sayi" ? "number" : "text"}
                inputMode={a.tur === "sayi" ? "numeric" : undefined}
                min={a.min}
                max={a.max}
                placeholder={a.ornek}
                value={yeni[a.ad] ?? ""}
                onChange={(o) => setYeni({ ...yeni, [a.ad]: o.target.value })}
                hata={yeniHata(a.ad)}
              />
            ))}
            <Dugme ikon={<Plus />} type="submit" className={stil.ekleDugmesi} yukleniyor={ekle.isPending} yukleniyorMetni="Ekleniyor...">
              Ekle
            </Dugme>
          </form>
        </section>
      )}

      {liste.isSuccess && ekBolum}

      <OnayPenceresi
        acik={silinecek !== null}
        baslik={silinecek ? `${deger(silinecek, "ad")} silinsin mi?` : ""}
        mesaj="Bu işlem geri alınamaz."
        onaylaMetni="Sil"
        tehlikeli
        yukleniyor={sil.isPending}
        onVazgec={() => setSilinecek(null)}
        onOnayla={() => silinecek && sil.mutate(silinecek)}
      />
    </>
  );
}
