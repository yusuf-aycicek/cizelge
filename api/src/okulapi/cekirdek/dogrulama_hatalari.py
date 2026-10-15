"""İstek doğrulama hataları: Türkçe ve tek biçim (docs/arayuz-plani.md bölüm 2.9).

FastAPI, şemaya uymayan bir isteği pydantic'in İngilizce hata listesiyle yanıtlar:
`{"detail": [{"loc": ["body", "email"], "msg": "String should match pattern ..."}]}`. Bu metinler
okul yöneticisine gösterilemez. Bu işleyici onları arayüzün doğrudan kullanabileceği biçime çevirir:

    {"detail": "Bazı alanlar hatalı", "alanlar": {"okul.ad": "Boş bırakılamaz",
                                                 "email": "Geçerli bir e-posta adresi girin"}}

`alanlar` anahtarları alanın istek gövdesindeki yoludur (iç içe alanlar noktayla). Arayüz her
mesajı ilgili alanın altına yerleştirir. Servislerin kendi hataları (`{"detail": "..."}`) zaten
Türkçe ve tek metindir; iki biçim `detail` alanında ortaktır.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

GENEL_MESAJ = "Bazı alanlar hatalı"
GOVDE_OKUNAMADI = "İstek okunamadı"
KONUMLAR = {"body", "query", "path", "header", "cookie"}


def _mesaj(hata: dict[str, Any], alan: str) -> str:
    tur, ctx = hata.get("type", ""), hata.get("ctx") or {}
    if tur == "missing":
        return "Bu alan gerekli"
    if tur == "string_too_short":
        return "Boş bırakılamaz" if ctx.get("min_length") == 1 else f"En az {ctx.get('min_length')} karakter olmalı"
    if tur == "string_too_long":
        return f"En fazla {ctx.get('max_length')} karakter olabilir"
    if tur == "string_pattern_mismatch":
        return "Geçerli bir e-posta adresi girin" if alan.split(".")[-1] == "email" else "Biçimi geçersiz"
    if tur == "greater_than_equal":
        return f"En az {ctx.get('ge')} olmalı"
    if tur == "less_than_equal":
        return f"En fazla {ctx.get('le')} olabilir"
    if tur == "greater_than":
        return f"{ctx.get('gt')} değerinden büyük olmalı"
    if tur == "less_than":
        return f"{ctx.get('lt')} değerinden küçük olmalı"
    if tur in ("int_parsing", "int_type", "int_from_float"):
        return "Tam sayı olmalı"
    if tur in ("float_parsing", "float_type"):
        return "Sayı olmalı"
    if tur in ("bool_parsing", "bool_type"):
        return "Evet ya da hayır olmalı"
    if tur in ("string_type",):
        return "Metin olmalı"
    if tur in ("uuid_parsing", "uuid_type"):
        return "Geçersiz kimlik"
    if tur == "literal_error":
        secenekler = str(ctx.get("expected", "")).replace("'", "").replace(" or ", " ya da ")
        return f"Şunlardan biri olmalı: {secenekler}"
    if tur in ("dict_type", "model_type", "model_attributes_type"):
        return "Biçimi geçersiz"
    return "Geçersiz değer"


def _alan_yolu(konum: tuple | list) -> str:
    parcalar = [str(p) for p in konum]
    if parcalar and parcalar[0] in KONUMLAR:
        parcalar = parcalar[1:]
    return ".".join(parcalar)


def dogrulama_hatasini_cevir(hatalar: list[dict[str, Any]]) -> dict[str, Any]:
    alanlar: dict[str, str] = {}
    for hata in hatalar:
        if hata.get("type") == "json_invalid":
            return {"detail": GOVDE_OKUNAMADI, "alanlar": {}}
        yol = _alan_yolu(hata.get("loc", ()))
        alanlar.setdefault(yol or "_", _mesaj(hata, yol))  # alan başına ilk hata yeterli
    return {"detail": GENEL_MESAJ, "alanlar": alanlar}


async def dogrulama_hatasi_isleyici(_istek: Request, hata: RequestValidationError) -> JSONResponse:
    return JSONResponse(dogrulama_hatasini_cevir(list(hata.errors())), status_code=422)


def openapi_semasini_uyarla(uygulama) -> None:
    """OpenAPI şemasındaki 422 tanımını (`HTTPValidationError`) gerçek yanıt biçimine çevirir.

    Arayüzün TypeScript tipleri bu şemadan üretilir (docs/arayuz-plani.md bölüm 1); şema yanıtla
    aynı olmazsa arayüz yanlış bir tipe güvenirdi.
    """
    ozgun = uygulama.openapi

    def sema() -> dict[str, Any]:
        if uygulama.openapi_schema is not None:
            return uygulama.openapi_schema
        s = ozgun()
        semalar = s.get("components", {}).get("schemas", {})
        if "HTTPValidationError" in semalar:
            semalar["HTTPValidationError"] = {
                "title": "HTTPValidationError",
                "type": "object",
                "description": "Doğrulama hatası: genel mesaj ve alan yolu -> Türkçe mesaj.",
                "properties": {
                    "detail": {"type": "string", "title": "Detail"},
                    "alanlar": {"type": "object", "additionalProperties": {"type": "string"}, "title": "Alanlar"},
                },
                "required": ["detail", "alanlar"],
            }
            semalar.pop("ValidationError", None)
        uygulama.openapi_schema = s
        return s

    uygulama.openapi = sema
