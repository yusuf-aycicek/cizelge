"""Ders programı endpoint'leri (/api/ders-programi/...). Çekirdeğin `crud_router` fabrikasını kullanır.

Not: `from __future__ import annotations` yok (FastAPI tip ipuçlarını çalışma anında okur).
"""

import uuid
from typing import Any

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool

from okulapi.cekirdek.api import crud_router
from okulapi.cekirdek.bagimliliklar import AktifOkulId, Kuyruk, OkulOturumu, OkulsuzOturum
from okulapi.cekirdek.depo import OgretmenDeposu
from okulapi.cekirdek.servisler import KayitBulunamadi
from okulapi.moduller.ders_programi import ice_aktarma, paylasim, semalar
from okulapi.moduller.ders_programi.cikti import excel, pdf
from okulapi.moduller.ders_programi.cikti.model import Cizelge
from okulapi.moduller.ders_programi.cikti.veri import program_ciktisi
from okulapi.moduller.ders_programi.elle import ElleDuzeltmeServisi
from okulapi.moduller.ders_programi.kurallar import KurallarServisi
from okulapi.moduller.ders_programi.servisler import (
    DersAtamaServisi,
    KisitServisi,
    MusaitlikCizelgesiServisi,
    MusaitlikServisi,
    ProgramServisi,
    SeviyeSablonuServisi,
    SubeIstisnasiServisi,
    dagilim_ozeti,
    dagilim_sekilleri,
    on_kontrol_sonucu,
)
from okulapi.moduller.ders_programi.yayin import YayinServisi

router = APIRouter()

sablon_router = APIRouter(prefix="/seviye-sablonlari", tags=["seviye şablonu"])


@sablon_router.post("/uygula", response_model=semalar.SablonUygulamaSonucu)
def sablonu_uygula(veri: semalar.SablonUygula, oturum: OkulOturumu) -> Any:
    """Seviyenin şablonunu o seviyedeki her şubeye uygular (öğretmeni boş atamalar)."""
    return SeviyeSablonuServisi(oturum).uygula(veri.seviye, veri.sube_grubu_id)


istisna_router = APIRouter(prefix="/istisnalar", tags=["şube istisnası"])


@istisna_router.get("", response_model=list[semalar.SubeIstisnasiYanit])
def istisnalari_listele(oturum: OkulOturumu) -> Any:
    """Şubelerin şablondan ayrıldığı dersler; ders dağılımıyla tutarsız olanlar `uyari` taşır."""
    return SubeIstisnasiServisi(oturum).listele()


@istisna_router.post("", response_model=semalar.SubeIstisnasiYanit, status_code=201)
def istisna_ekle(veri: semalar.SubeIstisnasiOlustur, oturum: OkulOturumu) -> Any:
    """"Almaz": şubenin o dersi kaldırılır ve şablon yeniden uygulansa da geri gelmez. "Ek": ders
    şubede yoksa istisnadaki saatle eklenir. 409: bu şubenin bu ders için zaten istisnası var."""
    return SubeIstisnasiServisi(oturum).olustur(veri.sinif_id, veri.ders_id, veri.tur, veri.haftalik_saat)


