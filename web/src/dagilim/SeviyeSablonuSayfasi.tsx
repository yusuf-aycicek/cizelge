import { dersIsaretleri } from "../dersler/isaret";
import { Illustrasyon } from "../bilesenler/Illustrasyon";
import { DersCipi } from "../dersler/DersCipi";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Copy, Layers, RotateCcw, Save, WandSparkles } from "lucide-react";
import { Iskelet } from "../bilesenler/Iskelet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";
import { hataMetni } from "../api/hata";
import { SecimAlani } from "../bilesenler/Alan";
import { FormHatasi } from "../bilesenler/form";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { Tablo } from "../bilesenler/Tablo";
import { dersKaynagi, sinifKaynagi, type Ders, type Sinif } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Dagilim.module.css";
import { useSubeGruplari, type SubeGrubu } from "../listeler/SubeGruplari";
import { atamaApi, sablonApi, SABLON, useAtamalarDegisti, useDagilimOzeti, type SablonRaporu, type SablonSatiri, type Sema } from "./veri";

/**
 * Hangi şube hangi şablonu kullanır: grubunun şablonunda ders varsa grubunkini, yoksa seviyenin.
 * Sunucudaki `sablon_kaynaklari` ile aynı kural (şablon uygulanırken o kullanılır).
 */
export function kullananSubeler(siniflar: Sinif[], sablon: SablonSatiri[], seviye: number, grupId: string | null): Sinif[] {
  const doluGruplar = new Set(sablon.flatMap((s) => (s.sube_grubu_id ? [s.sube_grubu_id] : [])));
  const kaynak = (s: Sinif) => (s.sube_grubu_id && doluGruplar.has(s.sube_grubu_id) ? s.sube_grubu_id : null);
  return turkceSirala(siniflar.filter((s) => s.seviye === seviye && kaynak(s) === grupId), (s) => s.ad);
}

/**
 * Seviye şablonu: bir seviyenin dersleri ve haftalık saatleri bir kez girilir, o seviyedeki bütün
 * şubelere uygulanır. Uygulama yalnızca **eksik** dersleri ekler (öğretmeni boş); şubede zaten olan
 * ders değişmez. Saati şablondan farklı olanlar raporda listelenir, kullanıcı isterse tek
 * tıklamayla şablondaki saate çeker.
 *
 * Şablon bir seviyeye ("11. sınıflar") ya da bir şube grubuna ("11 Sayısal") ait olabilir (K5).
 * Grubun şablonunda ders varsa grubun şubeleri onu kullanır, seviyenin şablonu onlara uygulanmaz.
 */
