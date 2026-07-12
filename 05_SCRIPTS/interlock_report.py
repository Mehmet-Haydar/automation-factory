#!/usr/bin/env python3
"""
interlock_report.py — device-grouped interlock DRAFT from extracted S5 logic.

Takes the proven per-network condition expressions (s5_logic_extract) and
the RD01 device attribution (Equipment column) and writes
REPORTS/INTERLOCK_DRAFT.md:

  * per device: every output coil's ASSIGN / SET / RESET condition, rendered
    with Zuordnungsliste symbol names, plus the first-level Merker
    definitions those conditions depend on;
  * every expression carries its proof line ("verified on N random
    vectors against the original network");
  * everything the extractor refused is listed verbatim under UNPARSED —
    the engineer sees exactly what the machine did NOT understand.

DRAFT contract: this report is comment/review material. Nothing here is
injected into executable code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from s5_logic_extract import (  # type: ignore
    NetworkLogic, extract_project_logic, render_expr, _vars,
)


@dataclass
class InterlockSummary:
    networks: int = 0
    parsed: int = 0
    unparsed: int = 0
    device_coils: int = 0
    report_path: Path | None = None
    devices: dict = field(default_factory=dict)   # device -> [coil operands]


def _rd01_equipment_by_address(project_root: Path) -> dict[str, str]:
    """{canonical operand 'Q28.4': 'Y2'} from the RD01 Equipment column."""
    import re
    from iec_tag_generator import parse_rd01_signals  # type: ignore
    out: dict[str, str] = {}
    for sig in parse_rd01_signals(Path(project_root)):
        eq = (sig.get("equipment") or "").strip()
        if not eq:
            continue
        m = re.match(r"^%?([IQ])\s?(\d{1,3})\.(\d)$",
                     (sig.get("address") or "").strip())
        if m:
            out[f"{m.group(1)}{int(m.group(2))}.{m.group(3)}"] = eq
    return out


def _merker_defs(nets: list[NetworkLogic]) -> dict[str, NetworkLogic]:
    """First writer wins: {\"M8.0\": network that assigns/sets it}."""
    defs: dict[str, NetworkLogic] = {}
    for nl in nets:
        if not nl.parsed:
            continue
        for op in nl.coils:
            if op.startswith("M"):
                defs.setdefault(op, nl)
    return defs


def _deps(nl: NetworkLogic) -> set[str]:
    out: set[str] = set()
    for c in nl.coils.values():
        for e in (c.assign, c.set_cond, c.reset_cond):
            if e is not None:
                out |= {v.operand for v in _vars(e)}
    return out


def generate_interlock_draft(project_root: Path) -> InterlockSummary:
    root = Path(project_root)
    nets = extract_project_logic(root)
    summ = InterlockSummary(networks=len(nets))
    if not nets:
        return summ
    summ.parsed = sum(1 for n in nets if n.parsed)
    summ.unparsed = summ.networks - summ.parsed

    from legacy_enrich import load_symbols  # type: ignore
    names = load_symbols(root / "_raw" / "legacy_code")
    equip = _rd01_equipment_by_address(root)
    mdefs = _merker_defs(nets)

    # device -> [(network, coil operand, CoilLogic)]
    by_dev: dict[str, list] = {}
    for nl in nets:
        if not nl.parsed:
            continue
        for op, coil in nl.coils.items():
            if op.startswith("Q") and op in equip:
                by_dev.setdefault(equip[op], []).append((nl, op, coil))

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L: list[str] = [
        "# INTERLOCK DRAFT — extracted from legacy S5 logic (deterministic)",
        "",
        f"Generated: {now}",
        f"Networks: {summ.networks} · parsed & proven: {summ.parsed} · "
        f"refused (honest): {summ.unparsed}",
        "",
        "> **DRAFT_UNVERIFIED.** Every condition below was extracted "
        "mechanically from the original AWL and verified against it on "
        "random input vectors — but an engineer MUST confirm intent "
        "before use. Nothing here was written into executable code.",
        "",
    ]

    def _fmt_coil(nl: NetworkLogic, op: str, coil) -> list[str]:
        rows = []
        title = names.get(op, "")
        rows.append(f"#### `{op}`{f' — {title}' if title else ''}  "
                    f"({nl.block} / Netzwerk {nl.network}, "
                    f"proven on {nl.verified_vectors} vectors)")
        if coil.assign is not None:
            rows.append(f"- **=** {render_expr(coil.assign, names)}")
        if coil.set_cond is not None:
            rows.append(f"- **SET** {render_expr(coil.set_cond, names)}")
        if coil.reset_cond is not None:
            rows.append(f"- **RESET** {render_expr(coil.reset_cond, names)}")
        for t in nl.timers.values():
            rows.append(f"- timer `{t.timer}` {t.kind} {t.literal}: "
                        f"start = {render_expr(t.start, names)}")
        return rows

    if by_dev:
        L.append("## Per-device output conditions")
        L.append("")
        for dev in sorted(by_dev):
            L.append(f"### Device {dev}")
            dep_flags: set[str] = set()
            for nl, op, coil in by_dev[dev]:
                L.extend(_fmt_coil(nl, op, coil))
                dep_flags |= {d for d in _deps(nl) if d.startswith("M")}
                summ.device_coils += 1
            summ.devices[dev] = [op for _n, op, _c in by_dev[dev]]
            used = sorted(d for d in dep_flags if d in mdefs)
            if used:
                L.append("- depends on Merker logic:")
                for mop in used[:8]:
                    mnl = mdefs[mop]
                    mc = mnl.coils[mop]
                    # a trivial self-assign ("A M8.0 / = M8.0" refresh) hides
                    # the real latch — prefer the SET condition then
                    from s5_logic_extract import Var  # type: ignore
                    cond, label = mc.assign, "="
                    if cond is None or (isinstance(cond, Var)
                                        and cond.operand == mop):
                        if mc.set_cond is not None:
                            cond, label = mc.set_cond, "SET:"
                    L.append(f"  - `{mop}`"
                             f"{f' «{names[mop]}»' if mop in names else ''}"
                             f" {label} {render_expr(cond, names)[:160]} "
                             f"({mnl.block}/N{mnl.network})")
            L.append("")

    # Q coils with no device attribution — never silently dropped
    orphan = [(nl, op, c) for nl in nets if nl.parsed
              for op, c in nl.coils.items()
              if op.startswith("Q") and op not in equip]
    if orphan:
        L.append("## Outputs without a device (RD01 Equipment empty)")
        L.append("")
        for nl, op, coil in orphan:
            L.extend(_fmt_coil(nl, op, coil))
        L.append("")

    bad = [n for n in nets if not n.parsed]
    if bad:
        L.append("## UNPARSED — the machine refused these (engineer review)")
        L.append("")
        for nl in bad:
            L.append(f"### {nl.block} / Netzwerk {nl.network} — {nl.reason}")
            L.append("```")
            L.extend(ln.rstrip() for ln in nl.raw[:20])
            if len(nl.raw) > 20:
                L.append(f"… (+{len(nl.raw) - 20} lines)")
            L.append("```")
        L.append("")

    reports = root / "REPORTS"
    reports.mkdir(exist_ok=True)
    path = reports / "INTERLOCK_DRAFT.md"
    path.write_text("\n".join(L), encoding="utf-8")
    summ.report_path = path
    return summ


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: interlock_report.py <project_root>")
        raise SystemExit(2)
    s = generate_interlock_draft(Path(sys.argv[1]))
    print(f"networks={s.networks} parsed={s.parsed} unparsed={s.unparsed} "
          f"device_coils={s.device_coils} -> {s.report_path}")
