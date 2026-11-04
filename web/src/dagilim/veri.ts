/**
 * Seviye şablonu ve ders dağılımı sayfalarının sunucu verisi.
 *
 * Öğretmen ve sınıf yükü burada **hesaplanmaz**: API'nin `dagilim-ozeti` ucu, program üretiminin
 * ön kontrolüyle aynı hesabı (çözücü paketi, `cozucu.yuk`) çalıştırıp sonucu verir (ADR 0015).
 * Arayüz yalnızca gösterir. Bir atama değişince özet sorgusu tazelenir.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";

export type Sema = components["schemas"];
export type Atama = Sema["DersAtamaYanit"];
export type SablonSatiri = Sema["SeviyeSablonuYanit"];
export type SablonRaporu = Sema["SablonUygulamaSonucu"];
export type DagilimOzeti = Sema["DagilimOzeti"];
export type OgretmenYuku = Sema["OgretmenYukuYanit"];
export type SinifYuku = Sema["SinifYukuYanit"];
export type Istisna = Sema["SubeIstisnasiYanit"];

export const ATAMALAR = ["atamalar"] as const;
export const SABLON = ["seviye-sablonlari"] as const;
export const OZET = ["dagilim-ozeti"] as const;
export const ISTISNALAR = ["istisnalar"] as const;

const yol = (kayit_id: string) => ({ params: { path: { kayit_id } } });

export const atamaApi = {
  listele: () => cagir(api.GET("/api/ders-programi/atamalar")),
  olustur: (body: Sema["DersAtamaOlustur"]) => cagir(api.POST("/api/ders-programi/atamalar", { body })),
  guncelle: (id: string, body: Sema["DersAtamaGuncelle"]) =>
    cagir(api.PATCH("/api/ders-programi/atamalar/{kayit_id}", { ...yol(id), body })),
  sil: (id: string) => cagir(api.DELETE("/api/ders-programi/atamalar/{kayit_id}", yol(id))),
  topluOgretmen: (body: Sema["TopluOgretmenAta"]) => cagir(api.POST("/api/ders-programi/atamalar/toplu-ogretmen", { body })),
};

export const sablonApi = {
  listele: () => cagir(api.GET("/api/ders-programi/seviye-sablonlari")),
  olustur: (body: Sema["SeviyeSablonuOlustur"]) => cagir(api.POST("/api/ders-programi/seviye-sablonlari", { body })),
  guncelle: (id: string, haftalik_saat: number) =>
    cagir(api.PATCH("/api/ders-programi/seviye-sablonlari/{kayit_id}", { ...yol(id), body: { haftalik_saat } })),
  sil: (id: string) => cagir(api.DELETE("/api/ders-programi/seviye-sablonlari/{kayit_id}", yol(id))),
  topluKaydet: (body: Sema["SablonTopluKaydet"]) => cagir(api.PUT("/api/ders-programi/seviye-sablonlari/toplu", { body })),
  hepsiniUygula: () => cagir(api.POST("/api/ders-programi/seviye-sablonlari/uygula-hepsi")),
  uygula: (seviye: number, sube_grubu_id?: string) =>
    cagir(api.POST("/api/ders-programi/seviye-sablonlari/uygula", {
      body: sube_grubu_id ? { seviye, sube_grubu_id } : { seviye },
    })),
};

export const istisnaApi = {
  listele: () => cagir(api.GET("/api/ders-programi/istisnalar")),
  olustur: (body: Sema["SubeIstisnasiOlustur"]) => cagir(api.POST("/api/ders-programi/istisnalar", { body })),
  sil: (id: string) =>
    cagir(api.DELETE("/api/ders-programi/istisnalar/{istisna_id}", { params: { path: { istisna_id: id } } })),
};

export function useIstisnalar() {
  return useQuery({ queryKey: ISTISNALAR, queryFn: istisnaApi.listele });
}

export function useSablon() {
  return useQuery({ queryKey: SABLON, queryFn: sablonApi.listele });
}

/**
 * Şubenin kullandığı şablonun dersleri (ders_id -> haftalık saat): grubunun şablonunda ders varsa
 * grubunki, yoksa seviyesininki. Sunucudaki `sablon_kaynaklari` ile aynı kural.
 */
