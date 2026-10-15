"""Kimlik servisleri: kayıt, giriş, çıkış, oturum çözme; okulun kullanıcılarının yönetimi (ADR 0012).

`KimlikServisi` okul bilinmeden başlayan işleri yürütür (kayıt, giriş, oturum çözme, sunucudaki
parola sıfırlama). Bu yüzden tek bir oturum değil oturum fabrikası alır: önce okulsuz bir
oturumla veritabanı fonksiyonlarına (`giris_bilgisi`, `oturum_coz`, kaba kuvvet sayacı) sorar,
okulu öğrenince işe o okulun oturumuyla (ORM filtresi + RLS) devam eder.

`KullaniciServisi` ise bir okulun içinde, giriş yapmış bir kullanıcı adına çalışır.

Oturumları geçersiz kılma kuralları:
- müdür bir kullanıcının parolasını yeniden belirlerse o kullanıcının **bütün** oturumları silinir;
- kullanıcı kendi parolasını değiştirirse o anki oturumu dışındaki bütün oturumları silinir;
- sunucudaki `parola-sifirla` komutu bütün oturumları siler;
- silinen kullanıcının oturumları veritabanında silinir (yabancı anahtar ON DELETE CASCADE).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.kiraci import okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.kimlik import parola
from okulapi.cekirdek.modeller import Kullanici, Okul, Oturum
from okulapi.cekirdek.servisler import GecersizVeri, KayitBulunamadi, KayitCakismasi

ROLLER = ("mudur", "mudur_yardimcisi")


# --- istisnalar (main.py durum kodlarına çevirir) ---------------------------------------------

class GirisHatasi(Exception):
    """401. Yanlış e-posta ile yanlış parola aynı mesajı alır."""

    def __init__(self, mesaj: str = "E-posta ya da parola hatalı") -> None:
        super().__init__(mesaj)


class CokFazlaDeneme(Exception):
    """429. Kayıtlı olsun olmasın her e-posta için aynı davranır."""

    def __init__(self, dakika: int) -> None:
        super().__init__(f"Çok fazla hatalı deneme. {dakika} dakika sonra yeniden deneyin.")


class YetkiYok(Exception):
    """403. Kullanıcı girişli ama bu işe yetkisi yok."""


class EpostaKullaniliyor(KayitCakismasi):
    def __init__(self) -> None:
        super().__init__("Bu e-posta adresi başka bir hesapta kullanılıyor")


class SonMudur(KayitCakismasi):
    def __init__(self, islem: str) -> None:
        super().__init__(f"Okulun son müdürü {islem}. Önce başka bir kullanıcıyı müdür yapın.")


# --- yardımcılar ------------------------------------------------------------------------------

@dataclass(frozen=True)
class OturumBilgisi:
    """İsteği yapanın kim olduğu: `oturum_coz` sonucu."""

    oturum_id: uuid.UUID
    kullanici_id: uuid.UUID
    okul_id: uuid.UUID


def jeton_uret() -> str:
    """32 bayt rastgele; URL'de ve çerezde güvenle taşınır (43 karakter)."""
    return secrets.token_urlsafe(32)


