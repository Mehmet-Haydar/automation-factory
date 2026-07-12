"""
AUTOMATION_FACTORY bridges package (Phase 37).

A "bridge" connects AUTOMATION_FACTORY to an external automation tool
(TIA Portal, Factory I/O, CODESYS, etc.). Generated SCL or scene
configuration goes directly to the target instead of manual copy-paste.

All bridges:
  - **OPTIONAL** — opened via toggle through bridge_manager.py
  - **DISABLED BY DEFAULT** — when toggle is OFF, the existing flow is unchanged
  - **LAZY IMPORT** — if a dependency is missing, the GUI is not broken;
    only that bridge becomes "not_installed"

Architecture:
  bridges/base.py             — Abstract BridgeBase + BridgeStatus + BridgeResult
  bridges/bridge_manager.py   — Bridge registration + toggle + settings management
  bridges/tia/                — TIA Portal V19 / V20 Openness bridges
  bridges/factoryio/          — Factory I/O launcher + scene importer

Safety rules:
  - F-blocks (Safety / RD05) are never auto-written/downloaded by any bridge
  - NO automatic download to a real PLC — PLCSIM Advanced only
  - All destructive operations require user confirmation
"""

__version__ = "0.1.0"
