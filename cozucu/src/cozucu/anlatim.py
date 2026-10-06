"""Kimlikleri kullanıcının diline çevirir: "a-9a-mat" yerine "9-A Matematik", gun=1 yerine "Salı".

Ön kontrol ve çelişki mesajları bunu kullanır. Bilinmeyen bir kimlik kimliğin kendisiyle
gösterilir; mesaj üretimi hiçbir zaman hata fırlatmaz.
"""

from __future__ import annotations

from cozucu.model import CozumGirdisi, DersAtama

GUN_ADLARI = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


class Anlatim:
    def __init__(self, girdi: CozumGirdisi) -> None:
        self._ogretmen = {o.id: o.ad for o in girdi.ogretmenler}
        self._sinif = {s.id: s.ad for s in girdi.siniflar}
        self._ders = {d.id: d.ad for d in girdi.dersler}
        self._atama = {a.id: a for a in girdi.atamalar}

    def ogretmen(self, ogretmen_id: str | None) -> str:
        if ogretmen_id is None:
            return "(öğretmen seçilmemiş)"
        return self._ogretmen.get(ogretmen_id, ogretmen_id)

    def sinif(self, sinif_id: str) -> str:
        return self._sinif.get(sinif_id, sinif_id)

    def ders(self, ders_id: str) -> str:
        return self._ders.get(ders_id, ders_id)

    def sinif_ders(self, sinif_id: str, ders_id: str) -> str:
        return f"{self.sinif(sinif_id)} {self.ders(ders_id)}"

    def atama(self, atama: DersAtama | str) -> str:
        """"9-A Matematik" biçimi."""
        if isinstance(atama, str):
            if atama not in self._atama:
                return atama
            atama = self._atama[atama]
        return self.sinif_ders(atama.sinif_id, atama.ders_id)

    @staticmethod
    def zaman(gun: int, saat: int) -> str:
        """"Salı 1. saat" biçimi."""
        gun_adi = GUN_ADLARI[gun] if 0 <= gun < len(GUN_ADLARI) else f"{gun + 1}. gün"
        return f"{gun_adi} {saat + 1}. saat"

    @staticmethod
    def gun(gun: int) -> str:
        return GUN_ADLARI[gun] if 0 <= gun < len(GUN_ADLARI) else f"{gun + 1}. gün"


def iyelik(ad: str) -> str:
    """Türkçe iyelik eki, kesme işaretiyle: "Ayşe Yılmaz" -> "Ayşe Yılmaz'ın".

    Son ünlüye göre büyük ünlü uyumu (ın/in/un/ün); ünlüyle bitiyorsa kaynaştırma -n-.
    """
    unluler = "aıoueiöüAIOUEİÖÜ"
    kucuk = {"A": "a", "I": "ı", "O": "o", "U": "u", "E": "e", "İ": "i", "Ö": "ö", "Ü": "ü"}
    son_unlu = next((h for h in reversed(ad) if h in unluler), "e")
    son_unlu = kucuk.get(son_unlu, son_unlu)
    ek = {"a": "ın", "ı": "ın", "o": "un", "u": "un", "e": "in", "i": "in", "ö": "ün", "ü": "ün"}[son_unlu]
    if ad and ad[-1] in unluler:
        ek = "n" + ek
    return f"{ad}'{ek}"
