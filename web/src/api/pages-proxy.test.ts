// @vitest-environment node
// Pages Function (functions/api) testi burada: functions/ altındaki her dosyayı Cloudflare bir yol sayar.
import { afterEach, describe, expect, it, vi } from "vitest";
import { onRequest } from "../../functions/api/[[path]]";

afterEach(() => vi.unstubAllGlobals());

describe("Pages Function /api proxy'si", () => {
  it("isteği yolu, sorgusu, yöntemi, gövdesi ve başlıklarıyla API'ye iletir, yanıtı olduğu gibi döner", async () => {
    const giden: Request[] = [];
    vi.stubGlobal("fetch", async (istek: Request) => {
      giden.push(istek);
      return new Response("{}", { status: 201, headers: { "Set-Cookie": "oturum=j; Path=/api" } });
    });
    const istek = new Request("https://cizelge.pages.dev/api/ogretmenler?sira=ad", {
      method: "POST",
      body: JSON.stringify({ ad: "Ayşe" }),
      headers: { Cookie: "oturum=eski", Origin: "https://cizelge.pages.dev", "Content-Type": "application/json" },
    });

    const yanit = await onRequest({ request: istek, env: { API_KOKENI: "https://cizelge-api.onrender.com" } });

    expect(yanit.status).toBe(201);
    expect(yanit.headers.get("Set-Cookie")).toBe("oturum=j; Path=/api");
    const [iletilen] = giden;
    expect(iletilen?.url).toBe("https://cizelge-api.onrender.com/api/ogretmenler?sira=ad");
    expect(iletilen?.method).toBe("POST");
    expect(iletilen?.headers.get("Cookie")).toBe("oturum=eski");
    expect(iletilen?.headers.get("Origin")).toBe("https://cizelge.pages.dev");
    expect(await iletilen?.json()).toEqual({ ad: "Ayşe" });
  });

  it("API adresi ayarlanmamışsa anlaşılır bir hata döner", async () => {
    const yanit = await onRequest({ request: new Request("https://cizelge.pages.dev/api/saglik"), env: {} });
    expect(yanit.status).toBe(500);
    expect(await yanit.json()).toEqual({ detail: "Sunucu ayarı eksik (API_KOKENI)" });
  });
});
