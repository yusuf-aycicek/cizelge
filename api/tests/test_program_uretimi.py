"""Program üretme isteği: POST /programlar, durum izleme, okul başına tek etkin üretim, takılı
üretim temizliği, kuyruğa ulaşılamaması (ADR 0011).

Kuyruk bellek içidir (`kuyruk` fikstürü); worker'ı test kendisi oynar: kuyruğa konan işin
argümanlarıyla `programi_uret`'i çağırır. Gerçek Redis + RQ + worker: kabul testi (4. alt adım).
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.cekirdek.kuyruk import BellekKuyrugu
from okulapi.cekirdek.servisler import KayitCakismasi
from okulapi.moduller.ders_programi.modeller import Program
from okulapi.moduller.ders_programi.servisler import ETKIN_URETIM_VAR, KUYRUGA_ULASILAMADI, ProgramServisi
from okulapi.moduller.ders_programi.uretim import (
    OKSUZ,
    URETIM_BASARISIZ,
    URETIM_ISI,
    YARIDA_KALDI,
    UretimSonucu,
    is_suresi_siniri_sn,
    programi_uret,
)
from test_uretim import SahteCozucu, bos_okul, kalici  # noqa: F401  (kalici: fikstür)

SURE = 30


@pytest.fixture
def okul(mini_yukle):
    okul_id, harita = mini_yukle()
    return {"id": uuid.UUID(okul_id), "baslik": okul_basligi(okul_id), "harita": harita}


def uret(istemci, okul, **govde):
    return istemci.post(f"{DP}/programlar", json={"ad": "Güz", "sure_siniri_sn": SURE, **govde},
                        headers=okul["baslik"])


def getir(istemci, okul, program_id):
    yanit = istemci.get(f"{DP}/programlar/{program_id}", headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def worker_calistir(oturum_fabrikasi, kuyruk, program_id, cozucu=None):
    """Worker'ı oynar: kuyruktaki işi argümanlarıyla çalıştırır, sonra işi bitmiş sayar."""
    is_ = kuyruk.isler[str(program_id)]
    assert is_.fonksiyon == URETIM_ISI
    sonuc = programi_uret(oturum_fabrikasi, is_.argumanlar["okul_id"], is_.argumanlar["program_id"],
                          cozucu or SahteCozucu())
    kuyruk.bitir(str(program_id))
    return sonuc


def program_ekle(oturum_fabrikasi, okul_id, **alanlar) -> uuid.UUID:
    with okul_oturumu(oturum_fabrikasi, okul_id) as o:
        program = Program(ad=alanlar.pop("ad", "Eski"), sure_siniri_sn=alanlar.pop("sure_siniri_sn", SURE), **alanlar)
        o.add(program)
        o.commit()
        return program.id


# --- akış: istek -> bekliyor -> uretiliyor -> hazir ----------------------------------------

def test_uretim_istegi_kabul_edilir_ve_is_kuyruga_konur(istemci, okul, kuyruk):
    yanit = uret(istemci, okul, ad="Güz dönemi")

    assert yanit.status_code == 202, yanit.text
    program = yanit.json()
    assert (program["ad"], program["durum"], program["sure_siniri_sn"]) == ("Güz dönemi", "bekliyor", SURE)
    assert program["baslama"] is None and program["cozum_durumu"] is None
    assert yanit.headers["Location"] == f"{DP}/programlar/{program['id']}"

    is_ = kuyruk.isler[program["id"]]  # işin kimliği = program kimliği
    assert is_.fonksiyon == URETIM_ISI and is_.basarisizlikta == URETIM_BASARISIZ
    assert is_.argumanlar == {"okul_id": str(okul["id"]), "program_id": program["id"]}
    assert is_.zaman_asimi_sn == is_suresi_siniri_sn(SURE) == 2 * SURE + 120


