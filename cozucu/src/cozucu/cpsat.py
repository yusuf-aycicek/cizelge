"""`ProgramCozucu` arayüzünün OR-Tools CP-SAT gerçeklemesi (bkz. docs/adr/0001, 0018)."""

from __future__ import annotations

import time
from collections.abc import Callable

from ortools.sat.python import cp_model

from cozucu.arayuz import VARSAYILAN_SURE_SINIRI_SN, ProgramCozucu
from cozucu.celiski import celiskileri_bul
from cozucu.kalite import agirlikli_ceza, olc
from cozucu.kisitlar import Baglam, GirdiHatasi, etkin_agirliklar, kurallari_hazirla
from cozucu.model import Celiski, CozumDurumu, CozumGirdisi, CozumSonucu, Yerlesim
from cozucu.on_kontrol import on_kontrol

# Çözümsüzlükte çelişki analizine ayrılan en fazla süre (ana süre sınırından ayrı).
CELISKI_ANALIZ_SURESI_SN = 30.0
# Ana çözüm `bilinmiyor` dönerse, yalnızca zorunlu kısıtlarla yapılan ikinci kontrolün süresi.
UYGUNLUK_KONTROLU_SURESI_SN = 60.0
# İki aşamalı çözümde ilk aşamaya (yalnızca zorunlu kısıtlar, ilk çözümde durur) ayrılan en
# fazla pay. İlk aşama ilk programı bulunca durur, kalan süre ikinci aşamaya geçer; bu yüzden pay
# yalnızca ilk program geç gelirse sınırlar. Ölçüm (docs/olcumler.md, ADR 0018): 120 sn'de 0,25 /
# 0,5 / 1 aynı; 30 sn'de büyük sette 0,5 bir tohumda programsız bıraktı, 1 hiçbirinde.
UYGUNLUK_PAYI = 1.0

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


def _zorunlu_baglam(girdi: CozumGirdisi) -> Baglam:
    """Yalnızca zorunlu kısıtların modeli, amaç olmadan."""
    baglam = Baglam.kur(girdi)
    for kural in kurallari_hazirla(girdi):
        if kural.zorunlu:
            kural.uygula(baglam)
    return baglam


