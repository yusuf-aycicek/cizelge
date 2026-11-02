import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { KeyRound } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { MetinAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, useFormDegerleri, useIlkHatayaOdaklan, type AlanHatalari } from "../bilesenler/form";
import stil from "../sayfalar/Sayfa.module.css";
import { EN_AZ_PAROLA, parolaAciklamasi } from "./KayitSayfasi";
import { ROL_ADLARI, useBen } from "./oturum";

/**
 * Hesabım: kullanıcının bilgileri ve parola değiştirme. Parola değişince sunucu bu oturum
 * dışındaki bütün oturumları kapatır (ör. başka bir bilgisayarda açık kalmış olan).
 */
export function HesabimSayfasi() {
  const ben = useBen().data;
  const bildirim = useBildirim();
  const form = useFormDegerleri({ eski: "", yeni: "", yeniTekrar: "" });
  const [istemciHatalari, setIstemciHatalari] = useState<AlanHatalari>({});
  const [deneme, setDeneme] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);
  useIlkHatayaOdaklan(formRef, deneme);

  const degistir = useMutation({
    mutationFn: () => cagir(api.PUT("/api/ben/sifre", { body: { eski: form.degerler.eski, yeni: form.degerler.yeni } })),
    onSuccess: () => {
      form.sifirla();
      bildirim("basari", "Parolanız değiştirildi. Diğer cihazlardaki oturumlarınız kapatıldı.");
    },
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const d = form.degerler;
    const h: AlanHatalari = {};
    if (!d.eski) h.eski = "Mevcut parolanızı girin";
    if (d.yeni.length < EN_AZ_PAROLA) h.yeni = `Parola en az ${EN_AZ_PAROLA} karakter olmalı`;
    if (d.yeniTekrar !== d.yeni) h.yeniTekrar = "Parolalar eşleşmiyor";
    setIstemciHatalari(h);
    setDeneme((n) => n + 1);
    if (Object.keys(h).length === 0) degistir.mutate();
  }

  const sunucu = sunucuHatalari(degistir.error, (h) =>
    h.message.startsWith("Mevcut parola") ? "eski" : h.message.startsWith("Parola") ? "yeni" : undefined,
  );
  const hata = (alan: string) => istemciHatalari[alan] ?? sunucu.alanlar[alan];

  if (!ben) return null; // korumalı alan içinde her zaman dolu

  return (
    <>
      <SayfaBasligi baslik="Hesabım">Bilgileriniz ve parolanız.</SayfaBasligi>
      <section className={stil.kart} aria-labelledby="bilgilerim">
        <h2 id="bilgilerim">Bilgilerim</h2>
        <dl className={stil.durumListesi}>
          <dt>Ad</dt>
          <dd>{ben.kullanici.ad}</dd>
          <dt>E-posta</dt>
          <dd>{ben.kullanici.email}</dd>
          <dt>Rol</dt>
          <dd>{ROL_ADLARI[ben.kullanici.rol] ?? ben.kullanici.rol}</dd>
          <dt>Okul</dt>
          <dd>{ben.okul.ad}</dd>
        </dl>
      </section>
      <section className={stil.kart} aria-labelledby="parola">
        <h2 id="parola">Parolamı değiştir</h2>
        <FormHatasi mesaj={sunucu.genel} />
        <form ref={formRef} noValidate onSubmit={gonder}>
          <MetinAlani etiket="Mevcut parola" type="password" autoComplete="current-password" gerekli hata={hata("eski")} {...form.alan("eski")} />
          <MetinAlani etiket="Yeni parola" type="password" autoComplete="new-password" gerekli hata={hata("yeni")}
            aciklama={parolaAciklamasi(form.degerler.yeni)} {...form.alan("yeni")} />
          <MetinAlani etiket="Yeni parola (tekrar)" type="password" autoComplete="new-password" gerekli hata={hata("yeniTekrar")}
            {...form.alan("yeniTekrar")} />
          <Dugme ikon={<KeyRound />} type="submit" yukleniyor={degistir.isPending} yukleniyorMetni="Değiştiriliyor...">
            Parolayı değiştir
          </Dugme>
        </form>
      </section>
    </>
  );
}
