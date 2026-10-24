import { Ban, BoxSelect, Waves } from "lucide-react";
import { Fragment, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import { hataMetni } from "../api/hata";
import { useBildirim } from "../bilesenler/Bildirim";
import { ogleArasiSonrasi, ogleArasiZili, saatVar, zilMetni, zilSaatleri, type Hafta } from "../okul/zaman";
import { GUN_ADLARI, GUN_KISA_ADLARI } from "../program/aciklama";
import {
  DURUM_ADLARI,
  anahtar,
  degisiklikler,
  durumHaritasi,
  durumu,
  komsu,
  sonrakiDurum,
  topluHedef,
  type Durum,
  type Konum,
} from "./musaitlik";
import stil from "./Ogretmen.module.css";
import { useMusaitlik, useMusaitlikDegistir } from "./veri";

/** `hafta`: okulun günlere göre ders saati, öğle arası ve zil saatleri (kısa günün sonu tıklanamaz). */
type Props = { ogretmenId: string; ad: string; gunSayisi: number; saatSayisi: number; hafta: Hafta };

/** Sürükleme sürerken: hangi hücrelerden geçildi ve hepsi hangi duruma getirilecek. */
type Surukleme = { hedef: Durum; hucreler: Konum[] };

/** Durumun renk dışındaki işareti: ikon (ve CSS'te desen). Renk körü kullanıcı da ayırt eder. */
function DurumIkonu({ durum }: { durum: Durum }) {
  if (durum === "gelemez") return <Ban aria-hidden="true" />;
  if (durum === "tercih_etmez") return <Waves aria-hidden="true" />;
  return null;
}

/**
 * Öğretmenin müsaitlik çizelgesi: sütunlar günler, satırlar ders saatleri.
 *
 * - **Tek hücre:** tıklandıkça müsait → gelemez → tercih etmez → müsait.
 * - **Toplu:** gün ya da saat başlığına tıklamak o satırı/sütunu birlikte döndürür; hücrelerin
 *   üzerinden sürüklemek, geçilen her hücreyi ilk hücrenin yeni durumuna getirir. Her işlem **tek
 *   istektir**; sunucu birini reddederse hiçbiri değişmez.
 * - **Dokunmatik (5.6):** parmakla çizelgenin üstünde sayfa kaydırılabilir; dokunmak tek hücreyi
 *   değiştirir. Sürükleyerek toplu seçim yalnızca "Toplu seç" modunda: mod açıkken bu çizelgede
 *   sayfa kaymaz (`touch-action: none`), parmağın geçtiği hücreler seçilir. Fareyle sürükleme
 *   moddan bağımsız, her zaman çalışır.
 * - **İyimser güncelleme:** hücre sunucunun cevabını beklemeden döner; hata olursa geri alınır.
 * - **Klavye:** çizelgeye Tab ile bir kez girilir (roving tabindex: yalnızca odaktaki hücre
 *   sekme sırasındadır), oklar/Home/End ile gezilir, Enter ya da boşluk durumu değiştirir.
 * - **Kapasite:** cevaptaki yük sunucunun hesabıdır (ön kontrolle aynı); müsait saat ders yükünün
 *   altına düşerse anında uyarı.
 * - **Kısa gün:** günün uzunluğunu aşan saatler (ör. cuma 6. saat, cuma 5 saatse) hücre değil
 *   "ders yok" alanıdır; toplu işlemler ve oklar onları atlar.
 */
export function MusaitlikCizelgesi({ ogretmenId, ad, gunSayisi, saatSayisi, hafta }: Props) {
  const cizelge = useMusaitlik(ogretmenId);
  const degistir = useMusaitlikDegistir(ogretmenId);
  const bildirim = useBildirim();
  const [odak, setOdak] = useState<Konum>({ gun: 0, saat: 0 });
  const [surukleme, setSurukleme] = useState<Surukleme | null>(null);
  const suruklemeRef = useRef<Surukleme | null>(null);
  const [topluSecim, setTopluSecim] = useState(false);
  // Son basış parmakla (ya da kalemle) mı: dokunuşta tek hücre "click" olayında değişir; parmak
  // sayfayı kaydırırsa tarayıcı click üretmez, hücre de değişmez.
  const dokunus = useRef(false);
  const hucreRefleri = useRef(new Map<string, HTMLButtonElement>());

  const harita = durumHaritasi(cizelge.data?.hucreler ?? []);
  const var_ = (k: Konum) => saatVar(hafta.gun_saatleri, k.gun, k.saat);

  function kaydet(hucreler: Konum[], hedef: Durum) {
    const degisen = degisiklikler(harita, hucreler, hedef);
    if (degisen.length === 0) return;
    degistir.mutate(degisen, {
      onError: (hata) => bildirim("hata", `${hataMetni(hata)} Değişiklik geri alındı.`),
    });
  }

  // Sürükleme bırakıldığında (fare/parmak hücrenin dışında da bırakılabilir): pencereyi dinle.
  // Effect, React dışındaki bir şeyle (pencere olayları) senkronizasyon için doğru yerdir;
  // temizleme fonksiyonu dinleyiciyi kaldırır.
  useEffect(() => {
    if (!surukleme) return;
    const birak = () => {
      const s = suruklemeRef.current;
      suruklemeRef.current = null;
      setSurukleme(null);
      if (s) kaydet(s.hucreler, s.hedef);
    };
    const iptal = () => {
      suruklemeRef.current = null;
      setSurukleme(null);
    };
    window.addEventListener("pointerup", birak);
    window.addEventListener("pointercancel", iptal);
    return () => {
      window.removeEventListener("pointerup", birak);
      window.removeEventListener("pointercancel", iptal);
    };
  });

  function basla(olay: ReactPointerEvent<HTMLButtonElement>, k: Konum) {
    if (olay.button > 0) return; // yalnızca birincil tuş (sağ ve orta tuş değil)
    dokunus.current = olay.pointerType === "touch" || olay.pointerType === "pen";
    // Dokunuşta mod kapalıysa sürükleme başlamaz: parmak sayfayı kaydırabilsin.
    if (dokunus.current && !topluSecim) return;
    // Dokunmatik ekranda tarayıcı işaretçiyi ilk öğeye bağlar (pointer capture); bırakılmazsa
    // parmak başka hücreye geçtiğinde o hücre haberdar olmaz.
    olay.currentTarget.releasePointerCapture?.(olay.pointerId);
    const s = { hedef: sonrakiDurum(durumu(harita, k)), hucreler: [k] };
    suruklemeRef.current = s;
    setSurukleme(s);
    setOdak(k);
  }

  function gec(k: Konum) {
    const s = suruklemeRef.current;
    if (!s || s.hucreler.some((h) => anahtar(h) === anahtar(k))) return;
    const yeni = { ...s, hucreler: [...s.hucreler, k] };
    suruklemeRef.current = yeni;
    setSurukleme(yeni);
  }

  function tusla(olay: KeyboardEvent<HTMLButtonElement>, k: Konum) {
    if (olay.key === "Enter" || olay.key === " ") {
      olay.preventDefault();
      kaydet([k], sonrakiDurum(durumu(harita, k)));
      return;
    }
    const yeni = komsu(k, olay.key, gunSayisi, saatSayisi, var_);
    if (yeni) {
      olay.preventDefault();
      setOdak(yeni);
      hucreRefleri.current.get(anahtar(yeni))?.focus();
    }
  }

  function toplu(hucreler: Konum[]) {
    const varolan = hucreler.filter(var_);
    if (varolan.length > 0) kaydet(varolan, topluHedef(harita, varolan));
  }

  // Ekranda görünen durum: sürükleme sürerken geçilen hücreler yeni durumunu hemen gösterir.
  const gorunen = (k: Konum): Durum =>
    surukleme?.hucreler.some((h) => anahtar(h) === anahtar(k)) ? surukleme.hedef : durumu(harita, k);

  const gunler = Array.from({ length: gunSayisi }, (_, g) => GUN_ADLARI[g] ?? `${g + 1}. gün`);
  const saatler = Array.from({ length: saatSayisi }, (_, s) => s);
  const yuk = cizelge.data?.yuk;
  const zil = zilSaatleri(hafta, saatSayisi);
  const ogleZili = ogleArasiZili(hafta, zil);

  return (
    <section aria-labelledby="musaitlik-baslik" className={stil.kart}>
      <h2 id="musaitlik-baslik">Müsaitlik</h2>
      <p className={stil.aciklama}>
        Hücreye tıkladıkça değişir: müsait → gelemez → tercih etmez. Birçok hücre için üzerlerinden sürükleyin
        (dokunmatik ekranda önce &quot;Toplu seç&quot;) ya da gün veya saat başlığına tıklayın. Değişiklikler hemen kaydedilir.
      </p>
      <div className={stil.topluSatiri}>
        <button type="button" className={stil.topluDugmesi} aria-pressed={topluSecim} onClick={() => setTopluSecim(!topluSecim)}>
          <BoxSelect aria-hidden="true" />
          {topluSecim ? "Toplu seçimi bitir" : "Toplu seç"}
        </button>
        {topluSecim && (
          <p className={stil.topluBilgi} role="status">
            Toplu seçim açık: parmağınızı hücrelerin üzerinden kaydırın. Bu çizelgede sayfa kaymaz.
          </p>
        )}
      </div>
      <ul className={stil.lejant} aria-label="Lejant">
        {(["musait", "gelemez", "tercih_etmez"] as const).map((d) => (
          <li key={d}>
            <span className={stil.ornekHucre} data-durum={d}>
              <DurumIkonu durum={d} />
            </span>
            {d === "musait" ? "Müsait (boş)" : d === "gelemez" ? "Gelemez: bu saate ders konmaz" : "Tercih etmez: mümkünse konmaz"}
          </li>
        ))}
      </ul>
      {cizelge.isError ? (
        <p role="alert">{hataMetni(cizelge.error)}</p>
      ) : (
        <div className={stil.cizelgeKutusu} data-kaydirilabilir data-toplu={topluSecim || undefined}>
          <table className={stil.cizelge} aria-label={`${ad} müsaitlik çizelgesi`} aria-busy={cizelge.isPending}>
            <thead>
              <tr>
                <th scope="col" className={stil.kose}>
                  <span className="gorunmez">Saat</span>
                </th>
                {gunler.map((g, gun) => (
                  <th key={g} scope="col">
                    <button type="button" className={stil.baslikDugmesi} disabled={!cizelge.data}
                      onClick={() => toplu(saatler.map((saat) => ({ gun, saat })))}
                      aria-label={`${g}: bütün günü birlikte değiştir`}>
                      {/* Dar ekranda kısa ad (Pzt); erişilebilir ad zaten tam. */}
                      <span className={stil.uzunAd}>{g}</span>
                      <span className={stil.kisaAd}>{GUN_KISA_ADLARI[gun] ?? g}</span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {saatler.map((saat) => (
                <Fragment key={saat}>
                  <tr>
                    <th scope="row">
                      <button type="button" className={stil.baslikDugmesi} disabled={!cizelge.data}
                        onClick={() => toplu(gunler.map((_, gun) => ({ gun, saat })))}
                        aria-label={`${saat + 1}. saat: bütün günlerde birlikte değiştir`}>
                        {saat + 1}. saat
                        {zil?.[saat] && <span className={stil.zil}>{zilMetni(zil[saat])}</span>}
                      </button>
                    </th>
                    {gunler.map((g, gun) => {
                      const k = { gun, saat };
                      if (!var_(k)) {
                        return (
                          <td key={gun} className={stil.yok}>
                            <span className="gorunmez">{`${g}, ${saat + 1}. saat: bu saatte ders yok`}</span>
                          </td>
                        );
                      }
                      const d = gorunen(k);
                      const odakta = odak.gun === gun && odak.saat === saat;
                      return (
                        <td key={gun}>
                          <button
                            type="button"
                            ref={(el) => {
                              if (el) hucreRefleri.current.set(anahtar(k), el);
                              else hucreRefleri.current.delete(anahtar(k));
                            }}
                            className={stil.hucre}
                            data-durum={d}
                            disabled={!cizelge.data}
                            tabIndex={odakta ? 0 : -1}
                            aria-label={`${g}, ${saat + 1}. saat: ${DURUM_ADLARI[d]}`}
                            onPointerDown={(o) => basla(o, k)}
                            onPointerEnter={() => gec(k)}
                            // Klavye ve ekran okuyucunun "tıklaması" işaretçi olayı üretmez (detail 0). Dokunuşta
                            // (mod kapalı) tek hücre burada değişir; fare ve toplu seçim bırakınca kaydeder.
                            onClick={(o) => {
                              if (o.detail === 0 || (dokunus.current && !topluSecim)) kaydet([k], sonrakiDurum(durumu(harita, k)));
                            }}
                            onKeyDown={(o) => tusla(o, k)}
                            onFocus={() => setOdak(k)}
                          >
                            {/* key: durum değişince ikon yeniden kurulur, kısa giriş animasyonu oynar. */}
                            <span key={d} className={stil.hucreIcerik}>
                              <DurumIkonu durum={d} />
                            </span>
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                  {ogleArasiSonrasi(hafta.ogle_arasi_sonra, saat) && saat + 1 < saatSayisi && (
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
      )}
      {yuk && (
        <div aria-live="polite" className={stil.yukOzeti}>
          <p>
            Müsait <strong>{yuk.musait_saat} saat</strong>
            {yuk.kullanilabilir_saat < yuk.musait_saat && ` (günlük ders sınırıyla en fazla ${yuk.kullanilabilir_saat} saat derse girebilir)`}
            ; ders yükü <strong>{yuk.ders_saati} saat</strong>.
          </p>
          {yuk.asim && yuk.mesaj && (
            <p className={stil.kapasiteUyarisi} role="alert">
              <span aria-hidden="true">⚠ </span>
              {yuk.mesaj} Program bu haliyle üretilemez.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
