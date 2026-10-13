"""Zamana göre kalite ölçümü ve komut satırı."""

from pathlib import Path

from cozucu.cli import main as cli_main
from cozucu.kalite import agirlikli_ceza
from cozucu.kisitlar import etkin_agirliklar
from cozucu.olcum import olc_zamana_gore, tablo
from cozucu.veri_io import girdi_oku

MINI = Path(__file__).resolve().parents[2] / "veri" / "mini.json"


def test_zamana_gore_kalite_kontrol_noktalari():
    girdi = girdi_oku(MINI)
    c = olc_zamana_gore(girdi, tohum=0, noktalar=(0.0, 2.0, 4.0))
    assert [k.saniye for k in c.noktalar] == [0.0, 2.0, 4.0]
    assert c.ilk_cozum_sn is not None and c.iyilesme_sayisi >= 1
    son = c.noktalar[-1]
    assert son.olcum is not None
    assert son.gercek_ceza == agirlikli_ceza(son.olcum, etkin_agirliklar(girdi))
    # Model cezası ara çözümlerde gerçek cezadan küçük olamaz (yardımcılar yalnızca alttan sınırlı).
    assert son.model_ceza >= son.gercek_ceza
    # Zaman ilerledikçe kalite kötüleşmez.
    cezalar = [k.gercek_ceza for k in c.noktalar if k.gercek_ceza is not None]
    assert cezalar == sorted(cezalar, reverse=True)
    assert "| 0 | 4 |" in tablo([c])


def test_cli_mini_set(capsys):
    kod = cli_main([str(MINI), "--sure", "5", "--sinif", "9-A", "--ogretmen", "Mehmet Kaya"])
    cikti = capsys.readouterr().out
    assert kod == 0
    assert "Doğrulama: geçti" in cikti
    assert "### 9-A" in cikti and "### 10-A" not in cikti
    assert "### Mehmet Kaya" in cikti and "gelemez" in cikti


def test_cli_temel_ile_guncelleme(tmp_path, capsys):
    sonuc_dosyasi = tmp_path / "sonuc.json"
    assert cli_main([str(MINI), "--sure", "5", "--sinif", "--kaydet", str(sonuc_dosyasi)]) == 0
    assert cli_main([str(MINI), "--sure", "5", "--sinif", "--temel", str(sonuc_dosyasi)]) == 0
    assert "değişen hücre 0/71" in capsys.readouterr().out
