"""Guard — no real customer/plant identifiers in the public tree (S-4).

The 2026-07-10 audit found real employer/machine identifiers hard-coded in
comments and test docstrings. They were replaced with generic wording; this
guard keeps them out. The token list is base64-encoded on purpose — a
plain-text list would re-leak the very names it guards against.

Scope: every tracked *.py / *.md under the public folders. _dev/, denetim/
and .venv are excluded (git-ignored, never shipped).
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Forbidden tokens are base64-encoded so this guard file itself carries no
# plaintext identifier (a plain-text list would re-leak the names it guards).
_FORBIDDEN_B64 = ["U0hX", "TWlzY2hlciAxNTA1MEE=", "QkdUMTM3", "MTUwNTBB"]
_PUBLIC_DIRS = [
    "01_GLOBAL_STANDARDS", "02_PROJECT_TYPES", "03_DOMAIN_TOOLS",
    "04_AI_PROMPTS", "05_SCRIPTS", "06_KNOWLEDGE_BASE",
    "07_PROJECT_TEMPLATE", "08_METADATA_INPUT", "09_HARDWARE_LIBRARY",
    "docs", "examples", "tests", "webgui", "workbench",
]


def test_public_tree_carries_no_real_identifiers():
    tokens = [base64.b64decode(t).decode("ascii") for t in _FORBIDDEN_B64]
    patterns = [re.compile(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![a-z0-9])")
                for t in tokens]
    hits: list[str] = []
    me = Path(__file__).resolve()
    for d in _PUBLIC_DIRS:
        base = _ROOT / d
        if not base.is_dir():
            continue
        for p in list(base.rglob("*.py")) + list(base.rglob("*.md")):
            if p.resolve() == me or "_s5d_toolbox" in p.parts:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat, tok in zip(patterns, tokens):
                if pat.search(text):
                    hits.append(f"{p.relative_to(_ROOT)}: '{tok}'")
    assert not hits, (
        "Real customer/plant identifier found in the public tree — replace "
        "with generic wording:\n  " + "\n  ".join(hits))