export function SeviyeSablonuSayfasi() {
  const [parametreler, setParametreler] = useSearchParams();
  const siniflar = useQuery({ queryKey: sinifKaynagi.anahtar, queryFn: sinifKaynagi.listele });
  const dersler = useQuery({ queryKey: dersKaynagi.anahtar, queryFn: dersKaynagi.listele });
  const sablon = useQuery({ queryKey: SABLON, queryFn: sablonApi.listele });
  const ozet = useDagilimOzeti();
  const gruplar = useSubeGruplari();

  const sorgular = [siniflar, dersler, sablon, ozet, gruplar];
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
  } else if (!siniflar.data || !dersler.data || !sablon.data || !ozet.data || !gruplar.data) {
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
    const seviyeGruplari = (sv: number) => turkceSirala(gruplar.data.filter((g) => g.seviye === sv), (g) => g.ad);
    const grup = seviyeGruplari(seviye).find((g) => g.id === parametreler.get("grup"));
    const grupId = grup?.id ?? null;
    // Grubun şablonu boşken grubun şubeleri seviyenin şablonunu kullanır; grubun sayfasında yine
    // grubun şubeleri gösterilir (ilk ders eklenince bu şablona geçerler).
    const subeler = (sv: number, g: SubeGrubu | null) =>
      g && !sablon.data.some((s) => s.sube_grubu_id === g.id)
        ? turkceSirala(siniflar.data.filter((s) => s.sube_grubu_id === g.id), (s) => s.ad)
        : kullananSubeler(siniflar.data, sablon.data, sv, g?.id ?? null);
    const deger = (sv: number, g: SubeGrubu | null) => (g ? `${sv}:${g.id}` : String(sv));

    icerik = (
      <>
        <div className={stil.dersSecimi}>
          <SecimAlani etiket="Şablon" value={deger(seviye, grup ?? null)}
            aciklama="Seviyenin ya da bir şube grubunun (ör. 11 Sayısal) şablonu."
            onChange={(o) => {
              const [sv, g] = o.target.value.split(":");
              setParametreler(g ? { seviye: sv ?? "", grup: g } : { seviye: sv ?? "" });
            }}>
            {seviyeler.map((sv) =>
              seviyeGruplari(sv).length === 0 ? (
                <option key={sv} value={deger(sv, null)}>
                  {sv}. sınıflar ({subeler(sv, null).length} şube)
                </option>
              ) : (
                <optgroup key={sv} label={`${sv}. sınıf`}>
                  <option value={deger(sv, null)}>
                    {sv}. sınıflar ({subeler(sv, null).length} şube)
                  </option>
                  {seviyeGruplari(sv).map((g) => (
                    <option key={g.id} value={deger(sv, g)}>
                      {g.ad} grubu ({subeler(sv, g).length} şube)
                    </option>
                  ))}
                </optgroup>
              ),
            )}
          </SecimAlani>
        </div>
        {/* key: şablon değişince tablo taslağı ve rapor sıfırlansın. */}
        <SeviyeSablonu
          key={deger(seviye, grup ?? null)}
          seviye={seviye}
          grup={grup ?? null}
          satirlar={sablon.data.filter((s) => s.seviye === seviye && (s.sube_grubu_id ?? null) === grupId)}
          tumSatirlar={sablon.data}
          dersler={dersler.data}
          siniflar={siniflar.data}
          subeler={subeler(seviye, grup ?? null)}
          baskaSablonlu={grup ? [] : siniflar.data.filter((s) => s.seviye === seviye && !subeler(seviye, null).includes(s))}
          gruplar={gruplar.data}
          haftalikKapasite={ozet.data.haftalik_kapasite}
        />
      </>
    );
  }

  return (
    <>
      <SayfaBasligi baslik="Seviye şablonu">
        Bir seviyenin derslerini ve haftalık saatlerini bir kez girin, o seviyedeki bütün şubelere tek seferde
        uygulayın. Öğretmenleri sonra Ders dağılımı sayfasında seçersiniz.
      </SayfaBasligi>
      {icerik}
    </>
  );
}

type SablonProps = {
  seviye: number;
  /** Doluysa grubun şablonu; boşsa seviyenin. */
  grup: SubeGrubu | null;
  satirlar: SablonSatiri[];
  /** Okulun bütün şablon satırları ("Başka şablondan kopyala" için). */
  tumSatirlar: SablonSatiri[];
  dersler: Ders[];
  siniflar: Sinif[];
  /** Bu şablonu kullanan şubeler. */
  subeler: Sinif[];
  /** Seviyenin şablonunda: kendi grubunun şablonunu kullandığı için bu şablonun uygulanmadığı şubeler. */
  baskaSablonlu: Sinif[];
  gruplar: SubeGrubu[];
  haftalikKapasite: number;
};

type TopluRapor = Sema["SeviyeUygulamaRaporu"][];

/** Şablonun adı: "9. sınıflar" ya da "11 Sayısal grubu". */
function sablonEtiketi(seviye: number, grupId: string | null, gruplar: SubeGrubu[]): string {
  const g = grupId ? gruplar.find((x) => x.id === grupId) : undefined;
  return g ? `${g.ad} grubu` : `${seviye}. sınıflar`;
}

/** Tablodaki metinden saat: boş = 0 (şablonda yok). Geçersizse null. */
function saatOku(metin: string): number | null {
  if (metin.trim() === "") return 0;
  const n = Number(metin);
  return Number.isInteger(n) && n >= 0 && n <= 99 ? n : null;
}

