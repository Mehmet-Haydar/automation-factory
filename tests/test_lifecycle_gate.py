"""S-15 — Kütüphane lifecycle VALIDATED politikası.

Proof testler (B-P1 domain kararı):
- VALIDATED olmayan (DRAFT, vb.) blok kullanan assembly'de assembler UYARI üretir.
- VALIDATED blok kullanımında UYARI üretilmez.
- promote_to_validated(): kanıtsız çağrı → LifecyclePromoteError (fail-closed).
- promote_to_validated(): boş mühendis adı → LifecyclePromoteError.
- promote_to_validated(): geçerli kanıt → kontrat lifecycle güncellenir.
- get_block_lifecycle(): bilinmeyen blok → "DRAFT" (fail-safe).
- Assembler raporunda lifecycle sütunu görünür.

Fix geri alınırsa KIRILMALI: her test koruyucu davranışı doğrular.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# --- sys.path düzeltmesi: hem workbench hem 05_SCRIPTS lazım ---------------
WROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = WROOT / "05_SCRIPTS"
_WORKBENCH_CORE = WROOT / "workbench" / "core"
for _p in (_SCRIPTS, _WORKBENCH_CORE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import program_assembler as pa
from library_store import (
    LifecyclePromoteError,
    get_block_lifecycle,
    promote_to_validated,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIGNALS = [
    {"name": "MOT_CONV_001_FB",  "type": "DI", "address": "%I0.0",
     "desc": "Conveyor run feedback", "raw": ""},
    {"name": "MOT_CONV_001_OL",  "type": "DI", "address": "%I0.1",
     "desc": "Conveyor overload thermal relay", "raw": ""},
    {"name": "MOT_CONV_001_RUN", "type": "DQ", "address": "%Q0.0",
     "desc": "Conveyor motor contactor", "raw": ""},
]


@pytest.fixture(scope="module")
def assembled_draft(tmp_path_factory):
    """Tüm bloklar DRAFT lifecycle'lı — uyarı bekleniyor."""
    proj = tmp_path_factory.mktemp("proj_draft")
    res = pa.assemble_program(proj, signals=SIGNALS)
    return proj, res


# ---------------------------------------------------------------------------
# Test sınıfı: Assembler DRAFT lifecycle uyarısı
# ---------------------------------------------------------------------------

class TestAssemblerDraftWarning:

    def test_draft_block_produces_warning(self, assembled_draft):
        """DRAFT lifecycle'lı blok kullanılırsa assembler uyarı üretmeli."""
        _proj, res = assembled_draft
        draft_warnings = [w for w in res.warnings if "S-15/B-P1" in w]
        assert draft_warnings, (
            "DRAFT lifecycle'lı blok kullanıldığında assembler WARNING üretmeli. "
            "Fix geri alındığında bu test kırılmalı (S-15 proof testi)."
        )

    def test_draft_warning_names_the_block(self, assembled_draft):
        """DRAFT uyarısı hangi bloğun DRAFT olduğunu belirtmeli."""
        _proj, res = assembled_draft
        # En az bir uyarı bir blok adı içermeli
        draft_warnings = [w for w in res.warnings if "S-15/B-P1" in w]
        assert any("FB_Motor" in w or "FB_Valve" in w or "FB_" in w
                   for w in draft_warnings), (
            "DRAFT uyarısı blok adını içermeli."
        )

    def test_draft_warning_does_not_block_assembly(self, assembled_draft):
        """DRAFT uyarısı üretimi DURDURMAMAL — assembler tamamlanmalı."""
        _proj, res = assembled_draft
        # Assembly başarıyla tamamlandıysa matched bloklar kopyalanmış olmalı
        assert res.copied, (
            "DRAFT uyarısı üretimi bloklamaz — kopyalama tamamlanmış olmalı."
        )

    def test_draft_warning_lifecycle_text_present(self, assembled_draft):
        """Uyarı metni lifecycle değerini içermeli."""
        _proj, res = assembled_draft
        draft_warnings = [w for w in res.warnings if "S-15/B-P1" in w]
        assert any("lifecycle=" in w or "DRAFT" in w for w in draft_warnings), (
            "Uyarı mesajı lifecycle değerini içermeli."
        )

    def test_report_has_lifecycle_column(self, assembled_draft):
        """Raporda Lifecycle sütunu görünür olmalı."""
        proj, res = assembled_draft
        assert res.report_path and res.report_path.is_file()
        text = res.report_path.read_text(encoding="utf-8")
        assert "Lifecycle" in text, (
            "Assembler raporu Lifecycle sütunu içermeli (S-15 görünürlük gerekliliği)."
        )

    def test_report_marks_draft_warn(self, assembled_draft):
        """Raporda DRAFT bloklar için DRAFT-WARN işareti görünmeli."""
        proj, res = assembled_draft
        text = res.report_path.read_text(encoding="utf-8")
        assert "DRAFT-WARN" in text, (
            "Rapor DRAFT-WARN işaretini içermeli (S-15 görünürlük)."
        )

    def test_copied_entry_has_lifecycle_field(self, assembled_draft):
        """res.copied her girdi için lifecycle alanı içermeli."""
        _proj, res = assembled_draft
        for c in res.copied:
            assert "lifecycle" in c, (
                f"copied girdi '{c.get('name')}' için lifecycle alanı eksik."
            )


