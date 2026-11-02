import { Check, ListChecks } from "lucide-react";
import { BosDurum } from "../bilesenler/BosDurum";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { hataMetni } from "../api/hata";
import { SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { Tablo } from "../bilesenler/Tablo";
import { turkceSirala } from "../metin";
import stil from "./Dagilim.module.css";
import type { DagilimVerisi, Git } from "./DersDagilimiSayfasi";
import { OgretmenSecici } from "./OgretmenSecici";
import { atamaApi, useAtamalarDegisti, type Atama } from "./veri";

/**
 * Ders görünümü: bir dersin bütün şubeleri alt alta. Aynı dersi birden fazla şubede aynı öğretmene
 * vermenin kolay yolu: şubeleri işaretle, öğretmeni seç, "Seçilen şubelere ver". Tek istek, tek
 * işlem (`POST /atamalar/toplu-ogretmen`): ya hepsi değişir ya hiçbiri.
 */
export function DersGorunumu({ veri, dersId, git }: { veri: DagilimVerisi; dersId: string | null; git: Git }) {
  const dersler = turkceSirala(
    veri.dersler.filter((d) => veri.atamalar.some((a) => a.ders_id === d.id)),
    (d) => d.ad,
  );
  const ders = dersler.find((d) => d.id === dersId) ?? dersler[0];
  if (!ders) {
    return (
      <BosDurum cizim="ders" boyut="kucuk" baslikDuzeyi={3} baslik="Henüz hiçbir şubeye ders eklenmedi">
        <p>Önce seviye şablonunu uygulayın ya da şube görünümünden ders ekleyin.</p>
      </BosDurum>
    );
  }
  const subeSayisi = (id: string) => veri.atamalar.filter((a) => a.ders_id === id).length;

  return (
    <>
      <div className={stil.dersSecimi}>
        <SecimAlani etiket="Ders" value={ders.id} onChange={(o) => git({ gorunum: "ders", ders: o.target.value })}>
          {dersler.map((d) => (
            <option key={d.id} value={d.id}>
              {d.ad} ({subeSayisi(d.id)} şube)
            </option>
          ))}
        </SecimAlani>
      </div>
      {/* key: ders değişince işaretli şubeler ve seçilen öğretmen sıfırlansın. */}
      <DersinSubeleri key={ders.id} veri={veri} dersId={ders.id} />
    </>
  );
}

function DersinSubeleri({ veri, dersId }: { veri: DagilimVerisi; dersId: string }) {
  const bildirim = useBildirim();
  const atamalarDegisti = useAtamalarDegisti();
  const ders = veri.ders.get(dersId);
  const sinifAdi = (a: Atama) => veri.sinif.get(a.sinif_id)?.ad ?? "";
  const atamalar = turkceSirala(
    veri.atamalar.filter((a) => a.ders_id === dersId),
    sinifAdi,
  );

  const [secili, setSecili] = useState<Set<string>>(new Set());
  const [topluOgretmen, setTopluOgretmen] = useState<string | null>(null);
  const hepsi = atamalar.length > 0 && atamalar.every((a) => secili.has(a.id));
  const bazisi = !hepsi && atamalar.some((a) => secili.has(a.id));

  // "Tümünü seç" kutusunun yarı dolu hali (indeterminate) HTML'de bir özellik değil, DOM'da
  // bir alandır; React prop olarak veremez. Bu yüzden ref ile DOM'a yazılır: React'in dışındaki
  // dünyayla (DOM) senkronizasyon, effect'in asıl kullanım yeri.
  const tumuKutusu = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (tumuKutusu.current) tumuKutusu.current.indeterminate = bazisi;
  }, [bazisi]);

  function isaretle(id: string, isaretli: boolean) {
    setSecili((onceki) => {
      const yeni = new Set(onceki);
      if (isaretli) yeni.add(id);
      else yeni.delete(id);
      return yeni;
    });
  }

  const tekli = useMutation({
    mutationFn: (d: { atama: Atama; ogretmen_id: string | null }) =>
      atamaApi.guncelle(d.atama.id, { ogretmen_id: d.ogretmen_id }),
    onSuccess: async (sonuc, { atama }) => {
      const yuk = await atamalarDegisti(sonuc.ogretmen_id);
      const ogretmen = sonuc.ogretmen_id ? veri.ogretmen.get(sonuc.ogretmen_id)?.ad : null;
      const ad = `${sinifAdi(atama)} ${ders?.ad}`;
      bildirim("basari", ogretmen ? `${ad}: ${ogretmen} seçildi.` : `${ad}: öğretmen seçimi kaldırıldı.`);
      if (yuk?.asim && yuk.mesaj) bildirim("uyari", yuk.mesaj);
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  const toplu = useMutation({
    mutationFn: (d: { idler: string[]; ogretmen_id: string | null }) =>
      atamaApi.topluOgretmen({ atama_idleri: d.idler, ogretmen_id: d.ogretmen_id }),
    onSuccess: async (sonuc, { ogretmen_id }) => {
      const yuk = await atamalarDegisti(ogretmen_id);
      const subeler = turkceSirala(sonuc, sinifAdi).map(sinifAdi).join(", ");
      const ogretmen = ogretmen_id ? veri.ogretmen.get(ogretmen_id)?.ad : null;
      bildirim(
        "basari",
        ogretmen
          ? `${ders?.ad} dersinin öğretmeni ${sonuc.length} şubede (${subeler}) ${ogretmen} olarak kaydedildi.`
          : `${ders?.ad} dersinin öğretmen seçimi ${sonuc.length} şubede (${subeler}) kaldırıldı.`,
      );
      if (yuk?.asim && yuk.mesaj) bildirim("uyari", yuk.mesaj);
      setSecili(new Set());
    },
    onError: (hata) => bildirim("hata", hataMetni(hata)),
  });

  const ogretmensizler = atamalar.filter((a) => !a.ogretmen_id);

  return (
    <>
      <section aria-labelledby="toplu-baslik" className={stil.toplu}>
        <h2 id="toplu-baslik" className={stil.formBasligi}>
          Birden fazla şubeye aynı öğretmen
        </h2>
        <p className={stil.aciklama}>
          Aşağıdaki tablodan şubeleri işaretleyin, öğretmeni seçin ve verin.
          {ogretmensizler.length > 0 && ` ${ogretmensizler.length} şubede öğretmen seçilmedi.`}
        </p>
        <div className={stil.topluSatir}>
          <OgretmenSecici
            etiket="İşaretli şubelere verilecek öğretmen"
            ders={ders}
            ogretmenler={veri.ogretmenler}
            yukler={veri.ogretmenYukleri}
            deger={topluOgretmen}
            onDegis={setTopluOgretmen}
            bosMetin="Öğretmen seçin"
          />
          <Dugme ikon={<Check />}
            disabled={secili.size === 0 || !topluOgretmen}
            yukleniyor={toplu.isPending}
            yukleniyorMetni="Veriliyor..."
            onClick={() => toplu.mutate({ idler: [...secili], ogretmen_id: topluOgretmen })}
          >
            İşaretli {secili.size} şubeye ver
          </Dugme>
          {ogretmensizler.length > 0 && (
            <Dugme ikon={<ListChecks />} tur="ikincil" onClick={() => setSecili(new Set(ogretmensizler.map((a) => a.id)))}>
              Öğretmeni seçilmemişleri işaretle
            </Dugme>
          )}
        </div>
      </section>

      <Tablo<Atama>
        baslik={`${ders?.ad} dersinin şubeleri`}
        satirlar={atamalar}
        satirAnahtari={(a) => a.id}
        satirSinifi={(a) => (a.ogretmen_id ? undefined : stil.eksikSatir)}
        sutunlar={[
          {
            baslik: "Seç",
            baslikIcerik: (
              <input
                ref={tumuKutusu}
                type="checkbox"
                className={stil.kutu}
                aria-label="Bütün şubeleri işaretle"
                checked={hepsi}
                onChange={(o) => setSecili(o.target.checked ? new Set(atamalar.map((a) => a.id)) : new Set())}
              />
            ),
            hucre: (a) => (
              <input
                type="checkbox"
                className={stil.kutu}
                aria-label={`${sinifAdi(a)} işaretle`}
                checked={secili.has(a.id)}
                onChange={(o) => isaretle(a.id, o.target.checked)}
              />
            ),
          },
          { baslik: "Şube", hucre: sinifAdi },
          { baslik: "Haftalık saat", hucre: (a) => `${a.haftalik_saat} saat` },
          {
            baslik: "Öğretmen",
            hucre: (a) => (
              <OgretmenSecici
                etiket={`${sinifAdi(a)} ${ders?.ad} öğretmeni`}
                ders={ders}
                ogretmenler={veri.ogretmenler}
                yukler={veri.ogretmenYukleri}
                deger={a.ogretmen_id}
                disabled={tekli.isPending && tekli.variables?.atama.id === a.id}
                onDegis={(ogretmen_id) => tekli.mutate({ atama: a, ogretmen_id })}
              />
            ),
          },
        ]}
      />
    </>
  );
}
