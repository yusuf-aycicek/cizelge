"""Ders programı modülünün API şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Yanit(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- seviye şablonu ------------------------------------------------------------------


class SeviyeSablonuOlustur(BaseModel):
    seviye: int = Field(ge=1, le=12)
    # Doluysa satır bu şube grubunun şablonundadır (seviye grubun seviyesi olmalı); boşsa seviyenin.
    sube_grubu_id: uuid.UUID | None = None
    ders_id: uuid.UUID
    haftalik_saat: int = Field(ge=1)


class SeviyeSablonuGuncelle(BaseModel):
    haftalik_saat: int | None = Field(default=None, ge=1)


class SeviyeSablonuYanit(_Yanit):
    id: uuid.UUID
    seviye: int
    sube_grubu_id: uuid.UUID | None
    ders_id: uuid.UUID
    haftalik_saat: int


class SablonUygula(BaseModel):
    seviye: int = Field(ge=1, le=12)
    # Verilirse grubun şablonu grubun şubelerine uygulanır; yoksa seviyenin şablonu.
    sube_grubu_id: uuid.UUID | None = None


class SablonSatiri(BaseModel):
    ders_id: uuid.UUID
    haftalik_saat: int = Field(ge=0, le=99, description="0: ders şablondan çıkar")


class SablonTopluKaydet(BaseModel):
    """Şablonun tamamı: listede olmayan ya da saati 0 olan ders şablondan çıkar."""

    seviye: int = Field(ge=1, le=12)
    sube_grubu_id: uuid.UUID | None = None
    satirlar: list[SablonSatiri] = Field(max_length=500)


class FarkliSaat(BaseModel):
    atama_id: uuid.UUID
    sinif: str
    ders: str
    atamadaki_saat: int
    sablondaki_saat: int


class IstisnaAtlanan(BaseModel):
    sinif: str
    ders: str


class IstisnaEk(BaseModel):
    sinif: str
    ders: str
    haftalik_saat: int
    eklendi: bool = Field(description="false: ders şubede zaten vardı")


class BaskaSablonlu(BaseModel):
    sinif: str
    sablon: str = Field(description="Şubenin kullandığı şablon: \"11 Sayısal\" ya da \"11. sınıflar\"")


class SablonUygulamaSonucu(BaseModel):
    """Şablon uygulandı: oluşturulan atamalar, zaten var olanlar, saati şablondan farklı olanlar,
    şube istisnaları (atlanan "almaz" dersleri, eklenen "ek" dersleri) ve bu seviyede başka bir
    şablonu kullandığı için dokunulmayan şubeler."""

    sube_sayisi: int
    subeler: list[str]
    olusturulan: int
    zaten_var: int
    farkli_saatli: list[FarkliSaat]
    istisna_atlanan: list[IstisnaAtlanan]
    istisna_ek: list[IstisnaEk]
    baska_sablonlu: list[BaskaSablonlu]


class SeviyeUygulamaRaporu(BaseModel):
    """"Tüm seviyelere uygula"da bir şablonun raporu."""

    seviye: int
    sube_grubu_id: uuid.UUID | None
    sablon: str = Field(description="Şablonun adı: \"9. sınıflar\" ya da şube grubunun adı")
    sonuc: SablonUygulamaSonucu


# --- şube istisnaları -------------------------------------------------------------------


class SubeIstisnasiOlustur(BaseModel):
    sinif_id: uuid.UUID
    ders_id: uuid.UUID
    tur: Literal["almaz", "ek"]
    haftalik_saat: int | None = Field(default=None, ge=1, description="Yalnızca \"ek\" için")


class SubeIstisnasiYanit(BaseModel):
    id: uuid.UUID
    sinif_id: uuid.UUID
    ders_id: uuid.UUID
    tur: Literal["almaz", "ek"]
    haftalik_saat: int | None
    sinif_adi: str
    ders_adi: str
    sablonda: bool = Field(description="Ders şubenin kullandığı şablonda var mı")
    atanmis: bool = Field(description="Şubeye bu ders atanmış mı")
    uyari: str | None = Field(description="İstisna ile ders dağılımı tutarsızsa açıklama (otomatik düzeltilmez)")


class IstisnaKaldirmaSonucu(BaseModel):
    geri_eklenen_saat: int | None = Field(
        description="\"Almaz\" kalkınca ders şablondan geri eklendiyse haftalık saati")


# --- ders atama -------------------------------------------------------------------------


class DersAtamaOlustur(BaseModel):
    sinif_id: uuid.UUID
    ders_id: uuid.UUID
    ogretmen_id: uuid.UUID | None = None
    haftalik_saat: int = Field(ge=1)


class DersAtamaGuncelle(BaseModel):
    """Sınıf ve ders değiştirilemez: (sınıf, ders) atamanın kimliğidir. Başka bir sınıf/ders için
    yeni atama oluşturulur. `ogretmen_id: null` göndermek öğretmeni boşaltır."""

    ogretmen_id: uuid.UUID | None = None
    haftalik_saat: int | None = Field(default=None, ge=1)


class DersAtamaYanit(_Yanit):
    id: uuid.UUID
    sinif_id: uuid.UUID
    ders_id: uuid.UUID
    ogretmen_id: uuid.UUID | None
    haftalik_saat: int


class TopluOgretmenAta(BaseModel):
    """Aynı öğretmeni birden fazla atamaya tek seferde verir (ör. 9-A, 9-B, 9-C Matematik).
    `ogretmen_id: null` hepsinin öğretmenini boşaltır."""

    atama_idleri: list[uuid.UUID] = Field(min_length=1, max_length=500)
    ogretmen_id: uuid.UUID | None


# --- ders dağılımı özeti (öğretmen ve sınıf yükü) -----------------------------------------


class OgretmenYukuYanit(BaseModel):
    ogretmen_id: uuid.UUID
    ders_saati: int
    musait_saat: int = Field(description="Haftada gelemez olmadığı saat sayısı")
    kullanilabilir_saat: int = Field(description="Günlük ders sınırıyla birlikte derse girebileceği en fazla saat")
    hedefli_kapasite: int | None = Field(
        default=None, description="Boş gün hedefi tutarsa yaklaşık kapasite (hedef yoksa boş); uyarı değildir")
    asim: bool
    mesaj: str | None = Field(description="Aşım varsa ön kontrolün mesajı")
    yuk_uyarisi: str | None = Field(default=None, description="Haftalık yük okulun eşiklerinin dışındaysa uyarı (hata değil)")


class SinifYukuYanit(BaseModel):
    sinif_id: uuid.UUID
    ders_saati: int
    kapasite: int
    ogretmensiz_atama: int
    asim: bool
    mesaj: str | None


class DagilimOzeti(BaseModel):
    """Ders dağılımının erken uyarıları. Hesap, program üretiminin ön kontrolüyle aynıdır
    (çözücü paketi, `cozucu.yuk`; ADR 0015)."""

    haftalik_kapasite: int
    ogretmen_gunluk_siniri: int
    ogretmensiz_atama: int = Field(description="Öğretmeni seçilmemiş atama sayısı (bütün okul)")
    ogretmenler: list[OgretmenYukuYanit]
    siniflar: list[SinifYukuYanit]


# --- müsaitlik ----------------------------------------------------------------------------


class MusaitlikOlustur(BaseModel):
    ogretmen_id: uuid.UUID
    gun: int = Field(ge=0, le=6, description="0 = pazartesi")
    saat: int = Field(ge=0, le=15, description="0 = ilk ders")
    durum: Literal["gelemez", "tercih_etmez"]


class MusaitlikGuncelle(BaseModel):
    durum: Literal["gelemez", "tercih_etmez"] | None = None


class MusaitlikYanit(_Yanit):
    id: uuid.UUID
    ogretmen_id: uuid.UUID
    gun: int
    saat: int
    durum: str


class MusaitlikHucresi(BaseModel):
    gun: int = Field(ge=0, le=6, description="0 = pazartesi")
    saat: int = Field(ge=0, le=15, description="0 = ilk ders")
    durum: Literal["gelemez", "tercih_etmez"]


class MusaitlikDegisikligi(BaseModel):
    gun: int = Field(ge=0, le=6)
    saat: int = Field(ge=0, le=15)
    # "musait": o hücrenin kaydı silinir.
    durum: Literal["musait", "gelemez", "tercih_etmez"]


class MusaitlikToplu(BaseModel):
    degisiklikler: list[MusaitlikDegisikligi] = Field(min_length=1, max_length=7 * 16)


class OgretmenYukYanit(BaseModel):
    ders_saati: int
    musait_saat: int
    kullanilabilir_saat: int = Field(description="Günlük ders sınırıyla birlikte derse girebileceği en fazla saat")
    asim: bool
    mesaj: str | None = Field(description="Aşım varsa ön kontrolün mesajıyla aynı açıklama")


class MusaitlikCizelgesi(BaseModel):
    ogretmen_id: uuid.UUID
    hucreler: list[MusaitlikHucresi] = Field(description="Yalnızca müsait olmayan hücreler")
    yuk: OgretmenYukYanit


# --- kısıt --------------------------------------------------------------------------------


class KisitOlustur(BaseModel):
    tur: str = Field(min_length=1, max_length=50)
    parametreler: dict[str, Any] = Field(default_factory=dict)
    zorunlu: bool = True
    agirlik: int = Field(default=1, ge=0)


class KisitGuncelle(BaseModel):
    parametreler: dict[str, Any] | None = None
    zorunlu: bool | None = None
    agirlik: int | None = Field(default=None, ge=0)


class KisitYanit(_Yanit):
    id: uuid.UUID
    tur: str
    parametreler: dict[str, Any]
    zorunlu: bool
    agirlik: int
    # Üçü de boşsa okul geneli; değilse özel ayar. Özel ayarlar `/kurallar/{tur}/ozel` ile yazılır.
    ders_id: uuid.UUID | None = None
    sinif_id: uuid.UUID | None = None
    ogretmen_id: uuid.UUID | None = None


# --- kurallar (okul geneli kısıtlar, kullanıcının diliyle) --------------------------------


OnemSeviyesi = Literal["onemsiz", "onemli", "cok_onemli"]


# Kural parametresinin değeri: sayı (n, m, hedef boş gün), açık/kapalı (otomatik blok), dağılım
# şekli ([2, 2, 1]) ya da saate göre şekiller ({"4": [2, 1, 1]}).
ParametreDegeri = bool | int | list[int] | dict[str, list[int]]


class KuralYanit(BaseModel):
    tur: str
    ad: str
    aciklama: str
    zorunlu: bool
    parametreler: dict[str, ParametreDegeri]
    varsayilan_parametreler: dict[str, ParametreDegeri]
    # Yalnızca esnek kurallarda: sayısal ağırlık ve karşılık gelen önem seviyesi ("ozel": hiçbir
    # seviyeye denk gelmeyen, elle girilmiş ağırlık).
    agirlik: int | None
    seviye: Literal["onemsiz", "onemli", "cok_onemli", "ozel"] | None
    varsayilan_seviye: OnemSeviyesi | None
    varsayilan: bool
    # Kuralın özel ayar alabildiği yerler (çözücünün kural sınıfından) ve okuldaki özel ayarlar.
    kapsamlar: list[Literal["ogretmen", "ders", "sube", "sube_grubu"]]
    # Özel ayarda dolu olması gereken eksenler: dağılım şekli bir dersin saatine bağlı, ders ister.
    zorunlu_eksenler: list[Literal["ogretmen", "ders", "sube", "sube_grubu"]]
    ozel_ayarlar: list[OzelAyarYanit]


class KuralAyari(BaseModel):
    parametreler: dict[str, ParametreDegeri] | None = None
    seviye: OnemSeviyesi | None = None


class KuralKapsami(BaseModel):
    """Özel ayarın yeri. Öğretmen tek başına; ders, şube ve şube grubu tek başına ya da ders ile
    birlikte (ders + şube, ders + şube grubu). Şube ile şube grubu birlikte olamaz (ADR 0016)."""

    ogretmen_id: uuid.UUID | None = None
    ders_id: uuid.UUID | None = None
    sinif_id: uuid.UUID | None = None
    sube_grubu_id: uuid.UUID | None = None


class OzelAyar(BaseModel):
    kapsam: KuralKapsami
    parametreler: dict[str, ParametreDegeri]


class OzelAyarYanit(BaseModel):
    kapsam: KuralKapsami
    ad: str = Field(description="Kapsamın adı: \"Ayşe Yılmaz\", \"9-A · Matematik\"")
    parametreler: dict[str, ParametreDegeri]


class OzelAyarEtkisi(BaseModel):
    """Bir kapsama özel ayar verilirse: aynı kapsamdaki mevcut ayar, ezdiği ve onu ezen özel ayarlar."""

    mevcut: OzelAyarYanit | None
    ezdikleri: list[OzelAyarYanit]
    ezenler: list[OzelAyarYanit]


class DagilimSekli(BaseModel):
    """Bir ders atamasının dağılım şekli (blok dersler) ve nereden geldiği (`cozucu.blok`)."""

    atama_id: uuid.UUID
    ders_id: uuid.UUID
    sinif_id: uuid.UUID
    sinif_adi: str
    haftalik_saat: int
    desen: list[int] | None = Field(description="Uygulanacak bloklar, büyükten küçüğe; None: blok yok")
    metin: str = Field(description="\"2+2+1\" ya da \"blok yok\"")
    kaynak: Literal["ders_sube", "ders_grup", "ders", "okul", "yok"] = Field(
        description="ders_sube / ders_grup / ders: özel ayar; okul: okulun önerisi; yok: blok yok")
    # Okul önerisi bu atamada uygulanamadıysa önerilen şekil ve neden(ler) (kaynak "yok" olur).
    dusen_oneri: str | None
    nedenler: list[str]
    # Açıkça seçilmiş şekil uygulanamıyorsa ön kontrolün göreceği sorunlar (kısa metin).
    sorunlar: list[str]


# --- program -----------------------------------------------------------------------------


class ProgramUret(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    # Doluysa en az değişiklikle güncelleme; o programın kilitli hücreleri de korunur.
    temel_program_id: uuid.UUID | None = None
    # Çözücü süre sınırı. Varsayılan 120 sn (docs/olcumler.md).
    sure_siniri_sn: int = Field(default=120, ge=5, le=3600)


class CeliskiYanit(BaseModel):
    """Programın üretilmesini engelleyen bir sorun (ön kontrol ya da çelişki analizi)."""

    tur: str
    mesaj: str
    ilgili: list[str] = Field(default_factory=list, description="İlgili öğretmen, şube ya da atama kimlikleri")


class OnKontrolYanit(BaseModel):
    celiskiler: list[CeliskiYanit]
    uyarilar: list[CeliskiYanit] = Field(default_factory=list, description="Programı engellemeyen uyarılar")


class ProgramYanit(_Yanit):
    id: uuid.UUID
    ad: str
    durum: str
    hata_mesaji: str | None
    temel_program_id: uuid.UUID | None
    sure_siniri_sn: int
    olusturma: datetime
    baslama: datetime | None
    bitis: datetime | None
    # Üretim sonucu (üretim bitince dolar). girdi_ozeti iç bilgidir, dışarı verilmez.
    cozum_durumu: str | None
    toplam_ceza: int | None
    olcumler: dict[str, int] | None
    celiskiler: list[CeliskiYanit] | None
    # Tutmayan esnek hedefler, kişi kişi (ör. "Hasan Şahin: hedef 4 boş gündü, 3 verilebildi").
    notlar: list[CeliskiYanit] | None = None
    sure_sn: float | None
    # Hazır programda: üretildiği andaki veri şimdikinden farklı mı (6.3). None: bilinmiyor.
    eski_veri: bool | None = None
    # Elle düzeltme (7.1): geri alınabilir değişiklik sayısı (0: program üretildiği gibi).
    elle_duzeltme: int = 0


class ProgramAdi(BaseModel):
    ad: str = Field(min_length=1, max_length=200)


class SubeFarki(BaseModel):
    sinif_id: uuid.UUID
    ad: str
    sayi: int


class FarkHucresi(BaseModel):
    ders_atama_id: uuid.UUID
    gun: int
    saat: int


class ProgramFarki(BaseModel):
    """Bu programın başka bir programdan farklı hücreleri (6.3)."""

    ile_id: uuid.UUID
    ile_ad: str
    degisen: int
    subeler: list[SubeFarki]
    hucreler: list[FarkHucresi]


class HucreKonumu(BaseModel):
    gun: int
    saat: int


class TasimaHedefi(BaseModel):
    gun: int
    saat: int
    durum: Literal["uygun", "uyari", "engel"]
    nedenler: list[str]
    # Hedefte duran ve yer değiştirecek aynı şube dersleri ("9-A Fizik").
    takas: list[str] = Field(default_factory=list)


class TasimaHaritasi(BaseModel):
    """Bir dersin taşınabileceği her başlangıç hücresi (7.1). `hucreler`: birlikte taşınan blok."""

    hucreler: list[HucreKonumu]
    hedefler: list[TasimaHedefi]


class TasimaIstegi(BaseModel):
    ders_atama_id: uuid.UUID
    gun: int = Field(ge=0)
    saat: int = Field(ge=0)
    hedef_gun: int = Field(ge=0)
    hedef_saat: int = Field(ge=0)
    uyarilari_kabul: bool = False


class KilitIstegi(BaseModel):
    ders_atama_id: uuid.UUID
    gun: int = Field(ge=0)
    saat: int = Field(ge=0)
    kilitli: bool


class YerlesimYanit(_Yanit):
    id: uuid.UUID
    ders_atama_id: uuid.UUID
    gun: int
    saat: int
    kilitli: bool


KuralYanit.model_rebuild()


# --- Excel'den içe aktarma (8a, ADR 0021) --------------------------------------------


class IceAktarmaSatiri(_Yanit):
    satir: int  # Excel'deki satır numarası
    ad: str  # "Ayşe Yılmaz" ya da "9-A · Matematik"
    ayrinti: str  # ne değişecek ya da (hatalı satırda) neden


class IceAktarmaSayfasi(_Yanit):
    sayfa: Literal["ogretmen", "sinif", "ders", "dagilim"]
    baslik: str
    eklenecek: list[IceAktarmaSatiri]
    guncellenecek: list[IceAktarmaSatiri]
    hatali: list[IceAktarmaSatiri]
    degismeyen: int
    atlanan_ornek: int  # şablondaki değiştirilmemiş örnek satır


class IceAktarmaOnizleme(_Yanit):
    sayfalar: list[IceAktarmaSayfasi]
    eklenecek_sayisi: int
    guncellenecek_sayisi: int
    hata_sayisi: int
    ozet: str = Field(description="Planın parmak izi; kaydederken geri verilir")


class IceAktarmaSonucu(BaseModel):
    eklenen: int
    guncellenen: int


# --- yayın (8b, ADR 0022) ------------------------------------------------------------


class YayinIstegi(BaseModel):
    program_id: uuid.UUID


class YayinDurumu(BaseModel):
    program_id: uuid.UUID | None = Field(description="Program silindiyse boş; yayın yine kalır")
    program_adi: str
    yayin_zamani: datetime
    eski_veri: bool | None = Field(description="Program, yayından sonra değişen verilerle mi üretildi (bilinmiyorsa boş)")
    program_degisti: bool = Field(description="Programda yayından sonra değişiklik var (elle düzeltme, ad)")
    uyarilar: list[str]


# --- paylaşım linki (8b, ADR 0022) ---------------------------------------------------


PaylasimTuru = Literal["okul", "ogretmen", "sube"]


class PaylasimLinkiOlustur(BaseModel):
    tur: PaylasimTuru
    ogretmen_id: uuid.UUID | None = None
    sinif_id: uuid.UUID | None = None


class TopluLinkIstegi(BaseModel):
    tur: Literal["ogretmen", "sube"]


class PaylasimLinkiYanit(BaseModel):
    id: uuid.UUID
    tur: PaylasimTuru
    ogretmen_id: uuid.UUID | None
    sinif_id: uuid.UUID | None
    hedef_adi: str = Field(description="\"Bütün okul\", öğretmenin ya da şubenin adı")
    jeton: str = Field(description="Linkin adresi: /p/{jeton}")
    olusturma: datetime


class PaylasimHucresi(BaseModel):
    gun: int
    saat: int
    uzunluk: int
    ders: str
    kisa_ad: str
    renk: str
    sube: str
    ogretmen: str


class PaylasimCizelgesi(BaseModel):
    """Kimlik taşımaz: linkle gelene veritabanı kimliği verilmez."""

    ad: str
    tur: Literal["sube", "ogretmen"]
    hucreler: list[PaylasimHucresi]


class ZilSaati(BaseModel):
    baslangic: str
    bitis: str


class PaylasimHaftasi(BaseModel):
    gun_adlari: list[str]
    gun_saatleri: list[int]
    saat_sayisi: int
    ogle_arasi_sonra: int | None
    zil: list[ZilSaati] | None
    ogle_zili: ZilSaati | None


class PaylasimYanit(BaseModel):
    tur: PaylasimTuru
    yayinda: bool
    yayin_zamani: datetime | None
    okul: str
    program: str
    hafta: PaylasimHaftasi | None
    subeler: list[PaylasimCizelgesi]
    ogretmenler: list[PaylasimCizelgesi]
