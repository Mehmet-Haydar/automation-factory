"""UX overhaul v3.5.0 — Faz 0/1/2 regression guards.

Covers the 2026-06-10 UX audit fixes:
- subprocess output decoding is locale-safe (the German-Windows cp850
  console + PYTHONUTF8=1 combination crashed the reader thread with
  UnicodeDecodeError at every app start);
- copy_prompt exists for real (the frontend called a missing endpoint and
  the demo fallback faked a "copied" success);
- browse_for_file picker endpoint;
- no fake-success ``|| {ok:true ...}`` fallbacks left in the JS bridge.
"""

from __future__ import annotations

import importlib
import inspect
import types
from pathlib import Path

fw = importlib.import_module("factory_web")

APP_JS = fw.FACTORY_ROOT / "webgui" / "app.js"


# ---------------------------------------------------------------------------
# Subprocess encoding — every output-capturing call must be decode-safe
# ---------------------------------------------------------------------------

class TestSubprocessEncoding:
    def test_openness_group_check_is_decode_safe(self):
        from bridges.tia import version_detect
        src = inspect.getsource(version_detect.is_user_in_openness_group)
        assert 'errors="replace"' in src, (
            "whoami /groups emits the OEM codepage (cp850 on German "
            "Windows); without errors='replace' the PYTHONUTF8=1 start.bat "
            "environment crashes the reader thread at app start")

    def test_git_helper_is_decode_safe(self):
        src = inspect.getsource(fw._run_git)
        assert 'errors="replace"' in src

    def test_code_verifier_is_decode_safe(self):
        import code_verifier
        assert inspect.getsource(code_verifier).count('errors="replace"') >= 2

    def test_project_git_is_decode_safe(self):
        import project_git
        assert 'errors="replace"' in inspect.getsource(project_git)

    def test_fb_acceptance_check_is_decode_safe(self):
        import fb_acceptance_check
        assert 'errors="replace"' in inspect.getsource(fb_acceptance_check)

    def test_group_check_still_finds_group(self, monkeypatch):
        from bridges.tia import version_detect
        fake = types.SimpleNamespace(
            returncode=0,
            stdout="VORDEFINIERT\\Benutzer\nSiemens TIA Openness  Gruppe\n",
            stderr="")
        import subprocess
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
        monkeypatch.setattr(version_detect.sys, "platform", "win32")
        assert version_detect.is_user_in_openness_group() is True


# ---------------------------------------------------------------------------
# copy_prompt — real endpoint, real text
# ---------------------------------------------------------------------------

def _mk_api():
    api = object.__new__(fw.Api)
    api.settings = {}
    api.root = None
    return api


class TestCopyPrompt:
    def test_known_prompt_returns_text(self):
        prompts = sorted((fw.FACTORY_ROOT / "04_AI_PROMPTS").glob("**/*.md"))
        assert prompts, "factory ships AI prompts"
        r = _mk_api().copy_prompt(prompts[0].stem)
        assert r["ok"], r.get("msg")
        assert r["text"], "the GUI copies this text to the clipboard"
        assert r["preview"]

    def test_unknown_prompt_is_honest_failure(self):
        r = _mk_api().copy_prompt("no_such_prompt_xyz")
        assert not r["ok"], (
            "the old demo fallback faked 'copied' — failures must be loud")

    def test_empty_name_refused(self):
        assert not _mk_api().copy_prompt("")["ok"]


# ---------------------------------------------------------------------------
# browse_for_file — native picker endpoint
# ---------------------------------------------------------------------------

