import { useQuery } from "@tanstack/react-query";
import { BosDurum } from "../bilesenler/BosDurum";
import {
  ArrowRight,
  BookOpen,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  CircleDashed,
  Clock,
  GraduationCap,
  Plus,
  Radio,
  School,
  type LucideIcon,
} from "lucide-react";
import type { CSSProperties } from "react";
import { Link } from "react-router";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import { Dugme } from "../bilesenler/Dugme";
import { Iskelet } from "../bilesenler/Iskelet";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { useAtamalar, useDagilimOzeti, type DagilimOzeti } from "../dagilim/veri";
import { dersRenkStili } from "../dersler/dersRengi";
import { useBen } from "../kimlik/oturum";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi } from "../listeler/kaynaklar";
import { YAYIN } from "../paylasim/YayinSayfasi";
import { GUN_KISA_ADLARI } from "../program/aciklama";
import { cizelgeHucreleri, hucreAnahtari } from "../program/cizelge";
import { sonHazirProgram, sonProgram, useProgramlar, useYerlesimler } from "../program/veri";
import { IlerlemeHalkasi } from "./IlerlemeHalkasi";
import { kurulumDurumu, type AdimDurumu, type KurulumDurumu } from "./kurulum";
import { SayacSayi } from "./SayacSayi";
import { ilkAd, selam, tarihMetni } from "./selam";
import pano from "./Pano.module.css";
import stil from "./Sayfa.module.css";

const DURUM_IKONU: Record<AdimDurumu, LucideIcon> = {
  tamam: CircleCheck,
  eksik: CircleAlert,
  bekliyor: CircleDashed,
  "istege-bagli": CircleDashed,
};
const DURUM_ADI: Record<AdimDurumu, string> = {
  tamam: "Tamam",
  eksik: "Eksik",
  bekliyor: "Bekliyor",
  "istege-bagli": "İsteğe bağlı",
};

