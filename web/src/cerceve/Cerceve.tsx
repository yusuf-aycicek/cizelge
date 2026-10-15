import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { BEN_ANAHTARI, ROL_ADLARI, useBen } from "../kimlik/oturum";
import type { GirisDurumu } from "../kimlik/KorumaliAlan";
import stil from "./Cerceve.module.css";

/** Menüdeki sayfalar. Henüz yapılmamış olanlar "hazırlanıyor" sayfası gösterir. */
export const MENU = [
  { yol: "/", ad: "Ana sayfa" },
  { yol: "/okul", ad: "Okul ayarları" },
  { yol: "/ogretmenler", ad: "Öğretmenler" },
  { yol: "/siniflar", ad: "Sınıflar" },
  { yol: "/dersler", ad: "Dersler" },
  { yol: "/seviye-sablonu", ad: "Seviye şablonu" },
  { yol: "/ders-dagilimi", ad: "Ders dağılımı" },
  { yol: "/musaitlik", ad: "Öğretmen müsaitliği" },
  { yol: "/kullanicilar", ad: "Kullanıcılar" },
] as const;

/**
 * Sayfa çerçevesi: üst çubuk, menü ve içerik alanı. `<Outlet />`, o anki adresin sayfasının
 * çizileceği yerdir (React Router).
 *
 * - "İçeriğe geç" bağlantısı: klavyeyle gezinen kullanıcı her sayfada menüyü baştan sona
 *   dolaşmak zorunda kalmaz (ilk Tab ile görünür).
 * - Dar ekranda menü bir düğmeyle açılıp kapanır; `aria-expanded` ekran okuyucuya durumunu söyler.
 */
export function Cerceve() {
  // useState: bileşenin hatırladığı değer. setMenuAcik çağrılınca React bileşeni yeniden çizer.
  const [menuAcik, setMenuAcik] = useState(false);
  const konum = useLocation();
  const ben = useBen().data;
  const istemci = useQueryClient();
  const yonlendir = useNavigate();

  const cikis = useMutation({
    mutationFn: () => cagir(api.POST("/api/cikis")),
    // Sunucuya ulaşılamasa da kullanıcı çıkmış sayılır: önbellek temizlenir, giriş sayfasına gidilir.
    onSettled: () => {
      istemci.clear();
      istemci.setQueryData(BEN_ANAHTARI, null);
      const durum: GirisDurumu = { mesaj: "Çıkış yaptınız." };
      yonlendir("/giris", { replace: true, state: durum });
    },
  });
  // Sayfa değişince telefondaki menü kapanır. Effect değil: değişikliği çizim sırasında
  // fark edip state'i hemen düzeltmek React'in önerdiği yol.
  const [sonKonum, setSonKonum] = useState(konum.pathname);
  if (sonKonum !== konum.pathname) {
    setSonKonum(konum.pathname);
    setMenuAcik(false);
  }

  return (
    <div className={stil.cerceve}>
      <a href="#icerik" className={stil.icerigeGec}>
        İçeriğe geç
      </a>
      <header className={stil.ust}>
        <button
          type="button"
          className={stil.menuDugmesi}
          aria-expanded={menuAcik}
          aria-controls="ana-menu"
          onClick={() => setMenuAcik((acik) => !acik)}
        >
          ☰ <span>Menü</span>
        </button>
        <span className={stil.urun}>Ders Programı</span>
        {ben && (
          <div className={stil.kullanici}>
            <span className={stil.okulAdi}>{ben.okul.ad}</span>
            <Link to="/hesabim" className={stil.hesap} title="Hesabım">
              {ben.kullanici.ad}
              <span className={stil.rol}> · {ROL_ADLARI[ben.kullanici.rol] ?? ben.kullanici.rol}</span>
            </Link>
            <button type="button" className={stil.cikis} onClick={() => cikis.mutate()} disabled={cikis.isPending}>
              Çıkış
            </button>
          </div>
        )}
      </header>
      <nav id="ana-menu" aria-label="Ana menü" className={`${stil.menu} ${menuAcik ? stil.acik : ""}`}>
        <ul>
          {MENU.map((m) => (
            <li key={m.yol}>
              {/* NavLink, o anki sayfanın bağlantısına aria-current="page" ekler: ekran okuyucu
                  "geçerli sayfa" der, stil de buna göre vurgular. */}
              <NavLink to={m.yol} end={m.yol === "/"} className={stil.baglanti}>
                {m.ad}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main id="icerik" tabIndex={-1} className={stil.icerik}>
        <Outlet />
      </main>
    </div>
  );
}
