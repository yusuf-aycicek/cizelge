/**
 * Programların sunucu verisi. Durum takibi sorgulamayla yapılır (CLAUDE.md mimari karar 6):
 * üretim sürerken liste birkaç saniyede bir yeniden istenir, bitince sorgulama kendiliğinden durur.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { etkinMi, type Program } from "./aciklama";

export const PROGRAMLAR = ["programlar"] as const;
export const SORGULAMA_MS = 1500;

/**
 * Bütün programlar (eskiden yeniye). `refetchInterval` bir fonksiyondur: TanStack Query her
 * yanıttan sonra onu çağırır; etkin (bekliyor ya da üretiliyor) program varsa 1,5 sn sonra yeniden
 * ister, yoksa `false` döner ve sorgulama durur. Bileşen zamanlayıcı yazmaz.
 */
export function useProgramlar() {
  return useQuery({
    queryKey: PROGRAMLAR,
    queryFn: () => cagir(api.GET("/api/ders-programi/programlar")),
    refetchInterval: (sorgu) => (sorgu.state.data?.some(etkinMi) ? SORGULAMA_MS : false),
  });
}

/** Tek program (çizelge sayfası). */
export function useProgram(id: string) {
  return useQuery({
    queryKey: [...PROGRAMLAR, id],
    queryFn: () => cagir(api.GET("/api/ders-programi/programlar/{program_id}", { params: { path: { program_id: id } } })),
    refetchInterval: (sorgu) => (sorgu.state.data && etkinMi(sorgu.state.data) ? SORGULAMA_MS : false),
  });
}

export function useYerlesimler(id: string, hazir: boolean) {
  return useQuery({
    queryKey: [...PROGRAMLAR, id, "yerlesimler"],
    queryFn: () =>
      cagir(api.GET("/api/ders-programi/programlar/{program_id}/yerlesimler", { params: { path: { program_id: id } } })),
    enabled: hazir, // hazır olmayan programın yerleşimi yok
    staleTime: Infinity, // bir programın yerleşimleri üretildikten sonra değişmez
  });
}

/** Yeni üretim isteği. Sunucu 202 ile "bekliyor" durumundaki programı döner; liste tazelenir. */
export function useProgramUret() {
  const istemci = useQueryClient();
  return useMutation({
    mutationFn: (d: { ad: string; sure_siniri_sn: number }) => cagir(api.POST("/api/ders-programi/programlar", { body: d })),
    onSuccess: (program: Program) => {
      // Yeni programı hemen listeye koy (sorgulama bu sayede başlar), sonra sunucudan tazele.
      istemci.setQueryData<Program[]>(PROGRAMLAR, (eski) => [...(eski ?? []), program]);
      void istemci.invalidateQueries({ queryKey: PROGRAMLAR });
    },
  });
}

export const ON_KONTROL = ["on-kontrol"] as const;

/**
 * Üretimdeki ön kontrolün tamamı, üretmeden (özel ayarlar, müsaitlik, kurallar dahil). Sunucu
 * worker'ın kullandığı girdiyi ve fonksiyonu kullanır: burada temiz olan üretimde ön kontrolde
 * takılmaz. Sayfa her açıldığında yeniden istenir (veri başka sayfada değişmiş olabilir).
 */
export function useOnKontrol() {
  return useQuery({
    queryKey: ON_KONTROL,
    queryFn: () => cagir(api.GET("/api/ders-programi/on-kontrol")),
    refetchOnMount: "always",
  });
}

/** En son program (liste eskiden yeniye sıralı). */
export const sonProgram = (liste: readonly Program[] | undefined) => liste?.at(-1);

/** En son hazır program: panodaki "son program" bağlantısı. */
export const sonHazirProgram = (liste: readonly Program[] | undefined) =>
  liste ? [...liste].reverse().find((p) => p.durum === "hazir") : undefined;