def test_durum_bekliyor_uretiliyor_hazir_olarak_izlenir(istemci, okul, kuyruk, oturum_fabrikasi):
    """CLAUDE.md yapım sırası 3 kabulünün Redis'siz hali: arayüzün yaptığı gibi GET ile durum
    sorulur. Çözüm sırasında yapılan sorgu `uretiliyor` görür."""
    program_id = uret(istemci, okul).json()["id"]
    gorulen = [getir(istemci, okul, program_id)["durum"]]
    cozucu = SahteCozucu(sirasinda=lambda _g: gorulen.append(getir(istemci, okul, program_id)["durum"]))

    assert worker_calistir(oturum_fabrikasi, kuyruk, program_id, cozucu) is UretimSonucu.HAZIR
    son = getir(istemci, okul, program_id)
    gorulen.append(son["durum"])

    assert gorulen == ["bekliyor", "uretiliyor", "hazir"]
    assert son["cozum_durumu"] in ("optimal", "uygun") and son["olcumler"]["sinif_boslugu"] == 0
    yerlesimler = istemci.get(f"{DP}/programlar/{program_id}/yerlesimler", headers=okul["baslik"]).json()
    assert len(yerlesimler) == 71


def test_temel_programla_uretim(istemci, okul, kuyruk, oturum_fabrikasi):
    p1 = uret(istemci, okul, ad="Eylül").json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, p1)

    yanit = uret(istemci, okul, ad="Ekim", temel_program_id=p1)
    assert yanit.status_code == 202 and yanit.json()["temel_program_id"] == p1
    worker_calistir(oturum_fabrikasi, kuyruk, yanit.json()["id"])
    assert getir(istemci, okul, yanit.json()["id"])["olcumler"]["degisen_yerlesim"] == 0  # veri aynı


def test_temel_program_hazir_ve_bu_okulun_olmali(istemci, okul, kuyruk, oturum_fabrikasi, okul_olustur):
    # Hazır olmayan program temel alınamaz.
    basarisiz = program_ekle(oturum_fabrikasi, okul["id"], durum="basarisiz", bitis=datetime.now(timezone.utc))
    yanit = uret(istemci, okul, temel_program_id=str(basarisiz))
    assert yanit.status_code == 422 and "hazır" in yanit.json()["detail"]
    # Başka okulun programı: bulunamaz (var olduğu bile sızmaz).
    b = {"id": uuid.UUID(okul_olustur("B Lisesi")), "baslik": None}
    b["baslik"] = okul_basligi(b["id"])
    b_program = program_ekle(oturum_fabrikasi, b["id"], durum="basarisiz", bitis=datetime.now(timezone.utc))
    assert uret(istemci, okul, temel_program_id=str(b_program)).status_code == 404
    assert kuyruk.isler == {}  # hiçbir iş kuyruğa konmadı


@pytest.mark.parametrize("govde", [{"ad": ""}, {"sure_siniri_sn": 0}, {"sure_siniri_sn": 100000}])
def test_gecersiz_istek_422(istemci, okul, kuyruk, govde):
    assert uret(istemci, okul, **govde).status_code == 422
    assert kuyruk.isler == {}


# --- okul başına tek etkin üretim ---------------------------------------------------------

def test_devam_eden_uretim_varken_yeni_istek_409(istemci, okul, kuyruk, oturum_fabrikasi):
    ilk = uret(istemci, okul).json()["id"]
    yanit = uret(istemci, okul)
    assert yanit.status_code == 409 and yanit.json()["detail"] == ETKIN_URETIM_VAR
    assert list(kuyruk.isler) == [ilk]

    worker_calistir(oturum_fabrikasi, kuyruk, ilk)
    assert uret(istemci, okul).status_code == 202  # bitince yeni üretim yapılabilir


def test_baska_okulun_uretimi_engellemez(istemci, okul, kuyruk, okul_olustur):
    b_id = okul_olustur("B Lisesi")
    assert uret(istemci, okul).status_code == 202
    assert istemci.post(f"{DP}/programlar", json={"ad": "B", "sure_siniri_sn": SURE},
                        headers=okul_basligi(b_id)).status_code == 202


