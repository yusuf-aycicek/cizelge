/**
 * Uçtan uca (5.6): örnek okulla giriş → bir öğretmene müsaitlik ("gelemez") ve boş gün hedefi →
 * program üretme → çizelgede o öğretmenin "gelemez" saatinde dersi olmadığını görme. Masaüstünde
 * tablo, telefonda gün gün liste ve dokunma (tap).
 *
 * Örnek okul geliştirme veritabanındadır (`python -m okulapi ornek-okul`). Test başlangıç durumunu
 * API'den okur, iş bitince (test kırılsa da) geri alır ve başlangıçla aynı olduğunu denetler:
 * müsaitlik ve özel ayar API'yle, üretilen program veritabanından silinir (programı silen bir
 * API ucu yok).
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";

// api/src/okulapi/ornek_okul.py: örnek okulun geliştirme hesabı.
const EPOSTA = process.env.ORNEK_EMAIL ?? "mudur@ornek.test";
const PAROLA = process.env.ORNEK_PAROLA ?? "ornek-okul-parolasi";
const GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"];
const DP = "/api/ders-programi";

type Hucre = { gun: number; saat: number; durum: string };
type Ogretmen = { id: string; ad: string };
type OzelAyar = { kapsam: { ogretmen_id: string | null }; parametreler: Record<string, number> };

async function oku<T>(istek: APIRequestContext, yol: string): Promise<T> {
  const yanit = await istek.get(yol);
  expect(yanit.ok(), `${yol}: ${yanit.status()}`).toBeTruthy();
  return (await yanit.json()) as T;
}

/** Testin dokunduğu her şeyin o anki hâli: geri almadan sonra başlangıçla aynı olmalı. */
async function durum(istek: APIRequestContext, ogretmenId: string) {
  const musaitlik = await oku<{ hucreler: Hucre[] }>(istek, `${DP}/ogretmenler/${ogretmenId}/musaitlik`);
  const kurallar = await oku<{ tur: string; ozel_ayarlar: OzelAyar[] }[]>(istek, `${DP}/kurallar`);
  const programlar = await oku<{ id: string }[]>(istek, `${DP}/programlar`);
  return {
    musaitlik: musaitlik.hucreler,
    bosGun: kurallar.find((k) => k.tur === "bos_gun")!.ozel_ayarlar.filter((o) => o.kapsam.ogretmen_id === ogretmenId),
    programlar: programlar.map((p) => p.id).sort(),
  };
}

function programlariSil(idler: string[]) {
  if (idler.length === 0) return;
  // Yerleşimler ON DELETE CASCADE ile silinir.
  const sql = `DELETE FROM program WHERE id IN (${idler.map((id) => `'${id.replace(/[^0-9a-f-]/g, "")}'`).join(", ")})`;
  const psql = spawnSync("docker", ["exec", "-i", "ders-programi-db-1", "psql", "-U", "okul_sahip", "-d", "okul", "-v", "ON_ERROR_STOP=1"],
    { input: sql, encoding: "utf-8" });
  if (psql.status !== 0) throw new Error(`Deneme programı silinemedi: ${psql.stderr}`);
}

async function bas(telefon: boolean, hedef: ReturnType<Page["getByRole"]>) {
  if (telefon) await hedef.tap();
  else await hedef.click();
}

