/**
 * API istemcisi. Tipler (`paths`) API'nin OpenAPI şemasından üretilir (`npm run api:tipler`):
 * API'de bir yol ya da alan değişirse arayüz derlenmez, hata kullanıcıda değil derlemede görünür.
 *
 *     const yanit = await cagir(api.GET("/api/saglik"));   // yanit'in tipi şemadan gelir
 *
 * Adres göreli: arayüz ile API tarayıcıya aynı kökenden görünür (ADR 0013). Geliştirmede Vite,
 * /api isteklerini API'ye iletir. Çerez (oturum) tarayıcı tarafından kendiliğinden eklenir.
 */
import createClient from "openapi-fetch";
import type { paths } from "./sema";
import { izle } from "./uyanma";

export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? "",
  credentials: "same-origin",
  // fetch her çağrıda yeniden okunur: testlerde sahte sunucu (MSW) fetch'i sonradan sarar.
  // izle: uzun süren istekte "sunucu uyanıyor" bildirimi (uyanma.ts).
  fetch: (istek: Request) => izle(globalThis.fetch(istek)),
});
