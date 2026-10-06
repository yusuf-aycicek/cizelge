"""`ProgramCozucu` arayüzünün OR-Tools CP-SAT gerçeklemesi (bkz. docs/adr/0001)."""

from __future__ import annotations

import time

from ortools.sat.python import cp_model

from cozucu.arayuz import VARSAYILAN_SURE_SINIRI_SN, ProgramCozucu
from cozucu.kisitlar import Baglam, GirdiHatasi, kurallari_hazirla
from cozucu.model import CozumDurumu, CozumGirdisi, CozumSonucu, Yerlesim

_DURUM_KARSILIGI = {
    cp_model.OPTIMAL: CozumDurumu.OPTIMAL,
    cp_model.FEASIBLE: CozumDurumu.UYGUN,
    cp_model.INFEASIBLE: CozumDurumu.COZUMSUZ,
}


class CpSatCozucu(ProgramCozucu):
    def __init__(self, is_parcacigi: int = 8, tohum: int = 0) -> None:
        self.is_parcacigi = is_parcacigi
        self.tohum = tohum

    def coz(
        self, girdi: CozumGirdisi, sure_siniri_sn: float = VARSAYILAN_SURE_SINIRI_SN
    ) -> CozumSonucu:
        baslangic = time.perf_counter()
        try:
            baglam = Baglam.kur(girdi)
            cezalar = []
            for kural in kurallari_hazirla(girdi):
                cezalar.extend(kural.uygula(baglam))
        except GirdiHatasi as hata:
            return CozumSonucu(
                durum=CozumDurumu.ON_KONTROL_HATASI,
                mesajlar=[str(hata)],
                sure_sn=time.perf_counter() - baslangic,
            )

        if cezalar:
            baglam.model.minimize(sum(agirlik * ifade for ifade, agirlik in cezalar))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = sure_siniri_sn
        solver.parameters.num_workers = self.is_parcacigi
        solver.parameters.random_seed = self.tohum
        cp_durum = solver.solve(baglam.model)
        durum = _DURUM_KARSILIGI.get(cp_durum, CozumDurumu.BILINMIYOR)

        sonuc = CozumSonucu(durum=durum)
        if sonuc.basarili:
            kilitli = {(y.ders_atama_id, y.gun, y.saat) for y in girdi.kilitli_yerlesimler}
            sonuc.yerlesimler = [
                Yerlesim(ders_atama_id=a, gun=g, saat=s, kilitli=(a, g, s) in kilitli)
                for (a, g, s), degisken in baglam.x.items()
                if solver.boolean_value(degisken)
            ]
            sonuc.toplam_ceza = round(solver.objective_value) if cezalar else 0
            if durum is CozumDurumu.UYGUN:
                sonuc.mesajlar.append(
                    "Süre doldu: bulunan en iyi program döndü, daha iyisinin olmadığı kanıtlanamadı."
                )
        elif durum is CozumDurumu.COZUMSUZ:
            sonuc.mesajlar.append("Zorunlu kısıtların hepsini sağlayan bir program yok.")
        else:
            sonuc.mesajlar.append(
                f"Süre sınırı ({sure_siniri_sn:g} sn) içinde çözüm bulunamadı "
                f"(CP-SAT durumu: {solver.status_name(cp_durum)})."
            )
        sonuc.sure_sn = time.perf_counter() - baslangic
        return sonuc
