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

    yukle.okullar = okullar
    yield fabrika, yukle
    with sahip_motor.begin() as baglanti:  # tablo sahibi: RLS'yi atlar
        for tablo in reversed(Base.metadata.sorted_tables):
            if "okul_id" not in tablo.c and tablo.name != "okul":
                continue  # okula ait olmayan tablolar (ör. giris_denemesi)
            sutun = tablo.c.okul_id if "okul_id" in tablo.c else tablo.c.id
            baglanti.execute(delete(tablo).where(sutun.in_(okullar)))


def kalici_okullar_ekle(kalici, okul_id) -> None:
    """`kalici` düzeneğine, kendisinin oluşturmadığı bir okulu da sildirir."""
    kalici[1].okullar.append(okul_id)


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
    assert (program.durum, program.baslama, program.bitis is not None) == ("basarisiz", None, True)  # hiç başlamadı
    assert uretimi_basarisiz_yap(oturum_fabrikasi, okul_id, program_id, "ikinci kez") is False
    assert program_oku(oturum_fabrikasi, okul_id, program_id)[0].hata_mesaji == "kuyruğa ulaşılamadı"


# --- takılı üretim temizliği ---------------------------------------------------------------

def bos_okul(fabrika, ad: str) -> uuid.UUID:
    with okulsuz_oturum(fabrika) as oturum:
        return OkulServisi(oturum).olustur({"ad": ad}).id


def temizle(fabrika, okul_id, kuyruk=None) -> int:
    with okul_oturumu(fabrika, okul_id) as o:
        sayi = takili_uretimleri_temizle(o, kuyruk)
        o.commit()
        return sayi


def test_takili_uretim_temizligi_yalnizca_suresi_gecmisleri_ve_kendi_okulunu_etkiler(oturum_fabrikasi):
    # Okul başına en fazla bir etkin üretim olabildiği için her durum ayrı bir okulda.
    simdi = datetime.now(timezone.utc)
    sinir = timedelta(seconds=is_suresi_siniri_sn(SURE))  # 2 × 30 + 120 = 180 sn
    assert sinir == timedelta(seconds=180)
    durumlar = {
        # ad: (sure_siniri_sn, ne zaman başladı, temizlenmeli mi)
        "takili": (SURE, simdi - sinir - timedelta(minutes=10), True),
        "suruyor": (SURE, simdi - timedelta(seconds=10), False),
        # 1 saattir sürüyor ama sınırı 2 × 3600 + 120 sn: takılı değil
        "uzun": (3600, simdi - timedelta(hours=1), False),
    }
    programlar = {}
    for ad, (sure, baslama, _) in durumlar.items():
        okul_id = bos_okul(oturum_fabrikasi, ad)
        programlar[ad] = (okul_id, program_ekle(oturum_fabrikasi, okul_id, durum="uretiliyor",
                                                sure_siniri_sn=sure, baslama=baslama))
    b_okul, b_takili = programlar["takili"]

    # Başka bir okulun oturumuyla temizlik: "takili" okulunun programına dokunmaz (okul filtresi).
    assert temizle(oturum_fabrikasi, programlar["suruyor"][0]) == 0
    assert program_oku(oturum_fabrikasi, b_okul, b_takili)[0].durum == "uretiliyor"

    for ad, (okul_id, program_id) in programlar.items():
        temizle(oturum_fabrikasi, okul_id)
        program, _ = program_oku(oturum_fabrikasi, okul_id, program_id)
        if durumlar[ad][2]:
            assert (program.durum, program.hata_mesaji, program.bitis is not None) == ("basarisiz", YARIDA_KALDI, True)
        else:
            assert program.durum == "uretiliyor", ad


def test_temizlik_veritabani_saatini_kullanir(oturum_fabrikasi):
    # baslama = now() - (sınır - 5 sn): henüz takılı değil; now() - (sınır + 5 sn): takılı.
    sinir = func.make_interval(0, 0, 0, 0, 0, 0, is_suresi_siniri_sn(SURE))
    bes = func.make_interval(0, 0, 0, 0, 0, 0, 5)
    for ad, baslama, beklenen in (("az", func.now() - sinir + bes, "uretiliyor"),
                                  ("cok", func.now() - sinir - bes, "basarisiz")):
        okul_id = bos_okul(oturum_fabrikasi, ad)
        with okul_oturumu(oturum_fabrikasi, okul_id) as o:
            program = Program(ad=ad, sure_siniri_sn=SURE, durum="uretiliyor")
            program.baslama = baslama
            o.add(program)
            o.flush()
            takili_uretimleri_temizle(o, None)
            o.commit()
            o.refresh(program)
            assert program.durum == beklenen, ad


# --- öksüz "bekliyor" program: kuyruğa sorulur, süreye bakılmaz -------------------------------

