import { dersIsaretleri } from "../dersler/isaret";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarRange } from "lucide-react";
import { Fragment, type CSSProperties } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { hataMetni } from "../api/hata";
import { SecimAlani } from "../bilesenler/Alan";
import { kisaKisiAdi } from "../bilesenler/darAlan";
import { SigdirilanMetin } from "../bilesenler/SigdirilanMetin";
import { Iskelet } from "../bilesenler/Iskelet";
import { TELEFON, useMedya } from "../bilesenler/medya";
import { OgretmenRozeti } from "../bilesenler/OgretmenRozeti";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Sekmeler } from "../bilesenler/Sekmeler";
import { useAtamalar } from "../dagilim/veri";
import { DersCipi } from "../dersler/DersCipi";
import { useBen } from "../kimlik/oturum";
import { ogleArasiSonrasi, ogleArasiZili, saatVar, zilMetni, zilSaatleri, type ZilSaati } from "../okul/zaman";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi, type Ders, type Ogretmen, type Sinif } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { GUN_ADLARI } from "./aciklama";
import { birlesikHucreler, cizelgeBoyutu, cizelgeHucreleri, hucreAnahtari, yerlesmeGecikmesiMs, type Atama, type CizelgeTuru } from "./cizelge";
import stil from "./Cizelge.module.css";
import { GunlukCizelge } from "./GunlukCizelge";
import { KaliteOzeti } from "./KaliteOzeti";
import { useProgram, useYerlesimler } from "./veri";

const SEKMELER = [
  { anahtar: "sube", ad: "Şubeye göre" },
  { anahtar: "ogretmen", ad: "Öğretmene göre" },
] as const;

/**
 * Haftalık çizelge: bir programın şube ya da öğretmen bazında gün × saat görünümü. Seçili görünüm
 * ve kişi adres çubuğunda (`?gorunum=ogretmen&ogretmen=...`): bağlantı paylaşılabilir. Telefonda
 * (dar ekran) tablo yerine gün gün liste (5.6).
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
  const telefon = useMedya(TELEFON);

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
  const zil = zilSaatleri(okul, boyut.saat);
  const cizelgeOzellikleri: CizelgeProps | undefined = secili && {
    baslik: `${secili.ad} haftalık programı`,
    gunSayisi: boyut.gun,
    saatSayisi: boyut.saat,
    gunSaatleri: okul.gun_saatleri,
    ogleArasiSonra: okul.ogle_arasi_sonra,
    zil,
    ogleZili: ogleArasiZili(okul, zil),
    hucreler,
    gorunum,
    ders: new Map(dersler.data.map((d) => [d.id, d])),
    dersIsareti: dersIsaretleri(dersler.data),
    sinif: new Map(siniflar.data.map((s) => [s.id, s])),
    ogretmen: new Map(ogretmenler.data.map((o) => [o.id, o])),
  };

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
        {/* key: başka şube ya da öğretmen seçilince çizelge yeniden kurulur, hücreler yeniden yerleşir. */}
        {cizelgeOzellikleri &&
          (telefon ? (
            <GunlukCizelge key={`${gorunum}-${seciliId}`} {...cizelgeOzellikleri} />
          ) : (
            <Cizelge key={`${gorunum}-${seciliId}`} {...cizelgeOzellikleri} />
          ))}
      </Sekmeler>
      <div className={sayfaStili.kart}>
        <KaliteOzeti program={program.data} />
      </div>
    </>
  );
}

export type CizelgeProps = {
  baslik: string;
  gunSayisi: number;
  saatSayisi: number;
  /** Her günün ders saati sayısı: kısa günün sonundaki hücreler "ders yok" görünür. */
  gunSaatleri: readonly number[];
  ogleArasiSonra: number | null;
  zil: ZilSaati[] | null;
  ogleZili: ZilSaati | null;
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
function Cizelge({
  baslik, gunSayisi, saatSayisi, gunSaatleri, ogleArasiSonra, zil, ogleZili, hucreler, gorunum, ders, dersIsareti, sinif,
  ogretmen,
}: CizelgeProps) {
  const gunler = Array.from({ length: gunSayisi }, (_, g) => GUN_ADLARI[g] ?? `${g + 1}. gün`);
  const birlesik = birlesikHucreler(hucreler, gunSayisi, saatSayisi, ogleArasiSonra);
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
            <Fragment key={s}>
              <tr>
                <th scope="row" className={stil.saatBasligi}>
                  {s + 1}. saat
                  {zil?.[s] && <span className={stil.zil}>{zilMetni(zil[s])}</span>}
                </th>
                {gunler.map((_, g) => {
                  const a = hucreler.get(hucreAnahtari(g, s));
                  // Bloğun ikinci ve sonraki saatleri: üstteki hücre rowSpan ile kapsar.
                  if (birlesik.ortulen.has(hucreAnahtari(g, s))) return null;
                  if (!a && !saatVar(gunSaatleri, g, s)) {
                    // Kısa gün (ör. cuma 7 saat): bu saat o gün yok. Eski bir programın hücresi varsa yine gösterilir.
                    return (
                      <td key={g} className={stil.yok}>
                        <span className="gorunmez">Bu saatte ders yok</span>
                      </td>
                    );
                  }
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
                  const uzunluk = birlesik.uzunluk.get(hucreAnahtari(g, s)) ?? 1;
                  return (
                    <td key={g} className={uzunluk > 1 ? `${stil.dolu} ${stil.blok}` : stil.dolu} style={gecikme}
                      rowSpan={uzunluk > 1 ? uzunluk : undefined}>
                      {uzunluk > 1 && (
                        // Ekran okuyucu satır başlığı olarak yalnızca ilk saati okur: kaç saat sürdüğü burada.
                        <span className={stil.blokSuresi}>
                          <span aria-hidden="true">{uzunluk} saat</span>
                          <span className="gorunmez">{`${s + 1}.-${s + uzunluk}. saat, ${uzunluk} saat art arda: `}</span>
                        </span>
                      )}
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
              {ogleArasiSonrasi(ogleArasiSonra, s) && s + 1 < saatSayisi && (
                // Öğle arası iki ders arasında ince bir ayraç: satır, ama hücreleri yok.
                <tr className={stil.ogleArasi}>
                  <th scope="row" colSpan={gunSayisi + 1}>
                    <span>Öğle arası{ogleZili && ` · ${zilMetni(ogleZili)}`}</span>
                  </th>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
