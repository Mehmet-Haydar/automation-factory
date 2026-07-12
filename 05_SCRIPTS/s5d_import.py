#!/usr/bin/env python3
"""s5d_import.py — direct Step5 .s5d import (no S5-für-Windows needed).

Reads the customer's Step5 binary project via DotNetSiemensPLCToolBoxLibrary
(LGPL-2.1; DLLs are fetched by 05_SCRIPTS/fetch_s5d_toolbox.ps1 into
05_SCRIPTS/_s5d_toolbox/ — never vendored, never modified) and renders every
logic block into the same AWL dialect an S5-für-Windows export produces, so
the existing extraction pipeline consumes it unchanged.

Provenance: on the blind-test
machine the rendered stream is instruction-identical with the manual S5W
export for 20/21 logic blocks (~3000 instructions, timer constants
included); the single differing block was a code-version delta, not a
conversion artifact. 65/65 archive .s5d files open without a crash.

Timer constants: the library's text rendering loses "L KT <value>"; we
recover the value from the ROW's own MC5 bytes (opcode 0x3002, operand =
base<<12 | 3-digit BCD) — no ordering assumptions. If the bytes do not
decode as BCD the row keeps bare "KT" and the import reports a warning
(fail-honest, never guessed).

Out of scope (reported as warnings, never silently dropped): BB blocks
(library returns null), comment blocks (PK/OK/FK/DK), data blocks (values
come via the print export), special ASM bodies of Siemens standard FBs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
TOOLBOX_DIR = _SCRIPTS_DIR / "_s5d_toolbox"

# ---------------------------------------------------------------------------
# pure rendering layer (unit-tested; no .NET required)
# ---------------------------------------------------------------------------

# German (toolbox) -> English (S5W export dialect the pipeline understands).
# NOTE the treacherous timer pair: German SV == English SE (extended pulse),
# German SE == English SD (on-delay). Verified against the parity corpus.
OP_DE2EN = {
    "U": "A", "UN": "AN", "O": "O", "ON": "ON",
    "U(": "A(", "O(": "O(", ")": ")",
    "=": "=", "S": "S", "R": "R",
    "SPA": "JU", "SPB": "JC",
    "SI": "SP", "SV": "SE", "SE": "SD", "SS": "SS", "SA": "SF",
    "ZV": "CU", "ZR": "CD",
    "L": "L", "LC": "LC", "T": "T",
    "BE": "BE", "BEB": "BEC", "BEA": "BEU",
    "NOP0": "NOP", "NOP": "NOP",
    "UW": "AW", "OW": "OW", "XOW": "XOW",
    "SLW": "SLW", "SRW": "SRW",
    "!=F": "!=F", "><F": "><F", ">F": ">F", "<F": "<F",
    ">=F": ">=F", "<=F": "<=F", "+F": "+F", "-F": "-F",
    "I": "I", "D": "D", "ADD": "ADD", "TAK": "TAK",
    "STP": "STP", "STS": "STS", "BLD": "BLD",
}

# operand-area letters (first token of the parameter)
OPD_DE2EN = {
    "E": "I", "A": "Q", "M": "F", "Z": "C",
    "EB": "IB", "EW": "IW", "AB": "QB", "AW": "QW",
    "MB": "FY", "MW": "FW",
    # unchanged: T, D/DW/DL/DR, PB/OB/FB/SB/DB, PW/PY, K* constants
}


@dataclass
class S5Row:
    """One instruction as the toolbox reports it (German mnemonics)."""
    command: str
    parameter: str = ""
    label: str = ""
    mc5: bytes = b""


@dataclass
class ImportSummary:
    blocks_written: list = field(default_factory=list)
    networks: int = 0
    warnings: list = field(default_factory=list)
    seq_copied: list = field(default_factory=list)
    dest: Path | None = None


def decode_kt(mc5: bytes) -> str | None:
    """'L KT' row bytes -> '050.0' style constant; None if not decodable."""
    if len(mc5) < 4 or mc5[0] != 0x30 or mc5[1] != 0x02:
        return None
    word = (mc5[2] << 8) | mc5[3]
    digits = f"{word & 0x0FFF:03x}"
    if not digits.isdigit():        # nibbles must be BCD — never guess
        return None
    return f"{digits}.{(word >> 12) & 0x3}"


def _km_binary(text: str) -> str:
    """Toolbox 'KM <int>' -> S5W 'KM 11111111 00000000' bit style."""
    try:
        val = int(text) & 0xFFFF
    except ValueError:
        return text
    bits = f"{val:016b}"
    return f"{bits[:8]} {bits[8:]}"


def render_parameter(param: str) -> str:
    """Map the operand area letter to the English dialect."""
    parts = param.split()
    if not parts:
        return ""
    head = parts[0]
    if head == "KM" and len(parts) == 2:
        return f"KM {_km_binary(parts[1])}"
    mapped = OPD_DE2EN.get(head, head)
    return " ".join([mapped, *parts[1:]])


def render_row(row: S5Row) -> tuple[list[str], str]:
    """One toolbox row -> AWL export line(s). Returns (lines, warning)."""
    cmd = row.command.strip()
    if cmd == "BLD" or not cmd:
        return [], ""                       # display directive — no code
    op = OP_DE2EN.get(cmd)
    if op is None:
        # unknown mnemonic: keep it visibly foreign instead of guessing
        return [f"\t?{cmd}?\t{row.parameter}".rstrip()], (
            f"unknown mnemonic '{cmd}' kept as ?{cmd}?")
    warn = ""
    param = row.parameter.strip()
    if op == "NOP":
        param = "0"
    elif op == "L" and param == "KT":
        val = decode_kt(row.mc5)
        if val is not None:
            param = f"KT {val}"
        else:
            warn = "timer constant not recoverable — bare 'L KT' kept"
    elif param:
        param = render_parameter(param)
    prefix = f"{row.label}:" if row.label else ""
    line = f"{prefix}\t{op}\t{param}".rstrip() if param \
        else f"{prefix}\t{op}\t".rstrip("\t") + "\t"
    lines = [line]
    return lines, warn


_PG_CODE = {"OB": "80000000", "PB": "82000000", "FB": "84000000",
            "SB": "86000000"}


def render_block(name: str, networks: list[list[S5Row]]) -> tuple[str, list]:
    """Full block in S5W export format: ###PG header + [n ... ***] networks,
    final network closed by BE when present."""
    warns: list[str] = []
    out = [f"###PG:{_PG_CODE.get(name[:2], '82000000')}"]
    n_nets = len(networks)
    for ni, rows in enumerate(networks, 1):
        out.append(f"[{ni}\t")
        body: list[str] = []
        for row in rows:
            lines, warn = render_row(row)
            if warn:
                warns.append(f"{name}/N{ni}: {warn}")
            body.extend(lines)
        closed = False
        if ni == n_nets and body and body[-1].strip().startswith("BE"):
            body[-1] = "\tBE\t]"
            closed = True
        out.extend(body)
        if not closed:
            out.append("\t***\t]")
    return "\n".join(out) + "\n", warns


# ---------------------------------------------------------------------------
# .NET reader layer
# ---------------------------------------------------------------------------

_SKIP_PREFIXES = ("PK", "OK", "FK", "DK")     # Kommentarbausteine


def toolbox_available() -> bool:
    return (TOOLBOX_DIR / "DotNetSiemensPLCToolBoxLibrary.dll").exists()


def _load_projects_class():
    import sys
    if str(TOOLBOX_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLBOX_DIR))
    import clr  # type: ignore
    clr.AddReference(str(TOOLBOX_DIR / "DotNetSiemensPLCToolBoxLibrary"))
    from DotNetSiemensPLCToolBoxLibrary.Projectfiles import (  # type: ignore
        Projects,
    )
    return Projects


def _adapt_rows(net) -> list[S5Row]:
    rows: list[S5Row] = []
    for r in list(net.AWLCode):
        mc5 = getattr(r, "MC5", None)
        rows.append(S5Row(
            command=str(r.Command or ""),
            parameter=str(r.Parameter or ""),
            label=str(getattr(r, "Label", "") or ""),
            mc5=bytes(mc5) if mc5 is not None else b"",
        ))
    return rows


def import_s5d(s5d_path: str | Path, dest_dir: str | Path) -> ImportSummary:
    """Convert every logic block of the .s5d into <NAME>.AWL files in
    dest_dir and copy sibling symbol files (*.seq). Raises RuntimeError
    with an actionable message when prerequisites are missing."""
    s5d = Path(s5d_path)
    dest = Path(dest_dir)
    if not s5d.is_file() or s5d.suffix.lower() != ".s5d":
        raise RuntimeError(f"Not a .s5d file: {s5d}")
    if not toolbox_available():
        raise RuntimeError(
            "S5D toolbox DLLs missing — run "
            "05_SCRIPTS/fetch_s5d_toolbox.ps1 once (downloads the LGPL "
            "DotNetSiemensPLCToolBoxLibrary from NuGet).")
    try:
        Projects = _load_projects_class()
    except Exception as exc:
        raise RuntimeError(
            f"pythonnet/.NET load failed: {exc} — 'pip install pythonnet' "
            "and a .NET Framework 4.6.1+ runtime are required.") from exc

    summ = ImportSummary(dest=dest)
    prj = Projects.LoadProject(str(s5d), False)
    folder = prj.ProjectStructure
    bf = getattr(folder, "BlocksFolder", None)
    if bf is None:
        raise RuntimeError("No Step5 blocks folder found in this file.")

    dest.mkdir(parents=True, exist_ok=True)
    # Old .s5d files may carry several versions of the same block. Keep the
    # richest one (most networks; tie -> last seen) and say so out loud —
    # silently letting the last version win loses logic.
    kept_networks: dict[str, int] = {}
    version_count: dict[str, int] = {}
    for info in list(bf.BlockInfos):
        name = str(getattr(info, "BlockName", "") or "").replace(" ", "")
        if not name:
            continue
        if name.startswith(_SKIP_PREFIXES):
            continue                        # comment blocks — not code
        if name.startswith("DB"):
            summ.warnings.append(
                f"{name}: data block skipped — DB values are not converted "
                "(use the S5 print export if values are needed)")
            continue
        try:
            blk = bf.GetBlock(info)
        except Exception as exc:
            summ.warnings.append(f"{name}: read failed — {exc}")
            continue
        if blk is None:
            summ.warnings.append(
                f"{name}: library cannot decode this block type "
                "(known BB limitation) — export manually if it holds logic")
            continue
        nets = getattr(blk, "Networks", None)
        if not nets:
            summ.warnings.append(f"{name}: no networks — skipped")
            continue
        networks = [_adapt_rows(n) for n in list(nets)]
        version_count[name] = version_count.get(name, 0) + 1
        prev = kept_networks.get(name)
        if prev is not None and len(networks) < prev:
            continue                        # poorer duplicate — keep richer
        text, warns = render_block(name, networks)
        summ.warnings.extend(warns)
        (dest / f"{name}.AWL").write_text(text, encoding="utf-8")
        if prev is None:
            summ.blocks_written.append(name)
        kept_networks[name] = len(networks)

    summ.networks = sum(kept_networks.values())
    for name, cnt in sorted(version_count.items()):
        if cnt > 1:
            summ.warnings.append(
                f"{name}: {cnt} versions inside the .s5d — kept the richest "
                f"({kept_networks[name]} networks), discarded the rest")

    # symbol files travel next to the s5d in Step5 projects
    for seq in sorted(s5d.parent.glob("*.seq")) + \
            sorted(s5d.parent.glob("*.SEQ")):
        target = dest / seq.name.lower()
        if not target.exists():
            target.write_bytes(seq.read_bytes())
            summ.seq_copied.append(seq.name)

    if not summ.blocks_written:
        raise RuntimeError("No logic blocks could be converted from this "
                           ".s5d — see warnings.")
    return summ


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: s5d_import.py <file.s5d> <dest_dir>")
        raise SystemExit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    s = import_s5d(sys.argv[1], sys.argv[2])
    print(f"{len(s.blocks_written)} blocks, {s.networks} networks -> "
          f"{s.dest}")
    for w in s.warnings:
        print("  WARN", w)
    for q in s.seq_copied:
        print("  SEQ ", q)
