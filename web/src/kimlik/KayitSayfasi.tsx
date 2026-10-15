import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, useFormDegerleri, useIlkHatayaOdaklan, type AlanHatalari } from "../bilesenler/form";
import { BEN_ANAHTARI } from "./oturum";
import stil from "./Kimlik.module.css";

export const EN_AZ_PAROLA = 12;

/** Parola uzunluğu göstergesi: yazarken kaç karakter kaldığını söyler. */
export function parolaAciklamasi(parola: string): string {
  const kalan = EN_AZ_PAROLA - parola.length;
  if (parola.length === 0) return `En az ${EN_AZ_PAROLA} karakter.`;
  return kalan > 0 ? `En az ${EN_AZ_PAROLA} karakter. ${kalan} karakter daha.` : "Uzunluk yeterli ✓";
}

/**
 * Okul kaydı: okul, ilk müdür hesabı ve oturum tek istekte oluşur.
 *
 * Arayüz yalnızca bariz olanı önceden söyler (boş alan, kısa parola, parolalar eşleşmiyor);
 * asıl kurallar sunucudadır ve sunucunun Türkçe mesajları ilgili alanın altına yerleşir.
 */
export function KayitSayfasi() {
  const yonlendir = useNavigate();
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const form = useFormDegerleri({
    okulAdi: "", gunSayisi: "5", gunlukDersSaati: "8", ad: "", email: "", sifre: "", sifreTekrar: "",
  });
  const [istemciHatalari, setIstemciHatalari] = useState<AlanHatalari>({});
  const [deneme, setDeneme] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);
  useIlkHatayaOdaklan(formRef, deneme);
  const d = form.degerler;

  const kayit = useMutation({
    mutationFn: () =>
      cagir(api.POST("/api/kayit", {
        body: {
          okul: { ad: d.okulAdi.trim(), gun_sayisi: Number(d.gunSayisi), gunluk_ders_saati: Number(d.gunlukDersSaati) },
          ad: d.ad.trim(),
          email: d.email.trim(),
          sifre: d.sifre,
        },
      })),
    onSuccess: (ben) => {
      istemci.clear();
      istemci.setQueryData(BEN_ANAHTARI, ben);
      bildirim("basari", `${ben.okul.ad} kaydedildi. Hoş geldiniz!`);
      yonlendir("/", { replace: true });
    },
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const h: AlanHatalari = {};
    if (!d.okulAdi.trim()) h["okul.ad"] = "Okulunuzun adını girin";
    const saat = Number(d.gunlukDersSaati);
    if (!Number.isInteger(saat) || saat < 1 || saat > 16) h["okul.gunluk_ders_saati"] = "1 ile 16 arasında bir sayı girin";
    if (!d.ad.trim()) h.ad = "Adınızı girin";
    if (!d.email.trim()) h.email = "E-posta adresinizi girin";
    if (d.sifre.length < EN_AZ_PAROLA) h.sifre = `Parola en az ${EN_AZ_PAROLA} karakter olmalı`;
    if (d.sifreTekrar !== d.sifre) h.sifreTekrar = "Parolalar eşleşmiyor";
    setIstemciHatalari(h);
    setDeneme((n) => n + 1);
    if (Object.keys(h).length === 0) kayit.mutate();
  }

  // Sunucunun alan listesi olmayan bilinen hataları: 409 yalnızca e-posta çakışmasıdır,
  // "Parola ..." ile başlayan 422 parola kuralıdır.
  const sunucu = sunucuHatalari(kayit.error, (h) =>
    h.durum === 409 ? "email" : h.durum === 422 && h.message.startsWith("Parola") ? "sifre" : undefined,
  );
  const hata = (alan: string) => istemciHatalari[alan] ?? sunucu.alanlar[alan];

  return (
    <div className={`${stil.kart} ${stil.genis}`}>
      <h1>Okulunuzu kaydedin</h1>
      <p className={stil.aciklama}>Okulunuzun bilgilerini ve müdür hesabınızı oluşturun. Sonra bilgileri değiştirebilirsiniz.</p>
      <FormHatasi mesaj={sunucu.genel} />
      <form ref={formRef} noValidate onSubmit={gonder}>
        <fieldset className={stil.bolum}>
          <legend>Okulunuz</legend>
          <MetinAlani etiket="Okulun adı" gerekli hata={hata("okul.ad")} autoComplete="organization" {...form.alan("okulAdi")} />
          <div className={stil.ikili}>
            <SecimAlani etiket="Haftada kaç gün ders var" hata={hata("okul.gun_sayisi")} {...form.alan("gunSayisi")}>
              <option value="5">5 gün (pazartesi-cuma)</option>
              <option value="6">6 gün (pazartesi-cumartesi)</option>
            </SecimAlani>
            <MetinAlani etiket="Günde kaç ders saati var" type="number" inputMode="numeric" min={1} max={16}
              hata={hata("okul.gunluk_ders_saati")} {...form.alan("gunlukDersSaati")} />
          </div>
        </fieldset>
        <fieldset className={stil.bolum}>
          <legend>Müdür hesabınız</legend>
          <MetinAlani etiket="Adınız ve soyadınız" gerekli hata={hata("ad")} autoComplete="name" {...form.alan("ad")} />
          <MetinAlani etiket="E-posta" type="email" gerekli hata={hata("email")} autoComplete="email"
            aciklama="Giriş yaparken kullanacaksınız." {...form.alan("email")} />
          <MetinAlani etiket="Parola" type="password" gerekli hata={hata("sifre")} autoComplete="new-password"
            aciklama={parolaAciklamasi(d.sifre)} {...form.alan("sifre")} />
          <MetinAlani etiket="Parola (tekrar)" type="password" gerekli hata={hata("sifreTekrar")} autoComplete="new-password"
            {...form.alan("sifreTekrar")} />
        </fieldset>
        <Dugme type="submit" className={stil.tamGenislik} yukleniyor={kayit.isPending} yukleniyorMetni="Kaydediliyor...">
          Okulu kaydet
        </Dugme>
      </form>
      <p className={stil.alt}>
        Hesabınız var mı? <Link to="/giris">Giriş yapın</Link>
      </p>
    </div>
  );
}
