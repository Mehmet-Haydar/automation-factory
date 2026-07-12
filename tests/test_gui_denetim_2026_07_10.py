"""test_gui_denetim_2026_07_10.py — FAZ 4 GUI denetim testleri (2026-07-10).

Bağımsız 4-fazlı GUI denetiminde bulunan ve düzeltilen sınıflar:

  G-01 (boot race)      — window.pywebview.api hazır olmadan sabit
                           setTimeout(init, 900) ile init() çağrılması;
                           `started` guard bu durumda gerçek pywebviewready
                           olayını kalıcı olarak no-op'a çeviriyordu (GUI
                           sample/demo veride kilitli kalabiliyordu).
  G-02 (silent warning)  — get_provider_for_task()'ın hesapladığı
                           "output-ceiling risk" uyarısı, 4 internal AI
                           çağrı noktasında (generate_sequence_fb,
                           rd03_chat_propose, tia_fix_propose,
                           version_compare_hypotheses) hiç _warn()'e
                           aktarılmadan sessizce atılıyordu.
  G-04 (double-submit)   — Actions panelindeki (.action satırları, sağ
                           rail + Gate view hızlı eylemleri) runAction(id)
                           çağrısı re-entrancy guard'sızdı; hızlı çift tık
                           aynı AI çağrısını / dosya yazan pipeline'ı iki
                           kez ateşleyebiliyordu.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
WEBGUI = _ROOT / "webgui"
JS_FILE = WEBGUI / "app.js"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_web  # noqa: E402


def _read_js() -> str:
    return JS_FILE.read_text(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────
# G-01 — boot race condition
# ─────────────────────────────────────────────────────────────────────
def test_no_blind_boot_timeout():
    """The old `setTimeout(init, 900)` blind guess must be gone — it raced
    the real pywebviewready event and could permanently strand the GUI on
    SAMPLE/demo data once the `started` guard tripped."""
    js = _read_js()
    assert "setTimeout(init, 900)" not in js, \
        "blind 900ms boot timeout still present — reintroduces the G-01 race"


def test_boot_polls_for_pywebview_instead_of_guessing():
    js = _read_js()
    assert "_pollForPywebviewThenInit" in js, \
        "boot sequence must actively poll for window.pywebview.api"


def test_late_pywebviewready_recovers_from_demo_fallback():
    """If pywebview only shows up after the grace period, the GUI must
    replace the demo/sample render with real project state instead of
    leaving it stuck (fail-safe recovery, not a silent freeze)."""
    js = _read_js()
    assert "_bootFellBackToDemo" in js
    assert "refreshProjectState()" in js
    # the pywebviewready listener must reference the fallback flag so the
    # recovery path is actually reachable, not dead code
    listener_block = re.search(
        r'addEventListener\("pywebviewready",\s*\(\)\s*=>\s*\{(.*?)\}\);',
        js, re.DOTALL)
    assert listener_block, "pywebviewready listener not found"
    assert "_bootFellBackToDemo" in listener_block.group(1)


# ─────────────────────────────────────────────────────────────────────
# G-02 — output-ceiling warning silently dropped at internal call sites
# ─────────────────────────────────────────────────────────────────────
def test_emit_provider_warning_helper_exists():
    assert hasattr(factory_web, "_emit_provider_warning"), \
        "_emit_provider_warning helper missing"


def test_emit_provider_warning_appends_to_buffer_when_present():
    factory_web._flush_warnings()  # drain any leftovers from other tests
    factory_web._emit_provider_warning(
        {"provider": "deepseek", "model": "x", "max_tokens": 32000,
         "warning": "deepseek is hard-capped at 8192 output tokens"})
    warnings = factory_web._flush_warnings()
    assert any("8192" in w["msg"] for w in warnings), \
        "warning text must reach the flushed _warnings buffer"
    assert any(w["category"] == "provider" for w in warnings)


def test_emit_provider_warning_noop_when_absent():
    factory_web._flush_warnings()
    factory_web._emit_provider_warning({"provider": "anthropic", "model": "x",
                                         "max_tokens": 16384})
    assert factory_web._flush_warnings() == [], \
        "no 'warning' key → nothing should be queued"


def test_internal_ai_call_sites_surface_the_warning():
    """Every internal `get_provider_for_task(...)` call inside factory_web.py
    (i.e. NOT the one directly exposed to the GUI as
    `Api.get_provider_for_task`, whose caller reads `.warning` itself) must
    be immediately followed by `_emit_provider_warning(task_cfg)` — the
    fix for G-02. Regression guard: if a new AI call site is added and
    forgets this line, this test fails loudly instead of the risk being
    silently dropped again."""
    src = _SCRIPTS.joinpath("factory_web.py").read_text(encoding="utf-8")
    # Assignment sites inside methods (skip the `def get_provider_for_task`
    # method itself and its docstring/body).
    call_sites = [m.start() for m in re.finditer(
        r'task_cfg = self\.get_provider_for_task\(', src)]
    assert len(call_sites) >= 4, "expected at least 4 internal call sites"
    for pos in call_sites:
        # look at the next ~200 chars after the assignment line
        window = src[pos:pos + 250]
        assert "_emit_provider_warning(task_cfg)" in window, (
            "internal get_provider_for_task() call at offset "
            f"{pos} does not surface task_cfg's warning — "
            "output-ceiling risk would be silently dropped (G-02 regression)")


# ─────────────────────────────────────────────────────────────────────
# G-04 — Actions panel double-submit / race condition
# ─────────────────────────────────────────────────────────────────────
def test_run_action_has_reentrancy_guard():
    js = _read_js()
    assert "_actionRunning" in js, "runAction() re-entrancy guard missing"
    m = re.search(r'async function runAction\(id\)\s*\{(.*?)\n\}\n',
                   js, re.DOTALL)
    assert m, "runAction() function not found"
    body = m.group(1)
    assert "_actionRunning" in body
    assert "try {" in body and "finally {" in body, \
        "guard must release on every exit path (try/finally), not just the happy path"


def test_run_action_rejects_concurrent_clicks_with_a_message():
    js = _read_js()
    m = re.search(r'async function runAction\(id\)\s*\{(.*?)\n\}\n',
                   js, re.DOTALL)
    assert m
    head = m.group(1)[:300]
    assert "already running" in head.lower(), \
        "a rejected double-click must tell the engineer why nothing happened " \
        "(fail-honest, not a silent no-op)"
