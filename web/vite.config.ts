/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Arayüz ile API tarayıcıya aynı kökenden görünür (ADR 0013): tarayıcı yalnızca Vite'ı görür,
// Vite /api isteklerini API'ye iletir. Hedef: bilgisayarda localhost:8000, docker-compose'da
// api konteyneri (VITE_API_HEDEF).
const apiHedefi = process.env.VITE_API_HEDEF ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": { target: apiHedefi } },
    // Windows'ta Docker'a bağlanan klasörde dosya değişiklikleri olayla gelmez: yoklama.
    watch: process.env.WEB_YOKLAMA ? { usePolling: true, interval: 300 } : undefined,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/kurulum.ts"],
    // Varsayılan 5 sn; yük altında akış testleri (giriş + yönlendirme + birkaç istek) aşabiliyordu.
    testTimeout: 15_000,
    // Varsayılan, bütün çekirdekler kadar işçi. Docker (veritabanı, API, worker) aynı makinede
    // çalışırken işçiler birbirini yavaşlatıp bekleme sürelerini aşıyordu (tek başına geçen testler
    // toplu çalıştırmada düşüyordu). Yarısıyla sınırlamak kararsızlığı kaldırdı, toplam süre de kısaldı (ölçüm: 84 sn → 32 sn).
    maxWorkers: "50%",
    css: { modules: { classNameStrategy: "non-scoped" } },
  },
});
