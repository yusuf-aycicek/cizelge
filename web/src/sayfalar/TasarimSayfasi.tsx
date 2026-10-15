import { useState } from "react";
import { MetinAlani, SecimAlani } from "../bilesenler/Alan";
import { useBildirim } from "../bilesenler/Bildirim";
import { Dugme } from "../bilesenler/Dugme";
import { OnayPenceresi } from "../bilesenler/OnayPenceresi";
import { Tablo } from "../bilesenler/Tablo";
import stil from "./Sayfa.module.css";

type OrnekOgretmen = { id: string; ad: string; brans: string; yuk: number };

const OGRETMENLER: OrnekOgretmen[] = [
  { id: "1", ad: "Ayşe Yılmaz", brans: "Matematik", yuk: 18 },
  { id: "2", ad: "Mehmet Kaya", brans: "Türk Dili ve Edebiyatı", yuk: 15 },
  { id: "3", ad: "Zeynep Demir", brans: "Fen Bilimleri", yuk: 18 },
  { id: "4", ad: "Ali Çelik", brans: "İngilizce", yuk: 12 },
];

const RENKLER = [
  "--renk-birincil",
  "--renk-tehlike",
  "--renk-metin",
  "--renk-metin-ikincil",
  "--renk-yuzey",
  "--renk-basari-zemin",
  "--renk-hata-zemin",
  "--renk-uyari-zemin",
  "--renk-bilgi-zemin",
];

/**
 * Tasarım temeli vitrini (/tasarim): belirteçler ve ortak bileşenler bir arada. Geliştirirken
 * bileşenlerin görünümünü ve klavye davranışını tek yerde denemek için. Menüde yer almaz.
 */
export function TasarimSayfasi() {
  const bildirim = useBildirim();
  const [pencereAcik, setPencereAcik] = useState(false);
  const [ad, setAd] = useState("");
  const [gonderildi, setGonderildi] = useState(false);

  return (
    <>
      <h1>Tasarım temeli</h1>
      <p className={stil.giris}>Renkler, düğmeler, form alanları, tablo, bildirim ve onay penceresi.</p>

      <section className={stil.kart} aria-labelledby="renkler">
        <h2 id="renkler">Renkler</h2>
        <div className={stil.renkler}>
          {RENKLER.map((r) => (
            <div key={r} className={stil.renk}>
              <div className={stil.renkOrnegi} style={{ background: `var(${r})` }} />
              <div className={stil.renkAdi}>{r}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={stil.kart} aria-labelledby="dugmeler">
        <h2 id="dugmeler">Düğmeler</h2>
        <div className={stil.satir}>
          <Dugme>Kaydet</Dugme>
          <Dugme tur="ikincil">Vazgeç</Dugme>
          <Dugme tur="tehlike">Sil</Dugme>
          <Dugme tur="metin">Ayrıntılar</Dugme>
          <Dugme yukleniyor yukleniyorMetni="Kaydediliyor...">
            Kaydet
          </Dugme>
        </div>
      </section>

      <section className={stil.kart} aria-labelledby="formlar">
        <h2 id="formlar">Form alanları</h2>
        <form
          noValidate
          onSubmit={(olay) => {
            olay.preventDefault();
            setGonderildi(true);
          }}
        >
          <MetinAlani
            etiket="Öğretmenin adı"
            gerekli
            value={ad}
            onChange={(olay) => setAd(olay.target.value)}
            hata={gonderildi && ad.trim() === "" ? "Boş bırakılamaz" : undefined}
          />
          <MetinAlani etiket="E-posta" type="email" aciklama="Giriş yaparken kullanılır." />
          <SecimAlani etiket="Haftada kaç gün" defaultValue="5">
            <option value="5">5 gün</option>
            <option value="6">6 gün</option>
          </SecimAlani>
          <Dugme type="submit">Gönder</Dugme>
        </form>
      </section>

      <section className={stil.kart} aria-labelledby="tablo">
        <h2 id="tablo">Tablo</h2>
        <Tablo<OrnekOgretmen>
          baslik="Örnek öğretmen listesi"
          satirlar={OGRETMENLER}
          satirAnahtari={(o) => o.id}
          sutunlar={[
            { baslik: "Ad", hucre: (o) => o.ad },
            { baslik: "Branş", hucre: (o) => o.brans },
            { baslik: "Haftalık ders", hucre: (o) => `${o.yuk} saat`, hizala: "sag" },
            {
              baslik: "İşlemler",
              baslikGizli: true,
              hucre: (o) => (
                <Dugme tur="metin" aria-label={`${o.ad} düzenle`}>
                  Düzenle
                </Dugme>
              ),
            },
          ]}
        />
      </section>

      <section className={stil.kart} aria-labelledby="bildirimler">
        <h2 id="bildirimler">Bildirim ve onay penceresi</h2>
        <div className={stil.satir}>
          <Dugme tur="ikincil" onClick={() => bildirim("basari", "Öğretmen kaydedildi.")}>
            Başarı bildirimi
          </Dugme>
          <Dugme tur="ikincil" onClick={() => bildirim("hata", "Bu öğretmenin ders atamaları var, önce onları kaldırın.")}>
            Hata bildirimi
          </Dugme>
          <Dugme tur="tehlike" onClick={() => setPencereAcik(true)}>
            Öğretmeni sil...
          </Dugme>
        </div>
      </section>

      <OnayPenceresi
        acik={pencereAcik}
        baslik="Ayşe Yılmaz silinsin mi?"
        mesaj="Bu işlem geri alınamaz."
        onaylaMetni="Sil"
        tehlikeli
        onVazgec={() => setPencereAcik(false)}
        onOnayla={() => {
          setPencereAcik(false);
          bildirim("basari", "Ayşe Yılmaz silindi.");
        }}
      />
    </>
  );
}
