"""Program üretimi (worker'ın iş fonksiyonu): uretim.programi_uret ve yardımcıları.

Kuyruk ve RQ bu testlerde yok: iş fonksiyonu doğrudan çağrılır (kuyruk 3. alt adımda, gerçek RQ
uçtan uca kabul testinde). Çoğu test sahte bir çözücü kullanır: `ProgramCozucu` arayüzü (ADR 0001)
sayesinde "çözüm sürerken veri değişsin" ya da "çözücü bozuk bir program dönsün" gibi durumlar
kurulabilir.

İki tür test düzeneği var:
- `oturum_fabrikasi`: test başına geri alınan tek bağlantı (hızlı, iz bırakmaz);
- `kalici`: gerçekten commit edilen veri, ayrı bağlantılar. "Başka bir bağlantı `uretiliyor`u
  görüyor mu" ve "iki worker aynı anda" soruları ancak böyle sınanabilir. Veri test sonunda tablo
  sahibi rolüyle silinir.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from cozucu import CozumDurumu, CozumSonucu, CpSatCozucu, ProgramCozucu, dogrula, olc
from sqlalchemy import delete, func, select

from conftest import MINI
from okulapi.cekirdek.kiraci import okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.modeller import Ders, Ogretmen, Sinif
from okulapi.cekirdek.servisler import OkulServisi
from okulapi.cekirdek.veritabani import Base, oturum_fabrikasi as fabrika_olustur
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.modeller import DersAtama, Kisit, Musaitlik, Program, Yerlesim
from okulapi.moduller.ders_programi.uretim import (
    BEKLENMEYEN_HATA,
    DOGRULAMA_HATASI,
    VERI_DEGISTI,
    YARIDA_KALDI,
    UretimSonucu,
    girdi_ozeti,
    is_suresi_siniri_sn,
    programi_uret,
    takili_uretimleri_temizle,
    uretimi_basarisiz_yap,
)

SURE = 30  # gerçek çözücüyle mini set 1 sn'nin altında çözülür; sınır yalnızca güvenlik payı


# --- yardımcılar ----------------------------------------------------------------------------

def mini_yukle(fabrika, ad: str = "Mini Lisesi") -> tuple[uuid.UUID, dict[str, uuid.UUID]]:
    """veri/mini.json'u ORM ile yeni bir okula yükler. (okul_id, mini kimliği -> uuid) döner."""
    with open(MINI, encoding="utf-8") as f:
        mini = json.load(f)
    with okulsuz_oturum(fabrika) as oturum:
        okul_id = OkulServisi(oturum).olustur({"ad": ad, **mini["ayar"]}).id
    harita: dict[str, uuid.UUID] = {}
    with okul_oturumu(fabrika, okul_id) as o:
        for kayitlar, olustur in (
            (mini["ogretmenler"], lambda x: Ogretmen(ad=x["ad"], brans=x["brans"])),
            (mini["siniflar"], lambda x: Sinif(ad=x["ad"], seviye=x["seviye"])),
            (mini["dersler"], lambda x: Ders(ad=x["ad"], kisa_ad=x["kisa_ad"])),
        ):
            for x in kayitlar:
                nesne = olustur(x)
                o.add(nesne)
                o.flush()
                harita[x["id"]] = nesne.id
        for a in mini["atamalar"]:
            atama = DersAtama(sinif_id=harita[a["sinif_id"]], ders_id=harita[a["ders_id"]],
                              ogretmen_id=harita[a["ogretmen_id"]], haftalik_saat=a["haftalik_saat"])
            o.add(atama)
            o.flush()
            harita[a["id"]] = atama.id
        o.add_all([Musaitlik(**{**m, "ogretmen_id": harita[m["ogretmen_id"]]}) for m in mini["musaitlikler"]])
        o.add_all([Kisit(**k) for k in mini["kisitlar"]])
        o.commit()
    return okul_id, harita


