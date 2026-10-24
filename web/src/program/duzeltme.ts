/**
 * Elle düzeltme (7.1): taşıma haritası, taşıma, kilit ve geri alma. Karar sunucudadır (çözücü
 * paketinin bağımsız doğrulayıcısı); arayüz yalnızca gösterir. Her değişiklikten sonra programın
 * kendisi (kalite özeti, değişiklik sayısı) ve yerleşimleri tazelenir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { PROGRAMLAR } from "./veri";

export type TasimaHaritasi = components["schemas"]["TasimaHaritasi"];
export type Hedef = TasimaHaritasi["hedefler"][number];
/** Taşınan ders: kaynak hücre (bloğun herhangi bir saati). */
export type Kaynak = { ders_atama_id: string; gun: number; saat: number };

const yol = (program_id: string) => ({ path: { program_id } });

/** Taşıma başlayınca bir kez istenir: her hedef hücre uygun / uyarı / engel ve nedenleri. */
export function useTasimaHaritasi(programId: string, kaynak: Kaynak | null) {
  return useQuery({
    queryKey: [...PROGRAMLAR, programId, "tasima", kaynak],
    queryFn: () =>
      cagir(api.GET("/api/ders-programi/programlar/{program_id}/tasima", {
        params: { ...yol(programId), query: kaynak! },
      })),
    enabled: kaynak !== null,
    staleTime: 0,
    gcTime: 0,
  });
}

function useTazele(programId: string) {
  const istemci = useQueryClient();
  return async () => {
    // Program, yerleşimler ve fark tazelenir; taşıma haritası değil (taşıma bitince kapanır).
    await istemci.invalidateQueries({ queryKey: [...PROGRAMLAR, programId], predicate: (q) => q.queryKey[2] !== "tasima" });
    await istemci.invalidateQueries({ queryKey: PROGRAMLAR, exact: true });
  };
}

export function useTasi(programId: string) {
  const tazele = useTazele(programId);
  return useMutation({
    mutationFn: (d: Kaynak & { hedef_gun: number; hedef_saat: number; uyarilari_kabul: boolean }) =>
      cagir(api.POST("/api/ders-programi/programlar/{program_id}/tasi", { params: yol(programId), body: d })),
    onSuccess: tazele,
  });
}

export function useKilit(programId: string) {
  const tazele = useTazele(programId);
  return useMutation({
    mutationFn: (d: Kaynak & { kilitli: boolean }) =>
      cagir(api.PUT("/api/ders-programi/programlar/{program_id}/kilit", { params: yol(programId), body: d })),
    onSuccess: tazele,
  });
}

export function useGeriAl(programId: string) {
  const tazele = useTazele(programId);
  return useMutation({
    mutationFn: () => cagir(api.POST("/api/ders-programi/programlar/{program_id}/geri-al", { params: yol(programId) })),
    onSuccess: tazele,
  });
}
