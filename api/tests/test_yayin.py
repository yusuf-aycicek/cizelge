"""Yayın (8b-1, ADR 0022): dondurulmuş içerik, CASCADE'e karşı koruma, "eski veri" uyarısı."""

from __future__ import annotations

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.yayin import YayinServisi
from test_cikti import hazir_program, yerlesimler  # noqa: F401  (hazir_program: fikstür)
from test_program_uretimi import okul, program_ekle  # noqa: F401

YAYIN = f"{DP}/yayin"


def yayinla(istemci, okul, program_id):
    return istemci.put(YAYIN, json={"program_id": str(program_id)}, headers=okul["baslik"])


def icerik(oturum_fabrikasi, okul):
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        return YayinServisi(o).icerik()


def ogretmen_hucreleri(cikti, ad):
    return next(c for c in cikti.ogretmenler if c.ad == ad).hucreler


def test_yayinla_durum_ve_yeniden_yayinlama_tek_satir(istemci, okul, hazir_program):
    assert istemci.get(YAYIN, headers=okul["baslik"]).json() is None
    yanit = yayinla(istemci, okul, hazir_program)
    assert yanit.status_code == 200, yanit.text
    durum = yanit.json()
    assert durum["program_adi"] == "Eylül Programı" and durum["uyarilar"] == []
    assert durum["eski_veri"] is False and durum["program_degisti"] is False
    ilk = durum["yayin_zamani"]
    durum = yayinla(istemci, okul, hazir_program).json()
    assert durum["yayin_zamani"] > ilk
    assert istemci.get(YAYIN, headers=okul["baslik"]).json()["yayin_zamani"] == durum["yayin_zamani"]


def test_atama_ogretmen_ve_ders_silinse_de_yayin_eksilmez(istemci, okul, hazir_program, oturum_fabrikasi):
    """api-plani "Sonraya" 1: atama silinince yerleşimleri CASCADE ile silinir (taslak program
    eksilir), yayınlanan program aynı kalır."""
    yayinla(istemci, okul, hazir_program)
    once = icerik(oturum_fabrikasi, okul)
    ali = ogretmen_hucreleri(once, "Ali Çelik")
    assert ali
    # Ali Çelik'in bütün atamaları, sonra kendisi silinir.
    ali_id = okul["harita"]["o-ali"]
    atamalar = [a for a in istemci.get(f"{DP}/atamalar", headers=okul["baslik"]).json() if a["ogretmen_id"] == ali_id]
    for a in atamalar:
        assert istemci.delete(f"{DP}/atamalar/{a['id']}", headers=okul["baslik"]).status_code == 204
    assert istemci.delete(f"/api/ogretmenler/{ali_id}", headers=okul["baslik"]).status_code == 204
    # Taslak: yerleşimler CASCADE ile gitti.
    kalan = {y["ders_atama_id"] for y in yerlesimler(istemci, okul, hazir_program)}
    assert not kalan & {a["id"] for a in atamalar}
    # Yayın: hiçbir hücre kaybolmadı.
    sonra = icerik(oturum_fabrikasi, okul)
    assert ogretmen_hucreleri(sonra, "Ali Çelik") == ali
    assert sonra.subeler == once.subeler and sonra.ogretmenler == once.ogretmenler
    durum = istemci.get(YAYIN, headers=okul["baslik"]).json()
    assert durum["eski_veri"] is True and durum["program_degisti"] is True
    assert any("eski verilerle üretildi" in u for u in durum["uyarilar"])


def test_veri_degisince_eski_veri_uyarisi(istemci, okul, hazir_program):
    yayinla(istemci, okul, hazir_program)
    atama = okul["harita"]["a-9a-mat"]
    saat = istemci.get(f"{DP}/atamalar/{atama}", headers=okul["baslik"]).json()["haftalik_saat"]
    istemci.patch(f"{DP}/atamalar/{atama}", json={"haftalik_saat": saat - 1}, headers=okul["baslik"])
    durum = istemci.get(YAYIN, headers=okul["baslik"]).json()
    assert durum["eski_veri"] is True and durum["program_degisti"] is False
    assert durum["uyarilar"] == [
        "Yayınlanan program eski verilerle üretildi: öğretmen, ders, dağılım ya da kurallar yayından sonra "
        "değişti. Programı yeniden üretip yayınlayabilirsiniz."]


def test_program_silinince_yayin_kalir(istemci, okul, hazir_program, oturum_fabrikasi):
    yayinla(istemci, okul, hazir_program)
    assert istemci.delete(f"{DP}/programlar/{hazir_program}", headers=okul["baslik"]).status_code == 204
    durum = istemci.get(YAYIN, headers=okul["baslik"]).json()
    assert durum["program_id"] is None and any("silindi" in u for u in durum["uyarilar"])
    assert icerik(oturum_fabrikasi, okul).subeler


def test_hazir_olmayan_ya_da_baska_okulun_programi_yayinlanamaz(istemci, okul, hazir_program, okul_olustur,
                                                               oturum_fabrikasi):
    bekleyen = program_ekle(oturum_fabrikasi, okul["id"], durum="bekliyor")
    assert yayinla(istemci, okul, bekleyen).status_code == 409
    b = {"baslik": okul_basligi(okul_olustur("Başka Lise"))}
    assert yayinla(istemci, b, hazir_program).status_code == 404
    assert istemci.get(YAYIN, headers=b["baslik"]).json() is None
    yayinla(istemci, okul, hazir_program)
    assert istemci.get(YAYIN, headers=b["baslik"]).json() is None
    assert istemci.delete(YAYIN, headers=b["baslik"]).status_code == 404
    assert istemci.get(YAYIN, headers=okul["baslik"]).json() is not None


def test_yayini_kaldir(istemci, okul, hazir_program):
    yayinla(istemci, okul, hazir_program)
    assert istemci.delete(YAYIN, headers=okul["baslik"]).status_code == 204
    assert istemci.get(YAYIN, headers=okul["baslik"]).json() is None
    assert istemci.delete(YAYIN, headers=okul["baslik"]).status_code == 404