type Taslak = Record<string, string>;
const taslakOlustur = (dersler: Ders[], satirlar: SablonSatiri[]): Taslak =>
  Object.fromEntries(
    dersler.map((d) => {
      const s = satirlar.find((x) => x.ders_id === d.id);
      return [d.id, s ? String(s.haftalik_saat) : ""];
    }),
  );

const anahtar = (sv: number, g: string | null | undefined) => `${sv}:${g ?? ""}`;

/**
 * Şablon, okulun bütün dersleri alt alta bir tablodur: saatler yazılır, "Şablonu kaydet" hepsini
 * tek istekte kaydeder (boş ya da 0: ders şablonda yok). Toplam ve kapasite yazdıkça güncellenir.
 * Kaydedilmemiş değişiklik varken şubelere uygulanamaz (uygulama kaydedilmiş şablonu kullanır).
 *
 * Taslak (yazılan metinler) yerel state'tir; kaydedilince sunucunun yanıtıyla yeniden kurulur.
 */
function SeviyeSablonu({ seviye, grup, satirlar, tumSatirlar, dersler, siniflar, subeler, baskaSablonlu, gruplar, haftalikKapasite }: SablonProps) {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const atamalarDegisti = useAtamalarDegisti();
  const [taslak, setTaslak] = useState<Taslak>(() => taslakOlustur(dersler, satirlar));
  const [kaydetHatasi, setKaydetHatasi] = useState<string>();
  const [kaynak, setKaynak] = useState("");
  const [kopyaOnayi, setKopyaOnayi] = useState(false);
  const [rapor, setRapor] = useState<SablonRaporu | null>(null);
  const [topluRapor, setTopluRapor] = useState<TopluRapor | null>(null);

  const sirali = turkceSirala(dersler, (d) => d.ad);
  const saatler = new Map(sirali.map((d) => [d.id, saatOku(taslak[d.id] ?? "")]));
  const toplam = [...saatler.values()].reduce<number>((t, n) => t + (n ?? 0), 0);
  const kayitli = taslakOlustur(dersler, satirlar);
  const degisti = sirali.some((d) => saatler.get(d.id) !== saatOku(kayitli[d.id] ?? ""));
  const dolu = sirali.some((d) => (saatler.get(d.id) ?? 0) > 0);

  // Kopyalanabilecek öteki (dolu) şablonlar.
  const buAnahtar = anahtar(seviye, grup?.id);
  const kaynaklar = [...new Set(tumSatirlar.map((s) => anahtar(s.seviye, s.sube_grubu_id)))]
    .filter((k) => k !== buAnahtar)
    .map((k) => {
      const [sv, g] = k.split(":");
      return { anahtar: k, seviye: Number(sv), ad: sablonEtiketi(Number(sv), g || null, gruplar) };
    })
    .sort((a, b) => a.seviye - b.seviye || a.ad.localeCompare(b.ad, "tr"));

  const subeAdlari = subeler.map((s) => s.ad).join(", ");
  const sablonAdi = grup ? `${grup.ad} grubunun şablonu` : `${seviye}. sınıf şablonu`;
  const grupAdi = (id: string | null | undefined) => gruplar.find((g) => g.id === id)?.ad;
  const kaynakAdi = kaynaklar.find((k) => k.anahtar === kaynak)?.ad ?? "";

  const kaydet = useMutation({
    mutationFn: (yeniler: { ders_id: string; haftalik_saat: number }[]) =>
      sablonApi.topluKaydet({ seviye, ...(grup ? { sube_grubu_id: grup.id } : {}), satirlar: yeniler }),
    onSuccess: async (yeniler) => {
      setTaslak(taslakOlustur(dersler, yeniler));
      await istemci.invalidateQueries({ queryKey: SABLON });
      const saat = yeniler.reduce((t, s) => t + s.haftalik_saat, 0);
      bildirim("basari", `${sablonAdi} kaydedildi: ${yeniler.length} ders, haftada ${saat} saat.`);
    },
    onError: (hata) => setKaydetHatasi(hataMetni(hata)),
  });

  const uygula = useMutation({
    mutationFn: () => sablonApi.uygula(seviye, grup?.id),
    onSuccess: async (sonuc) => {
      await atamalarDegisti();
      setTopluRapor(null);
      setRapor(sonuc);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  const hepsiniUygula = useMutation({
    mutationFn: sablonApi.hepsiniUygula,
    onSuccess: async (sonuc) => {
      await atamalarDegisti();
      setRapor(null);
      setTopluRapor(sonuc);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  function kaydetGonder(olay: FormEvent) {
    olay.preventDefault();
    const hatali = sirali.filter((d) => saatler.get(d.id) === null);
    if (hatali.length > 0) {
      setKaydetHatasi(`Haftalık saat 0 ile 99 arasında tam sayı olmalı: ${hatali.map((d) => d.ad).join(", ")}.`);
      return;
    }
    setKaydetHatasi(undefined);
    kaydet.mutate(sirali.map((d) => ({ ders_id: d.id, haftalik_saat: saatler.get(d.id) ?? 0 })));
  }

  function kopyala() {
    setTaslak(taslakOlustur(dersler, tumSatirlar.filter((s) => anahtar(s.seviye, s.sube_grubu_id) === kaynak)));
    setKopyaOnayi(false);
    bildirim("basari", `${kaynakAdi} şablonu tabloya kopyalandı. Kontrol edip “Şablonu kaydet”e basın.`);
  }

  return (
    <>
      <section aria-labelledby="sablon-baslik" className={sayfaStili.kart}>
        <h2 id="sablon-baslik">{grup ? `${grup.ad} grubunun dersleri` : `${seviye}. sınıfların dersleri`}</h2>
        <p className={stil.aciklama}>
          {grup ? (
            <>
              Bu şablon <strong>{grup.ad}</strong> grubuna ait
              {subeler.length > 0 ? ` (${subeAdlari})` : "; grupta henüz şube yok (Sınıflar sayfasından ekleyin)"}.
              {satirlar.length === 0 && ` Şablon boşken grubun şubeleri ${seviye}. sınıfların şablonunu kullanır.`}
            </>
          ) : (
            <>
              Bu şablon <strong>{seviye}. sınıflara</strong> ait.
              {baskaSablonlu.length > 0 &&
                ` ${baskaSablonlu.map((s) => `${s.ad} (${grupAdi(s.sube_grubu_id)})`).join(", ")} kendi grubunun şablonunu kullanır.`}
            </>
          )}{" "}
          Okulun bütün dersleri aşağıda: şablondaki derslerin haftalık saatini yazın, olmayanları boş bırakın.
        </p>

        {kaynaklar.length > 0 && (
          <div className={stil.ekleAlanlari}>
            <SecimAlani etiket="Başka şablondan kopyala" value={kaynak} onChange={(o) => setKaynak(o.target.value)}
              aciklama="Saatler tabloya gelir; kaydetmeden önce değiştirebilirsiniz.">
              <option value="">Şablon seçin</option>
              {kaynaklar.map((k) => (
                <option key={k.anahtar} value={k.anahtar}>
                  {k.ad}
                </option>
              ))}
            </SecimAlani>
            <Dugme ikon={<Copy />} tur="ikincil" className={stil.ekleDugmesi} disabled={!kaynak}
              onClick={() => (dolu ? setKopyaOnayi(true) : kopyala())}>
              Kopyala
            </Dugme>
          </div>
        )}

        <form onSubmit={kaydetGonder} noValidate>
          <FormHatasi mesaj={kaydetHatasi} />
          <Tablo<Ders>
            baslik={sablonAdi}
            satirlar={sirali}
            satirAnahtari={(d) => d.id}
            sutunlar={[
              {
                baslik: "Ders",
                hucre: (d) => <DersCipi ad={d.ad} renk={d.renk} isaret={dersIsaretleri(dersler).get(d.id)} />,
              },
              {
                baslik: "Haftalık saat",
                hucre: (d) => (
                  <input type="number" inputMode="numeric" min={0} max={99} placeholder="–"
                    aria-label={`${d.ad} haftalık saat`} aria-invalid={saatler.get(d.id) === null || undefined}
                    className={stil.saat} value={taslak[d.id] ?? ""}
                    onChange={(o) => setTaslak({ ...taslak, [d.id]: o.target.value })} />
                ),
              },
            ]}
          />
          <p className={toplam > haftalikKapasite ? stil.toplamAsim : stil.toplam}>
            {toplam > haftalikKapasite && <span aria-hidden="true">⚠ </span>}
            Haftalık toplam <strong>{toplam} saat</strong>; okulun haftalık kapasitesi {haftalikKapasite} saat.
            {toplam > haftalikKapasite && " Bu şablonla şubelerin programı üretilemez."}
          </p>
          <div className={stil.islemler}>
            <Dugme ikon={<Save />} type="submit" disabled={!degisti} yukleniyor={kaydet.isPending} yukleniyorMetni="Kaydediliyor...">
              Şablonu kaydet
            </Dugme>
            {degisti && (
              <Dugme tur="metin" onClick={() => { setTaslak(kayitli); setKaydetHatasi(undefined); }}>
                Değişiklikleri geri al
              </Dugme>
            )}
          </div>
        </form>
      </section>

      <section aria-labelledby="uygula-baslik" className={sayfaStili.kart}>
        <h2 id="uygula-baslik">Şubelere uygula</h2>
        {degisti && (
          <p className={stil.aciklama} role="status">
            Şablonda kaydedilmemiş değişiklik var; uygulamadan önce kaydedin.
          </p>
        )}
        {subeler.length === 0 ? (
          <p className={stil.aciklama}>
            {grup
              ? `${grup.ad} grubunda şube yok. Sınıflar sayfasından şubeleri bu gruba alınca şablon uygulanabilir.`
              : `Okulda bu şablonu kullanan ${seviye}. sınıf şubesi yok. Şube eklenince şablon uygulanabilir.`}
          </p>
        ) : (
          <p className={stil.aciklama}>
            Şablondaki dersler {subeler.length} şubeye ({subeAdlari}) öğretmeni boş olarak eklenir. Şubede zaten olan
            dersler değiştirilmez; saati farklı olanlar size gösterilir. Şablonda olmayan dersler şubelerden
            kaldırılmaz. Bir şubenin almadığı ders (ders dağılımında “Bu şube almaz”) eklenmez. “Tüm seviyelere
            uygula” okulun bütün şablonlarını kendi şubelerine aynı kurallarla uygular.
          </p>
        )}
        <div className={stil.islemler}>
          {subeler.length > 0 && (
            <Dugme ikon={<WandSparkles />} disabled={satirlar.length === 0 || degisti} yukleniyor={uygula.isPending}
              yukleniyorMetni="Uygulanıyor..." onClick={() => uygula.mutate()}>
              {grup ? `${grup.ad} şubelerine uygula` : `${seviye}. sınıf şubelerine uygula`}
            </Dugme>
          )}
          <Dugme ikon={<Layers />} tur="ikincil" disabled={tumSatirlar.length === 0 || degisti}
            yukleniyor={hepsiniUygula.isPending} yukleniyorMetni="Uygulanıyor..." onClick={() => hepsiniUygula.mutate()}>
            Tüm seviyelere uygula
          </Dugme>
        </div>
        {rapor && (
          <UygulamaRaporu baslik="Şablon uygulandı" onKapat={() => setRapor(null)}>
            <RaporAyrintisi rapor={rapor} siniflar={siniflar} dersler={dersler} />
          </UygulamaRaporu>
        )}
        {topluRapor && (
          <UygulamaRaporu baslik={`${topluRapor.length} şablon uygulandı`} onKapat={() => setTopluRapor(null)}>
            {topluRapor.map((r) => (
              <section key={anahtar(r.seviye, r.sube_grubu_id)} aria-label={r.sablon} className={stil.raporBolumu}>
                <h4 className={stil.raporAltBasligi}>{r.sablon}</h4>
                <RaporAyrintisi rapor={r.sonuc} siniflar={siniflar} dersler={dersler} baskaSablonluGoster={false} />
              </section>
            ))}
          </UygulamaRaporu>
        )}
      </section>

      <OnayPenceresi
        acik={kopyaOnayi}
        baslik={`${sablonAdi} dolu`}
        mesaj={`Tablodaki saatler ${kaynakAdi} şablonundakilerle değiştirilecek. Kaydetmeden önce kontrol edebilirsiniz; kaydetmezseniz şablon değişmez.`}
        onaylaMetni="Kopyala"
        onOnayla={kopyala}
        onVazgec={() => setKopyaOnayi(false)}
      />
    </>
  );
}

/**
 * Uygulama raporunun çerçevesi. Rapor görününce odak başlığına taşınır: düğmeye basan klavye ve
 * ekran okuyucu kullanıcısı sonucu hemen duyar ve tablonun içinde gezinebilir.
 */
function UygulamaRaporu({ baslik, onKapat, children }: { baslik: string; onKapat: () => void; children: ReactNode }) {
  const baslikRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    baslikRef.current?.focus();
  }, [baslik]);
  return (
    <div className={stil.rapor}>
      <h3 ref={baslikRef} tabIndex={-1} className={stil.raporBasligi}>
        {baslik}
      </h3>
      {children}
      <Dugme tur="metin" onClick={onKapat}>
        Raporu kapat
      </Dugme>
    </div>
  );
}

/**
 * Bir şablonun uygulama sonucu, kullanıcının diliyle: kaç şube, kaç atama oluşturuldu, kaçı zaten
 * vardı, hangilerinin saati şablondan farklı (değiştirilmedi; tek tıkla şablondaki saate çekilir).
 */
function RaporAyrintisi({ rapor, siniflar, dersler, baskaSablonluGoster = true }: {
  rapor: SablonRaporu;
  siniflar: Sinif[];
  dersler: Ders[];
  baskaSablonluGoster?: boolean;
}) {
  const bildirim = useBildirim();
  const atamalarDegisti = useAtamalarDegisti();
  const [duzeltilen, setDuzeltilen] = useState<Set<string>>(new Set());

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

  const ilkSube = siniflar.find((s) => s.ad === rapor.subeler[0]);
  return (
    <>
      <ul className={stil.raporListesi}>
        <li>
          {rapor.sube_sayisi === 0 ? (
            <>Bu şablonu kullanan şube yok.</>
          ) : rapor.olusturulan > 0 ? (
            <>
              <strong>{rapor.sube_sayisi} şubeye toplam {rapor.olusturulan} ders eklendi</strong> (
              {rapor.subeler.join(", ")}). Öğretmenleri henüz seçilmedi.{" "}
              {ilkSube && <Link to={`/ders-dagilimi?gorunum=sube&sinif=${ilkSube.id}`}>Ders dağılımında öğretmen seçin</Link>}
            </>
          ) : (
            <>Eklenecek yeni ders yoktu: şablondaki derslerin hepsi şubelerde zaten var.</>
          )}
        </li>
        {rapor.zaten_var > 0 && <li>{rapor.zaten_var} ders şubelerde zaten vardı; değiştirilmedi.</li>}
        {rapor.istisna_atlanan.length > 0 && (
          <li>
            Şubenin almadığı {rapor.istisna_atlanan.length} ders eklenmedi (istisna):{" "}
            {rapor.istisna_atlanan.map((i) => `${i.sinif} ${i.ders}`).join(", ")}.
          </li>
        )}
        {rapor.istisna_ek.length > 0 && (
          <li>
            Şubelerin ek dersleri: {rapor.istisna_ek.map((i) => `${i.sinif} ${i.ders} (${i.haftalik_saat} saat${i.eklendi ? ", eklendi" : ""})`).join(", ")}.
          </li>
        )}
        {baskaSablonluGoster && rapor.baska_sablonlu.length > 0 && (
          <li>
            Kendi şablonunu kullandığı için dokunulmayan şubeler:{" "}
            {rapor.baska_sablonlu.map((b) => `${b.sinif} (${b.sablon})`).join(", ")}.
          </li>
        )}
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
    </>
  );
}
