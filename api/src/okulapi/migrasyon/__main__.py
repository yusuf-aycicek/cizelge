"""`alembic` komutunun sarmalayıcısı: python -m okulapi.migrasyon <alembic komutu ve seçenekleri>.

Standart `alembic.ini` yerine bunu kullanmamızın nedeni: sürüm klasörleri etkin modül listesinden
gelir. Yeni bir modül eklendiğinde ayrıca bir yapılandırma dosyasını düzenlemek gerekmez.
"""

from __future__ import annotations

import logging
import sys

from alembic.config import CommandLine

from okulapi.migrasyon import alembic_ayari


def main(argv: list[str] | None = None) -> None:
    # alembic.ini olmadığı için günlük ayarı burada: "Running upgrade -> ..." satırları görünsün.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("alembic").setLevel(logging.INFO)
    komut_satiri = CommandLine(prog="python -m okulapi.migrasyon")
    secenekler = komut_satiri.parser.parse_args(argv)
    if not hasattr(secenekler, "cmd"):
        komut_satiri.parser.error("bir alembic komutu verin (ör. upgrade heads)")
    komut_satiri.run_cmd(alembic_ayari(), secenekler)


if __name__ == "__main__":
    main(sys.argv[1:])
