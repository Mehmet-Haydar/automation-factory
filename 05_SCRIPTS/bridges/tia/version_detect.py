"""
Detect installed TIA Portal versions.

Siemens TIA Portal installs to this standard path:
  C:\\Program Files\\Siemens\\Automation\\Portal V{N}\\

Openness DLL:
  Portal V{N}\\PublicAPI\\V{N}\\Siemens.Engineering.dll

Both standard and 32-bit Program Files paths are scanned.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TiaInstall:
    version: str            # "V19", "V20", ...
    portal_root: Path       # Portal V20 folder
    engineering_dll: Path   # Siemens.Engineering.dll
    project_ext: str        # ".ap19" / ".ap20"

    @property
    def exists(self) -> bool:
        return self.engineering_dll.is_file()


_SEARCH_ROOTS_ENV = ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"]
_FALLBACK_ROOTS = [
    Path("C:/Program Files/Siemens/Automation"),
    Path("C:/Program Files (x86)/Siemens/Automation"),
    Path("D:/Program Files/Siemens/Automation"),
    Path("D:/Siemens/Automation"),
]


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    for env_var in _SEARCH_ROOTS_ENV:
        v = os.environ.get(env_var)
        if v:
            roots.append(Path(v) / "Siemens" / "Automation")
    roots.extend(_FALLBACK_ROOTS)
    # de-duplicated and existing
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        k = str(r).lower()
        if k not in seen:
            seen.add(k)
            if r.exists():
                out.append(r)
    return out


def find_installs(versions: list[str] | None = None) -> list[TiaInstall]:
    """Find TIA installations for the given versions.

    If versions is None, V14..V21 are all scanned.
    """
    if versions is None:
        versions = [f"V{n}" for n in range(14, 22)]
    found: list[TiaInstall] = []
    for root in _candidate_roots():
        for ver in versions:
            portal_dir = root / f"Portal {ver}"
            dll = portal_dir / "PublicAPI" / ver / "Siemens.Engineering.dll"
            if dll.is_file():
                found.append(TiaInstall(
                    version=ver,
                    portal_root=portal_dir,
                    engineering_dll=dll,
                    project_ext=f".ap{ver[1:]}",
                ))
    return found


def find_one(version: str) -> TiaInstall | None:
    """Search for a single version — returns None if not found."""
    for inst in find_installs([version]):
        if inst.version == version:
            return inst
    return None


def is_user_in_openness_group() -> bool | None:
    """
    Is the user in the 'Siemens TIA Openness' Windows local group?

    Returns:
      True  — in the group
      False — not in the group
      None  — could not check (not on Windows, or command failed)
    """
    if sys.platform != "win32":
        return None
    try:
        import subprocess
        # We search for the group in `whoami /groups` output
        # encoding+errors: the console emits the OEM codepage (cp850 on a
        # German Windows — 0x84 = "ä"); with PYTHONUTF8=1 a bare text=True
        # decodes as UTF-8 and the reader thread dies with
        # UnicodeDecodeError at every app start. The needle below is pure
        # ASCII, so lossy replacement is safe.
        out = subprocess.run(
            ["whoami", "/groups"],
            capture_output=True, text=True, timeout=8,
            encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if out.returncode != 0:
            return None
        text = out.stdout.lower()
        return "siemens tia openness" in text
    except Exception:
        return None


if __name__ == "__main__":
    print("TIA installations:")
    for inst in find_installs():
        print(f"  {inst.version}  ->  {inst.engineering_dll}")
    print()
    grp = is_user_in_openness_group()
    if grp is True:
        print("User in 'Siemens TIA Openness' group: YES")
    elif grp is False:
        print("User in 'Siemens TIA Openness' group: NO (need to add)")
    else:
        print("Could not check group membership.")
