/**
 * Program ekranlarının saf yardımcıları: bekleme aşamaları, çelişkilerin gruplanması, kalite
 * ölçülerinin sade Türkçesi, gün adları. React'ten bağımsız; ayrı ayrı test edilir.
 */
import type { components } from "../api/sema";

export type Program = components["schemas"]["ProgramYanit"];

export const GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

export const etkinMi = (p: Pick<Program, "durum">) => p.durum === "bekliyor" || p.durum === "uretiliyor";

// --- bekleme aşamaları --------------------------------------------------------------------

export type Asama = { anahtar: string; ad: string; aciklama: string };

/**
 * Üretimin kullanıcıya gösterilen aşamaları. Sunucu yalnızca "bekliyor / üretiliyor / hazır"
 * der; "üretiliyor"un içindeki aşamalar geçen süreden çıkarılır. Çözücü önce kontrol eder, sonra
 * geçerli bir yerleşim bulur, kalan sürede onu iyileştirir; süre dolunca en iyisini kaydeder.
 */
export const ASAMALAR: Asama[] = [
  { anahtar: "sira", ad: "Sırada", aciklama: "İstek alındı, üretim birazdan başlayacak." },
  { anahtar: "kontrol", ad: "Veriler kontrol ediliyor", aciklama: "Saatler, kapasiteler ve müsaitlikler denetleniyor." },
  { anahtar: "yerlesim", ad: "Dersler yerleştiriliyor", aciklama: "Hiçbir öğretmen ve şube aynı saatte iki yerde olmayacak." },
  { anahtar: "iyilestirme", ad: "Program iyileştiriliyor", aciklama: "Boş saatler, pencereler ve tercihler için daha iyisi aranıyor." },
  { anahtar: "hazir", ad: "Hazır", aciklama: "Program kaydedildi." },
];

/** Şu anki aşamanın sırası (0..4) ve süre çubuğu için 0..1 arası ilerleme. */
export function asamaBul(
  program: Pick<Program, "durum" | "baslama" | "sure_siniri_sn">,
  simdi: number,
): { sira: number; ilerleme: number; gecenSn: number } {
  if (program.durum === "hazir") return { sira: 4, ilerleme: 1, gecenSn: 0 };
  if (program.durum !== "uretiliyor" || !program.baslama) return { sira: 0, ilerleme: 0, gecenSn: 0 };
  const gecenSn = Math.max(0, (simdi - Date.parse(program.baslama)) / 1000);
  const ilerleme = Math.min(0.97, gecenSn / program.sure_siniri_sn); // süre dolana dek tamamlanmış görünmesin
  const sira = gecenSn < 2 ? 1 : gecenSn < 8 ? 2 : 3;
  return { sira, ilerleme, gecenSn };
}

// --- çelişkiler ------------------------------------------------------------------------------

export type Celiski = { tur: string; mesaj: string; ilgili?: string[] };

const TUR_BASLIKLARI: Record<string, string> = {
  ogretmen_secilmemis: "Öğretmeni seçilmemiş dersler",
  sinif_kapasitesi: "Haftalık kapasiteyi aşan şubeler",
  ogretmen_kapasitesi: "Müsait saatinden fazla dersi olan öğretmenler",
  ders_gun_kapasitesi: "Günlere sığmayan dersler",
  sinif_musaitligi: "Öğretmenlerinin müsaitliğine sığmayan şubeler",
  kilit_celiskisi: "Kilitli hücrelerde çelişki",
  tutarsiz_veri: "Tutarsız veri",
  gecersiz_kisit: "Geçersiz kural",
  celiski: "Birbiriyle çelişen kurallar",
};

export type CeliskiGrubu = { tur: string; baslik: string; maddeler: Celiski[] };

/** Çelişkileri türüne göre, sunucunun verdiği sırayı koruyarak gruplar. */
export function celiskileriGrupla(celiskiler: readonly Celiski[]): CeliskiGrubu[] {
  const gruplar = new Map<string, CeliskiGrubu>();
  for (const c of celiskiler) {
    const grup = gruplar.get(c.tur) ?? { tur: c.tur, baslik: TUR_BASLIKLARI[c.tur] ?? "Diğer sorunlar", maddeler: [] };
    grup.maddeler.push(c);
    gruplar.set(c.tur, grup);
  }
  return [...gruplar.values()];
}

// --- kalite ----------------------------------------------------------------------------------

export type KaliteMaddesi = { anahtar: string; iyi: boolean; metin: string };

/** Programın kalite ölçüleri, sade Türkçe. Sıfır olan ölçü "iyi" olarak söylenir. */
export function kaliteMaddeleri(o: Record<string, number> | null | undefined, temelVar = false): KaliteMaddesi[] {
  if (!o) return [];
  const m = (anahtar: string, sayi: number | undefined, iyi: string, kotu: (n: number) => string): KaliteMaddesi => ({
    anahtar,
    iyi: !sayi,
    metin: sayi ? kotu(sayi) : iyi,
  });
  const maddeler = [
    m("sinif_boslugu", o.sinif_boslugu, "Şubelerde gün ortasında boş saat yok.",
      (n) => `Şubelerde gün ortasında toplam ${n} boş saat var.`),
    m("ogretmen_penceresi", o.ogretmen_penceresi, "Öğretmenlerin gün içinde boş beklediği saat (pencere) yok.",
      (n) => `Öğretmenlerin toplam ${n} pencere saati var (iki dersi arasında boş bekledikleri saat).`),
    m("eksik_bos_gun", o.eksik_bos_gun, "Bütün öğretmenler boş gün hedefine ulaştı.",
      (n) => `Öğretmenler boş gün hedefinden toplam ${n} gün eksik kaldı.`),
    m("tercih_etmez", o.tercih_etmez, "Hiçbir ders öğretmenin \"tercih etmem\" dediği saate konmadı.",
      (n) => `${n} ders saati öğretmenin "tercih etmem" dediği saate kondu.`),
    m("bolunmus_ders", o.bolunmus_ders, "Aynı gündeki ders saatleri hep arka arkaya.",
      (n) => `Aynı gündeki ders saatleri ${n} yerde arka arkaya değil.`),
  ];
  if (temelVar) {
    maddeler.push(m("degisen_yerlesim", o.degisen_yerlesim, "Temel programdan hiçbir hücre değişmedi.",
      (n) => `Temel programa göre ${n} hücre değişti.`));
  }
  return maddeler;
}

/** "1 saniyeden kısa", "12 saniye", "2 dakika 5 saniye". */
export function sureMetni(sn: number): string {
  if (sn < 1) return "1 saniyeden kısa";
  const yuvarlak = Math.round(sn);
  if (yuvarlak < 60) return `${yuvarlak} saniye`;
  const dk = Math.floor(yuvarlak / 60);
  const kalan = yuvarlak % 60;
  return kalan ? `${dk} dakika ${kalan} saniye` : `${dk} dakika`;
}

/** Çözücünün sonucunu sade dille söyler. */
export function cozumAciklamasi(cozumDurumu: string | null | undefined): string {
  if (cozumDurumu === "optimal") return "Bu kurallarla bulunabilecek en iyi program (kanıtlandı).";
  if (cozumDurumu === "uygun") return "Süre sınırı dolduğunda bulunan en iyi program. Daha uzun süre daha iyisini bulabilir.";
  return "";
}
