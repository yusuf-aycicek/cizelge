"""Sunucuda çalıştırılan yönetim komutları. API'den erişilemez.

    python -m okulapi parola-sifirla <email>             yeni parola sorulur (iki kez, görünmez)
    python -m okulapi parola-sifirla <email> --rastgele  rastgele parola üretilir, bir kez gösterilir

Docker'da: docker compose exec api python -m okulapi parola-sifirla <email>

Okul müdürü parolasını unuttuğunda sistemi işleten kişi içindir (e-postayla sıfırlama yok,
ADR 0012). Parola değişir, kullanıcının bütün oturumları kapanır, kaba kuvvet kilidi kalkar.
Veritabanına uygulamanın rolüyle bağlanır; kullanıcı, giriş fonksiyonuyla e-postadan bulunur.

Çıkış kodları: 0 başarılı, 1 kullanıcı bulunamadı, 2 parola geçersiz ya da eşleşmedi.
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


def main(argv: list[str] | None = None, fabrika: sessionmaker | None = None) -> int:
    ayristirici = argparse.ArgumentParser(prog="python -m okulapi", description="Sunucu yönetim komutları")
    komutlar = ayristirici.add_subparsers(dest="komut", required=True)
    sifirla = komutlar.add_parser("parola-sifirla", help="Bir kullanıcının parolasını sıfırlar")
    sifirla.add_argument("email")
    sifirla.add_argument("--rastgele", action="store_true", help="Rastgele parola üret ve göster")
    secim = ayristirici.parse_args(argv)

    ayarlar = Ayarlar()
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
