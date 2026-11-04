/** Öğretmen, sınıf ve ders sayfaları: ortak liste bileşeninin üç kullanımı. */
import { dersIsaretleri } from "../dersler/isaret";
import { OgretmenAdi } from "../bilesenler/OgretmenRozeti";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";
import { Link } from "react-router";
import stil from "./Liste.module.css";
import { hataMetni } from "../api/hata";
import { useBildirim } from "../bilesenler/Bildirim";
import { DersCipi } from "../dersler/DersCipi";
import { RenkSecici } from "../dersler/RenkSecici";
import { DagilimSekliHucresi, useDagilimSekilleri } from "../dersler/DagilimSekli";
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import { KURALLAR_ANAHTARI } from "../okul/OkulAyarlariSayfasi";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi, type Ders, type Ogretmen, type Sinif } from "./kaynaklar";
import { BransSecici } from "./BransSecici";
import { ListeSayfasi, type ListeAlani } from "./ListeSayfasi";
import { SubeGrubuSecici, SubeGruplariBolumu, useSubeGruplari } from "./SubeGruplari";

// Alan listeleri bileşenin dışında sabit: her çizimde yeni dizi oluşmasın (useMemo bağımlılığı).
const OGRETMEN_ALANLARI: ListeAlani[] = [
  { ad: "ad", etiket: "Adı soyadı", gerekli: true, ornek: "Ayşe Yılmaz" },
  {
    ad: "brans", etiket: "Branşı",
    secici: ({ etiket, deger, onDegistir, hata, satirda }) => (
      <BransSecici etiket={etiket} deger={deger} onDegistir={onDegistir} hata={hata} satirda={satirda} />
    ),
  },
];
const SINIF_ALANLARI: ListeAlani[] = [
  { ad: "ad", etiket: "Şube", gerekli: true, ornek: "9-A" },
  { ad: "seviye", etiket: "Sınıf seviyesi", tur: "sayi", gerekli: true, min: 1, max: 12, ornek: "9" },
];
const DERS_ALANLARI: ListeAlani[] = [
  { ad: "ad", etiket: "Dersin adı", gerekli: true, ornek: "Matematik" },
  { ad: "kisa_ad", etiket: "Kısa adı", ornek: "MAT" },
];

export function OgretmenlerSayfasi() {
  return (
    <ListeSayfasi<Ogretmen, { ad: string; brans: string }>
      // Ad, öğretmenin sayfasına (kişisel ayarlar ve müsaitlik) bağlantıdır; ayrıca satırda görünür
      // bir "Müsaitlik ve ayarlar" bağlantısı var (ad tek başına tıklanabilir görünmüyordu).
      gorunum={(alan, o) =>
        alan === "ad" ? (
          <Link to={`/ogretmenler/${o.id}`} className={stil.ogretmenBaglantisi}>
            <OgretmenAdi id={o.id} ad={o.ad} />
          </Link>
        ) : undefined
      }
      ekSutunlar={[
        {
          baslik: "Ayarlar",
          baslikGizli: true,
          hucre: (o) => (
            <Link to={`/ogretmenler/${o.id}`} className={stil.ayarBaglantisi} aria-label={`${o.ad}: müsaitlik ve kişisel ayarlar`}>
              <CalendarClock aria-hidden="true" />
              <span className={stil.islemMetni}>Müsaitlik ve ayarlar</span>
            </Link>
          ),
        },
      ]}
      baslik="Öğretmenler"
      aciklama="Okulunuzdaki öğretmenler. Branşı okulun derslerinden seçilir (birden çok olabilir). Bir öğretmenin adına ya da “Müsaitlik ve ayarlar”a tıklayınca kişisel ayarları ve müsaitlik çizelgesi açılır. Hangi derse kimin gireceğini Ders dağılımı sayfasında seçeceksiniz."
      tekil="Öğretmen"
      bos={{
        baslik: "Henüz öğretmen eklenmedi",
        aciklama: "Ders dağılımı yapabilmek için önce öğretmenlerinizi ekleyin. Aşağıdaki formla ardı ardına hızlıca girebilirsiniz.",
        dugme: "İlk öğretmeni ekle",
        cizim: "ogretmen",
      }}
      kaynak={ogretmenKaynagi}
      alanlar={OGRETMEN_ALANLARI}
      girdi={(d) => ({ ad: (d.ad ?? "").trim(), brans: (d.brans ?? "").trim() })}
    />
  );
}

