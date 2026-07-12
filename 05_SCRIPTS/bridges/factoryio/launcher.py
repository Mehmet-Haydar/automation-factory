"""
Factory I/O launcher bridge.

Launches Factory I/O from the command line and opens the given scene.
Driver (S7 PLCSIM Advanced) connection parameters live inside the scene
file; this bridge only handles launching + scene loading. The user makes
the driver connection from inside Factory I/O via 'Connect'.

CLI usage:
  python -m bridges.factoryio.launcher --scene "C:/scenes/Sorting.factoryio"
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..base import BridgeBase, BridgeStatus, BridgeResult


_DEFAULT_EXE_CANDIDATES = [
    r"C:\Program Files (x86)\Real Games\Factory IO\Factory IO.exe",
    r"C:\Program Files\Real Games\Factory IO\Factory IO.exe",
    # some older/Steam installs may live under bin/
    r"C:\Program Files (x86)\Real Games\Factory IO\bin\Factory IO.exe",
    r"C:\Program Files\Real Games\Factory IO\bin\Factory IO.exe",
]


def find_factoryio_exe() -> Path | None:
    # Non-standard install location (other drive, portable) → set FACTORYIO_EXE
    env = os.environ.get("FACTORYIO_EXE", "")
    if env and Path(env).is_file():
        return Path(env)
    for c in _DEFAULT_EXE_CANDIDATES:
        p = Path(c)
        if p.is_file():
            return p
    # search via PATH
    pf = os.environ.get("PATH", "")
    for d in pf.split(os.pathsep):
        try:
            cand = Path(d) / "Factory IO.exe"
            if cand.is_file():
                return cand
        except Exception:
            pass
    return None


class FactoryIoLauncherBridge(BridgeBase):
    bridge_id = "factoryio_launcher"
    display_name = "Factory I/O Launcher"
    category = "factoryio"

    def __init__(self, settings, on_status=None):
        super().__init__(settings, on_status)
        self._exe: Path | None = None
        self._proc: subprocess.Popen | None = None

    # -- detect -----------------------------------------------------------
    def detect(self) -> BridgeStatus:
        # Manual path provided?
        cfg = self.settings.get("bridges", {}).get("factoryio", {})
        manual = cfg.get("exe_path", "")
        if manual:
            p = Path(manual)
            if p.is_file():
                self._exe = p
                return BridgeStatus.READY
            self.remember_error(f"Factory I/O exe path invalid: {manual}")
            return BridgeStatus.NOT_CONFIGURED

        p = find_factoryio_exe()
        if p is None:
            return BridgeStatus.NOT_INSTALLED
        self._exe = p
        return BridgeStatus.READY

    # -- main action ------------------------------------------------------
    def launch_scene(
        self,
        scene_path: Optional[Path] = None,
        wait: bool = False,
    ) -> BridgeResult:
        """Launch Factory I/O and load the scene.

        If scene_path is None, only Factory I/O is opened.
        """
        result = BridgeResult(success=False)

        if not self.is_enabled():
            result.message = f"{self.display_name} toggle is OFF."
            return result

        if self.detect() != BridgeStatus.READY:
            result.message = "Factory I/O not found. Set the exe path in settings."
            return result

        cmd: list[str] = [str(self._exe)]
        if scene_path:
            sp = Path(scene_path)
            if not sp.is_file():
                result.message = f"Scene file not found: {sp}"
                return result
            cmd.append(str(sp))
            result.artifacts.append(sp)

        self.status(f"Starting Factory I/O: {' '.join(cmd)}", "info")

        try:
            # CREATE_NO_WINDOW avoids opening a cmd window on Windows
            flags = 0
            if sys.platform == "win32":
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._proc = subprocess.Popen(
                cmd, creationflags=flags,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            result.message = f"Could not start: {e}"
            self.remember_error(str(e))
            return result

        if wait:
            try:
                rc = self._proc.wait()
                result.details.append(f"Factory I/O exited (code={rc}).")
            except Exception as e:
                result.warnings.append(f"Wait error: {e}")

        cfg = self.settings.get("bridges", {}).get("factoryio", {})
        host = cfg.get("plcsim_host", "127.0.0.1")
        slot = cfg.get("plcsim_slot", 1)
        result.details.append(
            f"Expected PLCSIM connection: {host}:slot {slot} "
            "(verify in Factory I/O > File > Drivers > S7-PLCSIM)"
        )
        result.message = "Factory I/O started."
        result.success = True
        return result

    def terminate(self) -> bool:
        if self._proc is None:
            return False
        try:
            self._proc.terminate()
            return True
        except Exception:
            return False


def main():
    import argparse
    p = argparse.ArgumentParser(description="Factory I/O launcher")
    p.add_argument("--scene", help="Path to scene .factoryio")
    p.add_argument("--wait", action="store_true", help="Wait until Factory I/O closes")
    args = p.parse_args()

    # Stand-alone test: build the settings dict by hand
    settings = {
        "bridges": {
            "enabled": {"factoryio_launcher": True},
            "factoryio": {"exe_path": "", "plcsim_host": "127.0.0.1", "plcsim_slot": 1},
        }
    }
    bridge = FactoryIoLauncherBridge(settings)
    st = bridge.detect()
    print(f"Status: {st.value}")
    if st != BridgeStatus.READY:
        return
    res = bridge.launch_scene(Path(args.scene) if args.scene else None, wait=args.wait)
    print(f"Result: {res.message}")
    for d in res.details:
        print(f"  - {d}")
    for w in res.warnings:
        print(f"  ! {w}")


if __name__ == "__main__":
    main()
