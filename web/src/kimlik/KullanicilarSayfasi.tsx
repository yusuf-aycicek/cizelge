/**
 * Kullanıcılar (5.6): okulun yönetici hesapları. Müdür yardımcı ekler, parolasını yeniden belirler,
 * rolünü değiştirir ve siler; yardımcı aynı listeyi düğmeler olmadan görür.
 *
 * Değişmez kural (sunucuda): her okulda en az bir müdür vardır. Arayüz bunu önceden söyler: tek
 * müdürün "Yardımcı yap" ve "Sil" düğmeleri pasiftir ve tablonun altında nedeni yazar. Aynı anda
 * başka bir müdür rol değiştirirse sunucunun 409 mesajı bildirim olarak gösterilir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Plus, ShieldCheck, ShieldMinus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { MetinAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi, sunucuHatalari, type AlanHatalari } from "../bilesenler/form";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Tablo } from "../bilesenler/Tablo";
import stil from "../listeler/Liste.module.css";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { EN_AZ_PAROLA, parolaAciklamasi } from "./KayitSayfasi";
import { BEN_ANAHTARI, ROL_ADLARI, useBen } from "./oturum";

type Kullanici = components["schemas"]["KullaniciYanit"];

export const KULLANICILAR = ["kullanicilar"] as const;

const yol = (kullanici_id: string) => ({ params: { path: { kullanici_id } } });

/** Tek müdür kalınca rolü düşürülemez ve silinemez; açıklama tek yerde. */
export function sonMudurAciklamasi(ad: string) {
  return `Okulda tek müdür var: ${ad}. Okul müdürsüz kalamayacağı için bu hesap yardımcı yapılamaz ve silinemez. Önce başka bir kullanıcıyı müdür yapın.`;
}

