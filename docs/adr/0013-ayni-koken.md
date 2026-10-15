# ADR 0013: Arayüz ve API tarayıcıya aynı kökenden görünür

Durum: Kabul edildi (2026-10-15).

## Bağlam

Oturum jetonu `SameSite=Strict` bir çerezde taşınır. Veri değiştiren isteklerde ayrıca `Origin`
başlığı denetlenir (ADR 0012). Arayüz (yapım sırası 5) React/Vite ile yazılacak ve geliştirmede
ayrı bir sunucuda (Vite, `localhost:5173`) çalışacak. API ise `localhost:8000`'de.

Tarayıcı açısından bunlar iki ayrı **köken**dir (origin = şema + alan adı + port). Arayüz API'ye
doğrudan `http://localhost:8000` adresinden istek atsaydı:
- CORS (kökenler arası kaynak paylaşımı) gerekirdi: ön kontrol istekleri (preflight), çerezli
  istekler için `credentials: include`, sunucuda izin başlıkları;
- köken denetimi bu isteklere izin verecek şekilde gevşetilmeliydi;
- geliştirme ortamı yayından farklı davranırdı.

## Karar

**Arayüz ile API tarayıcıya her zaman aynı köken üzerinden görünür.**

- **Geliştirme:** tarayıcı yalnızca Vite'ı görür (`http://localhost:5173`). Vite'ın proxy'si `/api`
  ile başlayan istekleri API'ye (`http://localhost:8000`) iletir. Tarayıcı için çerez de istek de
  aynı kökendendir: CORS yok, `SameSite=Strict` sorunsuz çalışır. API, veri değiştiren isteklerde
  `Origin: http://localhost:5173` görür; bu köken izinli listededir.
- **Yayın:** arayüzün derlenmiş dosyaları ile API aynı alan adının arkasındadır, ör.
  `https://dersprogrami.example` (statik dosyalar) ve `https://dersprogrami.example/api`. Bir ters
  vekil sunucu (reverse proxy, ör. nginx ya da Caddy) bunu sağlar. İzinli köken o alan adıdır.
- **Ayarlar** (ortam değişkenleri, önek `OKULAPI_`):
  - `izinli_kokenler`: veri değiştiren isteklerde kabul edilen `Origin` değerleri. Varsayılan boş:
    tarayıcıdan gelen hiçbir yazma isteği kabul edilmez. Ortam açıkça belirtmek zorundadır
    (güvenli varsayılan). Geliştirmede (docker-compose) Vite'ın adresi ve API'nin `/docs` sayfası.
  - `cerez_secure`: varsayılan açık (çerez yalnızca HTTPS üzerinden gider). Yerel geliştirmede
    http üzerinden çalışılabilsin diye docker-compose kapatır. Yayında açık kalır.
- CORS ara katmanı **eklenmez**. Kökenler arası istek gerekmediği için sunucu kökenler arası
  isteklere izin vermez.

## Değerlendirilen alternatifler

- **CORS ile iki ayrı köken:** geliştirmede de yayında da ek yapılandırma, çerezler için
  `SameSite=None` (bu da `Secure` ve HTTPS gerektirir, CSRF korumasını zayıflatır). Bu sistemde
  ayrı kökenin getirisi yok.
- **Jetonu çerez yerine `Authorization` başlığında taşımak:** CORS ve CSRF sorunu ortadan kalkardı,
  ama jeton JavaScript'in okuyabildiği bir yerde (`localStorage`) durur ve XSS ile çalınabilir
  (ADR 0012).
- **Köken denetimini yalnızca `SameSite`'a bırakmak:** modern tarayıcılarda yeterli. Ama ikinci
  katman ucuz ve eski ya da hatalı tarayıcılara karşı korur.

## Sonuçlar

- Arayüz kodu API'yi göreli adresle çağırır (`fetch("/api/ben")`): geliştirmede ve yayında aynı.
- Tarayıcı dışı istemciler (curl, testler) `Origin` göndermez; köken denetiminden geçer ama
  geçerli bir oturum çerezi gerektirir.
- Yeni bir ortam (ör. test sunucusu) kurulurken `OKULAPI_IZINLI_KOKENLER` verilmezse tarayıcıdan
  giriş bile yapılamaz (403). Hata mesajı "köken denetimi"ni söyler.
