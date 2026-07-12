"""
prompt_adapter.py — Adapts user prompts to Factory standards.

Detects missing context and provides suggestions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .factory_reader import FACTORY_ROOT, STANDARDS_FILE

REQUIRED_CONTEXT = [
    ("platform", ["tia portal", "siemens", "s7", "ab ", "allen-bradley",
                  "beckhoff", "twincat", "codesys"], "Target platform not specified"),
    ("iec_block", ["function_block", "fb_", "function ", "fc_", "data_block", "db_"],
     "IEC 61131-3 block type not specified (FB/FC/DB?)"),
    ("standard_ref", ["factory", "standard", "global_ai", "rules"], "Factory standards reference missing"),
]


def adapt(prompt: str, project_root: Optional[Path] = None) -> dict:
    """
    Analyses the prompt.
    Returns: {
        "warnings": [...],    # missing context warnings
        "suggestions": [...], # automatic addition suggestions
        "enhanced": str       # enhanced prompt
    }
    """
    lower = prompt.lower()
    warnings = []
    suggestions = []
    additions = []

    for key, keywords, msg in REQUIRED_CONTEXT:
        if not any(kw in lower for kw in keywords):
            warnings.append(msg)
            if key == "platform":
                suggestions.append("Default: Siemens S7-1500 / TIA Portal V18")
                additions.append("Target platform: Siemens S7-1500, TIA Portal V18, IEC 61131-3.")
            elif key == "iec_block":
                suggestions.append("Default: FUNCTION_BLOCK structure")
                additions.append("Generate using IEC 61131-3 FUNCTION_BLOCK structure.")
            elif key == "standard_ref":
                standards_ref = _get_standards_ref()
                if standards_ref:
                    suggestions.append(f"Factory standards added: {standards_ref}")
                    additions.append(f"Follow Factory coding standards: {standards_ref}")

    enhanced = prompt.strip()
    if additions:
        enhanced += "\n\n" + "\n".join(additions)

    return {
        "warnings": warnings,
        "suggestions": suggestions,
        "enhanced": enhanced,
    }


def _get_standards_ref() -> str:
    if STANDARDS_FILE.exists():
        rel = STANDARDS_FILE.relative_to(FACTORY_ROOT)
        return f"@{rel.as_posix()}"
    return ""