export function KullanicilarSayfasi() {
  const ben = useBen().data;
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const kullanicilar = useQuery({ queryKey: KULLANICILAR, queryFn: () => cagir(api.GET("/api/kullanicilar")) });
  const [silinecek, setSilinecek] = useState<Kullanici | null>(null);
  const [parolasi, setParolasi] = useState<Kullanici | null>(null);

  const tazele = () => istemci.invalidateQueries({ queryKey: KULLANICILAR });

  const rolDegistir = useMutation({
    mutationFn: (d: { k: Kullanici; rol: "mudur" | "mudur_yardimcisi" }) =>
      cagir(api.PUT("/api/kullanicilar/{kullanici_id}/rol", { ...yol(d.k.id), body: { rol: d.rol } })),
    onSuccess: async (k) => {
      await tazele();
      // Kendi rolünü düşüren müdür artık yardımcı: menü ve düğmeler yeni role göre çizilsin.
      if (k.id === ben?.kullanici.id) await istemci.invalidateQueries({ queryKey: BEN_ANAHTARI });
      bildirim("basari", `${k.ad} artık ${ROL_ADLARI[k.rol]?.toLocaleLowerCase("tr") ?? k.rol}.`);
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
  });
  const sil = useMutation({
    mutationFn: (k: Kullanici) => cagir(api.DELETE("/api/kullanicilar/{kullanici_id}", yol(k.id))),
    onSuccess: async (_, k) => {
      // Kendi hesabını silen müdürün oturumu da silindi: ben sorgusu 401 alır, giriş sayfasına döner.
      if (k.id === ben?.kullanici.id) return void istemci.invalidateQueries({ queryKey: BEN_ANAHTARI });
      await tazele();
      bildirim("basari", `${k.ad} silindi.`);
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
    onSettled: () => setSilinecek(null),
  });

  if (!ben) return null; // korumalı alan içinde her zaman dolu
  const mudurMu = ben.kullanici.rol === "mudur";
  const liste = turkceSirala(kullanicilar.data ?? [], (k) => `${k.rol === "mudur" ? 0 : 1} ${k.ad}`);
  const mudurler = liste.filter((k) => k.rol === "mudur");
  const tekMudur = mudurler.length === 1 ? mudurler[0] : undefined;

  return (
    <>
      <SayfaBasligi baslik="Kullanıcılar">
        Okulun programını düzenleyebilen yöneticiler.
      </SayfaBasligi>
      <section className={sayfaStili.kart} aria-labelledby="yoneticiler">
        <h2 id="yoneticiler">Yöneticiler</h2>
        {!mudurMu && (
          <p className={stil.kartAciklamasi}>Kullanıcı eklemeyi, silmeyi ve rol değiştirmeyi yalnızca okul müdürü yapabilir.</p>
        )}
        {kullanicilar.isError && <FormHatasi mesaj={hataMetni(kullanicilar.error)} />}
        {liste.length > 0 && (
          <Tablo<Kullanici>
            baslik="Yöneticiler"
            satirlar={liste}
            satirAnahtari={(k) => k.id}
            sutunlar={[
              { baslik: "Ad", hucre: (k) => (k.id === ben.kullanici.id ? `${k.ad} (siz)` : k.ad) },
              { baslik: "E-posta", hucre: (k) => k.email },
              { baslik: "Rol", hucre: (k) => ROL_ADLARI[k.rol] ?? k.rol },
              ...(mudurMu
                ? [
                    {
                      baslik: "İşlemler",
                      baslikGizli: true,
                      hizala: "sag" as const,
                      hucre: (k: Kullanici) => {
                        const sonMudur = tekMudur?.id === k.id;
                        return (
                          <span className={stil.islemler}>
                            {k.rol === "mudur" ? (
                              <Dugme ikon={<ShieldMinus />} tur="metin" disabled={sonMudur} aria-label={`${k.ad}: yardımcı yap`}
                                onClick={() => rolDegistir.mutate({ k, rol: "mudur_yardimcisi" })}>
                                <span className={stil.islemMetni}>Yardımcı yap</span>
                              </Dugme>
                            ) : (
                              <Dugme ikon={<ShieldCheck />} tur="metin" aria-label={`${k.ad}: müdür yap`}
                                onClick={() => rolDegistir.mutate({ k, rol: "mudur" })}>
                                <span className={stil.islemMetni}>Müdür yap</span>
                              </Dugme>
                            )}
                            {k.id !== ben.kullanici.id && (
                              <Dugme ikon={<KeyRound />} tur="metin" aria-label={`${k.ad}: parolasını yeniden belirle`}
                                onClick={() => setParolasi(k)}>
                                <span className={stil.islemMetni}>Parola</span>
                              </Dugme>
                            )}
                            <Dugme ikon={<Trash2 />} tur="metin" disabled={sonMudur} aria-label={`${k.ad}: sil`}
                              onClick={() => setSilinecek(k)}>
                              <span className={stil.islemMetni}>Sil</span>
                            </Dugme>
                          </span>
                        );
                      },
                    },
                  ]
                : []),
            ]}
          />
        )}
        {mudurMu && tekMudur && <p className={stil.kartAciklamasi}>{sonMudurAciklamasi(tekMudur.ad)}</p>}
        {mudurMu && (
          <p className={stil.kartAciklamasi}>
            Kendi parolanızı <Link to="/hesabim">Hesabım</Link> sayfasından değiştirirsiniz.
          </p>
        )}
      </section>
      {mudurMu && <YardimciEkle />}
      <OnayPenceresi
        acik={silinecek !== null}
        baslik={silinecek ? `${silinecek.ad} silinsin mi?` : ""}
        mesaj={
          silinecek?.id === ben.kullanici.id
            ? "Kendi hesabınızı siliyorsunuz. Oturumunuz kapanır ve bu hesapla bir daha giriş yapamazsınız."
            : "Hesap ve açık oturumları silinir. Bu kişi bir daha giriş yapamaz."
        }
        onaylaMetni="Sil"
        tehlikeli
        yukleniyor={sil.isPending}
        onVazgec={() => setSilinecek(null)}
        onOnayla={() => silinecek && sil.mutate(silinecek)}
      />
      {parolasi && <ParolaBelirle kullanici={parolasi} onKapat={() => setParolasi(null)} />}
    </>
  );
}

/** Müdür yardımcısı ekleme formu: ad, e-posta ve ilk parola (kişi sonra Hesabım'dan değiştirir). */
function YardimciEkle() {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const bos = { ad: "", email: "", sifre: "" };
  const [d, setD] = useState(bos);
  const [hatalar, setHatalar] = useState<AlanHatalari>({});
  const ekle = useMutation({
    mutationFn: () => cagir(api.POST("/api/kullanicilar", { body: { ad: d.ad.trim(), email: d.email.trim(), sifre: d.sifre } })),
    onSuccess: async (k) => {
      await istemci.invalidateQueries({ queryKey: KULLANICILAR });
      setD(bos);
      bildirim("basari", `${k.ad} müdür yardımcısı olarak eklendi. Giriş bilgilerini kendisine iletin.`);
    },
  });
  const sunucu = sunucuHatalari(ekle.error, (h) =>
    h.message.includes("e-posta") ? "email" : h.message.startsWith("Parola") ? "sifre" : undefined,
  );
  const hata = (alan: string) => hatalar[alan] ?? sunucu.alanlar[alan];

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    const h: AlanHatalari = {};
    if (!d.ad.trim()) h.ad = "Adını yazın";
    if (!/^\S+@\S+\.\S+$/.test(d.email.trim())) h.email = "Geçerli bir e-posta adresi girin";
    if (d.sifre.length < EN_AZ_PAROLA) h.sifre = `Parola en az ${EN_AZ_PAROLA} karakter olmalı`;
    setHatalar(h);
    if (Object.keys(h).length === 0) ekle.mutate();
  }

  return (
    <section className={sayfaStili.kart} aria-labelledby="yardimci-ekle">
      <h2 id="yardimci-ekle">Müdür yardımcısı ekle</h2>
      <FormHatasi mesaj={sunucu.genel} />
      <form noValidate onSubmit={gonder}>
        <MetinAlani etiket="Ad soyad" gerekli autoComplete="off" value={d.ad} hata={hata("ad")} maxLength={200}
          onChange={(o) => setD({ ...d, ad: o.target.value })} />
        <MetinAlani etiket="E-posta" type="email" gerekli autoComplete="off" value={d.email} hata={hata("email")}
          onChange={(o) => setD({ ...d, email: o.target.value })} />
        <MetinAlani etiket="İlk parola" type="password" gerekli autoComplete="new-password" value={d.sifre} hata={hata("sifre")}
          aciklama={parolaAciklamasi(d.sifre)} onChange={(o) => setD({ ...d, sifre: o.target.value })} />
        <Dugme ikon={<Plus />} type="submit" yukleniyor={ekle.isPending} yukleniyorMetni="Ekleniyor...">
          Müdür yardımcısı ekle
        </Dugme>
      </form>
    </section>
  );
}

/** Parolayı yeniden belirleme penceresi; kişinin açık oturumları kapanır. */
function ParolaBelirle({ kullanici, onKapat }: { kullanici: Kullanici; onKapat: () => void }) {
  const bildirim = useBildirim();
  const [sifre, setSifre] = useState("");
  const [tekrar, setTekrar] = useState("");
  const [hatalar, setHatalar] = useState<AlanHatalari>({});
  const belirle = useMutation({
    mutationFn: () => cagir(api.PUT("/api/kullanicilar/{kullanici_id}/sifre", { ...yol(kullanici.id), body: { sifre } })),
    onSuccess: () => {
      bildirim("basari", `${kullanici.ad} için yeni parola belirlendi; açık oturumları kapatıldı.`);
      onKapat();
    },
  });

  function onayla() {
    const h: AlanHatalari = {};
    if (sifre.length < EN_AZ_PAROLA) h.sifre = `Parola en az ${EN_AZ_PAROLA} karakter olmalı`;
    if (tekrar !== sifre) h.tekrar = "Parolalar eşleşmiyor";
    setHatalar(h);
    if (Object.keys(h).length === 0) belirle.mutate();
  }

  return (
    <OnayPenceresi
      acik
      baslik={`${kullanici.ad} için yeni parola`}
      mesaj="Açık oturumları kapanacak; yeni parolayla yeniden giriş yapması gerekir."
      onaylaMetni="Parolayı belirle"
      yukleniyor={belirle.isPending}
      onVazgec={onKapat}
      onOnayla={onayla}
    >
      <FormHatasi mesaj={belirle.error ? hataMetni(belirle.error) : undefined} />
      <MetinAlani etiket="Yeni parola" type="password" autoComplete="new-password" value={sifre} hata={hatalar.sifre}
        aciklama={parolaAciklamasi(sifre)} onChange={(o) => setSifre(o.target.value)} />
      <MetinAlani etiket="Yeni parola (tekrar)" type="password" autoComplete="new-password" value={tekrar} hata={hatalar.tekrar}
        onChange={(o) => setTekrar(o.target.value)} />
    </OnayPenceresi>
  );
}
