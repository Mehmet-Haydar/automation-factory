"""file_actions.py — Discover the actions that fit the selected file.

The Workbench right panel renders a small set of dynamic buttons based on
what is open. A .scl in the editor exposes "Send to TIA Portal" and
"Generate Unit Test"; an RD01_IO.md exposes "Validate IO"; an input
source XML exposes "Parse Source"; and so on. Static gate buttons are
gone — every action here is grounded in the file the user is touching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional


def _name(p: Optional[Path]) -> str:
    return p.name if p else ""


def _is_md_with_tag(p: Optional[Path], tag: str) -> bool:
    return bool(p and p.suffix.lower() == ".md" and tag.upper() in p.name.upper())


def _is_under(p: Optional[Path], folder_name: str) -> bool:
    if not p:
        return False
    return any(part.lower() == folder_name.lower() for part in p.parts)


# (label, action_id, predicate). Predicates take the selected Path and
# return True when the action applies. Order = display order.
FILE_ACTIONS: list[tuple[str, str, Callable[[Optional[Path]], bool]]] = [
    ("📊 Validate IO",         "validate_io",
        lambda p: _is_md_with_tag(p, "RD01")),
    ("✅ Validate RD",         "validate_rd",
        lambda p: bool(p and p.suffix.lower() == ".md"
                       and any(t in p.name.upper() for t in
                               ("RD01", "RD02", "RD03", "RD04", "RD05",
                                "RD06", "RD07", "RD08", "RD09", "RD10",
                                "RD11", "RD12", "RD13", "RD14")))),
    ("🔌 Send to TIA Portal",  "send_to_tia",
        lambda p: bool(p and p.suffix.lower() == ".scl")),
    ("🧪 Generate Unit Test",  "gen_unit_test",
        lambda p: bool(p and p.suffix.lower() == ".scl")),
    ("📋 Generate FAT",        "gen_fat",
        lambda p: _is_md_with_tag(p, "RD12")),
    ("🔍 Parse Source",        "parse_source",
        lambda p: bool(p and (p.suffix.lower() in (".xml", ".l5x", ".awl", ".st", ".s7p")
                              or _is_under(p, "_input")))),
    ("📈 Open in Excel",       "open_in_excel",
        lambda p: bool(p and p.suffix.lower() in (".xlsx", ".csv"))),
]


def actions_for(file_path: Optional[Path]) -> list[tuple[str, str]]:
    """Return the (label, action_id) pairs that apply to ``file_path``."""
    return [
        (label, action_id)
        for (label, action_id, predicate) in FILE_ACTIONS
        if predicate(file_path)
    ]
