"""Elle düzeltme (7.1): hazır bir programda ders taşıma, kilitleme ve geri alma.

Karar çözücü paketinin bağımsız doğrulayıcısından gelir (`cozucu.tasima`, `cozucu.dogrulama`);
burada yalnızca veritabanı işi yapılır:

- Program satırı işlem boyunca kilitlenir (FOR UPDATE): aynı programda aynı anda iki taşıma
  birbirinin durumunu görmeden yazamaz.
- Zorunlu kuralı çiğneyen taşıma 422 ile reddedilir (nedenler kullanıcının dilinde); yalnızca esnek
  ölçüyü kötüleştiren taşıma `uyarilari_kabul` olmadan 409 alır.
- Hedefte aynı şubenin başka dersi varsa yer değiştirir (takas, `cozucu.tasima.hareketler`); bütün
  hareketler tek işlemde yazılır.
- Her taşıma ve kilit değişikliği `program_islemi`ne yazılır; geri alma sonuncuyu tersine çevirir.
- Programın kalite ölçümü ve toplam cezası her değişiklikten sonra yeniden hesaplanır (`kalite.olc`,
  `agirlikli_ceza`): elle değiştirilmiş programın özeti güncel kalır.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, replace
from typing import Any

from cozucu.kalite import agirlikli_ceza, bos_gun_notlari, olc
from cozucu.kisitlar import etkin_agirliklar
from cozucu.model import CozumGirdisi
from cozucu.model import Yerlesim as CYerlesim
from cozucu.tasima import ENGEL, UYARI, Degerlendirici, Hareket, TasimaHatasi, blok_hucreleri
from sqlalchemy import delete, func, select, tuple_

from okulapi.cekirdek.servisler import GecersizVeri, KayitBulunamadi, KayitCakismasi
from okulapi.moduller.ders_programi.cozucu_donusturucu import cozum_girdisi_olustur
from okulapi.moduller.ders_programi.modeller import Program, ProgramIslemi, Yerlesim
from okulapi.moduller.ders_programi.uretim import not_sozlukleri

YALNIZCA_HAZIR = "Yalnızca hazır (başarıyla üretilmiş) bir program düzeltilebilir"
GERI_ALINACAK_YOK = "Geri alınacak bir değişiklik yok"


class ElleDuzeltmeServisi:
    def __init__(self, oturum) -> None:
        self.oturum = oturum

    # --- ortak -------------------------------------------------------------------------------

    def _program(self, program_id: uuid.UUID) -> Program:
        program = self.oturum.scalars(select(Program).where(Program.id == program_id).with_for_update()).one_or_none()
        if program is None:
            raise KayitBulunamadi("Program")
        if program.durum != "hazir":
            raise GecersizVeri(YALNIZCA_HAZIR)
        return program

    def _durum(self, program: Program) -> tuple[CozumGirdisi, list[Yerlesim], list[CYerlesim]]:
        # Üretimdeki girdi (temel programın yerleşimleri "değişen yerleşim" ölçüsü için), ama temel
        # programın kilitleri olmadan: bu programın kilitleri kendi yerleşimlerindedir; kullanıcı
        # burada bir dersin kilidini açtıysa temel programdaki kilit onu bağlamamalı.
        girdi = replace(cozum_girdisi_olustur(self.oturum, temel_program_id=program.temel_program_id), kilitli_yerlesimler=[])
        satirlar = list(self.oturum.scalars(select(Yerlesim).where(Yerlesim.program_id == program.id)))
        return girdi, satirlar, [CYerlesim(str(y.ders_atama_id), y.gun, y.saat, y.kilitli) for y in satirlar]

    def _kalite(self, program: Program, girdi: CozumGirdisi, yerlesimler: list[CYerlesim]) -> None:
        olcum = olc(girdi, yerlesimler)
        program.olcumler = asdict(olcum)
        program.toplam_ceza = agirlikli_ceza(olcum, etkin_agirliklar(girdi))
        program.notlar = not_sozlukleri(bos_gun_notlari(girdi, yerlesimler))

    def _islem_ekle(self, program: Program, tur: str, veri: dict[str, Any]) -> None:
        sira = self.oturum.scalar(select(func.coalesce(func.max(ProgramIslemi.sira), 0)).where(ProgramIslemi.program_id == program.id))
        self.oturum.add(ProgramIslemi(program_id=program.id, sira=sira + 1, tur=tur, veri=veri))

    def _uygula(self, program: Program, hareketler: list[Hareket]) -> None:
        """Her hareketin eski hücrelerini siler, yenilerine ekler. Önce hepsi silinip flush edilir:
        kaydırma ve takas eski ve yeni hücreleri örtüştürür, benzersizlik takılmasın."""
        self.oturum.execute(delete(Yerlesim).where(
            Yerlesim.program_id == program.id,
            tuple_(Yerlesim.ders_atama_id, Yerlesim.gun, Yerlesim.saat).in_(
                [(uuid.UUID(h.ders_atama_id), g, s) for h in hareketler for g, s in h.eski]),
        ))
        self.oturum.flush()
        self.oturum.add_all([Yerlesim(program_id=program.id, ders_atama_id=uuid.UUID(h.ders_atama_id), gun=g, saat=s)
                             for h in hareketler for g, s in h.yeni])
        self.oturum.flush()

    # --- taşıma ------------------------------------------------------------------------------

    def harita(self, program_id: uuid.UUID, atama_id: uuid.UUID, gun: int, saat: int) -> dict[str, Any]:
        """Bir dersin taşınabileceği her başlangıç hücresi: uygun / uyarı / engel ve nedenleri."""
        program = self._program(program_id)
        girdi, _satirlar, yerlesimler = self._durum(program)
        try:
            hucreler = blok_hucreleri(girdi, yerlesimler, str(atama_id), gun, saat)
            hedefler = Degerlendirici(girdi, yerlesimler).harita(str(atama_id), gun, saat)
        except TasimaHatasi as hata:
            raise GecersizVeri(str(hata)) from hata
        self.oturum.rollback()  # yalnızca okundu; satır kilidini hemen bırak
        return {
            "hucreler": [{"gun": g, "saat": s} for g, s in hucreler],
            "hedefler": [{"gun": d.gun, "saat": d.saat, "durum": d.durum, "nedenler": list(d.nedenler), "takas": list(d.takas)}
                         for d in hedefler],
        }

    def tasi(self, program_id: uuid.UUID, atama_id: uuid.UUID, gun: int, saat: int, hedef_gun: int, hedef_saat: int,
             uyarilari_kabul: bool) -> tuple[Program, list[str]]:
        program = self._program(program_id)
        girdi, _satirlar, yerlesimler = self._durum(program)
        try:
            hucreler = blok_hucreleri(girdi, yerlesimler, str(atama_id), gun, saat)
        except TasimaHatasi as hata:
            raise GecersizVeri(str(hata)) from hata
        if (hedef_gun, hedef_saat) == hucreler[0]:
            raise GecersizVeri("Ders zaten bu saatte")
        if not all(girdi.ayar.aralikta(hedef_gun, hedef_saat + i) for i in range(len(hucreler))):
            raise GecersizVeri("Ders bu saate sığmıyor: okulun haftasının dışına taşar")
        d = Degerlendirici(girdi, yerlesimler).degerlendir(str(atama_id), gun, saat, hedef_gun, hedef_saat, hucreler)
        if d.durum == ENGEL:
            raise GecersizVeri("Bu taşıma yapılamaz: " + "; ".join(d.nedenler) + ".")
        if d.durum == UYARI and not uyarilari_kabul:
            raise KayitCakismasi("Taşıma programı kötüleştiriyor: " + "; ".join(d.nedenler) + ".")
        self._uygula(program, list(d.hareketler))
        self._islem_ekle(program, "tasima", {"ders_atama_id": str(atama_id), "hareketler": [
            {"ders_atama_id": h.ders_atama_id, "eski": list(h.eski), "yeni": list(h.yeni)} for h in d.hareketler]})
        assert d.olcum is not None
        program.olcumler = asdict(d.olcum)
        program.toplam_ceza = agirlikli_ceza(d.olcum, etkin_agirliklar(girdi))
        self.oturum.flush()
        program.notlar = not_sozlukleri(bos_gun_notlari(girdi, [
            CYerlesim(str(y.ders_atama_id), y.gun, y.saat, y.kilitli)
            for y in self.oturum.scalars(select(Yerlesim).where(Yerlesim.program_id == program.id))]))
        self.oturum.commit()
        return program, list(d.nedenler)

    # --- kilit -------------------------------------------------------------------------------

    def kilitle(self, program_id: uuid.UUID, atama_id: uuid.UUID, gun: int, saat: int, kilitli: bool) -> Program:
        """Dersi (blok dersse bütün bloğu) kilitler ya da kilidini açar. Kilitli ders taşınamaz ve
        bu program temel alınarak üretilen programda yerinde kalır."""
        program = self._program(program_id)
        girdi, satirlar, yerlesimler = self._durum(program)
        try:
            hucreler = set(blok_hucreleri(girdi, yerlesimler, str(atama_id), gun, saat))
        except TasimaHatasi as hata:
            raise GecersizVeri(str(hata)) from hata
        degisen = [y for y in satirlar if y.ders_atama_id == atama_id and (y.gun, y.saat) in hucreler and y.kilitli != kilitli]
        for y in degisen:
            y.kilitli = kilitli
        if degisen:
            self._islem_ekle(program, "kilit", {"ders_atama_id": str(atama_id), "hucreler": sorted((y.gun, y.saat) for y in degisen),
                                                "kilitli": kilitli})
        self.oturum.commit()
        return program

    # --- geri alma ---------------------------------------------------------------------------

    def geri_al(self, program_id: uuid.UUID) -> Program:
        """Son taşımayı ya da kilit değişikliğini tersine çevirir (işlemler sondan başa)."""
        program = self._program(program_id)
        islem = self.oturum.scalars(
            select(ProgramIslemi).where(ProgramIslemi.program_id == program.id).order_by(ProgramIslemi.sira.desc()).limit(1)
        ).one_or_none()
        if islem is None:
            raise KayitCakismasi(GERI_ALINACAK_YOK)
        atama_id = uuid.UUID(islem.veri["ders_atama_id"])
        if islem.tur == "tasima":
            # Tersi: her hareketin yenisinden eskisine.
            self._uygula(program, [Hareket(h["ders_atama_id"], tuple(map(tuple, h["yeni"])), tuple(map(tuple, h["eski"])))
                                   for h in islem.veri["hareketler"]])
        else:
            hucreler = {tuple(h) for h in islem.veri["hucreler"]}
            for y in self.oturum.scalars(select(Yerlesim).where(Yerlesim.program_id == program.id, Yerlesim.ders_atama_id == atama_id)):
                if (y.gun, y.saat) in hucreler:
                    y.kilitli = not islem.veri["kilitli"]
        self.oturum.delete(islem)
        self.oturum.flush()
        girdi, _satirlar, yerlesimler = self._durum(program)
        self._kalite(program, girdi, yerlesimler)
        self.oturum.commit()
        return program


def islem_sayilari(oturum, program_idler: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Program -> geri alınabilir elle değişiklik sayısı."""
    if not program_idler:
        return {}
    sorgu = (select(ProgramIslemi.program_id, func.count()).where(ProgramIslemi.program_id.in_(program_idler))
             .group_by(ProgramIslemi.program_id))
    return {program_id: sayi for program_id, sayi in oturum.execute(sorgu).all()}
