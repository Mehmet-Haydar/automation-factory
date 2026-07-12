#!/usr/bin/env python3
"""
script_openness_export.py — DEPRECATED (Phase 37)

This file was a stub and was replaced by the bridges/tia/ package in Phase 37.

New location:
  05_SCRIPTS/bridges/tia/v19.py      (TIA V19 bridge)
  05_SCRIPTS/bridges/tia/v20.py      (TIA V20 bridge)
  05_SCRIPTS/bridges/tia/openness_core.py (shared core)

CLI test:
  python -m bridges.tia.version_detect    # list installed TIA versions

GUI:
  Sidebar -> "Bridges" screen
"""

import sys


def main():
    print(__doc__)
    print()
    print("Module now lives under 'bridges.tia'. Use the 'Bridges' screen in the GUI.")
    sys.exit(0)


if __name__ == "__main__":
    main()
