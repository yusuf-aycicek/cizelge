"""Çıktı modelini veritabanından doldurur (oturumun okulu; okul filtresi depolardadır).

Blok birleştirme çizelgedekiyle aynı kuraldır (web `birlesikHucreler`): aynı ders atamasının
aynı gündeki art arda saatleri tek hücredir, öğle arası hücreyi böler.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulDeposu, SinifDeposu
from okulapi.cekirdek.kiraci import oturumun_okulu
from okulapi.cekirdek.servisler import KayitBulunamadi, KayitCakismasi
from okulapi.cekirdek.zil import okulun_zilleri
from okulapi.moduller.ders_programi.cikti.model import Cizelge, Hafta, Hucre, ProgramCiktisi
from okulapi.moduller.ders_programi.depo import DersAtamaDeposu, ProgramDeposu, YerlesimDeposu
from okulapi.moduller.ders_programi.kancalar import GUNLER

# Türkiye 2016'dan beri yıl boyu UTC+3; sunucu (Docker) UTC'de çalışır. Tarih yalnızca gösterimdir.
TURKIYE = timezone(timedelta(hours=3))

_ALFABE = "0123456789aâbcçdefgğhıiîjklmnoöprsştuûüvwxyz"


def tr_anahtar(metin: str) -> tuple:
    """Türkçe alfabe sırası; sayılar sayı olarak (9-A, 10-A'dan önce gelir)."""
    parcalar = re.split(r"(\d+)", metin.replace("I", "ı").replace("İ", "i").lower())
    return tuple(
        (0, int(p), ()) if p.isdigit() else (1, 0, tuple(_ALFABE.find(c) if c in _ALFABE else 100 + ord(c) for c in p))
        for p in parcalar if p
    )


def _birlestir(saatler: dict[tuple[int, int], uuid.UUID], ogle_arasi_sonra: int | None) -> list[tuple[int, int, int, uuid.UUID]]:
    """(gün, saat) -> atama haritasından (gün, saat, uzunluk, atama) hücreleri."""
    sonuc = []
    for (gun, saat), atama in sorted(saatler.items()):
        onceki = saatler.get((gun, saat - 1))
        ogle_ile_ayrik = ogle_arasi_sonra is not None and saat == ogle_arasi_sonra
        if onceki == atama and not ogle_ile_ayrik:
            g, s, u, a = sonuc[-1]
            sonuc[-1] = (g, s, u + 1, a)
        else:
            sonuc.append((gun, saat, 1, atama))
    return sonuc


def program_ciktisi(oturum, program_id: uuid.UUID) -> ProgramCiktisi:
    """404: program bu okulda yok (başka okulunki de görünmez). 409: program hazır değil."""
    program = ProgramDeposu(oturum).getir(program_id)
    if program is None:
        raise KayitBulunamadi("Program")
    if program.durum != "hazir":
        raise KayitCakismasi("Program hazır değil; çıktı yalnızca hazır programdan alınır")
    okul = OkulDeposu(oturum).getir(oturumun_okulu(oturum))

    atamalar = {a.id: a for a in DersAtamaDeposu(oturum).listele()}
    siniflar = {s.id: s for s in SinifDeposu(oturum).listele()}
    dersler = {d.id: d for d in DersDeposu(oturum).listele()}
    ogretmenler = {o.id: o for o in OgretmenDeposu(oturum).listele()}
    # Silinmiş atamanın yerleşimi atlanır (çizelgedeki gibi).
    yerlesimler = [y for y in YerlesimDeposu(oturum).programin(program_id) if y.ders_atama_id in atamalar]

    sube_saatleri: dict[uuid.UUID, dict] = {s: {} for s in siniflar}
    ogretmen_saatleri: dict[uuid.UUID, dict] = {o: {} for o in ogretmenler}
    for y in yerlesimler:
        a = atamalar[y.ders_atama_id]
        sube_saatleri[a.sinif_id][(y.gun, y.saat)] = a.id
        if a.ogretmen_id in ogretmen_saatleri:
            ogretmen_saatleri[a.ogretmen_id][(y.gun, y.saat)] = a.id

    def hucreler(saatler: dict) -> list[Hucre]:
        sonuc = []
        for gun, saat, uzunluk, atama_id in _birlestir(saatler, okul.ogle_arasi_sonra):
            a = atamalar[atama_id]
            d = dersler[a.ders_id]
            o = ogretmenler.get(a.ogretmen_id) if a.ogretmen_id else None
            sonuc.append(Hucre(gun=gun, saat=saat, uzunluk=uzunluk, ders=d.ad, kisa_ad=d.kisa_ad or d.ad[:4],
                               renk=d.renk, sube=siniflar[a.sinif_id].ad, ogretmen=o.ad if o else ""))
        return sonuc

    subeler = sorted(siniflar.values(), key=lambda s: (s.seviye, tr_anahtar(s.ad)))
    # Programda dersi olmayan öğretmen çıktıya girmez (sayfası boş olurdu).
    hocalar = sorted((o for o in ogretmenler.values() if ogretmen_saatleri[o.id]), key=lambda o: tr_anahtar(o.ad))
    zil, ogle_zili = okulun_zilleri(okul)
    saat_sayisi = max([okul.gunluk_ders_saati] + [y.saat + 1 for y in yerlesimler])
    return ProgramCiktisi(
        okul=okul.ad,
        program=program.ad,
        tarih=datetime.now(TURKIYE).date(),
        hafta=Hafta(gun_adlari=GUNLER[:okul.gun_sayisi], gun_saatleri=okul.gunluk_saatler, saat_sayisi=saat_sayisi,
                    ogle_arasi_sonra=okul.ogle_arasi_sonra, zil=zil, ogle_zili=ogle_zili),
        subeler=[Cizelge(ad=s.ad, tur="sube", hucreler=hucreler(sube_saatleri[s.id]), kimlik=s.id) for s in subeler],
        ogretmenler=[Cizelge(ad=o.ad, tur="ogretmen", hucreler=hucreler(ogretmen_saatleri[o.id]), kimlik=o.id) for o in hocalar],
    )
