/**
 * Yayın ve paylaşım (8b, ADR 0022): yöneticinin yayınladığı program ve girişsiz paylaşım linkleri.
 *
 * - Yayın: hazır bir program yayınlanır; içeriği dondurulur. Yayından sonra veri ya da program
 *   değişirse sunucu nedenini söyler (`uyarilar`), yönetici yeniden yayınlar.
 * - Linkler: bütün okul, her öğretmen, her şube. Link okula bağlıdır: yeniden yayınlamak linki
 *   değiştirmez. "Yenile" eski linki o anda geçersiz kılar; "İptal" siler.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, RefreshCw, Send, Share2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import type { components } from "../api/sema";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { turkceSirala } from "../metin";
import { PROGRAMLAR, useProgramlar } from "../program/veri";
import sayfaStili from "../sayfalar/Sayfa.module.css";
import stil from "./Yayin.module.css";

type LinkYaniti = components["schemas"]["PaylasimLinkiYanit"];
type Tur = LinkYaniti["tur"];

export const YAYIN = ["yayin"] as const;
export const LINKLER = ["paylasim-linkleri"] as const;

export const linkAdresi = (jeton: string) => `${globalThis.location?.origin ?? ""}/p/${jeton}`;

const tarih = (iso: string) =>
  new Date(iso).toLocaleString("tr-TR", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });

function YayinBolumu() {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const yayin = useQuery({ queryKey: YAYIN, queryFn: () => cagir(api.GET("/api/ders-programi/yayin")) });
  const hazirlar = (useProgramlar().data ?? []).filter((p) => p.durum === "hazir");
  const [secili, setSecili] = useState("");
  const [kaldirilacak, setKaldirilacak] = useState(false);

  const yayinla = useMutation({
    mutationFn: (program_id: string) => cagir(api.PUT("/api/ders-programi/yayin", { body: { program_id } })),
    onSuccess: async (y) => {
      istemci.setQueryData(YAYIN, y);
      await istemci.invalidateQueries({ queryKey: PROGRAMLAR });
      bildirim("basari", `“${y.program_adi}” yayınlandı. Paylaşım linkleri bu programı gösteriyor.`);
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
  });
  const kaldir = useMutation({
    mutationFn: () => cagir(api.DELETE("/api/ders-programi/yayin")),
    onSuccess: () => {
      istemci.setQueryData(YAYIN, null);
      setKaldirilacak(false);
      bildirim("basari", "Yayın kaldırıldı. Linkler artık “yayında program yok” gösteriyor.");
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
  });

  const y = yayin.data;
  const hedef = secili || (y?.program_id && hazirlar.some((p) => p.id === y.program_id) ? y.program_id : hazirlar.at(-1)?.id) || "";
  return (
    <section className={sayfaStili.kart} aria-labelledby="yayin-baslik">
      <h2 id="yayin-baslik">Yayındaki program</h2>
      {yayin.isPending ? (
        <p role="status">Yükleniyor…</p>
      ) : y ? (
        <>
          <p className={stil.yayinda}>
            <strong>“{y.program_adi}”</strong> {tarih(y.yayin_zamani)} tarihinde yayınlandı.
            {y.program_id && <> <Link to={`/program/${y.program_id}`}>Programı aç</Link></>}
          </p>
          {y.uyarilar.length > 0 && (
            <ul className={stil.uyarilar} aria-label="Yayın güncel değil">
              {y.uyarilar.map((u) => <li key={u}>{u}</li>)}
            </ul>
          )}
        </>
      ) : (
        <p>Henüz yayınlanmış program yok. Yayınlanan programı öğretmenler ve şubeler linkle, giriş yapmadan görür.</p>
      )}
      {hazirlar.length > 0 ? (
        <div className={stil.satir}>
          <label className={stil.secici}>
            Yayınlanacak program
            <select value={hedef} onChange={(e) => setSecili(e.target.value)}>
              {hazirlar.map((p) => <option key={p.id} value={p.id}>{p.ad}</option>)}
            </select>
          </label>
          <Dugme ikon={<Send />} yukleniyor={yayinla.isPending} yukleniyorMetni="Yayınlanıyor..."
            onClick={() => yayinla.mutate(hedef)}>
            {y && y.program_id === hedef ? "Yeniden yayınla" : "Yayınla"}
          </Dugme>
          {y && <Dugme tur="tehlike" ikon={<Trash2 />} onClick={() => setKaldirilacak(true)}>Yayından kaldır</Dugme>}
        </div>
      ) : (
        <p>Yayınlamak için önce <Link to="/program">bir program üretin</Link>.</p>
      )}
      <OnayPenceresi acik={kaldirilacak} baslik="Yayından kaldırılsın mı?" tehlikeli onaylaMetni="Yayından kaldır"
        mesaj="Linkler silinmez; açan kişi “yayında program yok” görür. Yeniden yayınlayınca aynı linkler çalışır."
        yukleniyor={kaldir.isPending} onOnayla={() => kaldir.mutate()} onVazgec={() => setKaldirilacak(false)} />
    </section>
  );
}

function LinkSatiri({ link, onYenile, onIptal }: { link: LinkYaniti; onYenile: () => void; onIptal: () => void }) {
  const bildirim = useBildirim();
  const adres = linkAdresi(link.jeton);
  const kopyala = async () => {
    try {
      await navigator.clipboard.writeText(adres);
      bildirim("basari", `${link.hedef_adi} linki kopyalandı.`);
    } catch {
      bildirim("hata", "Link kopyalanamadı; adresi seçip elle kopyalayın.");
    }
  };
  return (
    <tr>
      <th scope="row">{link.hedef_adi}</th>
      <td><input className={stil.adres} readOnly value={adres} aria-label={`${link.hedef_adi} linki`} onFocus={(e) => e.target.select()} /></td>
      <td className={stil.eylemler}>
        <Dugme tur="ikincil" ikon={<Copy />} onClick={kopyala} aria-label={`${link.hedef_adi} linkini kopyala`}>Kopyala</Dugme>
        <Dugme tur="metin" ikon={<RefreshCw />} onClick={onYenile} aria-label={`${link.hedef_adi} linkini yenile`}>Yenile</Dugme>
        <Dugme tur="metin" ikon={<Trash2 />} onClick={onIptal} aria-label={`${link.hedef_adi} linkini iptal et`}>İptal</Dugme>
      </td>
    </tr>
  );
}

const TUR_ADI: Record<Tur, string> = { okul: "Bütün okul", ogretmen: "Öğretmenler", sube: "Şubeler" };

function LinklerBolumu() {
  const istemci = useQueryClient();
  const bildirim = useBildirim();
  const linkler = useQuery({ queryKey: LINKLER, queryFn: () => cagir(api.GET("/api/ders-programi/paylasim-linkleri")) });
  const [islem, setIslem] = useState<{ tur: "yenile" | "iptal"; link: LinkYaniti } | null>(null);
  const tazele = () => istemci.invalidateQueries({ queryKey: LINKLER });

  const olustur = useMutation({
    mutationFn: (tur: Tur) => tur === "okul"
      ? cagir(api.POST("/api/ders-programi/paylasim-linkleri", { body: { tur } })).then(() => undefined)
      : cagir(api.POST("/api/ders-programi/paylasim-linkleri/toplu", { body: { tur } })).then(() => undefined),
    onSuccess: tazele,
    onError: (h) => bildirim("hata", hataMetni(h)),
  });
  const uygula = useMutation({
    mutationFn: async (d: { tur: "yenile" | "iptal"; link: LinkYaniti }) => {
      const yol = { params: { path: { link_id: d.link.id } } };
      if (d.tur === "yenile") await cagir(api.POST("/api/ders-programi/paylasim-linkleri/{link_id}/yenile", yol));
      else await cagir(api.DELETE("/api/ders-programi/paylasim-linkleri/{link_id}", yol));
      return d;
    },
    onSuccess: async (d) => {
      await tazele();
      setIslem(null);
      bildirim("basari", d.tur === "yenile"
        ? `${d.link.hedef_adi} için yeni link oluşturuldu; eski link artık açılmıyor.`
        : `${d.link.hedef_adi} linki iptal edildi.`);
    },
    onError: (h) => bildirim("hata", hataMetni(h)),
  });

  const tum = linkler.data ?? [];
  return (
    <section className={sayfaStili.kart} aria-labelledby="linkler-baslik">
      <h2 id="linkler-baslik">Paylaşım linkleri</h2>
      <p className={stil.aciklama}>
        Link giriş istemez ve yalnızca kendi kapsamını gösterir: öğretmen linki o öğretmenin, şube linki o şubenin
        programını. Program yeniden yayınlanınca linkler değişmez.
      </p>
      {(["okul", "ogretmen", "sube"] as const).map((tur) => {
        const bunlar = turkceSirala(tum.filter((l) => l.tur === tur), (l) => l.hedef_adi);
        return (
          <div key={tur} className={stil.grup}>
            <div className={stil.grupUst}>
              <h3>{TUR_ADI[tur]}</h3>
              <Dugme tur="ikincil" ikon={<Share2 />} yukleniyor={olustur.isPending && olustur.variables === tur}
                disabled={tur === "okul" && bunlar.length > 0} onClick={() => olustur.mutate(tur)}>
                {tur === "okul" ? "Okul linki oluştur" : "Linki olmayanlara oluştur"}
              </Dugme>
            </div>
            {bunlar.length > 0 && (
              <table className={stil.tablo}>
                <caption className="gorunmez">{TUR_ADI[tur]} paylaşım linkleri</caption>
                <thead>
                  <tr><th scope="col">Kimin</th><th scope="col">Link</th><th scope="col"><span className="gorunmez">İşlemler</span></th></tr>
                </thead>
                <tbody>
                  {bunlar.map((l) => (
                    <LinkSatiri key={l.id} link={l} onYenile={() => setIslem({ tur: "yenile", link: l })}
                      onIptal={() => setIslem({ tur: "iptal", link: l })} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
      <OnayPenceresi acik={islem !== null} tehlikeli yukleniyor={uygula.isPending}
        baslik={islem?.tur === "yenile" ? "Link yenilensin mi?" : "Link iptal edilsin mi?"}
        onaylaMetni={islem?.tur === "yenile" ? "Yenile" : "İptal et"} vazgecMetni="Vazgeç"
        mesaj={islem ? `${islem.link.hedef_adi} için şimdiki link o anda çalışmaz olur.${islem.tur === "yenile" ? " Yeni linki yeniden göndermeniz gerekir." : ""}` : ""}
        onOnayla={() => islem && uygula.mutate(islem)} onVazgec={() => setIslem(null)} />
    </section>
  );
}

export function YayinSayfasi() {
  return (
    <>
      <SayfaBasligi baslik="Yayın ve paylaşım">
        Programı yayınlayın; öğretmenler ve şubeler kendi programlarını linkle, giriş yapmadan telefondan görsün.
      </SayfaBasligi>
      <YayinBolumu />
      <LinklerBolumu />
    </>
  );
}