def test_ayni_anda_iki_istek_veritabani_duzeyinde_tek_uretim(kalici):  # noqa: F811
    """İki istek "etkin üretim var mı" denetimini birlikte geçebilir: biri programını eklemiş ama
    henüz commit etmemişken öteki onu göremez. Kısmi benzersiz indeks ikinciyi durdurur."""
    fabrika, _ = kalici
    okul_id = bos_okul(fabrika, "Eşzamanlı Lisesi")
    kalici[1].okullar.append(okul_id)

    class YavasKuyruk(BellekKuyrugu):
        cagri = 0

        def kuyruga_ekle(self, *a, **k):
            YavasKuyruk.cagri += 1
            time.sleep(0.5)  # ilk istek kuyruğa eklerken (commit'ten önce) ikincisi gelsin
            super().kuyruga_ekle(*a, **k)

    kuyruk = YavasKuyruk()
    sonuclar = []

    def istek():
        with okul_oturumu(fabrika, okul_id) as o:
            try:
                sonuclar.append(ProgramServisi(o, kuyruk).uret("Güz", None, SURE).durum)
            except KayitCakismasi as hata:
                sonuclar.append(str(hata))

    ilk = threading.Thread(target=istek)
    ilk.start()
    time.sleep(0.15)  # ilk istek INSERT'i yaptı, kuyruğa ekliyor
    ikinci = threading.Thread(target=istek)
    ikinci.start()
    ilk.join(10)
    ikinci.join(10)

    assert sorted(sonuclar) == sorted(["bekliyor", ETKIN_URETIM_VAR])
    # İkinci istek benzersizlik ihlalini kuyruğa eklemeden ÖNCE almalı (program satırı kuyruktan
    # önce flush edilir). Yoksa 409 alan her istek kuyrukta öksüz bir iş bırakırdı.
    assert YavasKuyruk.cagri == 1 and len(kuyruk.isler) == 1


# --- takılı üretim yeni üretimi engellemez -------------------------------------------------

def test_suresi_gecmis_uretiliyor_varken_yeni_istek_kabul_edilir(istemci, okul, kuyruk, oturum_fabrikasi):
    """Worker çöktü, program `uretiliyor`da kaldı ve iş süresi sınırı geçti. Yeni istek 409 değil
    202 almalı; takılı program `basarisiz` olur (kullanıcı düzeltmesi, ADR 0011 madde 8)."""
    eski = datetime.now(timezone.utc) - timedelta(seconds=is_suresi_siniri_sn(SURE) + 60)
    takili = program_ekle(oturum_fabrikasi, okul["id"], durum="uretiliyor", baslama=eski)
    kuyruk.kuyruga_ekle(str(takili), URETIM_ISI, {}, 60)  # RQ'da "started" kalmış iş gibi

    yanit = uret(istemci, okul)

    assert yanit.status_code == 202, yanit.text
    eski_program = getir(istemci, okul, takili)
    assert (eski_program["durum"], eski_program["hata_mesaji"]) == ("basarisiz", YARIDA_KALDI)


def test_suresi_gecmemis_uretiliyor_varken_yeni_istek_409(istemci, okul, kuyruk, oturum_fabrikasi):
    yeni = datetime.now(timezone.utc) - timedelta(seconds=10)
    suren = program_ekle(oturum_fabrikasi, okul["id"], durum="uretiliyor", baslama=yeni)
    kuyruk.kuyruga_ekle(str(suren), URETIM_ISI, {}, 60)

    assert uret(istemci, okul).status_code == 409
    assert getir(istemci, okul, suren)["durum"] == "uretiliyor"


@pytest.mark.parametrize("is_durumu", ["hic_yok", "bitti"])
def test_kuyrukta_isi_olmayan_bekleyen_program_temizlenir_ve_yeni_istek_kabul_edilir(
        istemci, okul, kuyruk, oturum_fabrikasi, is_durumu):
    """Öksüz program: `bekliyor` ama işi kuyrukta yok. Süreye bakılmaz; az önce oluşturulmuş olsa
    bile kuyrukta işi yoksa temizlenir."""
    oksuz = program_ekle(oturum_fabrikasi, okul["id"])
    if is_durumu == "bitti":
        kuyruk.kuyruga_ekle(str(oksuz), URETIM_ISI, {}, 60)
        kuyruk.bitir(str(oksuz))

    yanit = uret(istemci, okul)

    assert yanit.status_code == 202, yanit.text
    eski = getir(istemci, okul, oksuz)
    assert (eski["durum"], eski["hata_mesaji"], eski["baslama"]) == ("basarisiz", OKSUZ, None)


