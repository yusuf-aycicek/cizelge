"""Elle düzeltme (7.1): taşıma haritası, taşıma (engel / uyarı / onay), kilit, geri alma, kalite.

Karar çözücü paketinin bağımsız doğrulayıcısından gelir (cozucu/tests/test_tasima.py); burada API'nin
onu doğru uyguladığı, veritabanına doğru yazdığı ve okul izolasyonu denetlenir.
"""

from __future__ import annotations

import uuid

import pytest
from cozucu import dogrula
from cozucu.model import Yerlesim as CYerlesim

from conftest import DP, okul_basligi
from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from test_program_uretimi import getir, okul, uret, worker_calistir  # noqa: F401  (okul: fikstür)


@pytest.fixture
def hazir_program(istemci, okul, kuyruk, oturum_fabrikasi):
    p = uret(istemci, okul, ad="Eylül").json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, p)
    return p


def yerlesimler(istemci, okul, p) -> set[tuple[str, int, int, bool]]:
    return {(y["ders_atama_id"], y["gun"], y["saat"], y["kilitli"])
            for y in istemci.get(f"{DP}/programlar/{p}/yerlesimler", headers=okul["baslik"]).json()}


def ilk_hucre(istemci, okul, p, atama_id) -> tuple[int, int]:
    return min((g, s) for a, g, s, _k in yerlesimler(istemci, okul, p) if a == atama_id)


def harita(istemci, okul, p, atama_id, gun, saat):
    yanit = istemci.get(f"{DP}/programlar/{p}/tasima", params={"ders_atama_id": atama_id, "gun": gun, "saat": saat},
                        headers=okul["baslik"])
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def tasi(istemci, okul, p, atama_id, kaynak, hedef, kabul=False):
    return istemci.post(f"{DP}/programlar/{p}/tasi", headers=okul["baslik"], json={
        "ders_atama_id": atama_id, "gun": kaynak[0], "saat": kaynak[1], "hedef_gun": hedef[0], "hedef_saat": hedef[1],
        "uyarilari_kabul": kabul})


def program_gecerli(oturum_fabrikasi, okul, istemci, p) -> bool:
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        girdi = cozum_girdisi_olustur(o)
    return dogrula(girdi, [CYerlesim(a, g, s, k) for a, g, s, k in yerlesimler(istemci, okul, p)]) == []


def test_harita_blogu_ve_her_hedefin_durumunu_kullanici_diliyle_verir(istemci, okul, hazir_program):
    mat = okul["harita"]["a-9a-mat"]  # 6 saat: 2+2+2
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    h = harita(istemci, okul, hazir_program, mat, g, s)
    assert len(h["hucreler"]) == 2
    durumlar = {x["durum"] for x in h["hedefler"]}
    assert "engel" in durumlar and durumlar <= {"uygun", "uyari", "engel"}
    nedenler = [n for x in h["hedefler"] for n in x["nedenler"]]
    assert nedenler and not any(okul["harita"]["o-ayse"] in n or mat in n for n in nedenler)  # kimlik değil ad
    assert any("9-A" in n for n in nedenler)


def test_zorunlu_kurali_cigneyen_tasima_engellenir_program_degismez(istemci, okul, hazir_program):
    mat = okul["harita"]["a-9a-mat"]
    kaynak = ilk_hucre(istemci, okul, hazir_program, mat)
    once = yerlesimler(istemci, okul, hazir_program)
    engel = next(x for x in harita(istemci, okul, hazir_program, mat, *kaynak)["hedefler"] if x["durum"] == "engel")
    yanit = tasi(istemci, okul, hazir_program, mat, kaynak, (engel["gun"], engel["saat"]), kabul=True)
    assert yanit.status_code == 422 and yanit.json()["detail"].startswith("Bu taşıma yapılamaz: ")
    assert engel["nedenler"][0] in yanit.json()["detail"]
    assert yerlesimler(istemci, okul, hazir_program) == once
    assert getir(istemci, okul, hazir_program)["elle_duzeltme"] == 0


