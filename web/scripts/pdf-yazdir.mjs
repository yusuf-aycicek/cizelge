// Bir HTML dosyasını PDF'e yazdırır (bilgisayardaki Edge, Playwright ile). Sayfa boyu ve sayfa
// numaraları sayfanın kendi CSS'indeki @page kurallarından gelir. scripts/md_pdf.py çağırır.
//
//   node scripts/pdf-yazdir.mjs <girdi.html> <cikti.pdf>
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const [girdi, cikti] = process.argv.slice(2);
if (!girdi || !cikti) {
  console.error("kullanım: node scripts/pdf-yazdir.mjs <girdi.html> <cikti.pdf>");
  process.exit(2);
}
const tarayici = await chromium.launch({ channel: "msedge" });
try {
  const sayfa = await tarayici.newPage();
  await sayfa.goto(pathToFileURL(resolve(girdi)).href, { waitUntil: "load" });
  await sayfa.pdf({
    path: resolve(cikti),
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
  });
} finally {
  await tarayici.close();
}
