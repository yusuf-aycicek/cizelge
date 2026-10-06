"""Çözücü arayüzü.

Worker ve geri kalan sistem yalnızca bu arayüzü bilir. CP-SAT yerine başka bir algoritmaya
geçmek yeni bir gerçekleme yazmak demektir; çağıran kod değişmez (bkz. docs/adr/0001).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cozucu.model import CozumGirdisi, CozumSonucu

VARSAYILAN_SURE_SINIRI_SN = 60.0


class ProgramCozucu(ABC):
    @abstractmethod
    def coz(
        self, girdi: CozumGirdisi, sure_siniri_sn: float = VARSAYILAN_SURE_SINIRI_SN
    ) -> CozumSonucu:
        """Girdiye uygun haftalık programı üretir.

        Süre dolarsa bulunan en iyi çözümü döner. Çözüm yoksa ya da veri hatalıysa
        `CozumSonucu.mesajlar` içinde nedenini açıklar; istisna fırlatmaz.
        """
