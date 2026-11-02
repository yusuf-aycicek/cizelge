import { CalendarCheck, ShieldCheck, Smartphone } from "lucide-react";
import { useRef, type CSSProperties, type PointerEvent, type ReactNode } from "react";
import { hareketAzaltilmis } from "../bilesenler/hareket";
import stil from "./Giris.module.css";

type Ders = "mat" | "fizik" | "turkce" | "tarih" | "ing" | "kimya";

const DERS_ADLARI: Record<Ders, string> = {
  mat: "Matematik",
  fizik: "Fizik",
  turkce: "Türk Dili",
  tarih: "Tarih",
  ing: "İngilizce",
  kimya: "Kimya",
};

// Ortadaki telefon: 9-A'nın haftası. Her gün bir başlık ve o günün dersleri (öğretmen adıyla).
const HAFTA: { gun: string; dersler: [Ders, string][] }[] = [
  { gun: "Pazartesi", dersler: [["mat", "Ayşe Yılmaz"], ["mat", "Ayşe Yılmaz"], ["tarih", "Fatma Şahin"], ["fizik", "Zeynep Demir"]] },
  { gun: "Salı", dersler: [["turkce", "Mehmet Kaya"], ["turkce", "Mehmet Kaya"], ["ing", "Ali Çelik"], ["mat", "Ayşe Yılmaz"], ["kimya", "Zeynep Demir"]] },
  { gun: "Çarşamba", dersler: [["fizik", "Zeynep Demir"], ["fizik", "Zeynep Demir"], ["tarih", "Fatma Şahin"], ["mat", "Ayşe Yılmaz"]] },
  { gun: "Perşembe", dersler: [["mat", "Ayşe Yılmaz"], ["kimya", "Zeynep Demir"], ["kimya", "Zeynep Demir"], ["turkce", "Mehmet Kaya"]] },
  { gun: "Cuma", dersler: [["ing", "Ali Çelik"], ["ing", "Ali Çelik"], ["turkce", "Mehmet Kaya"], ["tarih", "Fatma Şahin"]] },
];

// Sağdaki telefon: 5 gün x 6 saat; kareler karışık ama sabit bir sırayla düşer (her yenilemede aynı).
const KARELER: Ders[] = ["mat", "turkce", "fizik", "mat", "ing", "mat", "turkce", "fizik", "kimya", "ing", "tarih", "ing", "tarih", "kimya", "turkce", "fizik", "mat", "mat", "turkce", "tarih", "kimya", "kimya", "ing", "fizik", "mat", "tarih", "turkce", "mat", "fizik", "ing"];
const SIRA = [12, 3, 25, 7, 0, 18, 5, 21, 9, 1, 14, 27, 4, 16, 10, 29, 2, 23, 8, 19, 13, 26, 6, 17, 11, 28, 15, 22, 20, 24];

const ETIKETLER = [
  { ikon: ShieldCheck, metin: "Çakışmasız program" },
  { ikon: CalendarCheck, metin: "Öğretmenlere boş gün" },
  { ikon: Smartphone, metin: "Telefondan paylaşım" },
];

/**
 * Giriş sayfasının tanıtımı: üç telefon. Ortada 9-A'nın kayan haftalık programı, solda bir
 * öğretmenin kendi ekranı, sağda hazırlanan program (kareler düşer, çubuk dolar). Telefonlar
 * hafifçe süzülür, arkalarındaki hale nefes alır, fare panelin üstünde gezince telefonlar ona
 * doğru eğilir. Hareket azaltılmışsa hepsi durur ve son hâlleri görünür (dolu çizelge, dolu çubuk).
 * Süstür: ekran okuyucuya tek cümlelik açıklama okunur.
 */
