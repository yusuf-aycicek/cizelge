import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiHatasi } from "./api/hata";
import { BEN_ANAHTARI, SURE_DOLDU_ANAHTARI } from "./kimlik/oturum";

/**
 * TanStack Query istemcisi: sunucu verisinin önbelleği.
 *
 * - `staleTime`: veri 30 sn "taze" sayılır. Aynı veriyi isteyen ikinci bileşen yeni istek atmaz.
 * - Yeniden deneme: bağlantı ya da sunucu hatasında iki kez denenir. 4xx hatalarında denenmez:
 *   "e-posta kullanılıyor" ikinci denemede değişmez.
 * - Pencereye dönünce yeniden çekme kapalı: veri giren kullanıcının ekranı habersiz değişmesin.
 * - **Oturum süresi doldu:** herhangi bir sorgu ya da değişiklik 401 alırsa kullanıcı `null`
 *   yapılır ve işaret konur. Korumalı alan bunu görüp giriş sayfasına yönlendirir.
 */
export function sorguIstemcisiOlustur(yenidenDene = true): QueryClient {
  const oturumKapandi = (hata: unknown, anahtar?: readonly unknown[]) => {
    if (!(hata instanceof ApiHatasi) || hata.durum !== 401) return;
    if (anahtar && anahtar[0] === BEN_ANAHTARI[0]) return; // ben sorgusu 401'i kendisi yorumlar
    if (istemci.getQueryData(BEN_ANAHTARI)) {
      istemci.setQueryData(SURE_DOLDU_ANAHTARI, true);
    }
    istemci.setQueryData(BEN_ANAHTARI, null);
  };

  const istemci: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: (hata, sorgu) => oturumKapandi(hata, sorgu.queryKey) }),
    mutationCache: new MutationCache({ onError: (hata) => oturumKapandi(hata) }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (deneme, hata) => {
          if (!yenidenDene) return false;
          if (hata instanceof ApiHatasi && hata.durum >= 400 && hata.durum < 500) return false;
          return deneme < 2;
        },
      },
      mutations: { retry: false },
    },
  });
  return istemci;
}
