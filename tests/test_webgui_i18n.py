"""Proof tests — GUI i18n dictionary consistency (EN/TR/DE).

The 2026-07-06 user finding was MIXED languages in the GUI (15 hardcoded
Turkish strings in an otherwise-English app.js). These tests keep that from
regressing: every key used in markup/code exists in the dictionary, and
every dictionary entry carries all three languages.
"""
from __future__ import annotations

import re
from pathlib import Path

WEBGUI = Path(__file__).resolve().parents[1] / "webgui"
I18N_SRC = (WEBGUI / "i18n.js").read_text(encoding="utf-8")
APP_SRC = (WEBGUI / "app.js").read_text(encoding="utf-8")
HTML_SRC = (WEBGUI / "index.html").read_text(encoding="utf-8")

_KEY_RE = re.compile(r'^\s*"([a-z0-9_.]+)":\s*\{', re.M)
_ENTRY_RE = re.compile(r'"([a-z0-9_.]+)":\s*\{(.*?)\}', re.S)


def _dictionary() -> dict[str, str]:
    body = I18N_SRC.split("const I18N = {", 1)[1]
    return {m.group(1): m.group(2) for m in _ENTRY_RE.finditer(body)}


def test_every_entry_has_all_three_languages():
    d = _dictionary()
    assert len(d) >= 50, "sözlük beklenenden küçük — parse mi bozuldu?"
    missing = []
    for key, body in d.items():
        for lang in ("en:", "tr:", "de:"):
            if lang not in body:
                missing.append(f"{key} → {lang[:-1]}")
    assert not missing, f"eksik çeviriler: {missing}"


def test_keys_used_in_html_exist():
    used = set(re.findall(r'data-i18n(?:-title|-ph)?="([a-z0-9_.]+)"',
                          HTML_SRC))
    assert used, "index.html hiç data-i18n taşımıyor — entegrasyon kayıp"
    d = _dictionary()
    unknown = sorted(used - set(d))
    assert not unknown, f"index.html bilinmeyen anahtar kullanıyor: {unknown}"


def test_keys_used_in_app_js_exist():
    used = set(re.findall(r'\bt\("([a-z0-9_.]+)"\)', APP_SRC))
    assert used, "app.js hiç t() çağrısı içermiyor — entegrasyon kayıp"
    d = _dictionary()
    unknown = sorted(used - set(d))
    assert not unknown, f"app.js bilinmeyen anahtar kullanıyor: {unknown}"


def test_i18n_loaded_before_app_js():
    i = HTML_SRC.find('src="i18n.js"')
    a = HTML_SRC.find('src="app.js"')
    assert 0 < i < a, "i18n.js app.js'ten ÖNCE yüklenmeli (t() tanımı için)"


def test_no_stray_turkish_outside_dictionary():
    """app.js may contain Turkish only as language NAMES or backend-message
    match keywords — never as UI copy (the original mixed-language bug)."""
    allow = ("Türkçe", "TÜV", "sınıflandırılmış", "Gördüm")
    hits = []
    for n, line in enumerate(APP_SRC.splitlines(), 1):
        if any(ch in line for ch in "çğşıİĞŞÇ"):
            if not any(a in line for a in allow):
                hits.append(f"{n}: {line.strip()[:70]}")
    assert not hits, f"app.js'te sözlük dışı Türkçe metin: {hits}"