class TestBrowseForFile:
    def _stub_webview(self, monkeypatch, windows):
        # Other tests may leave a fake webview module with windows behind —
        # pin our own stub so the result is deterministic in the full suite.
        import sys
        stub = types.SimpleNamespace(windows=windows,
                                     OPEN_DIALOG=0, FOLDER_DIALOG=1)
        monkeypatch.setitem(sys.modules, "webview", stub)

    def test_no_window_returns_ok_false(self, monkeypatch):
        self._stub_webview(monkeypatch, [])
        r = _mk_api().browse_for_file("tia_project")
        assert r == {"ok": False, "path": ""}

    def test_unknown_kind_is_safe(self, monkeypatch):
        self._stub_webview(monkeypatch, [])
        r = _mk_api().browse_for_file("nonsense")
        assert r["ok"] is False

    def test_picker_returns_first_selection(self, monkeypatch):
        class _Win:
            def create_file_dialog(self, dialog_type, file_types=None):
                assert file_types, "TIA preset must pass a filter"
                return [r"C:\proj\plant.ap19"]
        self._stub_webview(monkeypatch, [_Win()])
        r = _mk_api().browse_for_file("tia_project")
        assert r["ok"] and r["path"].endswith("plant.ap19")


# ---------------------------------------------------------------------------
# JS bridge honesty — no fake-success fallbacks
# ---------------------------------------------------------------------------

class TestJsBridgeHonesty:
    def test_no_fake_ok_true_fallbacks(self):
        js = APP_JS.read_text(encoding="utf-8", errors="replace")
        assert "|| {ok:true" not in js, (
            "a dead backend must never look like success — demo data is "
            "allowed only for read-only sample views (SAMPLE*)")


# ---------------------------------------------------------------------------
# Faz 1 — single source of truth (gate/RD status must match on every page)
# ---------------------------------------------------------------------------

class TestSingleSourceOfTruth:
    def _js(self):
        return APP_JS.read_text(encoding="utf-8", errors="replace")

    def test_single_action_map(self):
        js = self._js()
        assert "const actMap" not in js, (
            "dashboard and gate view carried diverging copies — use "
            "ACTION_LABELS/ACTION_ICONS")
        assert js.count("const ACTION_LABELS") == 1
        assert js.count("const ACTION_ICONS") == 1

    def test_single_rd_status_map(self):
        js = self._js()
        assert js.count("const RD_STATUS_LABEL") == 1
        assert js.count("const RD_STATUS_CLASS") == 1
        # the old inline dashboard map (empty→warn vs draft divergence)
        assert 'ok:"ok",mod:"mod",warn:"warn",draft:"draft"' not in js

    def test_refresh_helper_wired(self):
        js = self._js()
        assert "async function refreshProjectState()" in js
        assert js.count("refreshProjectState()") >= 7, (
            "open/create/advance/pipeline/rd03-apply/tia-success/refresh "
            "must all go through the single refresh path")


# ---------------------------------------------------------------------------
# Faz 2 — "Mode A/B" language removed, activity bar grouped
# ---------------------------------------------------------------------------

class TestModeLanguageRemoved:
    INDEX_HTML = fw.FACTORY_ROOT / "webgui" / "index.html"
    STYLES_CSS = fw.FACTORY_ROOT / "webgui" / "styles.css"

    def _read(self, p: Path) -> str:
        return p.read_text(encoding="utf-8", errors="replace")

    def test_no_mode_ab_text_in_ui_sources(self):
        # Users never understood "Mode A/B" — plain PROJECT/LIBRARY language
        # only. Case-insensitive sweep over every UI source file.
        import re
        pat = re.compile(r"mode[-_ ]?[ab]\b", re.IGNORECASE)
        for p in (APP_JS, self.INDEX_HTML, self.STYLES_CSS):
            hits = pat.findall(self._read(p))
            assert not hits, f"'Mode A/B' remnants in {p.name}: {hits}"

    def test_activity_bar_grouped(self):
        html = self._read(self.INDEX_HTML)
        assert html.count('class="act-group-label"') == 2
        assert ">PROJECT</div>" in html and ">LIBRARY</div>" in html
        assert ".act-group-label" in self._read(self.STYLES_CSS)

    def test_activity_icons_have_tooltips(self):
        import re
        html = self._read(self.INDEX_HTML)
        for m in re.finditer(r'<div class="act-btn[^"]*"[^>]*>', html):
            assert 'title="' in m.group(0), f"icon without tooltip: {m.group(0)}"

    def test_library_workspace_badge(self):
        js = self._read(APP_JS)
        assert js.count('class="ws-badge ws-library"') == 2, (
            "Library + Prompt workspace pages carry the badge; the Gate "
            "page is a plain title (no badge)")
        assert ".ws-badge" in self._read(self.STYLES_CSS)


