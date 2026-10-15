"""Parola özeti: argon2id (ADR 0012).

Parola hiçbir yerde saklanmaz; yalnızca tek yönlü, tuzlu (salt), bilerek yavaş ve bellek yoğun
özeti saklanır. Girişte girilen parola aynı parametrelerle yeniden özetlenip karşılaştırılır.

Kurallar (docs/kimlik-plani.md):
- en az 12, en çok 256 karakter. Üst sınır: çok uzun bir parolayla sunucuyu argon2 hesabıyla
  yormak (DoS) mümkün olmasın;
- karakter türü zorunluluğu yok (büyük harf, rakam, sembol): NIST SP 800-63B önermez, çünkü
  kullanıcıları "Parola1!" gibi tahmin edilebilir kalıplara iter. Uzunluk daha etkilidir.
"""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from okulapi.cekirdek.servisler import GecersizVeri

EN_AZ_UZUNLUK = 12
EN_FAZLA_UZUNLUK = 256

# Kütüphanenin önerdiği varsayılanlar (argon2id, 64 MiB bellek, 3 tur). Testler hız için daha
# ucuz parametrelerle değiştirir (conftest); varsayılanları ayrı bir test denetler.
_OZETLEYICI = PasswordHasher()


class ParolaGecersiz(GecersizVeri):
    pass


def kurala_uygun_mu(parola: str) -> None:
    if len(parola) < EN_AZ_UZUNLUK:
        raise ParolaGecersiz(f"Parola en az {EN_AZ_UZUNLUK} karakter olmalı")
    if len(parola) > EN_FAZLA_UZUNLUK:
        raise ParolaGecersiz(f"Parola en fazla {EN_FAZLA_UZUNLUK} karakter olabilir")


def ozetle(parola: str) -> str:
    """Kurala uymayan parola `ParolaGecersiz` fırlatır. Çıktı ör. `$argon2id$v=19$m=65536,t=3,p=4$...`"""
    kurala_uygun_mu(parola)
    return _OZETLEYICI.hash(parola)


def dogrula(ozet: str, parola: str) -> bool:
    if len(parola) > EN_FAZLA_UZUNLUK:  # uzun girdiyle de hesap yaptırılmasın
        return False
    try:
        return _OZETLEYICI.verify(ozet, parola)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def yeniden_ozetlenmeli(ozet: str) -> bool:
    """Parametreler değiştiyse (ör. bellek artırıldı) eski özet başarılı girişte yenilenir."""
    try:
        return _OZETLEYICI.check_needs_rehash(ozet)
    except InvalidHashError:
        return True


def sahte_dogrulama(parola: str) -> None:
    """Kullanıcı bulunamadığında da bir doğrulama yapılır: yanıt süresi, e-postanın kayıtlı olup
    olmadığını belli etmesin (ADR 0012 madde 5)."""
    dogrula(_sahte_ozet(_OZETLEYICI), parola)


@lru_cache(maxsize=4)
def _sahte_ozet(ozetleyici: PasswordHasher) -> str:
    # Gerçek özetlerle aynı parametreler: doğrulama süresi aynı olsun.
    return ozetleyici.hash("bu-hesap-yok-sahte-parola")
