"""Proof test for factory_reader.RD_EXTRACTORS canonical alignment.

The RD04-RD13 rows were scrambled (RD13 Annotation -> MOTION prompt, etc.)
after the RD numbering was reordered without re-syncing this map. This test
locks every RD to its correct extractor prompt AND verifies the prompt file
actually exists, so a future renumber that forgets this map fails CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_WORKBENCH = _ROOT / "workbench"
if str(_WORKBENCH) not in sys.path:
    sys.path.insert(0, str(_WORKBENCH))

from core.factory_reader import RD_EXTRACTORS  # noqa: E402

_PROMPTS_DIR = _ROOT / "04_AI_PROMPTS" / "analyze"

# Canonical taxonomy — must match project_analyzer.RD_INPUT_NEEDS / prompt_meta.
_EXPECTED = {
    "RD01": "PROMPT_EXTRACT_IO_FROM_CODE",
    "RD02": "PROMPT_EXTRACT_DATADICT_FROM_CODE",
    "RD03": "PROMPT_EXTRACT_FLOWCHART_FROM_CODE",
    "RD04": "PROMPT_EXTRACT_MODE_FROM_CODE",
    "RD05": "PROMPT_EXTRACT_SAFETY_FROM_CODE",
    "RD06": "PROMPT_EXTRACT_MOTION_FROM_CODE",
    "RD07": "PROMPT_EXTRACT_TIMING_FROM_CODE",
    "RD08": "PROMPT_EXTRACT_ALARM_FROM_CODE",
    "RD09": "PROMPT_EXTRACT_COMMS_FROM_CODE",
    "RD10": "PROMPT_EXTRACT_FBSPEC_FROM_CODE",
    "RD11": "PROMPT_EXTRACT_HMI_FROM_CODE",
    "RD12": "PROMPT_EXTRACT_USECASE_FROM_CODE",
    "RD13": "PROMPT_EXTRACT_ANNOTATION_FROM_CODE",
    "RD14": "PROMPT_EXTRACT_MODERNIZATION_FROM_CODE",
}


def test_mapping_matches_canonical():
    assert RD_EXTRACTORS == _EXPECTED


def test_rd13_is_annotation_not_motion():
    # Headline regression: RD13 is the Legacy Annotation, never MOTION.
    assert RD_EXTRACTORS["RD13"] == "PROMPT_EXTRACT_ANNOTATION_FROM_CODE"


def test_every_mapped_prompt_file_exists():
    for rd, name in RD_EXTRACTORS.items():
        assert (_PROMPTS_DIR / f"{name}.md").is_file(), f"{rd} -> missing {name}.md"
