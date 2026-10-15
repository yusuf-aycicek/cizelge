import { useQuery } from "@tanstack/react-query";
import { cagir, hataMetni } from "../api/hata";
import { api } from "../api/istemci";
import { Dugme } from "../bilesenler/Dugme";
import stil from "./Sayfa.module.css";

/**
 * Ana sayfa. Bu adımda yalnızca sistem durumunu gösterir. Kurulum adımları kontrol listesi
 * 5.6'da gelir.
 *
 * useQuery: "bu veriyi istiyorum" der; çekme, yükleniyor durumu, hata, önbellek ve yeniden
 * deneme TanStack Query'dedir. Bileşen yalnızca üç durumdan birini çizer: yükleniyor, hata, veri.
 */
export function AnaSayfa() {
  const saglik = useQuery({
    queryKey: ["saglik"],
    queryFn: () => cagir(api.GET("/api/saglik")),
  });

  return (
    <>
      <h1>Hoş geldiniz</h1>
      <p className={stil.giris}>
        Bu sistem okulunuz için öğretmen ve sınıf çakışması olmayan haftalık ders programı hazırlar.
        Önce okulunuzun bilgilerini girin, sonra programı üretin.
      </p>

      <section aria-labelledby="sistem-durumu" className={stil.kart}>
        <h2 id="sistem-durumu">Sistem durumu</h2>
        {saglik.isPending && <p>Sunucuya bağlanılıyor...</p>}
        {saglik.isError && (
          <div className={stil.hataKutusu} role="alert">
            <p>{hataMetni(saglik.error)}</p>
            <Dugme tur="ikincil" onClick={() => saglik.refetch()} yukleniyor={saglik.isFetching}>
              Yeniden dene
            </Dugme>
          </div>
        )}
        {saglik.isSuccess && (
          <dl className={stil.durumListesi}>
            <dt>Sunucu</dt>
            <dd>
              <span className={stil.iyi}>✓ Çalışıyor</span>
            </dd>
            <dt>Veritabanı</dt>
            <dd>
              <span className={stil.iyi}>✓ Bağlı</span>
            </dd>
          </dl>
        )}
      </section>
    </>
  );
}
