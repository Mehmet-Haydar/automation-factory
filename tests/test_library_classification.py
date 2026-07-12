"""
I-1 — IP sızıntı koruyucu testleri (library_store + tia_export).

Test stratejisi:
- Fix varken GEÇMELİ: CONFIDENTIAL/RESTRICTED kaynak reddedilir.
- Fix geri alınırsa KIRILMALI: smoke değil, koruyucu davranışı assert eder.
  (IPClassificationError / TIAExportClassificationError fırlatılır; PUBLIC geçer.)

sys.path düzenlemesi: workbench/core ve 05_SCRIPTS her iki modülü de içerir.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

# -- sys.path kurulumu -------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKBENCH_CORE = REPO_ROOT / "workbench" / "core"
SCRIPTS_DIR = REPO_ROOT / "05_SCRIPTS"

for _p in (str(WORKBENCH_CORE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from library_store import (  # noqa: E402
    IPClassificationError,
    LibraryBlock,
    _check_source_classification,
    import_block_to_project,
)
from tia_export import (  # noqa: E402
    TIAExportClassificationError,
    _check_project_classification_for_export,
    prepare_tia_package,
)


# -- Yardımcı ----------------------------------------------------------------

def _make_project_state(tmp_path: Path, classification: str) -> Path:
    """tmp_path'e PROJECT_STATE.json yazar, proje dizinini döndürür."""
    state = {"data_classification": classification, "project_id": "TEST-001"}
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def _make_dummy_scl(directory: Path, name: str = "FB_Test.scl") -> Path:
    """Boş/minimal .scl dosyası yarat, yolunu döndür."""
    directory.mkdir(parents=True, exist_ok=True)
    scl = directory / name
    scl.write_text("FUNCTION_BLOCK FB_Test\nEND_FUNCTION_BLOCK\n", encoding="utf-8")
    return scl


def _make_library_block(scl_path: Path) -> LibraryBlock:
    return LibraryBlock(
        name=scl_path.stem,
        category="test",
        version="1.0.0",
        platform="S7_1500",
        scl_path=scl_path,
        meta_path=None,
        description="test block",
    )


# ============================================================================
# _check_source_classification testleri
# ============================================================================

