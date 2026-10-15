/**
 * Giriş yapmış kullanıcı: `/api/ben` sorgusu. Ayrı bir global durum deposu yok; kullanıcı
 * TanStack Query'nin önbelleğinde durur ve her bileşen `useBen()` ile okur.
 *
 * - `null`: giriş yapılmamış (sunucu 401 döndü). Bu bir hata değil, bir durum.
 * - Girişte, kayıtta ve çıkışta önbellek elle güncellenir (`setQueryData`): sunucuya bir kez
 *   daha sormaya gerek yok, cevap zaten elimizde.
 * - Başka bir istek 401 alırsa (oturum süresi doldu) sorgu istemcisi kullanıcıyı `null` yapar ve
 *   "süresi doldu" işaretini koyar (sorgu.ts); korumalı alan giriş sayfasına yönlendirir.
 */
import { useQuery } from "@tanstack/react-query";
import { ApiHatasi, cagir } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";

export type Ben = components["schemas"]["BenYanit"];

export const BEN_ANAHTARI = ["ben"] as const;
export const SURE_DOLDU_ANAHTARI = ["oturum", "suresiDoldu"] as const;

export const ROL_ADLARI: Record<string, string> = {
  mudur: "Müdür",
  mudur_yardimcisi: "Müdür yardımcısı",
};

export async function beniGetir(): Promise<Ben | null> {
  try {
    return await cagir(api.GET("/api/ben"));
  } catch (hata) {
    if (hata instanceof ApiHatasi && hata.durum === 401) return null;
    throw hata;
  }
}

export function useBen() {
  return useQuery({
    queryKey: BEN_ANAHTARI,
    queryFn: beniGetir,
    // Kullanıcı kendiliğinden değişmez: yalnızca giriş, çıkış ve 401 değiştirir.
    staleTime: Infinity,
  });
}
