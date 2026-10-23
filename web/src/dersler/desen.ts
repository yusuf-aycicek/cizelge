/**
 * Dağılım şekli (blok dersler): "2+2+1" metni ile blok listesi arasında çeviri, hazır seçenekler.
 * Saf fonksiyonlar. Hangi şeklin uygulanacağı sunucuda hesaplanır (`cozucu.blok`); burada yalnızca
 * gösterim ve seçim var. Kurallar sunucudakiyle aynı: her blok 1-8 saat, büyükten küçüğe yazılır.
 */

export const EN_BUYUK_BLOK = 8;

/** Sunucunun hesapladığı dağılım şekilleri (`/dagilim-sekilleri`) için önbellek anahtarı. */
export const SEKILLER_ANAHTARI = ["dagilim-sekilleri"] as const;

/** Sunucudaki önerinin aynısı: olabildiğince 2'li, tek saat kalırsa sonda 1 (5 → 2+2+1). */
export function otomatikDesen(saat: number): number[] {
  return [...Array<number>(Math.floor(saat / 2)).fill(2), ...Array<number>(saat % 2).fill(1)];
}

/** "2+2+1"; boş liste "blok yok". */
export const desenMetni = (desen: readonly number[]) => (desen.length ? desen.join("+") : "blok yok");

/**
 * Kullanıcının yazdığı şekli okur: "2+2+1", "2 + 1 + 2" (sıralanır), "blok yok" ya da boş → [].
 * Geçersizse null.
 */
export function desenOku(metin: string): number[] | null {
  const temiz = metin.trim().toLocaleLowerCase("tr");
  if (temiz === "" || temiz === "blok yok") return [];
  if (!/^\d+(\s*\+\s*\d+)*$/.test(temiz)) return null;
  const bloklar = temiz.split("+").map((p) => Number(p.trim()));
  if (bloklar.some((b) => b < 1 || b > EN_BUYUK_BLOK)) return null;
  return bloklar.sort((a, b) => b - a);
}

/**
 * Hazır seçenekler: `saat`in en çok `enBuyuk` saatlik bloklara ve en çok `enCok` bloğa bölünüşleri,
 * büyük bloklu olanlar önce ("3+2", "2+2+1", "2+1+1+1"...). Sayı küçük olduğu için hepsi üretilir.
 */
export function bolunusler(saat: number, enBuyuk: number, enCok: number): number[][] {
  const sonuc: number[][] = [];
  const yuru = (kalan: number, ust: number, parca: number[]) => {
    if (parca.length > enCok) return;
    if (kalan === 0) {
      sonuc.push(parca);
      return;
    }
    for (let b = Math.min(ust, kalan); b >= 1; b--) yuru(kalan - b, b, [...parca, b]);
  };
  yuru(saat, Math.min(enBuyuk, EN_BUYUK_BLOK), []);
  return sonuc;
}

export const ayniDesen = (a: readonly number[], b: readonly number[]) =>
  a.length === b.length && a.every((x, i) => x === b[i]);
