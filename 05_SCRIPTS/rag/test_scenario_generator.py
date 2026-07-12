#!/usr/bin/env python3
"""
test_scenario_generator.py — Gate 6 (Simulation) test scenario generator.

Combines program_assembler DeviceMatch signal bindings with FB contract
behaviors to produce project-specific, address-resolved test scenarios.

NOTE: This is a Gate 6 SIMULATION artifact — NOT the RD13 Legacy Annotation
(which is a Gate 1 / Discovery pre-analysis output). The two were once
conflated under the "RD13" name; they are unrelated. See
the internal RD-gate design note.

Output:
  REPORTS/TEST_SCENARIOS.md              — human-readable FAT/PLCSIM checklist
  REPORTS/gate_results/test_scenarios.json  — machine-readable (PLCSIM runner)

Usage (standalone):
  python test_scenario_generator.py <project_root>

Usage (from factory_web.py):
  from rag.test_scenario_generator import generate_test_scenarios
  result = generate_test_scenarios(project_root)
  # or with already-computed matches:
  result = generate_test_scenarios(project_root, assembly_result=res)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Signal binding resolution
# ---------------------------------------------------------------------------

def _resolve_expr(
    expr: str,
    in_bindings: dict,
    out_bindings: dict,
    instance_db: str,
    addr_map: dict,
) -> list[dict]:
    """Parse 'param=value' tokens from a behavior expression string.

    Returns list of resolved token dicts:
      param, value, signal, address, db_ref, type
    """
    tokens: list[dict] = []
    for m in re.finditer(r"(\w+)\s*=\s*([^\s,;AND]+)", expr):
        param, value = m.group(1).strip(), m.group(2).strip()
        if not param or param in {"AND", "OR", "NOT", "TRUE", "FALSE"}:
            continue
        if param in in_bindings:
            sig = in_bindings[param]
            tokens.append({
                "param": param,
                "value": value,
                "signal": sig,
                "address": addr_map.get(sig, ""),
                "db_ref": f"{instance_db}.{param}",
                "type": "field_input",
            })
        elif param in out_bindings:
            sig = out_bindings[param]
            tokens.append({
                "param": param,
                "value": value,
                "signal": sig,
                "address": addr_map.get(sig, ""),
                "db_ref": f"{instance_db}.{param}",
                "type": "field_output",
            })
        else:
            tokens.append({
                "param": param,
                "value": value,
                "signal": None,
                "address": "",
                "db_ref": f"{instance_db}.{param}",
                "type": "plc_internal",
            })
    return tokens


def _readable(tokens: list[dict]) -> str:
    parts: list[str] = []
    for t in tokens:
        if t["signal"]:
            addr = f" [{t['address']}]" if t["address"] else ""
            parts.append(f"{t['signal']}{addr} ({t['param']}) = {t['value']}")
        else:
            parts.append(f"{t['db_ref']} = {t['value']}")
    return ", ".join(parts) if parts else "—"


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------

def generate_test_scenarios(
    project_root: Path,
    assembly_result: Any = None,
) -> dict:
    """Generate Gate 6 test scenarios from RD01 + FB contract behaviors.

    Parameters
    ----------
    project_root:
        Path to the open Factory project (contains RD01, _output, REPORTS …).
    assembly_result:
        Optional AssemblyResult from program_assembler.assemble_program().
        When supplied the RD01 parse + device matching steps are skipped;
        only the behavior-to-binding resolution and file writing run.

    Returns
    -------
    dict with keys: ok, tc_count, device_count, md_path, json_path, msg
    """
    sys.path.insert(0, str(_SCRIPTS_DIR))
    try:
        from program_assembler import (  # type: ignore
            load_contracts,
            group_devices,
            _classify_device,
            DeviceMatch,
            bind_device,
        )
        from iec_tag_generator import parse_rd01_signals  # type: ignore
    except ImportError as exc:
        return {"ok": False, "msg": f"Import error: {exc}", "tc_count": 0}

    # -- resolve device matches --------------------------------------------
    if assembly_result is not None:
        matches = assembly_result.matches
        signals = parse_rd01_signals(project_root)
    else:
        signals = parse_rd01_signals(project_root)
        if not signals:
            return {
                "ok": False,
                "msg": "RD01 IO list empty — complete Gate 3 (Code Generation) first.",
                "tc_count": 0,
            }
        contracts = load_contracts()
        devices, _ = group_devices(signals)
        matches = []
        for dev in devices:
            stem = _classify_device(dev)
            if stem is None or stem not in contracts:
                continue
            entry = contracts[stem]
            m = DeviceMatch(
                device=dev,
                contract_stem=stem,
                scl_path=entry["scl_path"],
                contract_path=entry["contract_path"],
                instance_db=f"iDB_{dev.device_id}",
            )
            bind_device(m)
            matches.append(m)

    # signal name → PLC address lookup (from RD01 Address column)
    addr_map: dict[str, str] = {
        s["name"]: s.get("address", "") for s in signals if s.get("name")
    }

    if not matches:
        return {
            "ok": False,
            "msg": "No matched devices found — check RD01 signal naming (SCOPE_EQUIP_NNN).",
            "tc_count": 0,
        }

    # -- build test cases --------------------------------------------------
    test_cases: list[dict] = []
    tc_index = 1

    for match in matches:
        try:
            contract = json.loads(
                match.contract_path.read_text(encoding="utf-8")
            )
        except Exception:
            continue

        behaviors = contract.get("behaviors", [])
        if not behaviors:
            continue

        for beh in behaviors:
            given_tokens = _resolve_expr(
                beh.get("given", ""),
                match.in_bindings, match.out_bindings, match.instance_db, addr_map,
            )
            then_tokens = _resolve_expr(
                beh.get("then", ""),
                match.in_bindings, match.out_bindings, match.instance_db, addr_map,
            )

            test_cases.append({
                "tc_id": f"TC-{tc_index:03d}",
                "device_id": match.device.device_id,
                "device_desc": match.device.description,
                "fb": match.contract_stem,
                "instance_db": match.instance_db,
                "behavior_id": beh.get("id", f"BEH-{tc_index}"),
                "given": {
                    "raw": beh.get("given", ""),
                    "tokens": given_tokens,
                    "readable": _readable(given_tokens),
                },
                "when": beh.get("when", ""),
                "then": {
                    "raw": beh.get("then", ""),
                    "tokens": then_tokens,
                    "readable": _readable(then_tokens),
                },
                "status": "PENDING",
                "in_bindings": match.in_bindings,
                "out_bindings": match.out_bindings,
                "unbound_ports": match.todos,
            })
            tc_index += 1

    # -- write outputs -----------------------------------------------------
    reports_dir = project_root / "REPORTS"
    gate_results_dir = reports_dir / "gate_results"
    gate_results_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat()
    project_name = project_root.name

    json_payload = {
        "generated": ts,
        "project": project_name,
        "tc_count": len(test_cases),
        "device_count": len(matches),
        "test_cases": test_cases,
    }
    json_path = gate_results_dir / "test_scenarios.json"
    json_path.write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    md_path = reports_dir / "TEST_SCENARIOS.md"
    md_path.write_text(
        _render_md(test_cases, matches, project_name, ts, addr_map),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "tc_count": len(test_cases),
        "device_count": len(matches),
        "md_path": str(md_path),
        "json_path": str(json_path),
        "msg": f"{len(test_cases)} test cases, {len(matches)} devices",
    }


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_md(
    test_cases: list[dict],
    matches: list,
    project_name: str,
    ts: str,
    addr_map: dict,
) -> str:
    lines = [
        "# Test Scenarios (Gate 6 Simulation)",
        "",
        f"**Project:** {project_name}  ",
        f"**Generated:** {ts[:19].replace('T', ' ')} UTC  ",
        f"**Device count:** {len(matches)}  **Test case count:** {len(test_cases)}  ",
        "",
        "> Source: FB contract behaviors + program_assembler signal bindings (RD01).  ",
        "> Each TC is resolved to a real field signal.  ",
        "> PLCSIM run: set 'Given' inputs -> wait for 'When' condition -> read 'Then' outputs.  ",
        "",
        "---",
        "",
    ]

    # group by device
    by_device: dict[str, list[dict]] = {}
    for tc in test_cases:
        by_device.setdefault(tc["device_id"], []).append(tc)

    for device_id, tcs in by_device.items():
        first = tcs[0]
        lines += [
            f"## {device_id} — {first['fb']}",
            f"",
            f"**Instance DB:** `{first['instance_db']}`  ",
            f"**Description:** {first['device_desc']}  ",
            "",
        ]

        in_b = first["in_bindings"]
        out_b = first["out_bindings"]
        if in_b or out_b:
            lines += [
                "**Signal Bindings:**",
                "",
                "| Dir | FB Parameter | Field Signal | PLC Address |",
                "|-----|---------------|--------------|------------|",
            ]
            for param, sig in in_b.items():
                addr = addr_map.get(sig, "—")
                lines.append(f"| IN  | `{param}` | `{sig}` | `{addr}` |")
            for param, sig in out_b.items():
                addr = addr_map.get(sig, "—")
                lines.append(f"| OUT | `{param}` | `{sig}` | `{addr}` |")
            lines.append("")

        unbound = first["unbound_ports"]
        if unbound:
            lines.append("**WARNING - Unbound ports (manual wiring required):**")
            for u in unbound:
                lines.append(f"- {u}")
            lines.append("")

        for tc in tcs:
            lines += [
                f"### {tc['tc_id']} — {tc['behavior_id']}",
                "",
                f"**Given:** {tc['given']['readable'] or tc['given']['raw']}  ",
                f"**When:** {tc['when']}  ",
                "**Then:**",
                "",
            ]
            for t in tc["then"]["tokens"]:
                sig = f" (`{t['signal']}`)" if t["signal"] else ""
                lines.append(f"- `{t['db_ref']}`{sig} = `{t['value']}`")
            lines += [
                "",
                "**Result:** `[ ] PASS  [ ] FAIL  [ ] SKIP`",
                "",
                "**Note:** ___",
                "",
                "---",
                "",
            ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_scenario_generator.py <project_root>")
        sys.exit(1)
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)
    out = generate_test_scenarios(root)
    print(json.dumps(out, indent=2, ensure_ascii=False))
