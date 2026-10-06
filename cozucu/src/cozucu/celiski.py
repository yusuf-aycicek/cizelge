"""Ön kontrolden geçip yine çözümsüz kalan girdilerde, birlikte sağlanamayan kuralları bulur.

Yöntem (bkz. docs/adr/0005):
1. Model yalnızca zorunlu kurallarla, analiz kipinde kurulur. Her kural kısıtlarını
   `baglam.grupla` ile anlamlı bir gruba bağlar ("Ayşe'nin gelemez saatleri", "9-A Matematik
   haftada 6 saat"). Her grubun bir literali vardır, kısıtlar yalnızca literal doğruysa geçerlidir.
2. Aday küme: Bütün literaller varsayım (assumption) olarak verilir. CP-SAT "çözüm yok" der ve
   `sufficient_assumptions_for_infeasibility` ile çelişen bir grup kümesi verir. Bu küme küçük
   olmak zorunda değildir, ama denenecek grup sayısını büyük ölçüde azaltır. Bu adıma sürenin en
   fazla üçte biri ayrılır. Süre yetmezse bütün gruplar aday kabul edilir.
3. Küçültme: Adaylar teker teker çıkarılır ve model "yalnızca kalan gruplar açık" olacak şekilde
   yeniden kurulup çözülür. Hâlâ çözümsüzse çıkarılan grup gereksizdir. Sonuç: hiçbir grubu
   çıkarılamayan en küçük küme.
   Bu denemelerde literaller varsayım olarak değil, sabit (`lit == 0/1`) olarak verilir. Varsayımlar
   CP-SAT'ın ön işlemesine görünmez, kısıtlar koşullu kalır ve gevşek model zayıflar. Sabitler ise
   ön işlemede yayılır ve kısıtlar normal haline döner. Mini sette bir çözümsüzlük kanıtı 4,4
   saniyeden 0,07 saniyeye indi.
4. Küme, kullanıcının diliyle bir maddeler listesine çevrilir.

Çakışma kuralları (sınıf/öğretmen aynı saatte tek yerde) gruba bağlanmaz. Bunlar programın
tanımıdır, "gevşetilecek" bir şey değildir.
"""

from __future__ import annotations

import time

from ortools.sat.python import cp_model

from cozucu.anlatim import Anlatim, iyelik
from cozucu.kisitlar import Baglam, kurallari_hazirla
from cozucu.kisitlar.temel import GrupAnahtari
from cozucu.model import (
    GUNLUK_DERS_SINIRI_TURU,
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_GUNLUK_DERS_SINIRI,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    Celiski,
    CozumGirdisi,
)

# Maddelerin mesajdaki sırası: önce kişiye/zamana bağlı kurallar, en son ders saatleri.
_SIRA = ("gelemez", "ogretmen_gunluk", "kilit", "gunluk_ders", "haftalik_saat")


def celiskileri_bul(
    girdi: CozumGirdisi, sure_siniri_sn: float = 30.0, is_parcacigi: int = 8
) -> list[Celiski]:
    """Çelişen en küçük kural kümesini tek bir `Celiski` olarak döner; bulunamazsa [].

    Süre küçültme bitmeden dolarsa o ana kadarki (en küçük olmayabilecek) küme raporlanır.
    """
    analiz = _Analiz(girdi, time.perf_counter() + sure_siniri_sn, is_parcacigi)
    if analiz.cozumsuz_mu(set(analiz.gruplar)) is not True:
        return []
    aday = analiz.varsayim_cekirdegi(sure_siniri_sn / 3) or list(analiz.gruplar)

    # Küçültme: aday sırayla çıkarılır. Çıkarınca hâlâ çözümsüzse grup gereksizdir.
    cekirdek = list(aday)
    for anahtar in aday:
        if len(cekirdek) == 1 or analiz.sure_doldu():
            break
        kalan = [a for a in cekirdek if a != anahtar]
        if analiz.cozumsuz_mu(set(kalan)) is True:
            cekirdek = kalan
    return [_anlat(girdi, cekirdek)]


