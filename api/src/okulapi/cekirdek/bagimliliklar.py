"""FastAPI bağımlılıkları: isteğin okulu ve o okula bağlı veritabanı oturumu.

**Geçici:** aktif okul `X-Okul-Id` başlığından okunur. Yapım sırası 4'te (kimlik doğrulama) bu
başlık tamamen kaldırılacak ve okul yalnızca oturumdan (token) belirlenecek (CLAUDE.md bölüm 8).
Okulun belirlendiği tek yer `aktif_okul_id` fonksiyonudur; değişiklik burada yapılacak.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from okulapi.cekirdek.kiraci import okul_oturumu, okulsuz_oturum
from okulapi.cekirdek.kuyruk import IsKuyrugu
from okulapi.cekirdek.modeller import Okul


def aktif_okul_id(x_okul_id: Annotated[uuid.UUID | None, Header()] = None) -> uuid.UUID:
    if x_okul_id is None:
        raise HTTPException(400, "X-Okul-Id başlığı gerekli (geçici; kimlik doğrulama adımında oturumla değişecek)")
    return x_okul_id


def okul_oturumu_al(istek: Request, okul_id: Annotated[uuid.UUID, Depends(aktif_okul_id)]) -> Iterator[Session]:
    """İsteğin okuluna bağlı oturum. Servisler commit eder; burada yalnızca kapatılır (commit
    edilmemiş değişiklik kalmışsa kapanışta geri alınır)."""
    oturum = okul_oturumu(istek.app.state.oturum_fabrikasi, okul_id)
    try:
        if oturum.get(Okul, okul_id) is None:
            raise HTTPException(404, "Okul bulunamadı")
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


OkulOturumu = Annotated[Session, Depends(okul_oturumu_al)]
AktifOkulId = Annotated[uuid.UUID, Depends(aktif_okul_id)]
OkulsuzOturum = Annotated[Session, Depends(okulsuz_oturum_al)]
Kuyruk = Annotated[IsKuyrugu, Depends(kuyruk_al)]
