import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { hataMetni } from "../api/hata";
import { Dugme } from "../bilesenler/Dugme";
import { Sekmeler } from "../bilesenler/Sekmeler";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi, type Ders, type Ogretmen, type Sinif } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Dagilim.module.css";
import { DersGorunumu } from "./DersGorunumu";
import { OgretmenGorunumu } from "./OgretmenGorunumu";
import { SubeGorunumu } from "./SubeGorunumu";
import {
  useAtamalar,
  useDagilimOzeti,
  useOgretmenYukleri,
  useSinifYukleri,
  type Atama,
  type DagilimOzeti,
  type OgretmenYuku,
  type SinifYuku,
} from "./veri";

type Gorunum = "sube" | "ogretmen" | "ders";
const SEKMELER = [
  { anahtar: "sube", ad: "Şubelere göre" },
  { anahtar: "ogretmen", ad: "Öğretmenlere göre" },
  { anahtar: "ders", ad: "Derslere göre" },
] as const;

/** Görünümlerin ortak verisi. Sayfa bir kez yükler, görünümlere prop olarak verir. */
export type DagilimVerisi = {
  ogretmenler: Ogretmen[];
  siniflar: Sinif[];
  dersler: Ders[];
  atamalar: Atama[];
  ozet: DagilimOzeti;
  ogretmenYukleri: Map<string, OgretmenYuku>;
  sinifYukleri: Map<string, SinifYuku>;
  ogretmen: Map<string, Ogretmen>;
  sinif: Map<string, Sinif>;
  ders: Map<string, Ders>;
};

/** Görünümlerin "başka bir yere git" isteği: sekme, şube, ders. */
export type Git = (hedef: { gorunum?: Gorunum; sinif?: string; ders?: string }) => void;

/**
 * Ders dağılımı: hangi şubenin hangi dersine hangi öğretmen, haftada kaç saat.
 *
 * **Durum yukarıda:** seçili görünüm, şube ve ders bu sayfada (adres çubuğunda, `?gorunum=sube&
 * sinif=...`) tutulur, görünümlerde değil. Görünümler yalnızca okur ve `git` ile değişiklik
 * ister. Bu yüzden öğretmen görünümündeki "9-A şubesine git" şube görünümünü 9-A seçili açabilir;
 * sayfa yenilenince ya da bağlantı paylaşılınca da aynı ekran gelir.
 */
export function DersDagilimiSayfasi() {
  const [parametreler, setParametreler] = useSearchParams();
  const gorunum = gecerliGorunum(parametreler.get("gorunum"));

  const git: Git = (hedef) =>
    setParametreler((onceki) => {
      const yeni = new URLSearchParams(onceki);
      for (const [ad, deger] of Object.entries(hedef)) if (deger) yeni.set(ad, deger);
      return yeni;
    });

  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const atamalar = useAtamalar();
  const ozet = useDagilimOzeti();
  const ogretmenYukleri = useOgretmenYukleri();
  const sinifYukleri = useSinifYukleri();

  const sorgular = [ogretmenler, siniflar, dersler, atamalar, ozet];
  const hatali = sorgular.find((s) => s.isError);

  let icerik;
  if (hatali) {
    icerik = (
      <div className={sayfaStili.hataKutusu} role="alert">
        <p>{hataMetni(hatali.error)}</p>
        <Dugme tur="ikincil" onClick={() => sorgular.forEach((s) => s.refetch())}>
          Yeniden dene
        </Dugme>
      </div>
    );
  } else if (!ogretmenler.data || !siniflar.data || !dersler.data || !atamalar.data || !ozet.data) {
    icerik = <p>Yükleniyor...</p>;
  } else if (!ogretmenler.data.length || !siniflar.data.length || !dersler.data.length) {
    icerik = <OnKosullar ogretmen={ogretmenler.data.length} sinif={siniflar.data.length} ders={dersler.data.length} />;
  } else {
    const veri: DagilimVerisi = {
      ogretmenler: ogretmenler.data,
      siniflar: siniflar.data,
      dersler: dersler.data,
      atamalar: atamalar.data,
      ozet: ozet.data,
      ogretmenYukleri,
      sinifYukleri,
      ogretmen: new Map(ogretmenler.data.map((o) => [o.id, o])),
      sinif: new Map(siniflar.data.map((s) => [s.id, s])),
      ders: new Map(dersler.data.map((d) => [d.id, d])),
    };
    icerik = (
      <>
        <DurumOzeti veri={veri} git={git} />
        <Sekmeler etiket="Görünüm" sekmeler={SEKMELER} secili={gorunum} onSec={(g) => git({ gorunum: g })} idOneki="dagilim">
          {gorunum === "sube" && <SubeGorunumu veri={veri} sinifId={parametreler.get("sinif")} git={git} />}
          {gorunum === "ogretmen" && <OgretmenGorunumu veri={veri} git={git} />}
          {gorunum === "ders" && <DersGorunumu veri={veri} dersId={parametreler.get("ders")} git={git} />}
        </Sekmeler>
      </>
    );
  }

  return (
    <>
      <h1>Ders dağılımı</h1>
      <p className={sayfaStili.giris}>
        Her şubenin her dersine bir öğretmen seçin. Seçtiğiniz anda kaydedilir. Öğretmenlerin ve şubelerin
        yükü, program üretilirken yapılan kontrolle aynı hesapla gösterilir.
      </p>
      {icerik}
    </>
  );
}