class _Analiz:
    def __init__(self, girdi: CozumGirdisi, bitis: float, is_parcacigi: int) -> None:
        self.girdi = girdi
        self.bitis = bitis
        self.is_parcacigi = is_parcacigi
        self.gruplar = list(self._kur().gruplar or {})

    def _kur(self) -> Baglam:
        baglam = Baglam.kur(self.girdi, analiz=True)
        for kural in kurallari_hazirla(self.girdi):
            if kural.zorunlu:
                kural.uygula(baglam)
        return baglam

    def sure_doldu(self) -> bool:
        return time.perf_counter() >= self.bitis

    def _solver(self, sure: float, is_parcacigi: int) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(sure, 0.01)
        solver.parameters.num_workers = is_parcacigi
        return solver

    def cozumsuz_mu(self, acik: set[GrupAnahtari]) -> bool | None:
        """Yalnızca `acik` gruplar geçerliyken çözüm yok mu? Süre yetmezse None."""
        if self.sure_doldu():
            return None
        baglam = self._kur()
        assert baglam.gruplar is not None
        for anahtar, literal in baglam.gruplar.items():
            baglam.model.add(literal == int(anahtar in acik))
        durum = self._solver(self.bitis - time.perf_counter(), self.is_parcacigi).solve(baglam.model)
        if durum == cp_model.INFEASIBLE:
            return True
        if durum in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return False
        return None

    def varsayim_cekirdegi(self, sure: float) -> list[GrupAnahtari] | None:
        """CP-SAT'ın varsayım çekirdeği; süre yetmezse None."""
        baglam = self._kur()
        assert baglam.gruplar is not None
        anahtar_of = {lit.index: a for a, lit in baglam.gruplar.items()}
        baglam.model.add_assumptions(list(baglam.gruplar.values()))
        sure = min(sure, self.bitis - time.perf_counter())
        solver = self._solver(sure, 1)  # varsayım çekirdeği tek iş parçacığında güvenilir
        if solver.solve(baglam.model) != cp_model.INFEASIBLE:
            return None
        return [anahtar_of[i] for i in solver.sufficient_assumptions_for_infeasibility()] or None


def _anlat(girdi: CozumGirdisi, cekirdek: list[GrupAnahtari]) -> Celiski:
    ad = Anlatim(girdi)
    atama = {a.id: a for a in girdi.atamalar}
    n = girdi.zorunlu_parametre(GUNLUK_DERS_SINIRI_TURU, "n", VARSAYILAN_GUNLUK_DERS_SINIRI)
    m = girdi.zorunlu_parametre(OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI)

    maddeler: list[str] = []
    ilgili: list[str] = []
    for anahtar in sorted(cekirdek, key=lambda k: (_SIRA.index(str(k[0])), [str(p) for p in k[1:]])):
        tur, *p = anahtar
        if tur == "gelemez":
            maddeler.append(f"{iyelik(ad.ogretmen(p[0]))} gelemez saatleri")
            ilgili.append(p[0])
        elif tur == "ogretmen_gunluk":
            maddeler.append(f"{ad.ogretmen(p[0])} günde en fazla {m} saat derse girebilir")
            ilgili.append(p[0])
        elif tur == "kilit":
            maddeler.append(f"{ad.atama(p[0])} {ad.zaman(p[1], p[2])}te kilitli")
            ilgili.append(p[0])
        elif tur == "gunluk_ders":
            maddeler.append(f"{ad.sinif_ders(p[0], p[1])} bir günde en fazla {n} saat olabilir")
            ilgili.append(p[0])
        elif tur == "haftalik_saat":
            a = atama[p[0]]
            maddeler.append(f"{ad.atama(a)} haftada {a.haftalik_saat} saat ({ad.ogretmen(a.ogretmen_id)})")
            ilgili.append(a.id)
    mesaj = (
        "Şu kurallar birlikte sağlanamıyor, en az birinin gevşetilmesi gerekiyor:\n"
        + "\n".join(f"- {madde}" for madde in maddeler)
    )
    return Celiski("celiski", mesaj, tuple(dict.fromkeys(ilgili)))
