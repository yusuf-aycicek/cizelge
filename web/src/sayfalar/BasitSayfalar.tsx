import { Link } from "react-router";
import stil from "./Sayfa.module.css";

/** Henüz yapılmamış sayfalar için yer tutucu: menü tamam görünsün, kullanıcı ne geleceğini bilsin. */
export function YapimAsamasinda({ baslik }: { baslik: string }) {
  return (
    <>
      <h1>{baslik}</h1>
      <p className={stil.giris}>Bu sayfa hazırlanıyor.</p>
    </>
  );
}

export function Bulunamadi() {
  return (
    <>
      <h1>Sayfa bulunamadı</h1>
      <p className={stil.giris}>
        Aradığınız sayfa yok ya da taşınmış. <Link to="/">Ana sayfaya dönün.</Link>
      </p>
    </>
  );
}