@istisna_router.delete("/{istisna_id}", response_model=semalar.IstisnaKaldirmaSonucu)
def istisna_kaldir(istisna_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    """İstisnayı kaldırır; "almaz" kalkınca ders şubenin şablonundaysa geri eklenir."""
    return SubeIstisnasiServisi(oturum).sil(istisna_id)


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
    return KurallarServisi(oturum).ozel_ayarla(tur, veri.kapsam.model_dump(), veri.parametreler)


@kural_router.get("/{tur}/ozel/etki", response_model=semalar.OzelAyarEtkisi)
def ozel_ayar_etkisi(
    tur: str, oturum: OkulOturumu, ogretmen_id: uuid.UUID | None = None, ders_id: uuid.UUID | None = None,
    sinif_id: uuid.UUID | None = None, sube_grubu_id: uuid.UUID | None = None,
) -> Any:
    """Kaydetmeden önce: bu kapsama verilecek özel ayar hangi özel ayarları ezer, hangileri onu ezer
    (kapsam önceliği, ADR 0016). 422: kural bu kapsamda ayarlanamıyor."""
    kapsam = {"ders_id": ders_id, "sinif_id": sinif_id, "sube_grubu_id": sube_grubu_id, "ogretmen_id": ogretmen_id}
    return KurallarServisi(oturum).ozel_etki(tur, kapsam)


@kural_router.delete("/{tur}/ozel", response_model=semalar.KuralYanit)
def ozel_ayari_kaldir(
    tur: str, oturum: OkulOturumu, ogretmen_id: uuid.UUID | None = None, ders_id: uuid.UUID | None = None,
    sinif_id: uuid.UUID | None = None, sube_grubu_id: uuid.UUID | None = None,
) -> Any:
    """Özel ayarı kaldırır: o kapsamda yeniden okul değeri geçerli olur."""
    kapsam = {"ders_id": ders_id, "sinif_id": sinif_id, "sube_grubu_id": sube_grubu_id, "ogretmen_id": ogretmen_id}
    return KurallarServisi(oturum).ozel_kaldir(tur, kapsam)


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


@program_router.patch("/{program_id}", response_model=semalar.ProgramYanit)
def program_adlandir(program_id: uuid.UUID, veri: semalar.ProgramAdi, oturum: OkulOturumu) -> Any:
    return ProgramServisi(oturum).yeniden_adlandir(program_id, veri.ad.strip())


@program_router.delete("/{program_id}", status_code=204)
def program_sil(program_id: uuid.UUID, oturum: OkulOturumu) -> Response:
    """409: üretimi süren program silinemez."""
    ProgramServisi(oturum).sil(program_id)
    return Response(status_code=204)


@program_router.get("/{program_id}/fark", response_model=semalar.ProgramFarki)
def program_farki(program_id: uuid.UUID, oturum: OkulOturumu, ile: uuid.UUID | None = None) -> Any:
    """Bu programın `ile` programından (verilmezse temel programından) farklı hücreleri. 422: karşılaştırılacak program yok."""
    return ProgramServisi(oturum).fark(program_id, ile)


@program_router.get("/{program_id}/tasima", response_model=semalar.TasimaHaritasi)
def tasima_haritasi(program_id: uuid.UUID, ders_atama_id: uuid.UUID, gun: int, saat: int, oturum: OkulOturumu) -> Any:
    """Elle düzeltme (7.1): dersin (blok dersse bütün bloğun) taşınabileceği her başlangıç hücresi;
    uygun / uyarı (esnek ölçü kötüleşir) / engel (zorunlu kural) ve nedenleri."""
    return ElleDuzeltmeServisi(oturum).harita(program_id, ders_atama_id, gun, saat)


@program_router.post("/{program_id}/tasi", response_model=semalar.ProgramYanit)
def ders_tasi(program_id: uuid.UUID, veri: semalar.TasimaIstegi, oturum: OkulOturumu) -> Any:
    """422: zorunlu kuralı çiğner (nedenler mesajda). 409: esnek ölçüyü kötüleştirir ve
    `uyarilari_kabul` verilmedi. Başarıda programın güncel hâli (kalite ölçümü yeniden hesaplanır)."""
    ElleDuzeltmeServisi(oturum).tasi(program_id, veri.ders_atama_id, veri.gun, veri.saat, veri.hedef_gun,
                                     veri.hedef_saat, veri.uyarilari_kabul)
    return ProgramServisi(oturum).getir(program_id)


@program_router.put("/{program_id}/kilit", response_model=semalar.ProgramYanit)
def ders_kilitle(program_id: uuid.UUID, veri: semalar.KilitIstegi, oturum: OkulOturumu) -> Any:
    ElleDuzeltmeServisi(oturum).kilitle(program_id, veri.ders_atama_id, veri.gun, veri.saat, veri.kilitli)
    return ProgramServisi(oturum).getir(program_id)


@program_router.post("/{program_id}/geri-al", response_model=semalar.ProgramYanit)
def degisikligi_geri_al(program_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    """Son elle değişikliği geri alır. 409: geri alınacak değişiklik yok."""
    ElleDuzeltmeServisi(oturum).geri_al(program_id)
    return ProgramServisi(oturum).getir(program_id)


@program_router.get("/{program_id}/yerlesimler", response_model=list[semalar.YerlesimYanit])
def program_yerlesimleri(program_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    return ProgramServisi(oturum).yerlesimler(program_id)


PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_CIKTI_YANITLARI = {404: {"description": "Program, şube ya da öğretmen bu okulda yok"},
                    409: {"description": "Program hazır değil"}}


def _dosya(icerik: bytes, tur: str, ad: str) -> Response:
    """İndirilen dosya. Türkçe ad `filename*` ile (RFC 5987), eski tarayıcılar için ASCII yedekle."""
    ascii_ad = ad.encode("ascii", "ignore").decode() or "program"
    return Response(icerik, media_type=tur, headers={
        "Content-Disposition": f"attachment; filename=\"{ascii_ad}\"; filename*=UTF-8''{quote(ad)}"})


def _sec(cizelgeler: list[Cizelge], kimlik: uuid.UUID | None, varlik: str) -> list[Cizelge]:
    """Hepsi ya da yalnızca seçilen şube/öğretmen (404: bu okulda yok)."""
    if kimlik is None:
        return cizelgeler
    secili = [c for c in cizelgeler if c.kimlik == kimlik]
    if not secili:
        raise KayitBulunamadi(varlik)
    return secili


@program_router.get("/{program_id}/cikti/subeler.pdf", response_class=Response, responses=_CIKTI_YANITLARI)
def subeler_pdf(program_id: uuid.UUID, oturum: OkulOturumu, sinif_id: uuid.UUID | None = None,
                imza: bool = False) -> Response:
    """Şube programları, her şube ayrı sayfa (A4 yatay). `sinif_id`: yalnızca o şube. `imza`: "Okul Müdürü" alanı."""
    cikti = program_ciktisi(oturum, program_id)
    secili = _sec(cikti.subeler, sinif_id, "Şube")
    ad = f"{secili[0].ad} programı.pdf" if sinif_id else "Şube programları.pdf"
    return _dosya(pdf.haftalik_pdf(cikti, secili, "Şube programları", imza), PDF, ad)


@program_router.get("/{program_id}/cikti/ogretmenler.pdf", response_class=Response, responses=_CIKTI_YANITLARI)
def ogretmenler_pdf(program_id: uuid.UUID, oturum: OkulOturumu, ogretmen_id: uuid.UUID | None = None,
                    imza: bool = False) -> Response:
    """Öğretmen programları, her öğretmen ayrı sayfa, haftalık toplam ders saatiyle (A4 yatay)."""
    cikti = program_ciktisi(oturum, program_id)
    ogretmen = OgretmenDeposu(oturum).getir(ogretmen_id) if ogretmen_id else None
    if ogretmen is not None and not any(c.kimlik == ogretmen.id for c in cikti.ogretmenler):
        # Programda dersi olmayan öğretmen tek başına istenirse boş haftası verilir.
        cikti.ogretmenler.append(Cizelge(ad=ogretmen.ad, tur="ogretmen", hucreler=[], kimlik=ogretmen.id))
    secili = _sec(cikti.ogretmenler, ogretmen_id, "Öğretmen")
    ad = f"{secili[0].ad} programı.pdf" if ogretmen_id else "Öğretmen programları.pdf"
    return _dosya(pdf.haftalik_pdf(cikti, secili, "Öğretmen programları", imza), PDF, ad)


@program_router.get("/{program_id}/cikti/carsaf.pdf", response_class=Response, responses=_CIKTI_YANITLARI)
def carsaf_pdf(program_id: uuid.UUID, oturum: OkulOturumu,
               satir: Literal["ogretmen", "sube"] = Query("ogretmen")) -> Response:
    """Çarşaf liste: bütün okul tek tabloda (A3 yatay); satırlar öğretmenler ya da şubeler."""
    cikti = program_ciktisi(oturum, program_id)
    ad = "Çarşaf liste (öğretmenler).pdf" if satir == "ogretmen" else "Çarşaf liste (şubeler).pdf"
    return _dosya(pdf.carsaf_pdf(cikti, satir), PDF, ad)


@program_router.get("/{program_id}/cikti/program.xlsx", response_class=Response, responses=_CIKTI_YANITLARI)
def program_excel(program_id: uuid.UUID, oturum: OkulOturumu) -> Response:
    """Excel: şubeler, öğretmenler, çarşaf listeler ve filtrelenebilir ders listesi sekmeleri."""
    cikti = program_ciktisi(oturum, program_id)
    return _dosya(excel.program_xlsx(cikti), XLSX, f"{cikti.program}.xlsx")


ice_router = APIRouter(prefix="/ice-aktarma", tags=["içe aktarma"])
_XLSX_GOVDE = {"requestBody": {"required": True, "content": {XLSX: {"schema": {"type": "string", "format": "binary"}}}}}


async def _yuklenen_dosya(istek: Request) -> bytes:
    """İstek gövdesi dosyanın kendisidir (multipart değil). Sınırı aşan dosya sonuna kadar okunmaz (413)."""
    parcalar, boyut = [], 0
    async for parca in istek.stream():
        boyut += len(parca)
        if boyut > ice_aktarma.MAKS_BOYUT:
            raise HTTPException(413, f"Dosya çok büyük: en çok {ice_aktarma.MAKS_BOYUT // (1024 * 1024)} MB yüklenebilir")
        parcalar.append(parca)
    return b"".join(parcalar)


@ice_router.get("/sablon.xlsx", response_class=Response,
                responses={200: {"content": {XLSX: {}}, "description": "Boş şablon"}})
def ice_aktarma_sablonu(_okul_id: AktifOkulId) -> Response:
    """Öğretmenler, Sınıflar, Dersler, Ders dağılımı sayfaları; her birinde açıklama ve örnek satır."""
    return _dosya(ice_aktarma.sablon_xlsx(), XLSX, "İçe aktarma şablonu.xlsx")


@ice_router.post("/onizleme", response_model=semalar.IceAktarmaOnizleme, openapi_extra=_XLSX_GOVDE,
                 responses={413: {"description": "Dosya çok büyük"}, 422: {"description": "Dosya okunamadı"}})
async def ice_aktarma_onizleme(istek: Request, oturum: OkulOturumu) -> Any:
    """Dosyayı okur, her satırda ne olacağını söyler (eklenecek, güncellenecek, hatalı). Kaydetmez."""
    icerik = await _yuklenen_dosya(istek)
    return (await run_in_threadpool(ice_aktarma.onizle, oturum, icerik)).yanit()


@ice_router.post("", response_model=semalar.IceAktarmaSonucu, openapi_extra=_XLSX_GOVDE,
                 responses={409: {"description": "Veri önizlemeden sonra değişti"},
                            413: {"description": "Dosya çok büyük"}, 422: {"description": "Hatalı satır var"}})
async def ice_aktar(istek: Request, oturum: OkulOturumu, ozet: str = Query(max_length=64)) -> Any:
    """Önizlenen dosyayı tek işlemde kaydeder; hatalı satır varsa hiçbiri. `ozet`: önizlemenin özeti."""
    icerik = await _yuklenen_dosya(istek)
    return await run_in_threadpool(ice_aktarma.kaydet, oturum, icerik, ozet)


yayin_router = APIRouter(prefix="/yayin", tags=["yayın"])


@yayin_router.get("", response_model=semalar.YayinDurumu | None)
def yayin_durumu(oturum: OkulOturumu) -> Any:
    """Okulun yayınlanan programı (yoksa null) ve güncel olmama nedenleri."""
    return YayinServisi(oturum).durum()


@yayin_router.put("", response_model=semalar.YayinDurumu, responses=_CIKTI_YANITLARI)
def yayinla(veri: semalar.YayinIstegi, oturum: OkulOturumu) -> Any:
    """Programı yayınlar: içeriği dondurulur (sonradan atama, öğretmen ya da ders silinse de
    değişmez). Var olan yayının yerini alır; paylaşım linkleri aynı kalır."""
    return YayinServisi(oturum).yayinla(veri.program_id)


@yayin_router.delete("", status_code=204)
def yayini_kaldir(oturum: OkulOturumu) -> Response:
    """404: yayın yok."""
    YayinServisi(oturum).kaldir()
    return Response(status_code=204)


link_router = APIRouter(prefix="/paylasim-linkleri", tags=["paylaşım"])


@link_router.get("", response_model=list[semalar.PaylasimLinkiYanit])
def linkleri_listele(oturum: OkulOturumu) -> Any:
    return paylasim.PaylasimServisi(oturum).listele()


@link_router.post("", response_model=semalar.PaylasimLinkiYanit)
def link_olustur(veri: semalar.PaylasimLinkiOlustur, oturum: OkulOturumu) -> Any:
    """Kapsamın (okul, öğretmen ya da şube) linki; zaten varsa o döner."""
    return paylasim.PaylasimServisi(oturum).olustur(veri.tur, veri.ogretmen_id, veri.sinif_id)


@link_router.post("/toplu", response_model=list[semalar.PaylasimLinkiYanit])
def toplu_link_olustur(veri: semalar.TopluLinkIstegi, oturum: OkulOturumu) -> Any:
    """Linki olmayan bütün öğretmenlere ya da şubelere link; o türün bütün linkleri döner."""
    return paylasim.PaylasimServisi(oturum).toplu_olustur(veri.tur)


@link_router.post("/{link_id}/yenile", response_model=semalar.PaylasimLinkiYanit)
def link_yenile(link_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    """Yeni jeton; eski link o anda çalışmaz olur."""
    return paylasim.PaylasimServisi(oturum).yenile(link_id)


@link_router.delete("/{link_id}", status_code=204)
def link_iptal(link_id: uuid.UUID, oturum: OkulOturumu) -> Response:
    paylasim.PaylasimServisi(oturum).iptal(link_id)
    return Response(status_code=204)


# Girişsiz uçlar: oturum yok, okul bağlamı açılmaz (OkulsuzOturum). İçerik veritabanında, jetonun
# kapsamına göre süzülür (paylasim_icerigi, ADR 0022).
acik_router = APIRouter(prefix="/paylasim", tags=["paylaşım (girişsiz)"])
_GIZLI = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex"}
_LINK_YOK = "Paylaşım linki bulunamadı"


def _paylasim(oturum, jeton: str) -> dict:
    veri = paylasim.icerik(oturum, jeton)
    if veri is None:
        raise HTTPException(404, _LINK_YOK, headers=_GIZLI)
    return veri


@acik_router.get("/{jeton}", response_model=semalar.PaylasimYanit, responses={404: {"description": "Link yok ya da iptal edildi"}})
def paylasim_goster(jeton: str, oturum: OkulsuzOturum, yanit: Response) -> Any:
    """Linkin kapsamındaki yayınlanmış program (giriş gerekmez)."""
    veri = _paylasim(oturum, jeton)
    yanit.headers.update(_GIZLI)
    icerik = veri["icerik"]
    if icerik is None:
        return {"tur": veri["tur"], "yayinda": False, "yayin_zamani": None, "okul": "", "program": "", "hafta": None,
                "subeler": [], "ogretmenler": []}
    return {"tur": veri["tur"], "yayinda": True, "yayin_zamani": veri["yayin_zamani"], "okul": icerik["okul"],
            "program": icerik["program"], "hafta": icerik["hafta"], "subeler": icerik["subeler"],
            "ogretmenler": icerik["ogretmenler"]}


@acik_router.get("/{jeton}/program.pdf", response_class=Response,
                 responses={404: {"description": "Link yok, iptal edildi ya da yayında program yok"}})
def paylasim_pdf(jeton: str, oturum: OkulsuzOturum, sube: str | None = None, ogretmen: str | None = None) -> Response:
    """Linkin kapsamındaki programın PDF'i. Okul linkinde `sube` ya da `ogretmen` (adıyla) tek sayfa
    seçer; seçim yalnızca linkin zaten gördüğü çizelgeler arasında yapılır."""
    veri = _paylasim(oturum, jeton)
    if veri["icerik"] is None:
        raise HTTPException(404, "Yayında program yok", headers=_GIZLI)
    cikti = paylasim.cikti_modeli(veri)
    cizelgeler = cikti.subeler + cikti.ogretmenler
    if sube is not None or ogretmen is not None:
        cizelgeler = [c for c in cizelgeler if (c.tur, c.ad) in {("sube", sube), ("ogretmen", ogretmen)}]
        if not cizelgeler:
            raise HTTPException(404, "Bu linkte böyle bir şube ya da öğretmen yok", headers=_GIZLI)
    ad = cizelgeler[0].ad if len(cizelgeler) == 1 else cikti.okul
    yanit = _dosya(pdf.haftalik_pdf(cikti, cizelgeler, "Ders programı"), PDF, f"{ad} programı.pdf")
    yanit.headers.update(_GIZLI)
    return yanit


# Özel yollar (/uygula) CRUD'un /{kayit_id} yollarından önce eklenir.
router.include_router(sablon_router)
router.include_router(atama_router)
router.include_router(kural_router)
router.include_router(istisna_router)
router.include_router(ice_router)
router.include_router(yayin_router)
router.include_router(link_router)
router.include_router(acik_router)
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
