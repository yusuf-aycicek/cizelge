import { CalendarDays, Check, Play } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type AnimationEvent, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { MetinAlani } from "../bilesenler/Alan";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, useFormDegerleri } from "../bilesenler/form";
import { hareketAzaltilmis } from "../bilesenler/hareket";
import { ImzaLogosu } from "../bilesenler/ImzaLogosu";
import { TemaDugmesi } from "../bilesenler/TemaDugmesi";
import { UYGULAMA_ACIKLAMASI, UYGULAMA_ADI } from "../urun";
import type { GirisDurumu } from "./KorumaliAlan";
import { BEN_ANAHTARI, type Ben } from "./oturum";
import { SuzulenKartlar } from "./SuzulenKartlar";
import { TanitimPaneli } from "./TanitimPaneli";
import stil from "./Giris.module.css";

/** Başarılı girişte "Hoş geldiniz" bu kadar görünür, sonra yönlendirilir (hareket azaltılmışsa hemen). */
export const HOSGELDIN_MS = 700;
const BOS_ALAN_MESAJI = "E-posta ve parolanızı yazın.";

/**
 * Giriş. Solda giriş kartı, sağda tanıtım paneli (telefonda altta). Sunucunun mesajları olduğu
 * gibi gösterilir: "E-posta ya da parola hatalı" (hangisinin yanlış olduğu bilerek söylenmez) ve
 * kaba kuvvet kilidinde "15 dakika sonra yeniden deneyin". Hata ve boş alan mesajı kartın içinde,
 * düğmenin hemen üstündedir; kart kısa bir sallanmayla dikkati çeker. Boş alanla sunucuya gidilmez.
 *
 * Giriş düğmesi önce "Giriş yapılıyor…", başarıda onay işaretiyle "Hoş geldiniz" der, sonra
 * yönlendirir.
 *
 * "Demo ile dene" yalnızca sunucuda demo açıksa görünür (ADR 0027). Parola arayüzde yoktur:
 * sunucunun ayrı ucu demo hesabına oturum açar, çerez girişteki gibidir.
 */
