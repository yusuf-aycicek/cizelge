"""Çözücü arayüzü.

Worker ve geri kalan sistem yalnızca bu arayüzü bilir. CP-SAT yerine başka bir algoritmaya
geçmek yeni bir gerçekleme yazmak demektir; çağıran kod değişmez (bkz. docs/adr/0001).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cozucu.model import CozumGirdisi, CozumSonucu

# Ölçüm sonucu (docs/olcumler.md): iki test setinde de sınıf boşluğunu her tohumda sıfırlayan
# en kısa süre. Program üretimi kuyrukta worker'da çalıştığı için arayüzü bekletmez.
VARSAYILAN_SURE_SINIRI_SN = 120.0


class ProgramCozucu(ABC):
    @abstractmethod
    def coz(
        self, girdi: CozumGirdisi, sure_siniri_sn: float = VARSAYILAN_SURE_SINIRI_SN
    ) -> CozumSonucu:
        """Girdiye uygun haftalık programı üretir.

        Süre dolarsa bulunan en iyi çözümü döner. Çözüm yoksa ya da veri hatalıysa
        `CozumSonucu.mesajlar` içinde nedenini açıklar; istisna fırlatmaz.
        """
