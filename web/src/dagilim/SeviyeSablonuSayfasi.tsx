import { dersIsaretleri } from "../dersler/isaret";
import { Illustrasyon } from "../bilesenler/Illustrasyon";
import { DersCipi } from "../dersler/DersCipi";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Layers } from "lucide-react";
import { Plus, RotateCcw, WandSparkles, X } from "lucide-react";
import { Iskelet } from "../bilesenler/Iskelet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { hataMetni } from "../api/hata";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { Tablo } from "../bilesenler/Tablo";
import { dersKaynagi, sinifKaynagi, type Ders, type Sinif } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Dagilim.module.css";
import { SaatGirdisi } from "./SaatGirdisi";
import { atamaApi, sablonApi, SABLON, useAtamalarDegisti, useDagilimOzeti, type SablonRaporu, type SablonSatiri } from "./veri";

/**
 * Seviye şablonu: bir seviyenin dersleri ve haftalık saatleri bir kez girilir, o seviyedeki bütün
 * şubelere uygulanır. Uygulama yalnızca **eksik** dersleri ekler (öğretmeni boş); şubede zaten olan
 * ders değişmez. Saati şablondan farklı olanlar raporda listelenir, kullanıcı isterse tek
 * tıklamayla şablondaki saate çeker.
 */
export function SeviyeSablonuSayfasi() {
  const [parametreler, setParametreler] = useSearchParams();
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const sablon = useQuery({ queryKey: SABLON, queryFn: sablonApi.listele });
  const ozet = useDagilimOzeti();

  const sorgular = [siniflar, dersler, sablon, ozet];
  const hatali = sorgular.find((s) => s.isError);

  let icerik;
  if (hatali) {
    icerik = (
      <div className={sayfaStili.hataKutusu} role="alert">
        <p>{hataMetni(hatali.error)}</p>
        <Dugme ikon={<RotateCcw />} tur="ikincil" onClick={() => sorgular.forEach((s) => s.refetch())}>
          Yeniden dene
        </Dugme>
      </div>
    );
  } else if (!siniflar.data || !dersler.data || !sablon.data || !ozet.data) {
    icerik = <Iskelet satir={6} kart />;
  } else if (siniflar.data.length === 0 || dersler.data.length === 0) {
    icerik = (
      <section aria-labelledby="sablon-on-kosul" className={stil.bosDurum}>
        <Illustrasyon tur="ders" />
        <h2 id="sablon-on-kosul">Önce sınıfları ve dersleri ekleyin</h2>
        <p>Şablon, bir seviyedeki şubelere hangi dersin haftada kaç saat verileceğini söyler.</p>
        <ul className={stil.eksikListesi}>
          {siniflar.data.length === 0 && <li><Link to="/siniflar">Sınıfları ekleyin</Link></li>}
          {dersler.data.length === 0 && <li><Link to="/dersler">Dersleri ekleyin</Link></li>}
        </ul>
      </section>
    );
  } else {
    // Seviyeler: okulda şubesi olanlar ve şablonu olanlar, küçükten büyüğe.
    const seviyeler = [...new Set([...siniflar.data.map((s) => s.seviye), ...sablon.data.map((s) => s.seviye)])].sort(
      (a, b) => a - b,
    );
    const istenen = Number(parametreler.get("seviye"));
    // Şube var (yukarıda denetlendi), yani en az bir seviye var; `?? 1` yalnızca tip için.
    const seviye = seviyeler.includes(istenen) ? istenen : (seviyeler[0] ?? 1);
    const subeler = (sv: number) => turkceSirala(siniflar.data.filter((s) => s.seviye === sv), (s) => s.ad);

    icerik = (
      <>
        <div className={stil.dersSecimi}>
          <SecimAlani etiket="Sınıf seviyesi" value={String(seviye)}
            onChange={(o) => setParametreler({ seviye: o.target.value })}>
            {seviyeler.map((sv) => (
              <option key={sv} value={sv}>
                {sv}. sınıflar ({subeler(sv).length} şube)
              </option>
            ))}
          </SecimAlani>
        </div>
        {/* key: seviye değişince ekleme formu ve rapor sıfırlansın. */}
        <SeviyeSablonu
          key={seviye}
          seviye={seviye}
          satirlar={sablon.data.filter((s) => s.seviye === seviye)}
          dersler={dersler.data}
          subeler={subeler(seviye)}
          haftalikKapasite={ozet.data.haftalik_kapasite}
        />
      </>
    );
  }

  return (
    <>
      <SayfaBasligi ikon={Layers} baslik="Seviye şablonu">
        Bir seviyenin derslerini ve haftalık saatlerini bir kez girin, o seviyedeki bütün şubelere tek seferde
        uygulayın. Öğretmenleri sonra Ders dağılımı sayfasında seçersiniz.
      </SayfaBasligi>
      {icerik}
    </>
  );
}

