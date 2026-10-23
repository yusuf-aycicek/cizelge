// Betiklerin (taşma denetimi, ekran görüntüsü) geliştirme veritabanına kaydettiği deneme okullarını
// siler: `python -m okulapi deneme-temizle` (örnek okula dokunmaz). Betikler iş bitince çağırır;
// deneme verisi veritabanında birikmez.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

export function denemeOkullariniTemizle() {
  const python = ["Scripts/python.exe", "bin/python"].map((p) => resolve("..", "api", ".venv", p)).find(existsSync);
  if (!python) {
    console.warn("Deneme okulları silinemedi: api/.venv bulunamadı. Elle: cd api && OKULAPI_ORTAM=gelistirme python -m okulapi deneme-temizle");
    return;
  }
  const sonuc = spawnSync(python, ["-m", "okulapi", "deneme-temizle"], {
    cwd: resolve("..", "api"),
    env: { ...process.env, OKULAPI_ORTAM: "gelistirme", PYTHONIOENCODING: "utf-8" },
    encoding: "utf-8",
  });
  if (sonuc.status !== 0) console.warn(`Deneme okulları silinemedi (çıkış ${sonuc.status}): ${sonuc.stderr}`);
  else console.log(sonuc.stdout.trim());
}
