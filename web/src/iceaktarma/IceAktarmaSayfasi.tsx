/**
 * Excel'den içe aktarma (8a, ADR 0021). Üç adım: şablonu indir, dosyayı seç, önizlemeyi onayla.
 *
 * Dosya seçilince sunucu yalnızca **önizler** (hiçbir şey yazmaz): her sayfada eklenecek,
 * güncellenecek ve hatalı satırlar. Hatalı satır varsa "Kaydet" pasiftir; kullanıcı dosyayı düzeltip
 * yeniden seçer. Onaylanınca aynı dosya önizlemenin özetiyle (`ozet`) gönderilir; sunucu planı
 * yeniden hesaplar, önizlemedekinden farklıysa (veri arada değiştiyse) kaydetmez.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileSpreadsheet, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./IceAktarma.module.css";

type Onizleme = components["schemas"]["IceAktarmaOnizleme"];
type Sayfa = components["schemas"]["IceAktarmaSayfasi"];
type Satir = components["schemas"]["IceAktarmaSatiri"];

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
export const SABLON_ADRESI = "/api/ders-programi/ice-aktarma/sablon.xlsx";

/** Dosyanın kendisi istek gövdesidir (multipart değil): openapi-fetch'in JSON'a çevirmesi kapatılır. */
const dosyaGovdesi = (dosya: File) => ({
  body: dosya as unknown as string,
  bodySerializer: (b: unknown) => b as BodyInit,
  headers: { "Content-Type": XLSX },
});

const sayi = (n: number, ad: string) => `${n} ${ad}`;

export function ozetMetni(o: Onizleme): string {
  const parcalar = [];
  if (o.eklenecek_sayisi) parcalar.push(sayi(o.eklenecek_sayisi, "kayıt eklenecek"));
  if (o.guncellenecek_sayisi) parcalar.push(sayi(o.guncellenecek_sayisi, "kayıt güncellenecek"));
  if (o.hata_sayisi) parcalar.push(sayi(o.hata_sayisi, "satır hatalı"));
  return parcalar.length ? parcalar.join(", ") + "." : "Dosyada eklenecek ya da değişecek bir şey yok.";
}

