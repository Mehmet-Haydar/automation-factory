"""FIX-4 (privacy) — visual files sent to Gemini Vision are NOT anonymized.

README/PROJECT_VISION already state this honestly; these tests pin the two
code-level safeguards so they cannot silently regress:

1. The GUI consent modal (webgui/app.js) must carry an explicit warning that
   photos/drawings/PDFs are uploaded as-is (only legacy code text is
   anonymized) and must tell the engineer to redact logos/nameplates first.

2. The backend (05_SCRIPTS/factory_web.py) must emit a privacy-category
   warning via _warn() before handing multimodal files to the AI runner, and
   the pre-analysis response must flush warnings to the UI via
   _attach_warnings().
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_JS = PROJECT_ROOT / "webgui" / "app.js"
FACTORY_WEB = PROJECT_ROOT / "05_SCRIPTS" / "factory_web.py"


def _consent_modal_source() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    start = src.index("function _openRetrofitConsentModal")
    # Slice to the next top-level function so assertions stay local.
    nxt = src.find("\nfunction ", start + 1)
    return src[start : nxt if nxt != -1 else len(src)]


def _preanalysis_source() -> str:
    src = FACTORY_WEB.read_text(encoding="utf-8")
    start = src.index("def run_retrofit_preanalysis")
    nxt = src.find("\n    def ", start + 1)
    return src[start : nxt if nxt != -1 else len(src)]


class TestConsentModalWarning:
    def test_modal_warns_visual_files_not_anonymized(self):
        modal = _consent_modal_source()
        assert re.search(r"NOT anonymized", modal), (
            "Consent modal must explicitly state that visual files are NOT "
            "anonymized before upload"
        )

    def test_modal_tells_engineer_to_redact_identifying_info(self):
        modal = _consent_modal_source()
        for needle in ("logo", "nameplate"):
            assert needle in modal.lower(), (
                f"Consent modal must instruct removal of customer {needle}s "
                "before upload"
            )


class TestBackendPrivacyWarning:
    def test_warn_emitted_before_runner_starts(self):
        body = _preanalysis_source()
        warn_pos = body.find('category="privacy"')
        run_pos = body.find("runner.run_async")
        assert warn_pos != -1, (
            "run_retrofit_preanalysis must emit a privacy-category _warn() "
            "for unanonymized visual files"
        )
        assert run_pos != -1, "expected runner.run_async call in pre-analysis"
        assert warn_pos < run_pos, (
            "privacy warning must be emitted BEFORE the AI workflow starts, "
            "not after the files have already been uploaded"
        )

    def test_warning_mentions_no_anonymization(self):
        body = _preanalysis_source()
        assert re.search(r"WITHOUT anonymization", body), (
            "backend warning text must state visual files go out WITHOUT "
            "anonymization"
        )

    def test_response_flushes_warnings_to_ui(self):
        body = _preanalysis_source()
        assert "_attach_warnings(" in body, (
            "pre-analysis responses must go through _attach_warnings() so the "
            "privacy warning reaches the UI warning feed"
        )