def test_tasima_blogu_butun_tasir_kaliteyi_gunceller_ve_geri_alinir(istemci, okul, hazir_program, oturum_fabrikasi):
    b = okul["baslik"]
    once, olcum_once = yerlesimler(istemci, okul, hazir_program), getir(istemci, okul, hazir_program)["olcumler"]
    # Çözücünün her üretimi farklı olabilir: taşınabilir (engelsiz hedefi olan) iki saatlik bir blok aranır.
    secim = None
    for a, g, s, _k in sorted(once):
        h = harita(istemci, okul, hazir_program, a, g, s)
        hedef = next((x for x in h["hedefler"] if x["durum"] != "engel" and not x["takas"]), None)
        if len(h["hucreler"]) == 2 and hedef:
            secim = a, (h["hucreler"][0]["gun"], h["hucreler"][0]["saat"]), hedef
            break
    assert secim, "mini sette takassız taşınabilen bir blok bulunmalı"
    mat, kaynak, hedef = secim

    if hedef["durum"] == "uyari":
        yanit = tasi(istemci, okul, hazir_program, mat, kaynak, (hedef["gun"], hedef["saat"]))
        assert yanit.status_code == 409 and "kötüleştiriyor" in yanit.json()["detail"]
    yanit = tasi(istemci, okul, hazir_program, mat, kaynak, (hedef["gun"], hedef["saat"]), kabul=True)
    assert yanit.status_code == 200, yanit.text
    sonra = yerlesimler(istemci, okul, hazir_program)
    assert {(g, s) for a, g, s, _k in sonra - once if a == mat} == {(hedef["gun"], hedef["saat"]), (hedef["gun"], hedef["saat"] + 1)}
    assert len({x for x in once - sonra if x[0] == mat}) == 2  # bloğun iki saati birlikte
    assert program_gecerli(oturum_fabrikasi, okul, istemci, hazir_program)
    p = yanit.json()
    assert p["elle_duzeltme"] == 1
    if hedef["durum"] == "uyari":
        assert p["olcumler"] != olcum_once

    yanit = istemci.post(f"{DP}/programlar/{hazir_program}/geri-al", headers=b)
    assert yanit.status_code == 200 and yanit.json()["elle_duzeltme"] == 0
    assert yerlesimler(istemci, okul, hazir_program) == once
    assert yanit.json()["olcumler"] == olcum_once
    yanit = istemci.post(f"{DP}/programlar/{hazir_program}/geri-al", headers=b)
    assert yanit.status_code == 409 and yanit.json()["detail"] == "Geri alınacak bir değişiklik yok"


def test_kilitli_ders_tasinamaz_kilit_geri_alinir(istemci, okul, hazir_program):
    b, mat = okul["baslik"], okul["harita"]["a-9a-mat"]
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    yanit = istemci.put(f"{DP}/programlar/{hazir_program}/kilit", headers=b,
                        json={"ders_atama_id": mat, "gun": g, "saat": s + 1, "kilitli": True})
    assert yanit.status_code == 200 and yanit.json()["elle_duzeltme"] == 1
    kilitli = {(a, gg, ss) for a, gg, ss, k in yerlesimler(istemci, okul, hazir_program) if k}
    assert kilitli == {(mat, g, s), (mat, g, s + 1)}  # bloğun ikinci saatinden kilitlense de bütün blok
    # Aynı duruma ikinci kilit işlem yazmaz.
    istemci.put(f"{DP}/programlar/{hazir_program}/kilit", headers=b, json={"ders_atama_id": mat, "gun": g, "saat": s, "kilitli": True})
    assert getir(istemci, okul, hazir_program)["elle_duzeltme"] == 1

    hedefler = harita(istemci, okul, hazir_program, mat, g, s)["hedefler"]
    assert all(x["durum"] == "engel" and "kilitli" in x["nedenler"][0] for x in hedefler)
    hedef = hedefler[0]
    yanit = tasi(istemci, okul, hazir_program, mat, (g, s), (hedef["gun"], hedef["saat"]), kabul=True)
    assert yanit.status_code == 422 and "önce kilidi açın" in yanit.json()["detail"]

    assert istemci.post(f"{DP}/programlar/{hazir_program}/geri-al", headers=b).status_code == 200
    assert not any(k for *_x, k in yerlesimler(istemci, okul, hazir_program))


