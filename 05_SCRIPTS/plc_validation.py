#!/usr/bin/env python3
"""
plc_validation.py — Independent validation orchestrator for GENERATED PLC code.

Implements PLAN_PLC_VALIDATION.md, increment 1 (offline layers + control flow):
  L1 static   → code_verifier.verify
  L2 contract → fb_acceptance_check.run_gate (when a contract exists)
  K1 safety carve-out · K4 per-artifact · K6 auto-fix loop · K9 hash cache.

L3 (TIA compile) and L4 (PLCSIM behavioural) are NOT wired here — they need the
runner — but their `Layer` values and result slots already exist so the model
is stable when they land.

Independence (PLAN §4): this orchestrator runs OBJECTIVE checks (a verifier and
a contract gate) that do not care what the code generator "claims". The fixer
is INJECTED (a callback), so the thing that writes a fix is never the thing that
decides it passed — every fix attempt is re-validated by the same objective
layers.

Hard rules honoured:
  * Empty/blank artifact = LOUD FAIL (never a silent pass).
  * Safety-critical code is NEVER auto-fixed (K1); only a named engineer may
    override (K6), and the override is recorded.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ── model ─────────────────────────────────────────────────────────────────────

class Layer(str, Enum):
    L1_STATIC = "L1_static"
    L2_CONTRACT = "L2_contract"
    L3_COMPILE = "L3_compile"        # wired in a later increment (needs TIA)
    L4_BEHAVIORAL = "L4_behavioral"  # wired in a later increment (needs PLCSIM)


class Status(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    QUARANTINE = "QUARANTINE"             # engineer deferred; re-validate later
    ACCEPTED_OVERRIDE = "ACCEPTED_OVERRIDE"  # engineer took responsibility (K6)
    SKIPPED_CACHED = "SKIPPED_CACHED"     # unchanged since last PASS (K9)


@dataclass
class LayerResult:
    layer: Layer
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ArtifactValidation:
    name: str
    content_hash: str
    status: Status
    is_safety: bool = False
    layers: list[LayerResult] = field(default_factory=list)
    fix_attempts: int = 0
    fixed_content: Optional[str] = None
    override_by: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in (
            Status.PASSED, Status.SKIPPED_CACHED, Status.ACCEPTED_OVERRIDE)

    @property
    def all_errors(self) -> list[str]:
        return [e for lr in self.layers for e in lr.errors]

    def error_signature(self) -> str:
        """Stable fingerprint of the current errors — for K6 no-progress stop."""
        return content_hash("\n".join(sorted(self.all_errors)))


# ── helpers ───────────────────────────────────────────────────────────────────

def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()


def _write_temp_scl(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".scl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def detect_safety(scl_path: Optional[Path], content: Optional[str],
                  safety_names: Optional[set] = None) -> bool:
    """Authoritative safety detection (reuses the Openness fail-closed gate).

    F_-prefix, RD05-declared names, keyword/content signatures. Fail-closed:
    an unreadable file counts as safety. Never auto-fix what this flags (K1).
    """
    from bridges.tia.openness_core import _looks_like_safety  # text-only, no pythonnet
    if scl_path is not None:
        return _looks_like_safety(Path(scl_path), safety_names)
    tmp = _write_temp_scl(content or "")
    try:
        return _looks_like_safety(Path(tmp), safety_names)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── layers ────────────────────────────────────────────────────────────────────

def run_l1(content: str) -> LayerResult:
    """L1 static verification (code_verifier). Empty content = loud FAIL."""
    if not content or not content.strip():
        return LayerResult(Layer.L1_STATIC, ok=False,
                           errors=["empty artifact — no SCL content (silent pass forbidden)"])
    from code_verifier import verify
    vr = verify(content)
    # NB: error_lines is a method (not a property) — must be called.
    return LayerResult(
        Layer.L1_STATIC,
        ok=not vr.has_errors,
        errors=list(vr.error_lines()) if vr.has_errors else [],
        warnings=[f"{vr.warning_count} warning(s)"] if vr.warning_count else [],
    )


def run_l2(scl_path: Path, contract_path: Path) -> LayerResult:
    """L2 contract acceptance gate (fb_acceptance_check.run_gate)."""
    from fb_acceptance_check import run_gate
    gr = run_gate(Path(scl_path), Path(contract_path))
    errors: list[str] = []
    warnings: list[str] = []
    for c in gr.checks:
        if c.status == "FAIL":
            issues = c.issues or [c.description]
            errors.extend(f"[{c.check_id}] {i}" for i in issues)
        elif c.status == "WARN":
            warnings.extend(f"[{c.check_id}] {i}" for i in (c.issues or []))
    return LayerResult(Layer.L2_CONTRACT, ok=(gr.overall == "PASS"),
                       errors=errors, warnings=warnings)


# ── cache (K9) ──────────────────────────────────────────────────────────────────

def _contract_hash(contract_path: Optional[Path]) -> str:
    """Return a 16-char hex digest of the contract file's raw bytes.

    Fail-safe: if contract_path is None, missing, or unreadable → return "".
    An empty string means "no contract"; it is a distinct cache key segment
    from any real contract hash, so the two cases never collide.
    """
    if contract_path is None:
        return ""
    try:
        raw = Path(contract_path).read_bytes()
        return hashlib.sha256(raw).hexdigest()[:16]
    except OSError:
        return ""


class ValidationCache:
    """Content-hash + contract-hash cache: re-validates only when EITHER
    the artifact content OR the L2 contract file changes.

    Cache key is the triple (name, content_hash, contract_hash).
    contract_hash="" means "no contract was supplied" — distinct from any
    real 16-char hex digest, so a run without a contract never collides with
    a run that had one.

    Stores only PASSING results — a failure is never cached as 'skip'."""

    def __init__(self) -> None:
        self._by_name: dict[str, tuple[tuple[str, str], ArtifactValidation]] = {}

    def get(self, name: str, h: str,
            contract_hash: str = "") -> Optional[ArtifactValidation]:
        entry = self._by_name.get(name)
        if entry and entry[0] == (h, contract_hash):
            cached = entry[1]
            # Copy the mutable lists so a caller mutating the returned object
            # cannot corrupt the cached entry.
            return replace(cached, status=Status.SKIPPED_CACHED,
                           layers=list(cached.layers), notes=list(cached.notes))
        return None

    def put(self, name: str, h: str, av: ArtifactValidation,
            contract_hash: str = "") -> None:
        if av.status == Status.PASSED:
            self._by_name[name] = ((h, contract_hash), av)


# ── orchestration ───────────────────────────────────────────────────────────────

def validate_artifact(
    name: str,
    *,
    scl_path: Optional[Path] = None,
    content: Optional[str] = None,
    contract_path: Optional[Path] = None,
    safety_names: Optional[set] = None,
    cache: Optional[ValidationCache] = None,
) -> ArtifactValidation:
    """Run L1 (+ L2 when a contract is given) on one artifact, with hash cache.

    L2 runs only when L1 passes — a file that does not even parse cannot be
    meaningfully checked against a contract.
    """
    if content is None and scl_path is not None:
        content = Path(scl_path).read_text(encoding="utf-8", errors="replace")
    if content is None:
        raise ValueError("validate_artifact needs content or scl_path")

    h = content_hash(content)
    c_hash = _contract_hash(contract_path)
    if cache is not None:
        hit = cache.get(name, h, c_hash)
        if hit is not None:
            return hit

    is_safety = detect_safety(scl_path, content, safety_names)
    layers: list[LayerResult] = []

    l1 = run_l1(content)
    layers.append(l1)

    if contract_path is not None and l1.ok:
        l2_path = Path(scl_path) if scl_path is not None else Path(_write_temp_scl(content))
        try:
            layers.append(run_l2(l2_path, Path(contract_path)))
        except Exception as exc:
            # A bad/missing/corrupt contract must surface as a FAILED layer, not
            # a raw exception — the caller always expects an ArtifactValidation.
            # Log hygiene: type only, no path/message that could leak a folder.
            layers.append(LayerResult(
                Layer.L2_CONTRACT, ok=False,
                errors=[f"contract gate could not run: {type(exc).__name__}"]))
        finally:
            if scl_path is None:
                try:
                    os.unlink(l2_path)
                except OSError:
                    pass

    status = Status.PASSED if all(lr.ok for lr in layers) else Status.FAILED
    av = ArtifactValidation(name=name, content_hash=h, status=status,
                            is_safety=is_safety, layers=layers)
    if cache is not None:
        cache.put(name, h, av, c_hash)
    return av


# Fixer signature: (current_content, errors) -> fixed_content.
# Injected by the caller; the real implementation is an LLM call via
# tia_fix_assist (a later increment). Keeping it injected is what preserves
# independence: the generator/fixer never decides the verdict.
Fixer = Callable[[str, list[str]], str]


def validate_with_autofix(
    name: str,
    *,
    scl_path: Optional[Path] = None,
    content: Optional[str] = None,
    contract_path: Optional[Path] = None,
    safety_names: Optional[set] = None,
    fixer: Optional["Fixer"] = None,
    max_attempts: int = 3,
) -> ArtifactValidation:
    """K6: validate, then (for NON-safety code) try the injected fixer up to
    `max_attempts` times. Stops early when the error set stops changing
    (no-progress). Safety-critical code is NEVER auto-fixed (K1)."""
    if content is None and scl_path is not None:
        content = Path(scl_path).read_text(encoding="utf-8", errors="replace")

    av = validate_artifact(name, scl_path=scl_path, content=content,
                           contract_path=contract_path, safety_names=safety_names)
    if av.ok:
        return av

    if av.is_safety:
        av.notes.append("K1: safety-critical — auto-fix refused; named engineer required.")
        return av

    if fixer is None:
        av.notes.append("no fixer provided — engineer action required.")
        return av

    cur = content
    last_sig = av.error_signature()
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            cur = fixer(cur, av.all_errors)
        except Exception as exc:
            # An LLM/network failure in the fixer must not crash the gate.
            av.fix_attempts = attempts
            av.notes.append(
                f"fixer failed on attempt {attempts}: {type(exc).__name__} — "
                "engineer action required.")
            return av
        if cur is None or not str(cur).strip():
            av.fix_attempts = attempts
            av.notes.append(
                f"fixer returned nothing usable on attempt {attempts} — "
                "engineer action required.")
            return av
        av = validate_artifact(name, content=cur, contract_path=contract_path,
                               safety_names=safety_names)
        av.fix_attempts = attempts
        av.fixed_content = cur
        if av.is_safety:
            # K1 fail-closed: a fix turned the artifact into safety-classified
            # content — stop auto-fixing, a named engineer must take over.
            av.notes.append(
                "K1: artifact became safety-classified during fix — auto-fix stopped.")
            return av
        if av.ok:
            av.notes.append(f"auto-fixed in {attempts} attempt(s) (K6).")
            return av
        sig = av.error_signature()
        if sig == last_sig:
            av.notes.append(f"no progress after attempt {attempts} — stopping (K6).")
            break
        last_sig = sig

    av.notes.append(
        "auto-fix exhausted — engineer action required "
        "(manual fix / QUARANTINE / named override).")
    return av


# ── engineer actions on a persistent failure (K6) ───────────────────────────────

def quarantine(av: ArtifactValidation) -> ArtifactValidation:
    """Engineer defers: stamp QUARANTINE so it is fixable later and re-tested."""
    return replace(
        av, status=Status.QUARANTINE,
        notes=av.notes + ["QUARANTINE: deferred by engineer; re-validate after fix."])


def accept_override(av: ArtifactValidation, engineer: str,
                    *, project_path: Optional[Path] = None) -> ArtifactValidation:
    """Engineer takes responsibility for a still-failing artifact (K6).

    A name is mandatory (responsibility); the override is recorded. For
    safety-critical code the strongest warning is attached AND an audit-log
    record is MANDATORY — the SYSTEM never auto-passes safety; only a named
    engineer can, on the record (PLAN K6, AI_DECISION_LOG).

    `project_path` is where the audit record is written. It is required for a
    safety override (refused without it) and used when given for any override.
    """
    engineer = (engineer or "").strip()
    if not engineer:
        raise ValueError(
            "override requires a named engineer — responsibility cannot be anonymous (K6)")
    if av.is_safety and project_path is None:
        raise ValueError(
            "safety override requires project_path — the AI_DECISION_LOG audit "
            "record is mandatory for a safety-critical override (K6)")

    notes = av.notes + [
        f"ACCEPTED_OVERRIDE by {engineer} — responsibility on the engineer."]
    if av.is_safety:
        notes.append(
            "SAFETY OVERRIDE: this is a safety-critical block forced past failing "
            "validation by a named engineer. System never auto-passes safety (K1/K6).")

    if project_path is not None:
        from ai_decision_log import log_ai_action
        kind = "SAFETY-override" if av.is_safety else "override"
        log_ai_action(
            Path(project_path),
            step_label=f"PLC-validation {kind}: {av.name}"[:60],
            ai_model="-", ai_provider="-",
            output_text=(f"engineer={engineer}; safety={av.is_safety}; "
                         f"status_before={av.status.value}; errors={av.all_errors}"),
        )

    return replace(av, status=Status.ACCEPTED_OVERRIDE, override_by=engineer, notes=notes)
