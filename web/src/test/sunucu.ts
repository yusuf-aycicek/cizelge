/**
 * Sahte API (MSW, Mock Service Worker). Bileşenler gerçek `fetch` yapar; MSW isteği ağ
 * düzeyinde yakalayıp burada tanımlanan yanıtı verir. Testler kendi durumlarını
 * `sunucu.use(...)` ile ekler (ör. 409, 503, bağlantı hatası).
 */
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const varsayilanIsleyiciler = [
  http.get("/api/saglik", () => HttpResponse.json({ durum: "ok", veritabani: "ok", moduller: ["ders_programi"] })),
];

export const sunucu = setupServer(...varsayilanIsleyiciler);
