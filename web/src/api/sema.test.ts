/**
 * API tipleri güncel mi? `src/api/sema.d.ts`, `openapi.json`'dan üretilmiş olmalı.
 * (`openapi.json`'un API ile aynı olduğunu da api/tests/test_openapi_guncel.py denetler.)
 * İkisi birlikte: API değişip tipler yenilenmezse bir test kırılır.
 *
 * Yollar web/ klasörüne göredir (vitest orada çalışır).
 *
 * Yenilemek için: api/.venv/Scripts/python scripts/openapi_yaz.py && npm run api:tipler
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import openapiTS, { astToString } from "openapi-typescript";
import { expect, it } from "vitest";

it("sema.d.ts, openapi.json'dan üretilmiş", async () => {
  const sema = JSON.parse(readFileSync(resolve("openapi.json"), "utf-8"));
  const uretilen = astToString(await openapiTS(sema));
  const kayitli = readFileSync(resolve("src/api/sema.d.ts"), "utf-8");
  // Üretecin başına eklediği açıklama satırları karşılaştırılmaz.
  const govde = (metin: string) => metin.replace(/^\/\*\*[\s\S]*?\*\/\s*/, "").replace(/\r\n/g, "\n").trim();
  expect(govde(kayitli)).toBe(govde(uretilen));
});
