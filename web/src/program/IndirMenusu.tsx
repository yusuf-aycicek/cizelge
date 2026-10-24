import { ChevronDown, Download, FileSpreadsheet, FileText } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import stil from "./IndirMenusu.module.css";

/** Seçili şube ya da öğretmen: o kişinin/şubenin tek sayfalık PDF'i de menüde görünür. */
export type IndirmeSecimi = { tur: "sube" | "ogretmen"; id: string; ad: string };

type Props = { programId: string; secili?: IndirmeSecimi };

/** Çıktı uçlarının adresi (api: moduller/ders_programi/api.py, ADR 0020). */
export const ciktiAdresi = (programId: string, dosya: string, parametreler: Record<string, string> = {}) => {
  const sorgu = new URLSearchParams(parametreler).toString();
  return `/api/ders-programi/programlar/${programId}/cikti/${dosya}${sorgu ? `?${sorgu}` : ""}`;
};

/**
 * "İndir" menüsü: PDF ve Excel çıktıları sunucuda üretilir; bağlantılar dosyayı doğrudan indirir
 * (oturum çerezi aynı kökenden gider). Açılır kutu "disclosure" desenidir: düğme `aria-expanded`
 * ile listeyi açar, içindekiler sıradan bağlantılardır (Tab ile gezilir). Escape ve dışarı
 * tıklama kapatır.
 */
export function IndirMenusu({ programId, secili }: Props) {
  const [acik, setAcik] = useState(false);
  const [imza, setImza] = useState(false);
  const kok = useRef<HTMLDivElement>(null);
  const dugme = useRef<HTMLButtonElement>(null);
  const listeId = useId();

  // Açıkken dışarı tıklanınca ya da Escape'e basılınca kapanır (Escape odağı düğmeye geri verir).
  useEffect(() => {
    if (!acik) return;
    const tikla = (o: MouseEvent) => {
      if (kok.current && !kok.current.contains(o.target as Node)) setAcik(false);
    };
    const tus = (o: KeyboardEvent) => {
      if (o.key === "Escape") {
        setAcik(false);
        dugme.current?.focus();
      }
    };
    document.addEventListener("mousedown", tikla);
    document.addEventListener("keydown", tus);
    return () => {
      document.removeEventListener("mousedown", tikla);
      document.removeEventListener("keydown", tus);
    };
  }, [acik]);

  const imzaParametresi: Record<string, string> = imza ? { imza: "true" } : {};
  const pdf = (ad: string, aciklama: string, href: string) => ({ ad, aciklama, href, excel: false });
  const ogeler = [
    ...(secili
      ? [pdf(`${secili.ad} programı`, "PDF, tek sayfa", ciktiAdresi(programId, secili.tur === "sube" ? "subeler.pdf" : "ogretmenler.pdf",
          { [secili.tur === "sube" ? "sinif_id" : "ogretmen_id"]: secili.id, ...imzaParametresi }))]
      : []),
    pdf("Şube programları", "PDF, A4 yatay, her şube bir sayfa", ciktiAdresi(programId, "subeler.pdf", imzaParametresi)),
    pdf("Öğretmen programları", "PDF, A4 yatay, haftalık toplamla", ciktiAdresi(programId, "ogretmenler.pdf", imzaParametresi)),
    pdf("Çarşaf liste (öğretmenler)", "PDF, A3 yatay, bütün okul", ciktiAdresi(programId, "carsaf.pdf", { satir: "ogretmen" })),
    pdf("Çarşaf liste (şubeler)", "PDF, A3 yatay, bütün okul", ciktiAdresi(programId, "carsaf.pdf", { satir: "sube" })),
    { ad: "Excel", aciklama: "Şubeler, öğretmenler, çarşaf ve liste sekmeleri", href: ciktiAdresi(programId, "program.xlsx"), excel: true },
  ];

  return (
    <div className={stil.kok} ref={kok}>
      <button ref={dugme} type="button" className={stil.dugme} aria-expanded={acik} aria-controls={listeId}
        onClick={() => setAcik(!acik)}>
        <Download aria-hidden="true" /> İndir <ChevronDown aria-hidden="true" className={stil.ok} />
      </button>
      {acik && (
        <div id={listeId} className={stil.kutu}>
          <ul className={stil.liste}>
            {ogeler.map((o) => (
              <li key={o.href}>
                <a href={o.href} download className={stil.oge} onClick={() => setAcik(false)}>
                  {o.excel ? <FileSpreadsheet aria-hidden="true" /> : <FileText aria-hidden="true" />}
                  <span>
                    <span className={stil.ad}>{o.ad}</span>
                    <span className={stil.aciklama}>{o.aciklama}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
          <label className={stil.imza}>
            <input type="checkbox" checked={imza} onChange={(o) => setImza(o.target.checked)} />
            Şube ve öğretmen PDF'ine "Okul Müdürü" imza alanı ekle
          </label>
        </div>
      )}
    </div>
  );
}
