"""Find the real source line of the FB_WATCHDOG 'line 57' compile error.

Injects a deliberate syntax error at a KNOWN source line (keeping the
line count identical) and reads which line number TIA reports -> offset.

Usage: .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_tia_probe2.py
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


def compile_variant(core, plc_sw, ICompilable, name: str, text: str,
                    tmpdir: Path) -> None:
    variant = text.replace('FUNCTION_BLOCK "FB_WATCHDOG"',
                           f'FUNCTION_BLOCK "{name}"')
    f = tmpdir / f"{name}.scl"
    f.write_text(variant, encoding="utf-8")

    ext_grp = plc_sw.ExternalSourceGroup
    for cleanup in ("src", "blk"):
        try:
            if cleanup == "src":
                old = ext_grp.ExternalSources.Find(f.name)
            else:
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
        print(f"{name}: block missing after generation", flush=True)
        return
    try:
        cs = _summarize_compile_result(blk.GetService[ICompilable]().Compile())
        print(f"{name}: state={cs.state} errors={cs.errors}", flush=True)
        for m in cs.messages:
            if m.severity == "Error":
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
    tmpdir = Path(tempfile.mkdtemp(prefix="wdt_probe2_"))

    # Corrupt source line 56 ("s_bResetEdgeMem := in_bReset;") keeping the
    # line count — TIA's reported number for it gives us the offset.
    corrupted = lines.copy()
    assert "s_bResetEdgeMem := in_bReset;" in corrupted[55]
    corrupted[55] = corrupted[55].replace(":=", ":= @@@")
    compile_variant(core, plc_sw, ICompilable, "FB_WDT_OFS",
                    "\n".join(corrupted) + "\n", tmpdir)

    # Suspect-elimination variants (line counts preserved by blanking):
    def blank(idx0_from, idx0_to):  # inclusive 0-based
        v = lines.copy()
        for i in range(idx0_from, idx0_to + 1):
            v[i] = ""
        return "\n".join(v) + "\n"

    # ELSE branch of CASE (source lines 109-110)
    compile_variant(core, plc_sw, ICompilable, "FB_WDT_NOELSE",
                    blank(108, 109), tmpdir)
    # 99: branch (source lines 106-107)
    compile_variant(core, plc_sw, ICompilable, "FB_WDT_NO99",
                    blank(105, 106), tmpdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
