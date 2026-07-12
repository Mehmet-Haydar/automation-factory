"""
Bridge base class and shared data types.

Every concrete bridge (TIA V19, TIA V20, Factory I/O launcher, etc.) inherits
from this class. detect() / is_enabled() are mandatory; main action methods
are bridge-specific (e.g. import_scl, launch_scene, parse_csv).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


class BridgeStatus(Enum):
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"   # target tool (TIA, Factory I/O) not on machine
    NOT_CONFIGURED = "not_configured" # tool exists but path/license missing
    READY = "ready"                   # can connect, can launch
    BUSY = "busy"                     # currently running an operation
    ERROR = "error"                   # last operation returned an error
    DISABLED = "disabled"             # toggle disabled by user


@dataclass
class BridgeResult:
    """Result of a bridge action."""
    success: bool
    message: str = ""
    details: list[str] = field(default_factory=list)
    artifacts: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Structured compile errors: [{"block": str, "severity": str, "text": str}]
    # — plain dicts, never pythonnet objects, so they survive JSON transport.
    compile_errors: list[dict] = field(default_factory=list)


# Status callback: (message, level) — level: info|ok|warn|error
StatusCallback = Callable[[str, str], None]

# Step callback: (step_id, status, info) — status: running|ok|warn|fail|skip
StepCallback = Callable[[str, str, str], None]


class BridgeBase(ABC):
    """Base class for all bridges."""

    bridge_id: str = ""        # unique short id, e.g. "tia_v20"
    display_name: str = ""     # user-facing name
    category: str = ""         # "tia" | "factoryio" | "codesys" etc.

    def __init__(self, settings: dict, on_status: Optional[StatusCallback] = None):
        self.settings = settings
        self._on_status = on_status
        self._on_step: Optional[StepCallback] = None
        self._last_error: str = ""

    # -- mandatory --------------------------------------------------------
    @abstractmethod
    def detect(self) -> BridgeStatus:
        """Probe whether the target tool is installed/accessible."""

    def is_enabled(self) -> bool:
        """Looks at the toggle in settings — default False."""
        return bool(
            self.settings.get("bridges", {})
                         .get("enabled", {})
                         .get(self.bridge_id, False)
        )

    # -- helpers ----------------------------------------------------------
    def status(self, msg: str, level: str = "info") -> None:
        if self._on_status:
            try:
                self._on_status(msg, level)
            except Exception:
                pass

    def step(self, step_id: str, status: str, info: str = "") -> None:
        """Report a phase transition (portal/import_scl/compile/...) to the
        GUI's live step view. status: running|ok|warn|fail|skip."""
        if self._on_step:
            try:
                self._on_step(step_id, status, info)
            except Exception:
                pass

    def remember_error(self, msg: str) -> None:
        self._last_error = msg

    @property
    def last_error(self) -> str:
        return self._last_error

    def describe(self) -> str:
        """Short bridge description — for GUI tooltips."""
        return self.display_name or self.bridge_id