const tarihSaat = (iso: string) =>
  new Date(iso).toLocaleString("tr-TR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

/**
 * Ana sayfa: günün saatine göre selam ve bugünün tarihi; sayı kartları (sıfırdan sayarak gelir);
 * yayındaki program, bir şubenin haftası (küçük çizelge) ve öğretmenlerin yükü; açılıp kapanan
 * kurulum listesi ve sistem durumu.
 *
 * Halka ve kontrol listesi aynı hesaptan gelir (`kurulumDurumu`). Öğretmensiz ders sayısı ve
 * öğretmen yükleri, ders dağılımı sayfasıyla aynı sunucu özetinden okunur (ADR 0015).
 */
export function AnaSayfa() {
  const ben = useBen().data;
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const atamalar = useAtamalar();
  const ozet = useDagilimOzeti();
  const programlar = useProgramlar();
  const yayin = useQuery({ queryKey: YAYIN, queryFn: () => cagir(api.GET("/api/ders-programi/yayin")) });
  const sonHazir = sonHazirProgram(programlar.data);

  const hazir = ben && ogretmenler.data && siniflar.data && dersler.data && atamalar.data && ozet.data && programlar.data;
  const kurulum = hazir
    ? kurulumDurumu({
        gunSayisi: ben.okul.gun_sayisi,
        gunlukDersSaati: ben.okul.gunluk_ders_saati,
        ogretmen: ogretmenler.data.length,
        sinif: siniflar.data.length,
        ders: dersler.data.length,
        atama: atamalar.data.length,
        ogretmensizAtama: ozet.data.ogretmensiz_atama,
        sonProgram: sonProgram(programlar.data),
        sonHazirProgram: sonHazir,
      })
    : null;
  const toplamSaat = atamalar.data?.reduce((t, a) => t + a.haftalik_saat, 0) ?? 0;
  // Küçük çizelgede yayındaki program; yayın yoksa en son hazır program.
  const gosterilen = yayin.data?.program_id
    ? { id: yayin.data.program_id, ad: yayin.data.program_adi }
    : sonHazir
      ? { id: sonHazir.id, ad: sonHazir.ad }
      : null;
  const simdi = new Date();

  return (
    <>
      <SayfaBasligi
        etiket={tarihMetni(simdi).toLocaleUpperCase("tr-TR")}
        baslik={ben ? `${selam(simdi)}, ${ilkAd(ben.kullanici.ad)}` : selam(simdi)}
        eylemler={
          <span className={pano.eylemler}>
            {sonHazir && (
              <Link to={`/program/${sonHazir.id}`} className={pano.ikincilEylem}>
                Son programı aç <ArrowRight aria-hidden="true" />
              </Link>
            )}
            <Link to="/program#olustur" className={pano.anaEylem}>
              <Plus aria-hidden="true" /> Yeni program
            </Link>
          </span>
        }
      >
        {ben?.okul.ad}
        {kurulum && kurulum.yuzde < 100 && " · Aşağıdaki adımları tamamlayınca programı üretebilirsiniz."}
        {kurulum && kurulum.yuzde === 100 && " · Kurulum tamam ve programınız hazır."}
      </SayfaBasligi>

      {!kurulum ? (
        <Iskelet satir={4} kart />
      ) : (
        <>
          <ul className={pano.sayilar} aria-label="Okulunuz sayılarla">
            <SayiKarti ikon={GraduationCap} sayi={ogretmenler.data?.length ?? 0} ad="Öğretmen" yol="/ogretmenler" sira={1} />
            <SayiKarti ikon={School} sayi={siniflar.data?.length ?? 0} ad="Şube" yol="/siniflar" sira={2} />
            <SayiKarti ikon={BookOpen} sayi={dersler.data?.length ?? 0} ad="Ders" yol="/dersler" sira={3} />
            <SayiKarti ikon={Clock} sayi={toplamSaat} ad="Haftalık ders saati" yol="/ders-dagilimi" sira={4} />
          </ul>

          <div className={pano.izgara}>
            <div className={pano.anaSutun}>
              {gosterilen ? (
                <MiniCizelge programId={gosterilen.id} programAdi={gosterilen.ad} />
              ) : (
                <section className={`${stil.kart} ${pano.bosKart}`} aria-labelledby="mini-baslik">
                  <h2 id="mini-baslik">Haftalık program</h2>
                  <BosDurum cizim="takvim" boyut="kucuk" baslikDuzeyi={3} baslik="Henüz hazır bir program yok"
                    eylem={
                      <Link to="/program" className={pano.metinBaglanti}>
                        Program sayfasına git <ArrowRight aria-hidden="true" />
                      </Link>
                    }>
                    <p>Kurulum adımları bitince programı oluşturun; haftası burada görünür.</p>
                  </BosDurum>
                </section>
              )}
              <KurulumListesi kurulum={kurulum} />
            </div>
            <div className={pano.yanSutun}>
              <YayinKarti durum={yayin.data} yukleniyor={yayin.isPending} />
              <YukKarti ozet={ozet.data} adlar={new Map((ogretmenler.data ?? []).map((o) => [o.id, o.ad]))} />
              <SistemDurumu />
            </div>
          </div>
        </>
      )}
    </>
  );
}

function SayiKarti({ ikon: Ikon, sayi, ad, yol, sira }: { ikon: LucideIcon; sayi: number; ad: string; yol: string; sira: number }) {
  return (
    <li>
      <Link to={yol} className={pano.sayiKarti} style={{ "--sira": sira } as CSSProperties}>
        <Ikon aria-hidden="true" className={pano.sayiIkonu} />
        <span className={pano.sayi}>
          <SayacSayi hedef={sayi} />
        </span>
        <span className={pano.sayiAdi}>{ad}</span>
      </Link>
    </li>
  );
}

/** Kurulum adımları: kurulum bitmişse kapalı gelir (özetinde halka ve "6/6"), bitmemişse açık. */
function KurulumListesi({ kurulum }: { kurulum: KurulumDurumu }) {
  return (
    <details className={`${stil.kart} ${pano.kurulum}`} open={kurulum.yuzde < 100}>
      <summary className={pano.kurulumOzeti}>
        <IlerlemeHalkasi yuzde={kurulum.yuzde} tamamlanan={kurulum.tamamlanan} gereken={kurulum.gereken} />
        <span className={pano.kurulumBasligi}>
          <strong>Kurulum adımları</strong>
          <span>
            {kurulum.tamamlanan}/{kurulum.gereken} adım tamam
          </span>
        </span>
        <ChevronDown aria-hidden="true" className={pano.acKapa} />
      </summary>
      <section aria-label="Kurulum adımları">
        <ol className={pano.adimlar}>
          {kurulum.adimlar.map((a) => {
            const Ikon = DURUM_IKONU[a.durum];
            return (
              <li key={a.anahtar}>
                <Link to={a.yol} className={`${pano.adim} ${pano[a.durum.replace("-", "")] ?? ""}`}>
                  <Ikon aria-hidden="true" className={pano.adimIkonu} />
                  <span className={pano.adimMetni}>
                    <span className={pano.adimAdi}>{a.ad}</span>
                    <span className={pano.adimAyrinti}>{a.ayrinti}</span>
                  </span>
                  <span className="gorunmez">({DURUM_ADI[a.durum]})</span>
                  <ChevronRight aria-hidden="true" className={pano.ok} />
                </Link>
              </li>
            );
          })}
        </ol>
      </section>
    </details>
  );
}

type YayinDurumu = { program_id: string | null; program_adi: string; yayin_zamani: string; uyarilar: string[] } | null | undefined;

/** Yayındaki program: öğretmenlerin paylaşım linkinden gördüğü. Yoksa nasıl yayınlanacağı. */
function YayinKarti({ durum, yukleniyor }: { durum: YayinDurumu; yukleniyor: boolean }) {
  return (
    <section className={`${stil.kart} ${pano.yayinKarti} ${durum ? pano.yayinda : ""}`} aria-labelledby="yayin-baslik">
      <p className={pano.kartEtiketi}>
        <Radio aria-hidden="true" /> {durum ? "YAYINDA" : "YAYIN"}
      </p>
      <h2 id="yayin-baslik">{yukleniyor ? "Yayın durumu" : durum ? durum.program_adi : "Yayında program yok"}</h2>
      {durum ? (
        <>
          <p className={pano.soluk}>{tarihSaat(durum.yayin_zamani)} tarihinde yayınlandı. Öğretmenler linkten bu programı görür.</p>
          {durum.uyarilar.map((u) => (
            <p key={u} className={pano.uyari}>
              {u}
            </p>
          ))}
        </>
      ) : (
        !yukleniyor && <p className={pano.soluk}>Hazır bir programı yayınlayın; öğretmenler kendi programını telefonundan görsün.</p>
      )}
      <Link to="/yayin" className={pano.metinBaglanti}>
        Yayın ve paylaşım <ArrowRight aria-hidden="true" />
      </Link>
    </section>
  );
}

/** Programın ilk şubesinin haftası, küçük renkli bloklarla. Tamamı çizelge sayfasında. */
function MiniCizelge({ programId, programAdi }: { programId: string; programAdi: string }) {
  const ben = useBen().data;
  const yerlesimler = useYerlesimler(programId, true);
  const atamalar = useAtamalar();
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const sube = [...(siniflar.data ?? [])].sort((a, b) => a.ad.localeCompare(b.ad, "tr", { numeric: true }))[0];
  const gunSayisi = ben?.okul.gun_sayisi ?? 5;
  const saatSayisi = ben?.okul.gunluk_ders_saati ?? 8;
  const dersMap = new Map((dersler.data ?? []).map((d) => [d.id, d]));
  const hucreler = sube && yerlesimler.data && atamalar.data ? cizelgeHucreleri(yerlesimler.data, atamalar.data, "sube", sube.id) : null;

  return (
    <section className={`${stil.kart} ${pano.miniKart}`} aria-labelledby="mini-baslik">
      <div className={pano.miniUst}>
        <div>
          <p className={pano.kartEtiketi}>HAFTALIK PROGRAM</p>
          <h2 id="mini-baslik">
            {sube?.ad ?? "Şube"} <span className={pano.soluk}>· {programAdi}</span>
          </h2>
        </div>
        <Link to={`/program/${programId}`} className={pano.metinBaglanti}>
          Tamamını aç <ArrowRight aria-hidden="true" />
        </Link>
      </div>
      {!hucreler ? (
        <Iskelet satir={3} />
      ) : (
        <div
          className={pano.mini}
          style={{ "--gun": gunSayisi } as CSSProperties}
          role="img"
          aria-label={`${sube?.ad} şubesinin haftası: ${hucreler.size} ders saati. Tamamı için "Tamamını aç".`}
        >
          <span aria-hidden="true" />
          {GUN_KISA_ADLARI.slice(0, gunSayisi).map((g) => (
            <span key={g} className={pano.miniGun} aria-hidden="true">
              {g}
            </span>
          ))}
          {Array.from({ length: saatSayisi }, (_, s) => [
            <span key={`s${s}`} className={pano.miniSaat} aria-hidden="true">
              {s + 1}
            </span>,
            ...Array.from({ length: gunSayisi }, (_, g) => {
              const a = hucreler.get(hucreAnahtari(g, s));
              const ders = a ? dersMap.get(a.ders_id) : undefined;
              return a ? (
                <span key={g} className={pano.miniDers} style={dersRenkStili(ders?.renk)} aria-hidden="true">
                  {ders?.kisa_ad || ders?.ad}
                </span>
              ) : (
                <span key={g} className={pano.miniBos} aria-hidden="true" />
              );
            }),
          ])}
        </div>
      )}
    </section>
  );
}

/** Öğretmenlerin haftalık yükü: en yüklü beşi, derse girebileceği saate göre çubukla. */
function YukKarti({ ozet, adlar }: { ozet: DagilimOzeti | undefined; adlar: Map<string, string> }) {
  const sirali = [...(ozet?.ogretmenler ?? [])].filter((o) => o.ders_saati > 0).sort((a, b) => b.ders_saati - a.ders_saati);
  const ilkler = sirali.slice(0, 5);
  return (
    <section className={stil.kart} aria-labelledby="yuk-baslik">
      <p className={pano.kartEtiketi}>ÖĞRETMEN YÜKÜ</p>
      <h2 id="yuk-baslik">Haftalık ders saatleri</h2>
      {ilkler.length === 0 ? (
        <p className={pano.soluk}>Henüz ders atanmadı.</p>
      ) : (
        <ul className={pano.yukler}>
          {ilkler.map((o) => {
            const oran = o.kullanilabilir_saat > 0 ? Math.min(1, o.ders_saati / o.kullanilabilir_saat) : 1;
            return (
              <li key={o.ogretmen_id} className={o.asim ? pano.asim : undefined}>
                <span className={pano.yukAdi}>{adlar.get(o.ogretmen_id) ?? "Öğretmen"}</span>
                <span className={pano.yukSaati}>
                  {o.ders_saati} / {o.kullanilabilir_saat} saat
                </span>
                <span className={pano.yukCubugu} aria-hidden="true">
                  <span style={{ "--oran": oran } as CSSProperties} />
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {sirali.length > ilkler.length && <p className={pano.soluk}>ve {sirali.length - ilkler.length} öğretmen daha</p>}
      <Link to="/ders-dagilimi?gorunum=ogretmen" className={pano.metinBaglanti}>
        Ders dağılımı <ArrowRight aria-hidden="true" />
      </Link>
    </section>
  );
}

/**
 * useQuery: "bu veriyi istiyorum" der; çekme, yükleniyor durumu, hata, önbellek ve yeniden
 * deneme TanStack Query'dedir. Bileşen yalnızca üç durumdan birini çizer: yükleniyor, hata, veri.
 */
function SistemDurumu() {
  const saglik = useQuery({
    queryKey: ["saglik"],
    queryFn: () => cagir(api.GET("/api/saglik")),
  });
  return (
    <section aria-labelledby="sistem-durumu" className={stil.kart}>
      <h2 id="sistem-durumu">Sistem durumu</h2>
      {saglik.isPending && <p>Sunucuya bağlanılıyor...</p>}
      {saglik.isError && (
        <div className={stil.hataKutusu} role="alert">
          <p>{hataMetni(saglik.error)}</p>
          <Dugme tur="ikincil" onClick={() => saglik.refetch()} yukleniyor={saglik.isFetching}>
            Yeniden dene
          </Dugme>
        </div>
      )}
      {saglik.isSuccess && (
        <dl className={stil.durumListesi}>
          <dt>Sunucu</dt>
          <dd>
            <span className={stil.iyi}>✓ Çalışıyor</span>
          </dd>
          <dt>Veritabanı</dt>
          <dd>
            <span className={stil.iyi}>✓ Bağlı</span>
          </dd>
        </dl>
      )}
    </section>
  );
}