def jeton_ozeti(jeton: str) -> str:
    """Veritabanında jeton değil özeti saklanır. Jeton zaten rastgele ve uzun olduğu için yavaş bir
    özete (argon2) gerek yok: SHA-256 yeterli ve her istekte ucuz."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def eposta_duzelt(email: str) -> str:
    return email.strip().lower()


def _sqlstate(hata: IntegrityError) -> str | None:
    return getattr(hata.orig, "sqlstate", None)


def _eposta_cakismasi_mi(hata: IntegrityError) -> bool:
    return _sqlstate(hata) == "23505" and "uq_kullanici_email_kucuk" in str(hata.orig)


# --- okul bilinmeden başlayan işler -----------------------------------------------------------

class KimlikServisi:
    def __init__(self, fabrika: sessionmaker, ayarlar: Ayarlar | None = None) -> None:
        self.fabrika = fabrika
        self.ayarlar = ayarlar or Ayarlar()

    # -- veritabanı fonksiyonları (okulsuz oturumla) --

    def _giris_bilgisi(self, oturum: Session, email: str):
        tablo = func.giris_bilgisi(email).table_valued("kullanici_id", "okul_id", "sifre_hash")
        return oturum.execute(select(tablo)).mappings().first()

    def _eposta_kullaniliyor_mu(self, email: str) -> bool:
        with okulsuz_oturum(self.fabrika) as o:
            return self._giris_bilgisi(o, email) is not None

    def _sayaci_sil(self, email: str) -> None:
        with okulsuz_oturum(self.fabrika) as o:
            o.execute(select(func.giris_denemelerini_sil(email)))
            o.commit()

    def _oturum_ac(self, oturum: Session, okul_id: uuid.UUID, kullanici_id: uuid.UUID) -> str:
        """`oturum` o okulun oturumu olmalı. Jetonu döner; commit çağırana aittir."""
        jeton = jeton_uret()
        simdi = datetime.now(timezone.utc)
        # Bu kullanıcının süresi dolmuş eski oturumları da temizlenir.
        oturum.execute(delete(Oturum).where(
            Oturum.kullanici_id == kullanici_id,
            (Oturum.bitis_mutlak < func.now()) | (Oturum.son_kullanim + Oturum.hareketsizlik_siniri < func.now()),
        ))
        oturum.add(Oturum(
            okul_id=okul_id, kullanici_id=kullanici_id, jeton_ozeti=jeton_ozeti(jeton),
            hareketsizlik_siniri=timedelta(hours=self.ayarlar.oturum_hareketsizlik_saat),
            bitis_mutlak=simdi + timedelta(days=self.ayarlar.oturum_en_uzun_gun),
        ))
        return jeton

    # -- işler --

    def kayit(self, okul_alanlari: dict, ad: str, email: str, sifre: str) -> tuple[Okul, Kullanici, str]:
        """Okul, ilk müdür ve oturumu **tek işlemde** oluşturur. (okul, müdür, jeton) döner."""
        email = eposta_duzelt(email)
        sifre_hash = parola.ozetle(sifre)  # kurala uymayan parola burada durur
        if self._eposta_kullaniliyor_mu(email):
            raise EpostaKullaniliyor()
        okul_id = uuid.uuid4()
        # Yeni okulun oturumu: RLS, okul satırının kendi bağlamında eklenmesine izin verir.
        with okul_oturumu(self.fabrika, okul_id) as o:
            try:
                okul = Okul(id=okul_id, **okul_alanlari)
                o.add(okul)
                o.flush()
                mudur = Kullanici(email=email, sifre_hash=sifre_hash, ad=ad, rol="mudur")
                o.add(mudur)
                o.flush()
                jeton = self._oturum_ac(o, okul_id, mudur.id)
                o.commit()
            except IntegrityError as hata:
                o.rollback()
                if _eposta_cakismasi_mi(hata):  # aynı anda aynı e-postayla iki kayıt
                    raise EpostaKullaniliyor() from hata
                if _sqlstate(hata) == "23514":
                    raise GecersizVeri("Okul ayarları geçersiz") from hata
                raise
            return okul, mudur, jeton

    def giris(self, email: str, sifre: str) -> tuple[OturumBilgisi, str]:
        email = eposta_duzelt(email)
        a = self.ayarlar
        with okulsuz_oturum(self.fabrika) as o:
            if o.execute(select(func.giris_kilitli_mi(email))).scalar():
                raise CokFazlaDeneme(a.giris_kilit_dk)
            bilgi = self._giris_bilgisi(o, email)
            if bilgi is None:
                parola.sahte_dogrulama(sifre)
                dogru = False
            else:
                dogru = parola.dogrula(bilgi["sifre_hash"], sifre)
            if not dogru:
                o.execute(select(func.giris_hatasi_kaydet(
                    email, a.giris_hata_esigi, timedelta(minutes=a.giris_pencere_dk), timedelta(minutes=a.giris_kilit_dk))))
                o.commit()
                raise GirisHatasi()
            o.execute(select(func.giris_denemelerini_sil(email)))
            o.commit()

        okul_id, kullanici_id = bilgi["okul_id"], bilgi["kullanici_id"]
        with okul_oturumu(self.fabrika, okul_id) as o:
            if parola.yeniden_ozetlenmeli(bilgi["sifre_hash"]):
                o.get(Kullanici, kullanici_id).sifre_hash = parola.ozetle(sifre)
            jeton = self._oturum_ac(o, okul_id, kullanici_id)
            o.flush()
            oturum_id = o.scalars(select(Oturum.id).where(Oturum.jeton_ozeti == jeton_ozeti(jeton))).one()
            o.commit()
        return OturumBilgisi(oturum_id, kullanici_id, okul_id), jeton

    def oturum_coz(self, jeton: str | None) -> OturumBilgisi | None:
        if not jeton or len(jeton) > 200:
            return None
        tablo = func.oturum_coz(jeton_ozeti(jeton)).table_valued("oturum_id", "kullanici_id", "okul_id")
        with okulsuz_oturum(self.fabrika) as o:
            satir = o.execute(select(tablo)).mappings().first()
            o.commit()  # fonksiyon son kullanım zamanını güncellemiş olabilir
        return OturumBilgisi(**satir) if satir else None

    def cikis(self, jeton: str | None) -> None:
        bilgi = self.oturum_coz(jeton)
        if bilgi is None:
            return
        with okul_oturumu(self.fabrika, bilgi.okul_id) as o:
            o.execute(delete(Oturum).where(Oturum.id == bilgi.oturum_id))
            o.commit()

    def parolayi_sifirla(self, email: str, yeni_sifre: str) -> Kullanici:
        """Sunucudaki `parola-sifirla` komutu için (API'de karşılığı yok). Parolayı değiştirir,
        bütün oturumları kapatır, kaba kuvvet kilidini kaldırır."""
        email = eposta_duzelt(email)
        sifre_hash = parola.ozetle(yeni_sifre)
        with okulsuz_oturum(self.fabrika) as o:
            bilgi = self._giris_bilgisi(o, email)
        if bilgi is None:
            raise KayitBulunamadi("Bu e-postayla bir kullanıcı")
        with okul_oturumu(self.fabrika, bilgi["okul_id"]) as o:
            kullanici = o.get(Kullanici, bilgi["kullanici_id"])
            kullanici.sifre_hash = sifre_hash
            o.execute(delete(Oturum).where(Oturum.kullanici_id == kullanici.id))
            o.commit()
            o.expunge(kullanici)
        self._sayaci_sil(email)
        return kullanici


# --- okulun içinde, giriş yapmış kullanıcı adına -----------------------------------------------

class KullaniciServisi:
    """Okulun hesapları. `oturum` isteğin okul oturumudur; `istek` isteği yapanın oturum bilgisi.

    Yönetim işleri (ekle, sil, parola belirle, rol değiştir) yalnızca müdüründür.
    Değişmez kural: her okulda en az bir müdür vardır.
    """

    def __init__(self, oturum: Session, istek: OturumBilgisi, fabrika: sessionmaker | None = None) -> None:
        self.oturum = oturum
        self.istek = istek
        self.fabrika = fabrika

    def _ben(self) -> Kullanici:
        ben = self.oturum.get(Kullanici, self.istek.kullanici_id)
        if ben is None:
            raise KayitBulunamadi("Kullanıcı")
        return ben

    def _mudur_olmali(self) -> None:
        if self._ben().rol != "mudur":
            raise YetkiYok("Bu işlemi yalnızca okul müdürü yapabilir")

    def _getir(self, kullanici_id: uuid.UUID) -> Kullanici:
        k = self.oturum.get(Kullanici, kullanici_id)
        if k is None:  # başka okulun kullanıcısı da (okul filtresi) "bulunamadı"
            raise KayitBulunamadi("Kullanıcı")
        return k

    def _mudurleri_kilitle(self) -> list[uuid.UUID]:
        """Okulun müdür satırlarını işlem sonuna kadar kilitler (FOR UPDATE) ve kimliklerini döner.

        İki müdür aynı anda birbirinin rolünü düşürürse ikisi de "başka müdür var" görebilirdi ve
        okul müdürsüz kalırdı. Kilit, ikinci işlemi birincinin sonucunu beklemeye zorlar; bekledikten
        sonra PostgreSQL satırları yeniden değerlendirir ve rolü düşen satır artık listede olmaz.
        """
        return list(self.oturum.scalars(
            select(Kullanici.id).where(Kullanici.rol == "mudur").order_by(Kullanici.id).with_for_update()))

    def listele(self) -> list[Kullanici]:
        return list(self.oturum.scalars(select(Kullanici).order_by(Kullanici.rol, Kullanici.ad)))

    def yardimci_ekle(self, ad: str, email: str, sifre: str) -> Kullanici:
        self._mudur_olmali()
        kullanici = Kullanici(ad=ad, email=eposta_duzelt(email), sifre_hash=parola.ozetle(sifre), rol="mudur_yardimcisi")
        self.oturum.add(kullanici)
        try:
            self.oturum.commit()
        except IntegrityError as hata:
            self.oturum.rollback()
            if _eposta_cakismasi_mi(hata):
                raise EpostaKullaniliyor() from hata
            raise
        return kullanici

    def parola_belirle(self, kullanici_id: uuid.UUID, yeni_sifre: str) -> None:
        """Müdür bir kullanıcının parolasını yeniden belirler: o kullanıcının **bütün** oturumları
        kapanır (kendisininki dahil; müdür kendi parolası için `kendi_parolasini_degistir`'i
        kullanır, o anki oturumu korunur)."""
        self._mudur_olmali()
        hedef = self._getir(kullanici_id)
        hedef.sifre_hash = parola.ozetle(yeni_sifre)
        self.oturum.execute(delete(Oturum).where(Oturum.kullanici_id == hedef.id))
        self.oturum.commit()

    def kendi_parolasini_degistir(self, eski_sifre: str, yeni_sifre: str) -> None:
        ben = self._ben()
        if not parola.dogrula(ben.sifre_hash, eski_sifre):
            raise GecersizVeri("Mevcut parola hatalı")
        ben.sifre_hash = parola.ozetle(yeni_sifre)
        # O anki oturum dışındaki bütün oturumlar (ör. başka bir bilgisayarda açık kalmış olan).
        self.oturum.execute(delete(Oturum).where(Oturum.kullanici_id == ben.id, Oturum.id != self.istek.oturum_id))
        self.oturum.commit()

    def sil(self, kullanici_id: uuid.UUID) -> None:
        """Oturumları veritabanı siler (ON DELETE CASCADE). Son müdür silinemez."""
        self._mudur_olmali()
        hedef = self._getir(kullanici_id)
        if hedef.rol == "mudur" and self._mudurleri_kilitle() == [hedef.id]:
            raise SonMudur("silinemez")
        self.oturum.delete(hedef)
        self.oturum.commit()

    def rol_degistir(self, kullanici_id: uuid.UUID, rol: str) -> Kullanici:
        """Müdür bir yardımcıyı müdür yapabilir ya da bir müdürün rolünü düşürebilir (kendisininki
        dahil). Son müdürün rolü düşürülemez. Rol her istekte veritabanından okunduğu için oturumlar
        kapatılmaz: yeni rol bir sonraki istekte geçerli olur."""
        if rol not in ROLLER:
            raise GecersizVeri(f"Rol şunlardan biri olmalı: {', '.join(ROLLER)}")
        self._mudur_olmali()
        hedef = self._getir(kullanici_id)
        if hedef.rol == "mudur" and rol != "mudur" and self._mudurleri_kilitle() == [hedef.id]:
            raise SonMudur("rolü düşürülemez")
        hedef.rol = rol
        self.oturum.commit()
        return hedef
