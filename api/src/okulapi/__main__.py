"""Sunucuda çalıştırılan yönetim komutları. API'den erişilemez.

    python -m okulapi parola-sifirla <email>             yeni parola sorulur (iki kez, görünmez)
    python -m okulapi parola-sifirla <email> --rastgele  rastgele parola üretilir, bir kez gösterilir

    OKULAPI_ORTAM=gelistirme python -m okulapi ornek-okul --evet
                                                         geliştirme veritabanını temizler, örnek okulu yükler
                                                         (bilgisayarda çalıştırılır; bkz. okulapi/ornek_okul.py)

Docker'da: docker compose exec api python -m okulapi parola-sifirla <email>

Okul müdürü parolasını unuttuğunda sistemi işleten kişi içindir (e-postayla sıfırlama yok,
ADR 0012). Parola değişir, kullanıcının bütün oturumları kapanır, kaba kuvvet kilidi kalkar.
Veritabanına uygulamanın rolüyle bağlanır; kullanıcı, giriş fonksiyonuyla e-postadan bulunur.

Çıkış kodları: 0 başarılı, 1 kullanıcı bulunamadı, 2 parola geçersiz ya da eşleşmedi (ornek-okul:
2 onay yok), 3 geliştirme ortamı değil (OKULAPI_ORTAM=gelistirme verilmedi).
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys

from sqlalchemy.orm import sessionmaker

import okulapi.cekirdek.kiraci  # noqa: F401  (okul filtresi olayları kaydolur)
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.kimlik.parola import ParolaGecersiz
from okulapi.cekirdek.kimlik.servis import KimlikServisi
from okulapi.cekirdek.servisler import KayitBulunamadi
from okulapi.cekirdek.veritabani import motor_olustur, oturum_fabrikasi


def parola_sifirla(email: str, rastgele: bool, fabrika: sessionmaker, ayarlar: Ayarlar) -> int:
    if rastgele:
        yeni = secrets.token_urlsafe(12)  # 16 karakter
    else:
        yeni = getpass.getpass("Yeni parola: ")
        if getpass.getpass("Yeni parola (tekrar): ") != yeni:
            print("Parolalar eşleşmedi; hiçbir şey değişmedi.", file=sys.stderr)
            return 2
    try:
        kullanici = KimlikServisi(fabrika, ayarlar).parolayi_sifirla(email, yeni)
    except KayitBulunamadi:
        print(f"Bu e-postayla bir kullanıcı yok: {email}", file=sys.stderr)
        return 1
    except ParolaGecersiz as hata:
        print(f"{hata}; hiçbir şey değişmedi.", file=sys.stderr)
        return 2
    print(f"{kullanici.ad} ({kullanici.email}) için parola değiştirildi; bütün oturumları kapatıldı.")
    if rastgele:
        print(f"Yeni parola (yalnızca bir kez gösterilir): {yeni}")
    return 0


def ornek_okul(evet: bool, ayarlar: Ayarlar, veri_seti: str = "mini") -> int:
    from okulapi.ornek_okul import ORNEK_EMAIL, ORNEK_PAROLA, ORTAM_UYARISI, SETLER, ornek_okul_kur

    # İki koruma: açık ortam ayarı (yayında hiç tanımlanmaz) ve onay bayrağı.
    if ayarlar.ortam != "gelistirme":
        print(ORTAM_UYARISI, file=sys.stderr)
        return 3
    if not evet:
        print("Bu komut veritabanındaki BÜTÜN okulları, kullanıcıları ve oturumları siler, sonra örnek "
              "okulu yükler. Yalnızca geliştirme veritabanında kullanın. Devam etmek için: --evet",
              file=sys.stderr)
        return 2
    sayilar = ornek_okul_kur(ayarlar, SETLER[veri_seti])
    print("Örnek okul yüklendi: " + ", ".join(f"{v} {k}" for k, v in sayilar.items()))
    print(f"Giriş: {ORNEK_EMAIL} / {ORNEK_PAROLA}")
    return 0


def deneme_temizle(ayarlar: Ayarlar) -> int:
    from okulapi.ornek_okul import ORTAM_UYARISI, deneme_okullarini_sil

    if ayarlar.ortam != "gelistirme":
        print(ORTAM_UYARISI, file=sys.stderr)
        return 3
    silinen = deneme_okullarini_sil(ayarlar)
    print(f"{len(silinen)} deneme okulu silindi" + (f": {', '.join(sorted(set(silinen)))}" if silinen else "."))
    return 0


def main(argv: list[str] | None = None, fabrika: sessionmaker | None = None, ayarlar: Ayarlar | None = None) -> int:
    ayristirici = argparse.ArgumentParser(prog="python -m okulapi", description="Sunucu yönetim komutları")
    komutlar = ayristirici.add_subparsers(dest="komut", required=True)
    sifirla = komutlar.add_parser("parola-sifirla", help="Bir kullanıcının parolasını sıfırlar")
    sifirla.add_argument("email")
    sifirla.add_argument("--rastgele", action="store_true", help="Rastgele parola üret ve göster")
    ornek = komutlar.add_parser("ornek-okul", help="Geliştirme veritabanını temizler, örnek okulu yükler")
    ornek.add_argument("--evet", action="store_true", help="Bütün verinin silineceğini onaylıyorum")
    ornek.add_argument("--set", dest="veri_seti", choices=["mini", "gercekci"], default="mini",
                       help="Veri seti: mini (varsayılan, hızlı) ya da gercekci (24 şube)")
    komutlar.add_parser("deneme-temizle", help="Betiklerin açtığı deneme okullarını siler (örnek okula dokunmaz)")
    secim = ayristirici.parse_args(argv)

    ayarlar = ayarlar or Ayarlar()
    if secim.komut == "ornek-okul":
        return ornek_okul(secim.evet, ayarlar, secim.veri_seti)
    if secim.komut == "deneme-temizle":
        return deneme_temizle(ayarlar)
    motor = None
    if fabrika is None:
        motor = motor_olustur(ayarlar.veritabani_url)
        fabrika = oturum_fabrikasi(motor)
    try:
        return parola_sifirla(secim.email, secim.rastgele, fabrika, ayarlar)
    finally:
        if motor is not None:
            motor.dispose()


if __name__ == "__main__":
    sys.exit(main())