export function TanitimPaneli() {
  const grup = useRef<HTMLDivElement>(null);

  function egil(olay: PointerEvent<HTMLElement>) {
    if (olay.pointerType !== "mouse" || hareketAzaltilmis() || !grup.current) return;
    const kutu = olay.currentTarget.getBoundingClientRect();
    const x = (olay.clientX - kutu.left) / kutu.width - 0.5; // -0.5 … 0.5
    const y = (olay.clientY - kutu.top) / kutu.height - 0.5;
    grup.current.style.setProperty("--ry", `${(x * 14).toFixed(2)}deg`); // en çok 7°
    grup.current.style.setProperty("--rx", `${(-y * 10).toFixed(2)}deg`); // en çok 5°
  }
  function duzel() {
    grup.current?.style.setProperty("--ry", "0deg");
    grup.current?.style.setProperty("--rx", "0deg");
  }

  return (
    <aside className={stil.panel} aria-label="Çizelge'nin tanıtımı" onPointerMove={egil} onPointerLeave={duzel}>
      <div className={stil.panelIcerik}>
        <p className={stil.etiket}>OKUL DERS PROGRAMI, CEBİNİZDE</p>
        <h2 className={stil.panelBasligi}>Program saniyeler içinde hazır, öğretmenler telefonundan görür.</h2>

        <div
          className={stil.sahne}
          role="img"
          aria-label="Üç telefon: 9-A şubesinin haftalık programı, öğretmen Ayşe Yılmaz'ın ekranı ve hazırlanan program: çakışma yok, bütün öğretmenlere boş gün."
        >
          <span className={stil.hale} aria-hidden="true" />
          <div ref={grup} className={stil.telefonlar} aria-hidden="true">
            <OgretmenTelefonu />
            <HaftaTelefonu />
            <HazirlanmaTelefonu />
          </div>
        </div>

        <ul className={stil.etiketler}>
          {ETIKETLER.map(({ ikon: Ikon, metin }) => (
            <li key={metin}>
              <Ikon aria-hidden="true" strokeWidth={2} />
              {metin}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

function Telefon({ yan, koyu, children }: { yan?: "sol" | "sag"; koyu?: boolean; children: ReactNode }) {
  return (
    <div className={`${stil.telefon} ${yan ? stil.yanTelefon : ""} ${yan === "sag" ? stil.sagTelefon : ""} ${yan === "sol" ? stil.solTelefon : ""}`}>
      <div className={`${stil.ekran} ${koyu ? stil.koyuEkran : ""}`}>
        <div className={stil.durumCubugu}>
          <span>08:30</span>
          <span className={stil.centik} />
          <span>%86</span>
        </div>
        {children}
      </div>
    </div>
  );
}

function HaftaTelefonu() {
  // Liste iki kez yazılır: yarısı kadar kayınca başa dönüş görünmez.
  const liste = (kopya: number) =>
    HAFTA.map(({ gun, dersler }) => (
      <div key={`${kopya}-${gun}`} className={stil.gunGrubu}>
        <p className={stil.gunAdi}>{gun}</p>
        {dersler.map(([ders, ogretmen], i) => (
          <div key={i} className={stil.dersSatiri} data-ders={ders}>
            <span className={stil.dersSaati}>{i + 1}</span>
            <span className={stil.dersBilgisi}>
              <strong>{DERS_ADLARI[ders]}</strong>
              <span>{ogretmen}</span>
            </span>
          </div>
        ))}
      </div>
    ));
  return (
    <Telefon>
      <div className={stil.ekranBasligi}>
        <strong>9-A</strong>
        <span>Haftalık program</span>
      </div>
      <div className={stil.kaydirmaAlani}>
        <div className={stil.kayanListe}>
          {liste(0)}
          {liste(1)}
        </div>
      </div>
    </Telefon>
  );
}

function OgretmenTelefonu() {
  return (
    <Telefon yan="sol">
      <div className={stil.selam}>
        <span>Merhaba,</span>
        <strong>Ayşe Yılmaz</strong>
      </div>
      <div className={stil.bugun}>
        <span>Bugün · Perşembe</span>
        <strong>3 ders</strong>
        <div className={stil.dersSatiri} data-ders="mat">
          <span className={stil.dersSaati}>1</span>
          <span className={stil.dersBilgisi}>
            <strong>Matematik</strong>
            <span>9-A</span>
          </span>
        </div>
        <div className={stil.dersSatiri} data-ders="mat">
          <span className={stil.dersSaati}>3</span>
          <span className={stil.dersBilgisi}>
            <strong>Matematik</strong>
            <span>10-A</span>
          </span>
        </div>
        <div className={stil.dersSatiri} data-ders="mat">
          <span className={stil.dersSaati}>5</span>
          <span className={stil.dersBilgisi}>
            <strong>Matematik</strong>
            <span>9-B</span>
          </span>
        </div>
      </div>
      <div className={stil.bosGunKarti}>
        <CalendarCheck aria-hidden="true" />
        <span>
          <strong>Cuma boş gün</strong>
          <span>Bu hafta dersiniz yok</span>
        </span>
      </div>
      <div className={stil.haftaSeridi}>
        {["Pzt", "Sal", "Çar", "Per", "Cum"].map((g, i) => (
          <span key={g} className={i === 4 ? stil.bosGun : i === 3 ? stil.bugunGun : undefined}>
            {g}
          </span>
        ))}
      </div>
    </Telefon>
  );
}

function HazirlanmaTelefonu() {
  return (
    <Telefon yan="sag" koyu>
      <p className={stil.hazirlaniyor}>
        <span className={stil.nokta} />
        HAZIRLANIYOR
      </p>
      <div className={stil.kareler}>
        {KARELER.map((ders, i) => (
          <span key={i} className={stil.kare} data-ders={ders} style={{ "--d": ((SIRA[i] ?? 0) * 0.1).toFixed(1) } as CSSProperties} />
        ))}
      </div>
      <div className={stil.ilerleme}>
        <span />
      </div>
      <dl className={stil.olcumler}>
        <div>
          <dt>Çakışma</dt>
          <dd>0</dd>
        </div>
        <div>
          <dt>Pencere saat</dt>
          <dd>0</dd>
        </div>
        <div>
          <dt>Boş gün</dt>
          <dd>5/5</dd>
        </div>
      </dl>
    </Telefon>
  );
}
