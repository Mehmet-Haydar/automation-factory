"""Proof tests — fail-open holes closed (S-2 audit gaps, S-3 anonymization).

2026-07-10 audit classes:
- S-3: every AI-send path anonymized inside `except Exception: pass` —
  exactly when the data classification made anonymization MANDATORY, a
  failure silently sent the ORIGINAL text to the provider. Contract now:
  _anonymize_or_block fails CLOSED when required, warns visibly when not.
- S-2: two audit-log call sites swallowed AuditLogError with a bare pass;
  the gap in the audit chain is now surfaced through the warnings channel.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_web  # noqa: E402
from factory_web import _anonymize_or_block  # noqa: E402


def _boom(text, anon_map):
    raise RuntimeError("regex exploded")


def test_required_anonymization_failure_blocks():
    with patch("anonymizer.anonymize_text", _boom):
        text, err = _anonymize_or_block("SECRET GmbH", {"SECRET": "X"},
                                        required=True, what="unit test")
    assert err is not None and "blocked" in err
    assert "SECRET GmbH" == text, "caller gets original ONLY with the error"


def test_optional_anonymization_failure_warns_but_continues():
    factory_web._flush_warnings()
    with patch("anonymizer.anonymize_text", _boom):
        text, err = _anonymize_or_block("plain text", {}, required=False,
                                        what="unit test")
    assert err is None and text == "plain text"
    warns = factory_web._flush_warnings()
    assert any(w.get("category") == "privacy" for w in warns), \
        "opsiyonel yol bile SESSİZ kalamaz"


def test_success_path_passes_through():
    with patch("anonymizer.anonymize_text",
               lambda t, m: (t.replace("ACME", "CUSTOMER_A"), m)):
        text, err = _anonymize_or_block("ACME line", {"ACME": "CUSTOMER_A"},
                                        required=True, what="unit test")
    assert err is None and text == "CUSTOMER_A line"


def test_no_bare_pass_left_on_anonymize_or_audit_paths():
    """Static regression guard: the fixed patterns must not come back."""
    import re
    src = (Path(factory_web.__file__)).read_text(encoding="utf-8")
    bare = re.findall(
        r"anonymize_text\([^)]*\)\s*\n\s*except Exception:\s*\n\s*pass", src)
    assert not bare, f"fail-open anonymize deseni geri gelmiş: {bare}"
    # every call site outside the helper routes through _anonymize_or_block:
    # the helper holds the ONLY `from anonymizer import anonymize_text`
    helper_end = src.index("def _flush_warnings")
    assert "from anonymizer import anonymize_text" not in src[helper_end:], \
        "helper dışında çıplak anonymize_text kullanımı kalmamalı"
    assert "pass  # audit failure is non-blocking" not in src, \
        "sessiz audit-log yutması geri gelmiş"
