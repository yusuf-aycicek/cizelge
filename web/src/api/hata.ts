/**
 * API hatalarının arayüzdeki tek temsili (docs/arayuz-plani.md bölüm 2.9).
 *
 * Sunucunun iki hata biçimi vardır, ikisi de `detail` alanında Türkçe bir metin taşır:
 * - servis hataları: `{"detail": "Bu e-posta adresi başka bir hesapta kullanılıyor"}`;
 * - doğrulama hataları: `{"detail": "Bazı alanlar hatalı", "alanlar": {"email": "..."}}`.
 *
 * Bağlantı kopması, vekil sunucu hatası (502/504) ya da metinsiz bir yanıt da burada anlaşılır bir
 * Türkçe mesaja çevrilir. Arayüzün geri kalanı yalnızca `ApiHatasi` görür; "Hata 422" asla görünmez.
 */

export type AlanHatalari = Record<string, string>;

export class ApiHatasi extends Error {
  /** HTTP durum kodu; bağlantı hiç kurulamadıysa 0. */
  readonly durum: number;
  /** Alan yolu -> mesaj, ör. {"okul.ad": "Boş bırakılamaz"}. */
  readonly alanlar: AlanHatalari;
  /** Sunucunun ham yanıt gövdesi: bazı uçlar ek bilgi taşır (ör. 409'da `etkiler` listesi). */
  readonly govde: unknown;

  constructor(durum: number, mesaj: string, alanlar: AlanHatalari = {}, govde: unknown = undefined) {
    super(mesaj);
    this.name = "ApiHatasi";
    this.durum = durum;
    this.alanlar = alanlar;
    this.govde = govde;
  }

  get baglantiHatasi(): boolean {
    return this.durum === 0 || this.durum === 502 || this.durum === 504;
  }
}

export const BAGLANTI_HATASI = "Sunucuya ulaşılamıyor. Bağlantınızı kontrol edip biraz sonra yeniden deneyin.";

const DURUM_MESAJLARI: Record<number, string> = {
  400: "İstek anlaşılamadı.",
  401: "Oturum açmanız gerekiyor.",
  403: "Bu işlem için yetkiniz yok.",
  404: "Aradığınız kayıt bulunamadı.",
  409: "Bu işlem mevcut kayıtlarla çakışıyor.",
  422: "Bazı alanlar hatalı.",
  429: "Çok fazla deneme yapıldı. Biraz sonra yeniden deneyin.",
};

function nesneMi(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

/** Sunucunun yanıt gövdesinden (hata durumunda) `ApiHatasi` üretir. */
export function govdedenHata(durum: number, govde: unknown): ApiHatasi {
  if (nesneMi(govde) && typeof govde.detail === "string") {
    const alanlar: AlanHatalari = {};
    if (nesneMi(govde.alanlar)) {
      for (const [yol, mesaj] of Object.entries(govde.alanlar)) {
        if (typeof mesaj === "string") alanlar[yol] = mesaj;
      }
    }
    return new ApiHatasi(durum, govde.detail, alanlar, govde);
  }
  if (durum === 502 || durum === 503 || durum === 504) {
    return new ApiHatasi(durum, BAGLANTI_HATASI);
  }
  const mesaj =
    DURUM_MESAJLARI[durum] ??
    (durum >= 500 ? "Sunucuda beklenmeyen bir hata oluştu. Biraz sonra yeniden deneyin." : "İstek tamamlanamadı.");
  return new ApiHatasi(durum, mesaj);
}

/** openapi-fetch çağrısının sonucu: başarılıysa `data`, değilse `error` ve her durumda `response`. */
type CagriSonucu<T> = { data?: T; error?: unknown; response: Response };

/**
 * Bir API çağrısını bekler; başarılıysa veriyi döner, değilse `ApiHatasi` fırlatır.
 *
 *     const okul = await cagir(api.GET("/api/okul"));
 *
 * TanStack Query hatayı yakalar ve bileşene `error` olarak verir.
 */
export async function cagir<T>(istek: Promise<CagriSonucu<T>>): Promise<T> {
  let sonuc: CagriSonucu<T>;
  try {
    sonuc = await istek;
  } catch {
    // fetch, sunucuya hiç ulaşamazsa (ağ yok, sunucu kapalı) istisna fırlatır.
    throw new ApiHatasi(0, BAGLANTI_HATASI);
  }
  if (!sonuc.response.ok) {
    throw govdedenHata(sonuc.response.status, sonuc.error);
  }
  return sonuc.data as T;
}

/** Herhangi bir hatadan kullanıcıya gösterilecek metin. */
export function hataMetni(hata: unknown): string {
  if (hata instanceof ApiHatasi) return hata.message;
  return "Beklenmeyen bir hata oluştu. Sayfayı yenileyip yeniden deneyin.";
}
