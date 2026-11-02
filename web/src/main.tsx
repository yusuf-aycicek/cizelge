// Yazı tipi projenin içinden sunulur (Google Fonts'a istek gitmez); Türkçe karakterler latin-ext
// alt kümesinde. Değişken yazı tipi: bütün kalınlıklar tek dosyada.
import "@fontsource-variable/nunito";
import "@fontsource-variable/bricolage-grotesque"; // başlıklar
import "@fontsource/jetbrains-mono/latin-800.css"; // yalnızca logo (">ya")
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "./stil/belirtecler.css";
import "./stil/ders-renkleri.css";
import "./stil/temel.css";
import { sorguIstemcisiOlustur } from "./sorgu";
import { temayiBaslat } from "./stil/tema";
import { Uygulama } from "./Uygulama";

const kok = document.getElementById("kok");
if (!kok) throw new Error("index.html içinde #kok yok");
temayiBaslat();

// StrictMode: yalnızca geliştirmede, bileşenleri ve etkileri (effect) bilerek iki kez çalıştırır.
// Böylece "iki kez çalışınca bozulan" kod (temizlenmeyen zamanlayıcı, çift istek) erkenden görünür.
createRoot(kok).render(
  <StrictMode>
    <BrowserRouter>
      <Uygulama sorguIstemcisi={sorguIstemcisiOlustur()} />
    </BrowserRouter>
  </StrictMode>,
);
