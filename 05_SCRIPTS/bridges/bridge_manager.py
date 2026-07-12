"""
Bridge manager — bridge registration, toggle management, settings integration.

The GUI uses this class as the single entry point:
  mgr = BridgeManager(self.settings, on_status=self._toast)
  for b in mgr.list_bridges():
      st = b.detect()
      ...
"""

from __future__ import annotations

import importlib
from typing import Optional

from .base import BridgeBase, BridgeStatus, StatusCallback


# For each bridge (module_path, class_name) — lazy imported
# The bridges package is found via 05_SCRIPTS on sys.path
BRIDGE_REGISTRY: list[tuple[str, str]] = [
    ("bridges.tia.v21",                    "TiaV21Bridge"),
    ("bridges.tia.v20",                    "TiaV20Bridge"),
    ("bridges.tia.v19",                    "TiaV19Bridge"),
    ("bridges.factoryio.launcher",         "FactoryIoLauncherBridge"),
    ("bridges.factoryio.scene_importer",   "FactoryIoSceneImporterBridge"),
]


DEFAULT_BRIDGE_SETTINGS = {
    "enabled": {
        "tia_v19": False,
        "tia_v20": False,
        "tia_v21": False,
        "factoryio_launcher": False,
        "factoryio_scene_importer": False,
    },
    "tia": {
        # Openness Windows group check enabled
        "openness_user_check": True,
        # Auto-compile after SCL import
        "auto_compile_after_import": True,
        # RD05 — never touch F-blocks automatically
        "skip_safety_blocks": True,
        # Never auto-download to a real PLC
        "plcsim_only": True,
        # PLCSIM Advanced info (for download)
        "plcsim_instance_name": "PLCSIM_AF",
        "plcsim_cpu_type": "1518-4 PN/DP",
        # Manual override DLL path (if auto-detect fails)
        "tia_v19_dll_path": "",
        "tia_v20_dll_path": "",
        "tia_v21_dll_path": "",
        # PLC name to import into (device name in the TIA project)
        "default_plc_name": "PLC_1",
        # Send-to-TIA modal: structured live step view (off = raw log only)
        "live_progress": True,
        # Compile-error assistance: off | hints | suggest | auto_propose.
        # No mode ever applies a fix without engineer approval.
        "fix_assist_mode": "hints",
    },
    "factoryio": {
        # Manual path if auto-detect fails
        "exe_path": "",
        # Scene folder
        "default_scene_dir": "",
        # PLCSIM Advanced connection
        "plcsim_host": "127.0.0.1",
        "plcsim_slot": 1,
        # Auto-launch Factory I/O after successful compile
        "auto_launch_on_compile": False,
        # Scene tag CSV import — enrich RD01
        "enrich_rd01_on_import": True,
    },
}


def ensure_bridge_settings(settings: dict) -> dict:
    """Builds the settings['bridges'] structure and fills in missing keys."""
    if "bridges" not in settings or not isinstance(settings.get("bridges"), dict):
        settings["bridges"] = {}
    _deep_merge_defaults(DEFAULT_BRIDGE_SETTINGS, settings["bridges"])
    return settings


def _deep_merge_defaults(src: dict, dst: dict) -> None:
    for k, v in src.items():
        if isinstance(v, dict):
            if not isinstance(dst.get(k), dict):
                dst[k] = {}
            _deep_merge_defaults(v, dst[k])
        else:
            dst.setdefault(k, v)


class BridgeManager:
    """Bridge registration and toggle management."""

    def __init__(self, settings: dict, on_status: Optional[StatusCallback] = None):
        ensure_bridge_settings(settings)
        self.settings = settings
        self._on_status = on_status
        self._cache: dict[str, BridgeBase] = {}
        self._load_errors: dict[str, str] = {}  # bridge_id -> error message

    # -- list / access ----------------------------------------------------
    def list_bridges(self) -> list[BridgeBase]:
        out: list[BridgeBase] = []
        for mod_path, cls_name in BRIDGE_REGISTRY:
            inst = self._load_one(mod_path, cls_name)
            if inst is not None:
                out.append(inst)
        return out

    def get(self, bridge_id: str) -> Optional[BridgeBase]:
        for b in self.list_bridges():
            if b.bridge_id == bridge_id:
                return b
        return None

    def _load_one(self, mod_path: str, cls_name: str) -> Optional[BridgeBase]:
        cache_key = f"{mod_path}.{cls_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            inst = cls(self.settings, self._on_status)
        except Exception as e:
            self._load_errors[cache_key] = f"{type(e).__name__}: {e}"
            return None
        self._cache[cache_key] = inst
        return inst

    def load_errors(self) -> dict[str, str]:
        return dict(self._load_errors)

    # -- toggle -----------------------------------------------------------
    def set_enabled(self, bridge_id: str, enabled: bool) -> None:
        ensure_bridge_settings(self.settings)
        self.settings["bridges"]["enabled"][bridge_id] = bool(enabled)

    def is_enabled(self, bridge_id: str) -> bool:
        return bool(
            self.settings.get("bridges", {})
                         .get("enabled", {}).get(bridge_id, False)
        )

    # -- settings access --------------------------------------------------
    def tia_settings(self) -> dict:
        ensure_bridge_settings(self.settings)
        return self.settings["bridges"]["tia"]

    def factoryio_settings(self) -> dict:
        ensure_bridge_settings(self.settings)
        return self.settings["bridges"]["factoryio"]
