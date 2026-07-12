"""Binary-search the FB_WATCHDOG parse error by blanking code ranges.

The error reports at TIA line 57 = source line 109 even when that line is
blank -> the parser dies failing to CLOSE something opened earlier. Blank
each suspect range (line count preserved); the variant that goes clean
contains the culprit.

Usage: .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_tia_probe3.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / "05_SCRIPTS")):
    if p not in sys.path:
        sys.path.insert(0, p)

from bridges.tia.version_detect import find_one  # noqa: E402
from bridges.tia.openness_core import OpennessCore, _summarize_compile_result  # noqa: E402

# Diagnostic scripts run against a scratch TIA project on the dev machine.
# Set TIA_PROBE_PROJECT to your own .ap19/.ap20/.ap21 scratch project.
AP = Path(os.environ.get(
    "TIA_PROBE_PROJECT",
    r"C:\TIA_Projects\OpennessTest\OpennessTest.ap19"))
SRC = (ROOT / "examples" / "Demo_Beispielmaschine_4711" / "_output" / "scl"
       / "FB_Watchdog.scl")


def compile_variant(core, plc_sw, ICompilable, name, text, tmpdir):
    variant = text.replace('FUNCTION_BLOCK "FB_WATCHDOG"',
                           f'FUNCTION_BLOCK "{name}"')
    f = tmpdir / f"{name}.scl"
    f.write_text(variant, encoding="utf-8")
    ext_grp = plc_sw.ExternalSourceGroup
    try:
        old = ext_grp.ExternalSources.Find(f.name)
        if old is not None:
            old.Delete()
    except Exception:
        pass
    try:
        old = core._find_block(plc_sw.BlockGroup, name)
        if old is not None:
            old.Delete()
    except Exception:
        pass
    try:
        ext_src = ext_grp.ExternalSources.CreateFromFile(f.name, str(f))
        ext_src.GenerateBlocksFromSource()
    except Exception as e:
        print(f"{name}: GENERATION FAILED: {e}", flush=True)
        return
    blk = core._find_block(plc_sw.BlockGroup, name)
    if blk is None:
        print(f"{name}: block missing", flush=True)
        return
    try:
        cs = _summarize_compile_result(blk.GetService[ICompilable]().Compile())
        errs = [m for m in cs.messages
                if m.severity == "Error" and "Compiling finished" not in m.text]
        verdict = "CLEAN" if cs.errors == 0 else "ERROR"
        print(f"{name}: {verdict} (errors={cs.errors})", flush=True)
        for m in errs:
            print(f"    [ERROR] path={m.block!r} | {m.text}", flush=True)
    finally:
        try:
            blk.Delete()
        except Exception:
            pass


def main() -> int:
    inst = find_one("V19")
    core = OpennessCore(inst.engineering_dll)
    core.start_portal()
    proj = core.open_project(AP)
    _, plc_sw = core.find_plc(proj, "PLC_1")
    try:
        ICompilable = core._tia.Compiler.ICompilable
    except Exception:
        import Siemens.Engineering.Compiler as comp  # type: ignore
        ICompilable = comp.ICompilable

    lines = SRC.read_text(encoding="utf-8").splitlines()
    tmpdir = Path(tempfile.mkdtemp(prefix="wdt_probe3_"))

    def blank(*ranges):  # 1-based inclusive source-line ranges
        v = lines.copy()
        for lo, hi in ranges:
            for i in range(lo - 1, hi):
                v[i] = ""
        return "\n".join(v) + "\n"

    # source ranges (1-based):
    #  75-114 whole REGION 02 (incl. REGION/END_REGION)
    #  81- 86 heartbeat-edge IF + TON start call
    #  88- 97 timeout IF body
    # 100-104 monitorcomms IF
    # 106-111 99: branch + ELSE + END_CASE? (END_CASE=111, keep!) -> 106-110
    # 113     step-change IF (one line)
    cases = [
        ("R02_ALL", [(75, 114)]),
        ("HEARTBEAT_IF", [(81, 86)]),
        ("TIMEOUT_IF", [(88, 97)]),
        ("COMMS_IF", [(100, 104)]),
        ("TAIL_99_ELSE", [(106, 110)]),
        ("STEPCHANGE_IF", [(113, 113)]),
    ]
    for name, ranges in cases:
        compile_variant(core, plc_sw, ICompilable, f"FB_WDT_{name}",
                        blank(*ranges), tmpdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
