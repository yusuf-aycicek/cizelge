/**
 * Paylaşım sayfası (8b, ADR 0022): `/p/:jeton`. Girişsiz, salt okunur; yayınlanan programın linkin
 * kapsamındaki kısmı (bütün okul, tek öğretmen ya da tek şube). Sunucu içeriği zaten süzer: bu
 * sayfa yalnızca gelen çizelgeleri gösterir.
 *
 * Telefonda gün gün (bugün açık başlar), genişte haftalık tablo; ikisi de aynı veriden, görünür
 * olan CSS ile seçilir. PDF sunucuda, yayının içeriğinden üretilir.
 */
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { ApiHatasi, cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { UYGULAMA_ADI } from "../urun";
import stil from "./Paylasim.module.css";

type Icerik = components["schemas"]["PaylasimYanit"];
type Cizelge = components["schemas"]["PaylasimCizelgesi"];
type Hucre = components["schemas"]["PaylasimHucresi"];
type Hafta = components["schemas"]["PaylasimHaftasi"];

export const paylasimPdfAdresi = (jeton: string, secim?: Cizelge) => {
  const sorgu = secim ? `?${new URLSearchParams({ [secim.tur]: secim.ad })}` : "";
  return `/api/ders-programi/paylasim/${encodeURIComponent(jeton)}/program.pdf${sorgu}`;
};

/** Bugün okul günüyse o gün (pazartesi 0), değilse pazartesi. */
function bugun(gunSayisi: number): number {
  const g = (new Date().getDay() + 6) % 7;
  return g < gunSayisi ? g : 0;
}

const zilMetni = (h: Hafta, s: number, uzunluk = 1) => {
  const bas = h.zil?.[s];
  const son = h.zil?.[s + uzunluk - 1];
  return bas && son ? `${bas.baslangic}–${son.bitis}` : "";
};

const saatMetni = (s: number, uzunluk: number) => (uzunluk > 1 ? `${s + 1}.-${s + uzunluk}. saat` : `${s + 1}. saat`);

function HucreIcerigi({ h, tur }: { h: Hucre; tur: Cizelge["tur"] }) {
  // Öğretmen çizelgesinde şube, şube çizelgesinde öğretmen ikinci satırdır.
  const ikinci = tur === "ogretmen" ? h.sube : h.ogretmen;
  return (
    <>
      <span className={stil.ders}>{tur === "ogretmen" ? h.sube : h.ders}</span>
      {ikinci && <span className={stil.ikinci}>{tur === "ogretmen" ? h.ders : ikinci}</span>}
    </>
  );
}

// Telefonda bütün günler tek satıra sığsın diye kısa ad; ekran okuyucu tam adı okur (aria-label).
const KISA_GUN: Record<string, string> = {
  Pazartesi: "Pzt", Salı: "Sal", Çarşamba: "Çar", Perşembe: "Per", Cuma: "Cum", Cumartesi: "Cmt", Pazar: "Paz",
};

function GunGun({ c, hafta }: { c: Cizelge; hafta: Hafta }) {
  const [gun, setGun] = useState(() => bugun(hafta.gun_adlari.length));
  const satirlar = [];
  for (let s = 0; s < (hafta.gun_saatleri[gun] ?? hafta.saat_sayisi); s++) {
    const h = c.hucreler.find((x) => x.gun === gun && x.saat === s);
    if (c.hucreler.some((x) => x.gun === gun && x.saat < s && s < x.saat + x.uzunluk)) continue;
    const uzunluk = h?.uzunluk ?? 1;
    satirlar.push(
      <li key={s} className={h ? stil.dolu : stil.bos} style={h ? { borderInlineStartColor: h.renk } : undefined}>
        <span className={stil.saat}>
          {saatMetni(s, uzunluk)}
          <span className={stil.zil}>{zilMetni(hafta, s, uzunluk)}</span>
        </span>
        <span className={stil.icerik}>{h ? <HucreIcerigi h={h} tur={c.tur} /> : "Boş"}</span>
      </li>,
    );
    if (hafta.ogle_arasi_sonra != null && s + uzunluk === hafta.ogle_arasi_sonra) {
      satirlar.push(<li key={`ogle-${s}`} className={stil.ogle}>Öğle arası {hafta.ogle_zili ? `· ${hafta.ogle_zili.baslangic}–${hafta.ogle_zili.bitis}` : ""}</li>);
    }
  }
  return (
    <div className={stil.gunGun}>
      <div className={stil.gunler} role="group" aria-label="Gün">
        {hafta.gun_adlari.map((ad, g) => (
          <button key={ad} type="button" aria-pressed={g === gun} aria-label={ad} onClick={() => setGun(g)}
            className={stil.gunDugmesi}>
            {KISA_GUN[ad] ?? ad.slice(0, 3)}
          </button>
        ))}
      </div>
      <ol className={stil.liste} aria-label={`${hafta.gun_adlari[gun]} dersleri`}>{satirlar}</ol>
    </div>
  );
}

function Haftalik({ c, hafta }: { c: Cizelge; hafta: Hafta }) {
  const govde = [];
  for (let s = 0; s < hafta.saat_sayisi; s++) {
    govde.push(
      <tr key={s}>
        <th scope="row">{s + 1}. saat<span className={stil.zil}>{zilMetni(hafta, s)}</span></th>
        {hafta.gun_adlari.map((ad, g) => {
          if (c.hucreler.some((x) => x.gun === g && x.saat < s && s < x.saat + x.uzunluk)) return null;
          const h = c.hucreler.find((x) => x.gun === g && x.saat === s);
          if (!h) return <td key={ad} className={s < (hafta.gun_saatleri[g] ?? 0) ? undefined : stil.yok} />;
          return (
            <td key={ad} rowSpan={h.uzunluk} className={stil.dolu} style={{ borderInlineStartColor: h.renk }}>
              <HucreIcerigi h={h} tur={c.tur} />
            </td>
          );
        })}
      </tr>,
    );
    if (hafta.ogle_arasi_sonra != null && s + 1 === hafta.ogle_arasi_sonra) {
      govde.push(<tr key="ogle" className={stil.ogle}><td colSpan={hafta.gun_adlari.length + 1}>Öğle arası</td></tr>);
    }
  }
  return (
    <table className={stil.tablo}>
      <caption className="gorunmez">{c.ad} haftalık ders programı</caption>
      <thead>
        <tr>
          <td />
          {hafta.gun_adlari.map((ad) => <th key={ad} scope="col">{ad}</th>)}
        </tr>
      </thead>
      <tbody>{govde}</tbody>
    </table>
  );
}

function Secici({ icerik, secili, onSec }: { icerik: Icerik; secili: Cizelge; onSec: (c: Cizelge) => void }) {
  const hepsi = [...icerik.subeler, ...icerik.ogretmenler];
  return (
    <label className={stil.secici}>
      Şube ya da öğretmen
      <select value={`${secili.tur}:${secili.ad}`} onChange={(e) => {
        const c = hepsi.find((x) => `${x.tur}:${x.ad}` === e.target.value);
        if (c) onSec(c);
      }}>
        <optgroup label="Şubeler">
          {icerik.subeler.map((c) => <option key={c.ad} value={`sube:${c.ad}`}>{c.ad}</option>)}
        </optgroup>
        <optgroup label="Öğretmenler">
          {icerik.ogretmenler.map((c) => <option key={c.ad} value={`ogretmen:${c.ad}`}>{c.ad}</option>)}
        </optgroup>
      </select>
    </label>
  );
}

export function PaylasimSayfasi() {
  const { jeton = "" } = useParams();
  const sorgu = useQuery({
    queryKey: ["paylasim", jeton],
    queryFn: () => cagir(api.GET("/api/ders-programi/paylasim/{jeton}", { params: { path: { jeton } } })),
    retry: false,
  });
  const [secim, setSecim] = useState<Cizelge | null>(null);

  // Jeton adreste: bu sayfadan başka siteye giden istek adresi (Referer) taşımasın.
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "referrer";
    meta.content = "no-referrer";
    document.head.appendChild(meta);
    return () => meta.remove();
  }, []);

  const icerik = sorgu.data;
  const cizelgeler = icerik ? [...icerik.subeler, ...icerik.ogretmenler] : [];
  const secili = secim ?? cizelgeler[0];
  useEffect(() => {
    if (icerik?.yayinda) document.title = `${secili?.ad ?? icerik.okul} – ${UYGULAMA_ADI}`;
  }, [icerik, secili]);

  let govde;
  if (sorgu.isPending) govde = <p role="status">Program yükleniyor…</p>;
  else if (sorgu.isError) {
    govde = (
      <div className={stil.mesaj}>
        <h1>Bu link geçerli değil</h1>
        <p>
          {sorgu.error instanceof ApiHatasi && sorgu.error.durum === 404
            ? "Link iptal edilmiş ya da yenilenmiş olabilir. Okul yönetiminden güncel linki isteyin."
            : hataMetni(sorgu.error)}
        </p>
      </div>
    );
  } else if (!icerik?.yayinda || !icerik.hafta) {
    govde = (
      <div className={stil.mesaj}>
        <h1>Yayında program yok</h1>
        <p>Okul yönetimi programı yayınladığında burada görünecek.</p>
      </div>
    );
  } else if (!secili) {
    govde = (
      <div className={stil.mesaj}>
        <h1>{icerik.okul}</h1>
        <p>Yayınlanan programda bu linkin dersi yok.</p>
      </div>
    );
  } else {
    govde = (
      <>
        <header className={stil.ust}>
          <p className={stil.okul}>{icerik.okul}</p>
          <h1>{secili.ad} <span className={stil.altBaslik}>haftalık ders programı</span></h1>
          <p className={stil.bilgi}>
            {icerik.program}
            {icerik.yayin_zamani && ` · ${new Date(icerik.yayin_zamani).toLocaleDateString("tr-TR")} tarihinde yayınlandı`}
            {` · haftada ${secili.hucreler.reduce((t, h) => t + h.uzunluk, 0)} ders saati`}
          </p>
          <div className={stil.eylemler}>
            {cizelgeler.length > 1 && <Secici icerik={icerik} secili={secili} onSec={setSecim} />}
            <a className={stil.pdf} href={paylasimPdfAdresi(jeton, cizelgeler.length > 1 ? secili : undefined)} download>
              <Download aria-hidden="true" /> PDF indir
            </a>
          </div>
        </header>
        <div className={stil.haftalik}><Haftalik c={secili} hafta={icerik.hafta} /></div>
        <GunGun key={`${secili.tur}:${secili.ad}`} c={secili} hafta={icerik.hafta} />
      </>
    );
  }

  return (
    <main className={stil.sayfa}>
      <p className={stil.marka}><CalendarDays aria-hidden="true" /> {UYGULAMA_ADI}</p>
      {govde}
    </main>
  );
}
