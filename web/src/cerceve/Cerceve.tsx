import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, LogOut, Menu, UserRound } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { cagir } from "../api/hata";
import { useBildirimleriTemizle } from "../bilesenler/Bildirim";
import { api } from "../api/istemci";
import { BEN_ANAHTARI, ROL_ADLARI, useBen } from "../kimlik/oturum";
import type { GirisDurumu } from "../kimlik/KorumaliAlan";
import { UYGULAMA_ADI } from "../urun";
import { TemaDugmesi } from "../bilesenler/TemaDugmesi";
import { basHarfler } from "../bilesenler/OgretmenRozeti";
import { MENU, type MenuGrubu, type MenuOgesi } from "./menu";
import stil from "./Cerceve.module.css";

// Menü bölümleri, sırasıyla: grupsuz üst (Ana sayfa), üç grup, grupsuz alt (Kullanıcılar).
type Bolum = { grup?: MenuGrubu; ogeler: MenuOgesi[] };
function bolumler(): Bolum[] {
  const sonuc: Bolum[] = [];
  for (const oge of MENU) {
    const son = sonuc[sonuc.length - 1];
    if (son && son.grup === oge.grup && oge.grup) son.ogeler.push(oge);
    else sonuc.push({ grup: oge.grup, ogeler: [oge] });
  }
  return sonuc;
}
const BOLUMLER = bolumler();

/**
 * Sayfa çerçevesi: üst çubuk, menü ve içerik alanı. `<Outlet />`, o anki adresin sayfasının
 * çizileceği yerdir (React Router).
 *
 * - "İçeriğe geç" bağlantısı: klavyeyle gezinen kullanıcı her sayfada menüyü baştan sona
 *   dolaşmak zorunda kalmaz (ilk Tab ile görünür).
 * - Menü OKUL, DAĞITIM ve PROGRAM bölümlerine ayrılır; her bölümün başlığı listenin adıdır
 *   (aria-labelledby), ekran okuyucu "OKUL, liste, 5 öğe" der.
 * - Dar ekranda menü bir düğmeyle açılıp kapanır; `aria-expanded` ekran okuyucuya durumunu söyler.
 */
