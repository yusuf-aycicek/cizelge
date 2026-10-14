"""Alembic yapılandırması: sürüm klasörleri etkin modül listesinden toplanır (bkz. docs/adr/0010).

Nasıl çalışır:
- Her modülün (ve çekirdeğin) kendi `migrations/` klasörü ve kendi Alembic **dalı** vardır.
  Dalın ilk revizyonu `branch_labels=("<modül adı>",)` taşır.
- Bir modül dalının ilk revizyonu `depends_on = "cekirdek_0001"` der. Alembic bu revizyonu
  uygulamadan önce çekirdeğin o revizyonunu uygular. Sıra böyle garanti edilir. Modül sonradan
  çekirdeğin daha yeni bir tablosuna ihtiyaç duyarsa, o migration'ı da `depends_on` ile o çekirdek
  revizyonuna bağlar.
- `alembic_version` tablosu birbirini kapsamayan uç revizyonları tutar. Bir revizyon atası ya da
  bağımlılığı olduğu revizyonu kapsar: yalnızca `ders_programi_0001` uygulanmışsa (o da
  `cekirdek_0001`'e bağımlı) tabloda tek satır vardır. Çekirdeğe, modülün bağımlı olmadığı yeni
  bir revizyon eklenince iki satır olur (ör. cekirdek_0003 ve ders_programi_0002).
- `upgrade heads` bütün dalları en son haline getirir; `upgrade ders_programi@head` yalnızca o dalı
  (ve bağımlı olduğu çekirdek revizyonlarını) getirir.

Kullanım (api/ klasöründen):
    python -m okulapi.migrasyon upgrade heads
    python -m okulapi.migrasyon downgrade base
    python -m okulapi.migrasyon history
    python -m okulapi.migrasyon revision --autogenerate -m "ogretmen tablosu" \\
        --head cekirdek@head --version-path src/okulapi/cekirdek/migrations
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config

from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek import CEKIRDEK_MIGRATION_DIZINI
from okulapi.cekirdek.modul import modulleri_yukle

CEKIRDEK_DALI = "cekirdek"
CEKIRDEK_KOK_REVIZYONU = "cekirdek_0001"


def surum_dizinleri(ayarlar: Ayarlar) -> list[Path]:
    return [CEKIRDEK_MIGRATION_DIZINI] + [m.migration_dizini for m in modulleri_yukle(ayarlar.etkin_moduller)]


def alembic_ayari(ayarlar: Ayarlar | None = None, veritabani_url: str | None = None) -> Config:
    ayarlar = ayarlar or Ayarlar()
    ayar = Config()
    ayar.set_main_option("script_location", str(Path(__file__).parent))
    ayar.set_main_option("path_separator", "os")  # sürüm klasörleri işletim sisteminin ayıracıyla
    ayar.set_main_option("version_locations", os.pathsep.join(str(d) for d in surum_dizinleri(ayarlar)))
    url = veritabani_url or ayarlar.migrasyon_url  # migration: tablo sahibi rolüyle
    ayar.set_main_option("sqlalchemy.url", url.replace("%", "%%"))  # Config, % ile değişken açar
    ayar.attributes["ayarlar"] = ayarlar
    return ayar
