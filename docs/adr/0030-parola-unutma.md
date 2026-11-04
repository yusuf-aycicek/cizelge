# ADR 0030: Parolasını unutan kullanıcı, e-posta olmadan

Durum: Kabul edildi (2026-11-04, kullanıcının kararıyla).

## Bağlam

Giriş ekranında "Parolamı unuttum" yoktu. Bilinen yol, kullanıcıya e-postayla tek kullanımlık
sıfırlama bağlantısı göndermektir. Sistemde e-posta altyapısı yok: gönderici alan adı, SPF ve
DKIM, ücretli ya da kotalı bir gönderim hizmeti ve teslim edilemeyen postaların takibi
gerekirdi. Yayın yalnızca ücretsiz planlarla yapılıyor (ADR 0026). Kullanıcılar bir okulun
birkaç yöneticisi, birbirlerini tanıyorlar.

## Karar

En sade çözüm, kimliği zaten bilen birinin parolayı yenilemesidir:

1. **Okulun müdürü** başka bir kullanıcının parolasını Kullanıcılar sayfasından yeniler ("Parola").
   Bu uç zaten vardı: `PUT /api/kullanicilar/{id}/sifre`. Yalnızca müdür rolü kullanabilir. Yeni
   parola belirlenince o kullanıcının bütün oturumları kapanır (ADR 0012).
2. **Giriş ekranında not:** parola alanının açıklaması "Parolanızı unuttuysanız okul yöneticinize
   başvurun." Ekran okuyucu da alanla birlikte okur.
3. **Tek müdür kendi parolasını unutursa** (okulda parolayı yenileyebilecek başka müdür yoksa)
   sistemi işleten kişi, sunucu yönetim komutuyla parolayı yeniler:

   ```
   python -m okulapi parola-sifirla <email> --rastgele
   ```

   Komut rastgele bir parolayı bir kez gösterir ve kullanıcının bütün oturumlarını kapatır.
   Yeni parola müdüre okul dışı bir yoldan (telefon, yüz yüze) iletilir. Müdür girince
   Hesabım sayfasından değiştirir.
   - Geliştirmede: `docker compose exec api python -m okulapi parola-sifirla <email> --rastgele`.
   - Yayında (Render ücretsiz planında kabuk yok): işletici komutu kendi makinesinden, yayın
     veritabanının bağlantı ayarıyla çalıştırır (`.env.example`'daki değişkenler). Bağlantı adresi
     koda ya da belgelere yazılmaz.
   - İşletici, isteğin gerçekten o okulun müdüründen geldiğini okul dışı bir yoldan doğrular
     (okulun resmî telefonu). Bu adım teknik değil, ama sistemin en zayıf noktasıdır.
4. **Öneri:** her okulda en az iki kişinin müdür rolünde olması. Böylece 3. yola nadiren gerekir.
   Kullanıcılar sayfası okulda tek müdür olduğunu zaten gösteriyor.

## Değerlendirilen alternatifler

- **E-postayla sıfırlama bağlantısı.** Kullanıcı için en rahatı, ama altyapı ve bakım gerektirir
  (yukarıda). E-posta eklenirse bu ADR'nin yerine geçer: jeton `oturum` gibi özetiyle saklanır,
  kısa ömürlü ve tek kullanımlık olur.
- **Güvenlik sorusu.** Tahmin edilebilir yanıtlar ve ek veri. Bugün güvenli sayılmıyor.
- **Müdür yardımcısının müdürün parolasını yenilemesi.** Yetkiyi yükseltmenin yolu olurdu: yardımcı
  müdürün hesabına geçebilirdi. Reddedildi.

## Sonuçlar

- Kod değişikliği yalnızca giriş ekranındaki not. Sıfırlama ucu ve komut zaten vardı ve testliydi.
- Tek müdürlü okulda unutulan parola işleticiye bağımlıdır. Okul sayısı artarsa e-postalı
  sıfırlama yeniden değerlendirilir.