def test_kuyrukta_bekleyen_program_temizlenmez_ve_yeni_istek_409(istemci, okul, kuyruk, oturum_fabrikasi):
    """Gerçekten sırada bekleyen program: ne kadar eski olursa olsun dokunulmaz."""
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        program = Program(ad="Sırada", sure_siniri_sn=SURE)
        program.olusturma = datetime.now(timezone.utc) - timedelta(days=2)
        o.add(program)
        o.commit()
        bekleyen = program.id
    kuyruk.kuyruga_ekle(str(bekleyen), URETIM_ISI, {}, 60)

    assert uret(istemci, okul).status_code == 409
    assert getir(istemci, okul, bekleyen)["durum"] == "bekliyor"


def test_okunurken_de_oksuz_program_temizlenir(istemci, okul, kuyruk, oturum_fabrikasi):
    oksuz = program_ekle(oturum_fabrikasi, okul["id"])
    liste = istemci.get(f"{DP}/programlar", headers=okul["baslik"]).json()
    assert [(p["id"], p["durum"]) for p in liste] == [(str(oksuz), "basarisiz")]


def test_kuyruga_ulasilamazken_bekleyen_program_iptal_edilmez(istemci, okul, kuyruk, oturum_fabrikasi):
    bekleyen = program_ekle(oturum_fabrikasi, okul["id"])
    kuyruk.ulasilamaz = True
    assert getir(istemci, okul, bekleyen)["durum"] == "bekliyor"  # "bilmiyorum" ile iptal yok


# --- kuyruğa ulaşılamaz -------------------------------------------------------------------

def test_kuyruga_eklenemezse_program_basarisiz_ve_503(istemci, okul, kuyruk):
    kuyruk.ulasilamaz = True

    yanit = uret(istemci, okul, ad="Kuyruksuz")

    assert yanit.status_code == 503 and yanit.json()["detail"] == KUYRUGA_ULASILAMADI
    kuyruk.ulasilamaz = False
    programlar = istemci.get(f"{DP}/programlar", headers=okul["baslik"]).json()
    assert [(p["ad"], p["durum"], p["hata_mesaji"]) for p in programlar] == \
        [("Kuyruksuz", "basarisiz", KUYRUGA_ULASILAMADI)]
    assert programlar[0]["bitis"] is not None and programlar[0]["baslama"] is None
    # Başarısız istek okulu engellemez: kuyruk geri gelince yeni istek kabul edilir.
    assert uret(istemci, okul).status_code == 202


def test_kuyruga_eklenirken_yapilan_temizlik_yeni_programi_oksuz_saymaz(kalici):  # noqa: F811
    """Sıra "önce kuyruk, sonra commit" olduğu için: iş kuyruğa eklenirken başka bir istek
    (ör. arayüzün durum sorgusu) temizlik yaparsa yeni program ona görünmez. Sıra ters olsaydı
    (commit, sonra kuyruk) program bu anda "bekliyor ama işi kuyrukta yok" görünür ve haksız yere
    öksüz sayılırdı."""
    fabrika, _ = kalici
    okul_id = bos_okul(fabrika, "Sıra Lisesi")
    kalici[1].okullar.append(okul_id)

    class AraTemizlikliKuyruk(BellekKuyrugu):
        def kuyruga_ekle(self, *a, **k):
            with okul_oturumu(fabrika, okul_id) as baska_istek:  # ayrı bağlantı
                ProgramServisi(baska_istek, self).listele()
            super().kuyruga_ekle(*a, **k)

    with okul_oturumu(fabrika, okul_id) as o:
        program_id = ProgramServisi(o, AraTemizlikliKuyruk()).uret("Güz", None, SURE).id
    with okul_oturumu(fabrika, okul_id) as o:
        assert o.get(Program, program_id).durum == "bekliyor"


