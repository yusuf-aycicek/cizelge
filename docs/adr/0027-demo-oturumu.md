# ADR 0027: "Demo ile dene" düğmesi için ayrı oturum ucu

Durum: Kabul edildi (2026-10-27, kullanıcının kararıyla).

## Bağlam

Yayındaki sistemi deneyen kişi, demo okulun (ADR 0026) e-postasını ve parolasını bilmeden tek
tıkla girebilmeli. Parola arayüz koduna yazılırsa herkesin indirdiği JavaScript'te görünür ve
yalnızca demoya değil, `/api/giris`'e de verilebilen genel bir parola olur.

## Karar

- `POST /api/oturum/demo` yalnızca `demo@cizelge.test` hesabına oturum açar. E-posta sunucuda
  sabittir; istek gövdesi okunmaz. Oturum ve çerez girişteki gibidir (`_oturum_ac`, `_cerez_yaz`):
  aynı süreler, `HttpOnly`, `SameSite=Strict`, köken denetimi.
- Uç yalnızca sunucuda `OKULAPI_DEMO_PAROLA` tanımlıysa çalışır; değilse 404. `GET
  /api/oturum/demo` yalnızca `{"acik": true|false}` döner, arayüz düğmeyi buna göre gösterir.
- Parola doğrulanmaz ve kaba kuvvet kilidine bakılmaz. Hesap herkese açık olduğu için parolanın
  burada koruyacağı bir şey yoktur; kilide bakılsaydı biri `/api/giris`'e beş yanlış parola
  göndererek demoyu 15 dakika kilitleyebilirdi.

### Demo okulun sıfırlanması (2026-10-27, kullanıcının önerisiyle)

Demo hesabıyla giren herkes müdür olduğu için biri veriyi bozarsa sonraki kişi bozuk okul görür.

- Demo girişinden hemen önce `demo_okulu_tazele` (`ornek_okul.py`) çalışır. Demo okul
  `OKULAPI_DEMO_SIFIRLAMA_DK` dakikadan (varsayılan 60) eskiyse yalnızca o okul silinir ve mini
  veri setiyle baştan kurulur. Demo okul hiç yoksa (silinmiş ya da önceki kurulum yarıda kalmış)
  aynı yolla kurulur.
- "Son sıfırlama" okulun `olusturma` zamanıdır: sıfırlama okulu yeniden oluşturduğu için ayrı bir
  sütun ya da migration gerekmez. Süre veritabanının saatiyle ölçülür.
- Silinecek okul demo e-postasının okuludur; silme o okulun kimliğiyle sınırlıdır (`okulu_sil`,
  RLS'de aktif okul o okul). Başka okulun verisinin kalıp kalmadığını test denetler.
- İki giriş aynı anda sıfırlamaya kalkarsa PostgreSQL danışma kilidi (`pg_advisory_xact_lock`)
  ikincisini bekletir; ikinci giriş durumu kilitten sonra okur ve okulu taze bulur.
- Sıfırlama demo okulun bütün oturumlarını da kapatır: o sırada demoyu kullanan biri giriş
  sayfasına döner. Bir saatlik aralıkta bu nadirdir; demo bir deneme alanıdır.

Neden giriş anında: Render'ın ücretsiz planında zamanlanmış iş (cron) yoktur. Dışarıdan
zamanlanmış bir iş (ör. GitHub Actions) hem gizli bir yönetim ucu gerektirirdi hem de uyuyan
servisi boşuna uyandırırdı. Giriş anında sıfırlama yalnızca biri demoyu açarken çalışır; bedeli o
kişinin girişinin bir kaç saniye uzamasıdır.

## Değerlendirilen alternatifler

- **Parolayı arayüze gömmek:** en kısa yol; parola herkese açılır, kullanıcı istemedi.
- **Ucun sunucudaki parolayla `giris`'i çağırması:** parola doğrulaması aynen kalır, ama yukarıdaki
  kilit sorunu ve demo kullanıcısı parolayı değiştirince düğmenin bozulması kalır.
- **Ayrı bir "misafir" rolü:** salt okunur demo daha güvenli olurdu, ama rol modelini değiştirir;
  ilk sürüm için gereksiz.

## Sonuçları

- Demo hesabıyla giren herkes o okulun müdürüdür: veriyi değiştirebilir, silebilir. Demo okul
  paylaşılan bir deneme alanıdır; en geç bir saat sonraki demo girişinde ilk haline döner.
- `ACIK_UCLAR` listesine iki uç eklendi (`api/tests/test_kimlik_api.py`).