def program_ekle(fabrika, okul_id, **alanlar) -> uuid.UUID:
    with okul_oturumu(fabrika, okul_id) as o:
        program = Program(ad=alanlar.pop("ad", "Güz"), sure_siniri_sn=alanlar.pop("sure_siniri_sn", SURE), **alanlar)
        o.add(program)
        o.commit()
        return program.id


def program_oku(fabrika, okul_id, program_id) -> tuple[Program, list[Yerlesim]]:
    with okul_oturumu(fabrika, okul_id) as o:
        program = o.get(Program, program_id)
        yerlesimler = list(o.scalars(select(Yerlesim).where(Yerlesim.program_id == program_id)))
        o.expunge_all()
        return program, yerlesimler


def girdi_al(fabrika, okul_id, temel_program_id=None):
    with okul_oturumu(fabrika, okul_id) as o:
        return cozum_girdisi_olustur(o, kilit_programi_id=temel_program_id, temel_program_id=temel_program_id)


class SahteCozucu(ProgramCozucu):
    """Gerçek çözücüyü sarar; çözüm sırasında bir şey yapabilir ya da sonucu değiştirebilir."""

    def __init__(self, sirasinda=None, sonuc=None, bekle_sn: float = 0.0):
        self.sirasinda, self.sonuc, self.bekle_sn = sirasinda, sonuc, bekle_sn
        self.cagri_sayisi = 0

    def coz(self, girdi, sure_siniri_sn=120):
        self.cagri_sayisi += 1
        if self.sirasinda:
            self.sirasinda(girdi)
        time.sleep(self.bekle_sn)
        if self.sonuc is not None:
            return self.sonuc(girdi)
        return CpSatCozucu().coz(girdi, sure_siniri_sn)


@pytest.fixture
def mini(oturum_fabrikasi):
    return mini_yukle(oturum_fabrikasi)


@pytest.fixture
def kalici(motor, sahip_motor):
    """Gerçekten commit eden fabrika; oluşturulan okullar test sonunda silinir."""
    fabrika = fabrika_olustur(motor)
    okullar: list[uuid.UUID] = []

    def yukle(ad: str = "Kalıcı Mini Lisesi"):
        okul_id, harita = mini_yukle(fabrika, ad)
        okullar.append(okul_id)
        return okul_id, harita

    yield fabrika, yukle
    with sahip_motor.begin() as baglanti:  # tablo sahibi: RLS'yi atlar
        for tablo in reversed(Base.metadata.sorted_tables):
            sutun = tablo.c.okul_id if "okul_id" in tablo.c else tablo.c.id
            baglanti.execute(delete(tablo).where(sutun.in_(okullar)))


# --- 1. uçtan uca (gerçek çözücü) -----------------------------------------------------------

def test_mini_set_uretilir_ve_dogrulayicidan_gecer(oturum_fabrikasi, mini):
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)

    assert programi_uret(oturum_fabrikasi, okul_id, program_id) is UretimSonucu.HAZIR

    program, yerlesimler = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert program.durum == "hazir" and program.cozum_durumu in ("optimal", "uygun")
    assert program.baslama is not None and program.bitis is not None and program.bitis >= program.baslama
    assert program.hata_mesaji is None and program.celiskiler == []
    assert len(yerlesimler) == 71  # mini setin toplam ders saati
    girdi = girdi_al(oturum_fabrikasi, okul_id)
    from cozucu import Yerlesim as CY
    cozum = [CY(str(y.ders_atama_id), y.gun, y.saat, y.kilitli) for y in yerlesimler]
    assert dogrula(girdi, cozum) == []
    assert program.olcumler == olc(girdi, cozum).__dict__
    assert program.olcumler["sinif_boslugu"] == 0
    assert program.girdi_ozeti == girdi_ozeti(girdi) and len(program.girdi_ozeti) == 64
    assert {y.okul_id for y in yerlesimler} == {okul_id}


# --- 2. durum geçişi başka bir bağlantıdan görünür --------------------------------------------

