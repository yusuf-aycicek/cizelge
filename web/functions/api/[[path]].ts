/**
 * Cloudflare Pages Function: /api/* isteklerini API'ye (Render) iletir (ADR 0026).
 *
 * Tarayıcı arayüzü ve API'yi aynı adresten (ör. https://cizelge.pages.dev) görür. Bu sayede
 * oturum çerezi SameSite=Strict kalır, CORS gerekmez (ADR 0013); geliştirmedeki Vite proxy'sinin
 * yayındaki karşılığıdır. Dosya adı `[[path]]`: /api altındaki bütün yolları yakalar.
 *
 * API'nin adresi Pages ortam değişkeninden gelir: API_KOKENI=https://<servis>.onrender.com
 * İstek olduğu gibi (yöntem, gövde, başlıklar: Cookie ve Origin dahil) iletilir; yanıt da olduğu
 * gibi döner (Set-Cookie dahil). Çerezde Domain olmadığı için tarayıcı onu Pages adresine yazar.
 */

interface Ortam {
  API_KOKENI?: string;
}

export const onRequest = async ({ request, env }: { request: Request; env: Ortam }): Promise<Response> => {
  if (!env.API_KOKENI) {
    return Response.json({ detail: "Sunucu ayarı eksik (API_KOKENI)" }, { status: 500 });
  }
  const gelen = new URL(request.url);
  const hedef = new URL(gelen.pathname + gelen.search, env.API_KOKENI);
  // Yönlendirmeler izlenmez, olduğu gibi tarayıcıya iletilir (geliştirmedeki Vite proxy'si gibi).
  return fetch(new Request(hedef, request), { redirect: "manual" });
};
