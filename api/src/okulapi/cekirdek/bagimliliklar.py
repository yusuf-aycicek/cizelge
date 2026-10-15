"""FastAPI bağımlılıkları: isteği yapan (oturum), isteğin okulu ve o okula bağlı veritabanı oturumu.

Aktif okul **yalnızca oturumdan** belirlenir (ADR 0012, CLAUDE.md yapım sırası 4): çerezdeki jeton
`oturum_coz` veritabanı fonksiyonuyla çözülür, oturumun okulu isteğin okuludur. İstemcinin
gönderdiği hiçbir başlık ya da parametre okulu seçemez. Okulun belirlendiği tek yer
`aktif_oturum` fonksiyonudur.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from okulapi.cekirdek.kiraci import okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.kimlik.servis import KimlikServisi, OturumBilgisi
from okulapi.cekirdek.kuyruk import IsKuyrugu
from okulapi.cekirdek.modeller import Okul

OTURUM_GEREKLI = "Oturum açmanız gerekiyor"


def kimlik_servisi(istek: Request) -> KimlikServisi:
    return KimlikServisi(istek.app.state.oturum_fabrikasi, istek.app.state.ayarlar)


def aktif_oturum(istek: Request) -> OturumBilgisi:
    """Çerezdeki jetonun oturumu; yoksa, süresi dolmuşsa ya da geçersizse 401."""
    jeton = istek.cookies.get(istek.app.state.ayarlar.cerez_adi)
    bilgi = kimlik_servisi(istek).oturum_coz(jeton)
    if bilgi is None:
        raise HTTPException(401, OTURUM_GEREKLI)
    return bilgi


def aktif_okul_id(oturum: Annotated[OturumBilgisi, Depends(aktif_oturum)]) -> uuid.UUID:
    return oturum.okul_id


def okul_oturumu_al(istek: Request, okul_id: Annotated[uuid.UUID, Depends(aktif_okul_id)]) -> Iterator[Session]:
    """İsteğin okuluna bağlı oturum. Servisler commit eder; burada yalnızca kapatılır (commit
    edilmemiş değişiklik kalmışsa kapanışta geri alınır)."""
    oturum = okul_oturumu(istek.app.state.oturum_fabrikasi, okul_id)
    try:
        if oturum.get(Okul, okul_id) is None:
            raise HTTPException(401, OTURUM_GEREKLI)
        yield oturum
    finally:
        oturum.close()


def okulsuz_oturum_al(istek: Request) -> Iterator[Session]:
    oturum = okulsuz_oturum(istek.app.state.oturum_fabrikasi)
    try:
        yield oturum
    finally:
        oturum.close()


def kuyruk_al(istek: Request) -> IsKuyrugu:
    return istek.app.state.kuyruk


AktifOturum = Annotated[OturumBilgisi, Depends(aktif_oturum)]
OkulOturumu = Annotated[Session, Depends(okul_oturumu_al)]
AktifOkulId = Annotated[uuid.UUID, Depends(aktif_okul_id)]
OkulsuzOturum = Annotated[Session, Depends(okulsuz_oturum_al)]
Kimlik = Annotated[KimlikServisi, Depends(kimlik_servisi)]
Kuyruk = Annotated[IsKuyrugu, Depends(kuyruk_al)]
