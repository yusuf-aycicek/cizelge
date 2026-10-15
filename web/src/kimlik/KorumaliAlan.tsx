import { useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router";
import { hataMetni } from "../api/hata";
import { Dugme } from "../bilesenler/Dugme";
import { SURE_DOLDU_ANAHTARI, useBen } from "./oturum";
import stil from "./Kimlik.module.css";

/** Giriş sayfasına taşınan bilgi: girişten sonra dönülecek adres ve gösterilecek mesaj. */
export type GirisDurumu = { donus?: string; mesaj?: string };

export const SURE_DOLDU_MESAJI = "Oturumunuzun süresi doldu. Devam etmek için yeniden giriş yapın.";

/**
 * Korumalı alan: içindeki sayfalar yalnızca giriş yapmış kullanıcıya görünür. Giriş yoksa
 * `<Navigate>` giriş sayfasına yönlendirir ve gelinen adresi yanında taşır.
 *
 * Bu bir güvenlik önlemi değil, kullanım kolaylığıdır: asıl koruma sunucudadır (oturumsuz
 * istek 401). Arayüz yalnızca kullanıcıyı doğru sayfaya götürür.
 */
export function KorumaliAlan() {
  const ben = useBen();
  const konum = useLocation();
  const istemci = useQueryClient();

  if (ben.isPending) {
    return <p className={stil.bekle}>Yükleniyor...</p>;
  }
  if (ben.isError) {
    return (
      <div className={stil.bekle} role="alert">
        <p>{hataMetni(ben.error)}</p>
        <Dugme tur="ikincil" onClick={() => ben.refetch()} yukleniyor={ben.isFetching}>
          Yeniden dene
        </Dugme>
      </div>
    );
  }
  if (!ben.data) {
    const suresiDoldu = istemci.getQueryData(SURE_DOLDU_ANAHTARI) === true;
    const durum: GirisDurumu = {
      donus: konum.pathname + konum.search,
      mesaj: suresiDoldu ? SURE_DOLDU_MESAJI : undefined,
    };
    return <Navigate to="/giris" replace state={durum} />;
  }
  return <Outlet />;
}