def test_kilitli_ders_temel_alinarak_uretilen_programda_yerinde_kalir(istemci, okul, hazir_program, kuyruk, oturum_fabrikasi):
    b, h = okul["baslik"], okul["harita"]
    mat = h["a-9a-mat"]
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    istemci.put(f"{DP}/programlar/{hazir_program}/kilit", headers=b, json={"ders_atama_id": mat, "gun": g, "saat": s, "kilitli": True})
    # Ayşe'nin o gün başka bir saatte gelemez olması programı değiştirmeye zorlasa da kilitli blok kalır.
    p2 = uret(istemci, okul, ad="Ekim", temel_program_id=hazir_program).json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, p2)
    assert {(mat, g, s), (mat, g, s + 1)} <= {(a, gg, ss) for a, gg, ss, _k in yerlesimler(istemci, okul, p2)}


def test_yalnizca_hazir_program_ve_kaynakta_ders_olmali(istemci, okul, hazir_program):
    b, mat = okul["baslik"], okul["harita"]["a-9a-mat"]
    bekleyen = uret(istemci, okul, ad="Bekleyen").json()["id"]
    yanit = tasi(istemci, okul, bekleyen, mat, (0, 0), (1, 0))
    assert yanit.status_code == 422 and "hazır" in yanit.json()["detail"]
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    bos = next((gg, ss) for gg in range(5) for ss in range(6)
               if (gg, ss) not in {(x[1], x[2]) for x in yerlesimler(istemci, okul, hazir_program) if x[0] == mat})
    yanit = tasi(istemci, okul, hazir_program, mat, bos, (g, s))
    assert yanit.status_code == 422 and yanit.json()["detail"] == "Bu hücrede bu ders yok"


def test_baska_okul_elle_duzeltemez(istemci, okul, hazir_program, okul_olustur):
    b2 = okul_basligi(okul_olustur("Başka Lise"))
    mat = okul["harita"]["a-9a-mat"]
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    p = hazir_program
    assert istemci.get(f"{DP}/programlar/{p}/tasima", params={"ders_atama_id": mat, "gun": g, "saat": s}, headers=b2).status_code == 404
    assert istemci.post(f"{DP}/programlar/{p}/tasi", headers=b2, json={
        "ders_atama_id": mat, "gun": g, "saat": s, "hedef_gun": 4, "hedef_saat": 4, "uyarilari_kabul": True}).status_code == 404
    assert istemci.put(f"{DP}/programlar/{p}/kilit", headers=b2,
                       json={"ders_atama_id": mat, "gun": g, "saat": s, "kilitli": True}).status_code == 404
    assert istemci.post(f"{DP}/programlar/{p}/geri-al", headers=b2).status_code == 404
    assert not any(k for *_x, k in yerlesimler(istemci, okul, p))


def test_program_silinince_islemleri_de_silinir(istemci, okul, hazir_program, oturum_fabrikasi):
    from okulapi.moduller.ders_programi.modeller import ProgramIslemi
    from sqlalchemy import func, select

    b, mat = okul["baslik"], okul["harita"]["a-9a-mat"]
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    istemci.put(f"{DP}/programlar/{hazir_program}/kilit", headers=b, json={"ders_atama_id": mat, "gun": g, "saat": s, "kilitli": True})
    assert istemci.delete(f"{DP}/programlar/{hazir_program}", headers=b).status_code == 204
    with okul_oturumu(oturum_fabrikasi, okul["id"]) as o:
        assert o.scalar(select(func.count()).select_from(ProgramIslemi)) == 0
    assert uuid.UUID(hazir_program)