type SablonProps = {
  seviye: number;
  satirlar: SablonSatiri[];
  dersler: Ders[];
  subeler: Sinif[];
  haftalikKapasite: number;
};

function SeviyeSablonu({ seviye, satirlar, dersler, subeler, haftalikKapasite }: SablonProps) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const atamalarDegisti = useAtamalarDegisti();
  const [yeni, setYeni] = useState({ ders_id: "", saat: "" });
  const [yeniHatasi, setYeniHatasi] = useState<string>();
  const [rapor, setRapor] = useState<SablonRaporu | null>(null);

  const dersAdi = (id: string) => dersler.find((d) => d.id === id)?.ad ?? "";
  const sirali = turkceSirala(satirlar, (s) => dersAdi(s.ders_id));
  const toplam = satirlar.reduce((t, s) => t + s.haftalik_saat, 0);
  const eklenebilir = turkceSirala(dersler.filter((d) => !satirlar.some((s) => s.ders_id === d.id)), (d) => d.ad);
  const tazele = () => istemci.invalidateQueries({ queryKey: SABLON });

  const ekle = useMutation({
    mutationFn: (d: { ders_id: string; haftalik_saat: number }) => sablonApi.olustur({ seviye, ...d }),
    onSuccess: async (s) => {
      await tazele();
      bildirim("basari", `${dersAdi(s.ders_id)} ${seviye}. sınıf şablonuna eklendi.`);
      setYeni({ ders_id: "", saat: "" });
    },
    onError: (hata) => setYeniHatasi(hataMetni(hata)),
  });

  const saatDegistir = useMutation({
    mutationFn: (d: { satir: SablonSatiri; saat: number }) => sablonApi.guncelle(d.satir.id, d.saat),
    onSuccess: async (s) => {
      await tazele();
      bildirim("basari", `${dersAdi(s.ders_id)}: şablonda haftada ${s.haftalik_saat} saat.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  const cikar = useMutation({
    mutationFn: (s: SablonSatiri) => sablonApi.sil(s.id),
    onSuccess: async (_, s) => {
      await tazele();
      bildirim("basari", `${dersAdi(s.ders_id)} şablondan çıkarıldı. Şubelerdeki dersler değişmedi.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  const uygula = useMutation({
    mutationFn: () => sablonApi.uygula(seviye),
    onSuccess: async (sonuc) => {
      await atamalarDegisti();
      setRapor(sonuc);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  function ekleGonder(olay: FormEvent) {
    olay.preventDefault();
    const saat = Number(yeni.saat);
    if (!yeni.ders_id) return setYeniHatasi("Eklenecek dersi seçin.");
    if (!Number.isInteger(saat) || saat < 1) return setYeniHatasi("Haftalık saat en az 1 olmalı.");
    setYeniHatasi(undefined);
    ekle.mutate({ ders_id: yeni.ders_id, haftalik_saat: saat });
  }

  const subeAdlari = subeler.map((s) => s.ad).join(", ");

  return (
    <>
      <section aria-labelledby="sablon-baslik" className={sayfaStili.kart}>
        <h2 id="sablon-baslik">{seviye}. sınıfların dersleri</h2>
        {sirali.length === 0 ? (
          <p className={stil.aciklama}>Bu seviyenin şablonunda henüz ders yok. Aşağıdan ekleyin.</p>
        ) : (
          <Tablo<SablonSatiri>
            baslik={`${seviye}. sınıf şablonu`}
            satirlar={sirali}
            satirAnahtari={(s) => s.id}
            sutunlar={[
              {
                baslik: "Ders",
                hucre: (s) => (
                  <DersCipi ad={dersAdi(s.ders_id)} renk={dersler.find((d) => d.id === s.ders_id)?.renk}
                    isaret={dersIsaretleri(dersler).get(s.ders_id)} />
                ),
              },
              {
                baslik: "Haftalık saat",
                hucre: (s) => (
                  <SaatGirdisi key={`${s.id}-${s.haftalik_saat}`} etiket={`${dersAdi(s.ders_id)} haftalık saat`}
                    deger={s.haftalik_saat} onKaydet={(saat) => saatDegistir.mutate({ satir: s, saat })} />
                ),
              },
              {
                baslik: "İşlemler",
                baslikGizli: true,
                hizala: "sag",
                hucre: (s) => (
                  <Dugme ikon={<X />} tur="metin" onClick={() => cikar.mutate(s)} aria-label={`${dersAdi(s.ders_id)} dersini şablondan çıkar`}>
                    Çıkar
                  </Dugme>
                ),
              },
            ]}
          />
        )}
        <p className={toplam > haftalikKapasite ? stil.toplamAsim : stil.toplam}>
          {toplam > haftalikKapasite && <span aria-hidden="true">⚠ </span>}
          Haftalık toplam <strong>{toplam} saat</strong>; okulun haftalık kapasitesi {haftalikKapasite} saat.
          {toplam > haftalikKapasite && " Bu şablonla şubelerin programı üretilemez."}
        </p>

        <form onSubmit={ekleGonder} className={stil.ekleFormu} noValidate>
          <h3 className={stil.formBasligi}>Şablona ders ekle</h3>
          <div className={stil.ekleAlanlari}>
            <SecimAlani etiket="Ders" value={yeni.ders_id} hata={yeniHatasi}
              onChange={(o) => setYeni({ ...yeni, ders_id: o.target.value })}>
              <option value="">Ders seçin</option>
              {eklenebilir.map((d) => (
                <option key={d.id} value={d.id}>{d.ad}</option>
              ))}
            </SecimAlani>
            <MetinAlani etiket="Haftalık saat" type="number" inputMode="numeric" min={1} value={yeni.saat}
              onChange={(o) => setYeni({ ...yeni, saat: o.target.value })} />
            <Dugme ikon={<Plus />} type="submit" className={stil.ekleDugmesi} yukleniyor={ekle.isPending} yukleniyorMetni="Ekleniyor...">
              Ekle
            </Dugme>
          </div>
        </form>
      </section>

      <section aria-labelledby="uygula-baslik" className={sayfaStili.kart}>
        <h2 id="uygula-baslik">Şubelere uygula</h2>
        {subeler.length === 0 ? (
          <p className={stil.aciklama}>Okulda {seviye}. sınıf şubesi yok. Şube eklenince şablon uygulanabilir.</p>
        ) : (
          <>
            <p className={stil.aciklama}>
              Şablondaki dersler {subeler.length} şubeye ({subeAdlari}) öğretmeni boş olarak eklenir. Şubede zaten olan
              dersler değiştirilmez; saati farklı olanlar size gösterilir. Şablonda olmayan dersler şubelerden
              kaldırılmaz.
            </p>
            <Dugme ikon={<WandSparkles />} disabled={sirali.length === 0} yukleniyor={uygula.isPending} yukleniyorMetni="Uygulanıyor..."
              onClick={() => uygula.mutate()}>
              {seviye}. sınıf şubelerine uygula
            </Dugme>
          </>
        )}
        {rapor && <UygulamaRaporu rapor={rapor} subeler={subeler} dersler={dersler} onKapat={() => setRapor(null)} />}
      </section>
    </>
  );
}

/**
 * Şablon uygulamasının sonucu, kullanıcının diliyle. Sunucunun raporu: kaç şube, kaç atama
 * oluşturuldu, kaçı zaten vardı, hangilerinin saati şablondan farklı (değiştirilmedi).
 *
 * Rapor görününce odak başlığına taşınır: düğmeye basan klavye ve ekran okuyucu kullanıcısı sonucu
 * hemen duyar ve tablonun içinde gezinebilir.
 */
function UygulamaRaporu({
  rapor,
  subeler,
  dersler,
  onKapat,
}: {
  rapor: SablonRaporu;
  subeler: Sinif[];
  dersler: Ders[];
  onKapat: () => void;
}) {
  const bildirim = useBildirim();
  const atamalarDegisti = useAtamalarDegisti();
  const baslik = useRef<HTMLHeadingElement>(null);
  const [duzeltilen, setDuzeltilen] = useState<Set<string>>(new Set());

  useEffect(() => {
    baslik.current?.focus();
  }, [rapor]);

  const sablonaCek = useMutation({
    mutationFn: (f: SablonRaporu["farkli_saatli"][number]) =>
      atamaApi.guncelle(f.atama_id, { haftalik_saat: f.sablondaki_saat }),
    onSuccess: async (_, f) => {
      await atamalarDegisti();
      setDuzeltilen((onceki) => new Set(onceki).add(f.atama_id));
      bildirim("basari", `${f.sinif} ${f.ders}: haftada ${f.sablondaki_saat} saat olarak güncellendi.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  const ilkSube = subeler[0];
  return (
    <div className={stil.rapor}>
      <h3 ref={baslik} tabIndex={-1} className={stil.raporBasligi}>
        Şablon uygulandı
      </h3>
      <ul className={stil.raporListesi}>
        <li>
          {rapor.olusturulan > 0 ? (
            <>
              <strong>{rapor.sube_sayisi} şubeye toplam {rapor.olusturulan} ders eklendi</strong> (
              {subeler.map((s) => s.ad).join(", ")}). Öğretmenleri henüz seçilmedi.{" "}
              {ilkSube && <Link to={`/ders-dagilimi?gorunum=sube&sinif=${ilkSube.id}`}>Ders dağılımında öğretmen seçin</Link>}
            </>
          ) : (
            <>Eklenecek yeni ders yoktu: şablondaki derslerin hepsi şubelerde zaten var.</>
          )}
        </li>
        {rapor.zaten_var > 0 && <li>{rapor.zaten_var} ders şubelerde zaten vardı; değiştirilmedi.</li>}
      </ul>
      {rapor.farkli_saatli.length > 0 && (
        <>
          <p>
            <span aria-hidden="true">⚠ </span>
            <strong>{rapor.farkli_saatli.length} dersin saati şablondan farklı.</strong> Bilerek farklı tutmuş
            olabileceğiniz için değiştirilmedi:
          </p>
          <Tablo<SablonRaporu["farkli_saatli"][number]>
            baslik="Saati şablondan farklı dersler"
            satirlar={rapor.farkli_saatli}
            satirAnahtari={(f) => f.atama_id}
            sutunlar={[
              { baslik: "Şube", hucre: (f) => f.sinif },
              {
                baslik: "Ders",
                hucre: (f) => {
                  const d = dersler.find((x) => x.ad === f.ders);
                  return <DersCipi ad={f.ders} renk={d?.renk} isaret={d ? dersIsaretleri(dersler).get(d.id) : 0} />;
                },
              },
              { baslik: "Şubede", hucre: (f) => `${f.atamadaki_saat} saat` },
              { baslik: "Şablonda", hucre: (f) => `${f.sablondaki_saat} saat` },
              {
                baslik: "İşlem",
                baslikGizli: true,
                hizala: "sag",
                hucre: (f) =>
                  duzeltilen.has(f.atama_id) ? (
                    <span className={stil.iyiMetin}>✓ Güncellendi</span>
                  ) : (
                    <Dugme tur="ikincil" yukleniyor={sablonaCek.isPending && sablonaCek.variables?.atama_id === f.atama_id}
                      onClick={() => sablonaCek.mutate(f)} aria-label={`${f.sinif} ${f.ders}: şablondaki ${f.sablondaki_saat} saati kullan`}>
                      Şablondaki saati kullan
                    </Dugme>
                  ),
              },
            ]}
          />
        </>
      )}
      <Dugme tur="metin" onClick={onKapat}>
        Raporu kapat
      </Dugme>
    </div>
  );
}
