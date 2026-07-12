"""
safety_utils.py — Central F-CPU detection helper (R-S-1 fix)

All F-CPU detection goes through this module; inline patterns are not copied.

Siemens F-CPU naming conventions (IEC 62061 / EN ISO 13849 context):
  - "CPU 1515F-2 PN"   -> dash+F (middle)
  - "CPU 1518F"        -> trailing F (word boundary)
  - "CPU 1516pro F"    -> space+F (end of line)
  - "CPU 317F-2"       -> dash+F (middle)
  - "CPU 1515TF-2 PN"  -> TF (Technology+Fail-safe)
  - "SF..." prefix     -> S7-300 family SF CPUs

Fail-safe default:
  None / empty string → False (assume non-safety).
  Unknown format → False (stay on the conservative side; hardware_sizer
  already raises SafetyMisconfigurationError when strict_safety=True).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Regex explanation (Siemens naming conventions):
#   (?i)             — case-insensitive
#   \bSF\b           — "SF" whole word (CPU SF... or SF in the middle)
#   ^SF              — SF prefix at string start (SF314C-2 PN/DP family)
#   \bTF\b           — "TF" whole word (e.g. CPU 1515TF-2 PN)
#   \dF[-\s/]        — F after a digit + separator (1515F-2, 317F-2, 1516F-3)
#   \dF$             — F after a digit at line/string end (CPU 1518F)
#   \dTF[-\s/]       — TF after a digit + separator (1515TF-2 PN)
#   \dTF$            — TF after a digit at line end (CPU 1515TF)
#   [-\s]F[-\s]      — F surrounded by dash/space (middle position)
#   [-\s]F$          — F at the end after a dash/space (CPU 1516pro F)
# ---------------------------------------------------------------------------
_F_CPU_RE = re.compile(
    r"(?i)(\bSF\b|^SF|\bTF\b|\dF[-\s/]|\dF$|\dTF[-\s/]|\dTF$|[-\s]F[-\s]|[-\s]F$)",
)


def is_f_cpu(cpu_model: str | None) -> bool:
    """Return whether the given CPU model name is a Siemens F-CPU (Failsafe/Safety).

    Parameters
    ----------
    cpu_model:
        The "target_cpu" field from PROJECT_STATE or an RD01 source string.
        None or empty string → **False** (fail-safe; assume non-safety).

    Returns
    -------
    bool
        True  → F-CPU (failsafe/safety CPU — F-FB/F-DB required).
        False → Standard CPU or unknown (assume non-safety).
    """
    if not cpu_model:
        return False
    return bool(_F_CPU_RE.search(cpu_model))
