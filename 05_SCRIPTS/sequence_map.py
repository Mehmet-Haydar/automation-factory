#!/usr/bin/env python3
"""
sequence_map.py — deterministic Schrittkette (step chain) detection.

Classic S5 sequences are S/R latch chains: step marker M_{k+1} is SET by a
condition that contains step marker M_k (plus the transition condition) and
RESET by the next step or the chain reset. That structure is mechanically
detectable from the proven coil logic (s5_logic_extract) — no AI:

  * step candidates  = M-flags with BOTH a set and a reset condition
  * edge A → B       = A appears (non-negated) in B's set condition
  * a chain          = a connected component with >= 3 steps

Output: REPORTS/SEQUENCE_DRAFT.md — ordered steps, symbol names, full
transition conditions, and the proof line per network. DRAFT: review
material for the engineer / input for the sequence-FB step; never code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from s5_logic_extract import (  # type: ignore
    NetworkLogic, Not, Var, extract_project_logic, render_expr, _vars,
)


@dataclass
class SequenceSummary:
    latches: int = 0
    chains: int = 0
    steps_in_chains: int = 0
    report_path: Path | None = None


def _positive_vars(e) -> set[str]:
    """Operands that appear WITHOUT negation anywhere in the expression.

    (A step edge is 'previous step active' — a negated occurrence is a
    lockout, not a predecessor.)"""
    out: set[str] = set()

    def walk(x, neg: bool):
        if isinstance(x, Var):
            if not neg:
                out.add(x.operand)
        elif isinstance(x, Not):
            walk(x.a, not neg)
        else:
            walk(x.a, neg)
            walk(x.b, neg)

    walk(e, False)
    return out


def build_chains(nets: list[NetworkLogic]) -> tuple[dict, list[list[str]]]:
    """Returns ({marker: (NetworkLogic, CoilLogic)}, chains as ordered lists)."""
    latches: dict[str, tuple] = {}
    for nl in nets:
        if not nl.parsed:
            continue
        for op, coil in nl.coils.items():
            if (op.startswith("M") and coil.set_cond is not None
                    and coil.reset_cond is not None and op not in latches):
                latches[op] = (nl, coil)

    edges: dict[str, set[str]] = {m: set() for m in latches}
    for m, (_nl, coil) in latches.items():
        for dep in _positive_vars(coil.set_cond):
            if dep in latches and dep != m:
                edges[dep].add(m)   # dep --> m

    # connected components (undirected view), then a greedy order following
    # the directed edges from the component's entry nodes
    seen: set[str] = set()
    chains: list[list[str]] = []
    undirected: dict[str, set[str]] = {m: set() for m in latches}
    for a, targets in edges.items():
        for b in targets:
            undirected[a].add(b)
            undirected[b].add(a)
    for start in sorted(latches):
        if start in seen:
            continue
        comp = []
        stack = [start]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            comp.append(n)
            stack.extend(sorted(undirected[n] - seen))
        if len(comp) < 3:
            continue
        # order: repeatedly take nodes whose in-chain predecessors are done
        comp_set = set(comp)
        preds = {m: {d for d in latches if m in edges.get(d, set())}
                 & comp_set for m in comp}
        ordered, left = [], set(comp)
        while left:
            ready = sorted(m for m in left if preds[m] <= set(ordered))
            if not ready:                 # cycle — take lowest, stay honest
                ready = [sorted(left)[0]]
            ordered.append(ready[0])
            left.discard(ready[0])
        chains.append(ordered)
    return latches, chains


def generate_sequence_draft(project_root: Path) -> SequenceSummary:
    root = Path(project_root)
    nets = extract_project_logic(root)
    latches, chains = build_chains(nets)
    summ = SequenceSummary(latches=len(latches), chains=len(chains),
                           steps_in_chains=sum(len(c) for c in chains))

    from legacy_enrich import load_symbols  # type: ignore
    names = load_symbols(root / "_raw" / "legacy_code")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L = [
        "# SEQUENCE DRAFT — Schrittkette candidates (deterministic)",
        "",
        f"Generated: {now}",
        f"S/R latches found: {summ.latches} · chains (≥3 steps): "
        f"{summ.chains}",
        "",
        "> **DRAFT_UNVERIFIED.** Chains were detected mechanically from the "
        "proven S/R logic (step k appears in step k+1's SET condition). "
        "Order is a topological suggestion — the engineer confirms the "
        "real sequence. Input material for the sequence FB; never code.",
        "",
    ]
    if not chains:
        L.append("_No step chains detected._")
    for ci, chain in enumerate(chains, 1):
        L.append(f"## Chain {ci} — {len(chain)} steps")
        L.append("")
        for step in chain:
            nl, coil = latches[step]
            title = names.get(step, "")
            L.append(f"### `{step}`{f' — {title}' if title else ''}  "
                     f"({nl.block}/N{nl.network}, proven on "
                     f"{nl.verified_vectors} vectors)")
            L.append(f"- SET: {render_expr(coil.set_cond, names)}")
            L.append(f"- RESET: {render_expr(coil.reset_cond, names)}")
        L.append("")

    reports = root / "REPORTS"
    reports.mkdir(exist_ok=True)
    path = reports / "SEQUENCE_DRAFT.md"
    path.write_text("\n".join(L), encoding="utf-8")
    summ.report_path = path
    return summ


def step_edges(nets: list[NetworkLogic]) -> dict[str, set[str]]:
    """Directed step edges {A: {B, …}} — A appears non-negated in B's SET."""
    latches, _ = build_chains(nets)
    edges: dict[str, set[str]] = {m: set() for m in latches}
    for m, (_nl, coil) in latches.items():
        for dep in _positive_vars(coil.set_cond):
            if dep in latches and dep != m:
                edges[dep].add(m)
    return edges


