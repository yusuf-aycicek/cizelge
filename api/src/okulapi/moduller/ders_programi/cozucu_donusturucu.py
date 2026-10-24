"""Veritabanı -> çözücü girdisi (`cozucu.model.CozumGirdisi`). Kullanan: worker (yapım sırası 3).

Bağımlılık yönü: ders programı modülü çözücü paketine bağımlıdır, tersi değil. Çözücü
veritabanından habersiz kalır (CLAUDE.md mimari karar 3, ADR 0003). Bu dönüşüm, "worker'daki
küçük dönüşüm katmanı" diye ADR 0003'te öngörülen parçadır.

Okul, oturumun okuludur: dönüştürücü okul filtresinden geçen depoları kullanır, yani başka bir
okulun verisini okuyamaz. Kimlikler (uuid) metin olarak geçirilir.
"""

from __future__ import annotations

import uuid

from cozucu import model as cm
from cozucu.kapsam import Kapsam
from cozucu.model import temel_program
from sqlalchemy.orm import Session

from okulapi.cekirdek.depo import DersDeposu, OgretmenDeposu, OkulDeposu, SinifDeposu
from okulapi.cekirdek.kiraci import OkulBaglamiYokHatasi, oturumun_okulu
from okulapi.moduller.ders_programi.depo import DersAtamaDeposu, KisitDeposu, MusaitlikDeposu, YerlesimDeposu


def cozum_girdisi_olustur(
    oturum: Session,
    kilit_programi_id: uuid.UUID | None = None,
    temel_program_id: uuid.UUID | None = None,
) -> cm.CozumGirdisi:
    """Oturumun okulunun bütün verisinden çözücü girdisi üretir.

    - `kilit_programi_id`: o programın **kilitli** yerleşimleri `kilitli_yerlesimler` olur
      (elle düzeltmede kilitlenen hücreler, yapım sırası 7).
    - `temel_program_id`: en az değişiklikle güncellemede temel alınacak program; yerleşimleri
      (sınıf, ders, gün, saat) biçimine çevrilir (çözücü ADR 0006).
    """
    okul_id = oturumun_okulu(oturum)
    if okul_id is None:
        raise OkulBaglamiYokHatasi("Çözücü girdisi yalnızca bir okulun oturumuyla üretilebilir")
    okul = OkulDeposu(oturum).getir(okul_id)

    atamalar = [
        cm.DersAtama(id=str(a.id), sinif_id=str(a.sinif_id), ders_id=str(a.ders_id),
                     ogretmen_id=None if a.ogretmen_id is None else str(a.ogretmen_id),
                     haftalik_saat=a.haftalik_saat)
        for a in DersAtamaDeposu(oturum).listele()
    ]
    yerlesim_deposu = YerlesimDeposu(oturum)
    kilitliler = (
        [cm.Yerlesim(ders_atama_id=str(y.ders_atama_id), gun=y.gun, saat=y.saat, kilitli=True)
         for y in yerlesim_deposu.programin(kilit_programi_id, yalnizca_kilitli=True)]
        if kilit_programi_id else []
    )
    temel = (
        temel_program(atamalar, [cm.Yerlesim(ders_atama_id=str(y.ders_atama_id), gun=y.gun, saat=y.saat)
                                 for y in yerlesim_deposu.programin(temel_program_id)])
        if temel_program_id else []
    )
    return cm.CozumGirdisi(
        ayar=cm.OkulAyari(gun_sayisi=okul.gun_sayisi, gunluk_ders_saati=okul.gunluk_ders_saati,
                          gun_saatleri=tuple(okul.gun_saatleri or ()), ogle_arasi_sonra=okul.ogle_arasi_sonra),
        ogretmenler=[cm.Ogretmen(id=str(o.id), ad=o.ad, brans=o.brans) for o in OgretmenDeposu(oturum).listele()],
        siniflar=[cm.Sinif(id=str(s.id), ad=s.ad, seviye=s.seviye,
                           sube_grubu_id=None if s.sube_grubu_id is None else str(s.sube_grubu_id))
                  for s in SinifDeposu(oturum).listele()],
        dersler=[cm.Ders(id=str(d.id), ad=d.ad, kisa_ad=d.kisa_ad) for d in DersDeposu(oturum).listele()],
        atamalar=atamalar,
        musaitlikler=[
            cm.Musaitlik(ogretmen_id=str(m.ogretmen_id), gun=m.gun, saat=m.saat, durum=cm.MusaitlikDurumu(m.durum))
            for m in MusaitlikDeposu(oturum).listele()
        ],
        kisitlar=[cm.KisitTanimi(tur=k.tur, parametreler=dict(k.parametreler), zorunlu=k.zorunlu, agirlik=k.agirlik,
                                 kapsam=_kapsam(k))
                  for k in KisitDeposu(oturum).listele()],
        kilitli_yerlesimler=kilitliler,
        temel_yerlesimler=temel,
    )


def _kapsam(k) -> Kapsam:
    def metin(deger: uuid.UUID | None) -> str | None:
        return None if deger is None else str(deger)

    return Kapsam(ders_id=metin(k.ders_id), sinif_id=metin(k.sinif_id), sube_grubu_id=metin(k.sube_grubu_id),
                  ogretmen_id=metin(k.ogretmen_id))
