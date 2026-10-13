"""Sabit tohumlu test veri seti üretici (gerçekçi ve büyük setler).

Gerçek okul verisi gelene kadar çözücüyü gerçekçi büyüklükte veriyle sınamak için kullanılır.
Aynı ayar ve tohum her zaman aynı seti üretir.

Çözüm garantisi ("gizli program" yöntemi):
1. Sınıflar ve müfredat kurulur, dersler branş öğretmenlerine yük hedeflerine göre dağıtılır.
2. Bazı öğretmenlere tam gün izin (gelemez) verilir.
3. Yalnızca zorunlu kısıtlarla bir program çözülür: bu "gizli program"dır. Tek iş parçacığı ve
   sabit tohum kullanılır, böylece sonuç tekrarlanabilir.
4. Ek gelemez saatleri yalnızca öğretmenin gizli programda boş olduğu saatlerden seçilir. Böylece
   gizli program geçerli kalır ve set kesinlikle çözülebilir olur. Tercih etmez saatleri esnek
   olduğu için dolu saatlere de düşebilir; çözücünün uğraşacağı bir şey olsun diye bu kasıtlıdır.
5. Gizli program son veriyle bağımsız doğrulayıcıdan geçirilir. Geçmezse üretici hata verir.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field, replace

from cozucu.cpsat import CpSatCozucu
from cozucu.dogrulama import dogrula
from cozucu.kisitlar import VARSAYILAN_KISITLAR
from cozucu.model import (
    CozumGirdisi,
    Ders,
    DersAtama,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Ogretmen,
    Sinif,
    Yerlesim,
)
from cozucu.on_kontrol import on_kontrol

# kısa ad -> (ders adı, branş). Branş, dersi hangi öğretmen grubunun verdiğini belirler.
DERSLER: dict[str, tuple[str, str]] = {
    "TDE": ("Türk Dili ve Edebiyatı", "Edebiyat"),
    "MAT": ("Matematik", "Matematik"),
    "FIZ": ("Fizik", "Fizik"),
    "KIM": ("Kimya", "Kimya"),
    "BIY": ("Biyoloji", "Biyoloji"),
    "TAR": ("Tarih", "Tarih"),
    "INK": ("T.C. İnkılap Tarihi ve Atatürkçülük", "Tarih"),
    "COG": ("Coğrafya", "Coğrafya"),
    "FEL": ("Felsefe", "Felsefe"),
    "DIN": ("Din Kültürü ve Ahlak Bilgisi", "Din Kültürü"),
    "ING": ("İngilizce", "İngilizce"),
    "ALM": ("Almanca", "Almanca"),
    "BED": ("Beden Eğitimi ve Spor", "Beden Eğitimi"),
    "GOR": ("Görsel Sanatlar", "Sanat"),
    "MUZ": ("Müzik", "Sanat"),
    "REH": ("Rehberlik ve Yönlendirme", "Rehberlik"),
    "SEC": ("Seçmeli Ders", "Seçmeli"),
}

# Seviye -> [(ders, haftalık saat)]. MEB lise çizelgesine yakın; 9-10: 40 saat, 11-12: 38 saat.
MUFREDAT: dict[int, list[tuple[str, int]]] = {
    9: [("TDE", 5), ("MAT", 6), ("FIZ", 2), ("KIM", 2), ("BIY", 2), ("TAR", 2), ("COG", 2),
        ("DIN", 2), ("ING", 4), ("ALM", 2), ("BED", 2), ("GOR", 1), ("MUZ", 1), ("REH", 1), ("SEC", 6)],
    10: [("TDE", 5), ("MAT", 6), ("FIZ", 2), ("KIM", 2), ("BIY", 2), ("TAR", 2), ("COG", 2), ("FEL", 2),
         ("DIN", 2), ("ING", 4), ("ALM", 2), ("BED", 2), ("GOR", 1), ("MUZ", 1), ("REH", 1), ("SEC", 4)],
    11: [("TDE", 5), ("MAT", 6), ("FIZ", 4), ("KIM", 4), ("BIY", 4), ("TAR", 2), ("FEL", 2),
         ("DIN", 2), ("ING", 4), ("BED", 2), ("REH", 1), ("SEC", 2)],
    12: [("TDE", 5), ("MAT", 6), ("FIZ", 4), ("KIM", 4), ("BIY", 4), ("INK", 2), ("COG", 2),
         ("DIN", 2), ("ING", 4), ("BED", 2), ("REH", 1), ("SEC", 2)],
}

_ADLAR = ("Ayşe Fatma Zeynep Elif Emine Hatice Merve Esra Büşra Selin Derya Gül Seda Özlem Aslı "
          "Mehmet Ali Mustafa Ahmet Hüseyin Hasan İbrahim Murat Emre Burak Oğuz Kemal Serkan Volkan Can").split()
_SOYADLAR = ("Yılmaz Kaya Demir Şahin Çelik Yıldız Yıldırım Öztürk Aydın Özdemir Arslan Doğan Kılıç "
             "Aslan Çetin Kara Koç Kurt Özkan Şimşek Polat Korkmaz Erdoğan Güneş Aksoy Tekin Uçar").split()


@dataclass(frozen=True)
class UreticiAyari:
    seviye_sube: dict[int, int]  # seviye -> şube sayısı
    gun_sayisi: int = 5
    gunluk_ders_saati: int = 8
    yuk_araligi: tuple[int, int] = (15, 30)  # öğretmen haftalık ders saati
    tam_gun_izin_orani: float = 0.25  # bir gün hiç gelemeyen öğretmen oranı
    gelemez_orani: float = 0.35  # ek gelemez saati olan öğretmen oranı
    tercih_etmez_orani: float = 0.35  # tercih etmez saati olan öğretmen oranı
    gizli_cozum_suresi_sn: float = 300.0
    kisitlar: list[KisitTanimi] = field(default_factory=list, hash=False)


GERCEKCI = UreticiAyari(seviye_sube={9: 6, 10: 6, 11: 6, 12: 6})  # 24 şube
BUYUK = UreticiAyari(seviye_sube={9: 10, 10: 10, 11: 10, 12: 10})  # 40 şube


class UretimHatasi(Exception):
    pass


def uret(ayar: UreticiAyari, tohum: int) -> tuple[CozumGirdisi, list[Yerlesim]]:
    """(veri seti, gizli program) döner. Gizli program, setin çözülebilir olduğunun kanıtıdır."""
    rnd = random.Random(tohum)
    siniflar, atamalar_tasla = _siniflar_ve_dersler(ayar)
    ogretmenler, atamalar = _ogretmen_ata(ayar, atamalar_tasla, rnd)
    okul = OkulAyari(ayar.gun_sayisi, ayar.gunluk_ders_saati)
    dersler = [Ders(f"d-{k.lower()}", ad, k) for k, (ad, _b) in DERSLER.items()]

    # Tam gün izin: yükü kalan günlere sığan öğretmenlerden seçilir (günde en fazla 6 saat
    # varsayımıyla, böylece pencere ve boş gün kuralları için de makul kalır).
    yuk = _yukler(atamalar)
    musaitlikler: list[Musaitlik] = []
    for o in ogretmenler:
        if yuk[o.id] <= (ayar.gun_sayisi - 1) * 6 and rnd.random() < ayar.tam_gun_izin_orani:
            gun = rnd.randrange(ayar.gun_sayisi)
            musaitlikler += [Musaitlik(o.id, gun, s, MusaitlikDurumu.GELEMEZ) for s in range(ayar.gunluk_ders_saati)]

    taslak = CozumGirdisi(
        ayar=okul, ogretmenler=ogretmenler, siniflar=siniflar, dersler=dersler,
        atamalar=atamalar, musaitlikler=musaitlikler,
        kisitlar=[KisitTanimi(t.tur, t.parametreler, zorunlu=False, agirlik=0)
                  for t in VARSAYILAN_KISITLAR if not t.zorunlu],  # yalnızca zorunlu kısıtlar
    )
    sorunlar = on_kontrol(taslak)
    if sorunlar:
        raise UretimHatasi(f"Taslak ön kontrolden geçmedi: {sorunlar[0].mesaj}")
    gizli = CpSatCozucu(is_parcacigi=1, tohum=tohum).coz(taslak, ayar.gizli_cozum_suresi_sn)
    if not gizli.basarili:
        raise UretimHatasi(f"Gizli program bulunamadı ({gizli.durum.value}); başka bir tohum deneyin.")

    musaitlikler += _ek_musaitlikler(ayar, ogretmenler, atamalar, gizli.yerlesimler, musaitlikler, rnd)
    girdi = replace(taslak, musaitlikler=musaitlikler, kisitlar=list(ayar.kisitlar))
    hatalar = dogrula(girdi, gizli.yerlesimler)
    if hatalar:
        raise UretimHatasi(f"Gizli program son veriyle geçersiz: {hatalar[0]}")
    return girdi, gizli.yerlesimler


def _siniflar_ve_dersler(ayar: UreticiAyari) -> tuple[list[Sinif], list[tuple[str, str, int]]]:
    siniflar, atamalar = [], []
    for seviye, adet in sorted(ayar.seviye_sube.items()):
        for i in range(adet):
            harf = "ABCDEFGHIJKLMNOPRSTU"[i]
            sinif_id = f"s-{seviye}{harf.lower()}"
            siniflar.append(Sinif(sinif_id, f"{seviye}-{harf}", seviye))
            atamalar += [(sinif_id, ders, saat) for ders, saat in MUFREDAT[seviye]]
    return siniflar, atamalar


def _ogretmen_ata(
    ayar: UreticiAyari, tasla: list[tuple[str, str, int]], rnd: random.Random
) -> tuple[list[Ogretmen], list[DersAtama]]:
    """Her branşın derslerini, rastgele yük hedefleri (15-30) olan öğretmenlere dağıtır."""
    alt, ust = ayar.yuk_araligi
    brans_dersleri: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for sinif_id, ders, saat in tasla:
        brans_dersleri[DERSLER[ders][1]].append((sinif_id, ders, saat))

    adlar = _ad_uretici(rnd)
    ogretmenler: list[Ogretmen] = []
    atamalar: list[DersAtama] = []
    for brans in sorted(brans_dersleri):
        isler = sorted(brans_dersleri[brans], key=lambda x: (-x[2], x[0], x[1]))
        toplam = sum(s for *_x, s in isler)
        for _deneme in range(200):
            hedefler = []
            while sum(hedefler) < toplam:
                hedefler.append(rnd.randint(alt, ust))
            yukler = [0] * len(hedefler)
            dagilim: list[list[tuple[str, str, int]]] = [[] for _ in hedefler]
            for is_ in isler:
                i = max(range(len(hedefler)), key=lambda k: (hedefler[k] - yukler[k], -k))
                yukler[i] += is_[2]
                dagilim[i].append(is_)
            if all(alt <= y <= ust for y in yukler) or (len(yukler) == 1 and yukler[0] <= ust):
                break
        else:
            raise UretimHatasi(f"{brans} branşında yükler {alt}-{ust} aralığına dağıtılamadı")
        for liste in dagilim:
            o = Ogretmen(f"o-{len(ogretmenler) + 1:03d}", next(adlar), brans)
            ogretmenler.append(o)
            atamalar += [DersAtama(f"a-{s}-{d.lower()}", s, f"d-{d.lower()}", o.id, saat) for s, d, saat in liste]
    return ogretmenler, atamalar


def _ek_musaitlikler(ayar, ogretmenler, atamalar, gizli, mevcut, rnd) -> list[Musaitlik]:
    """Gelemez: yalnızca gizli programda boş saatlerden. Tercih etmez: herhangi bir saat."""
    atama = {a.id: a for a in atamalar}
    dolu: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for y in gizli:
        dolu[atama[y.ders_atama_id].ogretmen_id].add((y.gun, y.saat))
    zaten_gelemez = {(m.ogretmen_id, m.gun, m.saat) for m in mevcut}
    son_saatler = range(ayar.gunluk_ders_saati - 3, ayar.gunluk_ders_saati)
    ilk_saatler = range(0, 3)

    eklenen: list[Musaitlik] = []
    for o in ogretmenler:
        if rnd.random() < ayar.gelemez_orani:
            # Gerçekçi desen: belirli günlerde ilk ya da son saatlere gelemez (2-6 saat).
            adaylar = [
                (g, s)
                for g in range(ayar.gun_sayisi)
                for s in (ilk_saatler if rnd.random() < 0.5 else son_saatler)
                if (g, s) not in dolu[o.id] and (o.id, g, s) not in zaten_gelemez
            ]
            for g, s in rnd.sample(adaylar, min(len(adaylar), rnd.randint(2, 6))):
                eklenen.append(Musaitlik(o.id, g, s, MusaitlikDurumu.GELEMEZ))
        if rnd.random() < ayar.tercih_etmez_orani:
            gun = rnd.randrange(ayar.gun_sayisi)
            saatler = son_saatler if rnd.random() < 0.6 else ilk_saatler
            for s in saatler:
                if (o.id, gun, s) not in zaten_gelemez:
                    eklenen.append(Musaitlik(o.id, gun, s, MusaitlikDurumu.TERCIH_ETMEZ))
    # Aynı hücre için hem gelemez hem tercih etmez olmasın: gelemez öncelikli.
    gelemez = {(m.ogretmen_id, m.gun, m.saat) for m in eklenen if m.durum is MusaitlikDurumu.GELEMEZ}
    return [m for m in eklenen if m.durum is MusaitlikDurumu.GELEMEZ or (m.ogretmen_id, m.gun, m.saat) not in gelemez]


def _yukler(atamalar: list[DersAtama]) -> dict[str, int]:
    yuk: dict[str, int] = defaultdict(int)
    for a in atamalar:
        if a.ogretmen_id is not None:
            yuk[a.ogretmen_id] += a.haftalik_saat
    return yuk


def _ad_uretici(rnd: random.Random):
    kullanilan: set[str] = set()
    while True:
        ad = f"{rnd.choice(_ADLAR)} {rnd.choice(_SOYADLAR)}"
        if ad not in kullanilan:
            kullanilan.add(ad)
            yield ad


def main(argv: list[str] | None = None) -> None:
    import argparse
    import time

    from cozucu.veri_io import girdi_yaz

    p = argparse.ArgumentParser(description="Test veri seti üretir.")
    p.add_argument("tur", choices=["gercekci", "buyuk"])
    p.add_argument("cikti")
    p.add_argument("--tohum", type=int, default=1)
    a = p.parse_args(argv)
    baslangic = time.perf_counter()
    girdi, gizli = uret(GERCEKCI if a.tur == "gercekci" else BUYUK, a.tohum)
    girdi_yaz(girdi, a.cikti)
    yuk = _yukler(girdi.atamalar)
    print(
        f"{a.cikti}: {len(girdi.siniflar)} şube, {len(girdi.ogretmenler)} öğretmen, "
        f"{len(girdi.atamalar)} atama, {sum(x.haftalik_saat for x in girdi.atamalar)} ders saati, "
        f"yük {min(yuk.values())}-{max(yuk.values())}, {len(girdi.musaitlikler)} müsaitlik kaydı, "
        f"{time.perf_counter() - baslangic:.1f} sn"
    )


if __name__ == "__main__":
    main()
