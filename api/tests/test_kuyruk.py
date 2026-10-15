"""İş kuyruğu (cekirdek/kuyruk.py): arayüz, RQ gerçeklemesi, bellek içi gerçekleme.

RQ gerçeklemesi burada fakeredis ile (bellek içinde çalışan sahte Redis) sınanır: işin kimliği,
"kuyrukta mı" sorusunun RQ iş durumlarına karşılığı, Redis'e ulaşılamaması. Gerçek Redis ve
gerçek worker ile uçtan uca akışı kabul testi sınar (4. alt adım).
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import fakeredis
import pytest
from rq.job import Job, JobStatus
from rq.timeouts import JobTimeoutException

from okulapi.cekirdek.kuyruk import BellekKuyrugu, IsKuyrugu, KuyrukHatasi, RqKuyrugu, _rq_basarisizlik

KAYNAK = Path(__file__).resolve().parents[1] / "src" / "okulapi"


@pytest.fixture
def redis():
    return fakeredis.FakeStrictRedis()


@pytest.fixture
def rq_kuyrugu(redis):
    return RqKuyrugu("redis://kullanilmaz", "deneme", baglanti=redis)


def test_rq_isin_kimligi_verilen_kimliktir_ve_ayarlar_iste_saklanir(rq_kuyrugu, redis):
    rq_kuyrugu.kuyruga_ekle("program-123", "os.getcwd", {"okul_id": "o1", "program_id": "p1"}, 360,
                            basarisizlikta="paket.modul.geri_cagri")
    is_ = Job.fetch("program-123", connection=redis)
    assert is_.func_name == "os.getcwd"
    assert is_.kwargs == {"okul_id": "o1", "program_id": "p1"}
    assert is_.timeout == 360
    assert is_.meta["basarisizlikta"] == "paket.modul.geri_cagri"
    assert is_.origin == "deneme"
    assert is_.failure_callback is not None


@pytest.mark.parametrize(
    ("durum", "kuyrukta"),
    [
        (JobStatus.QUEUED, True),
        (JobStatus.STARTED, True),
        (JobStatus.DEFERRED, True),
        (JobStatus.SCHEDULED, True),
        (JobStatus.FINISHED, False),
        (JobStatus.FAILED, False),
        (JobStatus.STOPPED, False),
        (JobStatus.CANCELED, False),
    ],
)
def test_rq_kuyrukta_mi_is_durumuna_gore(rq_kuyrugu, redis, durum, kuyrukta):
    rq_kuyrugu.kuyruga_ekle("is-1", "os.getcwd", {}, 60)
    is_ = Job.fetch("is-1", connection=redis)
    is_.set_status(durum)
    assert rq_kuyrugu.kuyrukta_mi("is-1") is kuyrukta


def test_rq_bilinmeyen_is_kuyrukta_degildir(rq_kuyrugu):
    assert rq_kuyrugu.kuyrukta_mi("hic-eklenmemis") is False


def test_rq_is_kaydi_silinirse_kuyrukta_degildir(rq_kuyrugu, redis):
    rq_kuyrugu.kuyruga_ekle("is-2", "os.getcwd", {}, 60)
    redis.flushall()  # Redis verisi kayboldu (ör. kalıcı olmayan Redis yeniden başladı)
    assert rq_kuyrugu.kuyrukta_mi("is-2") is False


def test_rq_redis_ulasilamazsa_kuyruk_hatasi():
    # Kapalı bir port: bağlantı zaman aşımı kısa tutulur (bu makinede kapalı porta bağlanma hemen
    # reddedilmiyor, zaman aşımına kadar bekliyor).
    kuyruk = RqKuyrugu("redis://127.0.0.1:1/0", "deneme", baglanti_zaman_asimi_sn=0.5)
    with pytest.raises(KuyrukHatasi):
        kuyruk.kuyruga_ekle("is-3", "os.getcwd", {}, 60)
    with pytest.raises(KuyrukHatasi):
        kuyruk.kuyrukta_mi("is-3")


# --- başarısızlık geri çağrısı: RQ'ya özgü imza -> kuyruktan bağımsız çağrı ----------------

CAGRILAR: list[dict] = []


def kaydeden_geri_cagri(**argumanlar) -> None:
    CAGRILAR.append(argumanlar)


@pytest.mark.parametrize(("hata", "zaman_asimi"), [(RuntimeError("çöktü"), False), (JobTimeoutException("süre"), True)])
def test_rq_basarisizlik_geri_cagrisi_argumanlari_ve_zaman_asimini_iletir(hata, zaman_asimi):
    CAGRILAR.clear()
    is_ = SimpleNamespace(meta={"basarisizlikta": f"{__name__}.kaydeden_geri_cagri"},
                          kwargs={"okul_id": "o1", "program_id": "p1"})
    _rq_basarisizlik(is_, None, type(hata), hata, None)
    assert CAGRILAR == [{"okul_id": "o1", "program_id": "p1", "zaman_asimi": zaman_asimi}]


def test_rq_basarisizlik_geri_cagrisi_tanimsizsa_bir_sey_yapmaz():
    CAGRILAR.clear()
    _rq_basarisizlik(SimpleNamespace(meta={}, kwargs={}), None, RuntimeError, RuntimeError(), None)
    assert CAGRILAR == []


# --- bellek içi kuyruk: testlerin kullandığı ikiz aynı sözleşmeye uyar -----------------------

def test_bellek_kuyrugu_sozlesmesi():
    kuyruk: IsKuyrugu = BellekKuyrugu()
    assert kuyruk.kuyrukta_mi("x") is False
    kuyruk.kuyruga_ekle("x", "paket.is", {"a": "1"}, 60, "paket.geri")
    assert kuyruk.kuyrukta_mi("x") is True
    assert kuyruk.isler["x"].argumanlar == {"a": "1"}
    kuyruk.bitir("x")
    assert kuyruk.kuyrukta_mi("x") is False
    kuyruk.kuyruga_ekle("y", "paket.is", {}, 60)
    kuyruk.kaybet("y")
    assert kuyruk.kuyrukta_mi("y") is False
    kuyruk.ulasilamaz = True
    with pytest.raises(KuyrukHatasi):
        kuyruk.kuyrukta_mi("x")
    with pytest.raises(KuyrukHatasi):
        kuyruk.kuyruga_ekle("z", "paket.is", {}, 60)


# --- mimari: RQ ve Redis yalnızca kuyruk gerçeklemesinde ------------------------------------

def test_rq_ve_redis_yalnizca_kuyruk_gercekleme_dosyasinda_kullanilir():
    """Uygulama kodu yalnızca `IsKuyrugu` arayüzünü bilir. Kuyruk teknolojisi değişirse (ör.
    PostgreSQL tabanlı bir kuyruk, ADR 0011) yalnızca cekirdek/kuyruk.py değişir."""
    izinli = KAYNAK / "cekirdek" / "kuyruk.py"
    ihlaller = []
    for dosya in KAYNAK.rglob("*.py"):
        if dosya == izinli:
            continue
        for dugum in ast.walk(ast.parse(dosya.read_text(encoding="utf-8"))):
            adlar = []
            if isinstance(dugum, ast.Import):
                adlar = [a.name for a in dugum.names]
            elif isinstance(dugum, ast.ImportFrom) and dugum.module:
                adlar = [dugum.module]
            ihlaller += [f"{dosya.relative_to(KAYNAK)}:{dugum.lineno} {ad}" for ad in adlar
                         if ad.split(".")[0] in ("rq", "redis")]
    assert ihlaller == []