def test_cozum_sirasinda_baska_baglanti_uretiliyor_gorur(kalici):
    fabrika, yukle = kalici
    okul_id, _ = yukle()
    program_id = program_ekle(fabrika, okul_id)
    gorulen = []

    def gozle(_girdi):
        # Ayrı bir oturum = havuzdan ayrı bir bağlantı (worker'ın bağlantısı bu sırada kapalı).
        with okul_oturumu(fabrika, okul_id) as o:
            p = o.get(Program, program_id)
            gorulen.append((p.durum, p.baslama is not None))

    assert programi_uret(fabrika, okul_id, program_id, SahteCozucu(sirasinda=gozle)) is UretimSonucu.HAZIR
    assert gorulen == [("uretiliyor", True)]
    assert program_oku(fabrika, okul_id, program_id)[0].durum == "hazir"


# --- 3. idempotency ------------------------------------------------------------------------

def test_ayni_is_iki_kez_calisirsa_ikincisi_bir_sey_yapmaz(oturum_fabrikasi, mini):
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)
    cozucu = SahteCozucu()
    assert programi_uret(oturum_fabrikasi, okul_id, program_id, cozucu) is UretimSonucu.HAZIR
    once, yerlesimler = program_oku(oturum_fabrikasi, okul_id, program_id)

    assert programi_uret(oturum_fabrikasi, okul_id, program_id, cozucu) is UretimSonucu.ATLANDI
    sonra, yerlesimler2 = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert cozucu.cagri_sayisi == 1  # ikinci iş çözücüyü hiç çağırmadı
    assert (sonra.durum, sonra.bitis) == (once.durum, once.bitis)
    assert len(yerlesimler2) == len(yerlesimler) == 71


def test_iki_worker_ayni_anda_alirsa_program_bir_kez_uretilir(kalici):
    """FOR UPDATE: ikinci worker birincinin kilidini bekler, sonra `uretiliyor` görüp çıkar."""
    fabrika, yukle = kalici
    okul_id, _ = yukle()
    program_id = program_ekle(fabrika, okul_id)
    cozucu = SahteCozucu(bekle_sn=1.0)
    sonuclar: list[UretimSonucu] = []
    engel = threading.Barrier(2)

    def worker():
        engel.wait()  # iki iş parçacığı aynı anda başlasın
        sonuclar.append(programi_uret(fabrika, okul_id, program_id, cozucu))

    is_parcaciklari = [threading.Thread(target=worker) for _ in range(2)]
    for t in is_parcaciklari:
        t.start()
    for t in is_parcaciklari:
        t.join(timeout=60)

    assert sorted(sonuclar) == sorted([UretimSonucu.HAZIR, UretimSonucu.ATLANDI])
    assert cozucu.cagri_sayisi == 1
    assert len(program_oku(fabrika, okul_id, program_id)[1]) == 71


# --- 4. çözüm sırasında veri değişir -------------------------------------------------------

@pytest.mark.parametrize("degisiklik", ["atama_silinir", "saat_degisir", "musaitlik_eklenir"])
def test_cozum_sirasinda_veri_degisirse_eski_program_yazilmaz(oturum_fabrikasi, mini, degisiklik):
    okul_id, harita = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)

    def degistir(_girdi):
        with okul_oturumu(oturum_fabrikasi, okul_id) as o:
            atama = o.get(DersAtama, harita["a-9a-mat"])
            if degisiklik == "atama_silinir":
                o.delete(atama)
            elif degisiklik == "saat_degisir":
                atama.haftalik_saat = 5
            else:
                o.add(Musaitlik(ogretmen_id=harita["o-ali"], gun=2, saat=3, durum="tercih_etmez"))
            o.commit()

    sonuc = programi_uret(oturum_fabrikasi, okul_id, program_id, SahteCozucu(sirasinda=degistir))

    assert sonuc is UretimSonucu.BASARISIZ
    program, yerlesimler = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert (program.durum, program.hata_mesaji, yerlesimler) == ("basarisiz", VERI_DEGISTI, [])
    assert program.bitis is not None


