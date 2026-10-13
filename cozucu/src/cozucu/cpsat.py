"""`ProgramCozucu` arayüzünün OR-Tools CP-SAT gerçeklemesi (bkz. docs/adr/0001)."""

from __future__ import annotations

import time
from collections.abc import Callable

from ortools.sat.python import cp_model

from cozucu.arayuz import VARSAYILAN_SURE_SINIRI_SN, ProgramCozucu
from cozucu.celiski import celiskileri_bul
from cozucu.kisitlar import Baglam, GirdiHatasi, kurallari_hazirla
from cozucu.model import Celiski, CozumDurumu, CozumGirdisi, CozumSonucu, Yerlesim
from cozucu.on_kontrol import on_kontrol

# Çözümsüzlükte çelişki analizine ayrılan en fazla süre (ana süre sınırından ayrı).
CELISKI_ANALIZ_SURESI_SN = 30.0

_DURUM_KARSILIGI = {
    cp_model.OPTIMAL: CozumDurumu.OPTIMAL,
    cp_model.FEASIBLE: CozumDurumu.UYGUN,
    cp_model.INFEASIBLE: CozumDurumu.COZUMSUZ,
}


# (geçen süre sn, model amaç değeri, yerleşimler) -> None. Her iyileşen çözümde çağrılır.
Gozlemci = Callable[[float, int, list[Yerlesim]], None]


class _CozumBildirici(cp_model.CpSolverSolutionCallback):
    def __init__(self, baglam: Baglam, gozlemci: Gozlemci, baslangic: float) -> None:
        super().__init__()
        self._baglam = baglam
        self._gozlemci = gozlemci
        self._baslangic = baslangic

    def on_solution_callback(self) -> None:
        yerlesimler = _yerlesimler(self._baglam, self.boolean_value)
        self._gozlemci(time.perf_counter() - self._baslangic, round(self.objective_value), yerlesimler)


def _yerlesimler(baglam: Baglam, deger: Callable[[cp_model.IntVar], bool]) -> list[Yerlesim]:
    kilitli = {(y.ders_atama_id, y.gun, y.saat) for y in baglam.girdi.kilitli_yerlesimler}
    return [
        Yerlesim(ders_atama_id=a, gun=g, saat=s, kilitli=(a, g, s) in kilitli)
        for (a, g, s), degisken in baglam.x.items()
        if deger(degisken)
    ]


class CpSatCozucu(ProgramCozucu):
    def __init__(self, is_parcacigi: int = 8, tohum: int = 0, gozlemci: Gozlemci | None = None) -> None:
        """`gozlemci`: verilirse her iyileşen ara çözüm ona bildirilir (zamana göre kalite ölçümü)."""
        self.is_parcacigi = is_parcacigi
        self.tohum = tohum
        self.gozlemci = gozlemci

    def coz(
        self, girdi: CozumGirdisi, sure_siniri_sn: float = VARSAYILAN_SURE_SINIRI_SN
    ) -> CozumSonucu:
        baslangic = time.perf_counter()
        sorunlar = on_kontrol(girdi)
        if not sorunlar:
            try:
                baglam = Baglam.kur(girdi)
                cezalar = []
                for kural in kurallari_hazirla(girdi):
                    cezalar.extend(kural.uygula(baglam))
            except GirdiHatasi as hata:  # ön kontrolün kaçırdığı bir tutarsızlık için güvenlik ağı
                sorunlar = [Celiski("tutarsiz_veri", str(hata))]
        if sorunlar:
            return CozumSonucu(
                durum=CozumDurumu.ON_KONTROL_HATASI,
                celiskiler=sorunlar,
                sure_sn=time.perf_counter() - baslangic,
            )

        if cezalar:
            baglam.model.minimize(sum(agirlik * ifade for ifade, agirlik in cezalar))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = sure_siniri_sn
        solver.parameters.num_workers = self.is_parcacigi
        solver.parameters.random_seed = self.tohum
        bildirici = _CozumBildirici(baglam, self.gozlemci, baslangic) if self.gozlemci else None
        cp_durum = solver.solve(baglam.model, bildirici)
        durum = _DURUM_KARSILIGI.get(cp_durum, CozumDurumu.BILINMIYOR)

        sonuc = CozumSonucu(durum=durum)
        if sonuc.basarili:
            sonuc.yerlesimler = _yerlesimler(baglam, solver.boolean_value)
            sonuc.toplam_ceza = round(solver.objective_value) if cezalar else 0
            if durum is CozumDurumu.UYGUN:
                sonuc.mesajlar.append(
                    "Süre doldu: bulunan en iyi program döndü, daha iyisinin olmadığı kanıtlanamadı."
                )
        elif durum is CozumDurumu.COZUMSUZ:
            sonuc.mesajlar.append("Zorunlu kısıtların hepsini sağlayan bir program yok.")
            sonuc.celiskiler = celiskileri_bul(girdi, min(sure_siniri_sn, CELISKI_ANALIZ_SURESI_SN))
        else:
            sonuc.mesajlar.append(
                f"Süre sınırı ({sure_siniri_sn:g} sn) içinde çözüm bulunamadı "
                f"(CP-SAT durumu: {solver.status_name(cp_durum)})."
            )
        sonuc.sure_sn = time.perf_counter() - baslangic
        return sonuc
