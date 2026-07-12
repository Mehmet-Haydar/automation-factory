"""RD03 Flowchart — parse, derive, check.

The Flow Steps TABLE is the single source of truth of RD03; the Mermaid
diagram is DERIVED from it deterministically (never hand-maintained, never
AI-generated). This module provides:

  parse_flow_steps(md_text)        -> list[FlowStep]
  generate_mermaid(steps)          -> str   (stateDiagram-v2 body)
  replace_mermaid_block(md, code)  -> str   (swap/append the ```mermaid fence)
  impact_check(steps, metadata_dir)-> list[dict]  (deterministic findings)

impact_check is the no-AI "what does this change affect" analysis used by the
flowchart chat loop: graph integrity (error severity) plus cross-references
against RD01 signals / RD02 variables / RD07 timers / RD04 modes (warning or
info severity — those references are heuristic by nature).

Spec: 01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_03_FLOWCHART.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Tokens that look like tag references but are language/literal keywords.
_CONDITION_KEYWORDS = {
    "TRUE", "FALSE", "AND", "OR", "NOT", "XOR",
    "DONE", "ELAPSED", "ACTIVE", "INACTIVE",
}

# StepID format per spec: ^S\d{3}[A-Z]?$
_STEP_ID_RE = re.compile(r"^S\d{3}[A-Z]?$")

# Underscore-containing identifiers inside condition/action text — the
# heuristic for "this references a signal/variable/timer".
_TAG_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")


@dataclass
class FlowStep:
    step_id: str = ""
    step_name: str = ""
    step_type: str = ""
    description: str = ""
    entry_condition: str = ""
    exit_condition: str = ""
    actions: str = ""
    next_step: str = ""
    error_step: str = ""
    timer_ref: str = ""
    mode_req: str = ""
    isa88_level: str = ""
    notes: str = ""
    status: str = "Active"

    def next_targets(self) -> list[str]:
        """NextStep cell split into individual targets.

        `(end)` is preserved as a target; `S010A | S010B` (alternative) and
        `S020A & S020B` (parallel) both yield each branch as a target.
        """
        return [t.strip() for t in re.split(r"[|&,]", self.next_step) if t.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Markdown table parsing (self-contained — no dependency on 05_SCRIPTS)
# ─────────────────────────────────────────────────────────────────────────────

def _split_row(line: str) -> list[str]:
    """Split one `| a | b |` markdown row into trimmed cells."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c or "---") for c in cells if c) \
        and any("-" in c for c in cells)


def parse_md_tables(text: str) -> list[dict]:
    """All markdown tables in `text` as {"header": [...], "rows": [[...]]}.

    Tolerant: a table is any run of `|`-prefixed lines whose second line is a
    `|---|` separator. Code fences are skipped so SCL/mermaid samples inside
    the document can contain pipe characters without confusing the parser.
    """
    tables: list[dict] = []
    lines = text.splitlines()
    in_fence = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence or not stripped.startswith("|"):
            i += 1
            continue
        # Candidate table start
        header = _split_row(lines[i])
        if i + 1 >= len(lines) or not _is_separator_row(_split_row(lines[i + 1])):
            i += 1
            continue
        rows: list[list[str]] = []
        j = i + 2
        while j < len(lines) and lines[j].strip().startswith("|"):
            rows.append(_split_row(lines[j]))
            j += 1
        tables.append({"header": header, "rows": rows})
        i = j
    return tables


def _pick(cells: list[str], idx_map: dict, *keys: str) -> str:
    for k in keys:
        if k in idx_map:
            i = idx_map[k]
            if i < len(cells):
                return (cells[i] or "").strip()
    return ""


def parse_flow_steps(md_text: str) -> list[FlowStep]:
    """The Flow Steps table of an RD03 document as FlowStep objects.

    The table is recognised by its header (must contain StepID and NextStep).
    Empty rows are skipped. Returns [] when no such table exists.
    """
    for tbl in parse_md_tables(md_text):
        idx_map = {h.strip().lower(): i for i, h in enumerate(tbl["header"])}
        # Accept canonical (StepID+NextStep) and pre-analysis slim (StepID+NextStep or StepID+Actions)
        has_id = "stepid" in idx_map or "step" in idx_map
        has_seq = "nextstep" in idx_map or "next" in idx_map or "actions" in idx_map
        if not (has_id and has_seq):
            continue
        steps: list[FlowStep] = []
        for cells in tbl["rows"]:
            step = FlowStep(
                step_id=_pick(cells, idx_map, "stepid", "step"),
                step_name=_pick(cells, idx_map, "stepname", "name"),
                step_type=_pick(cells, idx_map, "steptype"),
                description=_pick(cells, idx_map, "description"),
                entry_condition=_pick(cells, idx_map, "entrycondition", "entrycond", "entry"),
                exit_condition=_pick(cells, idx_map, "exitcondition", "exitcond", "exit"),
                actions=_pick(cells, idx_map, "actions", "action"),
                next_step=_pick(cells, idx_map, "nextstep", "next"),
                error_step=_pick(cells, idx_map, "errorstep"),
                timer_ref=_pick(cells, idx_map, "timerref"),
                mode_req=_pick(cells, idx_map, "modereq"),
                isa88_level=_pick(cells, idx_map, "isa88level"),
                notes=_pick(cells, idx_map, "notes"),
                status=_pick(cells, idx_map, "status") or "Active",
            )
            if not (step.step_id or step.step_name):
                continue
            steps.append(step)
        return steps
    return []


