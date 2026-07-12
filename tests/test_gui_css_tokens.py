"""test_gui_css_tokens.py — FAZ 4 GUI denetim testleri.

Sınıf 1: --bg2 CSS token tanımlı olmalı
Sınıf 2: .diag-row CSS kuralı tanımlı olmalı
Sınıf 14: strStore global reentrant kontrol (okuma)
"""
import re
from pathlib import Path

WEBGUI = Path(__file__).resolve().parent.parent / "webgui"
CSS_FILE = WEBGUI / "styles.css"
JS_FILE  = WEBGUI / "app.js"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def test_bg2_token_defined_in_root():
    """--bg2 CSS custom property tanımlı olmalı (dark theme root)."""
    css = _read(CSS_FILE)
    # :root içinde --bg2 tanımı olmalı
    assert "--bg2:" in css, "--bg2 CSS token ':root' içinde tanımlı değil"


def test_bg2_light_theme_defined():
    """--bg2 light tema override içinde de tanımlı olmalı."""
    css = _read(CSS_FILE)
    light_block_match = re.search(
        r':root\[data-theme="light"\]\s*\{([^}]+)\}', css, re.DOTALL
    )
    assert light_block_match, "Light theme :root block bulunamadı"
    block = light_block_match.group(1)
    assert "--bg2:" in block, "--bg2 light theme override içinde tanımlı değil"


def test_diag_row_css_defined():
    """.diag-row CSS kuralı tanımlı olmalı."""
    css = _read(CSS_FILE)
    assert ".diag-row" in css, ".diag-row CSS sınıfı tanımlı değil"


def test_diag_row_used_in_js():
    """.diag-row sınıfı JS içinde üretilmeli."""
    js = _read(JS_FILE)
    assert '"diag-row"' in js or "'diag-row'" in js or "diag-row" in js, \
        "diag-row JS içinde kullanılmıyor"


def test_bg2_used_in_css():
    """--bg2 token CSS içinde gerçekten kullanılmalı (sadece tanımlanmış değil)."""
    css = _read(CSS_FILE)
    uses = re.findall(r'var\(--bg2\)', css)
    assert len(uses) >= 1, "var(--bg2) CSS içinde hiç kullanılmıyor"


def test_advance_gate_bridge_signature():
    """Backend.advance_gate bridge metodu iki argüman kabul etmeli (accept_structural_only)."""
    js = _read(JS_FILE)
    # acceptStructural parametresi backend bridge'de olmalı
    assert "acceptStructural" in js, \
        "Backend.advance_gate bridge metodunda acceptStructural parametresi eksik"


def test_consume_warnings_in_backend():
    """Backend._consumeWarnings _warnings alanını tüketiyor olmalı."""
    js = _read(JS_FILE)
    assert "_consumeWarnings" in js, "Backend._consumeWarnings metodu bulunamadı"
    assert "_warnings" in js, "_warnings alanı JS tarafında tüketilmiyor"


def test_render_null_guard():
    """render() fonksiyonu STATE null kontrolü yapmalı."""
    js = _read(JS_FILE)
    # render() fonksiyonu içinde !STATE kontrolü
    render_block = re.search(r'function render\(\)\s*\{(.{0,200})', js, re.DOTALL)
    assert render_block, "render() fonksiyonu bulunamadı"
    block = render_block.group(1)
    assert "!STATE" in block or "STATE ==" in block, \
        "render() başında STATE null guard eksik"


def test_precondition_error_handled():
    """generate_customer_report precondition_error alanı JS tarafında işlenmeli."""
    js = _read(JS_FILE)
    assert "precondition_error" in js, \
        "generate_customer_report precondition_error JS tarafında işlenmiyor"
    assert "r.reasons" in js or "reasons" in js, \
        "precondition reasons alanı JS'te kullanılmıyor"
