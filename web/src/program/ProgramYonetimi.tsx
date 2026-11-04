/**
 * Programların yönetimi (6.3): liste (durum, zaman, kısa kalite, eski veri), yeniden adlandırma,
 * silme, "bu programı temel alarak yeniden üret"; temel programa göre fark özeti ve eski veri uyarısı.
 */
import { Check, GitCompareArrows, History, Pencil, Trash2, TriangleAlert, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { hataMetni } from "../api/hata";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { Tablo } from "../bilesenler/Tablo";
import { etkinMi, kaliteMaddeleri, sureMetni, type Program } from "./aciklama";
import stil from "./Program.module.css";
import { useProgramAdlandir, useProgramFarki, useProgramSil } from "./veri";

export const tarih = (iso: string) =>
  new Date(iso).toLocaleString("tr-TR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

const DURUM_ADLARI: Record<string, string> = {
  bekliyor: "Sırada",
  uretiliyor: "Hazırlanıyor",
  hazir: "Hazır",
  basarisiz: "Oluşturulamadı",
};

/** Tablodaki tek satırlık kalite: "Bütün kurallar iyi" ya da "3 konu iyileştirilebilir"; ayrıntı title'da. */
export function kisaKalite(p: Program): { metin: string; ayrinti: string } | null {
  if (p.durum !== "hazir") return null;
  const kotu = kaliteMaddeleri(p.olcumler, Boolean(p.temel_program_id)).filter((m) => !m.iyi);
  if (kotu.length === 0) return { metin: "Her ölçü iyi", ayrinti: "" };
  return { metin: `${kotu.length} konu iyileştirilebilir`, ayrinti: kotu.map((m) => m.metin).join("\n") };
}

/** "Bu program eski verilerle üretildi": sunucu, üretildiği andaki verinin özetini şimdikiyle karşılaştırır. */
export function EskiVeriUyarisi({ program, onTemelAl }: { program: Program; onTemelAl?: (p: Program) => void }) {
  if (!program.eski_veri) return null;
  return (
    <div className={stil.eskiVeri} role="note">
      <TriangleAlert aria-hidden="true" />
      <p>
        <strong>Ayarlar son programdan sonra değişti, programı yeniden oluşturun.</strong> Ders dağılımı,
        öğretmen ayarları, müsaitlik ya da kurallar bu program üretildikten sonra değişti; program bu
        değişiklikleri içermiyor (eski verilerle üretildi).
        {onTemelAl && " Güncel veriyle yeniden üretin; bu programı temel alırsanız program yalnızca gerektiği kadar değişir."}
      </p>
      {onTemelAl && (
        <Dugme tur="ikincil" ikon={<History />} onClick={() => onTemelAl(program)}>
          Temel alarak yeniden üret
        </Dugme>
      )}
    </div>
  );
}

/** Temel programa göre kaç ders saatinin, hangi şubelerde yer değiştirdiği (en az değişiklikle güncelleme). */
export function FarkOzeti({ program, cizelgeBaglantisi = true }: { program: Program; cizelgeBaglantisi?: boolean }) {
  const fark = useProgramFarki(program.id, program.durum === "hazir" && Boolean(program.temel_program_id));
  if (!program.temel_program_id || !fark.data) return null;
  const f = fark.data;
  return (
    <div className={stil.fark} role="status" aria-label="Temel programa göre değişiklik">
      <GitCompareArrows aria-hidden="true" />
      <p>
        {f.degisen === 0 ? (
          <>“{f.ile_ad}” programına göre hiçbir ders yer değiştirmedi.</>
        ) : (
          <>
            “{f.ile_ad}” programına göre <strong>{f.degisen} ders saati</strong> yer değiştirdi:{" "}
            {f.subeler.map((s) => `${s.ad} (${s.sayi})`).join(", ")}.{" "}
            {cizelgeBaglantisi && <Link to={`/program/${program.id}?fark=1`}>Değişenleri çizelgede göster</Link>}
          </>
        )}
      </p>
    </div>
  );
}

/** Bütün programlar, en yenisi üstte: durum, oluşturma zamanı, kısa kalite; adlandır, sil, temel al. */
export function ProgramlarTablosu({ programlar, onTemelAl }: { programlar: Program[]; onTemelAl: (p: Program) => void }) {
  const bildirim = useBildirim();
  const adlandir = useProgramAdlandir();
  const sil = useProgramSil();
  const [duzenlenen, setDuzenlenen] = useState<{ id: string; ad: string } | null>(null);
  const [silinecek, setSilinecek] = useState<Program | null>(null);
  const sirali = [...programlar].reverse();
  const adlar = new Map(programlar.map((p) => [p.id, p.ad]));

  function adiKaydet() {
    if (!duzenlenen?.ad.trim()) return;
    adlandir.mutate(
      { id: duzenlenen.id, ad: duzenlenen.ad.trim() },
      {
        onSuccess: (p) => {
          setDuzenlenen(null);
          bildirim("basari", `Programın yeni adı: ${p.ad}.`);
        },
        onError: (h) => bildirim("hata", hataMetni(h)),
      },
    );
  }

  return (
    <section aria-labelledby="onceki-baslik" className={stil.onceki}>
      <h2 id="onceki-baslik">Programlar</h2>
      <Tablo<Program>
        baslik="Programlar"
        satirlar={sirali}
        satirAnahtari={(p) => p.id}
        sutunlar={[
          {
            baslik: "Ad",
            hucre: (p) =>
              duzenlenen?.id === p.id ? (
                <input
                  className={stil.adKutusu}
                  aria-label="Programın adı (düzenleme)"
                  value={duzenlenen.ad}
                  maxLength={200}
                  autoFocus
                  onChange={(o) => setDuzenlenen({ id: p.id, ad: o.target.value })}
                  onKeyDown={(o) => {
                    if (o.key === "Enter") adiKaydet();
                    if (o.key === "Escape") setDuzenlenen(null);
                  }}
                />
              ) : (
                <span className={stil.sarar}>
                  {p.ad}
                  {p.temel_program_id && (
                    <span className={stil.ikincilSatir}>Temel: {adlar.get(p.temel_program_id) ?? "silinmiş program"}</span>
                  )}
                </span>
              ),
          },
          {
            baslik: "Durum",
            hucre: (p) => {
              const kalite = kisaKalite(p);
              return (
                <>
                  <span className={`${stil.durumRozeti} ${stil[`durum_${p.durum}`] ?? ""}`}>{DURUM_ADLARI[p.durum] ?? p.durum}</span>
                  {kalite && (
                    <span className={stil.ikincilSatir} title={kalite.ayrinti || undefined}>
                      {kalite.metin}
                    </span>
                  )}
                  {p.eski_veri && (
                    <span className={stil.eskiRozet}>
                      <TriangleAlert aria-hidden="true" /> Eski verilerle
                    </span>
                  )}
                </>
              );
            },
          },
          {
            // Oluşturma zamanı ve süre tek sütunda, alt alta: ayrı sütun dar ekranda tabloyu taşırıyordu.
            baslik: "Oluşturma",
            hucre: (p) => (
              <>
                {tarih(p.olusturma)}
                {p.sure_sn != null && <span className={stil.ikincilSatir}>{sureMetni(p.sure_sn)} sürdü</span>}
              </>
            ),
          },
          {
            baslik: "İşlemler",
            baslikGizli: true,
            hizala: "sag",
            hucre: (p) =>
              duzenlenen?.id === p.id ? (
                <span className={stil.islemler}>
                  <Dugme tur="metin" ikon={<Check />} yukleniyor={adlandir.isPending} onClick={adiKaydet}>Kaydet</Dugme>
                  <Dugme tur="metin" ikon={<X />} onClick={() => setDuzenlenen(null)}>Vazgeç</Dugme>
                </span>
              ) : (
                <span className={stil.islemler}>
                  {p.durum === "hazir" && (
                    <>
                      <Link to={`/program/${p.id}`} className={stil.tekSatir}>Çizelgeyi aç</Link>
                      <Dugme tur="metin" ikon={<History />} aria-label={`${p.ad}: temel alarak yeniden üret`} onClick={() => onTemelAl(p)}>
                        Temel al
                      </Dugme>
                    </>
                  )}
                  <Dugme tur="metin" ikon={<Pencil />} aria-label={`${p.ad}: adını değiştir`} onClick={() => setDuzenlenen({ id: p.id, ad: p.ad })}>
                    <span className={stil.islemMetni}>Adı</span>
                  </Dugme>
                  {!etkinMi(p) && (
                    <Dugme tur="metin" ikon={<Trash2 />} aria-label={`${p.ad}: sil`} onClick={() => setSilinecek(p)}>
                      <span className={stil.islemMetni}>Sil</span>
                    </Dugme>
                  )}
                </span>
              ),
          },
        ]}
      />
      <OnayPenceresi
        acik={silinecek !== null}
        baslik={silinecek ? `“${silinecek.ad}” silinsin mi?` : ""}
        mesaj={
          programlar.some((p) => p.temel_program_id === silinecek?.id)
            ? "Program ve çizelgesi silinir. Bu programı temel alan programlar silinmez, yalnızca temel bilgisi kalkar."
            : "Program ve çizelgesi silinir. Bu işlem geri alınamaz."
        }
        onaylaMetni="Programı sil"
        tehlikeli
        yukleniyor={sil.isPending}
        onVazgec={() => setSilinecek(null)}
        onOnayla={() =>
          silinecek &&
          sil.mutate(silinecek.id, {
            onSuccess: () => bildirim("basari", `“${silinecek.ad}” silindi.`),
            onError: (h) => bildirim("hata", hataMetni(h)),
            onSettled: () => setSilinecek(null),
          })
        }
      />
    </section>
  );
}
