import { useQuery } from "@tanstack/react-query";
import {
  CalendarRange, Check, CircleAlert, CircleX, Hourglass, LoaderCircle, RotateCcw, Sparkles, TableProperties, WandSparkles,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { hataMetni } from "../api/hata";
import { MetinAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { Iskelet } from "../bilesenler/Iskelet";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Tablo } from "../bilesenler/Tablo";
import { useAtamalar } from "../dagilim/veri";
import { ogretmenKaynagi, sinifKaynagi } from "../listeler/kaynaklar";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { ASAMALAR, asamaBul, celiskileriGrupla, etkinMi, sureMetni, type Celiski, type Program } from "./aciklama";
import { KaliteOzeti } from "./KaliteOzeti";
import stil from "./Program.module.css";
import { sonHazirProgram, sonProgram, useOnKontrol, useProgramlar, useProgramUret } from "./veri";

const SURELER = [
  { sn: 30, ad: "Hızlı", aciklama: "30 saniye. Denemek için." },
  { sn: 120, ad: "Dengeli", aciklama: "2 dakika. Çoğu okul için önerilen." },
  { sn: 300, ad: "Uzun", aciklama: "5 dakika. Büyük okullarda daha iyi sonuç." },
] as const;

/** "Süre yetmedi"den sonra önerilen daha uzun süreler (en uzun seçenekten sonra 10 dakika). */
const YENIDEN_DENEME_SURELERI = [...SURELER.map((s) => s.sn), 600];

/**
 * Bu kadar ve daha çok şubesi olan okulda "Hızlı" (30 sn) yetmeyebilir. Ölçüm (docs/olcumler.md,
 * "İki aşamalı çözüm"): gerçekçi sette (24 şube, bloklu) ilk program her tohumda 9 sn içinde; büyük
 * sette (40 şube) 10-25 sn'de, yani 30 sn'ye yakın (yük altında ya da daha yavaş bir sunucuda aşar).
 * Eşik ikisinin arasında, ilk programın sürenin yarısını (15 sn) geçtiği yerde.
 */
export const HIZLI_YETMEYEBILIR_SUBE = 30;

export const dahaUzunSure = (sn: number) => YENIDEN_DENEME_SURELERI.find((s) => s > sn);

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
 * etkin üretim varsa bekleme paneli, yoksa oluşturma kartı. Hazır bir program varsa (en yenisi) o öne
 * çıkar; ondan sonraki deneme başarısızsa yalnızca sade, açılabilir bir uyarıdır (kullanıcının elinde
 * çalışan bir program var). Hiç hazır program yoksa başarısız denemenin nedeni büyük panelde.
 * Sayfa yenilense ya da başka sekmede açılsa da aynı ekran gelir.
 */
export function ProgramSayfasi() {
  const programlar = useProgramlar();
  const son = sonProgram(programlar.data);
  const hazir = sonHazirProgram(programlar.data);

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
              {hazir && <HazirPaneli program={hazir} />}
              {son?.durum === "basarisiz" &&
                (hazir ? <SonDenemeUyarisi program={son} /> : <BasarisizPaneli program={son} />)}
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
  // Engeller, üretimdeki ön kontrolün kendisinden gelir (ayrı bir istemci hesabı yok): dağılım
  // özeti "tamam" deyip üretimin ön kontrolde takılması bu yüzden olamaz.
  const onKontrol = useOnKontrol();
  const atamalar = useAtamalar();
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const subeSayisi = siniflar.data?.length ?? 0;
  const uret = useProgramUret();
  const bildirim = useBildirim();
  const [ad, setAd] = useState(`Program ${sira}`);
  const [sure, setSure] = useState<number>(120);

  const atamaYok = atamalar.data?.length === 0;
  const celiskiler = onKontrol.data?.celiskiler ?? [];
  const engelVar = atamaYok || celiskiler.length > 0 || onKontrol.isError;
  const hazirlaniyor = onKontrol.isPending || atamalar.isPending;

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
      {onKontrol.isError ? (
        <div className={stil.engeller} role="note">
          <p>Program oluşturulmadan önceki kontrol yapılamadı: {hataMetni(onKontrol.error)}</p>
        </div>
      ) : atamaYok ? (
        <div className={stil.engeller} role="note">
          <p>
            <strong>Henüz hiçbir şubeye ders atanmadı.</strong> <Link to="/ders-dagilimi">Ders dağılımına git</Link>
          </p>
        </div>
      ) : celiskiler.length > 0 ? (
        <div className={stil.engeller} role="note">
          <p>
            <strong>Bu sorunlar düzeltilmeden program oluşturulamaz:</strong>
          </p>
          <CeliskiGruplari celiskiler={celiskiler} />
        </div>
      ) : (
        !hazirlaniyor && (
          <p className={stil.hazirNotu}>
            <Check aria-hidden="true" /> Ön kontrol tamam: bütün derslerin öğretmeni seçildi; dersler, öğretmenlerin
            müsaitliğine ve kurallara (özel ayarlar dahil) sığıyor.
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
                  {s.sn === 30 && subeSayisi >= HIZLI_YETMEYEBILIR_SUBE && (
                    <span className={stil.sureUyarisi}>
                      Okulunuzda {subeSayisi} şube var; bu süre program bulmaya yetmeyebilir.
                    </span>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <Dugme
          type="submit"
          ikon={<WandSparkles />}
          disabled={engelVar || hazirlaniyor}
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

/**
 * Çelişkiler türlerine göre gruplu; ilgili şube ve öğretmenler düzeltilecek sayfaya bağlantı.
 * Hem oluşturmadan önceki ön kontrol hem başarısız üretimin nedeni bununla gösterilir.
 */
function CeliskiGruplari({ celiskiler }: { celiskiler: readonly Celiski[] }) {
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const gruplar = celiskileriGrupla(celiskiler);

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
    <>
      {gruplar.map((g) => (
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
      ))}
    </>
  );
}

function BasarisizPaneli({ program }: { program: Program }) {
  const sureYetmedi = program.cozum_durumu === "bilinmiyor";
  return (
    <section aria-labelledby="basarisiz-baslik" className={stil.basarisiz}>
      <div className={stil.hazirUst}>
        <CircleX aria-hidden="true" className={stil.basarisizIkonu} />
        <div>
          <h2 id="basarisiz-baslik">“{program.ad}” oluşturulamadı</h2>
          <p className={stil.hazirZaman}>
            {sureYetmedi ? "Seçilen süre yetmedi." : "Aşağıdaki sorunları düzeltip yeniden deneyin."}
          </p>
        </div>
      </div>
      <BasarisizNedeni program={program} />
    </section>
  );
}

/**
 * Süre içinde ne program bulundu ne de olmadığı kanıtlandı (`bilinmiyor`). Bu bir veri hatası
 * değil: kural çelişkisi görülmedi, daha uzun süre büyük olasılıkla yeter. Tek tıkla aynı adla, bir
 * sonraki uzun süreyle (ve aynı temel programla) yeniden üretilir.
 */
function SureYetmedi({ program }: { program: Program }) {
  const uret = useProgramUret();
  const bildirim = useBildirim();
  const yeni = dahaUzunSure(program.sure_siniri_sn);
  return (
    <div className={stil.sureYetmedi}>
      <p>
        <Hourglass aria-hidden="true" className={stil.sureYetmediIkonu} />
        <span>
          <strong>Bu süre okulunuz için yetmedi.</strong> {sureMetni(program.sure_siniri_sn)} içinde kurallara uyan bir
          program bulunamadı; kuralların çeliştiği de görülmedi. Daha uzun bir süreyle yeniden deneyin.
        </span>
      </p>
      {yeni && (
        <Dugme
          ikon={<RotateCcw />}
          yukleniyor={uret.isPending}
          yukleniyorMetni="Gönderiliyor..."
          onClick={() =>
            uret.mutate(
              { ad: program.ad, sure_siniri_sn: yeni, ...(program.temel_program_id ? { temel_program_id: program.temel_program_id } : {}) },
              { onError: (hata) => bildirim("hata", hataMetni(hata)) },
            )
          }
        >
          {sureMetni(yeni)} ile yeniden dene
        </Dugme>
      )}
    </div>
  );
}

/** Başarısız üretimin nedeni: çelişkiler gruplu; yoksa sunucunun mesajı satır satır. */
function BasarisizNedeni({ program }: { program: Program }) {
  if (program.cozum_durumu === "bilinmiyor") return <SureYetmedi program={program} />;
  return (program.celiskiler ?? []).length > 0 ? (
    <CeliskiGruplari celiskiler={program.celiskiler ?? []} />
  ) : (
    <ul className={stil.celiskiGrubu}>
      {(program.hata_mesaji ?? "Program oluşturulamadı.").split("\n").map((satir) => (
        <li key={satir}>{satir}</li>
      ))}
    </ul>
  );
}

/**
 * Hazır programdan sonraki başarısız deneme: sade bir uyarı, nedeni açılır (<details>). Doğal
 * <details>/<summary> klavyeyle açılır kapanır; ekran okuyucu "daraltılmış/genişletilmiş" der.
 */
function SonDenemeUyarisi({ program }: { program: Program }) {
  return (
    <section aria-labelledby="son-deneme-baslik" className={stil.sonDeneme}>
      <p id="son-deneme-baslik" className={stil.sonDenemeBaslik}>
        <CircleAlert aria-hidden="true" />
        <span>
          Son deneme “{program.ad}” oluşturulamadı{program.bitis ? ` (${tarih(program.bitis)})` : ""}. Hazır program
          yukarıda;{" "}
          {program.cozum_durumu === "bilinmiyor"
            ? "seçilen süre yetmedi, daha uzun bir süreyle yeniden deneyebilirsiniz."
            : "yeni bir deneme için aşağıdaki sorunları düzeltin."}
        </span>
      </p>
      <details className={stil.sonDenemeAyrinti}>
        <summary>Nedenini göster</summary>
        <BasarisizNedeni program={program} />
      </details>
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
          // Uzun ad satır kırar; tablo dar alanda (800 px) yana kaymasın.
          { baslik: "Ad", hucre: (p) => <span className={stil.sarar}>{p.ad}</span> },
          {
            baslik: "Durum",
            hucre: (p) => <span className={`${stil.durumRozeti} ${stil[`durum_${p.durum}`] ?? ""}`}>{DURUM_ADLARI[p.durum] ?? p.durum}</span>,
          },
          {
            // Oluşturma zamanı ve süre tek sütunda, alt alta: ayrı sütun dar ekranda tabloyu taşırıyordu.
            baslik: "Oluşturma",
            hucre: (p) => (
              <>
                {tarih(p.olusturma)}
                {p.sure_sn != null && <span className={stil.ikincilSatir}>{sureMetni(p.sure_sn)} sürdü</span>}
              </>
            ),
          },
          {
            baslik: "Çizelge",
            baslikGizli: true,
            hizala: "sag",
            hucre: (p) => (p.durum === "hazir" ? <Link to={`/program/${p.id}`} className={stil.tekSatir}>Çizelgeyi aç</Link> : null),
          },
        ]}
      />
    </section>
  );
}

