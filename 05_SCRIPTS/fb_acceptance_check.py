#!/usr/bin/env python3
"""
fb_acceptance_check.py — FB Acceptance Gate  (FORGE Phase 1-B)

Runs the multi-step acceptance gate for a generated SCL block against a
.contract.json file derived from the single source of truth.

Gate steps (order matters):
  G-01  structural         scl_validator keyword/paren balance
  G-02  contract_interface required ports present with correct IEC types
  G-03  contract_behavior  MUST/SHOULD regex patterns found in SCL body
  G-04  contract_error_codes  hex error codes referenced in SCL
  G-05  forbidden_pattern  disallowed calls NOT present
  G-06  plcrex             optional IEC 61131-3 parse (skipped if tool absent)

Result labels (honest about what was verified):
  AUTO_VERIFIED_structural         G-01..G-05 passed, PLCreX unavailable
  AUTO_VERIFIED_structural_plcrex  G-01..G-06 passed
  PENDING_TIA_VERIFY               always appended (Siemens compile not tested)

CLI:
  python fb_acceptance_check.py <file.scl> --contract <file.contract.json>
  python fb_acceptance_check.py <file.scl> --contract <file.contract.json> \\
      --out gate_result.json [--verbose]

Exit codes:
  0  PASS (all MUST checks pass; SHOULD warnings allowed)
  1  FAIL (one or more MUST checks failed)
  2  TOOL ERROR (file not found, JSON parse error, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from scl_validator import validate_scl  # structural checker


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_id: str
    check_type: str
    description: str
    status: str                   # PASS | FAIL | WARN | SKIP
    issues: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    scl_file: str
    contract_file: str
    timestamp: str
    block_name: str
    overall: str                  # PASS | FAIL
    label: str
    checks: list[CheckResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scl_file":      self.scl_file,
            "contract_file": self.contract_file,
            "timestamp":     self.timestamp,
            "block_name":    self.block_name,
            "overall":       self.overall,
            "label":         self.label,
            "checks":        [
                {
                    "id":          c.check_id,
                    "type":        c.check_type,
                    "status":      c.status,
                    "description": c.description,
                    "issues":      c.issues,
                }
                for c in self.checks
            ],
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# SCL interface parser (regex-based, good enough for gate purposes)
# ---------------------------------------------------------------------------

# Matches "varName : SomeType" or "varName : SomeType := default" inside a VAR block
_VAR_DECL_RE = re.compile(
    r"^\s*(\w+)\s*:\s*([\w#]+)(?:\s*:=\s*[^;]+)?;",
    re.MULTILINE | re.IGNORECASE,
)

# Matches REGION <name> (case-insensitive)
_REGION_RE = re.compile(r"\bREGION\s+(\S+)", re.IGNORECASE)


def _extract_var_block(scl: str, section: str) -> str:
    """Return the text inside the first matching VAR_xxx ... END_VAR block."""
    pattern = re.compile(
        r"\b" + re.escape(section) + r"\b(.*?)\bEND_VAR\b",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(scl)
    return m.group(1) if m else ""


def _parse_vars(scl: str, section: str) -> dict[str, str]:
    """Return {name_lower: iec_type_lower} for all declarations in a VAR section."""
    block = _extract_var_block(scl, section)
    result: dict[str, str] = {}
    for m in _VAR_DECL_RE.finditer(block):
        name, typ = m.group(1), m.group(2)
        result[name.lower()] = typ.lower()
    return result


def _parse_interface(scl: str) -> dict[str, dict[str, str]]:
    return {
        "inputs":  _parse_vars(scl, "VAR_INPUT"),
        "outputs": _parse_vars(scl, "VAR_OUTPUT"),
        "in_out":  _parse_vars(scl, "VAR_IN_OUT"),
        "static":  _parse_vars(scl, "VAR"),
    }


def _parse_regions(scl: str) -> set[str]:
    return {m.group(1).upper() for m in _REGION_RE.finditer(scl)}


# ---------------------------------------------------------------------------
# IEC type alias normalization (Bool / BOOL / bool -> bool)
# ---------------------------------------------------------------------------

def _norm_type(t: str) -> str:
    return t.strip().lower()


# ---------------------------------------------------------------------------
# Individual gate checks
# ---------------------------------------------------------------------------

def check_structural(scl: str) -> CheckResult:
    cr = CheckResult(
        check_id="G-01", check_type="structural",
        description="scl_validator: keyword/paren balance",
        status="PASS",
    )
    result = validate_scl(scl)
    errors = [i.message for i in result.issues if i.severity == "error"]
    warnings = [i.message for i in result.issues if i.severity == "warning"]
    if errors:
        cr.status = "FAIL"
        cr.issues = errors
    elif warnings:
        cr.status = "WARN"
        cr.issues = warnings
    # info-level issues do not affect gate status
    return cr


def check_interface(scl: str, contract: dict) -> CheckResult:
    cr = CheckResult(
        check_id="G-02", check_type="contract_interface",
        description="Required ports declared with correct IEC types",
        status="PASS",
    )
    parsed = _parse_interface(scl)
    section_map = {
        "inputs":  "VAR_INPUT",
        "outputs": "VAR_OUTPUT",
        "in_out":  "VAR_IN_OUT",
    }
    for section_key, scl_section in section_map.items():
        for port in contract["interface"].get(section_key, []):
            if not port.get("required", True):
                continue
            name_lower = port["name"].lower()
            expected_type = _norm_type(port["iec_type"])
            if name_lower not in parsed[section_key]:
                cr.issues.append(
                    f"[{scl_section}] Missing required port: {port['name']} ({port['iec_type']})"
                )
            else:
                actual_type = parsed[section_key][name_lower]
                if actual_type != expected_type:
                    cr.issues.append(
                        f"[{scl_section}] {port['name']}: expected type {expected_type}, "
                        f"found {actual_type}"
                    )

    # Check mandatory static vars
    static_required = contract["interface"].get("static_vars", [])
    for sv in static_required:
        if sv["name"].lower() not in parsed["static"]:
            cr.issues.append(
                f"[VAR] Missing mandatory static var: {sv['name']} ({sv['iec_type']})"
            )

    if cr.issues:
        cr.status = "FAIL"
    return cr


def check_behaviors(scl: str, contract: dict) -> CheckResult:
    cr = CheckResult(
        check_id="G-03", check_type="contract_behavior",
        description="MUST behavioral patterns present in SCL body",
        status="PASS",
    )
    regions_found = _parse_regions(scl)
    mandatory_regions = [r.upper() for r in contract["constraints"]["mandatory_regions"]]

    for region in mandatory_regions:
        if region not in regions_found:
            cr.issues.append(f"Missing mandatory REGION: {region}")

    for behavior in contract["constraints"]["mandatory_behaviors"]:
        pattern = behavior["check_pattern"]
        severity = behavior.get("severity", "MUST")
        try:
            found = bool(re.search(pattern, scl, re.IGNORECASE | re.MULTILINE))
        except re.error as e:
            cr.issues.append(f"Regex error in {behavior['id']}: {e}")
            found = False

        if not found:
            msg = f"{behavior['id']}: {behavior['description']} — pattern not found: {pattern!r}"
            if severity == "MUST":
                cr.issues.append(msg)
            else:
                cr.issues.append(f"[SHOULD] {msg}")

    must_fails = [i for i in cr.issues if not i.startswith("[SHOULD]")]
    if must_fails:
        cr.status = "FAIL"
    elif cr.issues:
        cr.status = "WARN"
    return cr


def check_error_codes(scl: str, contract: dict) -> CheckResult:
    cr = CheckResult(
        check_id="G-04", check_type="contract_error_codes",
        description="Required error codes referenced in SCL",
        status="PASS",
    )
    for ec in contract["constraints"].get("error_codes", []):
        applies_to = ec.get("applies_to", [])
        if applies_to:
            continue  # skip type-specific codes in the base gate
        hex_val = ec["hex"].upper()
        # Normalize: 16#0001 -> also check 16#001, 1 etc.
        # Most reliable: search for the exact hex literal as written
        pattern = re.escape(hex_val)
        if not re.search(pattern, scl, re.IGNORECASE):
            cr.issues.append(
                f"Error code {hex_val} ({ec['meaning']}) not found in SCL"
            )
    if cr.issues:
        cr.status = "FAIL"
    return cr


def check_forbidden(scl: str, contract: dict) -> CheckResult:
    cr = CheckResult(
        check_id="G-05", check_type="forbidden_pattern",
        description="Forbidden patterns must NOT appear in SCL",
        status="PASS",
    )
    for pattern in contract["constraints"].get("forbidden_patterns", []):
        try:
            m = re.search(pattern, scl, re.IGNORECASE)
        except re.error as e:
            cr.issues.append(f"Regex error in forbidden pattern {pattern!r}: {e}")
            continue
        if m:
            cr.issues.append(
                f"Forbidden pattern found: {pattern!r} at position {m.start()} "
                f"(matched: {m.group()!r})"
            )
    if cr.issues:
        cr.status = "FAIL"
    return cr


def check_plcrex(scl_path: Path, contract: dict) -> CheckResult:
    cr = CheckResult(
        check_id="G-06", check_type="plcrex",
        description="PLCreX IEC 61131-3 structural parse (optional)",
        status="SKIP",
    )
    plcrex = shutil.which("plcrex") or shutil.which("PLCreX")
    if not plcrex:
        cr.issues.append("PLCreX not found on PATH — check skipped gracefully")
        return cr

    extra_flags = contract.get("gate", {}).get("plcrex_flags", [])
    cmd = [plcrex, "check", str(scl_path)] + extra_flags
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                              encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            cr.status = "PASS"
        else:
            cr.status = "FAIL"
            cr.issues = (proc.stderr or proc.stdout or "no output").splitlines()[:20]
    except subprocess.TimeoutExpired:
        cr.status = "WARN"
        cr.issues.append("PLCreX timed out after 30s")
    except Exception as e:
        cr.status = "WARN"
        cr.issues.append(f"PLCreX execution error: {e}")
    return cr


# ---------------------------------------------------------------------------
# Result label builder
# ---------------------------------------------------------------------------

def _build_label(checks: list[CheckResult]) -> str:
    plcrex_pass = any(c.check_id == "G-06" and c.status == "PASS" for c in checks)
    if plcrex_pass:
        base = "AUTO_VERIFIED_structural_plcrex"
    else:
        base = "AUTO_VERIFIED_structural"
    return f"{base} | PENDING_TIA_VERIFY"


# ---------------------------------------------------------------------------
# Block name extraction
# ---------------------------------------------------------------------------

def _extract_block_name(scl: str) -> str:
    # Strip comment lines before matching to avoid false positives from
    # phrases like "This function block is NOT..." in SAFETY NOTICE headers.
    non_comment = "\n".join(
        line for line in scl.splitlines()
        if not line.lstrip().startswith("//")
    )
    m = re.search(
        r"\b(?:FUNCTION_BLOCK|FUNCTION|ORGANIZATION_BLOCK)\s+\"?(\w+)\"?",
        non_comment, re.IGNORECASE,
    )
    return m.group(1) if m else "<unknown>"


# ---------------------------------------------------------------------------
# Main gate runner
# ---------------------------------------------------------------------------

def run_gate(scl_path: Path, contract_path: Path) -> GateResult:
    scl = scl_path.read_text(encoding="utf-8", errors="replace")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    block_name = _extract_block_name(scl)
    checks: list[CheckResult] = []

    checks.append(check_structural(scl))
    checks.append(check_interface(scl, contract))
    checks.append(check_behaviors(scl, contract))
    checks.append(check_error_codes(scl, contract))
    checks.append(check_forbidden(scl, contract))
    checks.append(check_plcrex(scl_path, contract))

    any_must_fail = any(
        c.status == "FAIL"
        for c in checks
        if c.check_id != "G-06"   # PLCreX is optional
    )
    overall = "FAIL" if any_must_fail else "PASS"
    label = _build_label(checks) if overall == "PASS" else "GATE_FAILED"

    notes = [
        "HONESTY NOTE: AUTO_VERIFIED (structural/tool-level) does NOT mean the block "
        "compiles in TIA Portal or behaves correctly on PLCSIM. "
        "Siemens-specific verification remains with the human engineer.",
        "PENDING_TIA_VERIFY: this label is always appended until a human engineer "
        "performs TIA Portal compile + PLCSIM run and signs off.",
    ]

    return GateResult(
        scl_file=str(scl_path),
        contract_file=str(contract_path),
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        block_name=block_name,
        overall=overall,
        label=label,
        checks=checks,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

STATUS_ICON = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}

def format_result(gr: GateResult, verbose: bool = False) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"FB ACCEPTANCE GATE — {gr.timestamp}")
    lines.append(f"Block    : {gr.block_name}")
    lines.append(f"SCL      : {gr.scl_file}")
    lines.append(f"Contract : {gr.contract_file}")
    lines.append(f"Result   : {STATUS_ICON.get(gr.overall, gr.overall)}  {gr.label}")
    lines.append("-" * 70)

    for c in gr.checks:
        icon = STATUS_ICON.get(c.status, c.status)
        lines.append(f"  {icon}  {c.check_id}  {c.description}")
        if c.issues and (verbose or c.status in ("FAIL", "WARN")):
            for issue in c.issues:
                lines.append(f"          - {issue}")

    lines.append("-" * 70)
    for note in gr.notes:
        lines.append(f"  NOTE: {note}")
    lines.append("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="FB Acceptance Gate — validates SCL against a .contract.json"
    )
    p.add_argument("scl_file", help=".scl file to check")
    p.add_argument("--contract", required=True, metavar="CONTRACT",
                   help="Path to .contract.json")
    p.add_argument("--out", metavar="JSON_OUT",
                   help="Write gate result JSON to this file")
    p.add_argument("--verbose", action="store_true",
                   help="Show all check issues, including PASSed checks")
    args = p.parse_args()

    scl_path = Path(args.scl_file)
    contract_path = Path(args.contract)

    if not scl_path.exists():
        print(f"[ERROR] SCL file not found: {scl_path}", file=sys.stderr)
        sys.exit(2)
    if not contract_path.exists():
        print(f"[ERROR] Contract file not found: {contract_path}", file=sys.stderr)
        sys.exit(2)

    try:
        result = run_gate(scl_path, contract_path)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse contract JSON: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)

    print(format_result(result, verbose=args.verbose))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nGate result saved: {out_path}")

    sys.exit(0 if result.overall == "PASS" else 1)


if __name__ == "__main__":
    main()
