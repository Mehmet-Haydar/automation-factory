#!/usr/bin/env python3
"""
script_state_validator.py
=========================
Checks the consistency of the PROJECT_STATE.json file.

CHECKS:
  1. Required fields present (project_id, current_gate, gates_status, rd_status)
  2. 7-Gate ordering is sound (Gate N+1 can only start when Gate N is completed)
  3. current_gate actually matches the first open gate
  4. rd_status completion_pct fields are within [0..100]
  5. If RD05 (Safety) is DRAFT_UNVERIFIED, a review_pending field exists
  6. activity_log field contains consecutive repeats (noise warning)

USAGE:
    python script_state_validator.py [PROJECT_FOLDER]

    If PROJECT_FOLDER is omitted, the current working dir is used.

OUTPUT:
    Exit code 0 = consistent, 1 = has issues.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


GATE_ORDER = [
    "gate1_kesif",
    "gate2_cikartim",
    "gate3_human_review",
    "gate4_validation",
    "gate5_kod_uretimi",
    "gate6_simulasyon",
    "gate7_fat_sat",
]

VALID_GATE_STATUSES = {
    "pending", "in_progress", "in_progress_partial", "completed", "blocked", "skipped"
}

REQUIRED_TOP_FIELDS = [
    "project_id", "project_name", "project_type", "current_gate",
    "gates_status", "rd_status",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_path", nargs="?", default=".",
                   help="Project folder (containing PROJECT_STATE.json). Default: cwd")
    p.add_argument("--state-file", default="PROJECT_STATE.json",
                   help="State file name (default: PROJECT_STATE.json)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    return p.parse_args()


def validate_state(state: dict) -> list[tuple[str, str]]:
    """Validate the state dict. Returns a list of (severity, message).

    severity: 'ERROR' | 'WARN'
    """
    issues: list[tuple[str, str]] = []

    # 1. Required fields
    for field in REQUIRED_TOP_FIELDS:
        if field not in state:
            issues.append(("ERROR", f"Missing field: {field}"))

    gates = state.get("gates_status", {})
    if not isinstance(gates, dict):
        issues.append(("ERROR", "gates_status must be a dict"))
        gates = {}

    # 2. Gate ordering
    # — after a non-completed gate, no gate may be
    #   in_progress/in_progress_partial.
    completed_until = -1  # index of last completed gate
    for i, g in enumerate(GATE_ORDER):
        s = gates.get(g)
        if s is None:
            issues.append(("WARN", f"{g}: not in gates_status"))
            continue
        if s not in VALID_GATE_STATUSES:
            issues.append(("ERROR", f"{g}: invalid status '{s}'"))
            continue
        if s == "completed":
            if completed_until == i - 1:
                completed_until = i
            else:
                issues.append((
                    "ERROR",
                    f"{g} is 'completed' but some earlier gates are not "
                    f"(last completed: index {completed_until})",
                ))
        elif s in ("in_progress", "in_progress_partial"):
            # All earlier gates must be completed
            for j in range(i):
                prev = gates.get(GATE_ORDER[j])
                if prev != "completed":
                    issues.append((
                        "ERROR",
                        f"{g}='{s}' but earlier {GATE_ORDER[j]}='{prev}' "
                        f"(7-Gate sequential — {GATE_ORDER[j]} must finish first)",
                    ))
                    break

    # 3. current_gate
    cg = state.get("current_gate")
    if isinstance(cg, int):
        if cg < 1 or cg > 7:
            issues.append(("ERROR", f"current_gate out of range: {cg} (must be 1-7)"))
        else:
            # current_gate must match the first non-completed gate
            expected = next(
                (i + 1 for i, g in enumerate(GATE_ORDER) if gates.get(g) != "completed"),
                7,
            )
            if cg != expected:
                issues.append((
                    "WARN",
                    f"current_gate={cg} but gates_status expects={expected}",
                ))

    # 4. rd_status completion_pct
    rd_status = state.get("rd_status", {})
    if not isinstance(rd_status, dict):
        issues.append(("ERROR", "rd_status must be a dict"))
        rd_status = {}
    for rd, info in rd_status.items():
        if not isinstance(info, dict):
            issues.append(("ERROR", f"{rd}: must be a dict"))
            continue
        pct = info.get("completion_pct")
        if pct is not None and not (isinstance(pct, (int, float)) and 0 <= pct <= 100):
            issues.append(("ERROR", f"{rd}.completion_pct invalid: {pct!r}"))
        # 5. RD05 safety
        if rd == "RD05_Safety":
            if info.get("status") == "DRAFT_UNVERIFIED" and not info.get("review_pending"):
                issues.append((
                    "WARN",
                    "RD05_Safety is DRAFT_UNVERIFIED but review_pending field is missing",
                ))

    # 6. activity_log noise
    log = state.get("activity_log", [])
    if isinstance(log, list) and len(log) >= 3:
        msgs = [entry.get("msg", "") if isinstance(entry, dict) else "" for entry in log]
        # Longest run of consecutive identical messages
        run = 1
        max_run = 1
        for a, b in zip(msgs, msgs[1:]):
            if a == b and a:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 1
        if max_run >= 5:
            issues.append((
                "WARN",
                f"{max_run} consecutive identical messages in activity_log — log noise",
            ))

    return issues


def main() -> int:
    args = parse_args()
    proj = Path(args.project_path).resolve()
    state_file = proj / args.state_file

    print(f"State Validator")
    print(f"  Project: {proj}")
    print(f"  File   : {state_file}")
    print()

    if not state_file.exists():
        print(f"ERROR: {state_file} not found")
        return 1

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: could not parse PROJECT_STATE.json: {e}")
        return 1

    issues = validate_state(state)

    if args.format == "json":
        print(json.dumps(
            [{"severity": s, "message": m} for s, m in issues],
            indent=2, ensure_ascii=False,
        ))
        return 0 if not any(s == "ERROR" for s, _ in issues) else 1

    errors = [m for s, m in issues if s == "ERROR"]
    warns = [m for s, m in issues if s == "WARN"]

    if errors:
        print(f"ERROR ({len(errors)}):")
        for m in errors:
            print(f"  - {m}")
        print()
    if warns:
        print(f"WARNING ({len(warns)}):")
        for m in warns:
            print(f"  - {m}")
        print()

    if not issues:
        print("PROJECT_STATE.json is consistent.")
        return 0
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
