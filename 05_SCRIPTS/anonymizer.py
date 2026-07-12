"""
anonymizer.py — Project-aware text anonymizer for pre-analysis pipeline.

Replaces known sensitive fields (customer name, project ID, engineer name,
etc.) from PROJECT_STATE.json with stable placeholders before text is sent
to a cloud AI provider. Provides a reverse map to restore originals in the
AI response.

Also applies lightweight regex patterns for common PII not in PROJECT_STATE
(email addresses, German phone numbers, German street addresses).

Usage:
    from anonymizer import build_anon_map, anonymize_text, deanonymize_text

    state = json.loads(Path("PROJECT_STATE.json").read_text())
    anon_map = build_anon_map(state)
    anon_text, replaced = anonymize_text(original_text, anon_map)
    # ... send anon_text to AI ...
    restored = deanonymize_text(ai_response, anon_map)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Placeholder tokens — stable, recognisable, reversible
# ---------------------------------------------------------------------------

_FIELD_PLACEHOLDERS: dict[str, str] = {
    "customer":     "CUSTOMER_A",
    "project_name": "PROJECT_001",
    "project_id":   "PRJ-001",
    "username":     "ENGINEER_1",
}

# Regex patterns for PII not stored in PROJECT_STATE.
# Each tuple: (compiled_pattern, replacement_token)
_REGEX_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "EMAIL_REDACTED"),
    # German/international phone numbers  (+49 ..., 0049 ..., 0XXX ...)
    (re.compile(r"(?<!\d)(\+49|0049|0\d{2,4})[\s\-/]?\d[\d\s\-/]{6,14}\d(?!\d)"), "PHONE_REDACTED"),
    # German street addresses  (Musterstraße 12, Hauptstr. 5a)
    (re.compile(
        r"\b[A-ZÄÖÜ][a-zäöüß]+(straße|strasse|str\.|weg|gasse|allee|platz|ring|damm)\s+\d+[a-z]?\b",
        re.IGNORECASE,
    ), "ADDRESS_REDACTED"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_anon_map(state: dict) -> dict[str, str]:
    """Build a {original_value: placeholder} map from PROJECT_STATE fields.

    Only non-empty values longer than 2 characters are included to avoid
    replacing short common words (e.g. a 2-letter project ID would match
    everywhere).
    """
    anon_map: dict[str, str] = {}
    for field, placeholder in _FIELD_PLACEHOLDERS.items():
        value = (state.get(field) or "").strip()
        if len(value) > 2:
            anon_map[value] = placeholder
    return anon_map


def anonymize_text(text: str, anon_map: dict[str, str]) -> tuple[str, list[str]]:
    """Replace known sensitive values and PII patterns in *text*.

    Returns:
        (anonymized_text, list_of_replaced_originals)
        The list contains each distinct original value that was substituted,
        for logging purposes (do NOT log the values themselves — log the count
        or hash them).
    """
    replaced: list[str] = []
    result = text

    # 1. Known PROJECT_STATE values (longest first to avoid partial matches)
    for original, placeholder in sorted(anon_map.items(), key=lambda x: -len(x[0])):
        if original in result:
            result = result.replace(original, placeholder)
            replaced.append(original)

    # 2. Regex patterns
    for pattern, token in _REGEX_PATTERNS:
        if pattern.search(result):
            result = pattern.sub(token, result)
            replaced.append(token)

    return result, replaced


def deanonymize_text(text: str, anon_map: dict[str, str]) -> str:
    """Restore original values from placeholders in AI response text."""
    result = text
    for original, placeholder in anon_map.items():
        result = result.replace(placeholder, original)
    return result


def anon_map_hash(anon_map: dict[str, str]) -> str:
    """SHA-256 of the sorted anon_map for audit logging.

    Stored in AI_DECISION_LOG and PROJECT_STATE so the exact anonymization
    applied can be verified later without storing the raw customer name.
    """
    payload = json.dumps(sorted(anon_map.items()), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def anonymize_file_text(
    file_path: Path,
    anon_map: dict[str, str],
    encoding: str = "utf-8",
) -> tuple[str, list[str]]:
    """Read a text file and anonymize its contents.

    Returns (anonymized_text, replaced_list).
    Binary/non-decodable files raise UnicodeDecodeError — caller should skip.
    """
    text = file_path.read_text(encoding=encoding, errors="replace")
    return anonymize_text(text, anon_map)


def build_anon_map_from_file(project_root: Path) -> dict[str, str]:
    """Convenience: read PROJECT_STATE.json and build the anonymization map."""
    state_file = project_root / "PROJECT_STATE.json"
    if not state_file.is_file():
        return {}
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        return build_anon_map(state)
    except Exception:
        return {}
