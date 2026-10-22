import "@fontsource-variable/inter";
import "@fontsource-variable/nunito";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "./stil/belirtecler.css";
import "./stil/temalar.css";
import "./stil/temel.css";
import { sorguIstemcisiOlustur } from "./sorgu";
import { Uygulama } from "./Uygulama";

const kok = document.getElementById("kok");
if (!kok) throw new Error("index.html içinde #kok yok");

// Tasarım yönü önizlemesi (geçici): ?tema=sicak ya da ?tema=kurumsal; seçim tarayıcıda hatırlanır.
// Kullanıcı bir yön seçince bu blok ve temalar.css kaldırılır (docs/arayuz-plani.md).
try {
  const istenen = new URLSearchParams(location.search).get("tema");
  if (istenen) localStorage.setItem("tema", istenen);
  const tema = istenen ?? localStorage.getItem("tema");
  if (tema === "sicak" || tema === "kurumsal") document.documentElement.dataset.tema = tema;
} catch {
  // localStorage kapalıysa varsayılan görünüm kalır.
}

// StrictMode: yalnızca geliştirmede, bileşenleri ve etkileri (effect) bilerek iki kez çalıştırır.
// Böylece "iki kez çalışınca bozulan" kod (temizlenmeyen zamanlayıcı, çift istek) erkenden görünür.
createRoot(kok).render(
  <StrictMode>
    <BrowserRouter>
      <Uygulama sorguIstemcisi={sorguIstemcisiOlustur()} />
    </BrowserRouter>
  </StrictMode>,
);
