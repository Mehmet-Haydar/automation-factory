"""prompt_normalizer.py — Rewrite a user prompt to match Factory standards.

Best-effort wrapper around AIClient. When the user opens the "+ New Prompt"
dialog and hits "Normalize", we call this with their draft, the chosen
category and an active AIClient. The reply is shown next to the original
so the user can pick whichever variant they prefer.

If anything goes wrong (no API key, network error, missing SDK) the
caller gets a NormalizeError and the dialog falls back to plain save.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from .factory_reader import get_standards_ref

# ---------------------------------------------------------------------------
# I-2 fix (grep kardeşi): classification guard — AI çağrısı öncesi kontrol
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "05_SCRIPTS"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from data_classification_guard import check_ai_send as _check_ai_send  # type: ignore
    _GUARD_AVAILABLE = True
except ImportError:
    _GUARD_AVAILABLE = False


class NormalizeError(Exception):
    """Raised when normalization could not produce a useful result."""


_SYSTEM_PROMPT = """You are a prompt-engineering reviewer for an industrial PLC
AI factory. Rewrite the user's draft so it complies with these rules:

1. Always start by referencing the Factory standards: {standards}
2. Specify the expected output format explicitly (Markdown table when the
   user lists tabular data; SCL code block when the user asks for code;
   Markdown sections otherwise).
3. End the prompt with a "#UNKNOWNS" section that asks the model to call
   out anything that needs human confirmation.
4. Keep the user's intent and domain terminology. Do not invent new
   constraints. Do not add disclaimers, apologies or commentary.
5. Match category="{category}" conventions: analyze prompts request
   structured extraction; code_gen prompts request TIA-compatible SCL
   with IEC 61131-3 style; review prompts request pass/fail tables;
   test_gen prompts request input/expected tables plus an SCL harness.

Return ONLY the rewritten prompt. No preface, no explanation."""


def normalize_prompt(
    raw: str,
    category: str,
    ai_client: Any,
    *,
    project_root: Optional[Path] = None,
    provider: str = "",
) -> str:
    """Rewrite ``raw`` through ``ai_client`` and return the normalized prompt.

    ``ai_client`` is expected to expose ``.chat(system, user, max_tokens)``
    returning ``(text, usage)`` (the project's AIClient class qualifies).
    Raises :class:`NormalizeError` on any failure path.

    Parameters
    ----------
    project_root:
        Aktif projenin kök dizini. Verilirse veri sınıflandırma kapısı
        uygulanır; eksikse fail-closed (bilinmeyen → CONFIDENTIAL → blok).
    provider:
        Kullanılan AI sağlayıcı adı (``ai_client``'tan çekilemiyorsa boş bırak;
        boş string bilinmeyen sağlayıcı olarak değerlendirilir → fail-closed).
    """
    if not raw or not raw.strip():
        raise NormalizeError("Cannot normalize an empty prompt.")

    if ai_client is None:
        raise NormalizeError("No AIClient available (set an API key first).")

    # ------------------------------------------------------------------
    # I-2 fix: classification guard — fail-closed
    # ------------------------------------------------------------------
    if _GUARD_AVAILABLE:
        _allowed, _reason = _check_ai_send(project_root, provider or "")
        if not _allowed:
            raise NormalizeError(
                f"[IP_LEAKAGE] Veri sınıflandırma kapısı engelledi — "
                f"normalize_prompt çalıştırılamaz: {_reason}"
            )
    else:
        # Guard modülü yüklenemedi → fail-closed
        raise NormalizeError(
            "[IP_LEAKAGE] data_classification_guard modülü yüklenemedi — "
            "fail-closed: normalize_prompt çalıştırılamaz."
        )

    system = _SYSTEM_PROMPT.format(
        standards=get_standards_ref() or "@01_GLOBAL_STANDARDS/rules/GLOBAL_AI_INTERFACE.md",
        category=category or "analyze",
    )
    try:
        text, _usage = ai_client.chat(
            system=system,
            user=raw.strip(),
            max_tokens=2000,
            temperature=0.2,
        )
    except Exception as e:
        raise NormalizeError(f"AI call failed: {e}") from e

    out = (text or "").strip()
    if not out:
        raise NormalizeError("AI returned an empty response.")
    return out
