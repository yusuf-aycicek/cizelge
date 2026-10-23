import { dersIsaretleri } from "../dersler/isaret";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarRange } from "lucide-react";
import type { CSSProperties } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { hataMetni } from "../api/hata";
import { SecimAlani } from "../bilesenler/Alan";
import { kisaKisiAdi } from "../bilesenler/darAlan";
import { SigdirilanMetin } from "../bilesenler/SigdirilanMetin";
import { Iskelet } from "../bilesenler/Iskelet";
import { OgretmenRozeti } from "../bilesenler/OgretmenRozeti";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Sekmeler } from "../bilesenler/Sekmeler";
import { useAtamalar } from "../dagilim/veri";
import { DersCipi } from "../dersler/DersCipi";
import { useBen } from "../kimlik/oturum";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi, type Ders, type Ogretmen, type Sinif } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { GUN_ADLARI } from "./aciklama";
import { cizelgeBoyutu, cizelgeHucreleri, hucreAnahtari, yerlesmeGecikmesiMs, type Atama, type CizelgeTuru } from "./cizelge";
import stil from "./Cizelge.module.css";
import { KaliteOzeti } from "./KaliteOzeti";
import { useProgram, useYerlesimler } from "./veri";

const SEKMELER = [
  { anahtar: "sube", ad: "Şubeye göre" },
  { anahtar: "ogretmen", ad: "Öğretmene göre" },
] as const;

/**
 * Haftalık çizelge: bir programın şube ya da öğretmen bazında gün × saat görünümü. Seçili görünüm
 * ve kişi adres çubuğunda (`?gorunum=ogretmen&ogretmen=...`): bağlantı paylaşılabilir.
 */
export function CizelgeSayfasi() {
  const { id = "" } = useParams();
  const [parametreler, setParametreler] = useSearchParams();
  const program = useProgram(id);
  const hazir = program.data?.durum === "hazir";
  const yerlesimler = useYerlesimler(id, hazir);
  const atamalar = useAtamalar();
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const okul = useBen().data?.okul;

  const sorgular = [program, atamalar, dersler, siniflar, ogretmenler];
  const hatali = sorgular.find((s) => s.isError) ?? (yerlesimler.isError ? yerlesimler : undefined);

  const baslik = (
    <SayfaBasligi ikon={CalendarRange} baslik="Haftalık çizelge">
      {program.data ? `“${program.data.ad}” programı. ` : ""}Bir şube ya da öğretmen seçin.
    </SayfaBasligi>
  );

  if (hatali) {
    return (
      <>
        {baslik}
        <div className={sayfaStili.hataKutusu} role="alert">
          <p>{hataMetni(hatali.error)}</p>
        </div>
      </>
    );
  }
  if (program.data && !hazir) {
    return (
      <>
        {baslik}
        <p>
          Bu program henüz hazır değil ya da oluşturulamadı. <Link to="/program">Program sayfasına dönün.</Link>
        </p>
      </>
    );
  }
  if (!program.data || !yerlesimler.data || !atamalar.data || !dersler.data || !siniflar.data || !ogretmenler.data || !okul) {
    return (
      <>
        {baslik}
        <Iskelet satir={8} kart />
      </>
    );
  }

  const gorunum: CizelgeTuru = parametreler.get("gorunum") === "ogretmen" ? "ogretmen" : "sube";
  const subeler = turkceSirala(siniflar.data, (s) => s.ad);
  const hocalar = turkceSirala(ogretmenler.data, (o) => o.ad);
  const secenekler = gorunum === "sube" ? subeler : hocalar;
  const seciliId = parametreler.get(gorunum === "sube" ? "sinif" : "ogretmen") ?? secenekler[0]?.id ?? "";
  const secili = secenekler.find((x) => x.id === seciliId);
  const sec = (degisiklik: Record<string, string>) =>
    setParametreler((onceki) => {
      const yeni = new URLSearchParams(onceki);
      for (const [k, v] of Object.entries(degisiklik)) yeni.set(k, v);
      return yeni;
    });

  const hucreler = cizelgeHucreleri(yerlesimler.data, atamalar.data, gorunum, seciliId);
  const boyut = cizelgeBoyutu(yerlesimler.data, okul.gun_sayisi, okul.gunluk_ders_saati);

  return (
    <>
      {baslik}
      <p className={stil.geri}>
        <Link to="/program">
          <ArrowLeft aria-hidden="true" /> Program sayfası
        </Link>
      </p>
      <Sekmeler etiket="Çizelge türü" sekmeler={SEKMELER} secili={gorunum} onSec={(g) => sec({ gorunum: g })} idOneki="cizelge">
        <div className={stil.secim}>
          <SecimAlani
            etiket={gorunum === "sube" ? "Şube" : "Öğretmen"}
            value={seciliId}
            onChange={(o) => sec(gorunum === "sube" ? { sinif: o.target.value } : { ogretmen: o.target.value })}
          >
            {secenekler.map((x) => (
              <option key={x.id} value={x.id}>
                {x.ad}
              </option>
            ))}
          </SecimAlani>
          <p className={stil.ozet}>{hucreler.size} ders saati</p>
        </div>
        {secili && (
          // key: başka şube ya da öğretmen seçilince tablo yeniden kurulur, hücreler yeniden yerleşir.
          <Cizelge
            key={`${gorunum}-${seciliId}`}
            baslik={`${secili.ad} haftalık programı`}
            gunSayisi={boyut.gun}
            saatSayisi={boyut.saat}
            hucreler={hucreler}
            gorunum={gorunum}
            ders={new Map(dersler.data.map((d) => [d.id, d]))}
            dersIsareti={dersIsaretleri(dersler.data)}
            sinif={new Map(siniflar.data.map((s) => [s.id, s]))}
            ogretmen={new Map(ogretmenler.data.map((o) => [o.id, o]))}
          />
        )}
      </Sekmeler>
      <div className={sayfaStili.kart}>
        <KaliteOzeti program={program.data} />
      </div>
    </>
  );
}

