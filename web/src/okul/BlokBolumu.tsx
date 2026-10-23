import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { FormHatasi } from "../bilesenler/form";
import { SEKILLER_ANAHTARI, ayniDesen, bolunusler, desenMetni, desenOku, otomatikDesen } from "../dersler/desen";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Okul.module.css";

type Kural = components["schemas"]["KuralYanit"];
type Okul = components["schemas"]["OkulYanit"];

const BLOK = "blok_deseni";
/** Tabloda gösterilen haftalık saatler (çoğu dersin saati bu aralıkta). */
const SAATLER = [1, 2, 3, 4, 5, 6];

/**
 * Okul geneli dağılım şekli: dersler bloklara bölünsün mü, bölünürse haftalık saate göre hangi
 * şekil önerilsin. Önerilen değerden farklı seçilen satırlar `varsayilanlar` olarak kaydedilir.
 * Derse özel şekil Dersler sayfasından seçilir.
 */
export function BlokBolumu({ kurallar, okul, onKaydet }: { kurallar: Kural[]; okul: Okul; onKaydet: () => void }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const kural = kurallar.find((k) => k.tur === BLOK);
  const n = Number(kurallar.find((k) => k.tur === "gunluk_ders_siniri")?.parametreler.n ?? 2);
  const kayitli = (kural?.parametreler.varsayilanlar ?? {}) as Record<string, number[]>;
  const [otomatik, setOtomatik] = useState(kural?.parametreler.otomatik !== false);
  const [secim, setSecim] = useState<Record<number, string>>(
    Object.fromEntries(SAATLER.map((s) => [s, desenMetni(kayitli[String(s)] ?? otomatikDesen(s))])),
  );

  const kaydet = useMutation({
    mutationFn: () => {
      // Yalnızca önerilenden farklı satırlar gönderilir; geri kalanı öneriyi izler.
      const varsayilanlar = Object.fromEntries(
        SAATLER.map((s) => [String(s), desenOku(secim[s] ?? "") ?? []] as const).filter(
          ([s, d]) => !ayniDesen(d, otomatikDesen(Number(s))),
        ),
      );
      return cagir(api.PUT("/api/ders-programi/kurallar/{tur}", {
        params: { path: { tur: BLOK } },
        body: { parametreler: { otomatik, varsayilanlar } },
      }));
    },
    onSuccess: () => {
      bildirim("basari", "Dağılım şekli kaydedildi.");
      onKaydet();
    },
    onSettled: () => Promise.all([SEKILLER_ANAHTARI, ["on-kontrol"]].map((k) => istemci.invalidateQueries({ queryKey: k }))),
  });

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    kaydet.mutate();
  }

  if (!kural) return null;
  return (
    <section className={sayfaStili.kart} aria-labelledby="dagilim-sekli">
      <h2 id="dagilim-sekli">Dağılım şekli (blok dersler)</h2>
      <p className={stil.aciklama}>
        Bir dersin haftalık saatleri art arda bloklara bölünür; her blok ayrı bir günde. Ör. 5 saatlik ders 2+2+1:
        iki gün ikişer saat, bir gün bir saat. Bir derste uygulanamazsa (gün, öğle arası, öğretmenin müsaitliği)
        o derste kendiliğinden kalkar. Derse özel şekil Dersler sayfasından seçilir.
      </p>
      <FormHatasi mesaj={kaydet.error ? hataMetni(kaydet.error) : undefined} />
      <form noValidate onSubmit={gonder}>
        <label className={stil.secenek}>
          <input type="checkbox" checked={otomatik} onChange={(o) => setOtomatik(o.target.checked)} />
          Dersleri bloklara böl (önerilen)
        </label>
        {otomatik && (
          <table className={stil.sekilTablosu}>
            <caption className="gorunmez">Haftalık saate göre önerilen dağılım şekli</caption>
            <thead>
              <tr>
                <th scope="col">Haftalık saat</th>
                <th scope="col">Dağılım şekli</th>
              </tr>
            </thead>
            <tbody>
              {SAATLER.map((s) => {
                const oneri = desenMetni(otomatikDesen(s));
                const secenekler = [...new Set([oneri, ...bolunusler(s, Math.min(n, 3), okul.gun_sayisi).map(desenMetni)])];
                return (
                  <tr key={s}>
                    <th scope="row">{s} saat</th>
                    <td>
                      <select aria-label={`${s} saatlik ders`} value={secim[s]} onChange={(o) => setSecim({ ...secim, [s]: o.target.value })}>
                        {secenekler.map((m) => (
                          <option key={m} value={m}>
                            {m}
                            {m === oneri ? " (önerilen)" : ""}
                          </option>
                        ))}
                        {!secenekler.includes(secim[s]!) && secim[s] !== "blok yok" && <option value={secim[s]}>{secim[s]}</option>}
                        <option value="blok yok">Blok yok</option>
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <Dugme type="submit" yukleniyor={kaydet.isPending} yukleniyorMetni="Kaydediliyor...">
          Dağılım şeklini kaydet
        </Dugme>
      </form>
    </section>
  );
}
