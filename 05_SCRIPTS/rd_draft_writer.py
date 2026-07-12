#!/usr/bin/env python3
"""
rd_draft_writer.py — safe writer for AI-generated RD drafts (M2).

Pre-analysis steps produce RD document drafts. This module places them in
``metadata/`` so the normal review/gate flow picks them up, with hard rules:

* **Never overwrite an engineer-approved RD.** If the current file's head
  says ``status: approved|ok|done|final``, the draft is written as a
  ``*.ai_draft.md`` sibling instead and the caller is warned.
* Every replaced file is backed up to ``metadata/_history/<utc>_<name>``.
* The written draft carries ``status: DRAFT_UNVERIFIED`` frontmatter plus a
  visible banner, so both factory_web._rd_status (→ "draft") and
  project_analyzer.detect_rd_file_status (→ "draft_unverified") classify it
  correctly and gates keep demanding human approval (W-A2/W-A5 unchanged).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Canonical filenames (07_PROJECT_TEMPLATE/metadata_template) used only when
# the project has no existing RDxx*.md file to update.
CANONICAL_FILENAMES = {
    "RD01": "RD01_IO_List.md",
    "RD02": "RD02_DataDict.md",
    "RD03": "RD03_Flowchart.md",
    "RD04": "RD04_Mode.md",
    # RD05 (Safety) IS AI-drafted, but only ever as DRAFT_UNVERIFIED: the writer
    # forces that status (see _draft_header) and the gate engine (W-A2) plus the
    # FAT / customer-report preconditions block every approval gate until a
    # certified safety engineer signs it off. The AI detects/reports safety
    # signals; it never guesses SIL/PLr and never has the final word.
    "RD05": "RD05_Safety.md",
    "RD06": "RD06_Motion.md",
    "RD07": "RD07_Timing.md",
    "RD08": "RD08_Alarm.md",
    "RD09": "RD09_Comms.md",
    "RD10": "RD10_FBSpec.md",
    "RD11": "RD11_HMI.md",
    "RD12": "RD12_UseCase.md",
    "RD13": "RD13_Annotation.md",
    "RD14": "RD14_Modernization.md",
}

# Mirrors factory_web._rd_status's "approved" vocabulary (head of file).
_APPROVED_RE = re.compile(r"status:\s*(approved|ok|done|final)\b", re.IGNORECASE)

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)

_TABLE_ROW_RE = re.compile(r"^\|.+\|\s*$", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|\s*$", re.MULTILINE)


@dataclass
class DraftWriteResult:
    path: Path
    action: str            # "written" | "sidecar"
    backed_up: bool = False
    warning: str = ""


def find_rd_target(metadata_dir: Path, rd_id: str) -> Path:
    """The project's existing RDxx file (any naming variant), else canonical."""
    if metadata_dir.is_dir():
        for p in sorted(metadata_dir.glob(f"{rd_id}*.md")):
            if not p.name.endswith(".ai_draft.md"):
                return p
    return metadata_dir / CANONICAL_FILENAMES.get(rd_id, f"{rd_id}_Draft.md")


def is_engineer_approved(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:600]
    except Exception:
        return False
    return bool(_APPROVED_RE.search(head))


def has_markdown_table(content: str) -> bool:
    """Shape check: drafts that feed downstream parsers must contain a table."""
    return bool(_TABLE_ROW_RE.search(content) and _TABLE_SEP_RE.search(content))


def _strip_outer_fence(content: str) -> str:
    """Unwrap a whole-document ```/```markdown fence.

    Cheap models often return the ENTIRE draft wrapped in one code fence
    (seen live: DeepSeek's RD05) — it then renders as one grey code block
    instead of a document. Only a fence wrapping the WHOLE payload is
    removed; fences inside the document (mermaid, SCL) are untouched."""
    t = content.strip()
    if not t.startswith("```"):
        return content
    lines = t.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        inner = "\n".join(lines[1:-1])
        # Inner fences must stay paired — otherwise the outer fence was
        # actually closing an inner block; keep the original then.
        if inner.count("```") % 2 == 0:
            return inner.strip() + "\n"
    return content


