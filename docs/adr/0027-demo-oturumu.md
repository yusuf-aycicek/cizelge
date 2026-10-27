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

## Değerlendirilen alternatifler

- **Parolayı arayüze gömmek:** en kısa yol; parola herkese açılır, kullanıcı istemedi.
- **Ucun sunucudaki parolayla `giris`'i çağırması:** parola doğrulaması aynen kalır, ama yukarıdaki
  kilit sorunu ve demo kullanıcısı parolayı değiştirince düğmenin bozulması kalır.
- **Ayrı bir "misafir" rolü:** salt okunur demo daha güvenli olurdu, ama rol modelini değiştirir;
  ilk sürüm için gereksiz.

## Sonuçları

- Demo hesabıyla giren herkes o okulun müdürüdür: veriyi değiştirebilir, silebilir. Demo okul
  paylaşılan bir deneme alanıdır; bozulursa `python -m okulapi demo-okul` yeniden kurar (hesap
  silinmişse).
- `ACIK_UCLAR` listesine iki uç eklendi (`api/tests/test_kimlik_api.py`).
