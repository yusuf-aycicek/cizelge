"""Program üretimi: worker'ın çalıştırdığı iş (yapım sırası 3, ADR 0011, docs/kuyruk-plani.md).

`programi_uret(fabrika, okul_id, program_id)` üç adımda çalışır. Her adım ayrı bir veritabanı
işlemidir; çözüm sırasında veritabanı bağlantısı açık tutulmaz:

1. **Başlat:** program satırı `SELECT ... FOR UPDATE` ile kilitlenir. Durum `bekliyor` değilse iş
   hiçbir şey yapmadan biter (idempotent: aynı iş iki kez gelse de program bir kez üretilir).
   Durum `uretiliyor`, başlama zamanı yazılır; girdi veritabanından üretilir, özeti saklanır;
   commit. Arayüz `uretiliyor`u bu commit'ten sonra görür.
2. **Çöz:** `ProgramCozucu.coz(girdi, sure_siniri_sn)`. Veritabanı yok.
3. **Yaz:** satır yeniden kilitlenir; durum hâlâ `uretiliyor` olmalı (bu arada takılı sayılıp
   temizlenmiş olabilir). Girdi yeniden üretilir ve özeti karşılaştırılır: veri çözüm sırasında
   değiştiyse eski veriyle üretilmiş program yazılmaz. Sonra bağımsız doğrulayıcı (`dogrula`)
   son bir kez çalışır, yerleşimler eklenir, program `hazir` ya da `basarisiz` olur; tek commit.

Okul izolasyonu burada da geçerlidir: bütün oturumlar `okul_oturumu(fabrika, okul_id)` ile açılır
(ORM filtresi + RLS). Başka okulun program kimliği verilse bile program bulunamaz.

Kilitli hücreler ve temel program aynı programdan gelir (plan karar b): `temel_program_id`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, replace
from enum import Enum
from typing import Any

from cozucu import CozumGirdisi, CozumSonucu, CpSatCozucu, ProgramCozucu, dogrula, olc
from cozucu.kalite import KaliteNotu, bos_gun_notlari
from cozucu.veri_io import girdi_to_dict
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from okulapi.cekirdek.kiraci import okul_oturumu
from okulapi.cekirdek.kuyruk import IsKuyrugu, KuyrukHatasi
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.modeller import Program, Yerlesim

gunluk = logging.getLogger(__name__)

# Worker işi, API programı commit etmeden alabilir (API önce kuyruğa ekler, sonra commit eder;
# ADR 0011 madde 4). Program bulunamazsa bu aralıklarla yeniden aranır (toplam ~4 sn).
BULUNAMAZSA_BEKLE_SN = (0.2, 0.5, 1.0, 2.0)

# İş süresi sınırı = 2 × çözücü süre sınırı + pay (plan karar f). Ana çözüm, zorunlu kısıtlarla
# ikinci kontrol ve çelişki analizi aynı işte çalışır.
IS_SURESI_PAYI_SN = 120

VERI_DEGISTI = "Program üretilirken okulun verileri değişti. Programı yeniden üretin."
YARIDA_KALDI = "Üretim yarıda kaldı (süre aşıldı ya da worker durdu). Programı yeniden üretin."
BEKLENMEYEN_HATA = "Program üretilirken beklenmeyen bir hata oluştu. Programı yeniden üretin."
DOGRULAMA_HATASI = "Üretilen program doğrulamadan geçemedi (iç hata). Programı yeniden üretin."
OKSUZ = "Üretim isteği iş kuyruğunda bulunamadı. Programı yeniden üretin."
SURE_YETMEDI = "Süre içinde program bulunamadı. Süre sınırını artırıp yeniden deneyin."


class UretimSonucu(str, Enum):
    """İşin ne yaptığı (günlük ve testler için; programın kendi durumu veritabanındadır)."""

    ATLANDI = "atlandi"  # program yok, başka okulun, ya da durumu bekliyor/uretiliyor değil
    HAZIR = "hazir"
    BASARISIZ = "basarisiz"


def is_suresi_siniri_sn(sure_siniri_sn: int) -> int:
    return 2 * sure_siniri_sn + IS_SURESI_PAYI_SN


def girdi_ozeti(girdi: CozumGirdisi) -> str:
    """Girdinin kanonik JSON'unun SHA-256'sı.

    Kanonik: anahtarlar ve listelerin elemanları sıralanır. Depolar satırları belirli bir sırayla
    döndürmek zorunda değildir; aynı veri her okumada aynı özeti vermeli.
    """
    veri = girdi_to_dict(girdi)
    for anahtar, deger in veri.items():
        if isinstance(deger, list):
            veri[anahtar] = sorted(deger, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
    metin = json.dumps(veri, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def not_sozlukleri(notlar: list[KaliteNotu]) -> list[dict[str, Any]]:
    """`program.notlar` sütununun biçimi (çelişkilerle aynı: tur, mesaj, ilgili)."""
    return [{"tur": n.tur, "mesaj": n.mesaj, "ilgili": list(n.ilgili)} for n in notlar]


def veri_ozeti(girdi: CozumGirdisi) -> str:
    """Yalnızca okulun verisinin özeti: temel programın yerleşimleri ve kilitler dışarıda (6.3)."""
    return girdi_ozeti(replace(girdi, kilitli_yerlesimler=[], temel_yerlesimler=[]))


def _kilitle(oturum: Session, program_id: uuid.UUID) -> Program | None:
    """Program satırını işlem sonuna kadar kilitler (SELECT ... FOR UPDATE).

    Aynı satırı kilitlemek isteyen başka bir işlem (ikinci worker, temizlik) bu işlem commit ya da
    rollback yapana kadar bekler. Okul filtresi bu sorguya da uygulanır.
    """
    return oturum.scalars(select(Program).where(Program.id == program_id).with_for_update()).one_or_none()


def _girdi(oturum: Session, program: Program) -> CozumGirdisi:
    return cozum_girdisi_olustur(
        oturum, kilit_programi_id=program.temel_program_id, temel_program_id=program.temel_program_id
    )


def _bitir(program: Program, durum: str, hata_mesaji: str | None = None) -> None:
    program.durum = durum
    program.hata_mesaji = hata_mesaji
    program.bitis = func.now()


def _hata_mesaji(sonuc: CozumSonucu) -> str:
    """Kullanıcıya gösterilecek metin: çelişkiler, yoksa çözücünün mesajları."""
    satirlar = [c.mesaj for c in sonuc.celiskiler] or list(sonuc.mesajlar)
    return "\n".join(satirlar) if satirlar else SURE_YETMEDI


def programi_uret(
    fabrika: sessionmaker,
    okul_id: uuid.UUID,
    program_id: uuid.UUID,
    cozucu: ProgramCozucu | None = None,
    bulunamazsa_bekle: tuple[float, ...] = (),
) -> UretimSonucu:
    """Program üretiminin kendisi; worker'da `uretim_isi` üzerinden çalışır. Çözücü dışarıdan verilebilir (testlerde sahte çözücü, ADR 0001).

    Herhangi bir adımda beklenmeyen bir istisna olursa program `basarisiz` yapılır ve istisna
    yeniden fırlatılır (worker günlüğe yazar, RQ işi başarısız sayar). Program `uretiliyor`da
    kalmaz; worker sürecinin kendisi ölürse takılı üretim temizliği devreye girer.
    """
    okul_id, program_id = uuid.UUID(str(okul_id)), uuid.UUID(str(program_id))
    try:
        return _uret(fabrika, okul_id, program_id, cozucu or CpSatCozucu(), bulunamazsa_bekle)
    except Exception:
        gunluk.exception("Program %s üretilirken hata", program_id)
        uretimi_basarisiz_yap(fabrika, okul_id, program_id, BEKLENMEYEN_HATA)
        raise


def _baslat(fabrika: sessionmaker, okul_id: uuid.UUID, program_id: uuid.UUID,
            bulunamazsa_bekle: tuple[float, ...]) -> tuple[CozumGirdisi, str, int] | None:
    for bekle in (*bulunamazsa_bekle, None):
        with okul_oturumu(fabrika, okul_id) as oturum:
            program = _kilitle(oturum, program_id)
            if program is None and bekle is not None:
                time.sleep(bekle)  # API henüz commit etmemiş olabilir
                continue
            if program is None or program.durum != "bekliyor":
                gunluk.info("Program %s atlandı (durum: %s)", program_id, program and program.durum)
                return None
            program.durum = "uretiliyor"
            program.baslama = func.now()
            girdi = _girdi(oturum, program)
            ozet = program.girdi_ozeti = girdi_ozeti(girdi)
            program.veri_ozeti = veri_ozeti(girdi)
            sure_siniri_sn = program.sure_siniri_sn
            oturum.commit()
            return girdi, ozet, sure_siniri_sn
    return None


def _uret(fabrika: sessionmaker, okul_id: uuid.UUID, program_id: uuid.UUID, cozucu: ProgramCozucu,
          bulunamazsa_bekle: tuple[float, ...]) -> UretimSonucu:
    # 1. Başlat ------------------------------------------------------------------------------
    baslangic = _baslat(fabrika, okul_id, program_id, bulunamazsa_bekle)
    if baslangic is None:
        return UretimSonucu.ATLANDI
    girdi, ozet, sure_siniri_sn = baslangic

    # 2. Çöz (veritabanı bağlantısı yok) -----------------------------------------------------
    # Çözücü sözleşmesi istisna fırlatmamaktır; fırlatırsa programi_uret yakalar.
    sonuc = cozucu.coz(girdi, sure_siniri_sn)

    # 3. Yaz (tek işlem) ---------------------------------------------------------------------
    with okul_oturumu(fabrika, okul_id) as oturum:
        program = _kilitle(oturum, program_id)
        if program is None or program.durum != "uretiliyor":
            gunluk.warning("Program %s çözüm sırasında değişti (durum: %s); sonuç yazılmadı",
                           program_id, program and program.durum)
            return UretimSonucu.ATLANDI

        program.cozum_durumu = sonuc.durum.value
        program.toplam_ceza = sonuc.toplam_ceza
        program.sure_sn = round(sonuc.sure_sn, 3)
        program.celiskiler = [{"tur": c.tur, "mesaj": c.mesaj, "ilgili": list(c.ilgili)} for c in sonuc.celiskiler]

        if girdi_ozeti(_girdi(oturum, program)) != ozet:
            _bitir(program, "basarisiz", VERI_DEGISTI)
        elif not sonuc.basarili:
            _bitir(program, "basarisiz", _hata_mesaji(sonuc))
        elif hatalar := dogrula(girdi, sonuc.yerlesimler):
            gunluk.error("Program %s doğrulamadan geçemedi: %s", program_id, hatalar)
            _bitir(program, "basarisiz", DOGRULAMA_HATASI)
        else:
            # ORM ile toplu ekleme: SQLAlchemy 2 satırları tek çok-değerli INSERT'lerle gönderir
            # ("insertmanyvalues"). okul_id'yi kiraci.py'nin before_flush olayı yazar.
            oturum.add_all([
                Yerlesim(program_id=program.id, ders_atama_id=uuid.UUID(y.ders_atama_id),
                         gun=y.gun, saat=y.saat, kilitli=y.kilitli)
                for y in sonuc.yerlesimler
            ])
            program.olcumler = asdict(olc(girdi, sonuc.yerlesimler))
            program.notlar = not_sozlukleri(bos_gun_notlari(girdi, sonuc.yerlesimler))
            _bitir(program, "hazir")
        durum = program.durum
        oturum.commit()

    gunluk.info("Program %s: %s (%s, %.1f sn)", program_id, durum, sonuc.durum.value, sonuc.sure_sn)
    return UretimSonucu(durum)


def uretimi_basarisiz_yap(fabrika: sessionmaker, okul_id: uuid.UUID, program_id: uuid.UUID, mesaj: str) -> bool:
    """Bitmemiş (bekliyor/uretiliyor) bir üretimi `basarisiz` yapar; bitmişse dokunmaz.

    Kullananlar: beklenmeyen hata (yukarıda) ve kuyruğun başarısızlık geri çağrısı
    (`uretim_basarisiz_oldu`). `bekliyor`dan doğrudan `basarisiz` olan programın `baslama`sı boş
    kalır: hiç başlamadı.
    """
    with okul_oturumu(fabrika, okul_id) as oturum:
        program = _kilitle(oturum, uuid.UUID(str(program_id)))
        if program is None or program.durum not in ("bekliyor", "uretiliyor"):
            return False
        _bitir(program, "basarisiz", mesaj)
        oturum.commit()
        return True


def takili_uretimleri_temizle(oturum: Session, kuyruk: IsKuyrugu | None) -> int:
    """Takılı üretimleri `basarisiz` yapar; kaç program olduğunu döner (ADR 0011 madde 8).

    İki tür takılı üretim vardır ve ikisi farklı ölçütle anlaşılır:

    - **`uretiliyor` ve süresi geçmiş:** worker başlatıp bitiremedi (süreç öldü). Süre program
      başınadır: `baslama + iş süresi sınırı < şimdi`; zaman veritabanının saatidir (`now()`).
    - **`bekliyor` ve işi kuyrukta yok (öksüz):** süreye bakılmaz, kuyruğa sorulur. İşin kimliği
      program kimliğidir. İş kuyruktaysa (sırada ya da çalışıyor) program gerçekten bekliyordur,
      dokunulmaz; kuyruk ne kadar uzun olursa olsun. Kuyruğa ulaşılamazsa (`KuyrukHatasi`) bu adım
      atlanır: "bilmiyorum" diye program iptal edilmez.

    `bekliyor` satırları `FOR UPDATE SKIP LOCKED` ile alınır: worker o anda bir programı
    başlatıyorsa (satırı kilitlemişse) temizlik onu beklemez ve ona dokunmaz.

    Okul filtresi buraya da uygulanır: yalnızca oturumun okulu temizlenir. Commit çağırana aittir.
    """
    sinir = func.make_interval(0, 0, 0, 0, 0, 0, 2 * Program.sure_siniri_sn + IS_SURESI_PAYI_SN)
    sayi = oturum.execute(
        update(Program)
        .where(Program.durum == "uretiliyor", Program.baslama + sinir < func.now())
        .values(durum="basarisiz", hata_mesaji=YARIDA_KALDI, bitis=func.now())
        .execution_options(synchronize_session=False)
    ).rowcount

    if kuyruk is not None:
        bekleyenler = oturum.scalars(
            select(Program).where(Program.durum == "bekliyor").with_for_update(skip_locked=True)
        ).all()
        try:
            oksuzler = [p for p in bekleyenler if not kuyruk.kuyrukta_mi(str(p.id))]
        except KuyrukHatasi:
            gunluk.warning("Kuyruğa ulaşılamadı; bekleyen programlar denetlenemedi")
            oksuzler = []
        for program in oksuzler:
            _bitir(program, "basarisiz", OKSUZ)
        sayi += len(oksuzler)

    if sayi:
        oturum.flush()
        gunluk.warning("%d takılı üretim başarısız sayıldı", sayi)
    return sayi


# --- kuyruk giriş noktaları ------------------------------------------------------------------
# Kuyruk bu fonksiyonları Python yoluyla çağırır; argümanlar yalnızca kimliklerdir (metin).
# Oturum fabrikası worker sürecinin kendisinden gelir (cekirdek/isci.py).

URETIM_ISI = f"{__name__}.uretim_isi"
URETIM_BASARISIZ = f"{__name__}.uretim_basarisiz_oldu"


def uretim_isi(okul_id: str, program_id: str) -> str:
    from okulapi.cekirdek.isci import isci_fabrikasi

    from okulapi.ayarlar import Ayarlar

    # İş parçacığı sayısı sunucunun ayarıdır (küçük sunucuda bellek için düşürülür).
    cozucu = CpSatCozucu(is_parcacigi=Ayarlar().cozucu_is_parcacigi)
    return programi_uret(isci_fabrikasi(), okul_id, program_id, cozucu,
                         bulunamazsa_bekle=BULUNAMAZSA_BEKLE_SN).value


def uretim_basarisiz_oldu(okul_id: str, program_id: str, zaman_asimi: bool) -> None:
    """İş istisnayla ya da zaman aşımıyla bittiğinde kuyruk çağırır. Program zaten bitmişse
    (programi_uret hatayı yakalayıp `basarisiz` yaptıysa) hiçbir şey yapmaz."""
    from okulapi.cekirdek.isci import isci_fabrikasi

    mesaj = YARIDA_KALDI if zaman_asimi else BEKLENMEYEN_HATA
    uretimi_basarisiz_yap(isci_fabrikasi(), okul_id, program_id, mesaj)