def _strip_ai_frontmatter(content: str) -> str:
    """Drop a leading frontmatter block the model may have invented —
    we inject our own with the authoritative status."""
    content = _strip_outer_fence(content)
    return _FRONTMATTER_RE.sub("", content.lstrip(), count=1)


def _draft_header(rd_id: str, source_step: str, model_id: str) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (
        "---\n"
        f"status: DRAFT_UNVERIFIED\n"
        f"source: ai_preanalysis\n"
        f"rd: {rd_id}\n"
        f"generated_at: {now}\n"
        f"model: {model_id}\n"
        f"step: {source_step}\n"
        "---\n\n"
        "> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit\n"
        "> Pre-Analysis. An engineer MUST verify every row against the real\n"
        "> machine and set `status:` to `done`/`approved` before the gate\n"
        "> can advance. Addresses and safety flags are NOT trustworthy yet.\n\n"
    )


def write_rd_draft(
    project_root: Path,
    rd_id: str,
    content: str,
    source_step: str = "",
    model_id: str = "",
) -> DraftWriteResult:
    """Persist an AI draft for *rd_id* under metadata/ (rules in module doc)."""
    metadata_dir = project_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    target = find_rd_target(metadata_dir, rd_id)
    gate_warning = ""
    if rd_id == "RD01":
        # Schema gate: the RD01 table feeds four deterministic consumers
        # (cross-check, autocomplete, Equipment enrichment, assembler) —
        # AI format drift is repaired or rejected HERE, never downstream.
        from rd_table_schema import gate_rd01_draft  # type: ignore
        content, gate_rep = gate_rd01_draft(project_root, content)
        if gate_rep.repaired_cells or gate_rep.rejected_rows:
            gate_warning = gate_rep.summary
    elif rd_id == "RD11":
        # B1 (E2E): PLC_Tag must follow the DB_HMI interface contract or the
        # whole HMI chain (codegen → wiring → FC) dies downstream. Repaired
        # here, deterministically, with a visible banner.
        from rd_table_schema import gate_rd11_draft  # type: ignore
        content, gate_rep = gate_rd11_draft(project_root, content)
        if gate_rep.repaired_cells or gate_rep.rejected_rows:
            gate_warning = gate_rep.summary
    body = _draft_header(rd_id, source_step, model_id) + _strip_ai_frontmatter(content)

    if is_engineer_approved(target):
        sidecar = target.with_name(target.stem + ".ai_draft.md")
        sidecar.write_text(body, encoding="utf-8")
        return DraftWriteResult(
            path=sidecar, action="sidecar",
            warning=(
                f"{target.name} is engineer-approved — draft saved as "
                f"{sidecar.name} instead. Merge manually if wanted."
            ),
        )

    backed_up = False
    if target.is_file() and target.stat().st_size > 0:
        history = metadata_dir / "_history"
        history.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (history / f"{ts}_{target.name}").write_text(
            target.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
        )
        backed_up = True

    target.write_text(body, encoding="utf-8")
    # Delivery baseline: capture the FIRST version of every RD file
    # (REVISION_LOG's "what did the analysis first say"). First-seen wins,
    # never overwrites; a snapshot failure never blocks the draft write.
    try:
        from revision_log import snapshot_baseline  # type: ignore
        snapshot_baseline(project_root)
    except Exception:
        pass
    warning = gate_warning
    if not has_markdown_table(content):
        _w = (
            f"{rd_id} draft contains no Markdown table — downstream parsers "
            "(tag generator, device mapper) will find nothing. The draft "
            "needs manual restructuring."
        )
        warning = f"{warning}; {_w}" if warning else _w
    return DraftWriteResult(path=target, action="written",
                            backed_up=backed_up, warning=warning)
