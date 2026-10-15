import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { MetinAlani } from "../bilesenler/Alan";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, useFormDegerleri, useIlkHatayaOdaklan, type AlanHatalari } from "../bilesenler/form";
import type { GirisDurumu } from "./KorumaliAlan";
import { BEN_ANAHTARI } from "./oturum";
import stil from "./Kimlik.module.css";

/**
 * Giriş. Sunucunun mesajları olduğu gibi gösterilir: "E-posta ya da parola hatalı" (hangisinin
 * yanlış olduğu bilerek söylenmez) ve kaba kuvvet kilidinde "15 dakika sonra yeniden deneyin".
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

  // useMutation: sunucuda bir şeyi değiştiren (ya da oturum açan) istek. useQuery'den farkı:
  // kendiliğinden çalışmaz, `mutate` çağrılınca çalışır.
  const giris = useMutation({
    mutationFn: () => cagir(api.POST("/api/giris", { body: form.degerler })),
    onSuccess: (ben) => {
      istemci.clear(); // önceki kullanıcının önbellekteki verisi kalmasın
      istemci.setQueryData(BEN_ANAHTARI, ben);
      yonlendir(durum.donus && durum.donus !== "/giris" ? durum.donus : "/", { replace: true });
    },
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

  return (
    <div className={stil.kart}>
      <h1>Giriş yap</h1>
      {durum.mesaj && !giris.error && <p className={stil.bilgi}>{durum.mesaj}</p>}
      <FormHatasi mesaj={sunucu.genel} />
      <form ref={formRef} noValidate onSubmit={gonder}>
        <MetinAlani etiket="E-posta" type="email" autoComplete="email" gerekli hata={hata("email")} {...form.alan("email")} />
        <MetinAlani etiket="Parola" type="password" autoComplete="current-password" gerekli hata={hata("sifre")} {...form.alan("sifre")} />
        <Dugme type="submit" className={stil.tamGenislik} yukleniyor={giris.isPending} yukleniyorMetni="Giriş yapılıyor...">
          Giriş yap
        </Dugme>
      </form>
      <p className={stil.alt}>
        Okulunuz henüz kayıtlı değil mi? <Link to="/kayit">Okulunuzu kaydedin</Link>
      </p>
    </div>
  );
}