# ---------------------------------------------------------------------------
# Test sınıfı: VALIDATED blok — uyarı üretilmemeli
# ---------------------------------------------------------------------------

class TestValidatedBlockNoWarning:

    def test_validated_block_no_draft_warning(self, tmp_path):
        """VALIDATED lifecycle'lı blok için S-15/B-P1 uyarısı üretilmemeli."""
        contracts_root = WROOT / "06_KNOWLEDGE_BASE" / "contracts"
        contract_path = next(
            contracts_root.rglob("FB_Motor_DOL.contract.json"), None
        )
        if contract_path is None:
            pytest.skip("FB_Motor_DOL.contract.json bulunamadı")

        original = contract_path.read_text(encoding="utf-8")
        try:
            data = json.loads(original)
            data["block"]["lifecycle"] = "VALIDATED"
            data["block"]["validated_by"] = "Test Muhendis"
            data["block"]["validated_date"] = "2026-06-11"
            data["block"]["validated_evidence"] = str(tmp_path / "fake_evidence.txt")
            # Kanıt dosyasını oluştur (gerçek yol olmalı — library_store.py bunu ister ama
            # assembler sadece kontrat verisine bakar; kontrat zaten in-memory değil disk)
            (tmp_path / "fake_evidence.txt").write_text("PLCSIM test log", encoding="utf-8")
            contract_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            proj = tmp_path / "proj_validated"
            proj.mkdir()
            res = pa.assemble_program(proj, signals=SIGNALS)
            # FB_Motor_DOL artık VALIDATED — bu blok için S-15 uyarısı olmamalı
            motor_dol_draft_warnings = [
                w for w in res.warnings
                if "S-15/B-P1" in w and "FB_Motor_DOL" in w
            ]
            assert not motor_dol_draft_warnings, (
                "VALIDATED lifecycle'lı FB_Motor_DOL için S-15/B-P1 uyarısı olmamalı. "
                "Fix geri alındığında bu test kırılmalı."
            )
        finally:
            # Restore orijinal kontrat (test izolasyonu)
            contract_path.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------------------
# Test sınıfı: promote_to_validated fail-closed
# ---------------------------------------------------------------------------

