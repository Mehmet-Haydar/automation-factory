"""Charter §11 regresyonu — *meta* test: factory_web.Api'nin AIClient veya
AutoFlowRunner instantiate eden HER metodu, gönderimden önce soft PII /
müşteri-adı uyarısını (_pii_soft_warn) çağırmalı.

İlk ULAK fazı (v3.2.0) uyarıyı 4 çağrı noktasına ekledi; sonradan eklenen
generate_sequence_fb / rd03_chat_propose / run_retrofit_preanalysis /
_ocr_legacy_pdf uyarısız kaldı — müşteri adı içeren proje verisi sessizce
public-tier API'ye gidebiliyordu. Ayrıca eski çağrı noktalarının döndürdüğü
`_pii_warnings` anahtarını GUI hiç okumuyordu (uyarı kullanıcıya görünmüyordu).
Yeni bir AI çağrı yolu eklendiğinde bu test, §11 uyarısı atlanırsa kırılır.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

import factory_web as fw

WEBGUI_APP_JS = Path(fw.__file__).resolve().parent.parent / "webgui" / "app.js"


def _ai_call_methods() -> list[tuple[str, str]]:
    """(name, source) of every Api method that constructs an AI sender."""
    src = inspect.getsource(fw)
    tree = ast.parse(src)
    api_cls = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == "Api"
    )
    found: list[tuple[str, str]] = []
    for node in api_cls.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        seg = ast.get_source_segment(src, node) or ""
        if "AIClient(" in seg or "AutoFlowRunner(" in seg:
            found.append((node.name, seg))
    return found


def test_scan_finds_known_ai_call_sites():
    """Tarayıcının kendisi kör olmasın: bilinen siteler listede olmalı."""
    names = {n for n, _ in _ai_call_methods()}
    expected = {
        "run_workflow", "normalize_prompt", "get_ai_suggestion",
        "run_ai_prompt", "generate_sequence_fb", "rd03_chat_propose",
        "run_retrofit_preanalysis", "_ocr_legacy_pdf",
    }
    missing = expected - names
    assert not missing, (
        f"Meta-test scanner no longer sees these AI call sites: {missing} — "
        "if they were renamed/removed update `expected`; if the scanner "
        "broke, fix it (it guards §11 coverage)."
    )


@pytest.mark.parametrize(
    "name,seg", _ai_call_methods(), ids=[n for n, _ in _ai_call_methods()],
)
def test_every_ai_call_site_emits_pii_soft_warn(name: str, seg: str):
    """§11: AI'ya veri gönderen her metot _pii_soft_warn'ı çağırmalı."""
    assert "_pii_soft_warn" in seg, (
        f"{name} instantiates an AI sender but never calls _pii_soft_warn — "
        "charter §11 soft PII/customer-name warning is being skipped. "
        "Add: for w in self._pii_soft_warn(provider): _warn(w, category='privacy') "
        "(or include the list in the response as '_pii_warnings')."
    )


def test_gui_consumes_pii_warnings_key():
    """Eski 4 çağrı noktası uyarıyı `_pii_warnings` anahtarıyla döndürür;
    app.js bu anahtarı okumazsa uyarı kullanıcıya hiç görünmez."""
    js = WEBGUI_APP_JS.read_text(encoding="utf-8", errors="replace")
    assert "_pii_warnings" in js, (
        "webgui/app.js no longer references `_pii_warnings` — the §11 PII "
        "warnings returned by run_workflow/normalize_prompt/get_ai_suggestion/"
        "run_ai_prompt would be silently dropped in the GUI."
    )


# ── _pii_soft_warn davranış testleri ────────────────────────────────────────

def _make_api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"ai_provider": "anthropic", "ai_mode": "api"}
    return api


def test_pii_warn_flags_customer_name(tmp_path, monkeypatch):
    (tmp_path / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    api = _make_api(tmp_path)
    monkeypatch.setattr(
        fw.Api, "_project_state",
        lambda self: {"customer_name": "ACME GmbH"},
    )
    warns = api._pii_soft_warn("anthropic")
    assert any("ACME GmbH" in w for w in warns), warns
    assert any("anthropic" in w for w in warns), warns


def test_pii_warn_flags_classification_markers(tmp_path, monkeypatch):
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"note": "CONFIDENTIAL customer data"}', encoding="utf-8",
    )
    api = _make_api(tmp_path)
    monkeypatch.setattr(fw.Api, "_project_state", lambda self: {})
    warns = api._pii_soft_warn("google")
    assert any("CONFIDENTIAL" in w for w in warns), warns


def test_pii_warn_silent_for_non_public_provider(tmp_path, monkeypatch):
    (tmp_path / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    api = _make_api(tmp_path)
    monkeypatch.setattr(
        fw.Api, "_project_state",
        lambda self: {"customer_name": "ACME GmbH"},
    )
    assert api._pii_soft_warn("local_llm") == []


def test_pii_warn_silent_without_project(monkeypatch):
    api = fw.Api()
    api.root = None
    assert api._pii_soft_warn("anthropic") == []
