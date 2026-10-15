import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "./stil/belirtecler.css";
import "./stil/temel.css";
import { sorguIstemcisiOlustur } from "./sorgu";
import { Uygulama } from "./Uygulama";

const kok = document.getElementById("kok");
if (!kok) throw new Error("index.html içinde #kok yok");

// StrictMode: yalnızca geliştirmede, bileşenleri ve etkileri (effect) bilerek iki kez çalıştırır.
// Böylece "iki kez çalışınca bozulan" kod (temizlenmeyen zamanlayıcı, çift istek) erkenden görünür.
createRoot(kok).render(
  <StrictMode>
    <BrowserRouter>
      <Uygulama sorguIstemcisi={sorguIstemcisiOlustur()} />
    </BrowserRouter>
  </StrictMode>,
);
