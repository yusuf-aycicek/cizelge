import { Plus, Trash2 } from "lucide-react";
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
import { atamaApi, useAtamalarDegisti, type Atama } from "./veri";

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
  const [yeni, setYeni] = useState({ ders_id: "", saat: "" });
  const [yeniHatasi, setYeniHatasi] = useState<string>();

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

  const ekle = useMutation({
    mutationFn: (d: { ders_id: string; haftalik_saat: number }) =>
      atamaApi.olustur({ sinif_id: sinif.id, ders_id: d.ders_id, haftalik_saat: d.haftalik_saat, ogretmen_id: null }),
    onSuccess: async (sonuc) => {
      await atamalarDegisti();
      bildirim("basari", `${dersAdi(sonuc)}, ${sinif.ad} şubesine eklendi. Öğretmenini seçin.`);
      setYeni({ ders_id: "", saat: "" });
    },
    onError: (hata) => setYeniHatasi(hataMetni(hata)),
  });

  const kaldir = useMutation({
    mutationFn: (a: Atama) => atamaApi.sil(a.id),
    onSuccess: async (_, a) => {
      await atamalarDegisti();
      bildirim("basari", `${dersAdi(a)}, ${sinif.ad} şubesinden kaldırıldı.`);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
    onSettled: () => setKaldirilacak(null),
  });

  function ekleGonder(olay: FormEvent) {
    olay.preventDefault();
    const saat = Number(yeni.saat);
    if (!yeni.ders_id) return setYeniHatasi("Eklenecek dersi seçin.");
    if (!Number.isInteger(saat) || saat < 1) return setYeniHatasi("Haftalık saat en az 1 olmalı.");
    setYeniHatasi(undefined);
    ekle.mutate({ ders_id: yeni.ders_id, haftalik_saat: saat });
  }

  const mesgul = (a: Atama) => guncelle.isPending && guncelle.variables?.atama.id === a.id;

  return (
    <section aria-labelledby="sube-baslik" className={stil.subePaneli}>
      <h2 id="sube-baslik">{sinif.ad} şubesinin dersleri</h2>

      {atamalar.length === 0 ? (
        <div className={stil.bosDurum}>
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
                  {dersAdi(a)}
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
                  <Dugme tur="metin" onClick={() => git({ gorunum: "ders", ders: a.ders_id })}
                    aria-label={`${dersAdi(a)} dersini bütün şubelerde göster`}>
                    Bütün şubeler
                  </Dugme>
                  <Dugme ikon={<Trash2 />} tur="metin" onClick={() => setKaldirilacak(a)} aria-label={`${dersAdi(a)} dersini kaldır`}>
                    Kaldır
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
        onOnayla={() => kaldirilacak && kaldir.mutate(kaldirilacak)}
        onVazgec={() => setKaldirilacak(null)}
      />
    </section>
  );
}
