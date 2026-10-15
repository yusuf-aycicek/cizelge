import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { Route, Routes } from "react-router";
import { BildirimSaglayici } from "./bilesenler/Bildirim";
import { Cerceve, MENU } from "./cerceve/Cerceve";
import { GirisSayfasi } from "./kimlik/GirisSayfasi";
import { HesabimSayfasi } from "./kimlik/HesabimSayfasi";
import { KayitSayfasi } from "./kimlik/KayitSayfasi";
import { KimlikCercevesi } from "./kimlik/KimlikCercevesi";
import { KorumaliAlan } from "./kimlik/KorumaliAlan";
import { AnaSayfa } from "./sayfalar/AnaSayfa";
import { Bulunamadi, YapimAsamasinda } from "./sayfalar/BasitSayfalar";
import { TasarimSayfasi } from "./sayfalar/TasarimSayfasi";

/**
 * Uygulamanın kökü: sağlayıcılar (Query önbelleği, bildirimler) ve sayfalar.
 *
 * Yönlendirici (BrowserRouter ya da testte MemoryRouter) dışarıdan sarılır: aynı uygulama
 * tarayıcıda gerçek adres çubuğuyla, testte bellekteki bir adresle çalışır.
 */
export function Uygulama({ sorguIstemcisi }: { sorguIstemcisi: QueryClient }) {
  return (
    <QueryClientProvider client={sorguIstemcisi}>
      <BildirimSaglayici>
        {/* İç içe yollar: dıştaki öğe (düzen) içtekinin çevresini çizer, içteki <Outlet />'e yerleşir. */}
        <Routes>
          <Route element={<KimlikCercevesi />}>
            <Route path="giris" element={<GirisSayfasi />} />
            <Route path="kayit" element={<KayitSayfasi />} />
          </Route>
          <Route element={<KorumaliAlan />}>
            <Route element={<Cerceve />}>
              <Route index element={<AnaSayfa />} />
              <Route path="hesabim" element={<HesabimSayfasi />} />
              <Route path="tasarim" element={<TasarimSayfasi />} />
              {MENU.filter((m) => m.yol !== "/").map((m) => (
                <Route key={m.yol} path={m.yol.slice(1)} element={<YapimAsamasinda baslik={m.ad} />} />
              ))}
              <Route path="*" element={<Bulunamadi />} />
            </Route>
          </Route>
        </Routes>
      </BildirimSaglayici>
    </QueryClientProvider>
  );
}