def test_commit_basarisiz_olursa_kuyrukta_kalan_is_sessizce_biter(kalici, monkeypatch):  # noqa: F811
    """Kuyruğa ekleme başarılı, commit başarısız: kuyrukta var olmayan bir programın işi kalır.
    Worker onu alınca programı bulamaz ve sessizce bitmelidir: istisna yok, yeniden deneme yok,
    RQ'nun başarısız işler kaydında birikme yok.

    İş gerçek RQ koduyla çalıştırılır: fakeredis üzerinde bir RQ worker'ı (SimpleWorker: iş için
    fork etmez; Windows'ta sinyal yerine zamanlayıcıyla süre sınırı)."""
    import fakeredis
    from rq import Queue, SimpleWorker
    from rq.job import Job, JobStatus
    from rq.registry import FailedJobRegistry
    from rq.timeouts import TimerDeathPenalty

    from conftest import TEST_UYGULAMA_URL
    from okulapi.cekirdek.isci import isci_fabrikasi
    from okulapi.cekirdek.kuyruk import RqKuyrugu

    fabrika, _ = kalici
    okul_id = bos_okul(fabrika, "Commit Lisesi")
    kalici[1].okullar.append(okul_id)
    redis = fakeredis.FakeStrictRedis()
    kuyruk = RqKuyrugu("redis://kullanilmaz", "program_uretimi", baglanti=redis)

    # 1) İstek: iş kuyruğa girer, sonra commit başarısız olur (ör. veritabanı bağlantısı koptu).
    oturum = okul_oturumu(fabrika, okul_id)

    def bozuk_commit():
        raise RuntimeError("commit sırasında bağlantı koptu")

    monkeypatch.setattr(oturum, "commit", bozuk_commit)
    with pytest.raises(RuntimeError, match="bağlantı koptu"):
        ProgramServisi(oturum, kuyruk).uret("Güz", None, SURE)
    oturum.close()  # commit edilmemiş program geri alınır

    is_ = Queue("program_uretimi", connection=redis).jobs[0]
    program_id = uuid.UUID(is_.id)
    assert kuyruk.kuyrukta_mi(is_.id)
    with okul_oturumu(fabrika, okul_id) as o:
        assert o.get(Program, program_id) is None  # program yok, işi var

    # 2) Worker işi alır. İş fonksiyonu worker sürecinin fabrikasını kullanır: test veritabanı.
    monkeypatch.setenv("OKULAPI_VERITABANI_URL", TEST_UYGULAMA_URL)
    isci_fabrikasi.cache_clear()
    try:
        class Worker(SimpleWorker):
            death_penalty_class = TimerDeathPenalty

        baslangic = time.monotonic()
        Worker([Queue("program_uretimi", connection=redis)], connection=redis).work(burst=True)
        gecen = time.monotonic() - baslangic
    finally:
        isci_fabrikasi().kw["bind"].dispose()
        isci_fabrikasi.cache_clear()

    is_ = Job.fetch(str(program_id), connection=redis)
    assert is_.get_status() == JobStatus.FINISHED  # başarısız değil
    assert is_.return_value() == UretimSonucu.ATLANDI.value
    assert len(FailedJobRegistry("program_uretimi", connection=redis)) == 0
    assert not kuyruk.kuyrukta_mi(str(program_id))
    assert 3 < gecen < 30  # programı kısa süre yeniden aradı (~4 sn), sonra vazgeçti
    with okul_oturumu(fabrika, okul_id) as o:
        assert o.get(Program, program_id) is None  # worker program oluşturmadı


def test_on_kontrol_ucu_ozel_ayari_da_denetler(istemci, okul, okul_olustur):
    """Uç, üretimdeki ön kontrolü çalıştırır (özel ayarlar dahil); başka okulun verisini görmez."""
    b, h = okul["baslik"], okul["harita"]
    yanit = istemci.get(f"{DP}/on-kontrol", headers=b)
    assert yanit.status_code == 200 and yanit.json() == {"celiskiler": [], "uyarilar": []}
    istemci.put(f"{DP}/kurallar/gunluk_ders_siniri/ozel",
                json={"kapsam": {"ders_id": h["d-mat"], "sinif_id": h["s-9a"]}, "parametreler": {"n": 1}}, headers=b)
    celiskiler = istemci.get(f"{DP}/on-kontrol", headers=b).json()["celiskiler"]
    assert [c["tur"] for c in celiskiler] == ["ders_gun_kapasitesi"]
    assert "9-A Matematik haftada 6 saat" in celiskiler[0]["mesaj"]
    baska = okul_basligi(okul_olustur("Başka Lise"))
    assert istemci.get(f"{DP}/on-kontrol", headers=baska).json() == {"celiskiler": [], "uyarilar": []}
    assert istemci.get(f"{DP}/on-kontrol").status_code == 401
