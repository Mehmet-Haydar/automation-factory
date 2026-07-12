"""
factory_reader.py — Reads prompts and standards from the Factory folder (read-only).

Context-aware prompt mapping (file location and type drive the category):
  _input/*.awl|xml|l5x|st|s7p → parse_source (single platform parser)
  _input/*.md (e.g. _parsed.md) → extract     (14 RD extractors only)
  metadata/RD0?_*.md           → analyze      (matching RD extractor)
  _output/<generic>.scl        → review_test  (review + test prompts)
  _output/FB_Motor*.scl        → motor        (code_gen/motor)
  SCL valve / pump / io / ob   → corresponding code_gen subfolder
  REPORTS/                     → review
  Gate 6-7                     → test_gen
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent

PROMPT_DIRS = {
    "analyze":   FACTORY_ROOT / "04_AI_PROMPTS" / "analyze",
    "motor":     FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen" / "motor",
    "valve":     FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen" / "valve",
    "process":   FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen" / "process",
    "io":        FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen" / "io",
    "ob":        FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen" / "ob",
    "system":    FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen" / "system",
    "review":    FACTORY_ROOT / "04_AI_PROMPTS" / "review",
    "doc_gen":   FACTORY_ROOT / "04_AI_PROMPTS" / "doc_gen",
    "test_gen":  FACTORY_ROOT / "04_AI_PROMPTS" / "test_gen",
    "code_gen":  FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen",
}

STANDARDS_FILE = FACTORY_ROOT / "01_GLOBAL_STANDARDS" / "rules" / "GLOBAL_AI_INTERFACE.md"

# Platform → primary analyze/parser prompt mapping.
# Keys match `target_platform` values stored in PROJECT_STATE.json.
PLATFORM_PROMPTS = {
    "S5":         "PROMPT_ANALYZE_S5_AWL",
    "S7_300":     "PROMPT_ANALYZE_S7_300_STL",
    "S7_400":     "PROMPT_ANALYZE_S7_400_STL",  # B-L6 / S-21: dedicated S7-400 parser
    "S7_1200":    "PROMPT_ANALYZE_S7_1500_OPENNESS",
    "S7_1500":    "PROMPT_ANALYZE_S7_1500_OPENNESS",
    "AB":         "PROMPT_ANALYZE_AB_L5X",
    "AB_LOGIX":   "PROMPT_ANALYZE_AB_L5X",
    "ALLEN_BRADLEY": "PROMPT_ANALYZE_AB_L5X",
    "CODESYS":    "PROMPT_ANALYZE_CODESYS",
    "TWINCAT":    "PROMPT_ANALYZE_CODESYS",
    "BECKHOFF":   "PROMPT_ANALYZE_CODESYS",
}

# RDxx (metadata template) -> corresponding extractor prompt.
# Order MUST match the canonical RD taxonomy in
# project_analyzer.RD_INPUT_NEEDS (+ prompt_meta). The RD04-RD13 rows were
# previously scrambled (e.g. RD13 Annotation -> MOTION prompt) after the RD
# numbering was reordered without re-syncing this map; resynced 2026-06-29.
RD_EXTRACTORS = {
    "RD01": "PROMPT_EXTRACT_IO_FROM_CODE",
    "RD02": "PROMPT_EXTRACT_DATADICT_FROM_CODE",
    "RD03": "PROMPT_EXTRACT_FLOWCHART_FROM_CODE",
    "RD04": "PROMPT_EXTRACT_MODE_FROM_CODE",
    "RD05": "PROMPT_EXTRACT_SAFETY_FROM_CODE",
    "RD06": "PROMPT_EXTRACT_MOTION_FROM_CODE",
    "RD07": "PROMPT_EXTRACT_TIMING_FROM_CODE",
    "RD08": "PROMPT_EXTRACT_ALARM_FROM_CODE",
    "RD09": "PROMPT_EXTRACT_COMMS_FROM_CODE",
    "RD10": "PROMPT_EXTRACT_FBSPEC_FROM_CODE",
    "RD11": "PROMPT_EXTRACT_HMI_FROM_CODE",
    "RD12": "PROMPT_EXTRACT_USECASE_FROM_CODE",
    "RD13": "PROMPT_EXTRACT_ANNOTATION_FROM_CODE",
    "RD14": "PROMPT_EXTRACT_MODERNIZATION_FROM_CODE",
}


def get_context_category(file_path: Optional[Path], gate: int) -> str:
    """Determines which prompt category to show based on the selected file."""
    if gate >= 6:
        return "test_gen"
    if file_path is None:
        return "analyze"

    name_lower = file_path.name.lower()
    suffix = file_path.suffix.lower()

    parents_lower = {p.name.lower() for p in file_path.parents}
    in_input  = "_input"  in parents_lower or "input"  in parents_lower
    in_output = "_output" in parents_lower or "output" in parents_lower

    # Raw legacy source under _input/ → single platform parser.
    if in_input and suffix in (".awl", ".xml", ".l5x", ".st", ".s7p"):
        return "parse_source"

    # Parsed/intermediate Markdown under _input/ → RD extractors only.
    if in_input and suffix in (".md", ".txt"):
        return "extract"

    # RD-tagged metadata template → single RD extractor (handled in filter).
    if suffix in (".md", ".xlsx", ".csv") and re.search(r"rd\d{2}", name_lower):
        return "analyze"

    if suffix == ".scl":
        if any(k in name_lower for k in ("motor", "mot", "drive", "drv")):
            return "motor"
        if any(k in name_lower for k in ("valve", "val", "vana")):
            return "valve"
        if any(k in name_lower for k in ("pump", "pompa", "proses", "process")):
            return "process"
        if "ob" in name_lower:
            return "ob"
        if any(k in name_lower for k in ("io", "tag", "addr")):
            return "io"
        # Generic SCL in _output → review + tests rather than design prompts.
        if in_output:
            return "review_test"
        return "code_gen"

    if file_path.parent.name == "REPORTS" or "report" in name_lower:
        return "review"

    return "analyze"


def filter_prompts_by_context(
    prompts: list[dict],
    file_path: Optional[Path],
    gate: int,
    target_platform: str = "",
    category: str = "analyze",
    project_type: str = "",
) -> list[dict]:
    """Reduce a prompt list down to the items relevant for the selected file.

    Filter layers (top down):
      1. project_type:
         - "greenfield" → drop every PROMPT_ANALYZE_* and PROMPT_EXTRACT_*
           because greenfield projects have no legacy code to parse.
         - "retrofit" / "" → no-op (the catalogue is already retrofit-friendly).
      2. category-specific narrowing — see each branch.
    """
    if not prompts:
        return prompts

    cat       = (category or "").lower()
    plat_key  = (target_platform or "").strip().upper().replace("-", "_")
    pt        = (project_type   or "").strip().lower()

    # 1) project_type-level filter
    if pt == "greenfield":
        prompts = [
            p for p in prompts
            if not (
                p["name"].upper().startswith("PROMPT_EXTRACT_")
                or p["name"].upper().startswith("PROMPT_ANALYZE_")
            )
        ]
        if not prompts:
            return prompts

    # 2) Category-specific narrowing
    if cat == "parse_source":
        # Only the platform parser; if platform missing, return as-is so the
        # user can pick from the 5 parsers (with a warning rendered by UI).
        if plat_key:
            target_name = PLATFORM_PROMPTS.get(plat_key)
            if target_name:
                hits = [p for p in prompts if p["name"].upper() == target_name.upper()]
                if hits:
                    return hits
        return prompts

    if cat == "extract":
        # RDxx in filename → just that extractor; else all 14.
        if file_path is not None:
            m = re.search(r"(RD\d{2})", file_path.name, re.IGNORECASE)
            if m:
                target_name = RD_EXTRACTORS.get(m.group(1).upper())
                if target_name:
                    hits = [p for p in prompts if p["name"].upper() == target_name.upper()]
                    if hits:
                        return hits
        return prompts

    if cat == "analyze":
        # RDxx wins outright.
        if file_path is not None:
            m = re.search(r"(RD\d{2})", file_path.name, re.IGNORECASE)
            if m:
                target_name = RD_EXTRACTORS.get(m.group(1).upper())
                if target_name:
                    hits = [p for p in prompts if p["name"].upper() == target_name.upper()]
                    if hits:
                        return hits
        # Else if a platform is known, drop non-matching ANALYZE parsers
        # (extractors stay so user can pick the next extraction step).
        if plat_key:
            target_name = PLATFORM_PROMPTS.get(plat_key)
            if target_name:
                target_up = target_name.upper()
                return [
                    p for p in prompts
                    if not p["name"].upper().startswith("PROMPT_ANALYZE_")
                    or p["name"].upper() == target_up
                ]
        return prompts

    # review_test, motor, valve, io, ob, process, code_gen, review, test_gen,
    # doc_gen, system — already narrow enough.
    return prompts


def list_prompts(category: str) -> list[dict]:
    """Returns all .md prompts for the category as [{name, path, title}, ...].

    Supports both physical categories (PROMPT_DIRS) and synthetic compound
    categories: "extract" (PROMPT_EXTRACT_* in analyze/), "parse_source"
    (PROMPT_ANALYZE_* in analyze/), "review_test" (review/ + test_gen/).
    """
    cat = (category or "").lower()

    if cat == "extract":
        return [
            p for p in _list_dir(PROMPT_DIRS["analyze"])
            if p["name"].upper().startswith("PROMPT_EXTRACT_")
        ]

    if cat == "parse_source":
        return [
            p for p in _list_dir(PROMPT_DIRS["analyze"])
            if p["name"].upper().startswith("PROMPT_ANALYZE_")
        ]

    if cat == "review_test":
        return _list_dir(PROMPT_DIRS["review"]) + _list_dir(PROMPT_DIRS["test_gen"])

    prompt_dir = PROMPT_DIRS.get(cat)
    if not prompt_dir:
        return []
    return _list_dir(prompt_dir)


def _list_dir(prompt_dir: Path) -> list[dict]:
    """Glob .md prompts inside a single directory."""
    results: list[dict] = []
    if prompt_dir and prompt_dir.exists():
        for md in sorted(prompt_dir.glob("*.md")):
            if md.name.startswith("_"):
                continue
            title = _extract_title(md)
            results.append({"name": md.stem, "path": md, "title": title})
    return results


def load_prompt_text(path: Path) -> str:
    """Reads the content of a prompt file."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def get_standards_ref() -> str:
    """Returns the @ reference to the Factory standards file."""
    if STANDARDS_FILE.exists():
        rel = STANDARDS_FILE.relative_to(FACTORY_ROOT)
        return f"@{rel.as_posix()}"
    return ""


def _extract_title(path: Path) -> str:
    """Reads the first # heading from an MD file."""
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("#"):
                return re.sub(r"^#+\s*", "", line).strip()
    except Exception:
        pass
    return path.stem.replace("_", " ")


def get_project_state(project_root: Path) -> dict:
    """Reads PROJECT_STATE.json; returns an empty dict if it does not exist."""
    import json
    state_file = project_root / "PROJECT_STATE.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def detect_gate(project_root: Path) -> int:
    """Detects the active Gate (1-7) based on the project state."""
    state = get_project_state(project_root)
    completed = state.get("completed_gates", [])
    for g in range(7, 0, -1):
        if g in completed or str(g) in completed:
            return min(g + 1, 7)
    return 1