def steps_to_md_table(steps: list[FlowStep]) -> str:
    """Render FlowStep objects back into the canonical Flow Steps table."""
    header = ("| StepID | StepName | StepType | Description | EntryCondition "
              "| ExitCondition | Actions | NextStep | ErrorStep | TimerRef "
              "| ModeReq | ISA88Level | Notes | Status |")
    sep = "|" + "--------|" * 14
    out = [header, sep]
    for s in steps:
        out.append("| " + " | ".join([
            s.step_id, s.step_name, s.step_type, s.description,
            s.entry_condition, s.exit_condition, s.actions, s.next_step,
            s.error_step, s.timer_ref, s.mode_req, s.isa88_level,
            s.notes, s.status,
        ]) + " |")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Mermaid derivation (table = source of truth, diagram = derived)
# ─────────────────────────────────────────────────────────────────────────────

def _mm_label(text: str, max_len: int = 60) -> str:
    """Sanitise free text for use as a Mermaid node/edge label."""
    t = " ".join((text or "").split())
    t = t.replace('"', "'").replace(":", " -").replace(";", ",").replace("|", "/")
    if len(t) > max_len:
        t = t[:max_len - 1] + "…"
    return t


def generate_mermaid(steps: list[FlowStep]) -> str:
    """Deterministic flowchart TD for the given steps.

    Uses flowchart TD (not stateDiagram-v2) because flowchart honours
    themeVariables.primaryColor reliably in Mermaid v11 base theme.

    Layout:
      _s((start)) --> first step
      SXXX[StepName]
      SXXX -->|ExitCondition| SNEXT   or   --> _e((end))
      error arcs shown in red via classDef
    """
    lines = ["flowchart TD"]
    if not steps:
        lines.append("    _s(( )) --> _e(( ))")
        return "\n".join(lines)

    known = {s.step_id for s in steps if s.step_id}
    step_ids = [s.step_id for s in steps if s.step_id]

    # Node definitions
    lines.append("    _s(( ))")
    for s in steps:
        if not s.step_id:
            continue
        label = _mm_label(s.step_name or s.description or s.step_id)
        lines.append(f'    {s.step_id}["{label}"]')
    lines.append("    _e(( ))")

    # Entry edges from start node
    initials = [s for s in steps if s.step_type.strip().lower() == "initial"]
    if not initials and steps:
        initials = [steps[0]]
    for s in initials:
        if s.step_id:
            lines.append(f"    _s --> {s.step_id}")

    # Transition edges
    for s in steps:
        if not s.step_id:
            continue
        cond = _mm_label(s.exit_condition, max_len=45)
        edge_label = f'|"{cond}"|' if cond else ""
        for target in s.next_targets():
            if target.lower() in ("(end)", "end", "(son)"):
                lines.append(f"    {s.step_id} -->{edge_label} _e")
            elif target in known or target:
                lines.append(f"    {s.step_id} -->{edge_label} {target}")
        # Error arc
        err = s.error_step.strip()
        if err and err.lower() not in ("(end)", "end", ""):
            dest = "_e" if err.lower() in ("(end)", "end") else err
            lines.append(f'    {s.step_id} -->|"Error"| {dest}')

    # Inline classDef — independent of mermaid.initialize() theme config.
    # Navy/teal palette reads well on both dark and light backgrounds.
    lines.append("    classDef terminal fill:#10b981,stroke:#10b981,color:#000")
    lines.append("    classDef step fill:#1e3a5f,stroke:#10b981,color:#e2e8f0,"
                 "font-size:12px")
    lines.append("    class _s,_e terminal")
    if step_ids:
        lines.append("    class " + ",".join(step_ids) + " step")
    # Arrow + edge label styling (inline — no mermaid.initialize dependency)
    lines.append("    linkStyle default stroke:#10b981,stroke-width:2px")

    return "\n".join(lines)