# ---------------------------------------------------------------------------
# Faz 3 — first-use guidance, honest buttons, error visibility
# ---------------------------------------------------------------------------

class TestFaz3Guidance:
    INDEX_HTML = fw.FACTORY_ROOT / "webgui" / "index.html"

    def _js(self):
        return APP_JS.read_text(encoding="utf-8", errors="replace")

    def _html(self):
        return self.INDEX_HTML.read_text(encoding="utf-8", errors="replace")

    def test_send_to_client_gone(self):
        # Nothing was ever sent — the button now says what it does.
        assert "Send to client" not in self._js()

    def test_manual_steps_are_disabled_not_fake(self):
        js = self._js()
        # pv-datasheet-btn is now automated (RAG Aşama C) — excluded from this list.
        for bid in ("lib-freeze-btn", "pv-gen-ref-fb-btn"):
            assert f'id="{bid}" disabled' in js, (
                f"{bid} is a manual CLI step — it must be visibly disabled "
                "with an honest tooltip, not a toast-only fake")

    def test_next_step_card(self):
        assert 'id="rr-next"' in self._html()
        js = self._js()
        assert "function updateNextStepCard()" in js
        assert "Start Retrofit Pre-Analysis" in js, (
            "retrofit + Gate 1 must surface the pre-analysis as THE next step")

    def test_onboarding_primary_new_project(self):
        js = self._js()
        assert 'id="onb-new-btn"' in js
        assert 'id="npd-template"' in js, (
            "template choice moved into the creation form — one primary path")

    def test_post_create_guidance(self):
        assert "_raw/legacy_code" in self._js(), (
            "after creating a project the user must be told the next step")

    def test_terminal_error_dot(self):
        assert 'id="term-dot"' in self._html()
        js = self._js()
        assert 'd.classList.add("show")' in js, (
            "an error logged while the terminal tab is hidden must light "
            "the unread dot")


class TestCreateProjectMeta:
    def _api(self, monkeypatch):
        monkeypatch.setattr(fw, "_save_settings", lambda s: None)
        return _mk_api()

    def test_onboarding_meta_persisted(self, tmp_path, monkeypatch):
        import json
        api = self._api(monkeypatch)
        r = api.create_project("retrofit", "Proj_X", str(tmp_path), {
            "platform": "S7-1500",
            "customer": "  ACME GmbH ",
            "output_language": "DE",
            "data_classification": "INTERNAL",
        })
        assert r["ok"], r.get("msg")
        state = json.loads((tmp_path / "Proj_X" / "PROJECT_STATE.json")
                           .read_text(encoding="utf-8"))
        assert state["customer"] == "ACME GmbH"
        assert state["output_language"] == "DE"
        assert state["data_classification"] == "INTERNAL"

    def test_invalid_meta_values_rejected(self, tmp_path, monkeypatch):
        import json
        api = self._api(monkeypatch)
        r = api.create_project("blank", "Proj_Y", str(tmp_path), {
            "customer": "   ",
            "output_language": "FR",
            "data_classification": "SECRET",
        })
        assert r["ok"], r.get("msg")
        state = json.loads((tmp_path / "Proj_Y" / "PROJECT_STATE.json")
                           .read_text(encoding="utf-8"))
        assert state.get("output_language") != "FR"
        assert state.get("data_classification") != "SECRET"
        assert not (state.get("customer") or "").strip() or \
            state.get("customer") != "   "