# ---------------------------------------------------------------------------
# RD03 flowchart cross-check — the AI's story vs the PROVEN chain
# ---------------------------------------------------------------------------

_RD03_SET_RE = re.compile(r"Set\s+([FM])\s?(\d{1,3})\.(\d)", re.I)


@dataclass
class FlowCheckResult:
    steps: int = 0                 # AI table rows with a step marker
    known_markers: int = 0         # markers that ARE proven S/R latches
    edges_checked: int = 0
    edges_confirmed: int = 0
    mismatches: list = field(default_factory=list)
    report_path: Path | None = None

    @property
    def summary(self) -> str:
        if not self.steps:
            return "RD03 cross-check: no step markers found in the table"
        return (f"RD03 cross-check: {self.known_markers}/{self.steps} step "
                f"markers proven, {self.edges_confirmed}/{self.edges_checked}"
                " transitions confirmed against the extracted chain")


def crosscheck_rd03(project_root: Path) -> FlowCheckResult:
    """Verify the AI-drafted RD03 step sequence against the deterministic,
    self-proven Schrittkette graph. The AI writes the STORY; the machine
    checks it — mismatches land in the report (and ledger), never silently.
    """
    import re as _re
    root = Path(project_root)
    res = FlowCheckResult()
    rd03 = next(iter(sorted((root / "metadata").glob("RD03*.md"))), None)
    if rd03 is None:
        return res
    nets = extract_project_logic(root)
    latches, _chains = build_chains(nets)
    edges = step_edges(nets)

    # parse the Step Sequence table: StepID -> (marker, next_step_id)
    rows: dict[str, tuple[str, str]] = {}
    for ln in rd03.read_text(encoding="utf-8",
                             errors="replace").splitlines():
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.split("|")[1:-1]]
        if len(cells) < 6 or not _re.match(r"^S\d{3}$", cells[0]):
            continue
        m = _RD03_SET_RE.search(cells[3])
        if not m:
            continue
        marker = f"M{int(m.group(2))}.{m.group(3)}"
        rows[cells[0]] = (marker, cells[5])

    res.steps = len(rows)
    for sid, (marker, nxt) in rows.items():
        if marker in latches:
            res.known_markers += 1
        else:
            res.mismatches.append(
                f"{sid}: step marker {marker} is NOT a proven S/R latch "
                "in the legacy code")
        if nxt in rows:
            res.edges_checked += 1
            nmarker = rows[nxt][0]
            if nmarker in edges.get(marker, set()):
                res.edges_confirmed += 1
            else:
                res.mismatches.append(
                    f"{sid}→{nxt}: transition {marker}→{nmarker} not found "
                    "in the extracted chain (order may be wrong)")

    reports = root / "REPORTS"
    reports.mkdir(exist_ok=True)
    path = reports / "FLOWCHART_CROSSCHECK.md"
    L = [
        "# FLOWCHART CROSS-CHECK — AI story vs proven chain",
        "",
        res.summary,
        "",
    ]
    if res.mismatches:
        L.append("## Mismatches (engineer review)")
        L += [f"- {m}" for m in res.mismatches]
    else:
        L.append("_Every step and transition matches the proven chain._")
    path.write_text("\n".join(L), encoding="utf-8")
    res.report_path = path
    return res


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: sequence_map.py <project_root>")
        raise SystemExit(2)
    s = generate_sequence_draft(Path(sys.argv[1]))
    print(f"latches={s.latches} chains={s.chains} "
          f"steps={s.steps_in_chains} -> {s.report_path}")
    c = crosscheck_rd03(Path(sys.argv[1]))
    print(c.summary)
    for m in c.mismatches[:10]:
        print("  !", m)
