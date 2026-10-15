"""İş kuyruğu: arka planda çalışacak işler (ADR 0011).

Uygulama kodu yalnızca `IsKuyrugu` arayüzünü bilir. İki gerçekleme vardır:
- `RqKuyrugu`: Redis + RQ (üretim). RQ'yu içe aktaran tek yer bu dosyadır; bunu bir mimari testi
  denetler (test_kuyruk.py).
- `BellekKuyrugu`: testler için; işleri bir sözlükte tutar, hiçbir şey çalıştırmaz.

Çekirdek hangi işlerin olduğunu bilmez: iş fonksiyonu ve başarısızlık fonksiyonu, Python yolu
("paket.modul.fonksiyon") olarak verilir. Worker bu yolu içe aktarıp çalıştırır.

İşin kimliği çağıranın verdiği kimliktir (ders programında program kimliği). Böylece "bu programın
işi kuyrukta mı" sorusu, ayrı bir eşleme tablosu tutmadan sorulabilir.
"""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

gunluk = logging.getLogger(__name__)


class KuyrukHatasi(Exception):
    """Kuyruğa ulaşılamadı (Redis kapalı, ağ hatası...)."""


class IsKuyrugu(ABC):
    @abstractmethod
    def kuyruga_ekle(
        self,
        is_id: str,
        fonksiyon: str,
        argumanlar: dict[str, Any],
        zaman_asimi_sn: int,
        basarisizlikta: str | None = None,
    ) -> None:
        """İşi kuyruğa koyar. Ulaşılamazsa `KuyrukHatasi`.

        `basarisizlikta`: iş istisnayla ya da zaman aşımıyla biterse çağrılacak fonksiyonun yolu.
        Çağrı biçimi: `f(**argumanlar, zaman_asimi=<bool>)`. Kuyruk teknolojisinden bağımsızdır.
        """

    @abstractmethod
    def kuyrukta_mi(self, is_id: str) -> bool:
        """İş hâlâ kuyrukta mı: sırada bekliyor, çalışıyor ya da yeniden denenecek.

        Bitmiş, başarısız olmuş, iptal edilmiş ya da hiç bilinmeyen iş için False.
        Ulaşılamazsa `KuyrukHatasi` (çağıran "bilmiyorum" durumunda karar vermemeli).
        """


def _fonksiyon(yol: str):
    modul, ad = yol.rsplit(".", 1)
    return getattr(importlib.import_module(modul), ad)


# --- RQ -------------------------------------------------------------------------------------

# RQ iş durumları -> "kuyrukta mı". created: henüz kuyruğa girmemiş; deferred: bağımlılık bekliyor;
# scheduled: ileri bir zamana ya da yeniden denemeye ertelenmiş.
_KUYRUKTA_SAYILAN = {"queued", "started", "deferred", "scheduled", "created"}


def _rq_basarisizlik(job, connection, type, value, traceback) -> None:  # noqa: A002 (RQ'nun imzası)
    """RQ'nun on_failure geri çağrısı. RQ'ya özgü imzayı kuyruktan bağımsız çağrıya çevirir."""
    from rq.timeouts import JobTimeoutException

    yol = job.meta.get("basarisizlikta")
    if yol:
        _fonksiyon(yol)(**job.kwargs, zaman_asimi=isinstance(value, JobTimeoutException))


