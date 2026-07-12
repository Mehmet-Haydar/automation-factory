"""
tests/test_audit_full_hash.py — Proof tests for S-3 / B-G3 fix.

COMPLIANCE: audit input_hash must be derived from the FULL (untruncated)
prompt sent to the AI — not from a display-only [:N] slice.

EU AI Act Article 12: audit integrity requires that the recorded hash
matches the exact bytes processed by the AI model.

Design contract:
  - Fix PRESENT  → all tests pass.
  - Fix REVERTED → tests that assert hash-from-full-text break
    (specifically: test_full_hash_differs_from_truncated_hash and
     test_full_prompt_text_kwarg_sets_correct_hash).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_decision_log import (  # noqa: E402
    LOG_FILENAME,
    log_ai_action,
    verify_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _long_prompt(length: int = 5000) -> str:
    """Generate a deterministic prompt string of the requested length."""
    base = "AUTOMATION_FACTORY audit proof — üretim verisi S-3 kanıtı. "
    return (base * ((length // len(base)) + 2))[:length]


# ===========================================================================
# 1. Core fix: full_prompt_text kwarg → hash from full text, not from slice
# ===========================================================================

class TestFullHashFromFullPrompt:
    def test_full_prompt_text_kwarg_sets_correct_hash(self, tmp_path):
        """(1) 5000-char prompt: full_prompt_text kwarg → input_hash == sha256(full),
        NOT sha256(first-2000-chars). This is the primary S-3 regression test."""
        full = _long_prompt(5000)
        display_slice = full[:2000]

        assert len(full) == 5000
        assert full != display_slice, "Sanity: slice must differ from full text"

        rec = log_ai_action(
            tmp_path,
            "S3_proof_step",
            "claude-sonnet-4-6",
            "anthropic",
            prompt_text=display_slice,        # display-only truncated slice
            full_prompt_text=full,            # S-3 fix: full text for hash
            prompt_id="s3:proof",
        )

        expected_hash = _sha256(full)
        wrong_hash    = _sha256(display_slice)

        assert rec["input_hash"] == expected_hash, (
            "input_hash must be sha256 of the FULL prompt, not the display slice"
        )
        assert rec["input_hash"] != wrong_hash, (
            "input_hash must NOT equal sha256 of the truncated [:2000] slice — "
            "S-3 bug is still present"
        )

    def test_full_hash_differs_from_truncated_hash(self, tmp_path):
        """Confirm the two hashes are genuinely different (not a coincidence)."""
        full = _long_prompt(5000)
        truncated = full[:2000]
        assert _sha256(full) != _sha256(truncated), (
            "sha256(full_5000) must differ from sha256(first_2000) — "
            "test data is degenerate"
        )


# ===========================================================================
# 2. Backward-compatibility: no full_prompt_text → old behaviour unchanged
# ===========================================================================

class TestBackwardCompat:
    def test_no_full_prompt_text_falls_back_to_prompt_text(self, tmp_path):
        """(2) When full_prompt_text is not provided, input_hash comes from
        prompt_text as before — no regression for existing callers."""
        text = "short prompt — always fits untruncated"
        rec = log_ai_action(
            tmp_path,
            "compat_step",
            "model",
            "provider",
            prompt_text=text,
            # full_prompt_text omitted intentionally
        )
        assert rec["input_hash"] == _sha256(text), (
            "Without full_prompt_text, input_hash must equal sha256(prompt_text)"
        )

    def test_none_full_prompt_text_falls_back_to_prompt_text(self, tmp_path):
        """Explicit None also falls back to prompt_text behaviour."""
        text = "another short prompt"
        rec = log_ai_action(
            tmp_path,
            "compat_step_none",
            "model",
            "provider",
            prompt_text=text,
            full_prompt_text=None,
        )
        assert rec["input_hash"] == _sha256(text)

    def test_empty_prompt_text_empty_hash(self, tmp_path):
        """Edge case: both empty → input_hash stays empty string."""
        rec = log_ai_action(
            tmp_path,
            "empty_step",
            "model",
            "provider",
            prompt_text="",
            full_prompt_text=None,
        )
        assert rec["input_hash"] == "", "Empty prompt must produce empty input_hash"


# ===========================================================================
# 3. Meta-guard: factory_web.py call sites with [:N] truncation MUST also
#    supply full_prompt_text in the same call (regex source scan)
# ===========================================================================

class TestSourceScanMetaGuard:
    """(3) Structural guard: every _audit_log / log_ai_action call in
    factory_web.py that passes prompt_text=...[:N] MUST also pass
    full_prompt_text= in the same call.

    This ensures new call sites added in the future are caught before merge.
    """

    FACTORY_WEB = SCRIPT_DIR / "factory_web.py"

    # Pattern: a prompt_text= argument using a slice  [:N]
    RE_TRUNCATED_PROMPT = re.compile(
        r"""prompt_text\s*=\s*[A-Za-z_]\w*\s*\[:[0-9]+\]""",
    )

    # Pattern: full_prompt_text= in any form (kwarg assignment)
    RE_FULL_HASH = re.compile(
        r"""full_prompt_text\s*=""",
    )

    def _call_blocks(self, source: str) -> list[str]:
        """Extract each _audit_log(...) or log_ai_action(...) multi-line call
        block from source, using parenthesis matching."""
        blocks: list[str] = []
        i = 0
        while i < len(source):
            # Find a call site opener
            m = re.search(r'(?:_audit_log|log_ai_action)\s*\(', source[i:])
            if not m:
                break
            start = i + m.start()
            # Walk forward, counting parens
            depth = 0
            end = i + m.start()
            for j in range(i + m.start(), len(source)):
                if source[j] == '(':
                    depth += 1
                elif source[j] == ')':
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            blocks.append(source[start:end])
            i = end
        return blocks

    def test_no_truncated_prompt_without_full_hash_kwarg(self):
        """Every _audit_log / log_ai_action call in factory_web.py that uses
        prompt_text=<var>[:N] MUST also contain full_prompt_text= in the
        same call block."""
        source = self.FACTORY_WEB.read_text(encoding="utf-8")
        blocks = self._call_blocks(source)

        offending: list[str] = []
        for block in blocks:
            if self.RE_TRUNCATED_PROMPT.search(block):
                if not self.RE_FULL_HASH.search(block):
                    offending.append(block.strip()[:300])

        assert offending == [], (
            "Found _audit_log / log_ai_action call(s) with truncated "
            "prompt_text=...[:N] but WITHOUT full_prompt_text= — S-3 bug "
            "not fully closed. Offending call(s):\n\n"
            + "\n---\n".join(offending)
        )


# ===========================================================================
# 4. Hash chain integrity: verify_chain still passes after S-3 changes
# ===========================================================================

class TestHashChainIntegrity:
    def test_verify_chain_unaffected_by_full_prompt_text(self, tmp_path):
        """(4) Adding full_prompt_text must not break the SHA256 chain.
        verify_chain must report zero violations."""
        full = _long_prompt(5000)

        for i in range(4):
            log_ai_action(
                tmp_path,
                f"chain_step_{i}",
                "model",
                "provider",
                prompt_text=full[:2000],
                full_prompt_text=full,
                prompt_id=f"chain:{i}",
            )

        violations = verify_chain(tmp_path)
        assert violations == [], (
            f"Hash chain must be intact after S-3 fix. Violations: {violations}"
        )

    def test_verify_chain_mixed_old_and_new_calls(self, tmp_path):
        """Chain stays valid when mixing old-style (no full_prompt_text) and
        new-style (with full_prompt_text) calls in the same log."""
        full = _long_prompt(3000)

        # Old-style call (backward compat)
        log_ai_action(tmp_path, "old_style", "m", "p", prompt_text="short")
        # New-style call (S-3 fix)
        log_ai_action(tmp_path, "new_style", "m", "p",
                      prompt_text=full[:2000], full_prompt_text=full)
        # Another old-style
        log_ai_action(tmp_path, "old_style_2", "m", "p", prompt_text="also short")

        violations = verify_chain(tmp_path)
        assert violations == [], (
            f"Mixed call styles must not corrupt the chain. Violations: {violations}"
        )

    def test_full_prompt_text_not_stored_in_log(self, tmp_path):
        """The full prompt text must NOT appear verbatim in the log file
        (only its SHA256 hash is stored — PII protection)."""
        full = _long_prompt(500)  # shorter, but still uniquely identifiable
        log_ai_action(
            tmp_path,
            "pii_check",
            "m",
            "p",
            prompt_text=full[:200],
            full_prompt_text=full,
        )
        raw = (tmp_path / LOG_FILENAME).read_text(encoding="utf-8")
        # The raw prompt text must not appear in the JSONL file
        assert full not in raw, (
            "full_prompt_text must NOT be stored verbatim — only its hash"
        )
        assert full[:200] not in raw, (
            "prompt_text (display slice) must NOT be stored verbatim either"
        )
