# ADR 0028: Arayüz de Render'daki servisten sunulur

Durum: Kabul edildi (2026-11-03, kullanıcının kararıyla). ADR 0026'nın "arayüz Cloudflare Pages'te"
kısmının yerine geçer; API, worker, kuyruk ve veritabanı aynı yerde kalır.

## Bağlam

`*.pages.dev` adresleri Türkiye'den erişime kapalı; `*.onrender.com` adresleri açılıyor. Hedef
kullanıcılar Türkiye'deki okullar olduğu için arayüz Pages'te kaldıkça canlı demo kullanılamıyor.
Koşul aynı: yalnızca ücretsiz planlar (Render ücretsiz web servisi: 512 MB bellek).

## Karar

Derlenmiş arayüz API'yle aynı Docker imajına girer ve aynı servisten sunulur:

- `api/Dockerfile` iki aşamalıdır: `node:22-slim` aşaması `npm ci && npm run build` çalıştırır, son
  imaja (`python:3.14-slim`) yalnızca `web/dist` kopyalanır (`/app/arayuz`, ~1 MB). Node, npm ve
  `node_modules` son imajda yoktur.
- FastAPI, `OKULAPI_ARAYUZ_DIZINI` verilmişse bu dizini sunar (`okulapi/cekirdek/arayuz.py`):
  - `/api/*` her zaman API'nindir; tanımsız API yolu JSON 404 döner, index.html değil.
  - `/assets/*` (adında içerik özeti olan dosyalar) `Cache-Control: public, max-age=31536000,
    immutable`; olmayan asset 404'tür.
  - index.html ve diğer dosyalar `no-cache`.
  - Bilinmeyen her yol index.html döner; sayfayı React Router seçer (`/giris`, `/program/<id>`,
    `/p/<jeton>`), sayfa yenileme 404 vermez.
  - Dizinin dışına çıkan yol (`../`) sunulmaz.
- Tarayıcı arayüzü ve API'yi yine aynı kökenden görür (ADR 0013 değişmez): oturum çerezi
  `SameSite=Strict`, `Path=/api` kalır, CORS yoktur. Köken denetimine (`OKULAPI_IZINLI_KOKENLER`)
  Render adresi eklenir.

Cloudflare Pages projesi ve `web/functions/` şimdilik silinmez: Pages adresi erişilebilen yerlerde
çalışmaya devam eder, geri dönüş kolay kalır.

## Değerlendirilen alternatifler

- **Ayrı bir Render statik sitesi:** ücretsizdir, ama arayüz ile API farklı kökenlere düşer: ya CORS
  ve `SameSite=None` çerez (ADR 0013'ü gevşetir) ya da statik sitede `/api` yeniden yazma kuralı
  gerekir. Tek servis daha basit.
- **Pages'in önüne özel alan adı:** alan adı ücretli ve engelin alan adına değil Cloudflare'in
  paylaşılan adreslerine olup olmadığı belirsiz.
- **StaticFiles bağlamak:** başlıkları (immutable / no-cache) ve "bilinmeyen yol → index.html,
  olmayan asset → 404" ayrımını özelleştirmek için yine sınıf yazmak gerekiyordu; tek bir yol
  fonksiyonu daha kısa ve testli.

## Sonuçlar

- Tek adres: `https://cizelge-api.onrender.com` hem arayüz hem API. Ücretsiz planın uyuması
  (ilk açılışın yavaşlığı) artık arayüzü de etkiler; arayüz zaten "Sunucu uyanıyor" diyordu.
- İmaj yerelde ölçüldü: 700 → 702 MB; 512 MB sınırıyla çalışırken (worker bir program üretmişken)
  284 MB bellek.
- İmaj derlemesi Node aşaması kadar uzar; aşama önbelleklidir (`package*.json` değişmedikçe
  `npm ci` yeniden çalışmaz).
- Docker Compose'daki `api` konteyneri de arayüzü `localhost:8000` adresinden sunar; geliştirmede
  yine Vite (`localhost:5173`) kullanılır.
