"""Alembic çalışma ortamı. Alembic her komutta bu dosyayı çalıştırır.

`target_metadata`, çekirdeğin ve etkin modüllerin bütün tablolarını içerir. `--autogenerate`
veritabanını buna göre karşılaştırır.
"""

from __future__ import annotations

from alembic import context

import okulapi.cekirdek.modeller  # noqa: F401  (çekirdek tabloları metadata'ya kaydolur)
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.modul import modulleri_yukle
from okulapi.cekirdek.veritabani import Base, motor_olustur

ayar = context.config
ayarlar = ayar.attributes.get("ayarlar") or Ayarlar()
modulleri_yukle(ayarlar.etkin_moduller)  # modüllerin modelleri içe aktarılır, metadata'ya kaydolur
target_metadata = Base.metadata


def cevrimdisi() -> None:
    """SQL'i veritabanına bağlanmadan yazdırır (ör. bir yöneticiye inceleme için vermek)."""
    context.configure(url=ayar.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def cevrimici() -> None:
    motor = motor_olustur(ayar.get_main_option("sqlalchemy.url"))
    with motor.connect() as baglanti:
        context.configure(connection=baglanti, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    cevrimdisi()
else:
    cevrimici()
