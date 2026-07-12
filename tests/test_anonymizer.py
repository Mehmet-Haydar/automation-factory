"""Tests for anonymizer.py — project-aware text anonymizer."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "05_SCRIPTS"))

from anonymizer import (
    build_anon_map,
    anonymize_text,
    deanonymize_text,
    anon_map_hash,
    build_anon_map_from_file,
)


STATE = {
    "customer":     "Bosch GmbH",
    "project_name": "CustomerA_Conveyor_2026",
    "project_id":   "BSH-2026-001",
    "username":     "Hans Becker",
}


def test_build_anon_map_keys():
    m = build_anon_map(STATE)
    assert "Bosch GmbH" in m
    assert "BSH-2026-001" in m
    assert "Hans Becker" in m
    assert m["Bosch GmbH"] == "CUSTOMER_A"
    assert m["BSH-2026-001"] == "PRJ-001"


def test_short_values_excluded():
    m = build_anon_map({"customer": "AB", "project_id": "X", "project_name": "MyProject"})
    assert "AB" not in m
    assert "X" not in m
    assert "MyProject" in m


def test_anonymize_replaces_known():
    m = build_anon_map(STATE)
    text = "Project CustomerA_Conveyor_2026 for Bosch GmbH — ref BSH-2026-001"
    anon, replaced = anonymize_text(text, m)
    assert "Bosch GmbH" not in anon
    assert "BSH-2026-001" not in anon
    assert "CUSTOMER_A" in anon
    assert "PRJ-001" in anon
    assert len(replaced) >= 2


def test_anonymize_no_change_when_map_empty():
    text = "No sensitive data here"
    anon, replaced = anonymize_text(text, {})
    assert anon == text
    assert replaced == []


def test_deanonymize_restores():
    m = build_anon_map(STATE)
    text = "Project CustomerA_Conveyor_2026 for Bosch GmbH"
    anon, _ = anonymize_text(text, m)
    restored = deanonymize_text(anon, m)
    assert "Bosch GmbH" in restored
    assert "CustomerA_Conveyor_2026" in restored


def test_email_redacted():
    m = {}
    text = "Contact: hans.becker@bosch.com for details"
    anon, replaced = anonymize_text(text, m)
    assert "hans.becker@bosch.com" not in anon
    assert "EMAIL_REDACTED" in anon


def test_phone_redacted():
    m = {}
    text = "Tel: +49 711 1234567"
    anon, _ = anonymize_text(text, m)
    assert "+49 711 1234567" not in anon
    assert "PHONE_REDACTED" in anon


def test_anon_map_hash_stable():
    m = build_anon_map(STATE)
    h1 = anon_map_hash(m)
    h2 = anon_map_hash(m)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_anon_map_hash_different_maps():
    m1 = build_anon_map(STATE)
    m2 = build_anon_map({**STATE, "customer": "Siemens AG"})
    assert anon_map_hash(m1) != anon_map_hash(m2)


def test_build_anon_map_from_file(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(STATE), encoding="utf-8"
    )
    m = build_anon_map_from_file(tmp_path)
    assert "Bosch GmbH" in m


def test_build_anon_map_from_file_missing(tmp_path):
    m = build_anon_map_from_file(tmp_path)
    assert m == {}


def test_longest_match_first():
    """Longer values should be replaced before shorter substrings."""
    state = {"customer": "Bosch GmbH Automotive", "project_name": "Bosch"}
    m = build_anon_map(state)
    text = "Bosch GmbH Automotive is the customer."
    anon, _ = anonymize_text(text, m)
    assert "Bosch GmbH Automotive" not in anon
