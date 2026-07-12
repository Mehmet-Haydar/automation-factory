"""
TIA compile-error assistance — deterministic classification + AI fix prompt.

After a Send-to-TIA compile run fails, this module groups the structured
compile errors (BridgeResult.compile_errors) by block ORIGIN so the GUI can
show targeted hints instead of a raw error wall:

  ai_generated  FB_Seq_*       the only AI-written artifact — a fix may be
                               PROPOSED (engineer approval required to apply)
  assembler     OB_* / iDB_*   deterministic generator output — fix the root
                               cause, never patch the output
  tags          "tag not defined" style errors — RD01 / tag-table mismatch
  library       06_KNOWLEDGE_BASE/blocks stems — SHA-256 verified, NEVER
                               patched inside a project
  unknown       anything else

Pure module: no AI calls, no file writes — factory_web owns those.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Optional

CATEGORY_AI = "ai_generated"
CATEGORY_ASSEMBLER = "assembler"
CATEGORY_TAGS = "tags"
CATEGORY_LIBRARY = "library"
CATEGORY_UNKNOWN = "unknown"

# Display order: actionable first.
_CATEGORY_ORDER = [CATEGORY_AI, CATEGORY_TAGS, CATEGORY_ASSEMBLER,
                   CATEGORY_LIBRARY, CATEGORY_UNKNOWN]

HINTS = {
    CATEGORY_AI: (
        "AI-generated sequence FB. A fix can be proposed by the AI — "
        "nothing is written without engineer approval."),
    CATEGORY_TAGS: (
        "Symbolic tag not found in the PLC tag table. Check the RD01 signal "
        "names, re-run Extract IO, and make sure tag import was not "
        "disabled for this transfer."),
    CATEGORY_ASSEMBLER: (
        "Deterministic assembler output (OB / instance DB). Fix the root "
        "cause and re-run Assemble Program — hand-patching the output "
        "drifts from the generators."),
    CATEGORY_LIBRARY: (
        "SHA-256 verified library block — never patched inside a project. "
        "Review with an engineer; library fixes go through the library "
        "acceptance gate."),
    CATEGORY_UNKNOWN: (
        "Block origin not recognised — review the error in TIA Portal."),
}


def library_block_names(kb_blocks_dir: Path) -> set:
    """Stems of all library SCL blocks (06_KNOWLEDGE_BASE/blocks/**)."""
    try:
        return {p.stem for p in Path(kb_blocks_dir).rglob("*.scl")}
    except Exception:
        return set()


def _block_stem(block: str) -> str:
    """Compile messages may carry a path-ish block reference — keep the
    last segment and drop a trailing block-type suffix like ' [FB123]'."""
    stem = (block or "").replace("\\", "/").split("/")[-1].strip()
    if " [" in stem:
        stem = stem.split(" [", 1)[0].strip()
    return stem


def classify_error(block: str, text: str, library_names: set) -> str:
    """Category for one compile error (see module docstring)."""
    low = (text or "").lower()
    if "tag" in low and ("not defined" in low or "not declared" in low):
        return CATEGORY_TAGS
    stem = _block_stem(block)
    if stem.startswith("FB_Seq"):
        return CATEGORY_AI
    if stem.startswith(("OB_", "iDB_")) or stem in ("Main", "OB1"):
        return CATEGORY_ASSEMBLER
    if stem in library_names:
        return CATEGORY_LIBRARY
    return CATEGORY_UNKNOWN


def classify(compile_errors: list, kb_blocks_dir: Optional[Path] = None,
             library_names: Optional[set] = None) -> list:
    """Group structured compile errors by origin category.

    ``compile_errors``: [{"block","severity","text"}] from BridgeResult.
    Returns ordered groups:
    [{"category","hint","proposable","blocks":[...],"errors":[...]}].
    Only ai_generated is proposable — the single AI-writable surface.
    """
    if library_names is None:
        library_names = (library_block_names(kb_blocks_dir)
                         if kb_blocks_dir else set())
    groups: dict = {}
    for err in compile_errors or []:
        cat = classify_error(err.get("block", ""), err.get("text", ""),
                             library_names)
        g = groups.setdefault(cat, {
            "category": cat,
            "hint": HINTS[cat],
            "proposable": cat == CATEGORY_AI,
            "blocks": [],
            "errors": [],
        })
        stem = _block_stem(err.get("block", ""))
        if stem and stem not in g["blocks"]:
            g["blocks"].append(stem)
        g["errors"].append({
            "block": stem,
            "text": err.get("text", ""),
        })
    return [groups[c] for c in _CATEGORY_ORDER if c in groups]


# ---------------------------------------------------------------------------
# AI fix prompt (used by factory_web.tia_fix_propose — FB_Seq only)
# ---------------------------------------------------------------------------

FIX_SYSTEM_PROMPT = """You are a Siemens SCL (Structured Text, TIA Portal) compile-error fixer.

You receive ONE complete SCL source for an AI-generated sequence FB plus the
compile errors TIA Portal reported for it. Produce a corrected version.

STRICT RULES:
1. Fix ONLY what the listed compile errors require — minimal diff, keep the
   block name, interface (VAR sections) and overall structure unchanged
   unless an error forces a change.
2. Use // line comments ONLY. Never use (* *) block comments — TIA's
   external-source parser terminates early on nested '*)'.
3. No empty statement bodies: every IF/ELSE/CASE/loop branch must contain at
   least one statement; use a lone ';' as a no-op placeholder.
4. Do not add new inputs/outputs, calls to other blocks, or functionality.
5. Output the COMPLETE corrected SCL source and nothing else — no markdown
   fences, no explanations.
"""


def build_fix_prompt(source_text: str, errors: list) -> tuple:
    """(system, user) prompt pair for the FB_Seq fix proposal."""
    err_lines = "\n".join(
        f"- [{e.get('block','?')}] {e.get('text','')}" for e in errors or [])
    user = (
        "TIA Portal compile errors:\n"
        f"{err_lines or '- (no structured errors — see source)'}\n\n"
        "Full SCL source to fix:\n"
        f"{source_text}"
    )
    return FIX_SYSTEM_PROMPT, user


def make_diff(old: str, new: str, name: str = "FB_Seq.scl") -> str:
    """Unified diff shown to the engineer before approval."""
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{name}", tofile=f"b/{name}"))
