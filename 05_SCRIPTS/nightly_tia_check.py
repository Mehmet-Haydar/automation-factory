"""
Nightly TIA compile check — Kademe 2 driver (SAT v2 Faz 7, PASSIVE prep).

Imports the 18 library SCL blocks into a scratch TIA project via Openness,
compiles, and prints a one-line PASS/FAIL per block. It is the script the
`.github/workflows/nightly-tia.yml` workflow calls; that workflow is
`workflow_dispatch`-only until a self-hosted `tia` runner exists
(see docs/NIGHTLY_TIA_CI_SETUP.md).

Design rules:
  * Log hygiene — ONLY the block name and PASS/FAIL/SKIP are printed.
    No project path, customer name, or filesystem path ever reaches stdout.
  * No silent success — an empty block inventory, a missing scratch project,
    or an unavailable Openness bridge is a LOUD non-zero exit, never a
    green "0 blocks, all pass".
  * Read-only intent — import + compile only. Never downloads to a PLC
    (the download path is not used here at all).

Modes:
  --preflight   Inventory-only: verify the 18 SCL blocks exist and print the
                plan. Exits 0 if all present. Safe to run on any host
                (no Openness needed) — this is what CI runs as a smoke check
                until a runner is wired.
  (default)     Full run: requires --project <scratch .ap*> and an available
                TIA bridge. Imports + compiles + reports.

Exit codes: 0 = all PASS (or preflight OK); 1 = a block FAILED or the run
could not be performed (missing project / no bridge / import error).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 06_KNOWLEDGE_BASE is two levels up from this file's parent (repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_KB = _REPO_ROOT / "06_KNOWLEDGE_BASE"

# The 18 library blocks (same inventory as the acceptance gate in ci.yml).
# Relative to 06_KNOWLEDGE_BASE/blocks/.
BLOCK_RELPATHS: list[str] = [
    "motor/FB_Motor_DOL.scl",
    "motor/FB_Motor_Standard.scl",
    "motor/FB_Motor_SoftStarter.scl",
    "motor/FB_Motor_StarDelta.scl",
    "motor/FB_Motor_VFD.scl",
    "ob/OB_Diagnostic_OB82.scl",
    "ob/OB_Main_OB1.scl",
    "ob/OB_RackFailure_OB86.scl",
    "ob/OB_Startup_OB100.scl",
    "process/FB_AlarmHandler.scl",
    "process/FB_AnalogScale.scl",
    "process/FB_PID_Wrapper.scl",
    "system/FB_ModeManager.scl",
    "system/FB_SequenceEngine.scl",
    "system/FB_Watchdog.scl",
    "valve/FB_Valve_3Way.scl",
    "valve/FB_Valve_Modulating.scl",
    "valve/FB_Valve_OnOff.scl",
]


def block_name(relpath: str) -> str:
    """Block name only (no path) — used for log-hygiene-safe output."""
    return Path(relpath).stem


def resolve_blocks(kb_root: Path = _KB) -> list[Path]:
    """Absolute SCL paths. Raises if the inventory is empty or incomplete.

    Returning a short or empty list silently would be a fake green run, so
    a missing block is a hard error here.
    """
    blocks_dir = kb_root / "blocks"
    found: list[Path] = []
    missing: list[str] = []
    for rel in BLOCK_RELPATHS:
        p = blocks_dir / rel
        if p.is_file():
            found.append(p)
        else:
            missing.append(block_name(rel))
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} library block(s) missing from inventory: "
            + ", ".join(missing)
        )
    if not found:
        raise FileNotFoundError("block inventory is empty")
    return found


def run_preflight(out=print) -> int:
    """Inventory smoke check — no Openness needed. 0 = OK, 1 = incomplete."""
    try:
        blocks = resolve_blocks()
    except FileNotFoundError as e:
        out(f"PREFLIGHT FAIL: {e}")
        return 1
    out(f"PREFLIGHT OK — {len(blocks)} blocks ready for nightly compile:")
    for b in blocks:
        out(f"  [READY] {b.stem}")
    out(
        "Openness compile not run in preflight mode. "
        "Wire a self-hosted 'tia' runner (see docs/NIGHTLY_TIA_CI_SETUP.md), "
        "then run without --preflight."
    )
    return 0


def _load_tia_bridge():
    """Return (bridge, core) or raise RuntimeError with a clear reason.

    Lazy — importing this module never requires pythonnet/Openness.
    """
    sys.path.insert(0, str(_REPO_ROOT / "05_SCRIPTS"))
    try:
        from bridges.bridge_manager import BridgeManager  # type: ignore
    except Exception as e:  # pragma: no cover - import wiring
        raise RuntimeError(f"bridge layer unavailable: {e}") from e

    settings: dict = {}
    mgr = BridgeManager(settings)
    # Prefer the newest enabled TIA bridge.
    for bid in ("tia_v21", "tia_v20", "tia_v19"):
        b = mgr.get(bid)
        if b is not None and mgr.is_enabled(bid):
            return b
    raise RuntimeError(
        "no enabled TIA bridge — set bridges.enabled.tia_vNN and configure "
        "Openness on this runner (see docs/NIGHTLY_TIA_CI_SETUP.md)"
    )


def run_full(project: Path, plc_name: str = "PLC_1", out=print) -> int:
    """Import + compile the 18 blocks into a scratch project. Log-hygiene safe."""
    try:
        blocks = resolve_blocks()
    except FileNotFoundError as e:
        out(f"FAIL: {e}")
        return 1
    if not project or not Path(project).exists():
        # Path is NOT printed (log hygiene) — only the fact of absence.
        out("FAIL: scratch TIA project not found (pass a valid --project)")
        return 1

    try:
        bridge = _load_tia_bridge()
    except RuntimeError as e:
        out(f"FAIL: {e}")
        return 1

    try:
        core = bridge._get_core()  # type: ignore[attr-defined]
        core.start_portal(with_ui=False)
        proj = core.open_project(Path(project))
        _plc_item, plc_sw = core.find_plc(proj, plc_name)
        if plc_sw is None:
            out(f"FAIL: PLC '{plc_name}' not found in scratch project")
            return 1
        imp = core.import_scl_files(plc_sw, blocks, skip_safety=True)
        generated = {Path(b).stem for b in imp.blocks_generated}
        failed_import = {block_name(str(f)) for f in imp.failed}
        # A compile that returns errors is a FAILURE even when import
        # succeeded — reporting [PASS] on an uncompilable block would be a
        # silent-success violation. Attribute errors per block when the
        # Openness messages name a block; otherwise fail the whole run.
        cs = core.compile_plc(plc_sw)
        compile_failed = {
            m.block for m in getattr(cs, "messages", [])
            if getattr(m, "severity", "") == "Error" and getattr(m, "block", "")
        }
        compile_errors_total = getattr(cs, "errors", 0)
    except Exception as e:  # noqa: BLE001 - surface, never swallow
        # Keep the message generic — no path leakage.
        out(f"FAIL: Openness run error: {type(e).__name__}")
        return 1
    finally:
        try:
            core.stop_portal()  # type: ignore[possibly-undefined]
        except Exception:
            pass

    bad: list[str] = []
    for b in blocks:
        name = b.stem
        if name in failed_import:
            out(f"  [FAIL] {name}  (import)")
            bad.append(name)
        elif name in compile_failed:
            out(f"  [FAIL] {name}  (compile)")
            bad.append(name)
        elif name in generated:
            out(f"  [PASS] {name}")
        else:
            out(f"  [FAIL] {name}  (not generated)")
            bad.append(name)

    # Compile reported errors but none mapped to a named block → fail loudly
    # rather than printing all-PASS on an unattributable compile error.
    if not bad and compile_errors_total:
        out(f"NIGHTLY TIA FAILED: compile reported {compile_errors_total} "
            "error(s) not attributable to a single block")
        return 1
    if bad:
        out(f"NIGHTLY TIA FAILED: {len(bad)}/{len(blocks)} block(s) — {', '.join(bad)}")
        return 1
    out(f"NIGHTLY TIA OK — all {len(blocks)} blocks imported + compiled")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Nightly TIA compile check (Kademe 2)")
    ap.add_argument("--project", default="",
                    help="scratch TIA project (.ap19/.ap20/.ap21)")
    ap.add_argument("--plc", default="PLC_1", help="PLC device name in the project")
    ap.add_argument("--preflight", action="store_true",
                    help="inventory-only smoke check (no Openness needed)")
    args = ap.parse_args(argv)

    if args.preflight:
        return run_preflight()
    return run_full(Path(args.project) if args.project else None, args.plc)


if __name__ == "__main__":
    sys.exit(main())
