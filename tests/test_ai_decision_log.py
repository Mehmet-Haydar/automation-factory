"""
tests/test_ai_decision_log.py — Proof tests for C-1 fix.

EU AI Act Article 12: append-only audit log, SHA256 hash chain,
approve_entry validation, fail-closed behaviour.

Design contract:
  - Fix PRESENT  → all tests pass.
  - Fix REVERTED → tests that assert the corrected behaviour break.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup so tests run from any cwd
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_decision_log import (  # noqa: E402
    AuditLogError,
    LOG_FILENAME,
    SIGNOFF_STATUSES,
    approve_all_pending,
    approve_entry,
    log_ai_action,
    read_log,
    verify_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(tmp_path: Path) -> Path:
    """Return a fresh project root with no log file."""
    return tmp_path


# ===========================================================================
# 1. log_ai_action — append-only (never rewrites when N records exist)
# ===========================================================================

class TestAppendOnly:
    def test_first_write_creates_jsonl(self, tmp_path):
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "claude-sonnet-4-6", "anthropic")
        log_path = root / LOG_FILENAME
        assert log_path.exists(), "Log file must be created"
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_second_write_appends_not_rewrites(self, tmp_path):
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "m1", "p1")
        # Capture raw content of first line
        log_path = root / LOG_FILENAME
        first_raw = log_path.read_text().splitlines()[0]

        log_ai_action(root, "Step B", "m2", "p2")
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2, "Second call must append, not rewrite"
        assert lines[0] == first_raw, "First line must be unchanged after append"

    def test_duplicate_step_label_still_appends(self, tmp_path):
        """Old code silently deduplicated — new code always appends (each call
        is a distinct audit event, even with the same label)."""
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "m", "p")
        log_ai_action(root, "Step A", "m", "p")
        lines = [l for l in (root / LOG_FILENAME).read_text().splitlines() if l.strip()]
        assert len(lines) == 2, "Each log_ai_action call must produce one record"


# ===========================================================================
# 2. Hash chain integrity
# ===========================================================================

class TestHashChain:
    def test_first_record_has_genesis_prev_hash(self, tmp_path):
        root = _project(tmp_path)
        rec = log_ai_action(root, "Step A", "m", "p")
        assert rec["prev_hash"] == "GENESIS"

    def test_second_record_chains_to_first_raw_line(self, tmp_path):
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "m", "p")
        log_path = root / LOG_FILENAME
        first_raw = [l for l in log_path.read_text().splitlines() if l.strip()][0]

        import hashlib
        expected_prev = "sha256:" + hashlib.sha256(first_raw.encode()).hexdigest()

        log_ai_action(root, "Step B", "m", "p")
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        second_rec = json.loads(lines[1])
        assert second_rec["prev_hash"] == expected_prev

    def test_verify_chain_clean_log(self, tmp_path):
        root = _project(tmp_path)
        for i in range(4):
            log_ai_action(root, f"Step {i}", "m", "p")
        violations = verify_chain(root)
        assert violations == [], f"Clean log must have no violations: {violations}"

    def test_verify_chain_detects_tampering(self, tmp_path):
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "m", "p")
        log_ai_action(root, "Step B", "m", "p")

        log_path = root / LOG_FILENAME
        lines = log_path.read_text().splitlines(keepends=True)
        # Tamper with first record's step_label
        rec = json.loads(lines[0])
        rec["step_label"] = "TAMPERED"
        lines[0] = json.dumps(rec) + "\n"
        log_path.write_text("".join(lines))

        violations = verify_chain(root)
        assert len(violations) >= 1, "Tampering must be detected by hash chain"


# ===========================================================================
# 3. Input / output hashes stored — no raw PII
# ===========================================================================

class TestNoPII:
    def test_prompt_hash_stored_not_raw_text(self, tmp_path):
        root = _project(tmp_path)
        secret = "CONFIDENTIAL customer data: valve PV-101 setpoint 42 bar"
        rec = log_ai_action(root, "Step A", "m", "p", prompt_text=secret)
        raw = (root / LOG_FILENAME).read_text()
        assert secret not in raw, "Raw prompt text must NOT appear in log"
        assert rec["input_hash"].startswith("sha256:"), "Input hash must be sha256 prefixed"

    def test_output_hash_stored_not_raw_text(self, tmp_path):
        root = _project(tmp_path)
        output = "CONFIDENTIAL response with customer specifics"
        rec = log_ai_action(root, "Step A", "m", "p", output_text=output)
        raw = (root / LOG_FILENAME).read_text()
        assert output not in raw, "Raw output text must NOT appear in log"
        assert rec["output_hash"].startswith("sha256:"), "Output hash must be sha256 prefixed"


# ===========================================================================
# 4. approve_entry validation
# ===========================================================================

class TestApproveEntry:
    def _setup(self, tmp_path):
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "m", "p")
        rec_id = read_log(root)[0]["id"]
        return root, rec_id

    def test_approved_status_sets_signoff(self, tmp_path):
        root, rec_id = self._setup(tmp_path)
        result = approve_entry(root, rec_id, "Eng. Smith", "approved", note="LGTM")
        assert result is True
        rec = read_log(root)[0]
        assert rec["signoff"]["status"] == "approved"
        assert rec["signoff"]["engineer"] == "Eng. Smith"
        assert rec["signoff"]["note"] == "LGTM"

    def test_rejected_status_accepted(self, tmp_path):
        root, rec_id = self._setup(tmp_path)
        approve_entry(root, rec_id, "Eng. Jones", "rejected", note="needs review")
        rec = read_log(root)[0]
        assert rec["signoff"]["status"] == "rejected"

    def test_invalid_status_raises_valueerror(self, tmp_path):
        root, rec_id = self._setup(tmp_path)
        with pytest.raises(ValueError, match="approved.*rejected|rejected.*approved"):
            approve_entry(root, rec_id, "Eng. X", "maybe")

    def test_empty_engineer_raises_valueerror(self, tmp_path):
        root, rec_id = self._setup(tmp_path)
        with pytest.raises(ValueError, match="engineer_name"):
            approve_entry(root, rec_id, "", "approved")

    def test_free_text_status_rejected(self, tmp_path):
        """Old code accepted free text in approved_by. New code enforces enum."""
        root, rec_id = self._setup(tmp_path)
        with pytest.raises(ValueError):
            approve_entry(root, rec_id, "Eng. X", "looks good to me")

    def test_note_is_separate_field(self, tmp_path):
        """Note must live in signoff.note, not in status or engineer fields."""
        root, rec_id = self._setup(tmp_path)
        approve_entry(root, rec_id, "Eng. A", "approved", note="verified against spec")
        rec = read_log(root)[0]
        assert rec["signoff"]["note"] == "verified against spec"
        assert "verified" not in rec["signoff"]["status"]
        assert "verified" not in rec["signoff"]["engineer"]


# ===========================================================================
# 5. Fail-closed: AuditLogError when log directory is unwritable
# ===========================================================================

class TestFailClosed:
    def test_unwritable_log_dir_raises_audit_log_error(self, tmp_path):
        """When the log cannot be written, log_ai_action must raise AuditLogError,
        NOT silently succeed — the AI call must be blocked."""
        import os, stat
        # chmod-based read-only protection does not apply to the superuser:
        # root bypasses Unix file permissions, so this test is only meaningful
        # for a normal user (which is how CI and end users run it).
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            pytest.skip("file-permission denial cannot be exercised as root")
        root = tmp_path / "readonly_proj"
        root.mkdir()
        log_path = root / LOG_FILENAME
        # Pre-create log as read-only
        log_path.write_text("")
        log_path.chmod(stat.S_IREAD)
        try:
            with pytest.raises(AuditLogError):
                log_ai_action(root, "Step A", "m", "p")
        finally:
            # Restore write permission for cleanup
            log_path.chmod(stat.S_IREAD | stat.S_IWRITE)

    def test_successful_write_does_not_raise(self, tmp_path):
        """Sanity: normal writable path must not raise."""
        root = _project(tmp_path)
        rec = log_ai_action(root, "Step A", "m", "p")
        assert rec["id"] == "L001"


# ===========================================================================
# 6. approve_all_pending
# ===========================================================================

class TestApproveAllPending:
    def test_approves_all_pending(self, tmp_path):
        root = _project(tmp_path)
        for s in ("Step A", "Step B", "Step C"):
            log_ai_action(root, s, "m", "p")
        count = approve_all_pending(root, "Eng. Bulk", "approved")
        assert count == 3
        for rec in read_log(root):
            assert rec["signoff"]["status"] == "approved"

    def test_invalid_status_raises(self, tmp_path):
        root = _project(tmp_path)
        log_ai_action(root, "Step A", "m", "p")
        with pytest.raises(ValueError):
            approve_all_pending(root, "Eng. X", "yes please")


# ===========================================================================
# 7. Regression: old _rebuild rewrite is gone — log grows by appending
# ===========================================================================

class TestNoRewrite:
    def test_log_line_count_grows_monotonically(self, tmp_path):
        root = _project(tmp_path)
        log_path = root / LOG_FILENAME
        for i in range(5):
            log_ai_action(root, f"Step {i}", "m", "p")
            lines = [l for l in log_path.read_text().splitlines() if l.strip()]
            assert len(lines) == i + 1, \
                f"After {i+1} calls, expected {i+1} lines, got {len(lines)}"


# ===========================================================================
# 8. Thread safety: SHA-256 hash zinciri eş zamanlı yazmalarda bozulmamalı
#    (_LOG_LOCK fix — bu test fix olmadan kırılır)
# ===========================================================================

class TestThreadSafety:
    """Proof test: _LOG_LOCK olmadan bu test güvenilir şekilde kırılır
    çünkü eş zamanlı thread'ler aynı prev_hash'i okuyabilir → zincir ihlali.
    _LOG_LOCK ile tüm oku-hesapla-yaz adımları atomik; zincir her zaman geçerli."""

    def test_concurrent_log_ai_action_chain_integrity(self, tmp_path):
        """N thread eş zamanlı log_ai_action çağırır; sonuçta verify_chain
        hiçbir ihlal raporlamamalı."""
        root = _project(tmp_path)
        n_threads = 20
        errors: list[str] = []

        def _write(idx: int) -> None:
            try:
                log_ai_action(root, f"Concurrent step {idx}", "model-x", "provider-y")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"thread {idx}: {exc}")

        threads = [threading.Thread(target=_write, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread exceptions: {errors}"

        log_path = root / LOG_FILENAME
        lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == n_threads, (
            f"Her thread tam olarak 1 kayıt yazmalı; beklenen {n_threads}, "
            f"bulunan {len(lines)}"
        )

        violations = verify_chain(root)
        assert violations == [], (
            "Eş zamanlı yazma sonrası hash zinciri bozuldu — "
            f"ihlaller: {violations}"
        )

    def test_concurrent_append_signoff_chain_integrity(self, tmp_path):
        """Mevcut kayıtlara eş zamanlı signoff eklenir; zincir bozulmamalı."""
        root = _project(tmp_path)
        n = 10
        # Önce n adet kayıt sıralı yaz
        rec_ids: list[str] = []
        for i in range(n):
            r = log_ai_action(root, f"Signoff step {i}", "m", "p")
            rec_ids.append(r["id"])

        errors: list[str] = []

        def _signoff(rid: str, idx: int) -> None:
            try:
                from ai_decision_log import approve_entry
                approve_entry(root, rid, f"Eng{idx}", "approved", note="ok")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"signoff {rid}: {exc}")

        threads = [
            threading.Thread(target=_signoff, args=(rid, i))
            for i, rid in enumerate(rec_ids)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Signoff thread exceptions: {errors}"

        violations = verify_chain(root)
        assert violations == [], (
            "Eş zamanlı signoff sonrası hash zinciri bozuldu — "
            f"ihlaller: {violations}"
        )

    def test_lock_exists_on_module(self, tmp_path):
        """_LOG_LOCK modül değişkeni var ve threading.Lock örneği olmalı.
        Fix geri alınırsa bu test import aşamasında AttributeError verir."""
        import ai_decision_log as adl
        assert hasattr(adl, "_LOG_LOCK"), (
            "_LOG_LOCK modül düzeyinde tanımlı olmalı"
        )
        assert isinstance(adl._LOG_LOCK, type(threading.Lock())), (
            "_LOG_LOCK bir threading.Lock örneği olmalı"
        )