def test_veri_degismezse_ozet_ayni_kalir(oturum_fabrikasi, mini):
    # Özet kanonik: aynı veri her okumada aynı özeti verir (satır sırası önemsiz).
    okul_id, _ = mini
    a, b = girdi_al(oturum_fabrikasi, okul_id), girdi_al(oturum_fabrikasi, okul_id)
    b.atamalar.reverse()
    b.musaitlikler.reverse()
    assert girdi_ozeti(a) == girdi_ozeti(b)
    b.atamalar[0] = replace(b.atamalar[0], haftalik_saat=b.atamalar[0].haftalik_saat + 1)
    assert girdi_ozeti(a) != girdi_ozeti(b)


# --- 5. çözümsüz girdi ----------------------------------------------------------------------

def test_cozumsuz_girdide_celiskiler_ve_okunur_mesaj_yazilir(oturum_fabrikasi, mini):
    okul_id, harita = mini
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        # Ayşe salı-cuma da gelemez: haftada 0 müsait saat, 9-A ve 9-B'de 6'şar saat dersi var.
        o.add_all([Musaitlik(ogretmen_id=harita["o-ayse"], gun=g, saat=s, durum="gelemez")
                   for g in range(1, 5) for s in range(6)])
        o.commit()
    program_id = program_ekle(oturum_fabrikasi, okul_id)

    assert programi_uret(oturum_fabrikasi, okul_id, program_id) is UretimSonucu.BASARISIZ

    program, yerlesimler = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert program.durum == "basarisiz" and yerlesimler == []
    assert program.cozum_durumu == "on_kontrol_hatasi"
    assert program.celiskiler and all({"tur", "mesaj", "ilgili"} <= c.keys() for c in program.celiskiler)
    assert "Ayşe Yılmaz" in program.hata_mesaji  # kimlik değil ad
    assert str(harita["o-ayse"]) in {i for c in program.celiskiler for i in c["ilgili"]}


def test_sure_yetmezse_basarisiz_ve_mesaj(oturum_fabrikasi, mini):
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)
    bilinmiyor = SahteCozucu(sonuc=lambda g: CozumSonucu(durum=CozumDurumu.BILINMIYOR, mesajlar=["Süre doldu."]))

    assert programi_uret(oturum_fabrikasi, okul_id, program_id, bilinmiyor) is UretimSonucu.BASARISIZ
    program, _ = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert (program.cozum_durumu, program.hata_mesaji) == ("bilinmiyor", "Süre doldu.")


# --- 6. okul izolasyonu ---------------------------------------------------------------------

def test_baska_okulun_programi_uretilemez(oturum_fabrikasi, mini):
    okul_a, _ = mini
    okul_b, _ = mini_yukle(oturum_fabrikasi, "B Lisesi")
    program_a = program_ekle(oturum_fabrikasi, okul_a)
    cozucu = SahteCozucu()

    # İş B okulunun oturumuyla A'nın programı için çalışırsa program bulunamaz (ORM filtresi + RLS).
    assert programi_uret(oturum_fabrikasi, okul_b, program_a, cozucu) is UretimSonucu.ATLANDI
    assert cozucu.cagri_sayisi == 0
    program, yerlesimler = program_oku(oturum_fabrikasi, okul_a, program_a)
    assert (program.durum, yerlesimler) == ("bekliyor", [])


# --- 7. temel programla güncelleme (en az değişiklik, kilitli hücreler) ---------------------