class TestPromoteToValidatedFailClosed:

    def test_empty_evidence_rejected(self, tmp_path):
        """Boş kanıt yolu → LifecyclePromoteError (fail-closed)."""
        with pytest.raises(LifecyclePromoteError, match="evidence path is empty"):
            promote_to_validated("FB_Motor_DOL", "", "Muhendis A")

    def test_whitespace_evidence_rejected(self, tmp_path):
        """Boşluk-dolu kanıt yolu → LifecyclePromoteError (fail-closed)."""
        with pytest.raises(LifecyclePromoteError, match="evidence path is empty"):
            promote_to_validated("FB_Motor_DOL", "   ", "Muhendis A")

    def test_empty_engineer_rejected(self, tmp_path):
        """Boş mühendis adı → LifecyclePromoteError (fail-closed)."""
        evidence = tmp_path / "evidence.txt"
        evidence.write_text("PLCSIM log", encoding="utf-8")
        with pytest.raises(LifecyclePromoteError, match="engineer name is empty"):
            promote_to_validated("FB_Motor_DOL", str(evidence), "")

    def test_nonexistent_evidence_file_rejected(self, tmp_path):
        """Var olmayan kanıt yolu → LifecyclePromoteError (fail-closed)."""
        nonexistent = str(tmp_path / "nonexistent_plcsim_log.txt")
        with pytest.raises(LifecyclePromoteError, match="evidence file not found"):
            promote_to_validated("FB_Motor_DOL", nonexistent, "Muhendis A")

    def test_unknown_block_raises_file_not_found(self, tmp_path):
        """Bilinmeyen blok adı → FileNotFoundError."""
        evidence = tmp_path / "evidence.txt"
        evidence.write_text("test log", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            promote_to_validated("FB_TAMAMEN_OLMAYAN_BLOK_XYZ", str(evidence), "Muhendis A")


class TestPromoteToValidatedSuccess:

    def test_valid_promote_updates_contract(self, tmp_path):
        """Geçerli kanıt + mühendis adı → lifecycle VALIDATED olarak güncellenir."""
        contracts_root = WROOT / "06_KNOWLEDGE_BASE" / "contracts"
        contract_path = next(
            contracts_root.rglob("FB_Motor_DOL.contract.json"), None
        )
        if contract_path is None:
            pytest.skip("FB_Motor_DOL.contract.json bulunamadı")

        original = contract_path.read_text(encoding="utf-8")
        evidence = tmp_path / "plcsim_test_report.txt"
        evidence.write_text("PLCSIM Advanced run: 5/5 PASS — 2026-06-11", encoding="utf-8")

        try:
            result_path = promote_to_validated(
                "FB_Motor_DOL",
                str(evidence),
                "Muhendis Test",
            )
            assert result_path == contract_path
            updated = json.loads(contract_path.read_text(encoding="utf-8"))
            assert updated["block"]["lifecycle"] == "VALIDATED", (
                "promote_to_validated() lifecycle'ı VALIDATED'a yükseltmeli. "
                "Fix geri alındığında bu test kırılmalı."
            )
            assert updated["block"]["validated_by"] == "Muhendis Test"
            assert updated["block"]["validated_evidence"] == str(evidence)
            assert "validated_date" in updated["block"]
        finally:
            contract_path.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------------------
# Test sınıfı: get_block_lifecycle fail-safe
# ---------------------------------------------------------------------------

class TestGetBlockLifecycle:

    def test_known_block_returns_lifecycle(self):
        """Bilinen bir blok için lifecycle değeri döner (boş olmaz)."""
        lc = get_block_lifecycle("FB_Motor_DOL")
        assert lc in {
            "DRAFT",
            "AUTO_VERIFIED_structural",
            "AUTO_VERIFIED_structural_plcrex",
            "PENDING_TIA_VERIFY",
            "VALIDATED",
            "FROZEN",
        }, f"Beklenmeyen lifecycle: {lc!r}"

    def test_unknown_block_returns_draft(self):
        """Bilinmeyen blok adı → fail-safe 'DRAFT' döner."""
        lc = get_block_lifecycle("FB_TAMAMEN_OLMAYAN_BLOK_99999")
        assert lc == "DRAFT", (
            "Bilinmeyen blok için get_block_lifecycle() fail-safe 'DRAFT' dönmeli. "
            "Fix geri alındığında bu test kırılmalı."
        )

    def test_empty_block_name_returns_draft(self):
        """Boş blok adı → fail-safe 'DRAFT' döner."""
        lc = get_block_lifecycle("")
        assert lc == "DRAFT"


# ---------------------------------------------------------------------------
# Test sınıfı: _get_lifecycle_from_entry (assembler yardımcısı)
# ---------------------------------------------------------------------------

class TestGetLifecycleFromEntry:

    def test_valid_entry_returns_lifecycle(self):
        """Geçerli entry dict → lifecycle string döner."""
        entry = {"data": {"block": {"lifecycle": "PENDING_TIA_VERIFY"}}}
        assert pa._get_lifecycle_from_entry(entry) == "PENDING_TIA_VERIFY"

    def test_unknown_lifecycle_value_returns_draft(self):
        """Tanınmayan lifecycle değeri → fail-safe 'DRAFT' döner."""
        entry = {"data": {"block": {"lifecycle": "BILINMEYEN_DEGER"}}}
        assert pa._get_lifecycle_from_entry(entry) == "DRAFT"

    def test_missing_lifecycle_key_returns_draft(self):
        """lifecycle anahtarı yoksa → fail-safe 'DRAFT' döner."""
        entry = {"data": {"block": {}}}
        assert pa._get_lifecycle_from_entry(entry) == "DRAFT"

    def test_empty_entry_returns_draft(self):
        """Boş entry → fail-safe 'DRAFT' döner."""
        assert pa._get_lifecycle_from_entry({}) == "DRAFT"

    def test_none_data_returns_draft(self):
        """data=None → fail-safe 'DRAFT' döner."""
        assert pa._get_lifecycle_from_entry({"data": None}) == "DRAFT"
