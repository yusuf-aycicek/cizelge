import { CalendarDays } from "lucide-react";
import { Navigate, Outlet } from "react-router";
import { useBen } from "./oturum";
import { UYGULAMA_ACIKLAMASI, UYGULAMA_ADI } from "../urun";
import stil from "./Kimlik.module.css";

/**
 * Giriş ve kayıt sayfalarının düzeni: menü yok, ortada tek bir kart. Zaten giriş yapmış
 * kullanıcı buraya gelirse ana sayfaya gönderilir.
 */
export function KimlikCercevesi({ yalin = false }: { yalin?: boolean }) {
  const ben = useBen();
  if (ben.data) return <Navigate to="/" replace />;
  // Giriş sayfası kendi iki sütunlu düzenini çizer; çerçeve yalnızca yönlendirmeyi yapar.
  if (yalin) return <Outlet />;
  return (
    <div className={stil.sayfa}>
      <header className={stil.ust}>
        <CalendarDays aria-hidden="true" className={stil.urunIkonu} />
        <span>
          <span className={stil.urunAdi}>{UYGULAMA_ADI}</span>
          <span className={stil.urunAciklamasi}>{UYGULAMA_ACIKLAMASI}</span>
        </span>
      </header>
      <main className={stil.orta}>
        <Outlet />
      </main>
    </div>
  );
}
