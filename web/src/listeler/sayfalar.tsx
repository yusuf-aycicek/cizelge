/** Öğretmen, sınıf ve ders sayfaları: ortak liste bileşeninin üç kullanımı. */
import { OgretmenAdi } from "../bilesenler/OgretmenRozeti";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, GraduationCap, School } from "lucide-react";
import { hataMetni } from "../api/hata";
import { useBildirim } from "../bilesenler/Bildirim";
import { DersCipi } from "../dersler/DersCipi";
import { RenkSecici } from "../dersler/RenkSecici";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi, type Ders, type Ogretmen, type Sinif } from "./kaynaklar";
import { ListeSayfasi, type ListeAlani } from "./ListeSayfasi";

// Alan listeleri bileşenin dışında sabit: her çizimde yeni dizi oluşmasın (useMemo bağımlılığı).
const OGRETMEN_ALANLARI: ListeAlani[] = [
  { ad: "ad", etiket: "Adı soyadı", gerekli: true, ornek: "Ayşe Yılmaz" },
  { ad: "brans", etiket: "Branşı", ornek: "Matematik" },
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
      gorunum={(alan, o) => (alan === "ad" ? <OgretmenAdi id={o.id} ad={o.ad} /> : undefined)}
      ikon={GraduationCap}
      baslik="Öğretmenler"
      aciklama="Okulunuzdaki öğretmenler. Hangi derse kimin gireceğini Ders dağılımı sayfasında seçeceksiniz."
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
  return (
    <ListeSayfasi<Sinif, { ad: string; seviye: number }>
      ikon={School}
      baslik="Sınıflar"
      aciklama="Okulunuzdaki şubeler. Seviye, seviye şablonunu aynı seviyedeki bütün şubelere uygulamak için kullanılır."
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
      gorunum={(alan, ders) => (alan === "ad" ? <DersCipi ad={ders.ad} renk={ders.renk} /> : undefined)}
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
      ]}
      ikon={BookOpen}
      baslik="Dersler"
      aciklama="Okulunuzda okutulan dersler. Her derse otomatik bir renk verilir; dersin her ekranda aynı renkte görünür, isterseniz değiştirebilirsiniz."
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
