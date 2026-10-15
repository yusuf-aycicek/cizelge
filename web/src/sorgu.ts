import { QueryClient } from "@tanstack/react-query";
import { ApiHatasi } from "./api/hata";

/**
 * TanStack Query istemcisi: sunucu verisinin önbelleği.
 *
 * - `staleTime`: veri 30 sn "taze" sayılır. Aynı veriyi isteyen ikinci bileşen yeni istek atmaz.
 * - Yeniden deneme: bağlantı ya da sunucu hatasında iki kez denenir. 4xx hatalarında denenmez:
 *   "e-posta kullanılıyor" ikinci denemede değişmez.
 * - Pencereye dönünce yeniden çekme kapalı: veri giren kullanıcının ekranı habersiz değişmesin.
 */
export function sorguIstemcisiOlustur(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (deneme, hata) => {
          if (hata instanceof ApiHatasi && hata.durum >= 400 && hata.durum < 500) return false;
          return deneme < 2;
        },
      },
      mutations: { retry: false },
    },
  });
}
