"""Attach to running TIA, export a program block to XML for inspection.

Usage:
  .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_tia_export_block.py [BLOCK] [OUT]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / "05_SCRIPTS")):
    if p not in sys.path:
        sys.path.insert(0, p)

from bridges.tia.version_detect import find_one  # noqa: E402
from bridges.tia.openness_core import OpennessCore  # noqa: E402

# Diagnostic scripts run against a scratch TIA project on the dev machine.
# Set TIA_PROBE_PROJECT to your own .ap19/.ap20/.ap21 scratch project.
AP = Path(os.environ.get(
    "TIA_PROBE_PROJECT",
    r"C:\TIA_Projects\OpennessTest\OpennessTest.ap19"))


def main() -> int:
    block_name = sys.argv[1] if len(sys.argv) > 1 else "FB_WATCHDOG"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else (
        ROOT / "_tmp_block_export.xml")

    inst = find_one("V19")
    core = OpennessCore(inst.engineering_dll)
    core.start_portal()
    proj = core.open_project(AP)
    _, plc_sw = core.find_plc(proj, "PLC_1")

    blk = core._find_block(plc_sw.BlockGroup, block_name)
    if blk is None:
        print(f"block not found: {block_name}", flush=True)
        return 1

    if out.exists():
        out.unlink()
    import Siemens.Engineering as tia  # type: ignore
    blk.Export(core._FileInfo(str(out)), tia.ExportOptions(0))
    print(f"exported: {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
