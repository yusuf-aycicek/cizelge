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
import type { Ben } from "../kimlik/oturum";

export const BEN_ORNEK: Ben = {
  kullanici: { id: "k1", ad: "Ayşe Yılmaz", email: "ayse@okul.test", rol: "mudur" },
  okul: { id: "o1", ad: "Atatürk Anadolu Lisesi", gun_sayisi: 5, gunluk_ders_saati: 8 },
};

export const oturumGerekli = () => HttpResponse.json({ detail: "Oturum açmanız gerekiyor" }, { status: 401 });

export const varsayilanIsleyiciler = [
  http.get("/api/saglik", () => HttpResponse.json({ durum: "ok", veritabani: "ok", moduller: ["ders_programi"] })),
  http.get("/api/ben", () => HttpResponse.json(BEN_ORNEK)),
  http.post("/api/cikis", () => new HttpResponse(null, { status: 204 })),
];

export const sunucu = setupServer(...varsayilanIsleyiciler);

/** Bu testte kimse giriş yapmamış: /api/ben 401. */
export function oturumYok() {
  sunucu.use(http.get("/api/ben", oturumGerekli));
}