@pytest.mark.parametrize(
    ("kuyruk_durumu", "temizlenir"),
    [
        ("kuyrukta", False),      # sırada ya da çalışıyor: gerçekten bekliyor
        ("hic_yok", True),        # iş kaydı yok: kuyruğa hiç girmedi ya da kayboldu
        ("bitti", True),          # iş bitti ama program hâlâ bekliyor: öksüz
        ("ulasilamaz", False),    # kuyruğa sorulamıyor: "bilmiyorum" ile iptal edilmez
        ("kuyruk_verilmedi", False),
    ],
)
def test_bekleyen_program_isi_kuyrukta_yoksa_temizlenir(oturum_fabrikasi, kuyruk_durumu, temizlenir):
    from okulapi.cekirdek.kuyruk import BellekKuyrugu
    from okulapi.moduller.ders_programi.uretim import OKSUZ

    okul_id = bos_okul(oturum_fabrikasi, "Bekleyen Lisesi")
    # Çok eski bir program: süreye dayalı bir kural olsaydı kesinlikle temizlenirdi.
    program_id = program_ekle(oturum_fabrikasi, okul_id)
    kuyruk = BellekKuyrugu()
    if kuyruk_durumu in ("kuyrukta", "bitti", "ulasilamaz"):
        kuyruk.kuyruga_ekle(str(program_id), "is", {}, 60)
    if kuyruk_durumu == "bitti":
        kuyruk.bitir(str(program_id))
    kuyruk.ulasilamaz = kuyruk_durumu == "ulasilamaz"

    sayi = temizle(oturum_fabrikasi, okul_id, None if kuyruk_durumu == "kuyruk_verilmedi" else kuyruk)

    program, _ = program_oku(oturum_fabrikasi, okul_id, program_id)
    if temizlenir:
        assert (sayi, program.durum, program.hata_mesaji) == (1, "basarisiz", OKSUZ)
        assert program.baslama is None and program.bitis is not None
    else:
        assert (sayi, program.durum) == (0, "bekliyor")


def test_worker_baslatirken_kilitledigi_bekleyen_programa_temizlik_dokunmaz(kalici):
    """SKIP LOCKED: worker satırı kilitlemişse (başlatma işleminin ortası) temizlik onu atlar ve
    beklemez. Burada iş kuyrukta görünmüyor; kilit olmasa öksüz sayılırdı."""
    from okulapi.cekirdek.kuyruk import BellekKuyrugu

    fabrika, _ = kalici
    okul_id = bos_okul(fabrika, "Kilit Lisesi")
    kalici_okullar_ekle(kalici, okul_id)
    program_id = program_ekle(fabrika, okul_id)

    with okul_oturumu(fabrika, okul_id) as worker:
        worker.scalars(select(Program).where(Program.id == program_id).with_for_update()).one()
        baslangic = time.monotonic()
        assert temizle(fabrika, okul_id, BellekKuyrugu()) == 0  # ayrı bağlantı
        assert time.monotonic() - baslangic < 2  # kilidi beklemedi
        worker.rollback()
    assert temizle(fabrika, okul_id, BellekKuyrugu()) == 1  # kilit kalkınca öksüz olarak görülür


# --- worker işi commit'ten önce alırsa ------------------------------------------------------

def test_program_henuz_commit_edilmemisse_worker_kisa_sure_yeniden_arar(kalici):
    """API önce kuyruğa ekler, sonra commit eder (ADR 0011 madde 4). Worker programı ilk denemede
    bulamazsa bekleyip yeniden arar."""
    fabrika, yukle = kalici
    okul_id, _ = yukle()
    program_id = uuid.uuid4()
    api = okul_oturumu(fabrika, okul_id)
    api.add(Program(id=program_id, ad="Geç commit", sure_siniri_sn=SURE))
    api.flush()  # satır eklendi ama commit edilmedi: başka bağlantılar görmez
    zamanlayici = threading.Timer(0.3, lambda: (api.commit(), api.close()))
    zamanlayici.start()
    try:
        sonuc = programi_uret(fabrika, okul_id, program_id, SahteCozucu(), bulunamazsa_bekle=(0.1, 0.2, 0.5, 1.0))
    finally:
        zamanlayici.join()
    assert sonuc is UretimSonucu.HAZIR


def test_program_hic_gelmezse_worker_vazgecer(oturum_fabrikasi, mini):
    okul_id, _ = mini
    cozucu = SahteCozucu()
    baslangic = time.monotonic()
    assert programi_uret(oturum_fabrikasi, okul_id, uuid.uuid4(), cozucu, bulunamazsa_bekle=(0.05, 0.05)) \
        is UretimSonucu.ATLANDI
    assert cozucu.cagri_sayisi == 0 and time.monotonic() - baslangic >= 0.1


def test_temizlenen_program_icin_gec_gelen_is_bir_sey_yapmaz(oturum_fabrikasi, mini):
    okul_id, _ = mini
    eski = datetime.now(timezone.utc) - timedelta(hours=1)
    program_id = program_ekle(oturum_fabrikasi, okul_id, durum="uretiliyor", baslama=eski)
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        takili_uretimleri_temizle(o, None)
        o.commit()
    assert programi_uret(oturum_fabrikasi, okul_id, program_id, SahteCozucu()) is UretimSonucu.ATLANDI