def test_temel_programla_guncelleme_kilitleri_korur_ve_az_degistirir(oturum_fabrikasi, mini):
    okul_id, harita = mini
    p1 = program_ekle(oturum_fabrikasi, okul_id, ad="Eylül")
    assert programi_uret(oturum_fabrikasi, okul_id, p1) is UretimSonucu.HAZIR

    # Yönetici 9-A Matematik'in bir hücresini kilitler (elle düzeltme, yapım sırası 7) ve Mehmet
    # artık pazartesi gelemez.
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        kilit = o.scalars(select(Yerlesim).where(Yerlesim.program_id == p1,
                                                 Yerlesim.ders_atama_id == harita["a-9a-mat"])).first()
        kilit.kilitli = True
        kilit_hucre = (kilit.ders_atama_id, kilit.gun, kilit.saat)
        o.add_all([Musaitlik(ogretmen_id=harita["o-mehmet"], gun=0, saat=s, durum="gelemez") for s in range(6)])
        o.commit()
    _, eski = program_oku(oturum_fabrikasi, okul_id, p1)

    p2 = program_ekle(oturum_fabrikasi, okul_id, ad="Eylül (güncelleme)", temel_program_id=p1)
    assert programi_uret(oturum_fabrikasi, okul_id, p2) is UretimSonucu.HAZIR

    program, yeni = program_oku(oturum_fabrikasi, okul_id, p2)
    assert program.temel_program_id == p1
    assert (kilit_hucre, True) in {((y.ders_atama_id, y.gun, y.saat), y.kilitli) for y in yeni}
    mehmet_pazartesi = sum(1 for y in eski if y.gun == 0 and y.ders_atama_id in
                           {harita[a] for a in ("a-9a-tde", "a-9b-tde", "a-10a-tde")})
    degisen = program.olcumler["degisen_yerlesim"]
    assert mehmet_pazartesi <= degisen <= mehmet_pazartesi + 6, (mehmet_pazartesi, degisen)
    assert len(yeni) == 71
    _, eski_sonra = program_oku(oturum_fabrikasi, okul_id, p1)
    assert len(eski_sonra) == 71  # temel program olduğu gibi kalır


# --- savunma: beklenmeyen durumlar ----------------------------------------------------------

def test_cozucu_istisna_firlatirsa_program_basarisiz_olur(oturum_fabrikasi, mini):
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)

    def patla(_girdi):
        raise RuntimeError("çözücü çöktü")

    with pytest.raises(RuntimeError, match="çözücü çöktü"):
        programi_uret(oturum_fabrikasi, okul_id, program_id, SahteCozucu(sirasinda=patla))
    program, _ = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert (program.durum, program.hata_mesaji) == ("basarisiz", BEKLENMEYEN_HATA)


def test_dogrulamadan_gecmeyen_cozum_yazilmaz(oturum_fabrikasi, mini):
    # Çözücü "optimal" der ama yerleşimlerin yarısı eksik: bağımsız doğrulayıcı yakalar.
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)

    def eksik(girdi):
        dogru = CpSatCozucu().coz(girdi, SURE)
        return CozumSonucu(durum=CozumDurumu.OPTIMAL, yerlesimler=dogru.yerlesimler[::2], toplam_ceza=0)

    assert programi_uret(oturum_fabrikasi, okul_id, program_id, SahteCozucu(sonuc=eksik)) is UretimSonucu.BASARISIZ
    program, yerlesimler = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert (program.durum, program.hata_mesaji, yerlesimler) == ("basarisiz", DOGRULAMA_HATASI, [])


def test_cozum_sirasinda_program_temizlenmisse_sonuc_yazilmaz(oturum_fabrikasi, mini):
    # Çözüm iş süresi sınırını aştı, bu arada takılı sayılıp başarısız yapıldı: geç gelen sonuç
    # o programı yeniden "hazir" yapmamalı.
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)

    def temizlendi(_girdi):
        uretimi_basarisiz_yap(oturum_fabrikasi, okul_id, program_id, YARIDA_KALDI)

    sonuc = programi_uret(oturum_fabrikasi, okul_id, program_id, SahteCozucu(sirasinda=temizlendi))
    assert sonuc is UretimSonucu.ATLANDI
    program, yerlesimler = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert (program.durum, program.hata_mesaji, yerlesimler) == ("basarisiz", YARIDA_KALDI, [])


def test_basarisiz_yap_bitmis_programa_dokunmaz(oturum_fabrikasi, mini):
    okul_id, _ = mini
    program_id = program_ekle(oturum_fabrikasi, okul_id)
    assert uretimi_basarisiz_yap(oturum_fabrikasi, okul_id, program_id, "kuyruğa ulaşılamadı") is True
    program, _ = program_oku(oturum_fabrikasi, okul_id, program_id)
    assert (program.durum, program.baslama is not None) == ("basarisiz", True)  # CHECK kısıtları sağlandı
    assert uretimi_basarisiz_yap(oturum_fabrikasi, okul_id, program_id, "ikinci kez") is False
    assert program_oku(oturum_fabrikasi, okul_id, program_id)[0].hata_mesaji == "kuyruğa ulaşılamadı"