class CpSatCozucu(ProgramCozucu):
    def __init__(
        self,
        is_parcacigi: int = 8,
        tohum: int = 0,
        gozlemci: Gozlemci | None = None,
        iki_asamali: bool = True,
        uygunluk_payi: float = UYGUNLUK_PAYI,
    ) -> None:
        """`gozlemci`: verilirse her iyileşen ara çözüm ona bildirilir (zamana göre kalite ölçümü).

        `iki_asamali`: önce yalnızca zorunlu kısıtlarla bir program bulunur (süre sınırının en
        fazla `uygunluk_payi` kadarında), sonra o program başlangıç ipucu olarak verilip esnek
        kurallarla kalan sürede iyileştirilir (ADR 0018).
        """
        self.is_parcacigi = is_parcacigi
        self.tohum = tohum
        self.gozlemci = gozlemci
        self.iki_asamali = iki_asamali
        self.uygunluk_payi = uygunluk_payi

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

        # Esnek kural yoksa ilk aşama ana çözümün aynısı olurdu.
        ilk: tuple[list[Yerlesim], int] | None = None
        ilk_durum = None
        if self.iki_asamali and cezalar:
            ilk_durum, ilk = self._ilk_asama(girdi, sure_siniri_sn * self.uygunluk_payi, baslangic)

        if ilk_durum == cp_model.INFEASIBLE:
            cp_durum, solver = cp_model.INFEASIBLE, None
        else:
            if ilk is not None:
                ipucu = {(y.ders_atama_id, y.gun, y.saat) for y in ilk[0]}
                baglam.model.clear_hints()  # temel programın ipucu ilk aşamada kullanıldı
                for anahtar, degisken in baglam.x.items():
                    baglam.model.add_hint(degisken, anahtar in ipucu)
            kalan = sure_siniri_sn - (time.perf_counter() - baslangic)
            if ilk is not None and kalan <= 0:
                cp_durum, solver = cp_model.UNKNOWN, None
            else:
                cp_durum, solver = self._ana_cozum(baglam, max(kalan, 0.1), baslangic)
        durum = _DURUM_KARSILIGI.get(cp_durum, CozumDurumu.BILINMIYOR)

        sonuc = CozumSonucu(durum=durum)
        if durum is CozumDurumu.BILINMIYOR and ilk is not None:
            # İkinci aşama süre içinde ilk aşamanın programından daha iyisini bulamadı.
            durum = sonuc.durum = CozumDurumu.UYGUN
            sonuc.yerlesimler, sonuc.toplam_ceza = ilk
            sonuc.mesajlar.append(
                "Süre doldu: kurallara uyan bir program bulundu, ama iyileştirmeye süre kalmadı. "
                "Daha uzun bir süre sınırıyla daha iyi bir program bulunabilir."
            )
        elif durum is CozumDurumu.BILINMIYOR:
            # Esnek hedef aramayı yavaşlatıp çözümsüzlüğün kanıtını geciktirebilir (gerçekçi sette
            # ana çözüm 60 sn'de kanıtlayamadı, yalnızca zorunlu kısıtlarla 18,6 sn'de kanıtlandı).
            # İlk aşama süre içinde sonuç vermediyse aynı soruyu biraz daha uzun sorar.
            ikinci = self._uygunluk_kontrolu(girdi, UYGUNLUK_KONTROLU_SURESI_SN)
            if ikinci == cp_model.INFEASIBLE:
                durum = sonuc.durum = CozumDurumu.COZUMSUZ
            elif ikinci in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                sonuc.mesajlar.append(
                    f"Kurallara uyan bir program var, ama {sure_siniri_sn:g} sn içinde bulunamadı. "
                    "Daha uzun bir süre sınırıyla yeniden deneyin."
                )
            else:
                sonuc.mesajlar.append(
                    f"Süre sınırı ({sure_siniri_sn:g} sn) içinde ne program bulunabildi ne de programın "
                    "olmadığı kanıtlanabildi. Daha uzun bir süre sınırıyla yeniden deneyin."
                )
        elif sonuc.basarili:
            sonuc.yerlesimler = _yerlesimler(baglam, solver.boolean_value)
            sonuc.toplam_ceza = round(solver.objective_value) if cezalar else 0
            if durum is CozumDurumu.UYGUN:
                sonuc.mesajlar.append(
                    "Süre doldu: bulunan en iyi program döndü, daha iyisinin olmadığı kanıtlanamadı."
                )
        if durum is CozumDurumu.COZUMSUZ:
            sonuc.mesajlar.append("Zorunlu kısıtların hepsini sağlayan bir program yok.")
            sonuc.celiskiler = celiskileri_bul(girdi, min(sure_siniri_sn, CELISKI_ANALIZ_SURESI_SN),
                                               self.is_parcacigi)
        sonuc.sure_sn = time.perf_counter() - baslangic
        return sonuc

    def _cozucu(self, sure: float) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = sure
        solver.parameters.num_workers = self.is_parcacigi
        solver.parameters.random_seed = self.tohum
        return solver

    def _ana_cozum(self, baglam: Baglam, sure: float, baslangic: float) -> tuple[int, cp_model.CpSolver]:
        solver = self._cozucu(sure)
        bildirici = _CozumBildirici(baglam, self.gozlemci, baslangic) if self.gozlemci else None
        return solver.solve(baglam.model, bildirici), solver

    def _ilk_asama(
        self, girdi: CozumGirdisi, sure: float, baslangic: float
    ) -> tuple[int, tuple[list[Yerlesim], int] | None]:
        """Yalnızca zorunlu kısıtlarla ilk programı arar; bulunca durur.

        Temel program varsa ipucu olarak verilir: ilk program temel programa yakın başlar.
        Dönen ceza, programın esnek kurallara göre bağımsız ölçülmüş toplam cezasıdır
        (modelin amaç değeriyle en iyi çözümde aynı ölçü).
        """
        baglam = _zorunlu_baglam(girdi)
        temel = {(t.sinif_id, t.ders_id, t.gun, t.saat) for t in girdi.temel_yerlesimler}
        if temel:
            for (a, g, s), degisken in baglam.x.items():
                atama = baglam.atama[a]
                baglam.model.add_hint(degisken, (atama.sinif_id, atama.ders_id, g, s) in temel)
        solver = self._cozucu(sure)
        solver.parameters.stop_after_first_solution = True
        durum = solver.solve(baglam.model)
        if durum not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return durum, None
        yerlesimler = _yerlesimler(baglam, solver.boolean_value)
        ceza = agirlikli_ceza(olc(girdi, yerlesimler), etkin_agirliklar(girdi))
        if self.gozlemci:
            self.gozlemci(time.perf_counter() - baslangic, ceza, yerlesimler)
        return durum, (yerlesimler, ceza)

    def _uygunluk_kontrolu(self, girdi: CozumGirdisi, sure: float) -> int:
        """Yalnızca zorunlu kısıtlarla, amaç olmadan: kurallara uyan herhangi bir program var mı?"""
        return self._cozucu(sure).solve(_zorunlu_baglam(girdi).model)
