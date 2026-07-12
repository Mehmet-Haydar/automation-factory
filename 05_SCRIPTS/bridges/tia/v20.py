"""
TIA Portal V20 Openness bridge.

Same structure as V19; only the version constants differ.
"""

from __future__ import annotations

from .v19 import TiaV19Bridge


class TiaV20Bridge(TiaV19Bridge):
    bridge_id = "tia_v20"
    display_name = "TIA Portal V20 (Openness)"
    _TARGET_VERSION = "V20"
    _PROJECT_EXT = ".ap20"
