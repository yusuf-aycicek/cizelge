"""Altyapı: sağlık kontrolü, modül yükleme, migration dalları ve mimari kural."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from conftest import TEST_URL, bos_veritabani_olustur
from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek.modul import ModulHatasi, modulleri_yukle
from okulapi.cekirdek.veritabani import motor_olustur
from okulapi.main import uygulama_olustur
from okulapi.migrasyon import CEKIRDEK_DALI, CEKIRDEK_KOK_REVIZYONU, alembic_ayari

KAYNAK = Path(__file__).resolve().parents[1] / "src" / "okulapi"


# --- sağlık ----------------------------------------------------------------------------


def test_saglik_veritabani_ile(istemci):
    yanit = istemci.get("/api/saglik")
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "ok", "veritabani": "ok", "moduller": ["ders_programi"]}


def test_saglik_veritabani_yoksa_503():
    # Hiçbir şeyin dinlemediği bir port: bağlantı reddedilir.
    ayarlar = Ayarlar(veritabani_url="postgresql+psycopg://x:y@127.0.0.1:1/yok")
    with TestClient(uygulama_olustur(ayarlar)) as istemci:
        yanit = istemci.get("/api/saglik")
    assert yanit.status_code == 503
    assert yanit.json() == {"detail": "Veritabanına ulaşılamıyor"}


# --- modüller --------------------------------------------------------------------------


def test_modul_yukleme():
    [modul] = modulleri_yukle(["ders_programi"])
    assert modul.ad == "ders_programi" and modul.onek == "ders-programi"
    assert modul.migration_dizini.is_dir()


def test_bilinmeyen_modul_anlasilir_hata():
    with pytest.raises(ModulHatasi, match="Modül bulunamadı: kutuphane"):
        modulleri_yukle(["kutuphane"])


def test_cekirdek_modulleri_ice_aktarmaz():
    """Mimari kural (ADR 0008): bağımlılık yalnızca modülden çekirdeğe doğrudur."""
    ihlaller = []
    for dosya in (KAYNAK / "cekirdek").rglob("*.py"):
        agac = ast.parse(dosya.read_text(encoding="utf-8"))
        for dugum in ast.walk(agac):
            adlar = []
            if isinstance(dugum, ast.Import):
                adlar = [a.name for a in dugum.names]
            elif isinstance(dugum, ast.ImportFrom) and dugum.module:
                adlar = [dugum.module]
            ihlaller += [f"{dosya.name}: {ad}" for ad in adlar if ad.startswith("okulapi.moduller")]
    assert ihlaller == []


def test_moduller_birbirini_ice_aktarmaz():
    ihlaller = []
    for modul_dizini in (p for p in (KAYNAK / "moduller").iterdir() if p.is_dir() and p.name != "__pycache__"):
        for dosya in modul_dizini.rglob("*.py"):
            for dugum in ast.walk(ast.parse(dosya.read_text(encoding="utf-8"))):
                if isinstance(dugum, ast.ImportFrom) and dugum.module and dugum.module.startswith("okulapi.moduller."):
                    hedef = dugum.module.split(".")[2]
                    if hedef != modul_dizini.name:
                        ihlaller.append(f"{modul_dizini.name}/{dosya.name} -> {hedef}")
    assert ihlaller == []


# --- migration dalları -----------------------------------------------------------------


def _betikler(ayarlar=None) -> ScriptDirectory:
    return ScriptDirectory.from_config(alembic_ayari(ayarlar or Ayarlar(veritabani_url=TEST_URL)))


def test_her_modulun_kendi_dali_var_ve_cekirdege_bagli():
    """Yeni bir modül eklendiğinde de denetlenir: dal etiketi modül adı, kökü çekirdeğe bağımlı."""
    betikler = _betikler()
    for modul in modulleri_yukle(Ayarlar().etkin_moduller):
        kokler = [r for r in betikler.walk_revisions() if r.down_revision is None
                  and Path(r.path).parent == modul.migration_dizini]
        assert len(kokler) == 1, f"{modul.ad}: tam bir kök revizyon olmalı"
        kok = kokler[0]
        assert kok.branch_labels == {modul.ad}
        assert CEKIRDEK_KOK_REVIZYONU in (kok.dependencies or ())
    cekirdek_kok = betikler.get_revision(CEKIRDEK_KOK_REVIZYONU)
    assert cekirdek_kok.branch_labels == {CEKIRDEK_DALI}


def test_her_dalin_bir_ucu_var():
    """Her dalın (çekirdek ve her modül) betiklerde tam bir uç revizyonu (head) vardır."""
    betikler = _betikler()
    dal_uclari: dict[str, list[str]] = {}
    for uc in betikler.get_heads():
        for etiket in _dal_etiketleri(betikler, uc):
            dal_uclari.setdefault(etiket, []).append(uc)
    assert set(dal_uclari) >= {"cekirdek", "ders_programi"}
    assert all(len(uclar) == 1 for uclar in dal_uclari.values()), dal_uclari


def _dal_etiketleri(betikler: ScriptDirectory, revizyon: str) -> set[str]:
    """Revizyonun ait olduğu dal: kendi down_revision zincirindeki kökün etiketi."""
    betik = betikler.get_revision(revizyon)
    while betik.down_revision is not None:
        betik = betikler.get_revision(betik.down_revision)
    return set(betik.branch_labels)


@pytest.fixture
def ayri_veritabani():
    """Migration sırası testleri için ayrı, boş bir veritabanı (oturumun test veritabanı bozulmasın)."""
    url = make_url(TEST_URL).set(database="okul_test_migrasyon").render_as_string(hide_password=False)
    bos_veritabani_olustur(url)
    yield url


def _alembic_version_satirlari(url: str) -> set[str]:
    motor = motor_olustur(url)
    try:
        with motor.connect() as baglanti:
            if baglanti.execute(text("SELECT to_regclass('alembic_version')")).scalar() is None:
                return set()
            return {s for (s,) in baglanti.execute(text("SELECT version_num FROM alembic_version"))}
    finally:
        motor.dispose()


def _kapanis(revizyonlar) -> set[str]:
    """Revizyonlar ve onların bütün ataları (down_revision) ile bağımlılıkları (depends_on)."""
    betikler = _betikler()
    sonuc: set[str] = set()
    yigin = list(revizyonlar)
    while yigin:
        revizyon = yigin.pop()
        if revizyon in sonuc:
            continue
        sonuc.add(revizyon)
        betik = betikler.get_revision(revizyon)
        for onceki in (betik.down_revision, betik.dependencies):
            if onceki:
                yigin.extend([onceki] if isinstance(onceki, str) else onceki)
    return sonuc


def _uygulanmis_revizyonlar(url: str) -> set[str]:
    """alembic_version yalnızca birbirini kapsamayan uç revizyonları tutar. Bir revizyon,
    atası ya da bağımlılığı olduğu bir uç kayıtlıysa uygulanmıştır."""
    return _kapanis(_alembic_version_satirlari(url))


def _tum_revizyonlar() -> set[str]:
    return {betik.revision for betik in _betikler().walk_revisions()}


def test_modul_dali_tek_basina_yukseltilince_bagimliliklari_da_uygulanir(ayri_veritabani):
    # Yalnızca ders programı dalı istendi: o dalın bütün revizyonları ve bağımlı olduğu çekirdek
    # revizyonları uygulanır; çekirdeğin ders programının bağımlı olmadığı revizyonları uygulanmaz.
    command.upgrade(alembic_ayari(veritabani_url=ayri_veritabani), "ders_programi@head")
    dal_ucu = _betikler().get_revision("ders_programi@head").revision
    beklenen = _kapanis([dal_ucu])
    assert CEKIRDEK_KOK_REVIZYONU in beklenen
    assert _uygulanmis_revizyonlar(ayri_veritabani) == beklenen


def test_cekirdek_modulden_once_uygulanir():
    """Çevrimdışı (--sql) çıktıda çekirdeğin revizyonu modülünkünden önce gelir."""
    import io

    ayar = alembic_ayari(Ayarlar(veritabani_url=TEST_URL))
    ayar.output_buffer = io.StringIO()
    command.upgrade(ayar, "ders_programi@head", sql=True)
    sql = ayar.output_buffer.getvalue()
    assert sql.index("'cekirdek_0001'") < sql.index("'ders_programi_0001'")


def test_upgrade_downgrade_upgrade(ayri_veritabani):
    ayar = alembic_ayari(veritabani_url=ayri_veritabani)
    command.upgrade(ayar, "heads")
    assert _uygulanmis_revizyonlar(ayri_veritabani) == _tum_revizyonlar()
    command.downgrade(ayar, "base")
    assert _alembic_version_satirlari(ayri_veritabani) == set()
    command.upgrade(ayar, "heads")
    assert _uygulanmis_revizyonlar(ayri_veritabani) == _tum_revizyonlar()


def test_okula_ait_tablolara_orm_disi_erisim_yok():
    """Ham SQL (`text(...)`) ve Core tablo nesneleri (`Model.__table__`) ORM okul filtresinden
    geçmez (test_kiraci.py, bilinen sınır). Uygulama kodunda yalnızca izin verilen yerlerde
    kullanılabilirler; RLS (4. alt adım) veritabanı düzeyinde ikinci güvencedir."""
    # saglik.py: SELECT 1 (hiçbir tabloya dokunmaz); kiraci.py: SET LOCAL app.okul_id (okulun
    # veritabanında belirlendiği tek yer).
    izinli = {"saglik.py", "kiraci.py"}
    ihlaller = []
    for dosya in KAYNAK.rglob("*.py"):
        if "migrations" in dosya.parts or "migrasyon" in dosya.parts or dosya.name in izinli:
            continue
        kaynak = dosya.read_text(encoding="utf-8")
        for dugum in ast.walk(ast.parse(kaynak)):
            if isinstance(dugum, ast.Attribute) and dugum.attr == "__table__":
                ihlaller.append(f"{dosya.name}:{dugum.lineno} __table__")
            if isinstance(dugum, ast.Call) and getattr(dugum.func, "id", getattr(dugum.func, "attr", "")) == "text":
                ihlaller.append(f"{dosya.name}:{dugum.lineno} text(...)")
    assert ihlaller == []


def test_modeller_ve_migrationlar_uyumlu(veritabani):
    """`alembic check`: modellerde migration'a yansıtılmamış bir değişiklik yok. Biri modeli
    değiştirip migration yazmayı unutursa bu test kırılır."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    import okulapi.cekirdek.modeller  # noqa: F401
    from okulapi.cekirdek.veritabani import Base

    modulleri_yukle(Ayarlar().etkin_moduller)
    motor = motor_olustur(veritabani)
    try:
        with motor.connect() as baglanti:
            farklar = compare_metadata(MigrationContext.configure(baglanti), Base.metadata)
    finally:
        motor.dispose()
    assert farklar == []
