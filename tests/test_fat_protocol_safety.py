"""S-2 Proof Tests — FAT Protocol Safety Notes & Counter Isolation.

Tests verifying that:
1. _load_safety_notes / _discover_rd05_file use glob-based discovery
   (any RD05_Safety*.md suffix is accepted; missing file → empty list + warning,
   NOT a silent pass that conceals missing safety data).
2. run_fat_protocol uses a per-call _Counter so back-to-back runs never share
   state (counter leak = corrupt audit trail).

Fix-revert contract: if the fixes in fat_protocol.py are reverted these tests
MUST fail — they are not smoke tests.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

import sys
import os

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fat_protocol import (
    _Counter,
    _discover_rd05_file,
    _load_safety_notes,
    run_fat_protocol,
)


# ===========================================================================
# Group A — _Counter isolation (replaces mutable _TC global)
# ===========================================================================


class TestCounter:
    """_Counter must be independent per instance — no shared state."""

    def test_counter_starts_at_zero(self):
        c = _Counter()
        assert c.value == 0

    def test_counter_increments_sequentially(self):
        c = _Counter()
        assert c.next_id() == "T001"
        assert c.next_id() == "T002"
        assert c.next_id() == "T010" if False else c.next_id() == "T003"
        assert c.value == 3

    def test_two_counters_are_isolated(self):
        """Core proof: two independent instances must not share state."""
        c1 = _Counter()
        c2 = _Counter()
        c1.next_id()
        c1.next_id()  # c1 is at 2
        # c2 must still start from 1 — if there were a global it would be 3
        assert c2.next_id() == "T001", (
            "_Counter instances share state — global counter not removed"
        )

    def test_run_fat_protocol_back_to_back_counter_resets(self, tmp_path):
        """Two consecutive run_fat_protocol calls must produce identical
        test-ID sequences.  With the old _TC global the second run would
        continue from where the first left off."""
        proj = tmp_path / "proj_a"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        # S-17: RD05 must exist with substantive content for FAT to proceed.
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "# RD05\n| Func | Desc |\n|---|---|\n"
            "| EStop | Emergency stop |\n| Door | Door interlock |\n",
            encoding="utf-8",
        )
        # AUDIT-004b: the banner now blocks without a recorded review
        import json as _json
        (proj / "PROJECT_STATE.json").write_text(_json.dumps({
            "rd_verifications": {"RD05": {"reviewed": True}}}),
            encoding="utf-8")
        out_a = tmp_path / "out_a"
        out_b = tmp_path / "out_b"

        r1 = run_fat_protocol(proj, out_a)
        r2 = run_fat_protocol(proj, out_b)

        # Both runs must generate the same number of tests (same structure)
        assert r1.test_count == r2.test_count, (
            f"Run 1 test_count={r1.test_count}, run 2 test_count={r2.test_count}. "
            "Counter is leaking across calls."
        )
        assert r1.test_count > 0, "Protocol generated zero tests — unexpected"

    def test_counter_leak_detected_if_global_remains(self, tmp_path):
        """Regression guard: if _TC global were reintroduced and NOT reset,
        a second run would produce a HIGHER first test ID.

        We parse the output Markdown to find the very first T-ID and assert
        it equals 'T001' on both runs.
        """
        proj = tmp_path / "proj_b"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        # S-17: RD05 must exist with substantive content for FAT to proceed.
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "# RD05\n| Func | Desc |\n|---|---|\n"
            "| EStop | Emergency stop |\n| Door | Door interlock |\n",
            encoding="utf-8",
        )
        # AUDIT-004b: the banner now blocks without a recorded review
        import json as _json
        (proj / "PROJECT_STATE.json").write_text(_json.dumps({
            "rd_verifications": {"RD05": {"reviewed": True}}}),
            encoding="utf-8")
        out_1 = tmp_path / "run1"
        out_2 = tmp_path / "run2"

        r1 = run_fat_protocol(proj, out_1)
        r2 = run_fat_protocol(proj, out_2)

        for run_num, result in [(1, r1), (2, r2)]:
            assert result.md_path is not None, f"Run {run_num}: no output file produced"
            text = result.md_path.read_text(encoding="utf-8")
            # Find the first T-ID in the markdown
            m = re.search(r"\|\s*(T\d{3})\s*\|", text)
            assert m is not None, f"Run {run_num}: no T-ID found in output"
            first_id = m.group(1)
            assert first_id == "T001", (
                f"Run {run_num}: first test ID is {first_id!r}, expected 'T001'. "
                "Counter state leaked from a previous run."
            )


# ===========================================================================
# Group B — _discover_rd05_file  (glob-based discovery)
# ===========================================================================


class TestDiscoverRd05File:
    def test_returns_none_when_no_metadata_dir(self, tmp_path):
        """No metadata directory → None (fail-closed)."""
        proj = tmp_path / "proj"
        proj.mkdir()
        assert _discover_rd05_file(proj) is None

    def test_returns_none_when_no_rd05_file(self, tmp_path):
        """metadata/ exists but no RD05_Safety*.md → None."""
        proj = tmp_path / "proj"
        (proj / "metadata").mkdir(parents=True)
        assert _discover_rd05_file(proj) is None

    def test_finds_draft_unverified_variant(self, tmp_path):
        """Classic filename must still be found."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        f = meta / "RD05_Safety_DRAFT_UNVERIFIED.md"
        f.write_text("# RD05\n", encoding="utf-8")
        assert _discover_rd05_file(proj) == f

    def test_finds_arbitrary_suffix(self, tmp_path):
        """A file named RD05_Safety_VERIFIED_2026.md must also be discovered."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        f = meta / "RD05_Safety_VERIFIED_2026.md"
        f.write_text("# RD05\n", encoding="utf-8")
        result = _discover_rd05_file(proj)
        assert result is not None
        assert result.name == "RD05_Safety_VERIFIED_2026.md"

    def test_finds_plain_rd05_safety(self, tmp_path):
        """RD05_Safety.md (no suffix) must also be discovered."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        f = meta / "RD05_Safety.md"
        f.write_text("# RD05\n", encoding="utf-8")
        assert _discover_rd05_file(proj) == f

    def test_multiple_files_returns_first_lexicographically(self, tmp_path):
        """When multiple matches exist the first (sorted) is chosen and a
        warning is emitted."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text("a", encoding="utf-8")
        (meta / "RD05_Safety_VERIFIED.md").write_text("b", encoding="utf-8")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = _discover_rd05_file(proj)

        assert result is not None
        assert result.name == "RD05_Safety_DRAFT_UNVERIFIED.md"
        assert any("multiple" in str(w.message).lower() for w in caught), (
            "Expected a warning about multiple RD05 files but none was emitted."
        )


# ===========================================================================
# Group C — _load_safety_notes  (fail-closed + content parsing)
# ===========================================================================


class TestLoadSafetyNotes:
    def test_missing_rd05_returns_empty_with_warning(self, tmp_path):
        """No RD05 file → empty list AND a warning (not silent success)."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "metadata").mkdir()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = _load_safety_notes(proj)

        assert result == [], "Expected empty list when RD05 is missing"
        assert any("no rd05" in str(w.message).lower() for w in caught), (
            "Expected a warning when RD05 is absent but none was emitted. "
            "Fail-closed contract broken."
        )

    def test_missing_metadata_dir_returns_empty_with_warning(self, tmp_path):
        """No metadata directory → empty list AND warning."""
        proj = tmp_path / "proj"
        proj.mkdir()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = _load_safety_notes(proj)

        assert result == []
        assert any(caught), "Expected at least one warning"

    def test_rd05_with_safety_entries_parsed(self, tmp_path):
        """Safety rows in the file must be returned."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "# RD05\n\n"
            "| FunctionName | Description |\n"
            "|---|---|\n"
            "| EStop_Main | E-stop safety function |\n"
            "| DoorInterlock | Door interlock function |\n"
            "| ConveyorMotor | Normal motor (not safety) |\n",
            encoding="utf-8",
        )
        result = _load_safety_notes(proj)
        # At least the safety-keyword rows must appear
        assert any("EStop" in n or "estop" in n.lower() for n in result), (
            f"EStop row not found in safety notes: {result}"
        )
        assert any("Door" in n or "door" in n.lower() for n in result), (
            f"Door row not found in safety notes: {result}"
        )

    def test_alternate_filename_suffix_still_parsed(self, tmp_path):
        """A file with a non-DRAFT suffix must still yield notes."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        (meta / "RD05_Safety_VERIFIED_2026.md").write_text(
            "| FunctionName | Desc |\n|---|---|\n| EStop_East | E-stop east panel |\n",
            encoding="utf-8",
        )
        result = _load_safety_notes(proj)
        assert len(result) >= 1, "Expected at least one safety note from alternate-suffix file"

    def test_empty_rd05_returns_empty_list_no_warning(self, tmp_path):
        """RD05 exists but has no safety-keyword rows → empty list, no warning."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "# RD05\nNo table here.\n",
            encoding="utf-8",
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = _load_safety_notes(proj)

        assert result == []
        # No "no RD05" warning should appear because the file EXISTS
        assert not any("no rd05" in str(w.message).lower() for w in caught)


# ===========================================================================
# Group D — run_fat_protocol integration (no RD05 → fail-closed, no crash)
# ===========================================================================


class TestRunFatProtocolIntegration:
    def test_run_without_rd05_is_blocked(self, tmp_path):
        """S-17 / B-P5: absent RD05 must BLOCK FAT generation (fail-closed).

        Previously this test asserted that FAT would be produced with a warning
        when RD05 was absent.  That behaviour was the vulnerability fixed by
        S-17 — a generic-safety-scenario FAT must never reach the customer
        without project-specific safety requirements.

        After the S-17 fix: run_fat_protocol raises Rd05BlockedError and writes
        no output file.
        """
        from fat_protocol import Rd05BlockedError
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "metadata").mkdir()  # metadata/ exists but no RD05 file
        out = tmp_path / "out"

        with pytest.raises(Rd05BlockedError):
            run_fat_protocol(proj, out)

        # No FAT file must have been written
        fat_files = list(out.glob("FAT_PROTOCOL_*.md")) if out.exists() else []
        assert fat_files == [], (
            "FAT was written despite missing RD05 — fail-closed contract broken."
        )

    def test_run_with_rd05_includes_notes(self, tmp_path):
        """When RD05 exists with safety entries they appear in the protocol."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "| FunctionName | Desc |\n|---|---|\n"
            "| EStop_Conveyor | E-stop on conveyor belt |\n",
            encoding="utf-8",
        )
        import json as _json
        (proj / "PROJECT_STATE.json").write_text(_json.dumps({
            "rd_verifications": {"RD05": {"reviewed": True}}}),
            encoding="utf-8")
        out = tmp_path / "out"
        result = run_fat_protocol(proj, out)

        assert result.md_path is not None
        text = result.md_path.read_text(encoding="utf-8")
        assert "EStop_Conveyor" in text or "EStop" in text, (
            "RD05 safety note was not included in protocol output."
        )

    def test_protocol_total_count_matches_body(self, tmp_path):
        """The 'Total test count' in the signature table must equal the actual
        number of T-IDs in the document body."""
        proj = tmp_path / "proj"
        meta = proj / "metadata"
        meta.mkdir(parents=True)
        # S-17: RD05 must exist with substantive content.
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "# RD05\n| Func | Desc |\n|---|---|\n"
            "| EStop | Emergency stop |\n| Door | Door interlock |\n",
            encoding="utf-8",
        )
        import json as _json
        (proj / "PROJECT_STATE.json").write_text(_json.dumps({
            "rd_verifications": {"RD05": {"reviewed": True}}}),
            encoding="utf-8")
        out = tmp_path / "out"
        # lang="en" — the declared-total label below is the EN string
        # (default language is DE since SAT v2 Faz 1).
        result = run_fat_protocol(proj, out, lang="en")

        assert result.md_path is not None
        text = result.md_path.read_text(encoding="utf-8")

        # Count T-IDs in body
        body_ids = re.findall(r"\|\s*T\d{3}\s*\|", text)
        # Extract declared total
        m = re.search(r"Total test count\s*\|\s*(\d+)", text)
        assert m is not None, "Total test count row not found"
        declared = int(m.group(1))
        assert declared == len(body_ids), (
            f"Declared total ({declared}) != actual T-ID count ({len(body_ids)}). "
            "Counter value drifted."
        )