type CizelgeProps = {
  baslik: string;
  gunSayisi: number;
  saatSayisi: number;
  hucreler: Map<string, Atama>;
  gorunum: CizelgeTuru;
  ders: Map<string, Ders>;
  dersIsareti: Map<string, number>;
  sinif: Map<string, Sinif>;
  ogretmen: Map<string, Ogretmen>;
};

/**
 * Gün × saat tablosu. Doğal <table>: ekran okuyucu hücreyi "Salı, 3. saat: Matematik, Ayşe Yılmaz"
 * diye okur (sütun ve satır başlıkları `scope` ile bağlı). Dolu hücreler kısa bir sırayla yerleşir
 * (CSS animasyonu, hücre başına gecikme); hareket azaltılmışsa hepsi hemen görünür.
 */
function Cizelge({ baslik, gunSayisi, saatSayisi, hucreler, gorunum, ders, dersIsareti, sinif, ogretmen }: CizelgeProps) {
  const gunler = Array.from({ length: gunSayisi }, (_, g) => GUN_ADLARI[g] ?? `${g + 1}. gün`);
  return (
    // Haftalık çizelge dar ekranda bilerek yana kayar (en az 44rem); taşma denetimi bunu bilir.
    <div className={stil.kutu} data-kaydirilabilir>
      <table className={stil.cizelge}>
        <caption className="gorunmez">{baslik}</caption>
        <thead>
          <tr>
            <th scope="col" className={stil.kose}>
              <span className="gorunmez">Saat</span>
            </th>
            {gunler.map((g) => (
              <th key={g} scope="col">
                {g}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: saatSayisi }, (_, s) => (
            <tr key={s}>
              <th scope="row" className={stil.saatBasligi}>
                {s + 1}. saat
              </th>
              {gunler.map((_, g) => {
                const a = hucreler.get(hucreAnahtari(g, s));
                if (!a) {
                  return (
                    <td key={g} className={stil.bos}>
                      <span className="gorunmez">Boş</span>
                    </td>
                  );
                }
                const d = ders.get(a.ders_id);
                const o = a.ogretmen_id ? ogretmen.get(a.ogretmen_id) : undefined;
                const gecikme = { animationDelay: `${yerlesmeGecikmesiMs(g, s, saatSayisi)}ms` } as CSSProperties;
                return (
                  <td key={g} className={stil.dolu} style={gecikme}>
                    <DersCipi ad={d?.ad ?? "?"} kisaAd={d?.kisa_ad} renk={d?.renk} isaret={dersIsareti.get(a.ders_id)} />
                    <span className={stil.ikinci}>
                      {gorunum === "sube" ? (
                        o && (
                          <>
                            <OgretmenRozeti id={o.id} ad={o.ad} boyut="kucuk" />
                            <SigdirilanMetin uzun={o.ad} kisa={kisaKisiAdi(o.ad)} />
                          </>
                        )
                      ) : (
                        sinif.get(a.sinif_id)?.ad
                      )}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
