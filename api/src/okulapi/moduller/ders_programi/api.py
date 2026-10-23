"""Ders programı endpoint'leri (/api/ders-programi/...). Çekirdeğin `crud_router` fabrikasını kullanır.

Not: `from __future__ import annotations` yok (FastAPI tip ipuçlarını çalışma anında okur).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Request, Response

from okulapi.cekirdek.api import crud_router
from okulapi.cekirdek.bagimliliklar import Kuyruk, OkulOturumu
from okulapi.moduller.ders_programi import semalar
from okulapi.moduller.ders_programi.kurallar import KurallarServisi
from okulapi.moduller.ders_programi.servisler import (
    DersAtamaServisi,
    KisitServisi,
    MusaitlikCizelgesiServisi,
    MusaitlikServisi,
    ProgramServisi,
    SeviyeSablonuServisi,
    dagilim_ozeti,
    dagilim_sekilleri,
    on_kontrol_sonucu,
)

router = APIRouter()

sablon_router = APIRouter(prefix="/seviye-sablonlari", tags=["seviye şablonu"])


@sablon_router.post("/uygula", response_model=semalar.SablonUygulamaSonucu)
def sablonu_uygula(veri: semalar.SablonUygula, oturum: OkulOturumu) -> Any:
    """Seviyenin şablonunu o seviyedeki her şubeye uygular (öğretmeni boş atamalar)."""
    return SeviyeSablonuServisi(oturum).uygula(veri.seviye)


atama_router = APIRouter(prefix="/atamalar", tags=["ders atama"])


@atama_router.post("/toplu-ogretmen", response_model=list[semalar.DersAtamaYanit])
def toplu_ogretmen_ata(veri: semalar.TopluOgretmenAta, oturum: OkulOturumu) -> Any:
    """Aynı öğretmeni birden fazla atamaya tek işlemde verir. Atamalardan biri bulunamazsa
    hiçbiri değişmez (404)."""
    return DersAtamaServisi(oturum).toplu_ogretmen_ata(veri.atama_idleri, veri.ogretmen_id)


@router.get("/dagilim-sekilleri", response_model=list[semalar.DagilimSekli], tags=["ders atama"])
def dagilim_sekillerini_getir(oturum: OkulOturumu) -> Any:
    """Her ders atamasının dağılım şekli (blok dersler), nereden geldiği ve okul önerisi
    uygulanamadıysa nedeni. Hesap çözücüdekiyle aynı (`cozucu.blok`)."""
    return dagilim_sekilleri(oturum)


@router.get("/dagilim-ozeti", response_model=semalar.DagilimOzeti, tags=["ders atama"])
def dagilim_ozetini_getir(oturum: OkulOturumu) -> Any:
    """Öğretmen ve sınıf yükleri: ders saati, müsaitliğe ve günlük sınıra göre kapasite, aşım
    mesajı; öğretmeni seçilmemiş atama sayısı. Program üretiminin ön kontrolüyle aynı hesap."""
    return dagilim_ozeti(oturum)


@router.get("/on-kontrol", response_model=semalar.OnKontrolYanit, tags=["program"])
def on_kontrolu_getir(oturum: OkulOturumu) -> Any:
    """Program üretilmeden önce, üretimdeki ön kontrolün tamamı (özel ayarlar dahil). `celiskiler`
    boş değilse üretim ön kontrolde başarısız olur; arayüz bu durumda oluşturma düğmesini kapatır."""
    return {"celiskiler": on_kontrol_sonucu(oturum)}


@router.get("/ogretmenler/{ogretmen_id}/musaitlik", response_model=semalar.MusaitlikCizelgesi, tags=["müsaitlik"])
def musaitlik_cizelgesini_getir(ogretmen_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    """Öğretmenin müsait olmadığı hücreler ve yükü (kapasite uyarısı ön kontrolle aynı hesap)."""
    return MusaitlikCizelgesiServisi(oturum).getir(ogretmen_id)


@router.put("/ogretmenler/{ogretmen_id}/musaitlik", response_model=semalar.MusaitlikCizelgesi, tags=["müsaitlik"])
def musaitlik_cizelgesini_degistir(ogretmen_id: uuid.UUID, veri: semalar.MusaitlikToplu, oturum: OkulOturumu) -> Any:
    """Bir ya da birçok hücreyi tek istekte değiştirir; biri geçersizse hiçbiri değişmez (422)."""
    return MusaitlikCizelgesiServisi(oturum).degistir(ogretmen_id, [d.model_dump() for d in veri.degisiklikler])


kural_router = APIRouter(prefix="/kurallar", tags=["kural"])


@kural_router.get("", response_model=list[semalar.KuralYanit])
def kurallari_listele(oturum: OkulOturumu) -> Any:
    """Okulun geçerli kuralları: çözücünün varsayılanları + okulun değiştirdikleri."""
    return KurallarServisi(oturum).listele()


@kural_router.put("/{tur}", response_model=semalar.KuralYanit)
def kurali_ayarla(tur: str, veri: semalar.KuralAyari, oturum: OkulOturumu) -> Any:
    """Bir kuralın ayarını (ör. {"n": 3}) ve/veya önem seviyesini değiştirir."""
    return KurallarServisi(oturum).ayarla(tur, veri.parametreler, veri.seviye)


@kural_router.delete("/{tur}", response_model=semalar.KuralYanit)
def kurali_varsayilana_dondur(tur: str, oturum: OkulOturumu) -> Any:
    return KurallarServisi(oturum).varsayilana_don(tur)


@kural_router.put("/{tur}/ozel", response_model=semalar.KuralYanit)
def ozel_ayari_kaydet(tur: str, veri: semalar.OzelAyar, oturum: OkulOturumu) -> Any:
    """Kuralın bir öğretmene, derse ya da şubeye özel değerini ekler ya da günceller.

    422: kural bu kapsamda ayarlanamıyor (ör. sınıf boşluğu öğretmene özel olamaz), kayıt bu
    okulda yok ya da değer geçersiz.
    """
    k = veri.kapsam
    return KurallarServisi(oturum).ozel_ayarla(tur, k.ders_id, k.sinif_id, k.ogretmen_id, veri.parametreler)


@kural_router.delete("/{tur}/ozel", response_model=semalar.KuralYanit)
def ozel_ayari_kaldir(
    tur: str, oturum: OkulOturumu, ogretmen_id: uuid.UUID | None = None, ders_id: uuid.UUID | None = None,
    sinif_id: uuid.UUID | None = None,
) -> Any:
    """Özel ayarı kaldırır: o kapsamda yeniden okul değeri geçerli olur."""
    return KurallarServisi(oturum).ozel_kaldir(tur, ders_id, sinif_id, ogretmen_id)


program_router = APIRouter(prefix="/programlar", tags=["program"])


@program_router.post("", response_model=semalar.ProgramYanit, status_code=202)
def program_uret(veri: semalar.ProgramUret, oturum: OkulOturumu, kuyruk: Kuyruk, istek: Request,
                 yanit: Response) -> Any:
    """Program üretme isteği. Üretim arka planda çalışır: 202 (kabul edildi) ve `bekliyor`
    durumundaki program döner; durum `GET /programlar/{id}` ile izlenir.

    409: okulun devam eden bir üretimi var. 503: iş kuyruğuna ulaşılamadı (program `basarisiz`
    olarak kaydedilir)."""
    program = ProgramServisi(oturum, kuyruk).uret(veri.ad, veri.temel_program_id, veri.sure_siniri_sn)
    yanit.headers["Location"] = f"{istek.url.path.rstrip('/')}/{program.id}"
    return program


@program_router.get("", response_model=list[semalar.ProgramYanit])
def programlari_listele(oturum: OkulOturumu, kuyruk: Kuyruk) -> Any:
    return ProgramServisi(oturum, kuyruk).listele()


@program_router.get("/{program_id}", response_model=semalar.ProgramYanit)
def program_getir(program_id: uuid.UUID, oturum: OkulOturumu, kuyruk: Kuyruk) -> Any:
    """Programın durumu. Arayüz üretim sürerken bunu birkaç saniyede bir sorar (polling)."""
    return ProgramServisi(oturum, kuyruk).getir(program_id)


@program_router.get("/{program_id}/yerlesimler", response_model=list[semalar.YerlesimYanit])
def program_yerlesimleri(program_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    return ProgramServisi(oturum).yerlesimler(program_id)


# Özel yollar (/uygula) CRUD'un /{kayit_id} yollarından önce eklenir.
router.include_router(sablon_router)
router.include_router(atama_router)
router.include_router(kural_router)
for alt in (
    crud_router("/seviye-sablonlari", SeviyeSablonuServisi, semalar.SeviyeSablonuOlustur,
                semalar.SeviyeSablonuGuncelle, semalar.SeviyeSablonuYanit, "seviye şablonu"),
    crud_router("/atamalar", DersAtamaServisi, semalar.DersAtamaOlustur, semalar.DersAtamaGuncelle,
                semalar.DersAtamaYanit, "ders atama"),
    crud_router("/musaitlikler", MusaitlikServisi, semalar.MusaitlikOlustur, semalar.MusaitlikGuncelle,
                semalar.MusaitlikYanit, "müsaitlik"),
    crud_router("/kisitlar", KisitServisi, semalar.KisitOlustur, semalar.KisitGuncelle,
                semalar.KisitYanit, "kısıt"),
    program_router,
):
    router.include_router(alt)
