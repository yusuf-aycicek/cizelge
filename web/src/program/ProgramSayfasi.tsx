import { useQuery } from "@tanstack/react-query";
import { CalendarRange, Check, CircleX, LoaderCircle, Sparkles, TableProperties, WandSparkles } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { hataMetni } from "../api/hata";
import { MetinAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { Iskelet } from "../bilesenler/Iskelet";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Tablo } from "../bilesenler/Tablo";
import { useAtamalar, useDagilimOzeti } from "../dagilim/veri";
import { ogretmenKaynagi, sinifKaynagi } from "../listeler/kaynaklar";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { ASAMALAR, asamaBul, celiskileriGrupla, etkinMi, type Program } from "./aciklama";
import { KaliteOzeti } from "./KaliteOzeti";
import stil from "./Program.module.css";
import { sonProgram, useProgramlar, useProgramUret } from "./veri";

const SURELER = [
  { sn: 30, ad: "Hızlı", aciklama: "30 saniye. Denemek için." },
  { sn: 120, ad: "Dengeli", aciklama: "2 dakika. Çoğu okul için önerilen." },
  { sn: 300, ad: "Uzun", aciklama: "5 dakika. Büyük okullarda daha iyi sonuç." },
] as const;

const tarih = (iso: string) =>
  new Date(iso).toLocaleString("tr-TR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

const DURUM_ADLARI: Record<string, string> = {
  bekliyor: "Sırada",
  uretiliyor: "Hazırlanıyor",
  hazir: "Hazır",
  basarisiz: "Oluşturulamadı",
};

/**
 * Program sayfası: oluşturma, bekleme, sonuç ve önceki programlar.
 *
 * Ekran tamamen sunucudaki son programın durumundan türetilir (ayrı bir "adım" state'i yok):
 * etkin üretim varsa bekleme paneli, yoksa oluşturma kartı; son program başarısızsa nedeni, hazırsa
 * kalite özeti ve çizelge bağlantısı. Sayfa yenilense ya da başka sekmede açılsa da aynı ekran gelir.
 */
export function ProgramSayfasi() {
  const programlar = useProgramlar();
  const son = sonProgram(programlar.data);

  return (
    <>
      <SayfaBasligi ikon={CalendarRange} baslik="Program">
        Ders dağılımına ve kurallara göre, hiçbir öğretmenin ve şubenin aynı saatte iki yerde olmadığı haftalık
        programı oluşturun.
      </SayfaBasligi>
      {programlar.isPending ? (
        <Iskelet satir={5} kart />
      ) : programlar.isError ? (
        <div className={sayfaStili.hataKutusu} role="alert">
          <p>{hataMetni(programlar.error)}</p>
        </div>
      ) : (
        <>
          {son && etkinMi(son) ? (
            <BeklemePaneli program={son} />
          ) : (
            <>
              {son?.durum === "hazir" && <HazirPaneli program={son} />}
              {son?.durum === "basarisiz" && <BasarisizPaneli program={son} />}
              <OlusturKarti sira={(programlar.data?.length ?? 0) + 1} yeniden={Boolean(son)} />
            </>
          )}
          {(programlar.data?.length ?? 0) > 0 && <OncekiProgramlar programlar={programlar.data ?? []} />}
        </>
      )}
    </>
  );
}

// --- oluşturma -----------------------------------------------------------------------------

function OlusturKarti({ sira, yeniden }: { sira: number; yeniden: boolean }) {
  const ozet = useDagilimOzeti();
  const atamalar = useAtamalar();
  const uret = useProgramUret();
  const bildirim = useBildirim();
  const [ad, setAd] = useState(`Program ${sira}`);
  const [sure, setSure] = useState<number>(120);

  const asanOgretmen = ozet.data?.ogretmenler.filter((o) => o.asim).length ?? 0;
  const asanSube = ozet.data?.siniflar.filter((s) => s.asim).length ?? 0;
  const ogretmensiz = ozet.data?.ogretmensiz_atama ?? 0;
  const atamaYok = atamalar.data?.length === 0;
  const engeller = [
    atamaYok && { metin: "Henüz hiçbir şubeye ders atanmadı.", yol: "/ders-dagilimi", baglanti: "Ders dağılımına git" },
    ogretmensiz > 0 && { metin: `${ogretmensiz} dersin öğretmeni seçilmedi.`, yol: "/ders-dagilimi", baglanti: "Öğretmenleri seç" },
    asanOgretmen > 0 && {
      metin: `${asanOgretmen} öğretmenin ders yükü müsait olduğu saatlerden fazla.`,
      yol: "/ders-dagilimi?gorunum=ogretmen",
      baglanti: "Öğretmenlere göre gör",
    },
    asanSube > 0 && { metin: `${asanSube} şubenin ders saati haftalık kapasiteyi aşıyor.`, yol: "/ders-dagilimi", baglanti: "Şubelere göre gör" },
  ].filter((e): e is { metin: string; yol: string; baglanti: string } => Boolean(e));
  const hazirlaniyor = ozet.isPending || atamalar.isPending;

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    uret.mutate(
      { ad: ad.trim() || `Program ${sira}`, sure_siniri_sn: sure },
      { onError: (hata) => bildirim("hata", hataMetni(hata)) },
    );
  }

  return (
    <section aria-labelledby="olustur-baslik" className={sayfaStili.kart}>
      <h2 id="olustur-baslik">{yeniden ? "Yeni program oluştur" : "Programı oluştur"}</h2>
      {engeller.length > 0 ? (
        <div className={stil.engeller} role="note">
          <p>
            <strong>Bu sorunlar düzeltilmeden program oluşturulamaz:</strong>
          </p>
          <ul>
            {engeller.map((e) => (
              <li key={e.metin}>
                {e.metin} <Link to={e.yol}>{e.baglanti}</Link>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        !hazirlaniyor && (
          <p className={stil.hazirNotu}>
            <Check aria-hidden="true" /> Ders dağılımı tamam: bütün derslerin öğretmeni seçildi, kapasite aşımı yok.
          </p>
        )
      )}
      <form onSubmit={gonder} className={stil.olusturFormu}>
        <div className={stil.adAlani}>
          <MetinAlani etiket="Programın adı" value={ad} onChange={(o) => setAd(o.target.value)} maxLength={200} />
        </div>
        <fieldset className={stil.sureler}>
          <legend>Ne kadar uğraşsın?</legend>
          <div className={stil.sureSecenekleri}>
            {SURELER.map((s) => (
              <label key={s.sn} className={stil.sure}>
                <input type="radio" name="sure" value={s.sn} checked={sure === s.sn} onChange={() => setSure(s.sn)} />
                <span>
                  <strong>{s.ad}</strong>
                  <span className={stil.sureAciklama}>{s.aciklama}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <Dugme
          type="submit"
          ikon={<WandSparkles />}
          disabled={engeller.length > 0 || hazirlaniyor}
          yukleniyor={uret.isPending}
          yukleniyorMetni="Gönderiliyor..."
          className={stil.olusturDugmesi}
        >
          Programı oluştur
        </Dugme>
      </form>
    </section>
  );
}

// --- bekleme -------------------------------------------------------------------------------

/**
 * Şu anki zaman, `aralikMs`'de bir güncellenir. Effect'in doğru kullanım yeri: React'in dışındaki
 * bir şeyle (saatle) senkronizasyon. Temizleme fonksiyonu zamanlayıcıyı durdurur; bileşen kalkınca
 * ya da `etkin` false olunca saat işlemez.
 */
function useSimdi(etkin: boolean, aralikMs = 500): number {
  const [simdi, setSimdi] = useState(() => Date.now());
  useEffect(() => {
    if (!etkin) return;
    const zamanlayici = window.setInterval(() => setSimdi(Date.now()), aralikMs);
    return () => window.clearInterval(zamanlayici);
  }, [etkin, aralikMs]);
  return simdi;
}

function BeklemePaneli({ program }: { program: Program }) {
  const simdi = useSimdi(true);
  const { sira, ilerleme, gecenSn } = asamaBul(program, simdi);
  const kalan = Math.max(0, Math.ceil(program.sure_siniri_sn - gecenSn));
  const simdikiAsama = ASAMALAR[sira];

  return (
    <section aria-labelledby="bekleme-baslik" className={stil.bekleme}>
      <HazirlanmaAnimasyonu />
      <div className={stil.beklemeMetni}>
        <h2 id="bekleme-baslik">Program hazırlanıyor</h2>
        <p className={stil.beklemeAciklama}>
          “{program.ad}” için {program.durum === "bekliyor" ? "sıra bekleniyor" : `en fazla ${kalan} saniye kaldı`}. Süre
          dolduğunda bulunan en iyi program kaydedilir. Bu sayfadan ayrılabilirsiniz; üretim arka planda sürer.
        </p>
        <div
          className={stil.cubuk}
          role="progressbar"
          aria-label="Ayrılan sürenin kullanılan kısmı"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(ilerleme * 100)}
        >
          <div className={stil.cubukDolgu} style={{ width: `${Math.max(3, ilerleme * 100)}%` }} />
        </div>
        <ol className={stil.asamalar}>
          {ASAMALAR.slice(0, 4).map((a, i) => {
            const durum = i < sira ? "bitti" : i === sira ? "suruyor" : "sirada";
            return (
              <li key={a.anahtar} className={stil[durum]} aria-current={durum === "suruyor" ? "step" : undefined}>
                <span className={stil.asamaIsareti} aria-hidden="true">
                  {durum === "bitti" ? <Check /> : durum === "suruyor" ? <LoaderCircle className={stil.donen} /> : null}
                </span>
                <span>
                  <span className={stil.asamaAdi}>{a.ad}</span>
                  {durum === "suruyor" && <span className={stil.asamaAciklama}>{a.aciklama}</span>}
                </span>
              </li>
            );
          })}
        </ol>
        {/* Ekran okuyucu her saniye değil, yalnızca aşama değişince duyar. */}
        <p className="gorunmez" role="status">
          {simdikiAsama?.ad}
        </p>
      </div>
    </section>
  );
}

/** Sakin bir döngü: küçük bir haftalık çizelgenin hücreleri sırayla dolup boşalır. Yalnızca süs. */
function HazirlanmaAnimasyonu() {
  return (
    <div className={stil.animasyon} aria-hidden="true">
      {Array.from({ length: 30 }, (_, i) => (
        <span key={i} className={stil.animasyonHucresi} style={{ animationDelay: `${((i % 5) * 6 + Math.floor(i / 5)) * 80}ms` }} />
      ))}
    </div>
  );
}

// --- sonuç ---------------------------------------------------------------------------------

function HazirPaneli({ program }: { program: Program }) {
  return (
    <section aria-labelledby="hazir-baslik" className={stil.hazir}>
      <div className={stil.hazirUst}>
        <Sparkles aria-hidden="true" className={stil.hazirIkonu} />
        <div>
          <h2 id="hazir-baslik">“{program.ad}” hazır</h2>
          <p className={stil.hazirZaman}>{program.bitis && tarih(program.bitis)}</p>
        </div>
        <Link to={`/program/${program.id}`} className={stil.cizelgeBaglantisi}>
          <TableProperties aria-hidden="true" /> Haftalık çizelgeyi aç
        </Link>
      </div>
      <KaliteOzeti program={program} baslikDuzeyi={3} />
    </section>
  );
}

function BasarisizPaneli({ program }: { program: Program }) {
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const gruplar = celiskileriGrupla(program.celiskiler ?? []);

  // İlgili kimlikleri (şube, öğretmen) düzeltilecek sayfaya bağlantıya çevir.
  const baglantilar = (ilgili: readonly string[] = []) =>
    ilgili.flatMap((id) => {
      const s = siniflar.data?.find((x) => x.id === id);
      if (s) return [{ id, ad: s.ad, yol: `/ders-dagilimi?gorunum=sube&sinif=${id}` }];
      const o = ogretmenler.data?.find((x) => x.id === id);
      if (o) return [{ id, ad: o.ad, yol: "/ders-dagilimi?gorunum=ogretmen" }];
      return [];
    });

  return (
    <section aria-labelledby="basarisiz-baslik" className={stil.basarisiz}>
      <div className={stil.hazirUst}>
        <CircleX aria-hidden="true" className={stil.basarisizIkonu} />
        <div>
          <h2 id="basarisiz-baslik">“{program.ad}” oluşturulamadı</h2>
          <p className={stil.hazirZaman}>Aşağıdaki sorunları düzeltip yeniden deneyin.</p>
        </div>
      </div>
      {gruplar.length > 0 ? (
        gruplar.map((g) => (
          <div key={g.tur} className={stil.celiskiGrubu}>
            <h3>{g.baslik}</h3>
            <ul>
              {g.maddeler.map((m, i) => (
                <li key={i}>
                  {m.mesaj}
                  {baglantilar(m.ilgili).length > 0 && (
                    <span className={stil.ilgili}>
                      {" "}
                      {baglantilar(m.ilgili).map((b) => (
                        <Link key={b.id} to={b.yol}>
                          {b.ad}
                        </Link>
                      ))}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))
      ) : (
        <ul className={stil.celiskiGrubu}>
          {(program.hata_mesaji ?? "Program oluşturulamadı.").split("\n").map((satir) => (
            <li key={satir}>{satir}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function OncekiProgramlar({ programlar }: { programlar: Program[] }) {
  const sirali = [...programlar].reverse();
  return (
    <section aria-labelledby="onceki-baslik" className={stil.onceki}>
      <h2 id="onceki-baslik">Programlar</h2>
      <Tablo<Program>
        baslik="Programlar"
        satirlar={sirali}
        satirAnahtari={(p) => p.id}
        sutunlar={[
          { baslik: "Ad", hucre: (p) => p.ad },
          {
            baslik: "Durum",
            hucre: (p) => <span className={`${stil.durumRozeti} ${stil[`durum_${p.durum}`] ?? ""}`}>{DURUM_ADLARI[p.durum] ?? p.durum}</span>,
          },
          { baslik: "Oluşturma", hucre: (p) => tarih(p.olusturma) },
          { baslik: "Süre", hucre: (p) => (p.sure_sn != null ? `${Math.round(p.sure_sn)} sn` : "") },
          {
            baslik: "Çizelge",
            baslikGizli: true,
            hizala: "sag",
            hucre: (p) => (p.durum === "hazir" ? <Link to={`/program/${p.id}`}>Çizelgeyi aç</Link> : null),
          },
        ]}
      />
    </section>
  );
}

