"""Testler için küçük yardımcılar."""

from cozucu import CozumGirdisi, Ders, Ogretmen, Sinif


def girdi_kur(**alanlar) -> CozumGirdisi:
    """Senaryo testleri için girdi. Atama ve müsaitliklerde geçen ama listelerde olmayan
    öğretmen, sınıf ve dersleri kimliğiyle aynı adla ekler; böylece senaryolar kısa kalır ve
    ön kontrolün tutarlılık denetiminden geçer.
    """
    girdi = CozumGirdisi(**alanlar)
    ogretmenler = {o.id for o in girdi.ogretmenler}
    siniflar = {s.id for s in girdi.siniflar}
    dersler = {d.id for d in girdi.dersler}
    for a in girdi.atamalar:
        if a.ogretmen_id is not None and a.ogretmen_id not in ogretmenler:
            girdi.ogretmenler.append(Ogretmen(a.ogretmen_id, a.ogretmen_id))
            ogretmenler.add(a.ogretmen_id)
        if a.sinif_id not in siniflar:
            girdi.siniflar.append(Sinif(a.sinif_id, a.sinif_id, seviye=9))
            siniflar.add(a.sinif_id)
        if a.ders_id not in dersler:
            girdi.dersler.append(Ders(a.ders_id, a.ders_id))
            dersler.add(a.ders_id)
    for m in girdi.musaitlikler:
        if m.ogretmen_id not in ogretmenler:
            girdi.ogretmenler.append(Ogretmen(m.ogretmen_id, m.ogretmen_id))
            ogretmenler.add(m.ogretmen_id)
    return girdi
