/** Öğretmen, sınıf ve ders sayfaları: ortak liste bileşeninin üç kullanımı. */
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
      baslik="Öğretmenler"
      aciklama="Okulunuzdaki öğretmenler. Hangi derse kimin gireceğini Ders dağılımı sayfasında seçeceksiniz."
      tekil="Öğretmen"
      bos={{
        baslik: "Henüz öğretmen eklenmedi",
        aciklama: "Ders dağılımı yapabilmek için önce öğretmenlerinizi ekleyin. Aşağıdaki formla ardı ardına hızlıca girebilirsiniz.",
        dugme: "İlk öğretmeni ekle",
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
      baslik="Sınıflar"
      aciklama="Okulunuzdaki şubeler. Seviye, seviye şablonunu aynı seviyedeki bütün şubelere uygulamak için kullanılır."
      tekil="Sınıf"
      bos={{
        baslik: "Henüz sınıf eklenmedi",
        aciklama: "Şubelerinizi (9-A, 9-B, 10-A...) ve seviyelerini ekleyin.",
        dugme: "İlk sınıfı ekle",
      }}
      kaynak={sinifKaynagi}
      alanlar={SINIF_ALANLARI}
      girdi={(d) => ({ ad: (d.ad ?? "").trim(), seviye: Number(d.seviye) })}
    />
  );
}

export function DerslerSayfasi() {
  return (
    <ListeSayfasi<Ders, { ad: string; kisa_ad: string }>
      baslik="Dersler"
      aciklama="Okulunuzda okutulan dersler. Kısa ad, haftalık çizelgede derse yer açmak için kullanılır."
      tekil="Ders"
      bos={{
        baslik: "Henüz ders eklenmedi",
        aciklama: "Okutulan dersleri ve kısa adlarını (MAT, TDE, FİZ...) ekleyin.",
        dugme: "İlk dersi ekle",
      }}
      kaynak={dersKaynagi}
      alanlar={DERS_ALANLARI}
      girdi={(d) => ({ ad: (d.ad ?? "").trim(), kisa_ad: (d.kisa_ad ?? "").trim() })}
    />
  );
}
