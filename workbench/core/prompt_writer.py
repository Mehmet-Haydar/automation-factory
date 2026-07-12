"""prompt_writer.py — Save a user-authored prompt into the right category.

The Workbench's "+ New Prompt" dialog calls save_user_prompt() with the
category of the currently selected file. The prompt is written under
04_AI_PROMPTS/<category>/ with a PROMPT_USER_ prefix, a normalised file
name and Factory frontmatter so the result drops straight into the
prompt library on the next refresh.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .factory_reader import PROMPT_DIRS

PROMPT_FRONTMATTER = """---
title: {title_yaml}
version: 1.0.0
last_updated: {date}
status: USER_DRAFT
gate: {gate}
category: {category}
author: workbench_user
target_ai: [Claude Sonnet 4+, Claude Opus 4+]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_AI_INTERFACE.md]
---

# {title_heading}

{body}

## #UNKNOWNS

<!-- List anything the customer or engineer still needs to confirm. -->
"""


def _safe_slug(name: str) -> str:
    """Turn a free-form title into an UPPER_SNAKE filename fragment."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    cleaned = cleaned.strip("_").upper()
    return cleaned or "USER_PROMPT"


def _sanitize_title(title: str) -> str:
    """M-A4: collapse a free-form title to a single safe line.

    Newlines, leading '---', and unbalanced quotes in the title break the
    surrounding YAML frontmatter — the resulting file looks valid in the
    editor but fails to parse on the next prompt-library refresh, and the
    prompt appears to vanish. We collapse whitespace, drop YAML delimiters,
    and use YAML-quoted output so embedded quotes/colons survive.
    """
    s = (title or "").strip()
    if not s:
        return "User Prompt"
    # Collapse any whitespace (incl. \n, \r, \t) into single spaces.
    s = re.sub(r"\s+", " ", s)
    # A leading '---' on its own would terminate the frontmatter block.
    s = s.lstrip("- ").strip() or "User Prompt"
    # Cap length so a pasted essay doesn't produce a 10kB title line.
    if len(s) > 200:
        s = s[:200].rstrip() + "…"
    return s


def _yaml_quote(s: str) -> str:
    """Quote `s` as a YAML double-quoted scalar (safe for frontmatter)."""
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def save_user_prompt(
    category: str,
    title: str,
    body: str,
    gate: int = 1,
) -> Path:
    """Persist a user prompt under the matching 04_AI_PROMPTS sub-folder.

    Returns the absolute path of the new file. Raises ValueError when the
    category does not map to a known prompt directory.
    """
    target_dir: Optional[Path] = PROMPT_DIRS.get(category)
    if target_dir is None:
        # Unknown category falls back to "analyze" — same heuristic the
        # reader uses for unclassified files.
        target_dir = PROMPT_DIRS["analyze"]

    target_dir.mkdir(parents=True, exist_ok=True)

    safe_title = _sanitize_title(title)
    slug = _safe_slug(safe_title)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"PROMPT_USER_{slug}_{stamp}.md"
    path = target_dir / file_name

    content = PROMPT_FRONTMATTER.format(
        title_yaml=_yaml_quote(safe_title),
        title_heading=safe_title,
        date=datetime.now().strftime("%Y-%m-%d"),
        gate=gate,
        category=category,
        body=body.strip() or "<!-- Write your prompt content here -->",
    )
    path.write_text(content, encoding="utf-8")
    return path
