#!/usr/bin/env python3
"""
accept_gate.py — Acceptance Gate CLI (charter Section 4 interface)

Thin wrapper around fb_acceptance_check.run_gate() that presents the
canonical charter JSON output format and honest PENDING_TIA_VERIFY labels.

Charter interface (Section 4):
  input : candidate_scl_path, contract_path
  output: JSON {
    result:        "PASS" | "FAIL",
    missing:       [...],         # missing required pins / error codes
    forbidden_hits:[...],         # forbidden pattern matches found
    compile:       "PENDING_TIA_VERIFY",
    sim:           "PENDING_TIA_VERIFY",
    label:         str,
    timestamp:     ISO-8601
  }
  exit 0 = tool-level PASS
  exit 1 = FAIL (one or more MUST checks failed)
  exit 2 = error (file not found, parse error, etc.)

Honesty constraint (charter Section 2):
  compile and sim results are ALWAYS "PENDING_TIA_VERIFY" when TIA Portal /
  PLCSIM Advanced hardware is not available. NEVER print AUTO_VERIFIED as if
  TIA verified it.

CLI:
  python accept_gate.py <scl_file> --contract <contract.json> [--out result.json] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from fb_acceptance_check import run_gate, format_result


def _charter_json(gate_result) -> dict:
    """Convert GateResult to charter Section 4 JSON shape."""
    missing: list[str] = []
    forbidden_hits: list[str] = []

    for check in gate_result.checks:
        if check.check_id == "G-02" and check.status == "FAIL":
            missing.extend(check.issues)
        elif check.check_id == "G-04" and check.status == "FAIL":
            missing.extend(check.issues)
        elif check.check_id == "G-05" and check.status == "FAIL":
            forbidden_hits.extend(check.issues)
        elif check.check_id == "G-03" and check.status == "FAIL":
            missing.extend(check.issues)

    return {
        "result":         gate_result.overall,
        "block_name":     gate_result.block_name,
        "scl_file":       gate_result.scl_file,
        "contract_file":  gate_result.contract_file,
        "timestamp":      gate_result.timestamp,
        "missing":        missing,
        "forbidden_hits": forbidden_hits,
        "compile":        "PENDING_TIA_VERIFY",
        "sim":            "PENDING_TIA_VERIFY",
        "label":          gate_result.label,
        "checks":         [
            {"id": c.check_id, "type": c.check_type, "status": c.status,
             "issues": c.issues}
            for c in gate_result.checks
        ],
        "notes": gate_result.notes,
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Acceptance Gate — validate SCL candidate against a .contract.json"
    )
    p.add_argument("scl_file", help="Candidate .scl file to check")
    p.add_argument("--contract", required=True, metavar="CONTRACT",
                   help="Path to .contract.json (single source of truth)")
    p.add_argument("--out", metavar="JSON_OUT",
                   help="Write charter JSON result to this file")
    p.add_argument("--verbose", action="store_true",
                   help="Show all check details, including PASSed checks")
    args = p.parse_args()

    scl_path      = Path(args.scl_file)
    contract_path = Path(args.contract)

    if not scl_path.exists():
        print(f"[ERROR] SCL file not found: {scl_path}", file=sys.stderr)
        sys.exit(2)
    if not contract_path.exists():
        print(f"[ERROR] Contract file not found: {contract_path}", file=sys.stderr)
        sys.exit(2)

    try:
        gate_result = run_gate(scl_path, contract_path)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse contract JSON: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)

    print(format_result(gate_result, verbose=args.verbose))

    charter_out = _charter_json(gate_result)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(charter_out, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nCharter gate result saved: {out_path}")
    else:
        print("\n--- Charter JSON ---")
        print(json.dumps(charter_out, indent=2, ensure_ascii=False))

    sys.exit(0 if gate_result.overall == "PASS" else 1)


if __name__ == "__main__":
    main()
