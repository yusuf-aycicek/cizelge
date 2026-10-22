/**
 * Kurulum durumu: ana sayfanın kontrol listesi ve ilerleme halkası bu tek fonksiyondan beslenir,
 * ikisi birbiriyle çelişemez. Saf fonksiyon: sunucu verisinin sayılarını alır, adımları döner.
 *
 * Program üretebilmek için gereken adımlar sayılır. Öğretmen müsaitliği isteğe bağlıdır: listede
 * görünür ama ilerlemeye katılmaz (hiç girilmese de program üretilebilir).
 */

export type AdimDurumu = "tamam" | "eksik" | "bekliyor" | "istege-bagli";

export type KurulumAdimi = {
  anahtar: string;
  ad: string;
  /** Kısa durum metni: "5 öğretmen", "3 dersin öğretmeni seçilmedi". */
  ayrinti: string;
  durum: AdimDurumu;
  yol: string;
};

export type KurulumGirdisi = {
  gunSayisi: number;
  gunlukDersSaati: number;
  ogretmen: number;
  sinif: number;
  ders: number;
  atama: number;
  /** Öğretmeni seçilmemiş atama sayısı (sunucunun dağılım özetinden). */
  ogretmensizAtama: number;
};

export type KurulumDurumu = {
  adimlar: KurulumAdimi[];
  tamamlanan: number;
  gereken: number;
  /** 0..100, tam sayı. */
  yuzde: number;
};

const sayili = (n: number, ad: string, yoksa: string) => (n > 0 ? `${n} ${ad}` : yoksa);

export function kurulumDurumu(g: KurulumGirdisi): KurulumDurumu {
  const dagilim: Pick<KurulumAdimi, "ayrinti" | "durum"> =
    g.atama === 0
      ? { ayrinti: "Henüz ders atanmadı", durum: "bekliyor" }
      : g.ogretmensizAtama > 0
        ? { ayrinti: `${g.ogretmensizAtama} dersin öğretmeni seçilmedi`, durum: "eksik" }
        : { ayrinti: `${g.atama} ders ataması, hepsinin öğretmeni seçildi`, durum: "tamam" };

  const adimlar: KurulumAdimi[] = [
    { anahtar: "okul", ad: "Okul ayarları", yol: "/okul", durum: "tamam",
      ayrinti: `${g.gunSayisi} gün, günde ${g.gunlukDersSaati} ders` },
    { anahtar: "ogretmen", ad: "Öğretmenler", yol: "/ogretmenler", durum: g.ogretmen > 0 ? "tamam" : "bekliyor",
      ayrinti: sayili(g.ogretmen, "öğretmen", "Henüz öğretmen yok") },
    { anahtar: "sinif", ad: "Sınıflar", yol: "/siniflar", durum: g.sinif > 0 ? "tamam" : "bekliyor",
      ayrinti: sayili(g.sinif, "şube", "Henüz şube yok") },
    { anahtar: "ders", ad: "Dersler", yol: "/dersler", durum: g.ders > 0 ? "tamam" : "bekliyor",
      ayrinti: sayili(g.ders, "ders", "Henüz ders yok") },
    { anahtar: "dagilim", ad: "Ders dağılımı", yol: "/ders-dagilimi", ...dagilim },
    { anahtar: "musaitlik", ad: "Öğretmen müsaitliği", yol: "/musaitlik", durum: "istege-bagli",
      ayrinti: "İsteğe bağlı" },
  ];
  const gerekenler = adimlar.filter((a) => a.durum !== "istege-bagli");
  const tamamlanan = gerekenler.filter((a) => a.durum === "tamam").length;
  return {
    adimlar,
    tamamlanan,
    gereken: gerekenler.length,
    yuzde: Math.round((tamamlanan / gerekenler.length) * 100),
  };
}
