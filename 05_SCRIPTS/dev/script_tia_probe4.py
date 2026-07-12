"""Verify the fix: a ';' no-op statement inside the comment-only IF body.

Usage: .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_tia_probe4.py
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
    # line 103 (1-based) is the commented-out example statement; line 102 the
    # placeholder note. Insert the no-op by rewriting line 103 and keeping the
    # example as part of the same line's comment.
    assert "out_bFault := TRUE; out_wErrorCode := 16#0002;" in lines[102]
    lines[102] = ("               ;  // no-op — replace with: "
                  "out_bFault := TRUE; out_wErrorCode := 16#0002;")

    name = "FB_WDT_FIXSEMI"
    text = ("\n".join(lines) + "\n").replace(
        'FUNCTION_BLOCK "FB_WATCHDOG"', f'FUNCTION_BLOCK "{name}"')
    tmpdir = Path(tempfile.mkdtemp(prefix="wdt_probe4_"))
    f = tmpdir / f"{name}.scl"
    f.write_text(text, encoding="utf-8")

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
    ext_src = ext_grp.ExternalSources.CreateFromFile(f.name, str(f))
    ext_src.GenerateBlocksFromSource()
    blk = core._find_block(plc_sw.BlockGroup, name)
    cs = _summarize_compile_result(blk.GetService[ICompilable]().Compile())
    print(f"FIXSEMI: state={cs.state} errors={cs.errors} "
          f"warnings={cs.warnings}", flush=True)
    for m in cs.messages:
        if m.severity == "Error" and "Compiling finished" not in m.text:
            print(f"    [ERROR] path={m.block!r} | {m.text}", flush=True)
    try:
        blk.Delete()
    except Exception:
        pass
    return 0 if cs.errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