export function Cerceve() {
  // useState: bileşenin hatırladığı değer. setMenuAcik çağrılınca React bileşeni yeniden çizer.
  const [menuAcik, setMenuAcik] = useState(false);
  const konum = useLocation();
  const ben = useBen().data;

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
          <Menu aria-hidden="true" className={stil.ikon} /> <span>Menü</span>
        </button>
        <Link to="/" className={stil.urun}>
          <CalendarDays aria-hidden="true" className={stil.urunIkonu} />
          {UYGULAMA_ADI}
        </Link>
        {ben && (
          <div className={stil.kullanici}>
            <span className={stil.okulAdi}>{ben.okul.ad}</span>
            <TemaDugmesi className={stil.temaDugmesi} />
            <HesapMenusu ad={ben.kullanici.ad} rol={ROL_ADLARI[ben.kullanici.rol] ?? ben.kullanici.rol} />
          </div>
        )}
      </header>
      <nav id="ana-menu" aria-label="Ana menü" className={`${stil.menu} ${menuAcik ? stil.acik : ""}`}>
        <div className={stil.menuIcerik}>
          {BOLUMLER.map((b, i) => (
            <MenuBolumu key={b.grup ?? `grupsuz-${i}`} bolum={b} alt={i === BOLUMLER.length - 1} />
          ))}
        </div>
      </nav>
      <main id="icerik" tabIndex={-1} className={stil.icerik}>
        {/* key: sayfa (adres yolu) değişince bu kutu yeniden kurulur ve solarak girer (CSS). Aynı
            sayfada yalnızca sorgu parametresi değişirse (ör. sekme) yeniden kurulmaz. */}
        <div key={konum.pathname} className={stil.sayfa}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function MenuBolumu({ bolum, alt }: { bolum: Bolum; alt: boolean }) {
  const baslikId = useId();
  return (
    <div className={`${stil.bolum} ${alt && !bolum.grup ? stil.altBolum : ""}`}>
      {bolum.grup && (
        <p id={baslikId} className={stil.bolumBasligi}>
          {bolum.grup}
        </p>
      )}
      <ul aria-labelledby={bolum.grup ? baslikId : undefined}>
        {bolum.ogeler.map((m) => (
          <li key={m.yol}>
            {/* NavLink, o anki sayfanın bağlantısına aria-current="page" ekler: ekran okuyucu
                "geçerli sayfa" der, stil de buna göre vurgular. */}
            <NavLink to={m.yol} end={m.yol === "/"} className={stil.baglanti}>
              <m.Ikon aria-hidden="true" className={stil.ikon} />
              {m.ad}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Baş harfli yuvarlak düğme ve açılan küçük menü (Hesabım, Çıkış). Açılır kutu deseni
 * (disclosure): düğmenin `aria-expanded`'i açık mı söyler; içerik sıradan bağlantı ve düğmedir.
 * Açılınca ilk öğeye odaklanır; Esc, dışarı tıklama ya da odağın dışarı çıkması kapatır, Esc
 * odağı düğmeye geri verir.
 */
function HesapMenusu({ ad, rol }: { ad: string; rol: string }) {
  const [acik, setAcik] = useState(false);
  const kutu = useRef<HTMLDivElement>(null);
  const dugme = useRef<HTMLButtonElement>(null);
  const ilkOge = useRef<HTMLAnchorElement>(null);
  const panelId = useId();
  const istemci = useQueryClient();
  const yonlendir = useNavigate();
  const bildirimleriTemizle = useBildirimleriTemizle();

  const cikis = useMutation({
    mutationFn: () => cagir(api.POST("/api/cikis")),
    // Sunucuya ulaşılamasa da kullanıcı çıkmış sayılır: önbellek temizlenir, giriş sayfasına gidilir.
    onSettled: () => {
      bildirimleriTemizle();
      istemci.clear();
      istemci.setQueryData(BEN_ANAHTARI, null);
      const durum: GirisDurumu = { mesaj: "Çıkış yaptınız." };
      yonlendir("/giris", { replace: true, state: durum });
    },
  });

  useEffect(() => {
    if (!acik) return;
    ilkOge.current?.focus();
    // Effect: tarayıcının olaylarına (belge düzeyinde tıklama) bağlanmak React'in dışındadır.
    const disariTiklama = (olay: PointerEvent) => {
      if (!kutu.current?.contains(olay.target as Node)) setAcik(false);
    };
    document.addEventListener("pointerdown", disariTiklama);
    return () => document.removeEventListener("pointerdown", disariTiklama);
  }, [acik]);

  return (
    <div
      ref={kutu}
      className={stil.hesapKutusu}
      onKeyDown={(olay) => {
        if (olay.key === "Escape" && acik) {
          setAcik(false);
          dugme.current?.focus();
        }
      }}
      onBlur={(olay) => {
        if (!kutu.current?.contains(olay.relatedTarget as Node | null)) setAcik(false);
      }}
    >
      <button
        ref={dugme}
        type="button"
        className={stil.avatar}
        aria-expanded={acik}
        aria-controls={panelId}
        aria-label={`Hesap: ${ad}`}
        title={`${ad} · ${rol}`}
        onClick={() => setAcik((a) => !a)}
      >
        {basHarfler(ad)}
      </button>
      <div id={panelId} className={stil.hesapPaneli} hidden={!acik}>
        <p className={stil.hesapAdi}>
          <strong>{ad}</strong>
          <span>{rol}</span>
        </p>
        <Link ref={ilkOge} to="/hesabim" className={stil.hesapOgesi} onClick={() => setAcik(false)}>
          <UserRound aria-hidden="true" className={stil.ikon} />
          Hesabım
        </Link>
        <button type="button" className={stil.hesapOgesi} onClick={() => cikis.mutate()} disabled={cikis.isPending}>
          <LogOut aria-hidden="true" className={stil.ikon} />
          Çıkış
        </button>
      </div>
    </div>
  );
}
