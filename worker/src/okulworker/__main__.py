"""Çalıştırma: python -m okulworker

Ayarlar API ile aynıdır (ortam değişkenleri, önek OKULAPI_): veritabanı adresi, Redis adresi,
kuyruk adı, etkin modüller.
"""

from __future__ import annotations

import logging

from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.kuyruk import rq_worker_calistir
from okulapi.cekirdek.modul import modulleri_yukle


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ayarlar = Ayarlar()
    # Modüller açılışta bir kez yüklenir: yanlış bir modül adı ilk işte değil, hemen fark edilsin.
    moduller = modulleri_yukle(ayarlar.etkin_moduller)
    logging.getLogger("okulworker").info("Kuyruk %s, modüller %s", ayarlar.kuyruk_adi, [m.ad for m in moduller])
    rq_worker_calistir(ayarlar.redis_url, ayarlar.kuyruk_adi)


if __name__ == "__main__":
    main()
