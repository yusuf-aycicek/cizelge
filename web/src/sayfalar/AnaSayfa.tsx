import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  CircleCheck,
  CircleDashed,
  CircleAlert,
  Clock,
  GraduationCap,
  School,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import { Dugme } from "../bilesenler/Dugme";
import { Iskelet } from "../bilesenler/Iskelet";
import { useAtamalar, useDagilimOzeti } from "../dagilim/veri";
import { useBen } from "../kimlik/oturum";
import { dersKaynagi, ogretmenKaynagi, sinifKaynagi } from "../listeler/kaynaklar";
import { IlerlemeHalkasi } from "./IlerlemeHalkasi";
import { kurulumDurumu, type AdimDurumu } from "./kurulum";
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

/**
 * Ana sayfa panosu: karşılama bandı ve kurulum ilerleme halkası, sayı kartları, kurulum adımları
 * (kontrol listesi) ve sistem durumu.
 *
 * Halka ve kontrol listesi aynı hesaptan gelir (`kurulumDurumu`). Öğretmensiz ders sayısı, ders
 * dağılımı sayfasıyla aynı sunucu özetinden okunur (ADR 0015).
 */
export function AnaSayfa() {
  const ben = useBen().data;
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const atamalar = useAtamalar();
  const ozet = useDagilimOzeti();

  const hazir = ben && ogretmenler.data && siniflar.data && dersler.data && atamalar.data && ozet.data;
  const kurulum = hazir
    ? kurulumDurumu({
        gunSayisi: ben.okul.gun_sayisi,
        gunlukDersSaati: ben.okul.gunluk_ders_saati,
        ogretmen: ogretmenler.data.length,
        sinif: siniflar.data.length,
        ders: dersler.data.length,
        atama: atamalar.data.length,
        ogretmensizAtama: ozet.data.ogretmensiz_atama,
      })
    : null;
  const toplamSaat = atamalar.data?.reduce((t, a) => t + a.haftalik_saat, 0) ?? 0;

  return (
    <>
      <section className={pano.karsilama} aria-labelledby="karsilama-baslik">
        <div className={pano.karsilamaMetni}>
          <h1 id="karsilama-baslik">Hoş geldiniz</h1>
          {ben && (
            <p className={stil.kim}>
              {ben.kullanici.ad} · {ben.okul.ad}
            </p>
          )}
          <p className={pano.karsilamaAciklama}>
            Bu sistem okulunuz için öğretmen ve sınıf çakışması olmayan haftalık ders programı hazırlar.
            {kurulum && kurulum.yuzde < 100 && " Aşağıdaki adımları tamamlayınca programı üretebilirsiniz."}
            {kurulum && kurulum.yuzde === 100 && " Kurulum tamam: program üretmeye hazırsınız."}
          </p>
        </div>
        {kurulum && <IlerlemeHalkasi yuzde={kurulum.yuzde} tamamlanan={kurulum.tamamlanan} gereken={kurulum.gereken} />}
      </section>

      {!kurulum ? (
        <Iskelet satir={4} kart />
      ) : (
        <>
          <ul className={pano.sayilar} aria-label="Okulunuz sayılarla">
            <SayiKarti ikon={GraduationCap} sayi={ogretmenler.data?.length ?? 0} ad="Öğretmen" yol="/ogretmenler" />
            <SayiKarti ikon={School} sayi={siniflar.data?.length ?? 0} ad="Şube" yol="/siniflar" />
            <SayiKarti ikon={BookOpen} sayi={dersler.data?.length ?? 0} ad="Ders" yol="/dersler" />
            <SayiKarti ikon={Clock} sayi={toplamSaat} ad="Haftalık ders saati" yol="/ders-dagilimi" />
          </ul>

          <div className={pano.ikiSutun}>
            <section aria-labelledby="kurulum-baslik" className={stil.kart}>
              <h2 id="kurulum-baslik">Kurulum adımları</h2>
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
            <SistemDurumu />
          </div>
        </>
      )}
    </>
  );
}

function SayiKarti({ ikon: Ikon, sayi, ad, yol }: { ikon: LucideIcon; sayi: number; ad: string; yol: string }) {
  return (
    <li>
      <Link to={yol} className={pano.sayiKarti}>
        <Ikon aria-hidden="true" className={pano.sayiIkonu} />
        <span className={pano.sayi}>{sayi}</span>
        <span className={pano.sayiAdi}>{ad}</span>
      </Link>
    </li>
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
