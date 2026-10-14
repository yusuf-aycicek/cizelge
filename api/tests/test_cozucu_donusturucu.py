"""Dönüştürücü: veritabanı -> CozumGirdisi. Gidiş-dönüş testi mini set ile.

1. Mini set API üzerinden bir okula yüklenir.
2. Dönüştürücü bu okuldan `CozumGirdisi` üretir.
3. Orijinal mini setle karşılaştırılır. Kimlikler değişir (veritabanı uuid üretir), bu yüzden iki
   taraf da doğal anahtarlara (öğretmen adı, sınıf adı, "9-A Matematik" ...) çevrilip öyle
   karşılaştırılır.
4. Çözücü bu girdiyle çalıştırılır ve bağımsız doğrulayıcıdan geçer.
"""

from __future__ import annotations

import uuid

import pytest
from cozucu import CpSatCozucu, dogrula, olc, temel_program
from cozucu.veri_io import girdi_oku

from conftest import MINI
from okulapi.cekirdek.kiraci import OkulBaglamiYokHatasi, okul_oturumu, okulsuz_oturum
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.modeller import Program, Yerlesim


def dogal(girdi) -> dict:
    """Kimliklerden bağımsız, sıralı bir karşılaştırma biçimi."""
    o = {x.id: x.ad for x in girdi.ogretmenler}
    s = {x.id: x.ad for x in girdi.siniflar}
    d = {x.id: x.ad for x in girdi.dersler}
    a = {x.id: (s[x.sinif_id], d[x.ders_id]) for x in girdi.atamalar}
    return {
        "ayar": girdi.ayar,
        "ogretmenler": sorted((x.ad, x.brans) for x in girdi.ogretmenler),
        "siniflar": sorted((x.ad, x.seviye) for x in girdi.siniflar),
        "dersler": sorted((x.ad, x.kisa_ad) for x in girdi.dersler),
        "atamalar": sorted((*a[x.id], o.get(x.ogretmen_id), x.haftalik_saat) for x in girdi.atamalar),
        "musaitlikler": sorted((o[x.ogretmen_id], x.gun, x.saat, x.durum.value) for x in girdi.musaitlikler),
        "kisitlar": sorted((x.tur, sorted(x.parametreler.items()), x.zorunlu, x.agirlik) for x in girdi.kisitlar),
        "kilitli": sorted((*a[x.ders_atama_id], x.gun, x.saat, x.kilitli) for x in girdi.kilitli_yerlesimler),
        "temel": sorted((s[t.sinif_id], d[t.ders_id], t.gun, t.saat) for t in girdi.temel_yerlesimler),
    }


def kilitli_program_ekle(oturum_fabrikasi, okul_id, harita, mini) -> uuid.UUID:
    """Kilitli hücreleri olan bir program (API'si yapım sırası 7'de; burada doğrudan eklenir)."""
    with okul_oturumu(oturum_fabrikasi, okul_id) as oturum:
        program = Program(ad="Kilitler")
        oturum.add(program)
        oturum.flush()
        for k in mini.kilitli_yerlesimler:
            oturum.add(Yerlesim(program_id=program.id, ders_atama_id=uuid.UUID(harita[k.ders_atama_id]),
                                gun=k.gun, saat=k.saat, kilitli=True))
        oturum.commit()
        return program.id


def test_mini_set_gidis_donus_ve_cozum(mini_yukle, oturum_fabrikasi):
    okul_id, harita = mini_yukle()
    okul_id = uuid.UUID(okul_id)
    mini = girdi_oku(MINI)
    kilit_programi = kilitli_program_ekle(oturum_fabrikasi, okul_id, harita, mini)

    with okul_oturumu(oturum_fabrikasi, okul_id) as oturum:
        girdi = cozum_girdisi_olustur(oturum, kilit_programi_id=kilit_programi)

    assert dogal(girdi) == dogal(mini)

    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=60)
    assert sonuc.basarili, sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    assert olc(girdi, sonuc.yerlesimler).sinif_boslugu == 0

    # Ters yönün önizlemesi (asıl kodu worker adımında): çözümü bir programa yaz, sonra o programı
    # temel alan girdi üret. Temel yerleşimler çözümün kendisi olmalı.
    with okul_oturumu(oturum_fabrikasi, okul_id) as oturum:
        program = Program(ad="Çözüm", durum="hazir")
        oturum.add(program)
        oturum.flush()
        oturum.add_all([Yerlesim(program_id=program.id, ders_atama_id=uuid.UUID(y.ders_atama_id),
                                 gun=y.gun, saat=y.saat, kilitli=y.kilitli) for y in sonuc.yerlesimler])
        oturum.commit()
        guncelleme_girdisi = cozum_girdisi_olustur(oturum, temel_program_id=program.id)
    beklenen = temel_program(girdi.atamalar, sonuc.yerlesimler)
    assert sorted(guncelleme_girdisi.temel_yerlesimler, key=str) == sorted(beklenen, key=str)


def test_donusturucu_yalnizca_oturumun_okulunu_okur(mini_yukle, okul_olustur, oturum_fabrikasi):
    mini_yukle()
    bos_okul = uuid.UUID(okul_olustur("Boş Okul"))
    with okul_oturumu(oturum_fabrikasi, bos_okul) as oturum:
        girdi = cozum_girdisi_olustur(oturum)
    assert girdi.ogretmenler == [] and girdi.atamalar == [] and girdi.musaitlikler == []
    with okulsuz_oturum(oturum_fabrikasi) as oturum, pytest.raises(OkulBaglamiYokHatasi):
        cozum_girdisi_olustur(oturum)
