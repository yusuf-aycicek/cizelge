/**
 * Okulun haftası: günlere göre ders saati, öğle arası ve zil saatleri. Saf fonksiyonlar; okul
 * ayarları ekranı (önizleme), haftalık çizelge ve müsaitlik çizelgesi bunları paylaşır.
 *
 * Zil saatleri yalnızca gösterimdir: sunucu saklar ama hesaplamaz (çözücü saatleri sırayla bilir).
 */
import type { components } from "../api/sema";

type Okul = components["schemas"]["OkulYanit"];

/** Zamanla ilgili okul alanları (ayar ekranındaki taslak da aynı biçimde). */
export type Hafta = Pick<
  Okul,
  "gun_saatleri" | "ogle_arasi_sonra" | "ilk_ders_baslangic" | "ders_suresi_dk" | "teneffus_dk" | "ogle_arasi_dk"
>;

export type ZilSaati = { baslangic: string; bitis: string };

/** Bu hücre okulun haftasında var mı (kısa günün sonundaki saatler yoktur). */
export const saatVar = (gunSaatleri: readonly number[], gun: number, saat: number) =>
  saat < (gunSaatleri[gun] ?? 0);

/** `saat` (0'dan) ile bir sonraki ders arasında öğle arası var mı (en uzun güne göre; satır ayracı). */
export const ogleArasiSonrasi = (ogleArasiSonra: number | null | undefined, saat: number) =>
  ogleArasiSonra != null && saat + 1 === ogleArasiSonra;

function dakika(metin: string): number | null {
  const m = /^(\d{1,2}):(\d{2})/.exec(metin);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

const biçim = (dk: number) =>
  `${String(Math.floor(dk / 60) % 24).padStart(2, "0")}:${String(dk % 60).padStart(2, "0")}`;

/**
 * Her ders saatinin başlangıç ve bitişi; zil saatleri tanımsızsa null. Ders aralarında teneffüs,
 * öğle arasından sonra öğle arası süresi kadar beklenir. Kısa günler aynı saatlerle erken biter.
 */
export function zilSaatleri(hafta: Hafta, saatSayisi: number): ZilSaati[] | null {
  const ilk = hafta.ilk_ders_baslangic ? dakika(hafta.ilk_ders_baslangic) : null;
  if (ilk === null) return null;
  const sonuc: ZilSaati[] = [];
  let simdi = ilk;
  for (let s = 0; s < saatSayisi; s++) {
    sonuc.push({ baslangic: biçim(simdi), bitis: biçim(simdi + hafta.ders_suresi_dk) });
    simdi += hafta.ders_suresi_dk + (ogleArasiSonrasi(hafta.ogle_arasi_sonra, s) ? hafta.ogle_arasi_dk : hafta.teneffus_dk);
  }
  return sonuc;
}

/** "08:30–09:10" (kısa çizgi: aralık). */
export const zilMetni = (z: ZilSaati) => `${z.baslangic}–${z.bitis}`;

/** Öğle arasının saatleri ("12:10–12:50"); öğle arası ya da zil saatleri yoksa null. */
export function ogleArasiZili(hafta: Hafta, zil: readonly ZilSaati[] | null): ZilSaati | null {
  const n = hafta.ogle_arasi_sonra;
  if (!zil || n == null || !zil[n - 1]) return null;
  const bitis = dakika(zil[n - 1]!.bitis)!;
  return { baslangic: zil[n - 1]!.bitis, bitis: biçim(bitis + hafta.ogle_arasi_dk) };
}

/** Yeni haftada eski haftanın bir hücresi kayboluyor mu (bir gün kısalıyor ya da gün azalıyor)? */
export function kisaliyor(eski: readonly number[], yeni: readonly number[]): boolean {
  return eski.some((s, g) => s > (yeni[g] ?? 0));
}
