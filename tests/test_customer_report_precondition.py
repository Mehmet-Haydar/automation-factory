"""C-2 regresyon testleri: customer_report.run_report ön-koşul (precondition) denetimleri.

Kapsanan davranışlar
--------------------
1. Gate 7 onaylanmamış ve RD05 DRAFT_UNVERIFIED ise run_report ReportPreconditionError fırlatır.
2. Yalnızca Gate 7 eksikse (RD05 tamam) ReportPreconditionError fırlatır.
3. Yalnızca RD05 DRAFT_UNVERIFIED ise (Gate 7 tamam) ReportPreconditionError fırlatır.
4. Her iki koşul da sağlanıyorsa rapor üretilir (hata fırlatılmaz).
5. COMPLETED badge'i JSON status alanından değil gate_history'den belirlenir.
6. gate_history'de Gate 7 kaydı yokken JSON status="completed" olsa bile badge IN PROGRESS kalır.
7. gate_history'de Gate 7 onaylı kayıt varken badge COMPLETED döner.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

# sys.path conftest.py tarafından ayarlanır.
from customer_report import (
    ReportPreconditionError,
    _check_report_preconditions,
    _determine_status_badge,
    _gate7_approved,
    _rd05_verified,
    run_report,
)


# ---------------------------------------------------------------------------
# Yardımcı fikstürler
# ---------------------------------------------------------------------------

_CHAIN_FIELDS = ("gate", "when", "who", "signature", "note", "prev_hash")


def _make_valid_gate_record(gate: int, *, note: str = "completed",
                             prev_hash: str = "") -> dict:
    """R-C-1 uyumlu geçerli gate kaydı üretir; hash advance_gate() ile özdeş."""
    record = {
        "gate": gate,
        "when": "2026-09-15",
        "who": "Hans Becker (TUV)",
        "signature": "Hans Becker (TUV)",
        "note": note,
        "prev_hash": prev_hash,
    }
    payload = json.dumps(
        {k: record[k] for k in _CHAIN_FIELDS},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    record["hash"] = hashlib.sha256(payload).hexdigest()
    return record


def _make_project(
    tmp_path: Path,
    *,
    gate7_approved: bool = False,
    rd05_status: str = "approved",
    json_status: str = "active",
) -> Path:
    """Minimal proje dizini oluşturur.

    gate7_approved=True ise gate_history'e Gate 7 onay kaydı ekler.
    R-C-1: hash-chain geçerli kayıtlar üretilir (önceki sahte hash kaldırıldı).
    rd05_status: PROJECT_STATE.json rd_status.RD05_Safety.status değeri.
    json_status: PROJECT_STATE.json kök status alanı (manipüle edilebilir alan).
    """
    gate_history = []
    if gate7_approved:
        gate_history.append(
            _make_valid_gate_record(7, note="approved", prev_hash="")
        )

    state = {
        "project_name": "TestProject",
        "customer": "Test GmbH",
        "status": json_status,
        "gate_history": gate_history,
        "rd_status": {
            "RD05_Safety": {
                "status": rd05_status,
                "completion_pct": 100,
            }
        },
    }
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "PROJECT_STATE.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    return project_dir


# ---------------------------------------------------------------------------
# Birim testleri: yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

class TestGate7Approved:
    def test_empty_history_returns_false(self):
        assert _gate7_approved([]) is False

    def test_none_history_returns_false(self):
        assert _gate7_approved(None) is False  # type: ignore[arg-type]

    # Canonical gate-7 record (advance_gate() format) for valid-chain tests.
    # Hash computed from: json.dumps({gate,when,who,signature,note,prev_hash},
    #   sort_keys=True, ensure_ascii=False) via SHA-256.
    _VALID_G7 = {
        "gate": 7, "note": "approved",
        "prev_hash": "GENESIS", "signature": "test-sig",
        "when": "2026-06-14T00:00:00", "who": "test_engineer",
        "hash": "ff58c08b546233cad6e8e54621e2fbf73916f5c12ff2524ba25a12d1c4d218d7",
    }

    def test_gate7_approved_valid_record_returns_true(self):
        # R-C-3: fully-formed record with correct hash must pass.
        assert _gate7_approved([self._VALID_G7]) is True

    def test_gate7_approved_null_hash_returns_false(self):
        # R-C-3: explicit null hash is rejected (spoofable legacy bypass).
        rec = {**self._VALID_G7, "hash": None}
        assert _gate7_approved([rec]) is False

    def test_gate7_approved_missing_hash_returns_false(self):
        # R-C-3: missing hash field is also rejected.
        rec = {k: v for k, v in self._VALID_G7.items() if k != "hash"}
        assert _gate7_approved([rec]) is False

    def test_gate7_completed_note_returns_false(self):
        # "completed" değil "approved" aranmalı (Gate 7 bir APPROVAL_GATE).
        hist = [{**self._VALID_G7, "note": "completed"}]
        assert _gate7_approved(hist) is False

    def test_gate6_approved_does_not_count(self):
        rec = {**self._VALID_G7, "gate": 6}
        assert _gate7_approved([rec]) is False

    def test_mixed_history_finds_gate7(self):
        hist = [self._VALID_G7]
        assert _gate7_approved(hist) is True


class TestRd05Verified:
    def test_draft_unverified_returns_false(self):
        state = {"rd_status": {"RD05_Safety": {"status": "DRAFT_UNVERIFIED"}}}
        assert _rd05_verified(state) is False

    def test_draft_returns_false(self):
        state = {"rd_status": {"RD05_Safety": {"status": "DRAFT"}}}
        assert _rd05_verified(state) is False

    def test_empty_status_returns_false(self):
        state = {"rd_status": {"RD05_Safety": {"status": ""}}}
        assert _rd05_verified(state) is False

    def test_missing_rd05_returns_false(self):
        # RD05 kaydı hiç yoksa fail-closed.
        state = {"rd_status": {}}
        assert _rd05_verified(state) is False

    def test_approved_returns_true(self):
        state = {"rd_status": {"RD05_Safety": {"status": "approved"}}}
        assert _rd05_verified(state) is True

    def test_done_returns_true(self):
        state = {"rd_status": {"RD05_Safety": {"status": "done"}}}
        assert _rd05_verified(state) is True

    def test_final_returns_true(self):
        state = {"rd_status": {"RD05_Safety": {"status": "final"}}}
        assert _rd05_verified(state) is True

    def test_case_insensitive(self):
        state = {"rd_status": {"RD05_Safety": {"status": "APPROVED"}}}
        assert _rd05_verified(state) is True


class TestDetermineStatusBadge:
    def test_no_gate7_gives_in_progress(self):
        state: dict = {"gate_history": [], "status": "completed"}
        # JSON status="completed" olsa dahi gate_history kontrol edilmeli.
        assert _determine_status_badge(state) == "IN PROGRESS"

    def test_gate7_approved_gives_completed(self):
        # R-C-3: must use a fully-formed, hashed record (null-hash is rejected).
        state = {"gate_history": [TestGate7Approved._VALID_G7]}
        assert _determine_status_badge(state) == "COMPLETED"

    def test_json_status_completed_without_gate7_gives_in_progress(self):
        """N-W8 core fix: JSON manipulation does NOT promote badge."""
        state = {"status": "completed", "gate_history": []}
        assert _determine_status_badge(state) == "IN PROGRESS"


# ---------------------------------------------------------------------------
# Entegrasyon testleri: _check_report_preconditions
# ---------------------------------------------------------------------------

class TestCheckReportPreconditions:
    def test_both_missing_raises_two_reasons(self, tmp_path):
        proj = _make_project(tmp_path, gate7_approved=False, rd05_status="DRAFT_UNVERIFIED")
        state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        with pytest.raises(ReportPreconditionError) as exc_info:
            _check_report_preconditions(proj, state)
        assert len(exc_info.value.reasons) == 2

    def test_only_gate7_missing_raises_one_reason(self, tmp_path):
        proj = _make_project(tmp_path, gate7_approved=False, rd05_status="approved")
        state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        with pytest.raises(ReportPreconditionError) as exc_info:
            _check_report_preconditions(proj, state)
        reasons = exc_info.value.reasons
        assert len(reasons) == 1
        assert "Gate 7" in reasons[0]

    def test_only_rd05_unverified_raises_one_reason(self, tmp_path):
        proj = _make_project(tmp_path, gate7_approved=True, rd05_status="DRAFT_UNVERIFIED")
        state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        with pytest.raises(ReportPreconditionError) as exc_info:
            _check_report_preconditions(proj, state)
        reasons = exc_info.value.reasons
        assert len(reasons) == 1
        assert "RD05" in reasons[0]

    def test_all_ok_does_not_raise(self, tmp_path):
        proj = _make_project(tmp_path, gate7_approved=True, rd05_status="approved")
        state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        # Hata fırlatılmamalı.
        _check_report_preconditions(proj, state)


# ---------------------------------------------------------------------------
# Entegrasyon testleri: run_report
# ---------------------------------------------------------------------------

class TestRunReport:
    def test_run_report_blocked_when_gate7_missing(self, tmp_path):
        """Temel koruyucu davranış: Gate 7 onaysız → rapor üretilmez, hata fırlatılır."""
        proj = _make_project(tmp_path, gate7_approved=False, rd05_status="approved")
        with pytest.raises(ReportPreconditionError):
            run_report(proj)

    def test_run_report_blocked_when_rd05_unverified(self, tmp_path):
        """RD05 DRAFT_UNVERIFIED → rapor üretilmez, hata fırlatılır."""
        proj = _make_project(tmp_path, gate7_approved=True, rd05_status="DRAFT_UNVERIFIED")
        with pytest.raises(ReportPreconditionError):
            run_report(proj)

    def test_run_report_blocked_both_missing(self, tmp_path):
        """Her iki koşul da eksikken tek çağrıda iki neden döner."""
        proj = _make_project(tmp_path, gate7_approved=False, rd05_status="DRAFT_UNVERIFIED")
        with pytest.raises(ReportPreconditionError) as exc_info:
            run_report(proj)
        assert len(exc_info.value.reasons) == 2

    def test_run_report_json_status_manipulation_does_not_bypass(self, tmp_path):
        """N-W8 proof: JSON'da status='completed' yazılması kontrolü atlatamaz."""
        proj = _make_project(
            tmp_path,
            gate7_approved=False,
            rd05_status="approved",
            json_status="completed",   # Saldırgan JSON'u manipüle etti
        )
        with pytest.raises(ReportPreconditionError) as exc_info:
            run_report(proj)
        # Hata mesajı Gate 7 ile ilgili olmalı.
        assert "Gate 7" in exc_info.value.reasons[0]

    def test_run_report_succeeds_when_preconditions_met(self, tmp_path):
        """Tüm koşullar sağlandığında rapor üretilir (MD fallback — reportlab yok)."""
        proj = _make_project(tmp_path, gate7_approved=True, rd05_status="approved")
        result = run_report(proj)
        assert result.ok
        assert result.output_path is not None

    def test_run_report_skip_preconditions_flag(self, tmp_path):
        """skip_preconditions=True (test-only) ile koşulsuz çalışır."""
        proj = _make_project(tmp_path, gate7_approved=False, rd05_status="DRAFT_UNVERIFIED")
        result = run_report(proj, skip_preconditions=True)
        # Ön koşul hatası fırlatılmaz, rapor üretilir.
        assert result.ok

    def test_precondition_error_str_contains_reasons(self, tmp_path):
        """ReportPreconditionError string temsili tüm nedenleri içerir."""
        proj = _make_project(tmp_path, gate7_approved=False, rd05_status="DRAFT_UNVERIFIED")
        with pytest.raises(ReportPreconditionError) as exc_info:
            run_report(proj)
        msg = str(exc_info.value)
        assert "Gate 7" in msg
        assert "RD05" in msg
