/**
 * Okulun haftası: günlere göre ders saati, öğle arası ve zil saatleri. Saf fonksiyonlar; okul
 * ayarları ekranı (önizleme), haftalık çizelge ve müsaitlik çizelgesi bunları paylaşır.
 *
 * Zil saatleri yalnızca gösterimdir ve sunucuda hesaplanır (tek kaynak: api cekirdek/zil.py); okul
 * yanıtındaki `zil_saatleri` ve `ogle_arasi_zili` alanlarından okunur. Çıktılar (PDF, Excel) da aynı
 * hesabı kullanır.
 */
import type { components } from "../api/sema";

type Okul = components["schemas"]["OkulYanit"];

/** Zamanla ilgili okul alanları (ayar ekranındaki taslak da aynı biçimde). */
export type Hafta = Pick<
  Okul,
  "gun_saatleri" | "ogle_arasi_sonra" | "zil_saatleri" | "ogle_arasi_zili"
>;

export type ZilSaati = components["schemas"]["ZilSaati"];

/** Bu hücre okulun haftasında var mı (kısa günün sonundaki saatler yoktur). */
export const saatVar = (gunSaatleri: readonly number[], gun: number, saat: number) =>
  saat < (gunSaatleri[gun] ?? 0);

/** `saat` (0'dan) ile bir sonraki ders arasında öğle arası var mı (en uzun güne göre; satır ayracı). */
export const ogleArasiSonrasi = (ogleArasiSonra: number | null | undefined, saat: number) =>
  ogleArasiSonra != null && saat + 1 === ogleArasiSonra;

/** "08:30–09:10" (kısa çizgi: aralık). */
export const zilMetni = (z: ZilSaati) => `${z.baslangic}–${z.bitis}`;

/** Yeni haftada eski haftanın bir hücresi kayboluyor mu (bir gün kısalıyor ya da gün azalıyor)? */
export function kisaliyor(eski: readonly number[], yeni: readonly number[]): boolean {
  return eski.some((s, g) => s > (yeni[g] ?? 0));
}
