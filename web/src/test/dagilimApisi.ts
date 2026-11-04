/**
 * Ders dağılımı ve seviye şablonu testleri için bellekte tutan sahte API.
 *
 * Yük özeti (`dagilim-ozeti`) burada **hesaplanmaz**: test, sunucunun ne diyeceğini `ozet`
 * nesnesine kendisi yazar. Hesabın doğruluğu çözücü ve API testlerinin işidir (ADR 0015); arayüz
 * testleri yalnızca sunucunun söylediğinin doğru gösterildiğini sınar.
 */
import { http, HttpResponse } from "msw";
import type { components } from "../api/sema";
import { sunucu } from "./sunucu";

type Sema = components["schemas"];
type Atama = Sema["DersAtamaYanit"];
type SablonSatiri = Sema["SeviyeSablonuYanit"];

export const OGRETMENLER: Sema["OgretmenYanit"][] = [
  { id: "o-zeynep", ad: "Zeynep Demir", brans: "Fizik" },
  { id: "o-sule", ad: "Şule Kaya", brans: "Matematik" },
  { id: "o-ali", ad: "Ali Çelik", brans: "İngilizce" },
  { id: "o-ayse", ad: "Ayşe Yılmaz", brans: "Matematik Öğretmeni" },
];
export const SINIFLAR: Sema["SinifYanit"][] = [
  { id: "s-10a", ad: "10-A", seviye: 10, sube_grubu_id: null },
  { id: "s-9c", ad: "9-C", seviye: 9, sube_grubu_id: null },
  { id: "s-9a", ad: "9-A", seviye: 9, sube_grubu_id: null },
  { id: "s-9b", ad: "9-B", seviye: 9, sube_grubu_id: null },
];

/** Şablon uygulamasının boş raporu; testler istediği alanı ezer. */
export function bosRapor(degisiklik: Partial<Sema["SablonUygulamaSonucu"]> = {}): Sema["SablonUygulamaSonucu"] {
  return {
    sube_sayisi: 0, subeler: [], olusturulan: 0, zaten_var: 0, farkli_saatli: [], istisna_atlanan: [], istisna_ek: [],
    baska_sablonlu: [], ...degisiklik,
  };
}
export const DERSLER: Sema["DersYanit"][] = [
  { id: "d-mat", ad: "Matematik", kisa_ad: "MAT", renk: "#1d4ed8" },
  { id: "d-fiz", ad: "Fizik", kisa_ad: "FİZ", renk: "#c2410c" },
  { id: "d-kim", ad: "Kimya", kisa_ad: "KİM", renk: "#15803d" },
];

/** 9-A Matematik (Şule, 6), 9-B ve 9-C Matematik (öğretmensiz, 6), 9-A Fizik (Zeynep, 2). */
export function ornekAtamalar(): Atama[] {
  return [
    { id: "a-9a-mat", sinif_id: "s-9a", ders_id: "d-mat", ogretmen_id: "o-sule", haftalik_saat: 6 },
    { id: "a-9b-mat", sinif_id: "s-9b", ders_id: "d-mat", ogretmen_id: null, haftalik_saat: 6 },
    { id: "a-9c-mat", sinif_id: "s-9c", ders_id: "d-mat", ogretmen_id: null, haftalik_saat: 6 },
    { id: "a-9a-fiz", sinif_id: "s-9a", ders_id: "d-fiz", ogretmen_id: "o-zeynep", haftalik_saat: 2 },
  ];
}

/** Sunucunun özetinin varsayılanı: kapasite 40, aşım yok; sayılar örnek atamalarla tutarlı. */
export function ornekOzet(): Sema["DagilimOzeti"] {
  const ogretmen = (id: string, ders_saati: number): Sema["OgretmenYukuYanit"] => ({
    ogretmen_id: id, ders_saati, musait_saat: 40, kullanilabilir_saat: 40, asim: false, mesaj: null,
  });
  const sinif = (id: string, ders_saati: number, ogretmensiz_atama: number): Sema["SinifYukuYanit"] => ({
    sinif_id: id, ders_saati, kapasite: 40, ogretmensiz_atama, asim: false, mesaj: null,
  });
  return {
    haftalik_kapasite: 40,
    ogretmen_gunluk_siniri: 8,
    ogretmensiz_atama: 2,
    ogretmenler: [ogretmen("o-zeynep", 2), ogretmen("o-sule", 6), ogretmen("o-ali", 0), ogretmen("o-ayse", 0)],
    siniflar: [sinif("s-10a", 0, 0), sinif("s-9c", 6, 1), sinif("s-9a", 8, 0), sinif("s-9b", 6, 1)],
  };
}

