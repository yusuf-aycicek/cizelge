import { SayfaBasligi } from "../bilesenler/SayfaBasligi";
import { Hammer, MapPinOff } from "lucide-react";
import { Link } from "react-router";

/** Henüz yapılmamış sayfalar için yer tutucu: menü tamam görünsün, kullanıcı ne geleceğini bilsin. */
export function YapimAsamasinda({ baslik }: { baslik: string }) {
  return (
    <>
      <SayfaBasligi ikon={Hammer} baslik={baslik}>
        Bu sayfa hazırlanıyor.
      </SayfaBasligi>
    </>
  );
}

export function Bulunamadi() {
  return (
    <>
      <SayfaBasligi ikon={MapPinOff} baslik="Sayfa bulunamadı">
        Aradığınız sayfa yok ya da taşınmış. <Link to="/">Ana sayfaya dönün.</Link>
      </SayfaBasligi>
    </>
  );
}
