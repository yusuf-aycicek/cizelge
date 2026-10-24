"""Ders programı modülünün tabloları.

Bütün ilişkiler **bileşik yabancı anahtardır**: `(okul_id, x_id) -> x(okul_id, id)`. Bir satır
yalnızca **aynı okuldaki** bir satırı gösterebilir. A okulunun ders ataması B okulunun öğretmenine
bağlanmak istenirse veritabanı bunu reddeder, uygulamada bir hata olsa bile (docs/adr/0009).
Hedef tablolardaki `UNIQUE (okul_id, id)` kısıtı (`OkulaAitMixin`) bunun için vardır.

Silme davranışları (ON DELETE) ve gerekçeleri:
- çekirdek kaydı (sınıf, ders, öğretmen) bir atamada kullanılıyorsa silinemez (RESTRICT): veri
  sessizce kaybolmasın, kullanıcı önce atamayı değiştirsin;
- öğretmen silinince müsaitlik kayıtları da silinir (CASCADE): müsaitlik öğretmenin parçasıdır;
  çekirdek bu tabloyu bilmeden silme işini veritabanı yapar (modüler yapıya uygun);
- program silinince yerleşimleri silinir (CASCADE); ders ataması silinince eski programlardaki
  yerleşimleri de silinir (CASCADE). RESTRICT olsaydı bir kez program üretilen bir atama bir daha
  silinemezdi. Eski program bu durumda eksik kalır; en az değişiklikle güncellemede bu, "kaldırılmış
  ders" olarak zaten doğru işlenir (çözücü ADR 0006);
- temel programı silinen programın `temel_program_id`'si boşalır: PostgreSQL 15+ ile gelen
  `ON DELETE SET NULL (temel_program_id)` yalnızca bu sütunu boşaltır, `okul_id`'ye dokunmaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, column, DateTime, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from okulapi.cekirdek.modeller import OkulaAitMixin
from okulapi.cekirdek.veritabani import Base


def okul_ici_fk(sutun: str, hedef: str, ondelete: str = "RESTRICT") -> ForeignKeyConstraint:
    """`(okul_id, <sutun>) -> <hedef>(okul_id, id)`: yalnızca aynı okuldaki satırı gösterebilir."""
    return ForeignKeyConstraint(["okul_id", sutun], [f"{hedef}.okul_id", f"{hedef}.id"], ondelete=ondelete)


class SeviyeSablonu(OkulaAitMixin, Base):
    """Bir seviyenin (ör. 9. sınıflar) ya da bir şube grubunun (ör. 11 Sayısal) ders listesi ve
    haftalık saatleri.

    `sube_grubu_id` boşsa satır seviyenin şablonudur (K5 öncesindeki bütün satırlar böyle kalır);
    doluysa grubun şablonudur ve `seviye` grubun seviyesidir (servis denetler). Grubun şablonunda
    en az bir ders varsa grubun şubeleri seviyenin şablonu yerine onu kullanır. Grup silinince
    şablonu da silinir (CASCADE): grubun parçasıdır.
    """

    __tablename__ = "seviye_sablonu"
    _tablo_kisitlari = (
        # NULLS NOT DISTINCT: seviyenin şablonunda (grup boş) bir ders bir kez bulunur.
        UniqueConstraint("okul_id", "seviye", "sube_grubu_id", "ders_id", postgresql_nulls_not_distinct=True),
        okul_ici_fk("ders_id", "ders"),
        okul_ici_fk("sube_grubu_id", "sube_grubu", ondelete="CASCADE"),
        CheckConstraint("seviye BETWEEN 1 AND 12", name="seviye"),
        CheckConstraint("haftalik_saat >= 1", name="haftalik_saat"),
    )

    seviye: Mapped[int]
    sube_grubu_id: Mapped[uuid.UUID | None]
    ders_id: Mapped[uuid.UUID]
    haftalik_saat: Mapped[int]


ISTISNA_TURLERI = ("almaz", "ek")


class SubeDersIstisnasi(OkulaAitMixin, Base):
    """Şubenin şablondan ayrıldığı ders: "9-B Din almaz" ya da "11-A ek olarak Felsefe 2 saat".

    Şablon uygulanırken okunur: `almaz` dersi şubeye eklenmez (silinmiş ders şablon yeniden
    uygulanınca geri gelmez), `ek` dersi şablonda olmasa da `haftalik_saat` ile eklenir. Çözücü
    istisnaları bilmez; onun girdisi ders atamalarıdır. Şube ya da ders silinince istisna da
    silinir (CASCADE).
    """

    __tablename__ = "sube_ders_istisnasi"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "sinif_id", "ders_id"),
        okul_ici_fk("sinif_id", "sinif", ondelete="CASCADE"),
        okul_ici_fk("ders_id", "ders", ondelete="CASCADE"),
        CheckConstraint(f"tur IN ({', '.join(repr(t) for t in ISTISNA_TURLERI)})", name="tur"),
        # Haftalık saat yalnızca "ek" istisnada vardır ve en az 1'dir.
        CheckConstraint("(tur = 'ek') = (haftalik_saat IS NOT NULL) AND (haftalik_saat IS NULL OR haftalik_saat >= 1)",
                        name="haftalik_saat"),
    )

    sinif_id: Mapped[uuid.UUID]
    ders_id: Mapped[uuid.UUID]
    tur: Mapped[str] = mapped_column(String(10))
    haftalik_saat: Mapped[int | None]


class DersAtama(OkulaAitMixin, Base):
    """Bir sınıfa bir dersin haftada kaç saat, hangi öğretmenle verileceği. Çözücünün asıl girdisi.

    "Bir sınıf, bir ders, bir öğretmen" (CLAUDE.md bölüm 3): her (sınıf, ders) için tek atama.
    `ogretmen_id` boş olabilir: bileşik yabancı anahtar varsayılan olarak MATCH SIMPLE'dır, yani
    sütunlardan biri NULL ise denetlenmez. Öğretmen seçilince denetim kendiliğinden başlar.
    """

    __tablename__ = "ders_atama"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "sinif_id", "ders_id"),
        okul_ici_fk("sinif_id", "sinif"),
        okul_ici_fk("ders_id", "ders"),
        okul_ici_fk("ogretmen_id", "ogretmen"),
        CheckConstraint("haftalik_saat >= 1", name="haftalik_saat"),
        # PostgreSQL yabancı anahtarın *gösteren* tarafına kendiliğinden indeks koymaz. Öğretmen
        # silinirken (RESTRICT denetimi) ve "bu öğretmenin atamaları" sorgusunda kullanılır.
        Index(None, "okul_id", "ogretmen_id"),
    )

    sinif_id: Mapped[uuid.UUID]
    ders_id: Mapped[uuid.UUID]
    ogretmen_id: Mapped[uuid.UUID | None]
    haftalik_saat: Mapped[int]


class Musaitlik(OkulaAitMixin, Base):
    __tablename__ = "musaitlik"
    _tablo_kisitlari = (
        UniqueConstraint("okul_id", "ogretmen_id", "gun", "saat"),
        okul_ici_fk("ogretmen_id", "ogretmen", ondelete="CASCADE"),
        CheckConstraint("durum IN ('gelemez', 'tercih_etmez')", name="durum"),
        CheckConstraint("gun BETWEEN 0 AND 6", name="gun"),
        CheckConstraint("saat BETWEEN 0 AND 15", name="saat"),
    )

    ogretmen_id: Mapped[uuid.UUID]
    gun: Mapped[int]  # 0 = pazartesi
    saat: Mapped[int]  # 0 = ilk ders
    durum: Mapped[str] = mapped_column(String(20))


class Kisit(OkulaAitMixin, Base):
    """Bir kural tanımı. `tur` çözücünün kural kayıt defterindeki adlardan biridir.

    Kapsam sütunlarının dördü de boşsa okul geneli kuraldır; biri doluysa okul değerini o derse,
    şubeye, şube grubuna ya da öğretmene özel ezen bir **özel ayardır** (ADR 0016). Özel ayarın kipi ve ağırlığı
    çözücüde okul tanımından gelir; burada okul tanımındakiyle aynı yazılır.
    """

    __tablename__ = "kisit"
    _tablo_kisitlari = (
        # NULLS NOT DISTINCT: kapsamın boş sütunları eşit sayılır; okul geneli satır da tek kalır
        # (migration ders_programi_0006).
        UniqueConstraint("okul_id", "tur", "ders_id", "sinif_id", "sube_grubu_id", "ogretmen_id",
                         name="uq_kisit_kapsam", postgresql_nulls_not_distinct=True),
        # Ona özel ayar, varlığın parçasıdır: varlık silinince ayar da silinir.
        okul_ici_fk("ders_id", "ders", ondelete="CASCADE"),
        okul_ici_fk("sinif_id", "sinif", ondelete="CASCADE"),
        okul_ici_fk("ogretmen_id", "ogretmen", ondelete="CASCADE"),
        okul_ici_fk("sube_grubu_id", "sube_grubu", ondelete="CASCADE"),
        CheckConstraint("agirlik >= 0", name="agirlik"),
        # Öğretmen ailesi (M, boş gün) ile yerleşim ailesi (N, blok) ayrıktır (ADR 0016 madde 3).
        CheckConstraint("ogretmen_id IS NULL OR (ders_id IS NULL AND sinif_id IS NULL AND sube_grubu_id IS NULL)",
                        name="kapsam_ailesi"),
        # Bir kapsamda şube ile şube grubu birlikte bulunamaz (cozucu.kapsam.Kapsam).
        CheckConstraint("sinif_id IS NULL OR sube_grubu_id IS NULL", name="sube_ya_da_grup"),
    )

    tur: Mapped[str] = mapped_column(String(50))
    # JSONB: esnek yapılı ama sorgulanabilir ve indekslenebilir JSON (ör. {"n": 2}).
    parametreler: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    zorunlu: Mapped[bool]
    agirlik: Mapped[int] = mapped_column(default=1, server_default="1")
    ders_id: Mapped[uuid.UUID | None]
    sinif_id: Mapped[uuid.UUID | None]
    sube_grubu_id: Mapped[uuid.UUID | None]
    ogretmen_id: Mapped[uuid.UUID | None]

    @property
    def okul_geneli(self) -> bool:
        return self.ders_id is None and self.sinif_id is None and self.sube_grubu_id is None and self.ogretmen_id is None


PROGRAM_DURUMLARI = ("bekliyor", "uretiliyor", "hazir", "basarisiz")
# cozucu.CozumDurumu değerleri. Burada ayrıca yazılır: veritabanı kısıtı Python enum'una değil,
# migration anındaki listeye bağlı kalmalı. Eşitliği test_ders_programi denetler.
# Bitmemiş üretim: okulda aynı anda en fazla bir tane olabilir.
ETKIN_DURUMLAR = ("bekliyor", "uretiliyor")
COZUM_DURUMLARI = ("optimal", "uygun", "cozumsuz", "on_kontrol_hatasi", "bilinmiyor")


def _liste(degerler: tuple[str, ...]) -> str:
    return ", ".join(f"'{d}'" for d in degerler)


class Program(OkulaAitMixin, Base):
    """Bir program üretme denemesi. Yazan taraf: worker (yapım sırası 3, docs/kuyruk-plani.md).

    Durum makinesi: bekliyor -> uretiliyor -> hazir | basarisiz. `bekliyor` da doğrudan
    `basarisiz` olabilir (kuyruğa ulaşılamadı). Sonuç alanları (`cozum_durumu`, `toplam_ceza`,
    `olcumler`, `celiskiler`, `sure_sn`, `girdi_ozeti`) üretim bitince dolar.

    Durumla alanlar arasındaki tutarlılık veritabanında da korunur (CHECK kısıtları): worker'da
    bir hata olsa bile "başlama zamanı olmayan üretim" ya da "çözümü olmayan hazır program"
    kaydedilemez.
    """

    __tablename__ = "program"
    _tablo_kisitlari = (
        okul_ici_fk("temel_program_id", "program", ondelete="SET NULL (temel_program_id)"),
        CheckConstraint(f"durum IN ({_liste(PROGRAM_DURUMLARI)})", name="durum"),
        CheckConstraint("sure_siniri_sn > 0", name="sure_siniri_sn"),
        CheckConstraint(f"cozum_durumu IN ({_liste(COZUM_DURUMLARI)})", name="cozum_durumu"),
        CheckConstraint("toplam_ceza >= 0", name="toplam_ceza"),
        # Takılı üretimin süresi başlama zamanından hesaplanır (plan karar e).
        CheckConstraint("durum NOT IN ('uretiliyor', 'hazir') OR baslama IS NOT NULL", name="baslama"),
        # Hazır program, geçerli bir çözümü olan programdır. IS NOT NULL gerekli: NULL IN (...)
        # sonucu NULL'dır ve CHECK kısıtı NULL'ı "geçti" sayar (SQL'in üç değerli mantığı).
        CheckConstraint(
            "durum <> 'hazir' OR (cozum_durumu IS NOT NULL AND cozum_durumu IN ('optimal', 'uygun'))",
            name="hazir_cozum",
        ),
        CheckConstraint("durum NOT IN ('hazir', 'basarisiz') OR bitis IS NOT NULL", name="bitis"),
        # "Bu okulun etkin üretimi var mı?" sorusu (plan karar c) her üretim isteğinde sorulur.
        Index(None, "okul_id", "durum"),
        # Okul başına en fazla bir etkin üretim (plan karar c), veritabanı düzeyinde. Kısmi
        # benzersiz indeks: yalnızca WHERE koşulunu sağlayan satırlar arasında benzersizlik. Aynı
        # anda gelen iki istek de "etkin üretim yok" görürse ikinci INSERT birincinin commit'ini
        # bekler, sonra benzersizlik hatası alır (409).
        Index("uq_program_okul_id_etkin", "okul_id", unique=True,
              postgresql_where=column("durum").in_(ETKIN_DURUMLAR)),
    )

    ad: Mapped[str] = mapped_column(String(200))
    durum: Mapped[str] = mapped_column(String(20), default="bekliyor", server_default="bekliyor")
    hata_mesaji: Mapped[str | None] = mapped_column(Text)
    temel_program_id: Mapped[uuid.UUID | None]
    sure_siniri_sn: Mapped[int] = mapped_column(default=120, server_default="120")
    baslama: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bitis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # --- üretim sonucu ---
    cozum_durumu: Mapped[str | None] = mapped_column(String(20))
    toplam_ceza: Mapped[int | None]
    # kalite.olc sonucu: {"sinif_boslugu": 0, "ogretmen_penceresi": 3, ...}
    olcumler: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # [{"tur": ..., "mesaj": ..., "ilgili": [kimlikler]}]; arayüz ilgili satırları vurgulayabilir.
    celiskiler: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    sure_sn: Mapped[float | None]
    # Çözücü girdisinin kanonik JSON'unun SHA-256'sı (hex). Çözüm sırasında veri değişti mi
    # sorusunu yanıtlar (docs/api-plani.md bölüm 14).
    girdi_ozeti: Mapped[str | None] = mapped_column(String(64))


class Yerlesim(OkulaAitMixin, Base):
    """Programın bir hücresi: bu atama bu gün bu saatte."""

    __tablename__ = "yerlesim"
    _tablo_kisitlari = (
        UniqueConstraint("program_id", "ders_atama_id", "gun", "saat"),
        okul_ici_fk("program_id", "program", ondelete="CASCADE"),
        okul_ici_fk("ders_atama_id", "ders_atama", ondelete="CASCADE"),
        CheckConstraint("gun BETWEEN 0 AND 6", name="gun"),
        CheckConstraint("saat BETWEEN 0 AND 15", name="saat"),
        Index(None, "okul_id", "ders_atama_id"),  # atama silinirken CASCADE araması için
    )

    program_id: Mapped[uuid.UUID]
    ders_atama_id: Mapped[uuid.UUID]
    gun: Mapped[int]
    saat: Mapped[int]
    kilitli: Mapped[bool] = mapped_column(default=False, server_default="false")