export function subeninSablonu(sinif: { seviye: number; sube_grubu_id: string | null }, sablon: SablonSatiri[]) {
  const grubunki = sinif.sube_grubu_id ? sablon.filter((s) => s.sube_grubu_id === sinif.sube_grubu_id) : [];
  const satirlar = grubunki.length > 0 ? grubunki : sablon.filter((s) => s.seviye === sinif.seviye && !s.sube_grubu_id);
  return new Map(satirlar.map((s) => [s.ders_id, s.haftalik_saat]));
}

export function useAtamalar() {
  return useQuery({ queryKey: ATAMALAR, queryFn: atamaApi.listele });
}

export function useDagilimOzeti() {
  return useQuery({ queryKey: OZET, queryFn: () => cagir(api.GET("/api/ders-programi/dagilim-ozeti")) });
}

/**
 * Özel kanca (custom hook): öğretmen kimliği -> yük. Birkaç bileşen (öğretmen seçici, öğretmen
 * görünümü) aynı haritayı ister. Sorgu önbellekte tek kopyadır: kanca kaç yerde çağrılırsa
 * çağrılsın sunucuya tek istek gider.
 *
 * `useMemo` burada hız için değil, **kimlik** için: kanca bir nesne döner. Her çizimde yeni bir Map
 * dönseydi, onu bir effect'in ya da başka bir useMemo'nun bağımlılık listesine koyan bileşen her
 * çizimde "değişti" görürdü. Özet aynı kaldıkça aynı Map döner.
 */
export function useOgretmenYukleri(): Map<string, OgretmenYuku> {
  const { data } = useDagilimOzeti();
  return useMemo(() => new Map((data?.ogretmenler ?? []).map((y) => [y.ogretmen_id, y])), [data]);
}

export function useSinifYukleri(): Map<string, SinifYuku> {
  const { data } = useDagilimOzeti();
  return useMemo(() => new Map((data?.siniflar ?? []).map((y) => [y.sinif_id, y])), [data]);
}

/**
 * Atamalar değişince çağrılır: atama listesi ve yük özeti tazelenir. Tazelenen özetten, işlemden
 * etkilenen öğretmenin yeni yükü döner; çağıran aşım varsa hemen uyarabilir ("erken uyarı").
 */
export function useAtamalarDegisti() {
  const istemci = useQueryClient();
  return async (ogretmenId?: string | null): Promise<OgretmenYuku | undefined> => {
    await Promise.all([
      istemci.invalidateQueries({ queryKey: ATAMALAR }),
      istemci.invalidateQueries({ queryKey: OZET }),
      istemci.invalidateQueries({ queryKey: ISTISNALAR }),
    ]);
    if (!ogretmenId) return undefined;
    return istemci.getQueryData<DagilimOzeti>(OZET)?.ogretmenler.find((y) => y.ogretmen_id === ogretmenId);
  };
}

/** "18 / 24 saat" */
/**
 * "8 / 35 saat"; boş gün hedefi kapasiteyi daraltıyorsa yaklaşık hedefli kapasite de:
 * "8 / 35 saat · hedefle ~21" (sunucunun `hedefli_kapasite`i; boş gün esnek kuraldır, uyarı değildir).
 */
export function yukMetni(y: { ders_saati: number; kullanilabilir_saat: number; hedefli_kapasite?: number | null }): string {
  const temel = `${y.ders_saati} / ${y.kullanilabilir_saat} saat`;
  return y.hedefli_kapasite != null && y.hedefli_kapasite < y.kullanilabilir_saat ? `${temel} · hedefle ~${y.hedefli_kapasite}` : temel;
}
