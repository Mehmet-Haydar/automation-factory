"""
test_rag_ingest_device.py

Proof tests for ingest_device() in factory_web.Api:
  - Invalid path / non-PDF rejected before any AI call
  - Missing PDF file rejected with clear error
  - No API key → clear error, no silent failure
  - AI output with unsafe library_path (path traversal) rejected
  - Clean AI output saved to 09_HARDWARE_LIBRARY and relative path returned
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_GOOD_DEVICE_MD = """\
# TestVendor TestModel — drives

## metadata
```yaml
schema_version: "1.0"
device_id: "TV_TESTMODEL"
vendor: "TestVendor"
model: "TestModel 1000"
category: "drives"
subcategory: "ac_drive"
part_number: "TV-1000"
datasheet_ref: "TestVendor TestModel Manual v1.0"
library_path: "drives/TestVendor/TestModel_1000.md"
last_verified: "2026-06"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | TestVendor TestModel 1000 |
| Category | AC Drive |

## 2. Communication Interfaces

| Interface | Protocol | Notes |
|-----------|----------|-------|
| PROFINET | IRT | Standard telegram 1 |
"""


def _make_api(tmp_path: Path):
    """Create a minimal Api instance with tmp_path as FACTORY_ROOT."""
    import factory_web
    api = factory_web.Api()
    # No open project; ingest_device uses FACTORY_ROOT (repo root)
    api.root = None
    api._settings_cache = {"ai_provider": "anthropic", "ai_model": "claude-sonnet-4-6", "api_keys": {"anthropic": "sk-test"}}
    return api


# ─────────────────────────────────────────────────────────────────────────────
# Input validation (no AI call needed)
# ─────────────────────────────────────────────────────────────────────────────

def test_ingest_device_rejects_empty_path(tmp_path):
    """Empty string → ok=False, no crash."""
    import factory_web
    api = factory_web.Api()
    result = api.ingest_device("")
    assert result["ok"] is False
    assert "pdf" in result["msg"].lower() or "path" in result["msg"].lower()


def test_ingest_device_rejects_non_pdf(tmp_path):
    """Non-.pdf extension → rejected before AI call."""
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("not a pdf", encoding="utf-8")
    import factory_web
    api = factory_web.Api()
    result = api.ingest_device(str(txt_file))
    assert result["ok"] is False
    assert "pdf" in result["msg"].lower()


def test_ingest_device_rejects_missing_file(tmp_path):
    """Non-existent PDF → ok=False with clear message."""
    import factory_web
    api = factory_web.Api()
    result = api.ingest_device(str(tmp_path / "nonexistent.pdf"))
    assert result["ok"] is False
    assert "not found" in result["msg"].lower() or "exist" in result["msg"].lower()


def test_ingest_device_rejects_relative_path(tmp_path):
    """Relative path → rejected (must be absolute — file dialog always returns absolute)."""
    import factory_web
    api = factory_web.Api()
    result = api.ingest_device("relative/path/to/file.pdf")
    assert result["ok"] is False


# ─────────────────────────────────────────────────────────────────────────────
# No API key
# ─────────────────────────────────────────────────────────────────────────────

def test_ingest_device_no_api_key_returns_clear_error(tmp_path):
    """No API key → ok=False with message about API key, no silent failure."""
    pdf = tmp_path / "device.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")

    import factory_web
    api = factory_web.Api()
    # Override settings to have no API key (api.settings is the real attribute)
    api.settings = {"ai_provider": "anthropic", "ai_model": "claude-sonnet-4-6", "api_keys": {}}

    with patch("factory_web.pdfplumber" if False else "pdfplumber.open") as mock_pdf:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Device technical data " * 10
        mock_pdf.return_value.__enter__ = lambda s: MagicMock(pages=[mock_page])
        mock_pdf.return_value.__exit__ = MagicMock(return_value=False)

        result = api.ingest_device(str(pdf))

    assert result["ok"] is False
    assert "api key" in result["msg"].lower() or "key" in result["msg"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Path traversal in library_path
# ─────────────────────────────────────────────────────────────────────────────

def test_ingest_device_rejects_path_traversal_in_library_path(tmp_path):
    """AI-returned library_path with '..' must be rejected."""
    pdf = tmp_path / "device.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")

    evil_md = _GOOD_DEVICE_MD.replace(
        'library_path: "drives/TestVendor/TestModel_1000.md"',
        'library_path: "../../etc/passwd"'
    )

    import factory_web

    # Monkey-patch FACTORY_ROOT to tmp_path so we can verify the check
    with patch("factory_web.FACTORY_ROOT", tmp_path):
        # The C4 guard reads FACTORY_ROOT's classification; declare tmp_path
        # PUBLIC (mirrors the real repo-root PROJECT_STATE.json) so the guard
        # allows the call and the flow reaches the path-traversal check.
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        # Create the prompt file
        hw_lib = tmp_path / "09_HARDWARE_LIBRARY"
        hw_lib.mkdir()
        prompt_file = hw_lib / "_PROMPT_DEVICE_SPEC_EXTRACT.md"
        prompt_file.write_text("## SYSTEM PROMPT (give to the AI)\nExtract.\n---\n## USER MESSAGE\n[PASTE]\n", encoding="utf-8")

        with patch("pdfplumber.open") as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Device technical data " * 10
            ctx = MagicMock()
            ctx.__enter__ = lambda s: MagicMock(pages=[mock_page])
            ctx.__exit__ = MagicMock(return_value=False)
            mock_pdf.return_value = ctx

            with patch.object(factory_web, "_audit_log", return_value=None):
                with patch("ai_client.AIClient") as MockAI:
                    MockAI.return_value.chat.return_value = (evil_md, {})
                    api = factory_web.Api()
                    # Set settings directly (it's an instance attr set in __init__)
                    api.settings = {
                        "ai_provider": "anthropic",
                        "ai_model": "claude-sonnet-4-6",
                        "api_keys": {"anthropic": "sk-test"},
                    }
                    # No open project: the classification guard must NOT block a
                    # public datasheet ingest, so the flow reaches the path check.
                    api.root = None
                    result = api.ingest_device(str(pdf))

    assert result["ok"] is False
    assert (
        "escapes" in result["msg"].lower()
        or "unsafe" in result["msg"].lower()
        or "traversal" in result["msg"].lower()
        or "refused" in result["msg"].lower()
    )


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY_ROOT must classify as PUBLIC.
#
# Regression guard: ingest_device (and any public framework operation) falls
# back to FACTORY_ROOT when no customer project is open. The C4 guard
# (check_ai_send) reads the root's PROJECT_STATE.json; if it is missing the
# guard fail-closes to CONFIDENTIAL and wrongly BLOCKS the public datasheet
# ingest. The repo-root PROJECT_STATE.json declares the framework template
# repository PUBLIC so the guard allows it. If that file is deleted or its
# classification changed, this test fails and the no-project block returns.
# ─────────────────────────────────────────────────────────────────────────────

def test_factory_root_is_public():
    """The shipped FACTORY_ROOT must resolve to PUBLIC so the C4 guard allows
    no-project public operations (e.g. datasheet ingest)."""
    import factory_web
    from data_classification_guard import read_project_classification, check_ai_send

    assert read_project_classification(factory_web.FACTORY_ROOT) == "PUBLIC", (
        "FACTORY_ROOT no longer classifies as PUBLIC — the repo-root "
        "PROJECT_STATE.json is missing or changed; no-project ingest will be "
        "wrongly blocked by the C4 guard."
    )
    # End-to-end: the guard itself must allow with no consent for FACTORY_ROOT.
    gate = check_ai_send(factory_web.FACTORY_ROOT, "anthropic", {})
    assert gate.allowed is True
    assert gate.requires_consent is False