export type Istek = { yontem: string; yol: string; govde?: unknown };

/**
 * Sahte API'yi kurar. Dönen nesne testin elindedir: `atamalar`, `sablon` ve `ozet` değiştirilebilir;
 * `istekler` gönderilen değişiklikleri kaydeder. `ozetGuncelle`, her değişiklikten sonra sunucunun
 * yeni özetini taklit etmek için çağrılır.
 */
export function dagilimApisiKur(
  secenekler: {
    atamalar?: Atama[];
    sablon?: SablonSatiri[];
    ogretmenler?: Sema["OgretmenYanit"][];
    siniflar?: Sema["SinifYanit"][];
    gruplar?: Sema["SubeGrubuYanit"][];
    istisnalar?: Sema["SubeIstisnasiYanit"][];
    ozetGuncelle?: (durum: SahteDurum) => void;
    uygulamaSonucu?: Sema["SablonUygulamaSonucu"];
    topluSonuc?: Sema["SeviyeUygulamaRaporu"][];
  } = {},
) {
  const durum: SahteDurum = {
    atamalar: secenekler.atamalar ?? ornekAtamalar(),
    sablon: secenekler.sablon ?? [],
    istisnalar: secenekler.istisnalar ?? [],
    ozet: ornekOzet(),
    istekler: [],
  };
  const siniflar = secenekler.siniflar ?? SINIFLAR;
  const degisti = () => secenekler.ozetGuncelle?.(durum);
  const kaydet = async (yontem: string, yol: string, request?: Request) => {
    const govde = request ? await request.json() : undefined;
    durum.istekler.push({ yontem, yol, govde });
    return govde;
  };

  sunucu.use(
    http.get("/api/ogretmenler", () => HttpResponse.json(secenekler.ogretmenler ?? OGRETMENLER)),
    http.get("/api/siniflar", () => HttpResponse.json(siniflar)),
    http.get("/api/sube-gruplari", () => HttpResponse.json(secenekler.gruplar ?? [])),
    http.get("/api/ders-programi/istisnalar", () => HttpResponse.json(durum.istisnalar)),
    // İstisna ders dağılımını da değiştirir (sunucudaki gibi): "almaz" dersi kaldırır, "ek" ekler.
    http.post("/api/ders-programi/istisnalar", async ({ request }) => {
      const govde = (await kaydet("POST", "istisnalar", request)) as Sema["SubeIstisnasiOlustur"];
      const ders = DERSLER.find((d) => d.id === govde.ders_id)?.ad ?? "";
      const sinif = siniflar.find((s) => s.id === govde.sinif_id)?.ad ?? "";
      if (govde.tur === "almaz") {
        durum.atamalar = durum.atamalar.filter((a) => !(a.sinif_id === govde.sinif_id && a.ders_id === govde.ders_id));
      } else if (!durum.atamalar.some((a) => a.sinif_id === govde.sinif_id && a.ders_id === govde.ders_id)) {
        durum.atamalar = [...durum.atamalar, { id: `a-ek-${durum.atamalar.length}`, sinif_id: govde.sinif_id,
          ders_id: govde.ders_id, ogretmen_id: null, haftalik_saat: govde.haftalik_saat ?? 1 }];
      }
      const yeni: Sema["SubeIstisnasiYanit"] = {
        id: `i-${durum.istisnalar.length}`, sinif_id: govde.sinif_id, ders_id: govde.ders_id, tur: govde.tur,
        haftalik_saat: govde.haftalik_saat ?? null, sinif_adi: sinif, ders_adi: ders, sablonda: govde.tur === "almaz",
        atanmis: govde.tur === "ek", uyari: null,
      };
      durum.istisnalar = [...durum.istisnalar, yeni];
      degisti();
      return HttpResponse.json(yeni, { status: 201 });
    }),
    http.delete("/api/ders-programi/istisnalar/:id", async ({ params }) => {
      await kaydet("DELETE", `istisnalar/${params.id}`);
      durum.istisnalar = durum.istisnalar.filter((i) => i.id !== params.id);
      return HttpResponse.json({ geri_eklenen_saat: null });
    }),
    http.get("/api/dersler", () => HttpResponse.json(DERSLER)),
    http.get("/api/ders-programi/atamalar", () => HttpResponse.json(durum.atamalar)),
    http.get("/api/ders-programi/dagilim-ozeti", () => HttpResponse.json(durum.ozet)),
    http.get("/api/ders-programi/seviye-sablonlari", () => HttpResponse.json(durum.sablon)),

    http.patch("/api/ders-programi/atamalar/:id", async ({ request, params }) => {
      const govde = (await kaydet("PATCH", `atamalar/${params.id}`, request)) as Partial<Atama>;
      durum.atamalar = durum.atamalar.map((a) => (a.id === params.id ? { ...a, ...govde } : a));
      degisti();
      return HttpResponse.json(durum.atamalar.find((a) => a.id === params.id));
    }),
    http.post("/api/ders-programi/atamalar/toplu-ogretmen", async ({ request }) => {
      const govde = (await kaydet("POST", "atamalar/toplu-ogretmen", request)) as Sema["TopluOgretmenAta"];
      durum.atamalar = durum.atamalar.map((a) =>
        govde.atama_idleri.includes(a.id) ? { ...a, ogretmen_id: govde.ogretmen_id ?? null } : a,
      );
      degisti();
      return HttpResponse.json(durum.atamalar.filter((a) => govde.atama_idleri.includes(a.id)));
    }),
    http.post("/api/ders-programi/atamalar", async ({ request }) => {
      const govde = (await kaydet("POST", "atamalar", request)) as Sema["DersAtamaOlustur"];
      const yeni: Atama = { id: `a-yeni-${durum.atamalar.length}`, ogretmen_id: null, ...govde };
      durum.atamalar = [...durum.atamalar, yeni];
      degisti();
      return HttpResponse.json(yeni, { status: 201 });
    }),
    http.delete("/api/ders-programi/atamalar/:id", async ({ params }) => {
      await kaydet("DELETE", `atamalar/${params.id}`);
      durum.atamalar = durum.atamalar.filter((a) => a.id !== params.id);
      degisti();
      return new HttpResponse(null, { status: 204 });
    }),

    http.put("/api/ders-programi/seviye-sablonlari/toplu", async ({ request }) => {
      const govde = (await kaydet("PUT", "seviye-sablonlari/toplu", request)) as Sema["SablonTopluKaydet"];
      const grup = govde.sube_grubu_id ?? null;
      const baska = durum.sablon.filter((s) => !(s.seviye === govde.seviye && (s.sube_grubu_id ?? null) === grup));
      const yeniler = govde.satirlar.filter((r) => r.haftalik_saat > 0).map((r, i) => ({
        id: `ss-toplu-${i}-${r.ders_id}`, seviye: govde.seviye, sube_grubu_id: grup, ders_id: r.ders_id, haftalik_saat: r.haftalik_saat,
      }));
      durum.sablon = [...baska, ...yeniler];
      return HttpResponse.json(yeniler);
    }),
    http.post("/api/ders-programi/seviye-sablonlari/uygula-hepsi", async () => {
      await kaydet("POST", "seviye-sablonlari/uygula-hepsi");
      return HttpResponse.json(secenekler.topluSonuc ?? []);
    }),
    http.post("/api/ders-programi/seviye-sablonlari/uygula", async ({ request }) => {
      await kaydet("POST", "seviye-sablonlari/uygula", request);
      return HttpResponse.json(secenekler.uygulamaSonucu ?? bosRapor());
    }),
    http.post("/api/ders-programi/seviye-sablonlari", async ({ request }) => {
      const govde = (await kaydet("POST", "seviye-sablonlari", request)) as Sema["SeviyeSablonuOlustur"];
      const yeni: SablonSatiri = { id: `ss-yeni-${durum.sablon.length}`, ...govde, sube_grubu_id: govde.sube_grubu_id ?? null };
      durum.sablon = [...durum.sablon, yeni];
      return HttpResponse.json(yeni, { status: 201 });
    }),
    http.patch("/api/ders-programi/seviye-sablonlari/:id", async ({ request, params }) => {
      const govde = (await kaydet("PATCH", `seviye-sablonlari/${params.id}`, request)) as { haftalik_saat: number };
      durum.sablon = durum.sablon.map((s) => (s.id === params.id ? { ...s, ...govde } : s));
      return HttpResponse.json(durum.sablon.find((s) => s.id === params.id));
    }),
    http.delete("/api/ders-programi/seviye-sablonlari/:id", async ({ params }) => {
      await kaydet("DELETE", `seviye-sablonlari/${params.id}`);
      durum.sablon = durum.sablon.filter((s) => s.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return durum;
}

export type SahteDurum = {
  atamalar: Atama[];
  sablon: SablonSatiri[];
  istisnalar: Sema["SubeIstisnasiYanit"][];
  ozet: Sema["DagilimOzeti"];
  istekler: Istek[];
};