function SatirTablosu({ baslik, satirlar, neden }: { baslik: string; satirlar: Satir[]; neden?: boolean }) {
  if (!satirlar.length) return null;
  return (
    <table className={stil.tablo}>
      <caption>{baslik} ({satirlar.length})</caption>
      <thead>
        <tr>
          <th scope="col">Satır</th>
          <th scope="col">Kayıt</th>
          <th scope="col">{neden ? "Neden" : "Ayrıntı"}</th>
        </tr>
      </thead>
      <tbody>
        {satirlar.map((s) => (
          <tr key={s.satir}>
            <td className={stil.no}>{s.satir}</td>
            <td>{s.ad || "—"}</td>
            <td>{s.ayrinti}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SayfaOnizlemesi({ sayfa }: { sayfa: Sayfa }) {
  const notlar = [];
  if (sayfa.degismeyen) notlar.push(`${sayfa.degismeyen} satır okulda zaten aynı, değişmeyecek`);
  if (sayfa.atlanan_ornek) notlar.push("şablondaki örnek satır okunmadı");
  const bos = !sayfa.eklenecek.length && !sayfa.guncellenecek.length && !sayfa.hatali.length;
  return (
    <section className={stil.sayfa} aria-labelledby={`ia-${sayfa.sayfa}`}>
      <h3 id={`ia-${sayfa.sayfa}`}>{sayfa.baslik}</h3>
      <div className={stil.hatali}>
        <SatirTablosu baslik="Hatalı satırlar" satirlar={sayfa.hatali} neden />
      </div>
      <SatirTablosu baslik="Eklenecek" satirlar={sayfa.eklenecek} />
      <SatirTablosu baslik="Güncellenecek" satirlar={sayfa.guncellenecek} />
      {(bos || notlar.length > 0) && (
        <p className={stil.not}>{bos && !notlar.length ? "Bu sayfada değişiklik yok." : notlar.join("; ") + "."}</p>
      )}
    </section>
  );
}

export function IceAktarmaSayfasi() {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const girdi = useRef<HTMLInputElement>(null);
  const [dosya, setDosya] = useState<File | null>(null);
  const [surukleniyor, setSurukleniyor] = useState(false);

  const onizle = useMutation({
    mutationFn: (d: File) => cagir(api.POST("/api/ders-programi/ice-aktarma/onizleme", dosyaGovdesi(d))),
  });
  const kaydet = useMutation({
    mutationFn: (d: { dosya: File; ozet: string }) =>
      cagir(api.POST("/api/ders-programi/ice-aktarma", { ...dosyaGovdesi(d.dosya), params: { query: { ozet: d.ozet } } })),
    onSuccess: async (s) => {
      // Öğretmen, sınıf, ders ve dağılım listelerinin hepsi değişmiş olabilir.
      await istemci.invalidateQueries();
      bildirim("basari", `İçe aktarma kaydedildi: ${s.eklenen} kayıt eklendi, ${s.guncellenen} kayıt güncellendi.`);
      setDosya(null);
      onizle.reset();
      if (girdi.current) girdi.current.value = "";
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
  });

  const sec = (d: File | undefined) => {
    kaydet.reset();
    setDosya(d ?? null);
    if (d) onizle.mutate(d);
    else onizle.reset();
  };
  const o = onizle.data;

  return (
    <>
      <SayfaBasligi baslik="Excel'den içe aktar">
        Öğretmenleri, sınıfları, dersleri ve ders dağılımını bir Excel dosyasından ekleyin ya da güncelleyin.
      </SayfaBasligi>

      <section className={sayfaStili.kart}>
        <h2 className={stil.adimBasligi}>
          <span className={stil.adimNo} aria-hidden="true">1</span>
          <span className="gorunmez">1. </span>Şablonu indirin
        </h2>
        <p className={stil.metin}>
          Şablonda dört sayfa var: Öğretmenler, Sınıflar, Dersler ve Ders dağılımı. Yalnızca gerekenleri
          doldurabilirsiniz. Okulda aynı adla bir kayıt varsa yenisi açılmaz (büyük/küçük harf ve boşluk farkı
          önemsizdir); boş bırakılan hücre var olan değeri değiştirmez.
        </p>
        <a className={stil.sablonDugmesi} href={SABLON_ADRESI} download>
          <Download aria-hidden="true" /> Şablonu indir (.xlsx)
        </a>
      </section>

      <section className={sayfaStili.kart}>
        <h2 className={stil.adimBasligi}>
          <span className={stil.adimNo} aria-hidden="true">2</span>
          <span className="gorunmez">2. </span>Doldurduğunuz dosyayı seçin
        </h2>
        {/* Bırakma alanı: etiketin kendisi. Tıklayınca (ya da klavyede girdiye gelip Boşluk/Enter)
            dosya penceresi açılır; dosya üzerine sürüklenip bırakılabilir. Girdi görünmez ama odaklanır. */}
        <label
          className={stil.birakmaAlani}
          htmlFor="ia-dosya"
          data-surukleniyor={surukleniyor || undefined}
          onDragOver={(e) => {
            e.preventDefault();
            setSurukleniyor(true);
          }}
          onDragLeave={() => setSurukleniyor(false)}
          onDrop={(e) => {
            e.preventDefault();
            setSurukleniyor(false);
            sec(e.dataTransfer.files[0]);
          }}
        >
          <span className={stil.birakmaIkonu} aria-hidden="true">
            {dosya ? <FileSpreadsheet /> : <Upload />}
          </span>
          <span className={stil.birakmaBaslik}>{dosya ? dosya.name : "Dosyayı buraya bırakın ya da seçmek için tıklayın"}</span>
          <span className={stil.birakmaIpucu}>Excel dosyası (.xlsx, en çok 2 MB){dosya && " · başka dosya seçmek için tıklayın"}</span>
        </label>
        <input id="ia-dosya" ref={girdi} type="file" className={stil.dosya}
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(e) => sec(e.target.files?.[0])} />
        {onizle.isPending && <p role="status">Dosya okunuyor…</p>}
        {onizle.isError && <p className={sayfaStili.hataKutusu} role="alert">{hataMetni(onizle.error)}</p>}
      </section>

      {o && dosya && (
        <section className={sayfaStili.kart} aria-labelledby="ia-onizleme">
          <h2 id="ia-onizleme">3. Önizleme</h2>
          <p role="status" className={stil.ozet}>{ozetMetni(o)} Onaylamadan hiçbir şey kaydedilmez.</p>
          {o.sayfalar.map((s) => <SayfaOnizlemesi key={s.sayfa} sayfa={s} />)}
          {o.hata_sayisi > 0 ? (
            <p className={sayfaStili.hataKutusu}>
              Hatalı satırları dosyada düzeltip dosyayı yeniden seçin. Hatalı satır varken hiçbir satır kaydedilmez.
            </p>
          ) : (
            <Dugme disabled={!o.eklenecek_sayisi && !o.guncellenecek_sayisi} yukleniyor={kaydet.isPending}
              yukleniyorMetni="Kaydediliyor..." onClick={() => kaydet.mutate({ dosya, ozet: o.ozet })}>
              Onayla ve kaydet
            </Dugme>
          )}
        </section>
      )}
    </>
  );
}
