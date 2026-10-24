# ADR 0021: Excel'den içe aktarma: önizle, sonra özetle onaylanan tek işlem

Durum: Kabul edildi (2026-10-24, 8a).

## Bağlam

Okulların öğretmen, şube, ders ve ders dağılımı listeleri çoğunlukla zaten Excel'dedir. Yüzlerce
satırı elle girmek yerine bir dosyadan aktarılmalı. Kullanıcı yanlış bir dosyayla okulun verisini
bozmamalı: önce ne olacağını görmeli, onaylamadan hiçbir şey kaydedilmemeli, kaydedilirse hepsi ya da
hiçbiri. Aynı dosya iki kez yüklenince kayıtlar çoğalmamalı ("AYŞE YILMAZ" ile "Ayşe  Yılmaz" aynı kişi).

## Karar

1. **İki istek, aynı dosya, durum sunucuda tutulmaz.** `POST /ice-aktarma/onizleme` dosyayı okur
   ve satır satır planı döner (eklenecek, güncellenecek, değişmeyen, hatalı; hatalıda satır
   numarası ve sade neden). `POST /ice-aktarma?ozet=` aynı dosyayla planı **yeniden hesaplar**;
   hatalı satır varsa 422, plan önizlemedekinden farklıysa (özet tutmuyorsa: veri arada değişti)
   409. Kayıt tek veritabanı işlemidir; herhangi bir ihlalde geri alınır.
2. **Eşleştirme adla, Türkçe anahtarla.** `anahtar()`: NFC, "I→ı, İ→i" ile küçük harf, boşluklar
   tekleşmiş, tire ve eğik çizgi çevresi boşluksuz. Var olan kaydın adı değiştirilmez. Okulda aynı
   anahtarla birden çok kayıt varsa (öğretmen adı tekil değil) satır hatalıdır: tahmin edilmez.
3. **Boş hücre "değiştirme" demektir** (branş, grup, atamanın öğretmeni). Silme yoktur: dosyada
   olmayan kayıt okulda kalır. İçe aktarma ekler ve günceller.
4. **Sayfalar adıyla, sütunlar başlığıyla bulunur**; sıra ve fazla sütun önemsiz. Şablonun örnek
   satırı ilk hücresinin "(örnek)" ekiyle tanınır ve okunmaz (gerçek "Ayşe Yılmaz" satırı yanlışlıkla
   atlanmasın diye içerikle değil işaretle).
5. **Gövde dosyanın kendisidir** (multipart değil): ek bağımlılık (`python-multipart`) gerekmez,
   akış okunurken 2 MB sınırı aşılınca kesilir (413).
6. **Sınırlar:** 2 MB dosya, içindeki XML'lerin toplamı 40 MB (sıkıştırma bombası), sayfa başına
   2000 kayıt ve 10000 ham satır. openpyxl salt okunur kipte açılır. Python 3.12'nin expat'i
   "billion laughs" türü varlık genişlemesine karşı korumalıdır.
7. **Yer: ders programı modülü.** Dosya ders dağılımını (modülün tablosu) içerir. Modül çekirdeğe
   bağımlı olabilir, tersi olamaz (ADR 0008); çekirdek kayıtları da modül yazar. Okul filtresi
   depolardan ve oturumdan gelir; içe aktarma ayrı bir izolasyon yolu açmaz.

## Değerlendirilen alternatifler

- **Önizlemeyi sunucuda saklamak** (kimlikli taslak): ikinci istekte dosya gönderilmez, ama süresi
  dolan taslak tablosu ve temizlik işi gerekir. Özet karşılaştırması aynı güvenceyi durumsuz verir.
- **Hatalı satırları atlayıp kalanını kaydetmek:** kullanıcının istemediği yarım veri bırakır;
  istenen "biri hatalıysa hiçbiri".
- **CSV:** okullar Excel kullanıyor; CSV'de Türkçe kodlama ve ayraç (`;` / `,`) sorunları çıkar.

## Sonuçları

- Aynı dosya tekrar yüklenince "değişmeyen" görünür, çoğalma olmaz.
- Okulda var olan iki aynı adlı öğretmen içe aktarmada hata verir; kullanıcı önce adları ayırır.
- Kayıt tek işlem olduğu için büyük dosyada istek birkaç saniye sürebilir; sınırlar bunu küçük tutar.