test("örnek okul: müsaitlik ve boş gün hedefi verilir, program üretilir, çizelge görünür", async ({ page, baseURL }, bilgi) => {
  const telefon = bilgi.project.name === "telefon";
  const istek = page.request; // sayfayla aynı çerezler (oturum)
  const koken = { Origin: baseURL! };

  // 1. Giriş
  await page.goto("/giris");
  await page.getByLabel("E-posta").fill(EPOSTA);
  await page.getByLabel("Parola").fill(PAROLA);
  await bas(telefon, page.getByRole("button", { name: "Giriş yap" }));
  await expect(page.getByRole("button", { name: "Çıkış" })).toBeVisible();

  // Öğretmen: adına göre ilki. Hücre: başlangıçta müsait olan ilk saat.
  const ogretmenler = await oku<Ogretmen[]>(istek, "/api/ogretmenler");
  const hoca = [...ogretmenler].sort((a, b) => a.ad.localeCompare(b.ad, "tr"))[0]!;
  const once = await durum(istek, hoca.id);
  const dolu = new Set(once.musaitlik.map((h) => `${h.gun}-${h.saat}`));
  const secilen = Array.from({ length: 30 }, (_, i) => ({ gun: i % 5, saat: Math.floor(i / 5) })).find((h) => !dolu.has(`${h.gun}-${h.saat}`))!;
  const gunAdi = GUNLER[secilen.gun]!;
  const hucreAdi = `${gunAdi}, ${secilen.saat + 1}. saat`;

  try {
    // 2. Öğretmen sayfası: boş gün hedefi ve müsaitlik
    await page.goto("/ogretmenler");
    await bas(telefon, page.getByRole("link", { name: hoca.ad }));
    await expect(page.getByRole("heading", { name: hoca.ad })).toBeVisible();
    await page.getByLabel("Boş gün hedefi").selectOption("2");
    await expect(page.getByText("özel", { exact: true })).toBeVisible();

    await bas(telefon, page.getByRole("button", { name: `${hucreAdi}: müsait` }));
    await expect(page.getByRole("button", { name: `${hucreAdi}: gelemez` })).toBeVisible();
    await expect.poll(async () => (await durum(istek, hoca.id)).musaitlik.find((h) => h.gun === secilen.gun && h.saat === secilen.saat)?.durum)
      .toBe("gelemez");
    expect((await durum(istek, hoca.id)).bosGun.map((o) => o.parametreler)).toEqual([{ hedef_bos_gun: 2 }]);

    // 3. Program üretme ("Hızlı")
    await page.goto("/program");
    await page.getByLabel("Programın adı").fill(`Uçtan uca ${bilgi.project.name}`);
    await page.getByRole("radio", { name: /Hızlı/ }).check();
    await bas(telefon, page.getByRole("button", { name: "Programı oluştur" }));
    const ac = page.getByRole("link", { name: "Haftalık çizelgeyi aç" }).first();
    await expect(ac).toBeVisible({ timeout: 150_000 });
    await bas(telefon, ac);
    await expect(page).toHaveURL(/\/program\/[0-9a-f-]+/);

    // 4. Çizelge: öğretmen görünümünde "gelemez" saati boş
    await bas(telefon, page.getByRole("tab", { name: "Öğretmene göre" }));
    await page.getByLabel("Öğretmen", { exact: true }).selectOption({ label: hoca.ad });
    await expect(page.getByText(/^\d+ ders saati$/)).not.toHaveText("0 ders saati");
    const saatMetni = new RegExp(`^${secilen.saat + 1}\\. saat`);
    if (telefon) {
      await expect(page.getByRole("table")).toHaveCount(0);
      await page.getByRole("group", { name: "Gün" }).getByRole("button", { name: gunAdi }).tap();
      const liste = page.getByRole("list", { name: `${hoca.ad} haftalık programı, ${gunAdi}` });
      await expect(liste.getByRole("listitem").filter({ hasText: saatMetni })).toContainText("Boş");
    } else {
      const tablo = page.getByRole("table", { name: `${hoca.ad} haftalık programı` });
      await expect(tablo).toBeVisible();
      const sutun = GUNLER.indexOf(gunAdi);
      const satir = tablo.getByRole("row").filter({ has: page.getByRole("rowheader", { name: saatMetni }) });
      await expect(satir.getByRole("cell").nth(sutun)).toContainText("Boş");
    }
  } finally {
    // Geri alma: test kırılsa da çalışır.
    await istek.put(`${DP}/ogretmenler/${hoca.id}/musaitlik`, {
      headers: koken, data: { degisiklikler: [{ ...secilen, durum: "musait" }] },
    });
    const ilk = once.bosGun[0];
    if (ilk) await istek.put(`${DP}/kurallar/bos_gun/ozel`, { headers: koken, data: { kapsam: ilk.kapsam, parametreler: ilk.parametreler } });
    else await istek.delete(`${DP}/kurallar/bos_gun/ozel?ogretmen_id=${hoca.id}`, { headers: koken });
    const simdi = await durum(istek, hoca.id);
    programlariSil(simdi.programlar.filter((id) => !once.programlar.includes(id)));
  }
  expect(await durum(istek, hoca.id)).toEqual(once);
});
