/**
 * Şube grupları (K5): "11 Sayısal", "11 Sözel" gibi aynı seviyedeki şubelerin grupları. Grubun
 * kendi seviye şablonu ve gruba özel kural ayarları olabilir. Sınıflar sayfasında yönetilir: alttaki
 * kartta gruplar eklenir, adı değiştirilir, silinir; şube satırında grup seçilir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { Tablo } from "../bilesenler/Tablo";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { sinifKaynagi, type Sinif } from "./kaynaklar";
import stil from "./Liste.module.css";

export type SubeGrubu = components["schemas"]["SubeGrubuYanit"];

export const SUBE_GRUPLARI = ["sube-gruplari"] as const;

export function useSubeGruplari() {
  return useQuery({ queryKey: SUBE_GRUPLARI, queryFn: () => cagir(api.GET("/api/sube-gruplari")) });
}

const yol = (kayit_id: string) => ({ params: { path: { kayit_id } } });

/** Şube satırındaki grup seçimi: yalnızca şubenin seviyesindeki gruplar; seçince kaydedilir. */
export function SubeGrubuSecici({ sinif, gruplar }: { sinif: Sinif; gruplar: SubeGrubu[] }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const uygun = turkceSirala(gruplar.filter((g) => g.seviye === sinif.seviye), (g) => g.ad);
  const degistir = useMutation({
    mutationFn: (grup: string) => sinifKaynagi.guncelle(sinif.id, { sube_grubu_id: grup || null }),
    onSuccess: async (s) => {
      await istemci.invalidateQueries({ queryKey: sinifKaynagi.anahtar });
      const grup = gruplar.find((g) => g.id === s.sube_grubu_id);
      bildirim("basari", grup ? `${s.ad} artık ${grup.ad} grubunda.` : `${s.ad} gruptan çıkarıldı.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });
  if (uygun.length === 0 && !sinif.sube_grubu_id) return <span className={stil.soluk}>—</span>;
  return (
    <select
      className={stil.satirSecimi}
      aria-label={`${sinif.ad} şubesinin grubu`}
      value={sinif.sube_grubu_id ?? ""}
      disabled={degistir.isPending}
      onChange={(o) => degistir.mutate(o.target.value)}
    >
      <option value="">Grup yok</option>
      {uygun.map((g) => (
        <option key={g.id} value={g.id}>
          {g.ad}
        </option>
      ))}
    </select>
  );
}

/** Grupların listesi, ekleme, ad değiştirme ve silme. */
export function SubeGruplariBolumu({ siniflar }: { siniflar: Sinif[] }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const gruplar = useSubeGruplari();
  const [yeni, setYeni] = useState({ ad: "", seviye: "" });
  const [hata, setHata] = useState<string>();
  const [duzenlenen, setDuzenlenen] = useState<{ id: string; ad: string } | null>(null);
  const [silinecek, setSilinecek] = useState<SubeGrubu | null>(null);
  const tazele = async () => {
    await istemci.invalidateQueries({ queryKey: SUBE_GRUPLARI });
    await istemci.invalidateQueries({ queryKey: sinifKaynagi.anahtar });
  };
  const seviyeler = [...new Set(siniflar.map((s) => s.seviye))].sort((a, b) => a - b);
  const subeleri = (g: SubeGrubu) => turkceSirala(siniflar.filter((s) => s.sube_grubu_id === g.id), (s) => s.ad);

  const ekle = useMutation({
    mutationFn: (g: { ad: string; seviye: number }) => cagir(api.POST("/api/sube-gruplari", { body: g })),
    onSuccess: async (g) => {
      await tazele();
      setYeni({ ad: "", seviye: yeni.seviye });
      bildirim("basari", `${g.ad} grubu eklendi. Şubeleri yukarıdaki tablodan bu gruba alabilirsiniz.`);
    },
    onError: (h) => setHata(hataMetni(h)),
  });
  const adDegistir = useMutation({
    mutationFn: (d: { id: string; ad: string }) =>
      cagir(api.PATCH("/api/sube-gruplari/{kayit_id}", { ...yol(d.id), body: { ad: d.ad } })),
    onSuccess: async (g) => {
      await tazele();
      setDuzenlenen(null);
      bildirim("basari", `Grubun yeni adı: ${g.ad}.`);
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
  });
  const sil = useMutation({
    mutationFn: (g: SubeGrubu) => cagir(api.DELETE("/api/sube-gruplari/{kayit_id}", yol(g.id))),
    onSuccess: async (_, g) => {
      await tazele();
      bildirim("basari", `${g.ad} grubu silindi; şubeleri artık seviyelerinin şablonunu kullanır.`);
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
    onSettled: () => setSilinecek(null),
  });

  function ekleGonder(olay: FormEvent) {
    olay.preventDefault();
    const seviye = Number(yeni.seviye);
    if (!yeni.ad.trim()) return setHata("Grubun adını yazın (ör. 11 Sayısal).");
    if (!seviye) return setHata("Grubun seviyesini seçin.");
    setHata(undefined);
    ekle.mutate({ ad: yeni.ad.trim(), seviye });
  }

  const liste = turkceSirala(gruplar.data ?? [], (g) => `${String(g.seviye).padStart(2, "0")} ${g.ad}`);
  return (
    <section aria-labelledby="gruplar-baslik" className={sayfaStili.kart}>
      <h2 id="gruplar-baslik">Şube grupları</h2>
      <p className={stil.kartAciklamasi}>
        Aynı seviyede farklı dersler okuyan şubeleri gruplayın (ör. 11 Sayısal, 11 Sözel). Bir grubun kendi seviye
        şablonu olabilir; grubu olmayan şube seviyesinin şablonunu kullanır.
      </p>
      {liste.length > 0 && (
        <Tablo<SubeGrubu>
          baslik="Şube grupları"
          satirlar={liste}
          satirAnahtari={(g) => g.id}
          sutunlar={[
            {
              baslik: "Grup",
              hucre: (g) =>
                duzenlenen?.id === g.id ? (
                  <input
                    className={stil.satirSecimi}
                    aria-label="Grubun adı"
                    value={duzenlenen.ad}
                    autoFocus
                    onChange={(o) => setDuzenlenen({ id: g.id, ad: o.target.value })}
                    onKeyDown={(o) => {
                      if (o.key === "Enter" && duzenlenen.ad.trim()) adDegistir.mutate({ id: g.id, ad: duzenlenen.ad.trim() });
                      if (o.key === "Escape") setDuzenlenen(null);
                    }}
                  />
                ) : (
                  g.ad
                ),
            },
            { baslik: "Seviye", hucre: (g) => `${g.seviye}. sınıf` },
            {
              baslik: "Şubeler",
              hucre: (g) => (subeleri(g).length ? subeleri(g).map((s) => s.ad).join(", ") : <span className={stil.soluk}>Henüz şube yok</span>),
            },
            {
              baslik: "İşlemler",
              baslikGizli: true,
              hizala: "sag",
              hucre: (g) =>
                duzenlenen?.id === g.id ? (
                  <span className={stil.islemler}>
                    <Dugme ikon={<Check />} tur="metin" yukleniyor={adDegistir.isPending}
                      onClick={() => duzenlenen.ad.trim() && adDegistir.mutate({ id: g.id, ad: duzenlenen.ad.trim() })}>
                      <span className={stil.islemMetni}>Kaydet</span>
                    </Dugme>
                    <Dugme ikon={<X />} tur="metin" onClick={() => setDuzenlenen(null)}>
                      <span className={stil.islemMetni}>Vazgeç</span>
                    </Dugme>
                  </span>
                ) : (
                  <span className={stil.islemler}>
                    <Dugme ikon={<Pencil />} tur="metin" aria-label={`${g.ad} grubunun adını değiştir`}
                      onClick={() => setDuzenlenen({ id: g.id, ad: g.ad })}>
                      <span className={stil.islemMetni}>Adını değiştir</span>
                    </Dugme>
                    <Dugme ikon={<Trash2 />} tur="metin" aria-label={`${g.ad} grubunu sil`} onClick={() => setSilinecek(g)}>
                      <span className={stil.islemMetni}>Sil</span>
                    </Dugme>
                  </span>
                ),
            },
          ]}
        />
      )}
      <form onSubmit={ekleGonder} className={stil.ekleFormu} noValidate>
        <MetinAlani etiket="Grubun adı" placeholder="11 Sayısal" value={yeni.ad} hata={hata} maxLength={100}
          onChange={(o) => setYeni({ ...yeni, ad: o.target.value })} />
        <SecimAlani etiket="Seviye" value={yeni.seviye} onChange={(o) => setYeni({ ...yeni, seviye: o.target.value })}>
          <option value="">Seçin</option>
          {seviyeler.map((s) => (
            <option key={s} value={s}>
              {s}. sınıf
            </option>
          ))}
        </SecimAlani>
        <Dugme ikon={<Plus />} type="submit" className={stil.ekleDugmesi} yukleniyor={ekle.isPending} yukleniyorMetni="Ekleniyor...">
          Grup ekle
        </Dugme>
      </form>
      <OnayPenceresi
        acik={silinecek !== null}
        baslik={silinecek ? `${silinecek.ad} grubu silinsin mi?` : ""}
        mesaj="Şubeler silinmez, grupsuz kalır ve seviyelerinin şablonunu kullanır. Grubun şablonu ve gruba özel kural ayarları silinir."
        onaylaMetni="Grubu sil"
        tehlikeli
        yukleniyor={sil.isPending}
        onVazgec={() => setSilinecek(null)}
        onOnayla={() => silinecek && sil.mutate(silinecek)}
      />
    </section>
  );
}
