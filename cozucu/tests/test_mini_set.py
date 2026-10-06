"""Uçtan uca: mini veri seti çözülür ve bağımsız doğrulayıcıdan geçer."""

from pathlib import Path

from cozucu import CozumDurumu, CpSatCozucu, dogrula
from cozucu.veri_io import girdi_oku

MINI = Path(__file__).resolve().parents[2] / "veri" / "mini.json"


def test_mini_set_cozulur_ve_dogrulanir():
    girdi = girdi_oku(MINI)
    assert len(girdi.siniflar) == 3 and len(girdi.ogretmenler) == 5

    sonuc = CpSatCozucu().coz(girdi, sure_siniri_sn=30)

    assert sonuc.durum in (CozumDurumu.OPTIMAL, CozumDurumu.UYGUN), sonuc.mesajlar
    assert dogrula(girdi, sonuc.yerlesimler) == []
    assert len(sonuc.yerlesimler) == sum(a.haftalik_saat for a in girdi.atamalar)
    assert [(y.ders_atama_id, y.gun, y.saat) for y in sonuc.yerlesimler if y.kilitli] == [
        ("a-9a-mat", 1, 0)
    ]
