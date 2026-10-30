import { CalendarDays, Play } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { MetinAlani } from "../bilesenler/Alan";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, useFormDegerleri, useIlkHatayaOdaklan, type AlanHatalari } from "../bilesenler/form";
import { UYGULAMA_ACIKLAMASI, UYGULAMA_ADI } from "../urun";
import type { GirisDurumu } from "./KorumaliAlan";
import { BEN_ANAHTARI, type Ben } from "./oturum";
import { TanitimPaneli } from "./TanitimPaneli";
import stil from "./Giris.module.css";

/**
 * Giriş. Solda giriş kartı, sağda tanıtım paneli (telefonda altta). Sunucunun mesajları olduğu
 * gibi gösterilir: "E-posta ya da parola hatalı" (hangisinin yanlış olduğu bilerek söylenmez) ve
 * kaba kuvvet kilidinde "15 dakika sonra yeniden deneyin".
 *
 * "Demo ile dene" yalnızca sunucuda demo açıksa görünür (ADR 0027). Parola arayüzde yoktur:
 * sunucunun ayrı ucu demo hesabına oturum açar, çerez girişteki gibidir.
 */
export function GirisSayfasi() {
  const durum = (useLocation().state ?? {}) as GirisDurumu;
  const yonlendir = useNavigate();
  const istemci = useQueryClient();
  const form = useFormDegerleri({ email: "", sifre: "" });
  const [istemciHatalari, setIstemciHatalari] = useState<AlanHatalari>({});
  const [deneme, setDeneme] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);
  useIlkHatayaOdaklan(formRef, deneme);

  function girildi(ben: Ben) {
    istemci.clear(); // önceki kullanıcının önbellekteki verisi kalmasın
    istemci.setQueryData(BEN_ANAHTARI, ben);
    yonlendir(durum.donus && durum.donus !== "/giris" ? durum.donus : "/", { replace: true });
  }

  // useMutation: sunucuda bir şeyi değiştiren (ya da oturum açan) istek. useQuery'den farkı:
  // kendiliğinden çalışmaz, `mutate` çağrılınca çalışır.
  const giris = useMutation({
    mutationFn: () => cagir(api.POST("/api/giris", { body: form.degerler })),
    onSuccess: girildi,
  });
  const demoDurumu = useQuery({
    queryKey: ["oturum", "demo"],
    queryFn: () => cagir(api.GET("/api/oturum/demo")),
    staleTime: Infinity,
  });
  const demo = useMutation({
    mutationFn: () => cagir(api.POST("/api/oturum/demo")),
    onSuccess: girildi,
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const hatalar: AlanHatalari = {};
    if (!form.degerler.email.trim()) hatalar.email = "E-posta adresinizi girin";
    if (!form.degerler.sifre) hatalar.sifre = "Parolanızı girin";
    setIstemciHatalari(hatalar);
    setDeneme((d) => d + 1);
    if (Object.keys(hatalar).length === 0) giris.mutate();
  }

  const sunucu = sunucuHatalari(giris.error);
  const hata = (alan: string) => istemciHatalari[alan] ?? sunucu.alanlar[alan];
  const mesgul = giris.isPending || demo.isPending;

  return (
    <div className={stil.sayfa}>
      <div className={stil.sol}>
        <header className={stil.marka}>
          <CalendarDays aria-hidden="true" className={stil.logo} />
          <span>
            <span className={stil.urunAdi}>{UYGULAMA_ADI}</span>
            <span className={stil.urunAciklamasi}>{UYGULAMA_ACIKLAMASI}</span>
          </span>
        </header>

        <main className={stil.kartAlani}>
          <div className={stil.kart}>
            <h1 className={stil.baslik}>Tekrar hoş geldiniz</h1>
            <p className={stil.altBaslik}>Okulunuzun programına kaldığınız yerden devam edin.</p>
            {durum.mesaj && !giris.error && <p className={stil.bilgi}>{durum.mesaj}</p>}
            <FormHatasi mesaj={sunucu.genel ?? sunucuHatalari(demo.error).genel} />
            <form ref={formRef} noValidate onSubmit={gonder} className={stil.form}>
              <MetinAlani etiket="E-posta" type="email" autoComplete="email" gerekli hata={hata("email")} {...form.alan("email")} />
              <MetinAlani etiket="Parola" type="password" autoComplete="current-password" gerekli hata={hata("sifre")} {...form.alan("sifre")} />
              <Dugme type="submit" className={stil.genisDugme} disabled={demo.isPending} yukleniyor={giris.isPending} yukleniyorMetni="Giriş yapılıyor...">
                Giriş yap
              </Dugme>
            </form>

            {demoDurumu.data?.acik && (
              <>
                <div className={stil.ayirici}>
                  <span>ya da</span>
                </div>
                <Dugme
                  tur="ikincil"
                  ikon={<Play />}
                  className={`${stil.genisDugme} ${stil.demoDugmesi}`}
                  aria-describedby="demo-notu"
                  onClick={() => demo.mutate()}
                  disabled={mesgul && !demo.isPending}
                  yukleniyor={demo.isPending}
                  yukleniyorMetni="Demo açılıyor..."
                >
                  Demo ile dene
                </Dugme>
                <p id="demo-notu" className={stil.not}>
                  Örnek okulla açılır, parola gerekmez. Demo verileri düzenli olarak sıfırlanır.
                </p>
              </>
            )}

            <p className={stil.alt}>
              Okulunuz henüz kayıtlı değil mi? <Link to="/kayit">Okulunuzu kaydedin</Link>
            </p>
          </div>
        </main>
      </div>
      <TanitimPaneli />
    </div>
  );
}
