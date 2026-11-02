import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { Link, Navigate, useNavigate, useParams } from "react-router";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import { SecimAlani } from "../bilesenler/Alan";
import { Iskelet } from "../bilesenler/Iskelet";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { useBen } from "../kimlik/oturum";
import { ogretmenKaynagi } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import { KURALLAR_ANAHTARI } from "../okul/OkulAyarlariSayfasi";
import { KisiselAyarlar } from "./KisiselAyarlar";
import { MusaitlikCizelgesi } from "./MusaitlikCizelgesi";
import stil from "./Ogretmen.module.css";

/**
 * Öğretmen detay sayfası (/ogretmenler/:id): üstte kişisel ayarlar (boş gün hedefi, günde en çok
 * ders), altta müsaitlik çizelgesi. Öğretmenler arasında hızlı geçiş: önceki/sonraki bağlantıları
 * ve seçim kutusu (adres değişir; sayfa yenilense de aynı öğretmen açılır).
 */
export function OgretmenSayfasi() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  const kurallar = useQuery({ queryKey: KURALLAR_ANAHTARI, queryFn: () => cagir(api.GET("/api/ders-programi/kurallar")) });
  const okul = useBen().data?.okul;

  const hata = ogretmenler.error ?? kurallar.error;
  if (hata) {
    return (
      <div className={sayfaStili.hataKutusu} role="alert">
        <p>{hataMetni(hata)}</p>
      </div>
    );
  }
  if (!ogretmenler.data || !kurallar.data || !okul) return <Iskelet satir={8} kart />;

  const sirali = turkceSirala(ogretmenler.data, (o) => o.ad);
  const sira = sirali.findIndex((o) => o.id === id);
  const ogretmen = sirali[sira];
  if (!ogretmen) {
    return (
      <>
        <SayfaBasligi baslik="Öğretmen bulunamadı">
          Bu öğretmen silinmiş ya da başka bir okula ait olabilir.
        </SayfaBasligi>
        <Link to="/ogretmenler">Öğretmen listesine dön</Link>
      </>
    );
  }
  const onceki = sirali[sira - 1];
  const sonraki = sirali[sira + 1];

  return (
    <>
      <SayfaBasligi baslik={ogretmen.ad}>
        {ogretmen.brans ? `${ogretmen.brans}. ` : ""}Kişisel ayarlar ve müsaitlik.
      </SayfaBasligi>
      <nav aria-label="Öğretmenler arasında geçiş" className={stil.gecis}>
        <Link to="/ogretmenler" className={stil.geri}>
          <ArrowLeft aria-hidden="true" /> Öğretmen listesi
        </Link>
        <div className={stil.gecisDugmeleri}>
          {onceki ? (
            <Link to={`/ogretmenler/${onceki.id}`} className={stil.gecisBaglantisi} aria-label={`Önceki öğretmen: ${onceki.ad}`}>
              <ChevronLeft aria-hidden="true" /> Önceki
            </Link>
          ) : (
            <span className={stil.gecisPasif} aria-hidden="true"><ChevronLeft /> Önceki</span>
          )}
          <SecimAlani etiket="Öğretmen" value={ogretmen.id} onChange={(o) => navigate(`/ogretmenler/${o.target.value}`)}>
            {sirali.map((o) => (
              <option key={o.id} value={o.id}>
                {o.ad}
              </option>
            ))}
          </SecimAlani>
          <span className={stil.sira}>
            {sira + 1} / {sirali.length}
          </span>
          {sonraki ? (
            <Link to={`/ogretmenler/${sonraki.id}`} className={stil.gecisBaglantisi} aria-label={`Sonraki öğretmen: ${sonraki.ad}`}>
              Sonraki <ChevronRight aria-hidden="true" />
            </Link>
          ) : (
            <span className={stil.gecisPasif} aria-hidden="true">Sonraki <ChevronRight /></span>
          )}
        </div>
      </nav>
      {/* key: başka öğretmene geçince bölümler baştan kurulur (odak, sürükleme durumu sıfırlanır). */}
      <KisiselAyarlar key={`ayar-${ogretmen.id}`} ogretmenId={ogretmen.id} kurallar={kurallar.data} okul={okul} />
      <MusaitlikCizelgesi key={`musaitlik-${ogretmen.id}`} ogretmenId={ogretmen.id} ad={ogretmen.ad}
        gunSayisi={okul.gun_sayisi} saatSayisi={okul.gunluk_ders_saati} hafta={okul} />
    </>
  );
}

/**
 * Eski "Öğretmen müsaitliği" adresi (/musaitlik): müsaitlik artık öğretmen sayfasında. İlk
 * öğretmenin sayfasına, öğretmen yoksa listeye gider.
 */
export function MusaitlikYonlendirme() {
  const ogretmenler = useQuery({ queryKey: ogretmenKaynagi.anahtar, queryFn: ogretmenKaynagi.listele });
  if (ogretmenler.isPending) return <Iskelet satir={4} />;
  const ilk = turkceSirala(ogretmenler.data ?? [], (o) => o.ad)[0];
  return <Navigate to={ilk ? `/ogretmenler/${ilk.id}` : "/ogretmenler"} replace />;
}