export function GirisSayfasi() {
  const durum = (useLocation().state ?? {}) as GirisDurumu;
  const yonlendir = useNavigate();
  const istemci = useQueryClient();
  const form = useFormDegerleri({ email: "", sifre: "" });
  const [bosAlan, setBosAlan] = useState(false);
  const [sallan, setSallan] = useState(false);
  const [hosgeldin, setHosgeldin] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  function salla() {
    if (!hareketAzaltilmis()) setSallan(true);
  }
  function sallanmaBitti(olay: AnimationEvent) {
    if (olay.animationName.includes("salla")) setSallan(false);
  }

  function girildi(ben: Ben) {
    const git = () => {
      istemci.clear(); // önceki kullanıcının önbellekteki verisi kalmasın
      istemci.setQueryData(BEN_ANAHTARI, ben);
      yonlendir(durum.donus && durum.donus !== "/giris" ? durum.donus : "/", { replace: true });
    };
    setHosgeldin(true);
    if (hareketAzaltilmis()) git();
    else window.setTimeout(git, HOSGELDIN_MS);
  }

  // useMutation: sunucuda bir şeyi değiştiren (ya da oturum açan) istek. useQuery'den farkı:
  // kendiliğinden çalışmaz, `mutate` çağrılınca çalışır.
  const giris = useMutation({
    mutationFn: () => cagir(api.POST("/api/giris", { body: form.degerler })),
    onSuccess: girildi,
    onError: salla,
  });
  const demoDurumu = useQuery({
    queryKey: ["oturum", "demo"],
    queryFn: () => cagir(api.GET("/api/oturum/demo")),
    staleTime: Infinity,
  });
  const demo = useMutation({
    mutationFn: () => cagir(api.POST("/api/oturum/demo")),
    onSuccess: girildi,
    onError: salla,
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    if (!form.degerler.email.trim() || !form.degerler.sifre) {
      setBosAlan(true);
      giris.reset();
      salla();
      // İlk boş alana odaklanılır: klavyeyle kullanan doğrudan yazmaya devam eder.
      const bos = [...(formRef.current?.querySelectorAll("input") ?? [])].find((g) => !g.value.trim());
      bos?.focus();
      return;
    }
    setBosAlan(false);
    giris.mutate();
  }

  const sunucu = sunucuHatalari(giris.error);
  const genelHata = bosAlan ? BOS_ALAN_MESAJI : (sunucu.genel ?? sunucuHatalari(demo.error).genel);
  const mesgul = giris.isPending || demo.isPending || hosgeldin;

  return (
    <div className={stil.sayfa}>
      <SuzulenKartlar />
      <div className={stil.sol}>
        <header className={stil.marka}>
          <CalendarDays aria-hidden="true" className={stil.logo} />
          <span className={stil.markaAdi}>
            <span className={stil.urunAdi}>{UYGULAMA_ADI}</span>
            <span className={stil.urunAciklamasi}>{UYGULAMA_ACIKLAMASI}</span>
          </span>
          <TemaDugmesi />
        </header>

        <main className={stil.kartAlani}>
          <div className={`${stil.kart} ${sallan ? stil.sallan : ""}`} onAnimationEnd={sallanmaBitti}>
            <h1 className={stil.baslik}>Tekrar hoş geldiniz</h1>
            <p className={stil.altBaslik}>Okulunuzun programına kaldığınız yerden devam edin.</p>
            {durum.mesaj && !giris.error && <p className={stil.bilgi}>{durum.mesaj}</p>}
            <form ref={formRef} noValidate onSubmit={gonder} className={stil.form}>
              <MetinAlani etiket="E-posta" type="email" autoComplete="email" gerekli hata={sunucu.alanlar.email} {...form.alan("email")} />
              <MetinAlani etiket="Parola" type="password" autoComplete="current-password" gerekli hata={sunucu.alanlar.sifre} {...form.alan("sifre")} />
              <FormHatasi mesaj={genelHata} />
              {hosgeldin ? (
                <Dugme type="button" className={`${stil.genisDugme} ${stil.basarili}`} ikon={<Check />} aria-disabled="true">
                  Hoş geldiniz
                </Dugme>
              ) : (
                <Dugme type="submit" className={stil.genisDugme} disabled={mesgul && !giris.isPending} yukleniyor={giris.isPending} yukleniyorMetni="Giriş yapılıyor…">
                  Giriş yap
                </Dugme>
              )}
              {/* Düğmenin metni değişince ekran okuyucu bunu kendiliğinden okumaz; durum bölgesi okur. */}
              <p role="status" className="gorunmez">
                {hosgeldin ? "Giriş başarılı. Hoş geldiniz." : ""}
              </p>
            </form>

            {demoDurumu.data?.acik && (
              <>
                <div className={stil.ayirici}>
                  <span>ya da</span>
                </div>
                {/* Işıltı çerçevesi: düğmenin arkasında dönen renkli bir halka (yalnızca süs). */}
                <span className={stil.demoCercevesi}>
                  <Dugme
                    tur="ikincil"
                    ikon={<Play />}
                    className={`${stil.genisDugme} ${stil.demoDugmesi}`}
                    aria-describedby="demo-notu"
                    onClick={() => demo.mutate()}
                    disabled={mesgul && !demo.isPending}
                    yukleniyor={demo.isPending}
                    yukleniyorMetni="Demo açılıyor…"
                  >
                    Demo ile dene
                  </Dugme>
                </span>
                <p id="demo-notu" className={stil.not}>
                  Örnek okulla açılır, parola gerekmez. Demo verileri düzenli olarak sıfırlanır.
                </p>
              </>
            )}

            <p className={stil.alt}>
              Okulunuz henüz kayıtlı değil mi? <Link to="/kayit">Okulunuzu kaydedin</Link>
            </p>
          </div>
          <p className={stil.imza}>
            <ImzaLogosu boyut={24} />
            Yusuf Ayçiçek tarafından geliştirildi
          </p>
        </main>
      </div>
      <TanitimPaneli />
    </div>
  );
}
