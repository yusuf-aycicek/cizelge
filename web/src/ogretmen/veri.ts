/** Öğretmen detay sayfasının sunucu verisi: müsaitlik çizelgesi (iyimser güncellemeyle). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { OZET } from "../dagilim/veri";
import { ON_KONTROL } from "../program/veri";
import { uygula, type Degisiklik } from "./musaitlik";

export type MusaitlikCizelgesi = components["schemas"]["MusaitlikCizelgesi"];

export const musaitlikAnahtari = (ogretmenId: string) => ["musaitlik", ogretmenId] as const;

export function useMusaitlik(ogretmenId: string) {
  return useQuery({
    queryKey: musaitlikAnahtari(ogretmenId),
    queryFn: () =>
      cagir(api.GET("/api/ders-programi/ogretmenler/{ogretmen_id}/musaitlik", { params: { path: { ogretmen_id: ogretmenId } } })),
  });
}

/**
 * Toplu değişiklik, **iyimser güncellemeyle** (optimistic update):
 * 1. `onMutate`: sunucuya gitmeden önce önbellekteki çizelge değiştirilir, hücre anında döner.
 *    Eski hali saklanır.
 * 2. Sunucu reddederse (`onError`) eski hal geri konur; çağıran mesaj gösterir.
 * 3. Kabul ederse (`onSuccess`) sunucunun cevabı yazılır: içindeki yük (kapasite) sunucunun
 *    hesabıdır, arayüz yükü kendisi hesaplamaz.
 * Dağılım özeti ve program ön kontrolü de müsaitliğe bağlı olduğu için tazelenir.
 */
export function useMusaitlikDegistir(ogretmenId: string) {
  const istemci = useQueryClient();
  const anahtar = musaitlikAnahtari(ogretmenId);
  return useMutation({
    mutationFn: (degisiklikler: Degisiklik[]) =>
      cagir(api.PUT("/api/ders-programi/ogretmenler/{ogretmen_id}/musaitlik", {
        params: { path: { ogretmen_id: ogretmenId } },
        body: { degisiklikler },
      })),
    onMutate: async (degisiklikler) => {
      // Yolda olan bir okuma, iyimser değeri eski veriyle ezmesin.
      await istemci.cancelQueries({ queryKey: anahtar });
      const onceki = istemci.getQueryData<MusaitlikCizelgesi>(anahtar);
      if (onceki) istemci.setQueryData<MusaitlikCizelgesi>(anahtar, { ...onceki, hucreler: uygula(onceki.hucreler, degisiklikler) });
      return { onceki };
    },
    onError: (_hata, _degisiklikler, baglam) => {
      if (baglam?.onceki) istemci.setQueryData(anahtar, baglam.onceki);
    },
    onSuccess: (cizelge) => {
      istemci.setQueryData(anahtar, cizelge);
    },
    onSettled: () => {
      void istemci.invalidateQueries({ queryKey: OZET });
      void istemci.invalidateQueries({ queryKey: ON_KONTROL });
    },
  });
}
