/**
 * Sahte API (MSW, Mock Service Worker). Bileşenler gerçek `fetch` yapar; MSW isteği ağ
 * düzeyinde yakalayıp burada tanımlanan yanıtı verir. Testler kendi durumlarını
 * `sunucu.use(...)` ile ekler (ör. 409, 503, bağlantı hatası).
 *
 * Varsayılan: giriş yapılmış bir müdür (çoğu test sayfaların kendisini sınar). Girişsiz durum
 * için `oturumYok()`.
 */
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import type { components } from "../api/sema";
import type { Ben } from "../kimlik/oturum";

export const BEN_ORNEK: Ben = {
  kullanici: { id: "k1", ad: "Ayşe Yılmaz", email: "ayse@okul.test", rol: "mudur" },
  okul: { id: "o1", ad: "Atatürk Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
};

type Kural = components["schemas"]["KuralYanit"];

/** API'nin varsayılan kuralları (moduller/ders_programi/kurallar.py ile aynı). */
export const ORNEK_KURALLAR: Kural[] = [
  sayili("gunluk_ders_siniri", "Aynı dersin günlük sınırı", "Aynı ders bir sınıfa günde en fazla bu kadar saat konur.", "n", 2),
  sayili("ogretmen_gunluk_siniri", "Öğretmenin günlük ders sınırı", "Bir öğretmen günde en fazla bu kadar saat derse girer.", "m", 8),
  esnek("sinif_boslugu", "Sınıfların boş saati olmasın", 30),
  esnek("degisiklik", "Mevcut programa bağlılık", 8),
  esnek("tercih_etmez", "Öğretmenin tercih etmediği saatler", 5),
  { ...esnek("bos_gun", "Öğretmene boş gün", 4), parametreler: { hedef_bos_gun: 1 }, varsayilan_parametreler: { hedef_bos_gun: 1 } },
  esnek("ogretmen_penceresi", "Öğretmenin boş (pencere) saatleri", 3),
  esnek("ardisik_ders", "Bir dersin saatleri arka arkaya", 2),
];

function sayili(tur: string, ad: string, aciklama: string, p: string, v: number): Kural {
  return { tur, ad, aciklama, zorunlu: true, parametreler: { [p]: v }, varsayilan_parametreler: { [p]: v },
    agirlik: null, seviye: null, varsayilan_seviye: null, varsayilan: true };
}

function esnek(tur: string, ad: string, agirlik: number): Kural {
  return { tur, ad, aciklama: `${ad} açıklaması.`, zorunlu: false, parametreler: {}, varsayilan_parametreler: {},
    agirlik, seviye: "onemli", varsayilan_seviye: "onemli", varsayilan: true };
}

/** API'nin paletinin başı (cekirdek/ders_renkleri.py ile aynı sırada). */
export const ORNEK_DERS_RENKLERI = [
  { renk: "#1d4ed8", ad: "Lacivert" },
  { renk: "#c2410c", ad: "Kiremit" },
  { renk: "#15803d", ad: "Yeşil" },
  { renk: "#7e22ce", ad: "Mor" },
];

export const oturumGerekli = () => HttpResponse.json({ detail: "Oturum açmanız gerekiyor" }, { status: 401 });

export const varsayilanIsleyiciler = [
  http.get("/api/saglik", () => HttpResponse.json({ durum: "ok", veritabani: "ok", moduller: ["ders_programi"] })),
  http.get("/api/ben", () => HttpResponse.json(BEN_ORNEK)),
  http.post("/api/cikis", () => new HttpResponse(null, { status: 204 })),
  http.get("/api/okul", () => HttpResponse.json(BEN_ORNEK.okul)),
  http.get("/api/ders-programi/kurallar", () => HttpResponse.json(ORNEK_KURALLAR)),
  http.get("/api/ogretmenler", () => HttpResponse.json([])),
  http.get("/api/siniflar", () => HttpResponse.json([])),
  http.get("/api/dersler", () => HttpResponse.json([])),
  http.get("/api/ders-renkleri", () => HttpResponse.json(ORNEK_DERS_RENKLERI)),
  http.get("/api/ders-programi/atamalar", () => HttpResponse.json([])),
  http.get("/api/ders-programi/programlar", () => HttpResponse.json([])),
  http.get("/api/ders-programi/seviye-sablonlari", () => HttpResponse.json([])),
  http.get("/api/ders-programi/dagilim-ozeti", () =>
    HttpResponse.json({ haftalik_kapasite: 40, ogretmen_gunluk_siniri: 8, ogretmensiz_atama: 0, ogretmenler: [], siniflar: [] }),
  ),
];

export const sunucu = setupServer(...varsayilanIsleyiciler);

/** Bu testte kimse giriş yapmamış: /api/ben 401. */
export function oturumYok() {
  sunucu.use(http.get("/api/ben", oturumGerekli));
}
