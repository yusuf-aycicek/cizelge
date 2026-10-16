/**
 * Liste sayfalarının API bağdaştırıcıları. Ortak liste bileşeni (ListeSayfasi) hangi varlığı
 * gösterdiğini bilmez; bu nesneler ona "listele, ekle, güncelle, sil"i verir. Her çağrının yolu ve
 * gövdesi OpenAPI şemasından gelen tiplerle denetlenir (yanlış alan adı derleme hatası olur).
 */
import { cagir } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";

type Sema = components["schemas"];
export type Ogretmen = Sema["OgretmenYanit"];
export type Sinif = Sema["SinifYanit"];
export type Ders = Sema["DersYanit"];

export type Kaynak<T, G> = {
  /** TanStack Query önbellek anahtarı. Değişiklikten sonra bu anahtarlı sorgu tazelenir. */
  anahtar: readonly string[];
  listele: () => Promise<T[]>;
  olustur: (girdi: G) => Promise<T>;
  guncelle: (id: string, girdi: Partial<G>) => Promise<T>;
  sil: (id: string) => Promise<unknown>;
};

const yol = (kayit_id: string) => ({ params: { path: { kayit_id } } });

export const ogretmenKaynagi: Kaynak<Ogretmen, Sema["OgretmenOlustur"]> = {
  anahtar: ["ogretmenler"],
  listele: () => cagir(api.GET("/api/ogretmenler")),
  olustur: (body) => cagir(api.POST("/api/ogretmenler", { body })),
  guncelle: (id, body) => cagir(api.PATCH("/api/ogretmenler/{kayit_id}", { ...yol(id), body })),
  sil: (id) => cagir(api.DELETE("/api/ogretmenler/{kayit_id}", yol(id))),
};

export const sinifKaynagi: Kaynak<Sinif, Sema["SinifOlustur"]> = {
  anahtar: ["siniflar"],
  listele: () => cagir(api.GET("/api/siniflar")),
  olustur: (body) => cagir(api.POST("/api/siniflar", { body })),
  guncelle: (id, body) => cagir(api.PATCH("/api/siniflar/{kayit_id}", { ...yol(id), body })),
  sil: (id) => cagir(api.DELETE("/api/siniflar/{kayit_id}", yol(id))),
};

export const dersKaynagi: Kaynak<Ders, Sema["DersOlustur"]> = {
  anahtar: ["dersler"],
  listele: () => cagir(api.GET("/api/dersler")),
  olustur: (body) => cagir(api.POST("/api/dersler", { body })),
  guncelle: (id, body) => cagir(api.PATCH("/api/dersler/{kayit_id}", { ...yol(id), body })),
  sil: (id) => cagir(api.DELETE("/api/dersler/{kayit_id}", yol(id))),
};
