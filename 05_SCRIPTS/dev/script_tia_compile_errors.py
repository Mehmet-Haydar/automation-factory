"""Attach to the running TIA Portal, compile PLC_1 and print ALL errors.

Usage: .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_tia_compile_errors.py
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
    inst = find_one("V19")
    core = OpennessCore(inst.engineering_dll)
    core.start_portal()  # attaches to the running portal
    proj = core.open_project(AP)
    _, plc_sw = core.find_plc(proj, "PLC_1")
    cs = core.compile_plc(plc_sw)
    print(f"state={cs.state} errors={cs.errors} warnings={cs.warnings}",
          flush=True)
    for m in cs.messages:
        if m.severity == "Error":
            print(f"[ERROR] block={m.block!r} | {m.text}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
