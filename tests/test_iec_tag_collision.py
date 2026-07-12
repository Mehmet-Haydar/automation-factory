"""Proof tests — IEC tag 24-char truncation collisions (E2E #2, F1).

E2E #2 (mixer-line test machine): two different long German names truncated to the same
24 chars and the table ended up with DI_UEBERLASTFOERDERSCHNE twice.
Contract now: every issued tag is unique table-wide, <= 24 chars, and
colliding names are disambiguated from the UNTRUNCATED name (stable hash),
so re-running the generator yields the same tags. result.duplicates keeps
reporting the colliding base for the GUI "Duplicates:" line.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from iec_tag_generator import generate_tags  # noqa: E402


def _sig(name, typ="DI", addr="E 0.0"):
    return {"name": name, "type": typ, "address": addr, "desc": "",
            "equipment": "", "oldtag": "", "srcmodule": "", "raw": f"| {name} |"}


def test_long_names_truncating_alike_stay_distinct():
    a = _sig("Ueberlastfoerderschneckenantrieb links")
    b = _sig("Ueberlastfoerderschneckenantrieb rechts")
    res = generate_tags([a, b])
    tags = [t.tag_name for t in res.tags]
    assert len(set(tags)) == 2, f"duplicate tag issued: {tags}"
    assert all(len(t) <= 24 for t in tags)
    assert res.duplicates == ["DI_UEBERLASTFOERDERSCHNE"], \
        "GUI 'Duplicates:' report must keep naming the colliding base"


def test_disambiguation_is_stable_across_runs():
    sigs = [_sig("Ueberlastfoerderschneckenantrieb links"),
            _sig("Ueberlastfoerderschneckenantrieb rechts")]
    first = [t.tag_name for t in generate_tags(sigs).tags]
    second = [t.tag_name for t in generate_tags(sigs).tags]
    assert first == second, "hash suffix must be deterministic (regen-proof)"


def test_identical_names_three_times_all_unique():
    sigs = [_sig("Ueberlastfoerderschneckenantrieb links")] * 3
    res = generate_tags(sigs)
    tags = [t.tag_name for t in res.tags]
    assert len(set(tags)) == 3, f"identical names must still be unique: {tags}"
    assert all(len(t) <= 24 for t in tags)


def test_adversarial_batch_table_wide_unique():
    """Many near-identical long names + short names — no pair may collide."""
    base = "Ueberlastfoerderschneckenantrieb"
    sigs = [_sig(f"{base} {suffix}") for suffix in
            ("A", "B", "C", "links", "rechts", "oben", "unten")]
    sigs += [_sig("Motor ein"), _sig("Motor ein")]          # true duplicate
    res = generate_tags(sigs)
    tags = [t.tag_name for t in res.tags]
    assert len(set(tags)) == len(tags), f"collision in: {tags}"
    assert all(len(t) <= 24 for t in tags)


def test_short_names_unchanged():
    res = generate_tags([_sig("Motor ein"), _sig("Pumpe aus", typ="DQ")])
    assert [t.tag_name for t in res.tags] == ["DI_MOTOR_EIN", "DQ_PUMPE_AUS"]
    assert res.duplicates == []
