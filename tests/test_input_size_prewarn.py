"""Proof tests — B-02: oversize legacy input pre-warning.

Field-audit finding: the whole _raw/legacy_code/ concat goes into a SINGLE
prompt. A 200-block S7 project overflows the model context; the provider
errors out or silently drops the tail → RD01 IO list is incomplete and gets
approved unnoticed. The fix warns with real numbers BEFORE tokens are spent
and surfaces the size in the polling status for the GUI badge.
"""
from __future__ import annotations

import time

import factory_web as fw


# ---------------------------------------------------------------------------
# 1. Threshold logic
# ---------------------------------------------------------------------------

def test_small_input_no_warning():
    assert fw.Api._input_size_warning(10_000) is None


def test_soft_limit_warns_with_numbers():
    n = fw.Api._INPUT_SOFT_LIMIT_CHARS + 1
    msg = fw.Api._input_size_warning(n)
    assert msg is not None
    assert f"{n:,}" in msg, "Uyarı gerçek karakter sayısını içermiyor"
    assert "tokens" in msg
    # Soft: actionable advice, not a death sentence
    assert "Cross-check" in msg or "split" in msg.lower()


def test_hard_limit_says_will_be_incomplete():
    msg = fw.Api._input_size_warning(fw.Api._INPUT_HARD_LIMIT_CHARS + 1)
    assert msg is not None
    assert "WILL be incomplete" in msg, (
        "Hard limit aşımında kesin dille eksik-analiz uyarısı verilmeli"
    )
    assert "Split the sources" in msg


def test_thresholds_are_sane():
    # soft < hard, and soft is high enough not to nag on normal projects
    assert fw.Api._INPUT_SOFT_LIMIT_CHARS < fw.Api._INPUT_HARD_LIMIT_CHARS
    assert fw.Api._INPUT_SOFT_LIMIT_CHARS >= 100_000


# ---------------------------------------------------------------------------
# 2. Status plumbing — GUI badge reads these fields while the job runs
# ---------------------------------------------------------------------------

def test_preanalysis_status_exposes_input_size():
    api = fw.Api()
    api._preanalysis_job = {
        "running": True, "done": False, "ok": None, "msg": "",
        "lines": [], "current_step": "Step 1", "drafts": [], "warnings": [],
        "started_at": time.time(),
        "input_chars": 480_000, "input_est_tokens": 120_000,
    }
    st = api.get_preanalysis_status()
    assert st["input_chars"] == 480_000
    assert st["input_est_tokens"] == 120_000


def test_preanalysis_status_defaults_for_legacy_jobs():
    """Older job dicts (no size keys) must not break the poll endpoint."""
    api = fw.Api()
    api._preanalysis_job = {
        "running": True, "done": False, "ok": None, "msg": "",
        "lines": [], "current_step": "", "drafts": [], "warnings": [],
        "started_at": time.time(),
    }
    st = api.get_preanalysis_status()
    assert st["input_chars"] == 0
    assert st["input_est_tokens"] == 0