def test_takasli_tasima_iki_dersi_de_yer_degistirir_ve_geri_alinir(istemci, okul, hazir_program, oturum_fabrikasi):
    """Hedefte aynı şubenin dersi varsa yer değiştirir; geri alma ikisini de eski yerine koyar."""
    b = okul["baslik"]
    once = yerlesimler(istemci, okul, hazir_program)
    secim = None
    for a, g, s, _k in sorted(once):
        hedef = next((x for x in harita(istemci, okul, hazir_program, a, g, s)["hedefler"] if x["durum"] != "engel" and x["takas"]), None)
        if hedef:
            secim = (a, (g, s), hedef)
            break
    assert secim, "mini sette takaslı bir taşıma bulunmalı"
    a, kaynak, hedef = secim
    yanit = tasi(istemci, okul, hazir_program, a, kaynak, (hedef["gun"], hedef["saat"]), kabul=True)
    assert yanit.status_code == 200, yanit.text
    sonra = yerlesimler(istemci, okul, hazir_program)
    degisen_atamalar = {x[0] for x in once ^ sonra}
    assert len(degisen_atamalar) >= 2 and a in degisen_atamalar
    assert program_gecerli(oturum_fabrikasi, okul, istemci, hazir_program)
    assert istemci.post(f"{DP}/programlar/{hazir_program}/geri-al", headers=b).status_code == 200
    assert yerlesimler(istemci, okul, hazir_program) == once


def ilk_hedef(istemci, okul, p, kosul):
    """Programda koşula uyan ilk (ders, kaynak, hedef); yoksa None."""
    for a, g, s, _k in sorted(yerlesimler(istemci, okul, p)):
        hedef = next((x for x in harita(istemci, okul, p, a, g, s)["hedefler"] if kosul(x)), None)
        if hedef:
            return a, (g, s), hedef
    return None


def test_esnek_olcuyu_kotulestiren_tasima_onaysiz_409_onayla_yapilir(istemci, okul, hazir_program):
    a, kaynak, hedef = ilk_hedef(istemci, okul, hazir_program, lambda x: x["durum"] == "uyari")
    once = yerlesimler(istemci, okul, hazir_program)
    yanit = tasi(istemci, okul, hazir_program, a, kaynak, (hedef["gun"], hedef["saat"]))
    assert yanit.status_code == 409 and hedef["nedenler"][0] in yanit.json()["detail"]
    assert yerlesimler(istemci, okul, hazir_program) == once
    assert tasi(istemci, okul, hazir_program, a, kaynak, (hedef["gun"], hedef["saat"]), kabul=True).status_code == 200
    assert yerlesimler(istemci, okul, hazir_program) != once


def test_geri_alma_sondan_basa(istemci, okul, hazir_program):
    b = okul["baslik"]
    a, kaynak, hedef = ilk_hedef(istemci, okul, hazir_program, lambda x: x["durum"] != "engel")
    once = yerlesimler(istemci, okul, hazir_program)
    tasi(istemci, okul, hazir_program, a, kaynak, (hedef["gun"], hedef["saat"]), kabul=True)
    tasindi = yerlesimler(istemci, okul, hazir_program)
    istemci.put(f"{DP}/programlar/{hazir_program}/kilit", headers=b,
                json={"ders_atama_id": a, "gun": hedef["gun"], "saat": hedef["saat"], "kilitli": True})
    # İlk geri alma kilidi kaldırır, taşıma yerinde kalır; ikincisi taşımayı geri alır.
    istemci.post(f"{DP}/programlar/{hazir_program}/geri-al", headers=b)
    assert yerlesimler(istemci, okul, hazir_program) == tasindi
    istemci.post(f"{DP}/programlar/{hazir_program}/geri-al", headers=b)
    assert yerlesimler(istemci, okul, hazir_program) == once


def test_temel_programin_kilidi_turetilen_programda_kilit_acilinca_baglamaz(istemci, okul, hazir_program, kuyruk, oturum_fabrikasi):
    b, mat = okul["baslik"], okul["harita"]["a-9a-mat"]
    g, s = ilk_hucre(istemci, okul, hazir_program, mat)
    istemci.put(f"{DP}/programlar/{hazir_program}/kilit", headers=b, json={"ders_atama_id": mat, "gun": g, "saat": s, "kilitli": True})
    p2 = uret(istemci, okul, ad="Ekim", temel_program_id=hazir_program).json()["id"]
    worker_calistir(oturum_fabrikasi, kuyruk, p2)
    assert (mat, g, s, True) in yerlesimler(istemci, okul, p2)
    istemci.put(f"{DP}/programlar/{p2}/kilit", headers=b, json={"ders_atama_id": mat, "gun": g, "saat": s, "kilitli": False})
    nedenler = [n for x in harita(istemci, okul, p2, mat, g, s)["hedefler"] for n in x["nedenler"]]
    assert not any("kilitli" in n for n in nedenler)
