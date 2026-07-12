"""Proof tests for plc_validation.py (PLAN_PLC_VALIDATION increment 1).

Covers the offline orchestration that the whole gate hangs off:
- L1 empty = loud FAIL (no silent pass); L1/L2 pass on a real library block.
- hash cache (K9): skip unchanged, re-validate on change, never cache failures.
- safety detection (K1 input): F_-prefix → safety.
- auto-fix loop (K6): success, no-progress stop, max-attempts cap, and the
  hard rule that safety-critical code is never auto-fixed.
- engineer actions (K6): QUARANTINE, named override (anonymous refused),
  safety-override carries the strongest warning.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
_KB = _ROOT / "06_KNOWLEDGE_BASE"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import plc_validation as pv

_BLOCK = _KB / "blocks" / "motor" / "FB_Motor_DOL.scl"
_CONTRACT = _KB / "contracts" / "motor" / "FB_Motor_DOL.contract.json"


# ── L1 / L2 layers (real components) ────────────────────────────────────

def test_l1_empty_is_loud_fail():
    r = pv.run_l1("")
    assert r.ok is False
    assert r.errors and "empty" in r.errors[0].lower()


def test_l1_passes_real_library_block():
    r = pv.run_l1(_BLOCK.read_text(encoding="utf-8"))
    assert r.ok is True, r.errors


def test_l1_real_invalid_scl_returns_errors_not_crash():
    # Regression for F-01: error_lines() must be CALLED. A non-empty invalid
    # block exercises the error branch that the earlier tests never hit.
    r = pv.run_l1("FUNCTION_BLOCK X\n VAR a : Bool\n garbage !!! no end")
    assert r.ok is False
    assert r.errors and all(isinstance(e, str) for e in r.errors)


def test_validate_artifact_missing_contract_is_failed_not_crash(tmp_path):
    # Regression for F-03: a missing/bad contract is a FAILED layer, not a raw
    # exception.
    av = pv.validate_artifact(
        "blk",
        content="FUNCTION_BLOCK X\nEND_FUNCTION_BLOCK\n",
        contract_path=tmp_path / "does_not_exist.json")
    assert av.status is pv.Status.FAILED
    assert any(lr.layer is pv.Layer.L2_CONTRACT and not lr.ok for lr in av.layers)


def test_validate_artifact_passes_real_block_and_contract():
    av = pv.validate_artifact("FB_Motor_DOL", scl_path=_BLOCK, contract_path=_CONTRACT)
    assert av.status is pv.Status.PASSED, av.all_errors
    assert {lr.layer for lr in av.layers} >= {pv.Layer.L1_STATIC, pv.Layer.L2_CONTRACT}


def test_validate_artifact_needs_content_or_path():
    with pytest.raises(ValueError):
        pv.validate_artifact("x")


# ── cache (K9) ──────────────────────────────────────────────────────────

def test_cache_skips_unchanged():
    cache = pv.ValidationCache()
    a = pv.validate_artifact("blk", scl_path=_BLOCK, contract_path=_CONTRACT, cache=cache)
    assert a.status is pv.Status.PASSED
    b = pv.validate_artifact("blk", scl_path=_BLOCK, contract_path=_CONTRACT, cache=cache)
    assert b.status is pv.Status.SKIPPED_CACHED
    assert b.ok is True


def test_cache_revalidates_on_change():
    cache = pv.ValidationCache()
    good = _BLOCK.read_text(encoding="utf-8")
    a = pv.validate_artifact("blk", content=good, cache=cache)
    assert a.status is pv.Status.PASSED
    b = pv.validate_artifact("blk", content=good + "\n// changed", cache=cache)
    assert b.status is not pv.Status.SKIPPED_CACHED              # hash changed → re-validated


def test_cache_does_not_store_failures():
    cache = pv.ValidationCache()
    pv.validate_artifact("blk", content="", cache=cache)         # empty → FAIL
    assert cache.get("blk", pv.content_hash("")) is None


# ── safety detection (K1 input) ─────────────────────────────────────────

def test_safety_detection_f_prefix(tmp_path):
    f = tmp_path / "F_EStop.scl"
    f.write_text("FUNCTION_BLOCK F_EStop\nEND_FUNCTION_BLOCK\n", encoding="utf-8")
    assert pv.detect_safety(f, None) is True


def test_safety_detection_standard_block():
    assert pv.detect_safety(_BLOCK, _BLOCK.read_text(encoding="utf-8")) is False


# ── auto-fix loop (K6) — deterministic via injected fixer ───────────────

def test_autofix_success():
    good = _BLOCK.read_text(encoding="utf-8")
    calls = {"n": 0}

    def fixer(_content, _errors):
        calls["n"] += 1
        return good

    av = pv.validate_with_autofix("blk", content="", fixer=fixer)
    assert av.status is pv.Status.PASSED
    assert av.fix_attempts == 1 and calls["n"] == 1


def test_autofix_no_progress_stops():
    # A fixer that keeps returning the SAME failing content → identical error
    # signature → stop early (K6 no-progress), don't burn all attempts.
    bad = "FUNCTION_BLOCK X\n VAR a : Bool\n garbage !!! no end"
    av = pv.validate_with_autofix("blk", content="", fixer=lambda c, e: bad)
    assert av.status is pv.Status.FAILED
    assert av.fix_attempts == 2
    assert any("no progress" in n.lower() for n in av.notes)


def test_autofix_fixer_exception_is_handled():
    # F-04: an LLM/network failure in the fixer must not crash the gate.
    def boom(_c, _e):
        raise RuntimeError("network timeout")
    av = pv.validate_with_autofix("blk", content="", fixer=boom)
    assert av.status is pv.Status.FAILED
    assert any("fixer failed" in n.lower() for n in av.notes)


def test_autofix_fixer_none_is_handled():
    # F-04: a fixer that yields nothing usable must not crash.
    av = pv.validate_with_autofix("blk", content="", fixer=lambda c, e: None)
    assert av.status is pv.Status.FAILED
    assert any("nothing usable" in n.lower() for n in av.notes)


def test_autofix_stops_if_content_becomes_safety(monkeypatch):
    # F-05 / K1 fail-closed: if a fix turns the artifact into safety-classified
    # content, auto-fix must stop (named engineer required).
    seq = {"n": 0}

    def fake_detect(scl_path, content, safety_names=None):
        seq["n"] += 1
        return seq["n"] >= 2          # initial detect False; after the fix True

    monkeypatch.setattr(pv, "detect_safety", fake_detect)
    av = pv.validate_with_autofix(
        "blk", content="",
        fixer=lambda c, e: "FUNCTION_BLOCK X\nEND_FUNCTION_BLOCK\n")
    assert any("became safety" in n.lower() for n in av.notes)


def test_autofix_refused_for_safety(tmp_path):
    f = tmp_path / "F_EStop.scl"
    f.write_text("", encoding="utf-8")          # safety name + empty → fails
    called = {"n": 0}

    def fixer(c, e):
        called["n"] += 1
        return c

    av = pv.validate_with_autofix("F_EStop", scl_path=f, fixer=fixer)
    assert av.is_safety is True
    assert av.status is pv.Status.FAILED
    assert called["n"] == 0                      # K1: never auto-fixed
    assert any("safety" in n.lower() for n in av.notes)


def test_autofix_respects_max_attempts(monkeypatch):
    # Isolate the loop control from code_verifier: each call fails with a NEW
    # error signature, so no-progress never triggers and the cap must.
    seq = {"n": 0}

    def fake_l1(content):
        seq["n"] += 1
        return pv.LayerResult(pv.Layer.L1_STATIC, ok=False,
                              errors=[f"err-{seq['n']}"])

    monkeypatch.setattr(pv, "run_l1", fake_l1)
    monkeypatch.setattr(pv, "detect_safety", lambda *a, **k: False)
    av = pv.validate_with_autofix("blk", content="start",
                                  fixer=lambda c, e: c + "x", max_attempts=3)
    assert av.status is pv.Status.FAILED
    assert av.fix_attempts == 3
    assert any("exhausted" in n.lower() for n in av.notes)


# ── engineer actions (K6) ───────────────────────────────────────────────

def test_quarantine():
    av = pv.validate_artifact("blk", content="")
    q = pv.quarantine(av)
    assert q.status is pv.Status.QUARANTINE
    assert any("quarantine" in n.lower() for n in q.notes)


def test_override_requires_named_engineer():
    av = pv.validate_artifact("blk", content="")
    with pytest.raises(ValueError):
        pv.accept_override(av, "")


def test_override_named_ok():
    av = pv.validate_artifact("blk", content="")
    o = pv.accept_override(av, "M. Haydar")
    assert o.status is pv.Status.ACCEPTED_OVERRIDE
    assert o.override_by == "M. Haydar" and o.ok is True


def test_safety_override_requires_project_path(tmp_path):
    # F-02 / K6: a safety override is refused without a project_path because the
    # AI_DECISION_LOG audit record is mandatory.
    f = tmp_path / "F_EStop.scl"
    f.write_text("", encoding="utf-8")
    av = pv.validate_artifact("F_EStop", scl_path=f)
    assert av.is_safety is True
    with pytest.raises(ValueError):
        pv.accept_override(av, "Safety Eng")          # no project_path


def test_safety_override_writes_audit_log(tmp_path):
    # F-02: the safety override must land in the project audit log.
    proj = tmp_path / "proj"
    proj.mkdir()
    f = tmp_path / "F_EStop.scl"
    f.write_text("", encoding="utf-8")
    av = pv.validate_artifact("F_EStop", scl_path=f)
    o = pv.accept_override(av, "Safety Eng", project_path=proj)
    assert o.status is pv.Status.ACCEPTED_OVERRIDE
    assert any("SAFETY OVERRIDE" in n for n in o.notes)
    from ai_decision_log import read_log
    records = read_log(proj)
    assert records and any("SAFETY-override" in r.get("step_label", "") for r in records)


# ---------------------------------------------------------------------------
# ValidationCache üçlü anahtar (contract_hash) fix (B2) — taşındı: test_cache_contract_hash.py
# ---------------------------------------------------------------------------

class TestContractHash:
    def test_none_returns_empty(self):
        """None → '' (no contract sentinel)."""
        assert pv._contract_hash(None) == ""

    def test_missing_file_returns_empty(self, tmp_path):
        """Okunamayan / yok dosya → fail-safe '' (OSError yakalanır)."""
        assert pv._contract_hash(tmp_path / "nonexistent.json") == ""

    def test_real_file_is_16_char_hex(self, tmp_path):
        """Gerçek dosya → 16 karakterli hex özet."""
        f = tmp_path / "contract.json"
        f.write_text('{"version": 1}', encoding="utf-8")
        h = pv._contract_hash(f)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_changes_when_content_changes(self, tmp_path):
        """İçerik değişince hash değişmeli."""
        f = tmp_path / "contract.json"
        f.write_text('{"version": 1}', encoding="utf-8")
        h1 = pv._contract_hash(f)
        f.write_text('{"version": 2, "extra": true}', encoding="utf-8")
        h2 = pv._contract_hash(f)
        assert h1 != h2


class TestCacheContractHash:
    """ValidationCache üçlü anahtar — contract değişince cache miss garantisi (B2)."""

    def test_prevents_stale_hit(self, tmp_path):
        """KRİTİK: Aynı SCL, FARKLI contract → cache miss (yeniden doğrulama)."""
        scl_content = _BLOCK.read_text(encoding="utf-8")
        contract_v1 = tmp_path / "contract_v1.json"
        contract_v1.write_bytes(_CONTRACT.read_bytes())

        cache = pv.ValidationCache()
        a = pv.validate_artifact(
            "FB_Motor_DOL", content=scl_content, contract_path=contract_v1, cache=cache)
        assert a.status is pv.Status.PASSED, f"İlk doğrulama başarısız: {a.all_errors}"

        contract_v2 = tmp_path / "contract_v2.json"
        contract_v2.write_text(
            '{"version": "CHANGED", "checks": [], "modified": true}', encoding="utf-8")
        b = pv.validate_artifact(
            "FB_Motor_DOL", content=scl_content, contract_path=contract_v2, cache=cache)
        assert b.status is not pv.Status.SKIPPED_CACHED, (
            "HATA: Farklı contract'a rağmen cache hit döndü — safety bug.")

    def test_hit_when_both_unchanged(self, tmp_path):
        """Aynı SCL + aynı contract → cache hit (SKIPPED_CACHED)."""
        scl_content = _BLOCK.read_text(encoding="utf-8")
        contract_copy = tmp_path / "contract.json"
        contract_copy.write_bytes(_CONTRACT.read_bytes())

        cache = pv.ValidationCache()
        a = pv.validate_artifact(
            "FB_Motor_DOL", content=scl_content, contract_path=contract_copy, cache=cache)
        assert a.status is pv.Status.PASSED
        b = pv.validate_artifact(
            "FB_Motor_DOL", content=scl_content, contract_path=contract_copy, cache=cache)
        assert b.status is pv.Status.SKIPPED_CACHED

    def test_miss_when_contract_added(self, tmp_path):
        """Önce contract'sız PASS, sonra contract eklenir → cache miss."""
        scl_content = _BLOCK.read_text(encoding="utf-8")
        cache = pv.ValidationCache()
        a = pv.validate_artifact("FB_Motor_DOL", content=scl_content, cache=cache)
        assert a.status is pv.Status.PASSED
        b = pv.validate_artifact(
            "FB_Motor_DOL", content=scl_content, contract_path=_CONTRACT, cache=cache)
        assert b.status is not pv.Status.SKIPPED_CACHED, (
            "Contract eklendi ama cache hit döndü — L2 katmanı atlanıyor (bug).")

    def test_miss_when_contract_removed(self, tmp_path):
        """Önce contract'lı PASS, sonra contract kaldırılır → cache miss."""
        scl_content = _BLOCK.read_text(encoding="utf-8")
        contract_copy = tmp_path / "contract.json"
        contract_copy.write_bytes(_CONTRACT.read_bytes())

        cache = pv.ValidationCache()
        a = pv.validate_artifact(
            "FB_Motor_DOL", content=scl_content, contract_path=contract_copy, cache=cache)
        assert a.status is pv.Status.PASSED
        b = pv.validate_artifact("FB_Motor_DOL", content=scl_content, cache=cache)
        assert b.status is not pv.Status.SKIPPED_CACHED, (
            "Contract kaldırıldı ama cache hit döndü — farklı doğrulama konfigürasyonu.")

    def test_direct_get_triple_key(self):
        """ValidationCache.get() üçlü anahtar — geriye dönük uyumlu."""
        from plc_validation import ArtifactValidation, Status, Layer, LayerResult
        cache = pv.ValidationCache()
        av = ArtifactValidation(
            name="x", content_hash="abc123", status=Status.PASSED,
            layers=[LayerResult(Layer.L1_STATIC, ok=True)])
        cache.put("x", "abc123", av, "")

        result = cache.get("x", "abc123", "")
        assert result is not None
        assert result.status is pv.Status.SKIPPED_CACHED

        result2 = cache.get("x", "abc123", "deadbeef12345678")
        assert result2 is None
