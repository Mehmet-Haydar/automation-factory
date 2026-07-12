"""
TIA Portal V21 Openness bridge.

Same structure as V19/V20; only the version constants differ. The Openness
calls we use (open project, import external source, compile, save) have
been API-stable since V16 — but V21 is the newest release, so treat the
first import+compile on a real machine as the acceptance test.
"""

from __future__ import annotations

from .v19 import TiaV19Bridge


class TiaV21Bridge(TiaV19Bridge):
    bridge_id = "tia_v21"
    display_name = "TIA Portal V21 (Openness)"
    _TARGET_VERSION = "V21"
    _PROJECT_EXT = ".ap21"
