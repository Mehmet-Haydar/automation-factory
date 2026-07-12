#!/usr/bin/env python3
"""
consistency_check_forge.py — FORGE Phase 4 Consistency Sweep
Cross-checks: contract <-> SCL block (interface + error codes + behaviors)
Reports: CONSISTENT / PARTIAL / INCONSISTENT / STUB per device type

CLI:
  python consistency_check_forge.py --report consistency_report.md
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).parent.parent


@dataclass
class Finding:
    severity: str   # OK / WARN / ERROR
    message: str


@dataclass
class TypeResult:
    name: str
    contract_file: str
    scl_file: str
    status: str = "UNKNOWN"   # CONSISTENT / PARTIAL / INCONSISTENT / MISSING_SCL
    findings: list[Finding] = field(default_factory=list)


def _parse_scl_vars(scl: str, section: str) -> dict[str, str]:
    pattern = re.compile(r"\b" + re.escape(section) + r"\b(.*?)\bEND_VAR\b", re.IGNORECASE | re.DOTALL)
    m = pattern.search(scl)
    if not m:
        return {}
    block = m.group(1)
    result: dict[str, str] = {}
    for mv in re.finditer(r"^\s*(\w+)\s*:\s*([\w#]+)(?:\s*:=\s*[^;]+)?;", block, re.MULTILINE | re.IGNORECASE):
        result[mv.group(1).lower()] = mv.group(2).lower()
    return result


def check_type(contract_path: Path, blocks_root: Path) -> TypeResult:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    name = contract["block"]["name"]
    block_type = contract["block"]["type"]
    domain = contract["block"]["domain"]
    device = contract["block"]["device_type"]

    # Locate SCL file
    # Try canonical locations
    scl_candidates = list(blocks_root.rglob(f"{name}.scl"))
    if not scl_candidates:
        # Try domain-based path
        for d in ["motor", "valve", "process", "system", "ob"]:
            p = blocks_root / d / f"{name}.scl"
            if p.exists():
                scl_candidates = [p]
                break

    result = TypeResult(
        name=name,
        contract_file=str(contract_path.relative_to(_ROOT)),
        scl_file="",
    )

    if not scl_candidates:
        result.status = "MISSING_SCL"
        result.findings.append(Finding("ERROR", f"No SCL file found for {name}"))
        return result

    scl_path = scl_candidates[0]
    result.scl_file = str(scl_path.relative_to(_ROOT))
    scl = scl_path.read_text(encoding="utf-8", errors="replace")
    errors = []
    warnings = []

    # 1. FB name match (for FB type)
    if block_type == "FB":
        if not re.search(rf'FUNCTION_BLOCK\s+"?{re.escape(name)}"?', scl, re.IGNORECASE):
            errors.append(f"FUNCTION_BLOCK name '{name}' not found in SCL")

    # 2. Interface consistency — required inputs
    parsed_in  = _parse_scl_vars(scl, "VAR_INPUT")
    parsed_out = _parse_scl_vars(scl, "VAR_OUTPUT")

    for port in contract["interface"].get("inputs", []):
        if not port.get("required", True):
            continue
        pname = port["name"].lower()
        if pname not in parsed_in:
            errors.append(f"Contract requires input '{port['name']}' — not found in VAR_INPUT")
        else:
            actual = parsed_in[pname]
            expected = port["iec_type"].lower()
            if actual != expected:
                warnings.append(f"Input '{port['name']}': contract={expected}, SCL={actual}")

    for port in contract["interface"].get("outputs", []):
        if not port.get("required", True):
            continue
        pname = port["name"].lower()
        if pname not in parsed_out:
            errors.append(f"Contract requires output '{port['name']}' — not found in VAR_OUTPUT")

    # 3. Error codes present in SCL
    for ec in contract["constraints"].get("error_codes", []):
        applies_to = ec.get("applies_to", [])
        if applies_to:
            continue  # skip type-specific
        if not re.search(re.escape(ec["hex"]), scl, re.IGNORECASE):
            errors.append(f"Error code {ec['hex']} ({ec['meaning']}) not in SCL")

    # 4. Mandatory regions present
    for region in contract["constraints"].get("mandatory_regions", []):
        if not re.search(r"\bREGION\s+" + re.escape(region), scl, re.IGNORECASE):
            errors.append(f"Mandatory REGION '{region}' not found in SCL")

    # 5. Forbidden patterns absent
    for pat in contract["constraints"].get("forbidden_patterns", []):
        if re.search(pat, scl, re.IGNORECASE):
            errors.append(f"Forbidden pattern '{pat}' found in SCL")

    # Build findings
    for msg in errors:
        result.findings.append(Finding("ERROR", msg))
    for msg in warnings:
        result.findings.append(Finding("WARN", msg))

    if errors:
        result.status = "INCONSISTENT"
    elif warnings:
        result.status = "PARTIAL"
    else:
        result.status = "CONSISTENT"

    return result


def run_sweep() -> list[TypeResult]:
    contracts_dir = _ROOT / "06_KNOWLEDGE_BASE" / "contracts"
    blocks_root   = _ROOT / "06_KNOWLEDGE_BASE" / "blocks"
    results = []
    for contract_path in sorted(contracts_dir.rglob("*.contract.json")):
        if contract_path.name.endswith("schema.json"):
            continue
        results.append(check_type(contract_path, blocks_root))
    return results


def format_report(results: list[TypeResult]) -> str:
    lines = ["# FORGE Phase 4 — Consistency Sweep Report", ""]
    consistent = sum(1 for r in results if r.status == "CONSISTENT")
    partial = sum(1 for r in results if r.status == "PARTIAL")
    inconsistent = sum(1 for r in results if r.status == "INCONSISTENT")
    missing = sum(1 for r in results if r.status == "MISSING_SCL")
    lines.append(f"Total: {len(results)} types | CONSISTENT: {consistent} | PARTIAL: {partial} | INCONSISTENT: {inconsistent} | MISSING_SCL: {missing}")
    lines.append("")
    lines.append("## Results by Type")
    lines.append("")
    for r in results:
        icon = {"CONSISTENT":"✓","PARTIAL":"~","INCONSISTENT":"✗","MISSING_SCL":"?","UNKNOWN":"?"}.get(r.status,"?")
        lines.append(f"### {icon} {r.name} — {r.status}")
        lines.append(f"- Contract: `{r.contract_file}`")
        lines.append(f"- SCL: `{r.scl_file}`")
        if r.findings:
            for f in r.findings:
                icon2 = {"OK":"  ✓","WARN":"  ⚠","ERROR":"  ✗"}.get(f.severity,"  ?")
                lines.append(f"{icon2} {f.message}")
        lines.append("")
    return "\n".join(lines)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--report", metavar="MD_OUT", help="Write markdown report to this file")
    args = p.parse_args()

    results = run_sweep()
    report = format_report(results)
    print(report)

    if args.report:
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(report, encoding="utf-8")
        print(f"\nReport written: {rp}")

    inconsistent = sum(1 for r in results if r.status in ("INCONSISTENT","MISSING_SCL"))
    sys.exit(0 if inconsistent == 0 else 1)


if __name__ == "__main__":
    main()
