"""Worker sürecinin veritabanı bağlantısı.

Kuyruktaki işler yalnızca kimlik taşır (ör. okul_id, program_id); veritabanı oturumu işin
argümanı olamaz. İş fonksiyonları oturum fabrikasını buradan alır.

Fabrika ilk kullanımda kurulur, süreç başına bir kez. RQ worker'ı her iş için `fork` ile yeni bir
alt süreç açar. Ana süreçte açılmış bir bağlantı alt sürece kopyalanıp iki süreçten kullanılırsa
bozulur. Fabrikayı tembel (lazy) kurmak, bağlantının işi çalıştıran süreçte açılmasını sağlar.
"""

from __future__ import annotations

from functools import cache

from sqlalchemy.orm import sessionmaker

import okulapi.cekirdek.kiraci  # noqa: F401  (okul filtresi olayları kaydolur)
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.modul import modulleri_yukle
from okulapi.cekirdek.veritabani import motor_olustur, oturum_fabrikasi


@cache
def isci_fabrikasi() -> sessionmaker:
    ayarlar = Ayarlar()
    modulleri_yukle(ayarlar.etkin_moduller)  # modellerin hepsi eşlensin (ilişkiler, okul filtresi)
    return oturum_fabrikasi(motor_olustur(ayarlar.veritabani_url))
