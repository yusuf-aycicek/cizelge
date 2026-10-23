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
  /** En son program: yoksa null. */
  sonProgram?: { id: string; ad: string; durum: string } | null;
  /** En son hazır program: panodan bağlantı verilir. */
  sonHazirProgram?: { id: string; ad: string } | null;
};

export type KurulumDurumu = {
  adimlar: KurulumAdimi[];
  tamamlanan: number;
  gereken: number;
  /** 0..100, tam sayı. */
  yuzde: number;
};

const sayili = (n: number, ad: string, yoksa: string) => (n > 0 ? `${n} ${ad}` : yoksa);

/** Son adım: program. Hazır bir program varsa tamamdır; yoksa önceki adımlar bitince sıradadır. */
function programAdimi(g: KurulumGirdisi, oncekilerTamam: boolean): KurulumAdimi {
  const temel = { anahtar: "program", ad: "Programı oluştur", yol: "/program" };
  const son = g.sonProgram;
  if (son && (son.durum === "bekliyor" || son.durum === "uretiliyor")) {
    return { ...temel, durum: "bekliyor", ayrinti: "Program hazırlanıyor..." };
  }
  if (g.sonHazirProgram) {
    return { ...temel, yol: `/program/${g.sonHazirProgram.id}`, durum: "tamam", ayrinti: `Son program: ${g.sonHazirProgram.ad}` };
  }
  if (son?.durum === "basarisiz") return { ...temel, durum: "eksik", ayrinti: "Son deneme başarısız oldu; nedenini görün" };
  return { ...temel, durum: "bekliyor", ayrinti: oncekilerTamam ? "Hazırsınız: programı oluşturun" : "Önceki adımlar bitince" };
}

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
    { anahtar: "musaitlik", ad: "Öğretmen müsaitliği", yol: "/ogretmenler", durum: "istege-bagli",
      ayrinti: "İsteğe bağlı: öğretmenin adına tıklayın" },
  ];
  adimlar.push(programAdimi(g, adimlar.every((a) => a.durum === "tamam" || a.durum === "istege-bagli")));
  const gerekenler = adimlar.filter((a) => a.durum !== "istege-bagli");
  const tamamlanan = gerekenler.filter((a) => a.durum === "tamam").length;
  return {
    adimlar,
    tamamlanan,
    gereken: gerekenler.length,
    yuzde: Math.round((tamamlanan / gerekenler.length) * 100),
  };
}
