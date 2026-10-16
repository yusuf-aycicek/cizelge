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

type Sema = components["schemas"];
export type Atama = Sema["DersAtamaYanit"];
export type SablonSatiri = Sema["SeviyeSablonuYanit"];
export type SablonRaporu = Sema["SablonUygulamaSonucu"];
export type DagilimOzeti = Sema["DagilimOzeti"];
export type OgretmenYuku = Sema["OgretmenYukuYanit"];
export type SinifYuku = Sema["SinifYukuYanit"];

export const ATAMALAR = ["atamalar"] as const;
export const SABLON = ["seviye-sablonlari"] as const;
export const OZET = ["dagilim-ozeti"] as const;

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
  uygula: (seviye: number) => cagir(api.POST("/api/ders-programi/seviye-sablonlari/uygula", { body: { seviye } })),
};

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
    ]);
    if (!ogretmenId) return undefined;
    return istemci.getQueryData<DagilimOzeti>(OZET)?.ogretmenler.find((y) => y.ogretmen_id === ogretmenId);
  };
}

/** "18 / 24 saat" */
export function yukMetni(y: { ders_saati: number; kullanilabilir_saat: number }): string {
  return `${y.ders_saati} / ${y.kullanilabilir_saat} saat`;
}
