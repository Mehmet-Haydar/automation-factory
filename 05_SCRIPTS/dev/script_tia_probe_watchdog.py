"""Bisect the FB_WATCHDOG compile error by importing renamed variants.

Imports each variant as FB_WDT_PROBEn into the open TIA project, compiles
just that block, prints the errors, then deletes the probe block.

Usage: .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_tia_probe_watchdog.py
"""

from __future__ import annotations

import re
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


def _variants(text: str):
    yield "verbatim", text
    yield "ascii_only", re.sub(r"[^\x00-\x7F]", "-", text)
    # strip the comment that sits on the same line as the CASE label
    yield "no_label_comments", re.sub(r"(\d+:)\s*//[^\n]*", r"\1", text)
    # comments stripped entirely
    yield "no_comments", re.sub(r"//[^\n]*", "", text)


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

    base = SRC.read_text(encoding="utf-8")
    tmpdir = Path(tempfile.mkdtemp(prefix="wdt_probe_"))

    for i, (label, text) in enumerate(_variants(base), start=1):
        name = f"FB_WDT_PROBE{i}"
        variant = text.replace('FUNCTION_BLOCK "FB_WATCHDOG"',
                               f'FUNCTION_BLOCK "{name}"')
        f = tmpdir / f"{name}.scl"
        f.write_text(variant, encoding="utf-8")

        ext_grp = plc_sw.ExternalSourceGroup
        try:
            old_src = ext_grp.ExternalSources.Find(f.name)
            if old_src is not None:
                old_src.Delete()
        except Exception:
            pass
        try:
            old_blk = core._find_block(plc_sw.BlockGroup, name)
            if old_blk is not None:
                old_blk.Delete()
        except Exception:
            pass

        try:
            ext_src = ext_grp.ExternalSources.CreateFromFile(f.name, str(f))
            ext_src.GenerateBlocksFromSource()
        except Exception as e:
            print(f"{label}: GENERATION FAILED: {e}", flush=True)
            continue

        blk = core._find_block(plc_sw.BlockGroup, name)
        if blk is None:
            print(f"{label}: block not found after generation", flush=True)
            continue
        try:
            result = blk.GetService[ICompilable]().Compile()
            cs = _summarize_compile_result(result)
            errs = [m for m in cs.messages if m.severity == "Error"]
            print(f"{label}: state={cs.state} errors={cs.errors}", flush=True)
            for m in errs:
                print(f"    [ERROR] path={m.block!r} | {m.text}", flush=True)
        except Exception as e:
            print(f"{label}: COMPILE CALL FAILED: {e}", flush=True)
        finally:
            try:
                blk.Delete()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