function gecerliGorunum(deger: string | null): Gorunum {
  return deger === "ogretmen" || deger === "ders" ? deger : "sube";
}

function OnKosullar({ ogretmen, sinif, ders }: { ogretmen: number; sinif: number; ders: number }) {
  const eksikler = [
    !sinif && { yol: "/siniflar", metin: "Sınıfları ekleyin" },
    !ders && { yol: "/dersler", metin: "Dersleri ekleyin" },
    !ogretmen && { yol: "/ogretmenler", metin: "Öğretmenleri ekleyin" },
  ].filter((e): e is { yol: string; metin: string } => Boolean(e));
  return (
    <section aria-labelledby="dagilim-on-kosul" className={stil.bosDurum}>
      <h2 id="dagilim-on-kosul">Ders dağılımı için önce listeleri doldurun</h2>
      <p>Ders dağılımı şubeleri, dersleri ve öğretmenleri birbirine bağlar. Eksik olanlar:</p>
      <ul className={stil.eksikListesi}>
        {eksikler.map((e) => (
          <li key={e.yol}>
            <Link to={e.yol}>{e.metin}</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Sayfanın üstündeki durum: öğretmeni seçilmemiş dersler, kapasitesi aşılan öğretmen ve şubeler.
 * Sayılar sunucunun özetinden gelir. `aria-live`: bir öğretmen seçilip sayı azalınca ekran okuyucu
 * yeni durumu sırası gelince okur.
 */
function DurumOzeti({ veri, git }: { veri: DagilimVerisi; git: Git }) {
  const siniflar = turkceSirala(veri.siniflar, (s) => s.ad);
  const yuk = (s: Sinif) => veri.sinifYukleri.get(s.id);
  const eksikSubeler = siniflar.filter((s) => (yuk(s)?.ogretmensiz_atama ?? 0) > 0);
  const asanSubeler = siniflar.filter((s) => yuk(s)?.asim);
  const asanOgretmenler = veri.ozet.ogretmenler.filter((o) => o.asim).length;
  const eksik = veri.ozet.ogretmensiz_atama;

  const maddeler = [];
  if (eksik > 0) {
    maddeler.push(
      <li key="eksik" className={stil.durumUyari}>
        <span>
          <span aria-hidden="true">⚠ </span>
          <strong>{eksik} dersin öğretmeni seçilmedi</strong> ({eksikSubeler.length} şubede:{" "}
          {eksikSubeler.map((s) => s.ad).join(", ")}).
        </span>
        <Dugme tur="metin" onClick={() => git({ gorunum: "sube", sinif: eksikSubeler[0]?.id })}>
          İlk eksik şubeyi aç
        </Dugme>
      </li>,
    );
  }
  if (asanOgretmenler > 0) {
    maddeler.push(
      <li key="ogretmen" className={stil.durumHata}>
        <span>
          <span aria-hidden="true">⚠ </span>
          <strong>{asanOgretmenler} öğretmenin ders yükü kapasitesini aşıyor.</strong> Program bu haliyle üretilemez.
        </span>
        <Dugme tur="metin" onClick={() => git({ gorunum: "ogretmen" })}>
          Öğretmenlere göre gör
        </Dugme>
      </li>,
    );
  }
  if (asanSubeler.length > 0) {
    maddeler.push(
      <li key="sube" className={stil.durumHata}>
        <span>
          <span aria-hidden="true">⚠ </span>
          <strong>{asanSubeler.length} şubenin ders saati haftalık kapasiteyi aşıyor</strong> (
          {asanSubeler.map((s) => s.ad).join(", ")}).
        </span>
        <Dugme tur="metin" onClick={() => git({ gorunum: "sube", sinif: asanSubeler[0]?.id })}>
          Şubeyi aç
        </Dugme>
      </li>,
    );
  }
  if (veri.atamalar.length === 0) {
    maddeler.push(
      <li key="bos" className={stil.durumBilgi}>
        <span>
          Henüz hiçbir şubeye ders eklenmedi. En hızlı yol: her seviyenin derslerini seviye şablonunda bir kez
          girip o seviyedeki bütün şubelere uygulamak. <Link to="/seviye-sablonu">Seviye şablonunu aç</Link>
        </span>
      </li>,
    );
  } else if (maddeler.length === 0) {
    maddeler.push(
      <li key="tamam" className={stil.durumIyi}>
        <span>
          <span aria-hidden="true">✓ </span>
          Bütün derslerin öğretmeni seçildi; kapasitesi aşılan öğretmen ya da şube yok.
        </span>
      </li>,
    );
  }

  return (
    <section aria-label="Ders dağılımının durumu" aria-live="polite" className={stil.durum}>
      <ul>{maddeler}</ul>
    </section>
  );
}