class TestCheckSourceClassification:

    def test_confidential_project_rejected(self, tmp_path):
        """CONFIDENTIAL proje → IPClassificationError fırlatılmalı."""
        proj = _make_project_state(tmp_path, "CONFIDENTIAL")
        scl = _make_dummy_scl(tmp_path / "src")
        with pytest.raises(IPClassificationError) as exc_info:
            _check_source_classification(scl, proj)
        assert "CONFIDENTIAL" in str(exc_info.value)

    def test_restricted_project_rejected(self, tmp_path):
        """RESTRICTED proje → IPClassificationError fırlatılmalı."""
        proj = _make_project_state(tmp_path, "RESTRICTED")
        scl = _make_dummy_scl(tmp_path / "src")
        with pytest.raises(IPClassificationError) as exc_info:
            _check_source_classification(scl, proj)
        assert "RESTRICTED" in str(exc_info.value)

    def test_public_project_allowed(self, tmp_path):
        """PUBLIC proje → hata fırlatılmamalı."""
        proj = _make_project_state(tmp_path, "PUBLIC")
        scl = _make_dummy_scl(tmp_path / "src")
        _check_source_classification(scl, proj)  # istisna yok → geçer

    def test_internal_project_allowed(self, tmp_path):
        """INTERNAL proje → hata fırlatılmamalı."""
        proj = _make_project_state(tmp_path, "INTERNAL")
        scl = _make_dummy_scl(tmp_path / "src")
        _check_source_classification(scl, proj)  # istisna yok → geçer

    def test_missing_state_file_is_failclosed(self, tmp_path):
        """PROJECT_STATE.json yoksa → fail-closed: CONFIDENTIAL varsayılır, reddedilir."""
        scl = _make_dummy_scl(tmp_path / "src")
        # tmp_path'de PROJECT_STATE.json yok
        with pytest.raises(IPClassificationError):
            _check_source_classification(scl, tmp_path)

    def test_missing_field_is_failclosed(self, tmp_path):
        """data_classification alanı yoksa → fail-closed: CONFIDENTIAL varsayılır."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"project_id": "X"}', encoding="utf-8"
        )
        scl = _make_dummy_scl(tmp_path / "src")
        with pytest.raises(IPClassificationError):
            _check_source_classification(scl, tmp_path)

    def test_corrupt_json_is_failclosed(self, tmp_path):
        """Bozuk JSON → fail-closed: CONFIDENTIAL varsayılır."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            "{ BAD JSON !!!", encoding="utf-8"
        )
        scl = _make_dummy_scl(tmp_path / "src")
        with pytest.raises(IPClassificationError):
            _check_source_classification(scl, tmp_path)

    def test_unknown_classification_value_is_failclosed(self, tmp_path):
        """Tanınmayan sınıflandırma değeri → fail-closed: CONFIDENTIAL varsayılır."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "SUPER_SECRET"}', encoding="utf-8"
        )
        scl = _make_dummy_scl(tmp_path / "src")
        with pytest.raises(IPClassificationError):
            _check_source_classification(scl, tmp_path)

    def test_error_message_includes_filename(self, tmp_path):
        """Hata mesajı dosya adını içermeli (tanımlama kolaylığı)."""
        proj = _make_project_state(tmp_path, "CONFIDENTIAL")
        scl = _make_dummy_scl(tmp_path / "src", "FB_Gizli_Motor.scl")
        with pytest.raises(IPClassificationError) as exc_info:
            _check_source_classification(scl, proj)
        assert "FB_Gizli_Motor.scl" in str(exc_info.value)


# ============================================================================
# import_block_to_project testleri
# ============================================================================

class TestImportBlockToProject:

    def test_confidential_project_blocks_import(self, tmp_path):
        """CONFIDENTIAL proje → kütüphane bloğu içe aktarılamaz."""
        src_dir = tmp_path / "lib_src"
        scl = _make_dummy_scl(src_dir)
        block = _make_library_block(scl)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _make_project_state(project_dir, "CONFIDENTIAL")

        with pytest.raises(IPClassificationError):
            import_block_to_project(block, project_dir)

        # Dosya kopyalanmamış olmalı
        assert not (project_dir / "SCL" / scl.name).exists()

    def test_public_project_allows_import(self, tmp_path):
        """PUBLIC proje → kütüphane bloğu içe aktarılabilir."""
        src_dir = tmp_path / "lib_src"
        scl = _make_dummy_scl(src_dir)
        block = _make_library_block(scl)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _make_project_state(project_dir, "PUBLIC")

        dest = import_block_to_project(block, project_dir)
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == scl.read_text(encoding="utf-8")

    def test_no_state_file_blocks_import(self, tmp_path):
        """PROJECT_STATE.json olmayan proje → fail-closed, içe aktarım reddedilir."""
        src_dir = tmp_path / "lib_src"
        scl = _make_dummy_scl(src_dir)
        block = _make_library_block(scl)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # PROJECT_STATE.json eklenmedi

        with pytest.raises(IPClassificationError):
            import_block_to_project(block, project_dir)

    def test_file_exists_error_still_raised_for_public(self, tmp_path):
        """PUBLIC projede hedef dosya varsa FileExistsError fırlatılmalı."""
        src_dir = tmp_path / "lib_src"
        scl = _make_dummy_scl(src_dir)
        block = _make_library_block(scl)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _make_project_state(project_dir, "PUBLIC")

        # İlk kopyalama başarılı
        import_block_to_project(block, project_dir)

        # İkinci kopyalama: FileExistsError (classification geçti, çakışma var)
        with pytest.raises(FileExistsError):
            import_block_to_project(block, project_dir)


# ============================================================================
# _check_project_classification_for_export (tia_export) testleri
# ============================================================================

class TestTIAExportClassificationCheck:

    def test_confidential_project_rejected(self, tmp_path):
        """CONFIDENTIAL proje → TIAExportClassificationError fırlatılmalı."""
        _make_project_state(tmp_path, "CONFIDENTIAL")
        with pytest.raises(TIAExportClassificationError) as exc_info:
            _check_project_classification_for_export(tmp_path)
        assert "CONFIDENTIAL" in str(exc_info.value)

    def test_restricted_project_rejected(self, tmp_path):
        """RESTRICTED proje → TIAExportClassificationError fırlatılmalı."""
        _make_project_state(tmp_path, "RESTRICTED")
        with pytest.raises(TIAExportClassificationError):
            _check_project_classification_for_export(tmp_path)

    def test_public_project_allowed(self, tmp_path):
        """PUBLIC proje → hata fırlatılmamalı."""
        _make_project_state(tmp_path, "PUBLIC")
        _check_project_classification_for_export(tmp_path)  # istisna yok → geçer

    def test_internal_project_allowed(self, tmp_path):
        """INTERNAL proje → hata fırlatılmamalı."""
        _make_project_state(tmp_path, "INTERNAL")
        _check_project_classification_for_export(tmp_path)  # istisna yok → geçer

    def test_missing_state_is_failclosed(self, tmp_path):
        """PROJECT_STATE.json yoksa → fail-closed."""
        with pytest.raises(TIAExportClassificationError):
            _check_project_classification_for_export(tmp_path)

    def test_missing_field_is_failclosed(self, tmp_path):
        """data_classification alanı yoksa → fail-closed."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"project_id": "X"}', encoding="utf-8"
        )
        with pytest.raises(TIAExportClassificationError):
            _check_project_classification_for_export(tmp_path)

    def test_corrupt_json_is_failclosed(self, tmp_path):
        """Bozuk JSON → fail-closed."""
        (tmp_path / "PROJECT_STATE.json").write_text("{ BAD }", encoding="utf-8")
        with pytest.raises(TIAExportClassificationError):
            _check_project_classification_for_export(tmp_path)


# ============================================================================
# prepare_tia_package entegrasyon testi
# ============================================================================

class TestPrepareTIAPackageClassificationGate:

    def test_confidential_project_blocks_tia_export(self, tmp_path):
        """CONFIDENTIAL proje → prepare_tia_package başlamadan reddedilmeli."""
        _make_project_state(tmp_path, "CONFIDENTIAL")
        scl_dir = tmp_path / "_output" / "scl"
        scl_dir.mkdir(parents=True)
        (scl_dir / "FB_Test.scl").write_text(
            "FUNCTION_BLOCK FB_Test\nEND_FUNCTION_BLOCK\n", encoding="utf-8"
        )
        with pytest.raises(TIAExportClassificationError):
            prepare_tia_package(tmp_path)

        # TIA import klasörü oluşturulmamış olmalı
        assert not (tmp_path / "_output" / "tia_import").exists()

    def test_public_project_allows_tia_export(self, tmp_path):
        """PUBLIC proje → prepare_tia_package çalışır."""
        _make_project_state(tmp_path, "PUBLIC")
        # SCL dosyası yok → sadece checklist üretilmeli (uyarıyla)
        result = prepare_tia_package(tmp_path)
        assert result is not None
        # Uyarı var (SCL dosyası yok) ama exception yok
        assert any("SCL" in w for w in result.warnings)