export function SiniflarSayfasi() {
  // Aynı önbellek (sınıflar) ListeSayfasi'yle paylaşılır: ek istek gitmez.
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const gruplar = useSubeGruplari();
  return (
    <ListeSayfasi<Sinif, { ad: string; seviye: number }>
      ekSutunlar={[
        {
          baslik: "Şube grubu",
          hucre: (sinif) => <SubeGrubuSecici sinif={sinif} gruplar={gruplar.data ?? []} />,
        },
      ]}
      ekBolum={<SubeGruplariBolumu siniflar={siniflar.data ?? []} />}
      baslik="Sınıflar"
      aciklama="Okulunuzdaki şubeler. Seviye, seviye şablonunu aynı seviyedeki bütün şubelere uygulamak için kullanılır. Aynı seviyede farklı dersler okuyan şubeleri (ör. 11 Sayısal, 11 Sözel) aşağıda gruplayabilirsiniz."
      tekil="Sınıf"
      bos={{
        baslik: "Henüz sınıf eklenmedi",
        aciklama: "Şubelerinizi (9-A, 9-B, 10-A...) ve seviyelerini ekleyin.",
        dugme: "İlk sınıfı ekle",
        cizim: "sinif",
      }}
      kaynak={sinifKaynagi}
      alanlar={SINIF_ALANLARI}
      girdi={(d) => ({ ad: (d.ad ?? "").trim(), seviye: Number(d.seviye) })}
    />
  );
}

export function DerslerSayfasi() {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  // Aynı önbellek (dersler) ListeSayfasi'yle paylaşılır: ek istek gitmez.
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const isaretler = dersIsaretleri(dersler.data ?? []);
  const sekiller = useDagilimSekilleri();
  const kurallar = useQuery({ queryKey: KURALLAR_ANAHTARI, queryFn: () => cagir(api.GET("/api/ders-programi/kurallar")) });
  // Renk seçilince hemen kaydedilir. Ders listesi tazelenir; aynı önbelleği okuyan ders dağılımı ve
  // şablon da yeni rengi gösterir.
  const renkDegistir = useMutation({
    mutationFn: (d: { ders: Ders; renk: string }) => dersKaynagi.guncelle(d.ders.id, { renk: d.renk }),
    onSuccess: async (ders) => {
      await istemci.invalidateQueries({ queryKey: dersKaynagi.anahtar });
      bildirim("basari", `${ders.ad} dersinin rengi değiştirildi.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  return (
    <ListeSayfasi<Ders, { ad: string; kisa_ad: string }>
      gorunum={(alan, ders) =>
        alan === "ad" ? <DersCipi ad={ders.ad} renk={ders.renk} isaret={isaretler.get(ders.id)} /> : undefined
      }
      ekSutunlar={[
        {
          baslik: "Renk",
          hucre: (ders) => (
            <RenkSecici
              etiket={`${ders.ad} dersinin rengi`}
              deger={ders.renk}
              disabled={renkDegistir.isPending}
              onDegis={(renk) => renkDegistir.mutate({ ders, renk })}
            />
          ),
        },
        {
          baslik: "Dağılım şekli",
          hucre: (ders) =>
            sekiller.data && kurallar.data ? (
              <DagilimSekliHucresi ders={ders} sekiller={sekiller.data} kurallar={kurallar.data} />
            ) : null,
        },
      ]}
      baslik="Dersler"
      aciklama="Okulunuzda okutulan dersler. Her derse otomatik bir renk verilir; dersin her ekranda aynı renkte görünür, isterseniz değiştirebilirsiniz. Dağılım şekli dersin haftalık saatlerinin nasıl bloklara bölüneceğini söyler (ör. 5 saat: 2+2+1, her blok ayrı bir günde art arda); okulun önerisi Okul ayarlarındadır."
      tekil="Ders"
      bos={{
        baslik: "Henüz ders eklenmedi",
        aciklama: "Okutulan dersleri ve kısa adlarını (MAT, TDE, FİZ...) ekleyin.",
        dugme: "İlk dersi ekle",
        cizim: "ders",
      }}
      kaynak={dersKaynagi}
      alanlar={DERS_ALANLARI}
      girdi={(d) => ({ ad: (d.ad ?? "").trim(), kisa_ad: (d.kisa_ad ?? "").trim() })}
    />
  );
}