def replace_flow_steps_table(md_text: str, new_table_md: str) -> str:
    """Swap the Flow Steps table of an RD03 document with `new_table_md`.

    The table is located exactly like parse_flow_steps() locates it (header
    containing StepID + NextStep, outside code fences); every other part of
    the document — frontmatter, summary, #UNKNOWNS, notes — is preserved.
    When no such table exists, a "## Flow Steps" section is appended.
    """
    lines = md_text.splitlines()
    in_fence = False
    start = end = None
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not in_fence and stripped.startswith("|"):
            header = {c.strip().lower() for c in _split_row(lines[i])}
            if ("stepid" in header and "nextstep" in header
                    and i + 1 < len(lines)
                    and _is_separator_row(_split_row(lines[i + 1]))):
                start = i
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    j += 1
                end = j
                break
        i += 1
    if start is None:
        sep = "" if md_text.endswith("\n") else "\n"
        return f"{md_text}{sep}\n## Flow Steps\n\n{new_table_md}\n"
    new_lines = lines[:start] + new_table_md.splitlines() + lines[end:]
    out = "\n".join(new_lines)
    if md_text.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out


_STATUS_LINE_RE = re.compile(r"^(status:\s*).+$", re.MULTILINE | re.IGNORECASE)


def demote_status_to_draft(md_text: str) -> str:
    """Set the frontmatter `status:` line to DRAFT (post-change re-review).

    Only the first occurrence (the frontmatter) is touched; documents without
    a status line are returned unchanged.
    """
    return _STATUS_LINE_RE.sub(lambda m: m.group(1) + "DRAFT", md_text, count=1)


_MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n.*?```", re.DOTALL)


def replace_mermaid_block(md_text: str, mermaid_code: str) -> str:
    """Swap the first ```mermaid fence of the document with `mermaid_code`.

    When the document has no mermaid fence yet, a "## Mermaid Diagram"
    section is appended. The code is always wrapped in a fresh fence.
    """
    fenced = f"```mermaid\n{mermaid_code}\n```"
    if _MERMAID_FENCE_RE.search(md_text):
        return _MERMAID_FENCE_RE.sub(lambda _m: fenced, md_text, count=1)
    sep = "" if md_text.endswith("\n") else "\n"
    return f"{md_text}{sep}\n## Mermaid Diagram\n\n{fenced}\n"


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic impact check (no AI involved)
# ─────────────────────────────────────────────────────────────────────────────

def _find_rd_file(metadata_dir: Path, rd: str) -> Optional[Path]:
    """First metadata file whose name starts with the RD id (e.g. RD01*.md)."""
    if not metadata_dir or not metadata_dir.is_dir():
        return None
    matches = sorted(metadata_dir.glob(f"{rd}*.md"))
    return matches[0] if matches else None


def _first_column_values(md_path: Optional[Path]) -> set[str]:
    """Set of first-column cell values of every table in the file."""
    if md_path is None or not md_path.is_file():
        return set()
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return set()
    out: set[str] = set()
    for tbl in parse_md_tables(text):
        for cells in tbl["rows"]:
            if cells and cells[0]:
                out.add(cells[0].strip().strip("*`"))
    return out


def _mode_vocabulary(md_path: Optional[Path]) -> set[str]:
    """Every cell value of RD04's tables, uppercased — lenient mode matching
    (ModeReq strings like AUTO/MAN map onto ModeName / OldModeName loosely)."""
    if md_path is None or not md_path.is_file():
        return set()
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return set()
    vocab: set[str] = set()
    for tbl in parse_md_tables(text):
        for cells in tbl["rows"]:
            for c in cells:
                c = (c or "").strip()
                if c and len(c) <= 24:
                    vocab.add(c.upper())
    return vocab


def _finding(severity: str, code: str, msg: str) -> dict:
    return {"severity": severity, "code": code, "msg": msg}


def impact_check(steps: list[FlowStep], metadata_dir: Optional[Path] = None) -> list[dict]:
    """Deterministic findings for a (proposed) Flow Steps table.

    Severity:
      error   — graph is structurally broken (duplicate/missing/unreachable)
      warning — referenced signal/timer not found in the project RDs
      info    — cross-reference could not be performed (source RD missing)
    """
    findings: list[dict] = []
    ids = [s.step_id for s in steps if s.step_id]
    known = set(ids)

    # -- Graph integrity (always available, error severity) -------------------
    seen: set[str] = set()
    for sid in ids:
        if sid in seen:
            findings.append(_finding(
                "error", "DUP_STEP", f"Duplicate StepID: {sid}"))
        seen.add(sid)

    for s in steps:
        if s.step_id and not _STEP_ID_RE.match(s.step_id):
            findings.append(_finding(
                "warning", "ID_FORMAT",
                f"{s.step_id}: StepID does not match the S### / S###A format"))

    initials = [s for s in steps if s.step_type.strip().lower() == "initial"]
    if not initials:
        findings.append(_finding(
            "error", "NO_INITIAL", "No step has StepType=Initial — the "
            "sequence has no defined start state"))
    for s in initials:
        if s.entry_condition.strip().upper() not in ("TRUE", ""):
            findings.append(_finding(
                "warning", "INITIAL_ENTRY",
                f"{s.step_id}: Initial step EntryCondition should be TRUE "
                f"(found: {s.entry_condition!r})"))

    has_end = False
    for s in steps:
        if not s.step_id:
            continue
        targets = s.next_targets()
        if not targets and s.step_type.strip().lower() != "final":
            findings.append(_finding(
                "error", "DEAD_END",
                f"{s.step_id}: no NextStep and not a Final step — sequence "
                f"stalls here"))
        for t in targets:
            if t.lower() in ("(end)", "end", "(son)"):
                has_end = True
                continue
            if t not in known:
                findings.append(_finding(
                    "error", "MISSING_TARGET",
                    f"{s.step_id}: NextStep target {t!r} does not exist in "
                    f"the table"))
        err = s.error_step.strip()
        if err and err.lower() not in ("(end)", "end") and err not in known:
            findings.append(_finding(
                "error", "MISSING_ERROR_STEP",
                f"{s.step_id}: ErrorStep target {err!r} does not exist in "
                f"the table"))
    if steps and not has_end:
        findings.append(_finding(
            "warning", "NO_END",
            "No step reaches (end) — the sequence never terminates"))

    # Reachability from the Initial steps (or the first row as fallback).
    if steps:
        roots = [s.step_id for s in (initials or steps[:1]) if s.step_id]
        edges: dict[str, list[str]] = {}
        for s in steps:
            if not s.step_id:
                continue
            outs = [t for t in s.next_targets() if t in known]
            err = s.error_step.strip()
            if err in known:
                outs.append(err)
            edges[s.step_id] = outs
        reachable: set[str] = set()
        stack = list(roots)
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            stack.extend(edges.get(cur, []))
        for sid in ids:
            if sid not in reachable:
                findings.append(_finding(
                    "error", "UNREACHABLE",
                    f"{sid}: unreachable from the Initial step"))

    # -- Cross-references against the other RDs (best effort) ----------------
    rd01 = _find_rd_file(metadata_dir, "RD01") if metadata_dir else None
    rd02 = _find_rd_file(metadata_dir, "RD02") if metadata_dir else None
    rd07 = _find_rd_file(metadata_dir, "RD07") if metadata_dir else None
    rd04 = _find_rd_file(metadata_dir, "RD04") if metadata_dir else None

    if metadata_dir:
        signals = _first_column_values(rd01)
        variables = _first_column_values(rd02)
        timers = _first_column_values(rd07)
        modes = _mode_vocabulary(rd04)
        vocab = signals | variables | timers | known

        if rd01 is None:
            findings.append(_finding(
                "info", "RD01_MISSING",
                "RD01 (IO list) not found — signal references unchecked"))

        if vocab - known:   # only meaningful when we have something to match
            for s in steps:
                text = " ".join((s.entry_condition, s.exit_condition, s.actions))
                for tok in _TAG_TOKEN_RE.findall(text):
                    if tok.upper() in _CONDITION_KEYWORDS:
                        continue
                    if tok.startswith(("TMR_", "T_")) and tok in timers:
                        continue
                    if tok not in vocab:
                        where = "RD07 timer list" if tok.startswith("TMR_") \
                            else "RD01 IO list or RD02 data dictionary"
                        findings.append(_finding(
                            "warning", "UNKNOWN_REF",
                            f"{s.step_id or s.step_name}: references "
                            f"{tok!r} — not found in the {where}. New "
                            f"hardware/sensor or a typo?"))

        for s in steps:
            tr = s.timer_ref.strip()
            if tr:
                if rd07 is None:
                    findings.append(_finding(
                        "info", "RD07_MISSING",
                        f"{s.step_id}: TimerRef {tr!r} — RD07 (timing) not "
                        f"found, unchecked"))
                elif tr not in timers:
                    findings.append(_finding(
                        "warning", "UNKNOWN_TIMER",
                        f"{s.step_id}: TimerRef {tr!r} is not defined in "
                        f"RD07 — add the timer or fix the reference"))

        if rd04 is not None and modes:
            for s in steps:
                for m in re.split(r"[,/|]", s.mode_req):
                    m = m.strip().upper()
                    if not m or m == "ALL":
                        continue
                    if m not in modes:
                        findings.append(_finding(
                            "warning", "UNKNOWN_MODE",
                            f"{s.step_id}: ModeReq {m!r} not found in RD04 "
                            f"mode table"))

    # De-duplicate identical findings (same token referenced by many steps
    # stays per-step; exact duplicates collapse).
    out: list[dict] = []
    seen_msgs: set[str] = set()
    for f in findings:
        if f["msg"] in seen_msgs:
            continue
        seen_msgs.add(f["msg"])
        out.append(f)
    return out
