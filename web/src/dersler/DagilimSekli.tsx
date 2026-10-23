import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { useBildirim } from "../bilesenler/Bildirim";
import { useBen } from "../kimlik/oturum";
import { KURALLAR_ANAHTARI } from "../okul/OkulAyarlariSayfasi";
import stil from "./Ders.module.css";
import type { Ders } from "../listeler/kaynaklar";
import { SEKILLER_ANAHTARI, bolunusler, desenMetni, desenOku } from "./desen";

type Sekil = components["schemas"]["DagilimSekli"];
type Kural = components["schemas"]["KuralYanit"];

const BLOK = "blok_deseni";
const OKUL_ONERISI = "";
const BASKA = "baska";

export function useDagilimSekilleri() {
  return useQuery({ queryKey: SEKILLER_ANAHTARI, queryFn: () => cagir(api.GET("/api/ders-programi/dagilim-sekilleri")) });
}

/**
 * Ders listesinde bir dersin dağılım şekli: geçerli şekil ve nereden geldiği, değiştirme seçimi,
 * sorunlar. Seçenekler: okul önerisi (özel ayarı kaldırır), blok yok, dersin haftalık saatinin hazır
 * bölünüşleri ve elle yazılan şekil ("2+2+1"). Seçim hemen kaydedilir (derse özel ayar).
 */
export function DagilimSekliHucresi({ ders, sekiller, kurallar }: { ders: Ders; sekiller: Sekil[]; kurallar: Kural[] }) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const okul = useBen().data?.okul;
  const id = useId();
  const [elle, setElle] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null);

  const satirlar = sekiller.filter((s) => s.ders_id === ders.id);
  const blok = kurallar.find((k) => k.tur === BLOK);
  const ozel = blok?.ozel_ayarlar.find((o) => o.kapsam.ders_id === ders.id && !o.kapsam.sinif_id);
  const ozelDesen = ozel ? (ozel.parametreler.desen as number[]) : null;
  const n = Number(kurallar.find((k) => k.tur === "gunluk_ders_siniri")?.parametreler.n ?? 2);
  // Hazır seçenekler dersin en sık haftalık saatine göre (şubelerde farklıysa elle yazılabilir).
  const saatler = [...new Set(satirlar.map((s) => s.haftalik_saat))];
  const saat = enSik(satirlar.map((s) => s.haftalik_saat));
  const hazir = saat ? bolunusler(saat, Math.min(n, 3), okul?.gun_sayisi ?? 5) : [];

  const kaydet = useMutation({
    mutationFn: async (desen: number[] | null) => {
      if (desen === null) {
        await cagir(api.DELETE("/api/ders-programi/kurallar/{tur}/ozel", {
          params: { path: { tur: BLOK }, query: { ders_id: ders.id } },
        }));
      } else {
        await cagir(api.PUT("/api/ders-programi/kurallar/{tur}/ozel", {
          params: { path: { tur: BLOK } },
          body: { kapsam: { ders_id: ders.id }, parametreler: { desen } },
        }));
      }
    },
    onSuccess: (_, desen) => {
      setElle(null);
      setHata(null);
      bildirim("basari", `${ders.ad}: dağılım şekli ${desen === null ? "okul önerisine döndü" : desenMetni(desen)}.`);
    },
    onError: (h) => setHata(hataMetni(h)),
    // Şekil ön kontrolü, özet ve kurallar listesini de değiştirir.
    onSettled: () =>
      Promise.all([SEKILLER_ANAHTARI, KURALLAR_ANAHTARI, ["on-kontrol"]].map((k) => istemci.invalidateQueries({ queryKey: k }))),
  });

  const secili = elle !== null ? BASKA : ozelDesen === null ? OKUL_ONERISI : desenMetni(ozelDesen);
  const hazirMetinler = hazir.map(desenMetni);
  const secenekVar = secili === OKUL_ONERISI || secili === BASKA || secili === "blok yok" || hazirMetinler.includes(secili);

  function sec(deger: string) {
    if (deger === BASKA) return setElle(ozelDesen ? desenMetni(ozelDesen) : "");
    setElle(null);
    kaydet.mutate(deger === OKUL_ONERISI ? null : (desenOku(deger) ?? []));
  }

  function elleKaydet() {
    const desen = desenOku(elle ?? "");
    if (desen === null) return setHata("Şekli 2+2+1 gibi yazın; her blok 1-8 saat.");
    kaydet.mutate(desen);
  }

  const etkin = [...new Set(satirlar.map((s) => s.metin))];
  const dusen = satirlar.filter((s) => s.dusen_oneri);
  const sorunlu = satirlar.filter((s) => s.sorunlar.length > 0);

  return (
    <div className={stil.sekil}>
      <div className={stil.sekilSatiri}>
        <select
          id={id}
          className={stil.sekilSecimi}
          aria-label={`${ders.ad} dersinin dağılım şekli`}
          value={secili}
          disabled={kaydet.isPending}
          onChange={(o) => sec(o.target.value)}
        >
          <option value={OKUL_ONERISI}>Okul önerisi{etkin.length && !ozel ? ` (${etkin.join(", ")})` : ""}</option>
          <option value="blok yok">Blok yok</option>
          {hazirMetinler.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
          {!secenekVar && <option value={secili}>{secili}</option>}
          <option value={BASKA}>Başka bir şekil…</option>
        </select>
        {ozel && <span className={stil.ozelRozeti}>özel</span>}
      </div>
      {elle !== null && (
        <form className={stil.sekilSatiri} onSubmit={(o) => { o.preventDefault(); elleKaydet(); }}>
          <input
            className={stil.sekilMetni}
            aria-label={`${ders.ad} dersinin dağılım şekli (ör. 2+2+1)`}
            placeholder="2+2+1"
            value={elle}
            autoFocus
            onChange={(o) => setElle(o.target.value)}
          />
          <button type="submit" className={stil.kucukDugme} disabled={kaydet.isPending}>Kaydet</button>
          <button type="button" className={stil.kucukDugme} onClick={() => { setElle(null); setHata(null); }}>Vazgeç</button>
        </form>
      )}
      {satirlar.length === 0 && <p className={stil.sekilNotu}>Henüz bir şubeye atanmadı.</p>}
      {saatler.length > 1 && ozel && (
        <p className={stil.sekilNotu}>Şubelerde haftalık saat farklı ({saatler.join(", ")}); şekil hepsine uymayabilir.</p>
      )}
      {sorunlu.map((s) => (
        <p key={s.atama_id} className={stil.sekilSorunu} role="note">
          {sinifAdi(s)}: {s.sorunlar.join("; ")}
        </p>
      ))}
      {dusen.length > 0 && (
        <p className={stil.sekilNotu}>
          Öneri uygulanamadı, blok yok: {dusen.map((s) => `${sinifAdi(s)} (${s.nedenler.join("; ")})`).join(", ")}.
        </p>
      )}
      {hata && <p className={stil.sekilSorunu} role="alert">{hata}</p>}
    </div>
  );
}

const sinifAdi = (s: Sekil) => s.sinif_adi;

function enSik(sayilar: number[]): number | undefined {
  const sayac = new Map<number, number>();
  for (const s of sayilar) sayac.set(s, (sayac.get(s) ?? 0) + 1);
  return [...sayac.entries()].sort((a, b) => b[1] - a[1] || b[0] - a[0])[0]?.[0];
}