class RqKuyrugu(IsKuyrugu):
    """Redis + RQ. Bağlantı ilk kullanımda kurulur; uygulama Redis'siz de açılabilir."""

    def __init__(self, redis_url: str, kuyruk_adi: str, baglanti=None, baglanti_zaman_asimi_sn: float = 2.0):
        self.redis_url, self.kuyruk_adi = redis_url, kuyruk_adi
        self._baglanti = baglanti
        self._zaman_asimi = baglanti_zaman_asimi_sn

    def _redis(self):
        if self._baglanti is None:
            from redis import Redis

            # Zaman aşımı: Redis kapalıysa istek uzun süre asılı kalmasın, hızla 503'e dönsün.
            self._baglanti = Redis.from_url(self.redis_url, socket_connect_timeout=self._zaman_asimi,
                                            socket_timeout=self._zaman_asimi)
        return self._baglanti

    def kuyruga_ekle(self, is_id, fonksiyon, argumanlar, zaman_asimi_sn, basarisizlikta=None) -> None:
        from redis.exceptions import RedisError
        from rq import Callback, Queue

        try:
            Queue(self.kuyruk_adi, connection=self._redis()).enqueue(
                fonksiyon,
                kwargs=argumanlar,
                job_id=is_id,
                job_timeout=zaman_asimi_sn,
                meta={"basarisizlikta": basarisizlikta},
                on_failure=Callback(_rq_basarisizlik) if basarisizlikta else None,
            )
        except RedisError as hata:
            raise KuyrukHatasi(str(hata)) from hata

    def kuyrukta_mi(self, is_id: str) -> bool:
        from redis.exceptions import RedisError
        from rq.exceptions import NoSuchJobError
        from rq.job import Job

        try:
            durum = Job.fetch(is_id, connection=self._redis()).get_status()
        except NoSuchJobError:
            return False
        except RedisError as hata:
            raise KuyrukHatasi(str(hata)) from hata
        return durum is not None and getattr(durum, "value", durum) in _KUYRUKTA_SAYILAN


def rq_worker_calistir(redis_url: str, kuyruk_adi: str) -> None:
    """Kuyruktaki işleri çalıştıran RQ worker'ı (bloklar). `/worker` paketi bunu çağırır.

    RQ'nun varsayılan worker'ı her iş için `fork` ile bir alt süreç açar: bir işin çökmesi ya da
    belleği şişirmesi worker'ı etkilemez; süre sınırı aşılırsa alt süreç öldürülür. `fork`
    yalnızca Linux/macOS'ta var: worker konteynerde çalışır.
    """
    from redis import Redis
    from rq import Queue, Worker

    baglanti = Redis.from_url(redis_url)
    Worker([Queue(kuyruk_adi, connection=baglanti)], connection=baglanti).work(with_scheduler=False)


# --- testler için ----------------------------------------------------------------------------

@dataclass
class KayitliIs:
    fonksiyon: str
    argumanlar: dict[str, Any]
    zaman_asimi_sn: int
    basarisizlikta: str | None
    kuyrukta: bool = True


@dataclass
class BellekKuyrugu(IsKuyrugu):
    """Bellek içi kuyruk. Testler işleri inceler, bitirir ya da "kaybeder".

    `ulasilamaz = True` iken her çağrı `KuyrukHatasi` fırlatır (Redis kapalıymış gibi).
    """

    isler: dict[str, KayitliIs] = field(default_factory=dict)
    ulasilamaz: bool = False

    def _denetle(self) -> None:
        if self.ulasilamaz:
            raise KuyrukHatasi("Bellek kuyruğu: ulaşılamaz (test)")

    def kuyruga_ekle(self, is_id, fonksiyon, argumanlar, zaman_asimi_sn, basarisizlikta=None) -> None:
        self._denetle()
        self.isler[is_id] = KayitliIs(fonksiyon, dict(argumanlar), zaman_asimi_sn, basarisizlikta)

    def kuyrukta_mi(self, is_id: str) -> bool:
        self._denetle()
        return is_id in self.isler and self.isler[is_id].kuyrukta

    def bitir(self, is_id: str) -> None:
        """İş çalışıp bitmiş gibi: kayıt kalır ama artık kuyrukta değildir."""
        self.isler[is_id].kuyrukta = False

    def kaybet(self, is_id: str) -> None:
        """İş kaydı hiç yokmuş gibi (Redis verisi silindi, kuyruğa hiç girmedi)."""
        del self.isler[is_id]
