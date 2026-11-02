import { Illustrasyon } from "../bilesenler/Illustrasyon";
import { DersCipi } from "../dersler/DersCipi";
import { Ban, Plus, Rows3, Trash2, Undo2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { hataMetni } from "../api/hata";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { Tablo } from "../bilesenler/Tablo";
import type { Sinif } from "../listeler/kaynaklar";
import { turkceSirala } from "../metin";
import stil from "./Dagilim.module.css";
import type { DagilimVerisi, Git } from "./DersDagilimiSayfasi";
import { OgretmenSecici } from "./OgretmenSecici";
import { SaatGirdisi } from "./SaatGirdisi";
import {
  atamaApi, istisnaApi, subeninSablonu, useAtamalarDegisti, useIstisnalar, useSablon, type Atama, type Istisna,
} from "./veri";

/**
 * Şube görünümü: solda şubeler (toplam saat, öğretmensiz ders sayısı), sağda seçili şubenin
 * dersleri. Seçili şube sayfadan gelir (`sinifId`); bu bileşen yalnızca `git` ile değiştirir.
 */
export function SubeGorunumu({ veri, sinifId, git }: { veri: DagilimVerisi; sinifId: string | null; git: Git }) {
  // Sıralama burada her çizimde yapılır; useMemo gerekmez: 24 şubeyi sıralamak mikrosaniyeler sürer.
  const siniflar = turkceSirala(veri.siniflar, (s) => s.ad);
  const secili = siniflar.find((s) => s.id === sinifId) ?? siniflar[0];
  if (!secili) return null; // sayfa şubesiz okulda bu görünümü çizmez

  return (
    <div className={stil.ikiSutun}>
      <nav aria-label="Şubeler">
        <ul className={stil.subeListesi}>
          {siniflar.map((s) => {
            const y = veri.sinifYukleri.get(s.id);
            return (
              <li key={s.id}>
                <button
                  type="button"
                  className={stil.subeDugmesi}
                  aria-current={s.id === secili.id ? "true" : undefined}
                  onClick={() => git({ gorunum: "sube", sinif: s.id })}
                >
                  <span className={stil.subeAdi}>{s.ad}</span>
                  {y && (
                    <span className={y.asim ? stil.asimMetni : stil.ikincil}>
                      {y.ders_saati}/{y.kapasite} saat{y.asim ? ", kapasite aşıldı" : ""}
                    </span>
                  )}
                  {y && y.ogretmensiz_atama > 0 && (
                    <span className={stil.rozet}>
                      <span aria-hidden="true">⚠ </span>
                      {y.ogretmensiz_atama} öğretmensiz
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      {/* key: başka şube seçilince form ve onay penceresi durumu sıfırdan başlasın. */}
      <SubeDersleri key={secili.id} veri={veri} sinif={secili} git={git} />
    </div>
  );
}

function SubeDersleri({ veri, sinif, git }: { veri: DagilimVerisi; sinif: Sinif; git: Git }) {
  const bildirim = useBildirim();
  const atamalarDegisti = useAtamalarDegisti();
  const [kaldirilacak, setKaldirilacak] = useState<Atama | null>(null);
  // Kaldırırken "bu şube bu dersi hiç almasın" (almaz istisnası); şablondaki derste açık başlar.
  const [almaz, setAlmaz] = useState(true);
  const [yeni, setYeni] = useState({ ders_id: "", saat: "" });
  const [ekDers, setEkDers] = useState(true);
  const [yeniHatasi, setYeniHatasi] = useState<string>();
  const sablon = subeninSablonu(sinif, useSablon().data ?? []);
  const istisnalar = (useIstisnalar().data ?? []).filter((i) => i.sinif_id === sinif.id);
  const ekMi = (dersId: string) => istisnalar.some((i) => i.ders_id === dersId && i.tur === "ek");

  const dersAdi = (a: Atama) => veri.ders.get(a.ders_id)?.ad ?? "";
  const atamalar = turkceSirala(
    veri.atamalar.filter((a) => a.sinif_id === sinif.id),
    dersAdi,
  );
  const yuk = veri.sinifYukleri.get(sinif.id);
  const eklenebilir = turkceSirala(
    veri.dersler.filter((d) => !atamalar.some((a) => a.ders_id === d.id)),
    (d) => d.ad,
  );

  const guncelle = useMutation({
    mutationFn: (d: { atama: Atama; degisiklik: { ogretmen_id?: string | null; haftalik_saat?: number } }) =>
      atamaApi.guncelle(d.atama.id, d.degisiklik),
    onSuccess: async (sonuc, { atama, degisiklik }) => {
      const ogretmenYuku = await atamalarDegisti(sonuc.ogretmen_id);
      const ad = `${sinif.ad} ${dersAdi(atama)}`;
      if ("ogretmen_id" in degisiklik) {
        const ogretmen = sonuc.ogretmen_id ? veri.ogretmen.get(sonuc.ogretmen_id)?.ad : null;
        bildirim("basari", ogretmen ? `${ad}: ${ogretmen} seçildi.` : `${ad}: öğretmen seçimi kaldırıldı.`);
      } else {
        bildirim("basari", `${ad}: haftada ${sonuc.haftalik_saat} saat olarak kaydedildi.`);
      }
      // Erken uyarı: bu değişiklikle öğretmenin kapasitesi aşıldıysa hemen söyle.
      if (ogretmenYuku?.asim && ogretmenYuku.mesaj) bildirim("uyari", ogretmenYuku.mesaj);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  // Şablonda olmayan ders "ek ders" istisnasıyla eklenir: istisna dersi de ekler (tek istek).
  const ekle = useMutation({
    mutationFn: async (d: { ders_id: string; haftalik_saat: number; ek: boolean }) => {
      if (d.ek) {
        await istisnaApi.olustur({ sinif_id: sinif.id, ders_id: d.ders_id, tur: "ek", haftalik_saat: d.haftalik_saat });
      } else {
        await atamaApi.olustur({ sinif_id: sinif.id, ders_id: d.ders_id, haftalik_saat: d.haftalik_saat, ogretmen_id: null });
      }
      return d;
    },
    onSuccess: async (d) => {
      await atamalarDegisti();
      const ad = veri.ders.get(d.ders_id)?.ad ?? "";
      bildirim("basari", `${ad}, ${sinif.ad} şubesine${d.ek ? " ek ders olarak" : ""} eklendi. Öğretmenini seçin.`);
      setYeni({ ders_id: "", saat: "" });
    },
    onError: (hata) => setYeniHatasi(hataMetni(hata)),
  });

  // "Almaz" istisnası dersi de kaldırır (tek istek); yoksa yalnızca ders kaldırılır.
  const kaldir = useMutation({
    mutationFn: async (d: { atama: Atama; almaz: boolean }) => {
      if (d.almaz) await istisnaApi.olustur({ sinif_id: sinif.id, ders_id: d.atama.ders_id, tur: "almaz" });
      else await atamaApi.sil(d.atama.id);
    },
    onSuccess: async (_, d) => {
      await atamalarDegisti();
      bildirim("basari", d.almaz
        ? `${sinif.ad} artık ${dersAdi(d.atama)} almıyor; şablon yeniden uygulansa da eklenmez.`
        : `${dersAdi(d.atama)}, ${sinif.ad} şubesinden kaldırıldı.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
    onSettled: () => setKaldirilacak(null),
  });

  const istisnaKaldir = useMutation({
    mutationFn: (i: Istisna) => istisnaApi.sil(i.id),
    onSuccess: async (sonuc, i) => {
      await atamalarDegisti();
      bildirim("basari", i.tur === "almaz"
        ? sonuc.geri_eklenen_saat
          ? `${i.ders_adi}, şablondaki ${sonuc.geri_eklenen_saat} saatle ${sinif.ad} şubesine geri eklendi. Öğretmenini seçin.`
          : `${sinif.ad} için “${i.ders_adi} almaz” işareti kaldırıldı.`
        : `${i.ders_adi} artık ${sinif.ad} şubesinin ek dersi olarak işaretli değil; ders şubede kalır.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  function ekleGonder(olay: FormEvent) {
    olay.preventDefault();
    const saat = Number(yeni.saat);
    if (!yeni.ders_id) return setYeniHatasi("Eklenecek dersi seçin.");
    if (!Number.isInteger(saat) || saat < 1) return setYeniHatasi("Haftalık saat en az 1 olmalı.");
    setYeniHatasi(undefined);
    ekle.mutate({ ders_id: yeni.ders_id, haftalik_saat: saat, ek: sablondaYok && ekDers });
  }
  const sablondaYok = Boolean(yeni.ders_id) && sablon.size > 0 && !sablon.has(yeni.ders_id);
  const kaldirilacakSablonda = kaldirilacak ? sablon.has(kaldirilacak.ders_id) : false;

  const mesgul = (a: Atama) => guncelle.isPending && guncelle.variables?.atama.id === a.id;

  return (
    <section aria-labelledby="sube-baslik" className={stil.subePaneli}>
      <h2 id="sube-baslik">{sinif.ad} şubesinin dersleri</h2>

      {atamalar.length === 0 ? (
        <div className={stil.bosDurum}>
          <Illustrasyon tur="ders" />
          <p>
            <strong>{sinif.ad} şubesine henüz ders eklenmedi.</strong>
          </p>
          <p>
            {sinif.seviye}. sınıfların derslerini seviye şablonunda bir kez girip bütün {sinif.seviye}. sınıf
            şubelerine uygulayabilirsiniz:{" "}
            <Link to={`/seviye-sablonu?seviye=${sinif.seviye}`}>{sinif.seviye}. sınıf şablonunu aç</Link>. Ya da
            aşağıdan tek tek ekleyin.
          </p>
        </div>
      ) : (
        <Tablo<Atama>
          baslik={`${sinif.ad} dersleri`}
          satirlar={atamalar}
          satirAnahtari={(a) => a.id}
          satirSinifi={(a) => (a.ogretmen_id ? undefined : stil.eksikSatir)}
          sutunlar={[
            {
              baslik: "Ders",
              hucre: (a) => (
                <>
                  <DersCipi ad={dersAdi(a)} renk={veri.ders.get(a.ders_id)?.renk} isaret={veri.dersIsareti.get(a.ders_id)} />
                  {ekMi(a.ders_id) && <span className={stil.ekRozet}>Ek ders</span>}
                  {!a.ogretmen_id && (
                    <span className={stil.eksikRozet}>
                      <span aria-hidden="true">⚠ </span>Öğretmen seçilmedi
                    </span>
                  )}
                </>
              ),
            },
            {
              baslik: "Haftalık saat",
              hucre: (a) => (
                <SaatGirdisi
                  key={`${a.id}-${a.haftalik_saat}`}
                  etiket={`${sinif.ad} ${dersAdi(a)} haftalık saat`}
                  deger={a.haftalik_saat}
                  disabled={mesgul(a)}
                  onKaydet={(haftalik_saat) => guncelle.mutate({ atama: a, degisiklik: { haftalik_saat } })}
                />
              ),
            },
            {
              baslik: "Öğretmen",
              hucre: (a) => (
                <OgretmenSecici
                  etiket={`${sinif.ad} ${dersAdi(a)} öğretmeni`}
                  ders={veri.ders.get(a.ders_id)}
                  ogretmenler={veri.ogretmenler}
                  yukler={veri.ogretmenYukleri}
                  deger={a.ogretmen_id}
                  disabled={mesgul(a)}
                  onDegis={(ogretmen_id) => guncelle.mutate({ atama: a, degisiklik: { ogretmen_id } })}
                />
              ),
            },
            {
              baslik: "İşlemler",
              baslikGizli: true,
              hizala: "sag",
              hucre: (a) => (
                <span className={stil.islemler}>
                  <Dugme tur="metin" ikon={<Rows3 />} onClick={() => git({ gorunum: "ders", ders: a.ders_id })}
                    aria-label={`${dersAdi(a)} dersini bütün şubelerde göster`} title="Bu dersi bütün şubelerde göster">
                    <span className={stil.uzunMetin}>Bütün şubeler</span>
                    <span className={stil.kisaMetin}>Şubeler</span>
                  </Dugme>
                  <Dugme ikon={<Trash2 />} tur="metin" onClick={() => { setAlmaz(true); setKaldirilacak(a); }}
                    aria-label={`${dersAdi(a)} dersini kaldır`} title="Dersi bu şubeden kaldır">
                    <span className={stil.uzunMetin}>Kaldır</span>
                  </Dugme>
                </span>
              ),
            },
          ]}
        />
      )}

      {yuk && (
        <p className={yuk.asim ? stil.toplamAsim : stil.toplam}>
          {yuk.asim ? (
            <>
              <span aria-hidden="true">⚠ </span>
              {yuk.mesaj}
            </>
          ) : (
            <>
              Toplam <strong>{yuk.ders_saati} saat</strong>; haftalık kapasite {yuk.kapasite} saat.
              {yuk.ogretmensiz_atama > 0 && ` ${yuk.ogretmensiz_atama} dersin öğretmeni seçilmedi.`}
            </>
          )}
        </p>
      )}

      {istisnalar.length > 0 && (
        <div className={stil.istisnalar}>
          <h3 className={stil.formBasligi}>Bu şubeye özel</h3>
          <ul>
            {istisnalar.map((i) => (
              <li key={i.id}>
                <span>
                  {i.tur === "almaz" ? (
                    <><Ban aria-hidden="true" className={stil.istisnaIkonu} /> <strong>{i.ders_adi}</strong> almaz</>
                  ) : (
                    <><Plus aria-hidden="true" className={stil.istisnaIkonu} /> <strong>{i.ders_adi}</strong> ek ders, haftada {i.haftalik_saat} saat</>
                  )}
                  {i.uyari && (
                    <span className={stil.istisnaUyarisi}>
                      <span aria-hidden="true">⚠ </span>
                      {i.uyari}
                    </span>
                  )}
                </span>
                <Dugme ikon={<Undo2 />} tur="metin" yukleniyor={istisnaKaldir.isPending && istisnaKaldir.variables?.id === i.id}
                  onClick={() => istisnaKaldir.mutate(i)}
                  aria-label={i.tur === "almaz" ? `${i.ders_adi}: “almaz” işaretini kaldır` : `${i.ders_adi}: ek ders işaretini kaldır`}>
                  {i.tur === "almaz" ? "Geri al" : "İşareti kaldır"}
                </Dugme>
              </li>
            ))}
          </ul>
        </div>
      )}

      <form onSubmit={ekleGonder} className={stil.ekleFormu} noValidate>
        <h3 className={stil.formBasligi}>Ders ekle</h3>
        <div className={stil.ekleAlanlari}>
          <SecimAlani etiket="Ders" value={yeni.ders_id} hata={yeniHatasi}
            onChange={(o) => setYeni({ ...yeni, ders_id: o.target.value })}>
            <option value="">Ders seçin</option>
            {eklenebilir.map((d) => (
              <option key={d.id} value={d.id}>
                {d.ad}
              </option>
            ))}
          </SecimAlani>
          <MetinAlani etiket="Haftalık saat" type="number" inputMode="numeric" min={1} value={yeni.saat}
            onChange={(o) => setYeni({ ...yeni, saat: o.target.value })} />
          <Dugme ikon={<Plus />} type="submit" className={stil.ekleDugmesi} yukleniyor={ekle.isPending} yukleniyorMetni="Ekleniyor...">
            Ekle
          </Dugme>
        </div>
        {sablondaYok && (
          <label className={stil.onayKutusu}>
            <input type="checkbox" checked={ekDers} onChange={(o) => setEkDers(o.target.checked)} />
            Bu ders şubenin şablonunda yok: ek ders olarak kaydet (şablon yeniden uygulandığında da korunur)
          </label>
        )}
      </form>

      <OnayPenceresi
        acik={kaldirilacak !== null}
        baslik={kaldirilacak ? `${dersAdi(kaldirilacak)} dersi kaldırılsın mı?` : ""}
        mesaj={
          kaldirilacak
            ? `${sinif.ad} şubesinin ${dersAdi(kaldirilacak)} dersi (haftada ${kaldirilacak.haftalik_saat} saat) ders dağılımından çıkarılacak.`
            : ""
        }
        onaylaMetni="Kaldır"
        tehlikeli
        yukleniyor={kaldir.isPending}
        onOnayla={() => kaldirilacak && kaldir.mutate({ atama: kaldirilacak, almaz: kaldirilacakSablonda && almaz })}
        onVazgec={() => setKaldirilacak(null)}
      >
        {kaldirilacak && kaldirilacakSablonda && (
          <label className={stil.onayKutusu}>
            <input type="checkbox" checked={almaz} onChange={(o) => setAlmaz(o.target.checked)} />
            {sinif.ad} bu dersi hiç almasın (şablon yeniden uygulandığında geri gelmez)
          </label>
        )}
      </OnayPenceresi>
    </section>
  );
}
