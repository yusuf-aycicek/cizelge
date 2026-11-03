# ADR 0026: Ücretsiz yayın: Cloudflare Pages + Render + Neon

Durum: Kabul edildi (2026-10-26, kullanıcının kararıyla). Arayüzün yeri ADR 0028 ile değişti:
arayüz de Render'daki servisten sunulur (`*.pages.dev` Türkiye'den erişilemiyor).

## Bağlam

Sistem, bilgisayar kapalıyken de denenebilsin diye internette kalıcı bir adreste yayınlanacak.
Koşul: yalnızca ücretsiz planlar. Kullanıcının seçtiği barındırıcılar: arayüz Cloudflare
Pages'te, API Render'da (Frankfurt), veritabanı Neon'da (Frankfurt).

Bu seçim mimarinin iki varsayımıyla çatışıyor:

1. Arayüz ile API tarayıcıya aynı kökenden görünür; oturum çerezi `SameSite=Strict`'tir, CORS
   yoktur (ADR 0012, 0013). `*.pages.dev` ile `*.onrender.com` ise farklı sitelerdir: tarayıcı
   çerezi API'ye göndermez.
2. API ve worker ayrı süreçlerdir, aralarında Redis vardır (ADR 0011). Render'ın ücretsiz planında
   arka plan worker servisi yoktur.

## Karar

- **Aynı köken, Pages Function ile.** `web/functions/api/[[path]].ts`, `/api/*` isteklerini
  Render'daki API'ye olduğu gibi iletir. Tarayıcı yalnızca Pages adresini görür. Bu, geliştirmedeki
  Vite proxy'sinin yayındaki karşılığıdır. Çerez, CORS ve köken denetimi değişmez; API'de yalnızca
  `OKULAPI_IZINLI_KOKENLER` Pages adresini içerir. Arayüzde API adresi diye bir ayar yoktur.
- **API ve worker tek serviste.** `docker/yayin-baslat.sh` sırayla migration'ları çalıştırır, demo
  okulu kurar (yoksa), worker'ı arka planda başlatır (ölürse yeniden), API'yi `$PORT` üzerinde açar.
  Kuyruk, Render'ın ücretsiz Key Value servisidir. Kod değişmez: worker yine aynı kuyruğu dinler,
  ileride ayrı servise taşımak yalnızca başlangıç komutunu değiştirir.
- **Neon'un sahip rolü süper kullanıcı değildir.** Fonksiyonları `okul_giris` ve `okul_paylasim`
  rollerine devreden iki migration, süper kullanıcı olmayan bir rolle de çalışacak şekilde
  düzeltildi: rolü oluşturan migration rolü kendisine verir; devir sırasında yeni sahibe şemada
  geçici CREATE yetkisi verilir. Bu, Neon benzeri bir veritabanında (süper kullanıcı olmayan
  sahip, PostgreSQL 17) denendi.
- **Neon'da "direct" (pooled olmayan) adres kullanılır.** RLS'nin okul ayarı işlem düzeyindedir
  (`set_config(..., true)` = `SET LOCAL`); PgBouncer'ın işlem havuzlamasıyla da doğru çalışırdı.
  Yine de migration'lar (DDL, DO blokları) ve tek bir sunucunun az sayıdaki bağlantısı için
  havuzlayıcıya gerek yoktur; bir katman eksik, bir belirsizlik eksik.
- **Bellek.** Ücretsiz servis 512 MB'tır. Çözücü 2 iş parçacığıyla çalışır
  (`OKULAPI_COZUCU_IS_PARCACIGI=2`). Mini setle 0,5 işlemcide üretim 6 sn, bellek ~280 MB ölçüldü.

## Değerlendirilen alternatifler

- **CORS + `SameSite=None` çerez.** Üçüncü taraf çerezi olur; Safari engeller, Chrome
  kısıtlıyor. iPhone'dan giriş yapılamazdı. Ayrıca CSRF korumasının ilk katmanı kalkardı.
- **Arayüzü de Render'dan (FastAPI) sunmak.** Tek servis, proxy yok; ama arayüz de sunucuyla
  birlikte uyur. Kullanıcı Cloudflare'i istedi.
- **Ayrı worker servisi / dış Redis (Upstash).** Ücretli ya da gereksiz bir hesap daha.

## Sonuçlar

- Render'ın ücretsiz servisi 15 dakika istek gelmezse uyur; ilk istek 30-60 sn sürebilir. Arayüz
  3 sn'den uzun süren istekte "Sunucu uyanıyor" bildirimi gösterir (`web/src/api/uyanma.ts`).
- Worker API ile aynı bellek ve işlemciyi paylaşır. Gerçekçi boyutta bir okul yavaş üretilir; bu
  yayın bir deneme ortamıdır.
- Tablo sahibinin adresi (`OKULAPI_MIGRASYON_URL`) API servisinde de bulunur (Docker Compose'daki
  gibi). Ücretsiz planda ayrı bir "deploy öncesi" adımı yoktur.
- Demo okul `python -m okulapi demo-okul` ile kurulur: hiçbir şeyi silmez, hesap varsa bir şey
  yapmaz, yarıda kalırsa yarım okulu geri siler. Parolası depoda değil, Render'daki gizli
  değişkende; bütün parolalar gibi en az 12 karakterdir (daha kısaysa demo okul kurulmaz, API yine
  açılır, hata günlükte görünür).
