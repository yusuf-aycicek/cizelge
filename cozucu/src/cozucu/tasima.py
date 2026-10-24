"""Elle düzeltme (7.1): bir dersi başka bir saate taşımanın değerlendirilmesi.

Kararı bağımsız doğrulayıcı (`dogrulama.ihlaller`) ve kalite ölçümü (`kalite.olc`) verir; çözücü
modeli kullanılmaz. Kurallar:

- **Blok bütün taşınır:** dağılım şekli olan dersin aynı gündeki kesintisiz saatleri (öğle arasıyla
  ayrılmayan) birlikte taşınır; şekli olmayan ders tek saat taşınır.
- **Yer değiştirme:** hedef saatlerde aynı şubenin başka dersi varsa o ders, taşınan dersin boşalttığı
  saatlere geçer (takas). Dolu bir okulda boş hücre azdır; takas olmadan neredeyse hiçbir taşıma
  yapılamıyordu (gerçekçi sette 40 dersin 38'inin geçerli hedefi yoktu). Takas edilen dersin bloğu
  bölünürse ya da öğretmeni o saatte doluysa doğrulayıcı yakalar.
- **Kilitli ders taşınmaz.**
- **Engel:** taşıma, programda önceden olmayan bir zorunlu kısıt ihlali doğuruyorsa (öğretmen ya da
  şube çakışması, gelemez, günlük sınırlar, blok, öğle arası, haftanın dışı). Yalnızca **yeni**
  ihlallere bakılır: veriler program üretildikten sonra değiştiyse programda zaten ihlal olabilir,
  bu taşımayı engellememeli.
- **Uyarı:** zorunlu kurallar sağlanıyor ama ağırlığı 0'dan büyük bir esnek ölçü kötüleşiyor
  (ör. öğretmen penceresi 3 → 5). Kullanıcı onaylarsa yapılır.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cozucu.anlatim import Anlatim
from cozucu.blok import BlokHesabi
from cozucu.dogrulama import Ihlal, ihlaller
from cozucu.kalite import OLCU_KURAL_TURU, KaliteOlcumu, olc
from cozucu.kisitlar import etkin_agirliklar
from cozucu.model import CozumGirdisi, Yerlesim

UYGUN, UYARI, ENGEL = "uygun", "uyari", "engel"

# Esnek ölçülerin kullanıcı dilindeki adları (uyarı metni: "Öğretmenlerin pencere saati 3 → 5").
OLCU_ADLARI = {
    "sinif_boslugu": "Sınıfların boş saati",
    "ogretmen_penceresi": "Öğretmenlerin pencere saati",
    "bolunmus_ders": "Bölünmüş ders",
    "tercih_etmez": "Tercih edilmeyen saate konan ders",
    "eksik_bos_gun": "Eksik boş gün",
    "fazla_bos_gun": "Hedeften fazla boş gün",
    "degisen_yerlesim": "Temel programdan değişen ders saati",
}


class TasimaHatasi(ValueError):
    """İstek anlamsız: kaynak hücrede bu ders yok."""


@dataclass(frozen=True)
class Degerlendirme:
    gun: int
    saat: int
    durum: str
    nedenler: tuple[str, ...]
    hucreler: tuple[tuple[int, int], ...] = ()
    olcum: KaliteOlcumu | None = field(default=None, compare=False)
    # Bütün hareketler (taşınan ders ve takas edilenler) ve takas edilen derslerin adları.
    hareketler: tuple[Hareket, ...] = field(default=(), compare=False)
    takas: tuple[str, ...] = ()


def blok_hucreleri(girdi: CozumGirdisi, yerlesimler: list[Yerlesim], atama_id: str, gun: int, saat: int) -> list[tuple[int, int]]:
    """Kaynak hücreyle birlikte taşınacak hücreler (gün, saat), saat sırasıyla."""
    saatler = {y.saat for y in yerlesimler if y.ders_atama_id == atama_id and y.gun == gun}
    if saat not in saatler:
        raise TasimaHatasi("Bu hücrede bu ders yok")
    atama = next((a for a in girdi.atamalar if a.id == atama_id), None)
    if atama is None or BlokHesabi(girdi).desen(atama) is None:
        return [(gun, saat)]
    ayrilir = girdi.ayar.ogle_arasiyla_ayrilir
    bas = saat
    while bas - 1 in saatler and not ayrilir(gun, bas - 1):
        bas -= 1
    son = saat
    while son + 1 in saatler and not ayrilir(gun, son):
        son += 1
    return [(gun, s) for s in range(bas, son + 1)]


@dataclass(frozen=True)
class Hareket:
    """Bir atamanın hücrelerinin yer değiştirmesi (taşınan ders ya da takas edilen ders)."""

    ders_atama_id: str
    eski: tuple[tuple[int, int], ...]
    yeni: tuple[tuple[int, int], ...]


def hareketler(girdi: CozumGirdisi, yerlesimler: list[Yerlesim], atama_id: str, hucreler: list[tuple[int, int]],
               hedef_gun: int, hedef_saat: int) -> list[Hareket]:
    """Taşımanın bütün hareketleri: önce taşınan ders, sonra hedefte duran aynı şube dersleri.

    Hedefte duran ders boşalan saatlere geçer: hedef ile kaynak örtüşmüyorsa aynı konuma (hedefin
    i. saatindeki ders kaynağın i. saatine), örtüşüyorsa (aynı günde kaydırma) sırayla boşalan saatlere.
    """
    hedef = [(hedef_gun, hedef_saat + i) for i in range(len(hucreler))]
    sinif = {a.id: a.sinif_id for a in girdi.atamalar}
    bu_sinif = sinif.get(atama_id)
    kaynak = set(hucreler)
    duranlar = sorted(
        ((y.gun, y.saat), y.ders_atama_id) for y in yerlesimler
        if (y.gun, y.saat) in set(hedef) and y.ders_atama_id != atama_id and sinif.get(y.ders_atama_id) == bu_sinif
    )
    sonuc = [Hareket(atama_id, tuple(hucreler), tuple(hedef))]
    if not duranlar:
        return sonuc
    if kaynak & set(hedef):
        bosalan = sorted(kaynak - set(hedef))
        eslesme = dict(zip([h for h, _a in duranlar], bosalan))
    else:
        eslesme = {h: hucreler[hedef.index(h)] for h, _a in duranlar}
    atamalara: dict[str, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
    for h, a in duranlar:
        atamalara.setdefault(a, []).append((h, eslesme[h]))
    sonuc += [Hareket(a, tuple(e for e, _y in ciftler), tuple(y for _e, y in ciftler)) for a, ciftler in atamalara.items()]
    return sonuc


def uygula(yerlesimler: list[Yerlesim], hareketler_: list[Hareket]) -> list[Yerlesim]:
    """Hareketleri yerleşim listesine uygular (kilit bilgisi hareket eden hücrelerde kalkar). Yeni liste döner."""
    kalkan = {(h.ders_atama_id, g, s) for h in hareketler_ for g, s in h.eski}
    kalan = [y for y in yerlesimler if (y.ders_atama_id, y.gun, y.saat) not in kalkan]
    return kalan + [Yerlesim(h.ders_atama_id, g, s) for h in hareketler_ for g, s in h.yeni]


def tasi(yerlesimler: list[Yerlesim], atama_id: str, hucreler: list[tuple[int, int]], hedef_gun: int, hedef_saat: int) -> list[Yerlesim]:
    """Takassız kaydırma: bloğun ilk saati `hedef_saat`e gelir. Yeni liste döner."""
    return uygula(yerlesimler, [Hareket(atama_id, tuple(hucreler), tuple((hedef_gun, hedef_saat + i) for i in range(len(hucreler))))])


class Degerlendirici:
    """Bir programın bir dersini taşımayı değerlendirir. Programın önceki ihlalleri ve ölçümü bir kez hesaplanır."""

    def __init__(self, girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> None:
        self.girdi = girdi
        self.yerlesimler = yerlesimler
        self.bloklar = BlokHesabi(girdi)
        self.onceki: set[tuple] = {i.anahtar for i in ihlaller(girdi, yerlesimler, self.bloklar)}
        self.olcum = olc(girdi, yerlesimler)
        self.agirliklar = etkin_agirliklar(girdi)
        self.ad = Anlatim(girdi)

    def degerlendir(self, atama_id: str, gun: int, saat: int, hedef_gun: int, hedef_saat: int,
                    hucreler: list[tuple[int, int]] | None = None) -> Degerlendirme:
        hucreler = hucreler or blok_hucreleri(self.girdi, self.yerlesimler, atama_id, gun, saat)
        hedef = tuple((hedef_gun, hedef_saat + i) for i in range(len(hucreler)))
        hepsi = hareketler(self.girdi, self.yerlesimler, atama_id, hucreler, hedef_gun, hedef_saat)
        takas = tuple(dict.fromkeys(self.ad.atama(h.ders_atama_id) for h in hepsi[1:]))
        kilitli = {(y.ders_atama_id, y.gun, y.saat) for y in self.yerlesimler if y.kilitli}
        for h in hepsi:
            if any((h.ders_atama_id, g, s) in kilitli for g, s in h.eski):
                neden = "taşımak için önce kilidi açın" if h.ders_atama_id == atama_id else "yer değiştiremez"
                return Degerlendirme(hedef_gun, hedef_saat, ENGEL, (f"{self.ad.atama(h.ders_atama_id)} kilitli; {neden}",), hedef)
        yeni = uygula(self.yerlesimler, hepsi)
        yeni_ihlaller: list[Ihlal] = [i for i in ihlaller(self.girdi, yeni, self.bloklar) if i.anahtar not in self.onceki]
        if yeni_ihlaller:
            return Degerlendirme(hedef_gun, hedef_saat, ENGEL, tuple(dict.fromkeys(i.mesaj for i in yeni_ihlaller)), hedef)
        sonra = olc(self.girdi, yeni)
        uyarilar = tuple(
            f"{OLCU_ADLARI[alan]} {getattr(self.olcum, alan)} → {getattr(sonra, alan)}"
            for alan, tur in OLCU_KURAL_TURU.items()
            if self.agirliklar.get(tur, 0) > 0 and getattr(sonra, alan) > getattr(self.olcum, alan)
        )
        return Degerlendirme(hedef_gun, hedef_saat, UYARI if uyarilar else UYGUN, uyarilar, hedef, sonra, tuple(hepsi), takas)

    def harita(self, atama_id: str, gun: int, saat: int) -> list[Degerlendirme]:
        """Bloğun sığdığı her başlangıç hücresi için değerlendirme (kendi yeri hariç)."""
        hucreler = blok_hucreleri(self.girdi, self.yerlesimler, atama_id, gun, saat)
        ayar = self.girdi.ayar
        sonuc = []
        for g in range(ayar.gun_sayisi):
            for s in range(ayar.saat_sayisi(g)):
                if (g, s) == hucreler[0] or not all(ayar.aralikta(g, s + i) for i in range(len(hucreler))):
                    continue
                sonuc.append(self.degerlendir(atama_id, gun, saat, g, s, hucreler))
        return sonuc
