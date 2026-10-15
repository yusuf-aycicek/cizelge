import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { Route, Routes } from "react-router";
import { BildirimSaglayici } from "./bilesenler/Bildirim";
import { Cerceve, MENU } from "./cerceve/Cerceve";
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
        <Routes>
          <Route element={<Cerceve />}>
            <Route index element={<AnaSayfa />} />
            <Route path="tasarim" element={<TasarimSayfasi />} />
            {MENU.filter((m) => m.yol !== "/").map((m) => (
              <Route key={m.yol} path={m.yol.slice(1)} element={<YapimAsamasinda baslik={m.ad} />} />
            ))}
            <Route path="*" element={<Bulunamadi />} />
          </Route>
        </Routes>
      </BildirimSaglayici>
    </QueryClientProvider>
  );
}