# --- takılı üretim temizliği ---------------------------------------------------------------

def test_takili_uretim_temizligi_yalnizca_suresi_gecmisleri_ve_kendi_okulunu_etkiler(oturum_fabrikasi, mini):
    okul_a, _ = mini
    okul_b, _ = mini_yukle(oturum_fabrikasi, "B Lisesi")
    simdi = datetime.now(timezone.utc)
    sinir = timedelta(seconds=is_suresi_siniri_sn(SURE))  # 2 × 30 + 120 = 180 sn
    assert sinir == timedelta(seconds=180)

    takili = program_ekle(oturum_fabrikasi, okul_a, ad="Takılı", durum="uretiliyor", baslama=simdi - sinir - timedelta(minutes=10))
    program_ekle(oturum_fabrikasi, okul_a, ad="Sürüyor", durum="uretiliyor", baslama=simdi - timedelta(seconds=10))
    # Uzun süre sınırı olan program: 1 saattir sürüyor ama sınırı 2 × 3600 + 120 sn.
    program_ekle(oturum_fabrikasi, okul_a, ad="Uzun", durum="uretiliyor", sure_siniri_sn=3600,
                        baslama=simdi - timedelta(hours=1))
    program_ekle(oturum_fabrikasi, okul_a, ad="Bekleyen")
    b_takili = program_ekle(oturum_fabrikasi, okul_b, ad="B takılı", durum="uretiliyor", baslama=simdi - timedelta(hours=2))

    with okul_oturumu(oturum_fabrikasi, okul_a) as o:
        assert takili_uretimleri_temizle(o) == 1
        o.commit()
        durumlar = dict(o.execute(select(Program.ad, Program.durum)).all())
        t = o.get(Program, takili)
        assert (t.hata_mesaji, t.bitis is not None) == (YARIDA_KALDI, True)
    assert durumlar == {"Takılı": "basarisiz", "Sürüyor": "uretiliyor", "Uzun": "uretiliyor", "Bekleyen": "bekliyor"}
    assert program_oku(oturum_fabrikasi, okul_b, b_takili)[0].durum == "uretiliyor"  # A'nın oturumu B'ye dokunmaz


def test_temizlenen_program_icin_gec_gelen_is_bir_sey_yapmaz(oturum_fabrikasi, mini):
    okul_id, _ = mini
    eski = datetime.now(timezone.utc) - timedelta(hours=1)
    program_id = program_ekle(oturum_fabrikasi, okul_id, durum="uretiliyor", baslama=eski)
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        takili_uretimleri_temizle(o)
        o.commit()
    assert programi_uret(oturum_fabrikasi, okul_id, program_id, SahteCozucu()) is UretimSonucu.ATLANDI


def test_temizlik_veritabani_saatini_kullanir(oturum_fabrikasi, mini):
    # baslama = now() - (sınır - 5 sn): henüz takılı değil; now() - (sınır + 5 sn): takılı.
    okul_id, _ = mini
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        sinir = func.make_interval(0, 0, 0, 0, 0, 0, is_suresi_siniri_sn(SURE))
        az = Program(ad="az", sure_siniri_sn=SURE, durum="uretiliyor")
        az.baslama = func.now() - sinir + func.make_interval(0, 0, 0, 0, 0, 0, 5)
        cok = Program(ad="çok", sure_siniri_sn=SURE, durum="uretiliyor")
        cok.baslama = func.now() - sinir - func.make_interval(0, 0, 0, 0, 0, 0, 5)
        o.add_all([az, cok])
        o.flush()
        assert takili_uretimleri_temizle(o) == 1
        o.commit()
        assert dict(o.execute(select(Program.ad, Program.durum)).all()) == {"az": "uretiliyor", "çok": "basarisiz"}
