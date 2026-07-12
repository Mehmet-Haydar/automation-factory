#!/usr/bin/env python3
"""factory_web.py — AUTOMATION_FACTORY Workbench web face.

Opens a native desktop window (pywebview) rendering the Dense Cockpit
Emerald HTML GUI and exposes a Python API the front-end calls for all
project operations (file tree, file I/O, actions, AI, git, library).

Business logic in workbench/core/* and 05_SCRIPTS/* is never modified here.

Run: python 05_SCRIPTS/factory_web.py   (or start.bat)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
FACTORY_ROOT = SCRIPT_DIR.parent
WEBGUI = FACTORY_ROOT / "webgui"
for p in (str(FACTORY_ROOT), str(SCRIPT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# C-1 fix: EU AI Act audit log — lazy import so startup is not broken if module missing
try:
    from ai_decision_log import log_ai_action as _log_ai_action, AuditLogError  # type: ignore
    _AUDIT_OK = True
except ImportError:
    _log_ai_action = None  # type: ignore
    AuditLogError = RuntimeError  # type: ignore
    _AUDIT_OK = False


# ---------------------------------------------------------------------------
# O-1 fix: Centralised warning accumulator — silent parse failures are now
# visible in the UI via the _warnings field in every API response that uses
# _project_state(), and also written to stderr via logging.warning so
# server-side logs capture them.  Behaviour (empty-dict fallback) is
# UNCHANGED; only observability is added.
# ---------------------------------------------------------------------------

_logger = logging.getLogger("factory_web")

_warnings_lock = threading.Lock()
_warnings_buf: list[dict] = []  # [{"msg": str, "category": str}, ...]


def _warn(msg: str, category: str = "parse") -> None:
    """Record a recoverable warning; emit to stderr and accumulate for UI."""
    _logger.warning("[%s] %s", category, msg)
    entry = {"msg": msg, "category": category}
    with _warnings_lock:
        _warnings_buf.append(entry)


def _emit_provider_warning(task_cfg: dict) -> None:
    """Denetim G-02 fix (2026-07-10): get_provider_for_task() computes an
    'output-ceiling risk' warning (provider hard-capped below the task's
    typical draft size — RD05/09/10 tables, SCL blocks can be cut mid-table)
    but several internal call sites read task_cfg["provider"/"model"] and
    silently dropped task_cfg["warning"] — the truncation risk was computed
    and then thrown away instead of "said out loud" as the comment above
    _LONG_OUTPUT_TASKS promises. Call this right after every internal
    `get_provider_for_task(...)` so the same _warnings/_pii_warnings channel
    already surfaced in the GUI diagnostics log (Backend._consumeWarnings)
    carries it through, not just the two JS call sites that already show it
    in the pre-analysis consent modal."""
    w = task_cfg.get("warning") if isinstance(task_cfg, dict) else None
    if w:
        _warn(str(w), category="provider")


def _anonymize_or_block(text: str, anon_map: dict, required: bool,
                        what: str):
    """S-3 (2026-07-10 audit): anonymization before an AI send must never
    fail open. Every call site used `except Exception: pass`, so exactly
    when the data classification made anonymization MANDATORY, a failure
    inside anonymize_text silently sent the original text to the provider.

    Returns (text, None) on success. On failure:
    - required=True  -> (original, error_msg): the caller MUST abort the
      AI call and surface error_msg (fail-closed).
    - required=False -> (original, None) with a visible privacy warning
      (regex-only pass was best-effort to begin with).
    """
    try:
        from anonymizer import anonymize_text  # type: ignore
        out, _ = anonymize_text(text, anon_map)
        return out, None
    except Exception as exc:
        if required:
            return text, (f"Anonymization failed for {what}: {exc} — AI call "
                          "blocked (the data classification requires "
                          "anonymization).")
        _warn(f"Anonymization failed for {what}: {exc} — content sent "
              "unmodified (classification does not require anonymization).",
              category="privacy")
        return text, None


def _flush_warnings() -> list[dict]:
    """Return accumulated warnings and clear the buffer (call once per request)."""
    with _warnings_lock:
        result = list(_warnings_buf)
        _warnings_buf.clear()
    return result


def _attach_warnings(response: dict) -> dict:
    """R-O-1 fix: flush the warning buffer and attach it to *response* as
    '_warnings'.  Called at every public API method that can emit _warn()
    (directly or via _project_state), so warnings are always delivered in the
    same response that triggered them — not deferred to the next get_state().

    Contract:
    - Idempotent: if '_warnings' is already present (shouldn't happen), the new
      list is merged so no warning is silently dropped.
    - If the buffer is empty the key is still present (empty list) for
      consistent consumer code.
    - Never raises: bare except so a flush failure cannot break the response.
    """
    try:
        w = _flush_warnings()
        existing = response.get("_warnings")
        if isinstance(existing, list):
            response["_warnings"] = existing + w
        else:
            response["_warnings"] = w
    except Exception:
        pass
    return response


def _audit_log(project_root, step_label, provider, model,
               prompt_text="", output_text="", prompt_id="",
               full_prompt_text=None):
    """Attempt to write an audit log entry. Raises AuditLogError if log is
    unwritable (fail-closed per EU AI Act Article 12).

    S-3 fix: input_hash is always derived from the full (untruncated) prompt.
    Pass full_prompt_text=<complete_prompt> alongside a display-only
    prompt_text=<prompt[:N]> slice to ensure audit hash integrity.
    When full_prompt_text is None, prompt_text is used as-is (backward compat).
    """
    if not _AUDIT_OK or _log_ai_action is None:
        raise AuditLogError(
            "ai_decision_log module not available — AI call blocked (EU AI Act Article 12)."
        )
    if project_root is None:
        raise AuditLogError(
            "No project open — cannot write audit log. AI call blocked."
        )
    _log_ai_action(
        project_path=project_root,
        step_label=step_label,
        ai_model=model,
        ai_provider=provider,
        prompt_text=prompt_text,
        output_text=output_text,
        prompt_id=prompt_id,
        full_prompt_text=full_prompt_text,
    )


GUI_SETTINGS  = FACTORY_ROOT / ".gui_settings.json"
WB_SETTINGS   = FACTORY_ROOT / ".workbench_settings.json"

KIND_BY_EXT = {
    ".scl": "scl", ".st": "scl", ".awl": "scl",
    # G-05 fix: .ini and .seq are recognised by platform_detector as S5 source
    # files. Map them to "text" so _kind() returns a readable kind (visible in
    # the editor) and search_project() indexes them, rather than skipping silently.
    ".ini": "text", ".seq": "text",
    ".md":  "md",  ".json": "json",
    ".xlsx": "table", ".xls": "table", ".csv": "table",
    ".txt": "text", ".log": "text",
    ".py": "text", ".bat": "text", ".sh": "text",
}

SAFE_WRITE_EXT = {".scl", ".st", ".awl", ".md", ".json", ".txt", ".csv"}

# W-A6: control-plane files. These hold gate state, classification, audit
# history, etc. — if save_file were allowed to overwrite them, the JS bridge
# (or any XSS in the embedded webview) could spoof the gate to 7, downgrade
# data_classification to PUBLIC, or zero out the validation error count and
# bypass every other check we just added. They must be edited only through
# the typed setter API (advance_gate, set_classification, …) that validates
# and audit-logs the change.
CONTROL_FILES = {
    "PROJECT_STATE.json",
    "PROJECT_MAESTRO.md",
}

# S-8 fix: Tek merkezi versiyon sabiti — get_state() ve diğer tüm kullanım
# noktaları buradan okur; hardcoded string kopyası yok.
APP_VERSION = "v3.10.0"

# B-15: gate 6 is honestly named — "Simulation" implied a PLCSIM run always
# happens, but PLCSIM Advanced is a separate paid license and the gate also
# passes on a signed manual-test declaration. The name must not overstate
# what was verified (it ends up in customer reports).
GATE_NAMES = [
    "Discovery", "Extraction", "Human Review", "Code Generation",
    "Validation", "PLCSIM / Field Verify", "FAT / SAT",
]

# Per-provider recommendation metadata — shown in Settings UI provider cards.
# default_max_tokens ×4 (2026-07-07 E2E: RD05/09/10 drafts were cut at the
# output ceiling). AIClient clamps every request to the provider's REAL
# output cap (_PROVIDER_MAX_OUTPUT), so a generous recommendation can never
# cause an API error — deepseek stays physically limited to 8192 out.
_PROVIDER_META: dict = {
    "anthropic": {
        "badge": "SCL generation · Code analysis · Safety",
        "recommended_for": ["scl_generation", "default"],
        "default_max_tokens": 32768,
    },
    "google": {
        "badge": "PDF/P&ID analysis · Translation · Large context",
        "recommended_for": ["preanalysis", "translation"],
        "default_max_tokens": 65536,
    },
    "deepseek": {
        "badge": "Low-cost template code (PUBLIC projects only)",
        "recommended_for": [],
        "default_max_tokens": 16384,
    },
    "openai": {
        "badge": "",
        "recommended_for": [],
        "default_max_tokens": 16384,
    },
}

# Default task → provider mapping (user can override in Settings).
_DEFAULT_TASK_ROUTING: dict = {
    "default":        "anthropic",
    "preanalysis":    "google",
    "scl_generation": "anthropic",
    "translation":    "google",
}

# Workflow steps whose drafts routinely exceed 8k output tokens (RD05/09/10
# tables, SCL blocks). Routing one to a provider with a lower hard output
# ceiling cuts the draft mid-table (E2E #2: deepseek 8192) — the user's
# routing choice is respected, but the truncation risk must be said out loud.
_LONG_OUTPUT_TASKS = {"default", "preanalysis", "scl_generation"}
_LONG_OUTPUT_MIN_CAP = 16384

def _canonical_rd_names() -> list[str]:
    """RD display names from the canonical taxonomy (project_analyzer.RD_INPUT_NEEDS).

    The old hard-coded list (Hardware/Architecture/Motors/Valves/Sensors/...) did
    not match the 14-Point schema and mislabeled the dashboard (W1).
    """
    try:
        from project_analyzer import RD_INPUT_NEEDS  # type: ignore
        names = [
            (RD_INPUT_NEEDS.get(f"RD{n:02d}", {}).get("title", "") or "").strip()
            for n in range(1, 15)
        ]
        if all(names):
            return names
    except Exception:
        pass
    # Fallback — kept in sync with project_analyzer.RD_INPUT_NEEDS titles.
    return [
        "IO List", "DataDict", "Flowchart", "Mode", "Safety ⚠️",
        "Motion", "Timing", "Alarm", "Comms", "FBSpec",
        "HMI", "UseCase", "Annotation (retrofit)", "Modernization (retrofit)",
    ]


RD_NAMES = _canonical_rd_names()

# Gates requiring explicit human/safety sign-off:
# Human Review, Code Generation, Simulation, FAT/SAT.
APPROVAL_GATES = {3, 4, 6, 7}

# Per-gate required RDs + actions (1-indexed by list position).
#
# All 14 RDs are ANALYSIS artifacts, produced in Discovery (1) + Extraction (2).
# Gates 3-7 own NO RDs — they review / generate code / validate / simulate /
# deliver, and are gated by sign-off, validation results and compile evidence
# in advance_gate, NOT by RD presence. Flow:
#   Discover -> Extract -> Human sign-off -> Code Gen -> Validate -> Simulate
#   -> Report.  See the internal RD-gate design note.
GATE_CONFIG = [
    # Generation is a panel button (Pre-Analysis / Topic Extraction), not a
    # gate "action". The old static "analyze" and "extract_io" actions only
    # re-scanned / re-extracted and were mistaken for generators, so they were
    # removed from the gate Actions list. IO-list validation errors are still
    # gated at the "validate" gates (3, 5) via last_io_validation.
    {"rds": ["RD01", "RD02", "RD03", "RD13"],
     "actions": []},
    {"rds": ["RD04", "RD05", "RD06", "RD07", "RD08",
             "RD09", "RD10", "RD11", "RD12", "RD14"],
     # hmi_draft: deterministic RD11/RD08 pre-fill from the wired-pulpit
     # inventory (buttons/lamps/thumbwheels) — an alternative seed to the
     # AI topic extraction for machines whose "HMI" is the pulpit itself.
     "actions": ["hmi_draft"]},
    # G-03 (2026-07-10 audit): rd01_crosscheck + generate_sequence_fb were
    # fully functional backend endpoints with no GUI reach — orphan APIs.
    {"rds": [], "actions": ["validate", "rd01_crosscheck"]},                 # 3 Human Review
    {"rds": [], "actions": ["assemble_program", "generate_scl",
                            "generate_sequence_fb",
                            "generate_hmi_interface"]},                      # 4 Code Generation
    {"rds": [], "actions": ["validate"]},                                    # 5 Validation
    {"rds": [], "actions": ["generate_test_scenarios", "export_tia", "send_to_tia"]},  # 6 Simulation
    {"rds": [], "actions": ["generate_report", "generate_fat"]},             # 7 FAT / SAT
]

# RD statuses that mean "input not produced yet" (project_analyzer vocabulary).
_RD_INCOMPLETE_STATUSES = {"empty", "template", ""}


def _json_safe_fm(fm: dict) -> dict:
    """Convert non-JSON-serializable values in YAML frontmatter (e.g. datetime)
    to strings so pywebview can return them without raising TypeError."""
    import datetime as _dt
    if not fm:
        return {}
    out = {}
    for k, v in fm.items():
        if isinstance(v, (_dt.datetime, _dt.date)):
            out[k] = v.isoformat()
        elif isinstance(v, (_dt.timedelta,)):
            out[k] = str(v)
        else:
            out[k] = v
    return out

# W-A2: RD05 (Safety) is allowed to sit at DRAFT_UNVERIFIED during early
# gates (extraction, code generation), but ANY approval gate — Human Review,
# Simulation, FAT/SAT — requires it to be explicitly approved by a human.
# Statuses that count as "human approved" for RD05's safety review.
_RD_APPROVED_STATUSES = {"done", "approved", "final"}


_SIGNATURE_MIN_LEN = 6
_SIGNATURE_MIN_WORDS = 2


def _validate_signature(sig: str) -> tuple[bool, str]:
    """W-A1: an approval signature is not just "any non-empty string".

    Previous behaviour accepted "x" / "." as a valid sign-off — a developer
    test value that survives into PROJECT_STATE.json sells the audit trail
    out. We now require something that is at least plausibly a person + role
    or person + organization. This is NOT cryptographic identity — that needs
    out-of-band PKI — but it stops trivial dummy values from satisfying
    SIL/PLr gate sign-offs.

    Rules:
      - at least 6 characters after trim
      - at least 2 whitespace-separated tokens (e.g. "Hans Becker",
        "QA sign-off", "M. Yilmaz (TÜV)")
      - must contain at least one letter (so "123 456" is rejected)
    """
    s = (sig or "").strip()
    if len(s) < _SIGNATURE_MIN_LEN:
        return False, (
            f"Signature too short (at least {_SIGNATURE_MIN_LEN} characters, "
            f"in name-surname or name-role format). Example: 'Hans Becker (TÜV)'."
        )
    tokens = [t for t in s.split() if t]
    if len(tokens) < _SIGNATURE_MIN_WORDS:
        return False, (
            "Signature must contain at least two words (name-surname or name-role). "
            "A single character or a single word is not accepted."
        )
    if not any(ch.isalpha() for ch in s):
        return False, "Signature must contain at least one letter."
    return True, ""


_COMPILE_LOG_KEYWORDS = ("tia", "compil", "build")


def _validate_compile_log(path: str) -> bool:
    """S-4: TIA Portal compile log content validation.

    Fail-safe default: returns False on unknown/parse-error/empty-file cases
    (deny, not allow). To be considered valid:
      1. File size must be > 0
      2. The file must contain at least one TIA Portal build marker:
         "tia", "compile" or "build" (case-insensitive)

    This validation prevents an arbitrary file (e.g. an empty placeholder or a
    text document) from passing Gate 6. It requires minimum evidence that the
    compile log is *real* TIA Portal output.
    """
    import os as _os
    try:
        if not _os.path.isfile(path):
            return False
        size = _os.path.getsize(path)
        if size == 0:
            return False
        # Content check: case-insensitive keyword search.
        # For large log files the first 8 KB is enough; tailing caps memory use.
        with open(path, "r", errors="replace", encoding="utf-8") as fh:
            head = fh.read(8192)
        lower = head.lower()
        if not any(kw in lower for kw in _COMPILE_LOG_KEYWORDS):
            return False
        return True
    except Exception:
        # Her türlü I/O / izin / encoding hatası → fail-safe: False
        return False


# Vites-2 — risk-based approval. Only these RDs REQUIRE an explicit human
# review for the gates to move: RD01 (IO list — every wire the code touches),
# RD03 (flowchart — the machine's logic), RD05 (safety — legally mandatory,
# named sign-off, W-A2). The remaining topic RDs are drafted, visible and
# reviewable at any time, but the flow no longer stalls on all 14: the Gate-3
# lock stamps unreviewed ones "auto-accepted" with an honest audit record.
# Field-audit B-04: 14 mandatory approvals ≈ half a working day before the
# first line of SCL — engineers bypass tools that do that.
CRITICAL_RDS = {"RD01", "RD03", "RD05"}


def _gate_advance_blockers(
    gate: int,
    rd_statuses: dict,
    signature: str = "",
    last_validation: dict | None = None,
    accept_structural_only: bool = False,
    last_io_validation: dict | None = None,
    compile_log_path: str = "",
    manual_test_confirmed: bool = False,
    tia_auto_compile: bool = False,
    rd_reviewed: dict | None = None,
    rd_na: set | None = None,
    io_reconciliation_ok: bool = True,
    gate3_unresolved: list | None = None,
) -> list[str]:
    """Reasons gate `gate` may NOT be completed yet (C5 + W-A1 + W-A5 + B-P2).
    Empty list -> may advance.

    Pure function so it can be unit-tested without a live project. Blocks when:
      - a required RD is still empty/template,
      - a validate-bearing gate has known validation errors,
      - a validate-bearing gate's last validation was structural-only (i.e.
        keyword/parenthesis balance) and the caller did NOT explicitly
        acknowledge that fact via `accept_structural_only=True` (W-A5),
      - an approval gate has no — or an invalid — sign-off signature,
      - gate 6 (Simulation) is attempted without compile log path pointing to
        an existing file AND without engineer manual-test declaration (B-P2).
    """
    blockers: list[str] = []
    _na = rd_na or set()
    cfg = GATE_CONFIG[gate - 1] if 1 <= gate <= len(GATE_CONFIG) else {"rds": [], "actions": []}
    for rd in cfg.get("rds", []):
        if rd in _na:
            continue  # engineer marked this RD Not Applicable → not required
        status = (rd_statuses.get(rd, "") or "").lower()
        if status in _RD_INCOMPLETE_STATUSES:
            blockers.append(f"{rd} incomplete (status: {status or 'empty'})")
    # S-7 (B-P4): IO-list validation errors (duplicate addresses, safety-type
    # mismatches) must block like SCL errors do — they were display-only before.
    # Applies from the gate that produces RD01 (extract_io) through every
    # validation gate. Absent result == not run yet → no blocker (same
    # semantics as last_validation below).
    _io_gates = {"extract_io", "validate"}
    if _io_gates & set(cfg.get("actions", [])) and last_io_validation:
        io_errors = int(last_io_validation.get("errors", 0) or 0)
        if io_errors > 0:
            blockers.append(
                f"IO list has {io_errors} validation error(s) "
                "(e.g. duplicate address / safety type) — fix RD01 first")
    if "validate" in cfg.get("actions", []) and last_validation:
        errors = int(last_validation.get("errors", 0) or 0)
        if errors > 0:
            blockers.append(f"Validation contains {errors} error(s) — fix them first")
        scope = str(last_validation.get("scope", "") or "").lower()
        # S-7: approval gate'lerde (3,5,6,7) accept_structural_only=True bypass
        # edilemez. Fail-closed: imzalı onay kapıları structural-only validation
        # ile geçilemez — tip uyumsuzlukları ve UDT hataları atlanmış olur.
        if scope == "structural_only" and (
            not accept_structural_only or gate in APPROVAL_GATES
        ):
            blockers.append(
                "Validation was structural only (keyword/parenthesis balance) — "
                "type mismatches, undefined functions and missing UDTs "
                "were NOT caught. Run a compile in TIA Portal, or "
                "explicitly accept proceeding with user approval "
                "(accept_structural_only)."
            )
    if gate in APPROVAL_GATES:
        sig = (signature or "").strip()
        if not sig:
            blockers.append("This gate requires human approval — enter a signature/approval")
        else:
            ok, reason = _validate_signature(sig)
            if not ok:
                blockers.append(f"Invalid signature: {reason}")
        # W-A2: RD05 (Safety) must be explicitly approved (not just non-empty)
        # before any approval gate can advance. DRAFT_UNVERIFIED is legitimate
        # during extraction (RD05 is allowed to remain auto-generated and
        # unverified through gate 2), but it must not survive into Human
        # Review / Simulation / FAT-SAT. README's "certified engineer approval
        # is mandatory" is otherwise unenforced.
        rd05_status = (rd_statuses.get("RD05", "") or "").lower()
        # A named RD05 review (3-state model) is the safety engineer's sign-off
        # and satisfies W-A2 just like a file-status approval does. A named RD05
        # N/A (safety engineer justified "no safety functions in scope") also
        # resolves it — mark_rd_na requires a named reason for RD05.
        rd05_reviewed = bool(rd_reviewed and rd_reviewed.get("RD05"))
        rd05_na = "RD05" in _na
        if (rd05_status and rd05_status not in _RD_APPROVED_STATUSES
                and not rd05_reviewed and not rd05_na):
            blockers.append(
                f"RD05 (Safety) is not approved (status: {rd05_status}). "
                "Certified safety engineer review is mandatory for "
                "approval gates — review RD05 (named sign-off) or set it "
                "to 'done' / 'approved'."
            )
    # 3-state model review gating. Skipped when rd_reviewed is None (pure-logic
    # / legacy callers), so gate tests that don't pass it keep their behaviour.
    # Only RDs present in rd_reviewed are reviewable (have a file on disk); a
    # produced-but-fileless RD is skipped rather than deadlocking the gate.
    if rd_reviewed is not None:
        # (A) A gate's OWN produced CRITICAL RDs must be approved (green)
        # before leaving it. Vites-2: non-critical topic RDs no longer stall
        # the gate — they stay reviewable and get auto-accepted at the lock.
        for rd in cfg.get("rds", []):
            if rd in _na:
                continue  # Not Applicable → not required to be reviewed
            if rd not in CRITICAL_RDS:
                continue  # risk-based: drafted is enough to move on
            status = (rd_statuses.get(rd, "") or "").lower()
            if status in _RD_INCOMPLETE_STATUSES:
                continue
            if rd in rd_reviewed and not rd_reviewed[rd]:
                blockers.append(
                    f"{rd} not yet reviewed — approve it (turn it green) "
                    f"before advancing past Gate {gate}."
                )
        # (B) Human Review (gate 3) is the bulk LOCK: every produced CRITICAL
        # RD must be human-approved (or N/A) before it can be sealed; the
        # remaining produced RDs are stamped auto-accepted by the lock itself.
        if gate == 3:
            for rd, status in sorted(rd_statuses.items()):
                if rd in _na or rd not in CRITICAL_RDS:
                    continue
                if (status or "").lower() in _RD_INCOMPLETE_STATUSES:
                    continue
                if rd in rd_reviewed and not rd_reviewed[rd]:
                    blockers.append(
                        f"{rd} not yet reviewed — an engineer must pre-approve it "
                        "(turn it green) before Human Review can be locked."
                    )
    # Gate-3 Reconciliation & Preview: the bulk lock cannot close over
    # unresolved cross-artifact deviations (orphan HMI↔IO refs, un-propagated
    # dossier decisions, semantic device-class changes). None = the caller did
    # not evaluate (pure-logic/legacy tests) → same opt-in semantics as
    # rd_reviewed. RED findings (EN ISO 13850 safety baseline) can never be
    # waived; the rest block until fixed OR consciously waived (name+reason).
    if gate == 3 and gate3_unresolved:
        reds = [f for f in gate3_unresolved if f.get("severity") == "red"]
        if reds:
            blockers.append(
                f"{len(reds)} RED consistency finding(s) — the safety baseline "
                "(EN ISO 13850) cannot be waived, not even with a signature. "
                "Go back and fix: "
                + "; ".join(f.get("title", "?") for f in reds[:3]))
        others = len(gate3_unresolved) - len(reds)
        if others:
            blockers.append(
                f"{others} unresolved reconciliation deviation(s) — fix them "
                "or record a conscious choice (reason + name) in the Gate-3 "
                "Reconciliation screen before locking.")
    # Gate 4 (Code Generation): the engineer must validate the IO reconciliation
    # (provenance + missing/extra/conflict) before code is generated. Fail-safe:
    # the caller passes io_reconciliation_ok=False when RD01 exists, is not N/A,
    # and there is no ack matching the current RD01 hash.
    if gate == 4 and not io_reconciliation_ok:
        blockers.append(
            "IO reconciliation not validated — review RD01 provenance "
            "(missing / extra / conflicting signals) and acknowledge it before "
            "code generation."
        )
    # B-P2 / S-4: Gate 6 (Simulation / PLCSIM) requires compile evidence AND
    # engineer manual-test declaration. Fail-closed: missing either → block.
    # tia_auto_compile=True means advance_gate() found tia_compile.json written
    # by _record_compile_success() (TIA Openness bridge) — satisfies compile
    # requirement automatically; manual file pick is not needed in that case.
    if gate == 6:
        if not tia_auto_compile:
            log_path = (compile_log_path or "").strip()
            if not log_path:
                blockers.append(
                    "Gate 6 (Simulation) requires compile evidence — "
                    "either run 'Send to TIA' (auto-detected) or provide the "
                    "TIA Portal compile log file path manually."
                )
            else:
                if not _validate_compile_log(log_path):
                    import os as _os
                    if not _os.path.isfile(log_path):
                        blockers.append(
                            f"Gate 6 compile log not found: '{log_path}' — "
                            "the file must exist on disk before advancing."
                        )
                    else:
                        blockers.append(
                            f"Compile log does not appear to be a TIA Portal build log: "
                            f"'{log_path}' — file must be non-empty and contain at least "
                            "one of 'TIA', 'Compile' or 'Build'."
                        )
        if not manual_test_confirmed:
            blockers.append(
                "Gate 6 (Simulation) requires engineer manual-test declaration — "
                "confirm 'I have manually tested this program' (manual_test_confirmed)."
            )
    return blockers


def _rd_content_hashes(root: Path) -> dict:
    """SHA-256 of every metadata/RD*.md — basis of the gate staleness snapshot."""
    import hashlib as _hl
    out: dict = {}
    md = root / "metadata"
    if not md.is_dir():
        return out
    for f in sorted(md.glob("RD*.md")):
        try:
            out[f.name] = _hl.sha256(f.read_bytes()).hexdigest()
        except Exception:
            continue
    return out


def _stale_rds(st: dict, root: Path) -> list[dict]:
    """RD files edited (or deleted) AFTER the last gate advance.

    Compares current metadata/RD*.md hashes against the `rd_snapshot` taken by
    advance_gate(). Only files present in the snapshot are considered — a
    brand-new RD added while working toward the NEXT gate is normal progress,
    not staleness. Advisory only (no gate regression): returns an empty list
    when there is no snapshot (legacy projects) or on any failure.
    """
    snap = (st or {}).get("rd_snapshot") or {}
    hashes = snap.get("hashes") or {}
    if not hashes or root is None:
        return []
    try:
        current = _rd_content_hashes(root)
    except Exception:
        return []
    out: list[dict] = []
    for name, h in sorted(hashes.items()):
        cur_h = current.get(name)
        if cur_h is None:
            change = "deleted"
        elif cur_h != h:
            change = "modified"
        else:
            continue
        out.append({
            "rd_file": name,
            "gate": snap.get("gate"),
            "when": snap.get("when", ""),
            "change": change,
        })
    return out


# ---------------------------------------------------------------------------
# S-18 / B-P8 — Gate auto-unsign when approval-gate RDs change after signing
# ---------------------------------------------------------------------------

def _gate_approval_rd_snapshot_key(gate: int) -> str:
    """PROJECT_STATE key that stores the per-gate RD snapshot for S-18."""
    return "gate_rd_snapshots"


def _effective_gate_rds(gate: int, rd_na: set | None = None) -> list[str]:
    """RDs whose change must invalidate this gate's sign-off (auto-unsign).

    After the phase-based redesign the approval gates (Human Review, Code
    Generation, Simulation, FAT/SAT) own NO RDs of their own — all 14 RDs are
    analysis artifacts produced in Discovery (1) + Extraction (2). An approval
    signature therefore certifies the *upstream analysis*, i.e. the cumulative
    set of RDs produced by gates 1..gate. For a gate that owns RDs this is just
    its own list; for an empty-rds approval gate it resolves to every RD from
    the preceding analysis gates. Without this, snapshots for gates 3-7 would be
    empty and auto-unsign would be a no-op (it would never detect a changed RD).

    N/A RDs are excluded so a greenfield project does not record bogus
    ``__MISSING__`` sentinels for retrofit-only RD13/RD14 in its audit snapshot.
    """
    if not (1 <= gate <= len(GATE_CONFIG)):
        return []
    _na = rd_na or set()
    seen: list[str] = []
    for i in range(gate):
        for rd in GATE_CONFIG[i].get("rds", []):
            if rd not in seen and rd not in _na:
                seen.append(rd)
    return seen


def _gate_rd_hashes_for_gate(root: "Path", gate: int, rd_na: set | None = None) -> dict:
    """SHA-256 of each RD file this gate's sign-off certifies (see
    ``_effective_gate_rds`` — the cumulative upstream analysis, not just the
    gate's own ``rds`` bucket, which is empty for approval gates 3-7).

    Returns empty dict if root/gate is invalid or files are missing (safe).
    """
    import hashlib as _hl
    out: dict = {}
    if root is None or not (1 <= gate <= len(GATE_CONFIG)):
        return out
    md = root / "metadata"
    if not md.is_dir():
        return out
    for rd_id in _effective_gate_rds(gate, rd_na):
        # RD files are named RD01_*.md — glob by prefix
        matches = sorted(md.glob(f"{rd_id}_*.md"))
        if not matches:
            # File missing → use a sentinel so absence is detected as "changed"
            out[rd_id] = "__MISSING__"
        else:
            f = matches[0]
            try:
                out[rd_id] = _hl.sha256(f.read_bytes()).hexdigest()
            except Exception:
                out[rd_id] = "__READ_ERROR__"
    return out


# ---------------------------------------------------------------------------
# Per-RD verification — 3-state model (draft 🟡 → reviewed 🟢 → locked 🔒)
# ---------------------------------------------------------------------------
# `rd_verifications` in PROJECT_STATE is the single source of truth for the
# review/lock tiers. The project_analyzer status vocabulary stays size/marker
# based and only tells us whether an RD was *produced*; approval lives here.
#   draft    🟡  produced by AI, not yet reviewed
#   reviewed 🟢  engineer pre-approved (one-click; RD05 needs a named sign-off)
#   locked   🔒  sealed at the Gate-3 bulk sign-off → Code Generation unlocks
# Editing a reviewed/locked RD changes its file hash, which silently demotes it
# back to 'draft' (stale) — the per-RD analogue of the gate auto-unsign.

def _rd_main_file(root: "Path | None", rd_id: str) -> "Path | None":
    """The project's canonical RD file (not an .ai_draft.md sidecar)."""
    if root is None:
        return None
    md = root / "metadata"
    if not md.is_dir():
        return None
    matches = sorted(
        p for p in md.glob(f"{rd_id}_*.md") if not p.name.endswith(".ai_draft.md")
    )
    return matches[0] if matches else None


def _rd_file_hash(root: "Path | None", rd_id: str) -> str:
    """SHA-256 of the canonical RD file ("" if absent/unreadable)."""
    import hashlib as _hl
    f = _rd_main_file(root, rd_id)
    if f is None:
        return ""
    try:
        return _hl.sha256(f.read_bytes()).hexdigest()
    except Exception:
        return ""


_RD_AUTHOR_RE = re.compile(r"^\s*(model|source):\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _rd_draft_author(root: "Path | None", rd_id: str) -> str:
    """Best-effort 'who produced this' from the AI draft frontmatter."""
    f = _rd_main_file(root, rd_id)
    if f is None:
        return ""
    try:
        head = f.read_text(encoding="utf-8", errors="replace")[:600]
    except Exception:
        return ""
    src = model = ""
    for m in _RD_AUTHOR_RE.finditer(head):
        if m.group(1).lower() == "source":
            src = m.group(2).strip()
        else:
            model = m.group(2).strip()
    if src and model:
        return f"{src} ({model})"
    return src or model


def _rd_review_states(root: "Path | None", st: dict, rd_statuses: dict) -> dict:
    """Per-RD verification view: ui_state + who/when, with live staleness.

    A reviewed/locked record whose stored content_hash no longer matches the
    file on disk is reported as ``stale`` and demoted to ``draft`` — so an edit
    after review/lock visibly un-verifies the RD.
    """
    vers = (st or {}).get("rd_verifications") or {}
    # RD13 (legacy annotation) + RD14 (modernization) are retrofit-only → auto
    # N/A on a greenfield project (there is no legacy code to annotate/modernize).
    _is_greenfield = ((st or {}).get("project_type") or "").lower() == "greenfield"
    _AUTO_NA = {"RD13", "RD14"} if _is_greenfield else set()
    out: dict = {}
    for rd_id, status in (rd_statuses or {}).items():
        produced = (status or "").lower() not in _RD_INCOMPLETE_STATUSES
        rec = vers.get(rd_id) or {}
        cur_hash = _rd_file_hash(root, rd_id)
        stored_hash = rec.get("content_hash", "")
        hash_ok = bool(stored_hash) and stored_hash == cur_hash
        # N/A is an engineer decision "this RD does not apply to this project"
        # (e.g. no HMI, or retrofit-only RD13/14 on a greenfield project). It is
        # independent of file presence/hash and takes precedence in the UI.
        _auto_na = rd_id in _AUTO_NA
        na = bool(rec.get("na")) or _auto_na
        was_reviewed = bool(rec.get("reviewed"))
        reviewed = was_reviewed and hash_ok and not na
        locked = bool(rec.get("locked")) and hash_ok and not na
        stale = was_reviewed and not hash_ok and not na
        if na:
            ui = "na"
        elif not produced:
            ui = "empty"
        elif locked:
            ui = "locked"
        elif reviewed:
            ui = "reviewed"
        else:
            ui = "draft"
        out[rd_id] = {
            "ui_state": ui,
            "reviewed": reviewed,
            "locked": locked,
            # Vites-2: machine-accepted at the Gate-3 lock, not human-reviewed
            # — the GUI badges it differently and audits stay honest.
            "auto_accepted": bool(rec.get("auto_accepted")) and reviewed,
            "stale": stale,
            "na": na,
            "na_reason": rec.get("na_reason", "")
                or ("retrofit-only (greenfield project)" if _auto_na else ""),
            "reviewed_by": rec.get("reviewed_by", ""),
            "reviewed_at": rec.get("reviewed_at", ""),
            "author": rec.get("author", ""),
        }
    return out


# ---------------------------------------------------------------------------
# IO reconciliation — cross-source provenance + delta (deterministic)
# ---------------------------------------------------------------------------
# Operates on the produced RD01 IO table (no AI). Provenance is read from the
# Source/SrcModule column; the "delta" uses Address (present = in the new
# wiring / EPLAN / drawing) vs OldTag (present = in the legacy code):
#   new_signals    = Address but no OldTag → in the new design, not in legacy
#   orphan_signals = OldTag but no Address → in legacy code, not in new design
# Plus hard conflicts (duplicate addresses) and ghost rows (neither). The
# engineer validates this before code generation (Gate 4).

_SAFETY_YES = {"Y", "YES", "TRUE", "1", "SAFE", "SAFE_DI", "SAFE_DQ"}


def _reconcile_io_rows(rows: list) -> dict:
    """Deterministic reconciliation summary from parsed RD01 IO rows."""
    import collections
    by_source: collections.Counter = collections.Counter()
    addr_map: dict = collections.defaultdict(list)
    new_signals: list = []
    orphan_signals: list = []
    ghost_rows: list = []
    safety = 0
    for r in rows:
        src = (getattr(r, "source_module", "") or "").strip() or "?"
        by_source[src] += 1
        addr = (getattr(r, "address", "") or "").strip()
        old = (getattr(r, "old_tag", "") or "").strip()
        tag = (getattr(r, "tag", "") or "").strip()
        if (getattr(r, "safety_related", "") or "").strip().upper() in _SAFETY_YES:
            safety += 1
        if addr:
            addr_map[addr.upper()].append(tag)
        if addr and not old:
            new_signals.append(tag)
        elif old and not addr:
            orphan_signals.append(tag)
        elif not addr and not old:
            ghost_rows.append(tag)
    duplicate_addresses = {a: t for a, t in addr_map.items() if len(t) > 1}
    return {
        "total": len(rows),
        "by_source": dict(by_source),
        "safety": safety,
        "new_signals": new_signals,
        "orphan_signals": orphan_signals,
        "ghost_rows": ghost_rows,
        "duplicate_addresses": duplicate_addresses,
        "errors": len(duplicate_addresses),
        "warnings": len(ghost_rows) + len(orphan_signals),
    }


def _extract_md_sections(text: str, headings: tuple) -> dict:
    """Pull the body under the given '## Heading' sections (verbatim)."""
    out: dict = {}
    for h in headings:
        m = re.search(rf"^##\s*{re.escape(h)}\s*$(.*?)(?=^##\s|\Z)",
                      text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if m:
            body = m.group(1).strip()
            if body:
                out[h] = body
    return out


def _rd_na_set(root: "Path | None", st: dict, rd_statuses: dict) -> set:
    """The set of RD ids the engineer marked Not Applicable (incl. greenfield
    auto-N/A) — the single source for every gate-progression/snapshot caller."""
    return {k for k, v in _rd_review_states(root, st, rd_statuses).items() if v.get("na")}


def _check_and_apply_autounsign(
    root: "Path | None",
    st: dict,
) -> tuple[dict, list[dict]]:
    """S-18 / B-P8: detect approval-gate RD changes and auto-unsign.

    Reads ``gate_rd_snapshots`` from *st*, compares with current on-disk RD
    hashes, and for every approval gate whose snapshot shows a change:

    - Appends a ``system`` record to ``gate_history`` (chain-compatible).
    - Removes the per-gate snapshot entry (so re-signing creates a fresh one).
    - Records the event in ``gate_autounsign_log``.

    **Legacy safety**: gates that were signed before S-18 have no snapshot
    entry → WARN only, no auto-unsign (backwards compatibility).

    Returns ``(updated_st, unsign_events)`` where *unsign_events* is a
    (possibly empty) list of dicts describing each auto-unsign action.  The
    caller must persist *updated_st* if it was modified.

    Pure enough for unit testing — the only I/O is ``_gate_rd_hashes_for_gate``
    which reads disk.  Accepts ``root=None`` / missing fields gracefully
    (returns unchanged state, no events).
    """
    import hashlib as _hl
    from datetime import datetime as _dt

    if root is None:
        return st, []

    snapshots: dict = (st.get("gate_rd_snapshots") or {})
    if not snapshots:
        return st, []

    hist = list(st.get("gate_history") or [])
    unsign_events: list[dict] = []

    # Work on a shallow copy so callers can detect mutations
    st = dict(st)
    new_snapshots = dict(snapshots)

    for gate_str, snap in sorted(snapshots.items()):
        try:
            gate = int(gate_str)
        except (ValueError, TypeError):
            continue
        if gate not in APPROVAL_GATES:
            continue

        saved_hashes: dict = snap.get("hashes") or {}
        if not saved_hashes:
            # No saved hashes → legacy / snapshot incomplete → warn only
            _logger.warning(
                "S-18: gate %d has gate_rd_snapshots entry but no hashes — "
                "skipping auto-unsign (legacy record). "
                "Re-sign gate to establish a fresh snapshot.",
                gate,
            )
            continue

        current_hashes = _gate_rd_hashes_for_gate(root, gate)
        changed_rds = []
        for rd_id, saved_h in saved_hashes.items():
            cur_h = current_hashes.get(rd_id, "__MISSING__")
            if cur_h != saved_h:
                change = "deleted" if cur_h == "__MISSING__" else "modified"
                changed_rds.append({"rd": rd_id, "change": change,
                                    "saved": saved_h[:12], "current": cur_h[:12]})

        if not changed_rds:
            continue  # RDs untouched — gate stays signed

        # Build the chain-compatible auto-unsign record
        prev_hash = hist[-1].get("hash", "") if hist else ""
        now = _dt.now().strftime("%Y-%m-%d")
        changed_summary = ", ".join(
            f"{c['rd']} ({c['change']})" for c in changed_rds
        )
        record: dict = {
            "gate":      gate,
            "when":      now,
            "who":       "system",
            "signature": "",
            "note":      f"auto-unsigned: {changed_summary} changed (S-18/B-P8)",
            "prev_hash": prev_hash,
        }
        payload = json.dumps(
            {k: record[k] for k in ("gate", "when", "who", "signature", "note", "prev_hash")},
            ensure_ascii=False, sort_keys=True,
        ).encode("utf-8")
        record["hash"] = _hl.sha256(payload).hexdigest()
        hist.append(record)

        # Remove snapshot so re-signing will create a fresh one
        del new_snapshots[gate_str]

        event = {
            "gate": gate,
            "when": now,
            "changed_rds": changed_rds,
            "msg": (
                f"Gate {gate} auto-unsigned: the following RD(s) changed since "
                f"approval — {changed_summary}. Re-review and re-sign required (B-P8)."
            ),
        }
        unsign_events.append(event)
        _logger.warning(
            "S-18/B-P8 auto-unsign: gate %d — %s",
            gate, changed_summary,
        )

    if unsign_events:
        st["gate_history"] = hist
        st["gate_rd_snapshots"] = new_snapshots
        # Append to running log (advisory — never cleared automatically)
        log: list = list(st.get("gate_autounsign_log") or [])
        log.extend(unsign_events)
        st["gate_autounsign_log"] = log

    return st, unsign_events


def _completed_gate_count(rd_statuses: dict, rd_na: set | None = None) -> int:
    """How many leading gates have ALL their required RDs produced (or N/A).

    Gates are sequential, so we stop at the first gate whose required RDs are
    not all produced. "Produced" = RD status is NOT in _RD_INCOMPLETE_STATUSES
    (empty/template) — the same RD rule _gate_advance_blockers enforces. A RD the
    engineer marked Not Applicable (rd_na) does NOT count as missing — otherwise
    a greenfield project (RD13/14 auto-N/A) or any project that legitimately
    skips a topic would be frozen at gate 1. This is the real, file-derived
    completion signal; it deliberately does NOT trust the stored `gate` counter,
    which advance_gate bumps independently and can sit inflated.
    """
    _na = rd_na or set()
    count = 0
    for i in range(1, 8):
        cfg = GATE_CONFIG[i - 1] if i <= len(GATE_CONFIG) else {"rds": []}
        rds = cfg.get("rds", [])
        # A gate with no RDs (Human Review / Code Gen / Validation / Simulation /
        # FAT-SAT) is not RD-gated — its completion is enforced elsewhere
        # (sign-off / validation / compile evidence in advance_gate). Treat it as
        # RD-complete so progress isn't frozen at the first non-analysis gate;
        # _effective_gate then clamps the DISPLAY by the conservative stored
        # counter, so an empty gate never over-reports real progress. N/A RDs are
        # excluded — a gate whose every RD is N/A counts as complete (all([])).
        produced = all(
            (rd_statuses.get(rd, "") or "").lower() not in _RD_INCOMPLETE_STATUSES
            for rd in rds if rd not in _na
        )
        if produced:
            count += 1
        else:
            break
    return count


def _effective_gate(stored_gate: int, rd_statuses: dict, rd_na: set | None = None) -> int:
    """Truthful current gate for display: never claims more progress than the
    RD evidence supports, but respects a conservative (lower) stored counter.

    `min(stored, completed+1)` self-heals an inflated/legacy counter (shows the
    real position) while never over-reporting beyond stored. Fail-safe: if RDs
    can't be analysed (empty dict), completed=0 -> gate 1, i.e. we under-claim
    rather than over-claim progress. Always clamped to 1..7. rd_na lets N/A RDs
    not freeze progression (see _completed_gate_count).
    """
    try:
        stored = int(stored_gate or 0)
    except (TypeError, ValueError):
        stored = 0
    rd_current = _completed_gate_count(rd_statuses, rd_na) + 1
    # F-2 (real-AI field test 2026-07-02): stored==0 (fresh project / missing
    # counter) must NOT fall back to the doc-derived position alone — a
    # freshly drafted 14-RD pack would then display gate 7/7 with ZERO human
    # signatures. A project that never advanced is at gate 1; the doc signal
    # only ever pulls the display DOWN from the official advance counter.
    eff = min(max(stored, 1), rd_current)
    return max(1, min(7, eff))


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

_KEYRING_SERVICE = "AUTOMATION_FACTORY_webgui"
_KEYRING_PLACEHOLDER = "__keyring__"

try:
    import keyring as _keyring  # type: ignore
    _KEYRING_OK = True
except Exception:
    _keyring = None  # type: ignore
    _KEYRING_OK = False


def _kr_set(provider: str, key: str) -> bool:
    """Store API key in OS keychain. Returns True on success."""
    if not _KEYRING_OK:
        return False
    try:
        _keyring.set_password(_KEYRING_SERVICE, provider, key)
        return True
    except Exception:
        return False


def _kr_get(provider: str) -> str:
    """Retrieve API key from OS keychain; returns "" on failure."""
    if not _KEYRING_OK:
        return ""
    try:
        return _keyring.get_password(_KEYRING_SERVICE, provider) or ""
    except Exception:
        return ""


def _load_settings() -> dict:
    """Read settings JSON from disk.

    C-A2: Do NOT resolve keyring placeholders into plaintext here. The Api
    object MUST NOT keep plaintext keys in memory or send them across the JS
    bridge — that would defeat the keystore. Resolution happens on-demand via
    Api._resolve_api_key() at the moment a key is actually needed.
    """
    for f in (GUI_SETTINGS, WB_SETTINGS):
        try:
            if f.exists():
                return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_KEYRING_WARN_EMITTED = False


def _save_settings(data: dict) -> None:
    """Persist settings to .gui_settings.json.

    Plaintext API keys are moved into the OS keystore via `keyring`; only an
    opaque sentinel remains on disk. When keyring is not available we fall
    back to plaintext on disk AND emit a visible stderr warning so the user
    is not silently tricked into thinking their keys are protected (C-A2).
    """
    global _KEYRING_WARN_EMITTED
    try:
        serializable = dict(data)
        if isinstance(serializable.get("api_keys"), dict):
            safe_keys: dict = {}
            for prov, key in serializable["api_keys"].items():
                if key and key != _KEYRING_PLACEHOLDER:
                    if _kr_set(prov, key):
                        safe_keys[prov] = _KEYRING_PLACEHOLDER
                    else:
                        # keyring unavailable — fall back to plaintext.
                        safe_keys[prov] = key
                        # S-9 (B-G9): the warning must reach the GUI warning
                        # queue, not just a one-time stderr line the user
                        # never sees — they just typed the key in Settings.
                        _warn(
                            f"'keyring' is not available — the {prov} API key "
                            "was stored in PLAINTEXT in .gui_settings.json. "
                            "Install the 'keyring' package (pip install "
                            "keyring) to enable OS keystore protection.",
                            category="security",
                        )
                        if not _KEYRING_WARN_EMITTED:
                            sys.stderr.write(
                                "[factory_web] WARNING: 'keyring' is not "
                                "available — API keys are being stored in "
                                "PLAINTEXT in .gui_settings.json. Install "
                                "the 'keyring' package to enable OS keystore "
                                "protection.\n"
                            )
                            _KEYRING_WARN_EMITTED = True
                else:
                    safe_keys[prov] = key
            serializable["api_keys"] = safe_keys
        GUI_SETTINGS.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _api_key_status(value: str) -> str:
    """Return a non-secret status flag describing how an API key is stored.

    - 'set'    : sentinel placeholder — actual key lives in the OS keystore
    - 'unsafe' : plaintext on disk (keyring unavailable or legacy setting)
    - 'unset'  : empty
    """
    if not value:
        return "unset"
    if value == _KEYRING_PLACEHOLDER:
        return "set"
    return "unsafe"


def _kind(path: Path) -> str:
    if path.is_dir():
        return "folder"
    return KIND_BY_EXT.get(path.suffix.lower(), "text")


def _status_for(path: Path) -> str | None:
    name = path.name.lower()
    if path.suffix.lower() in (".scl", ".st", ".awl"):
        return "mod"
    if "state" in name or "maestro" in name or name == "readme.md":
        return "ok"
    if path.suffix.lower() in (".md", ".json"):
        return "ok"
    return None


# GLOBAL_LANG_POLICY §7 — output-language directive for AI call sites.
# Tag names, SCL keywords and column headers stay English; prose follows
# the project's output_language.
_LANG_NAMES = {"TR": "Turkish", "EN": "English", "DE": "German"}


def _lang_directive(lang_code: str) -> str:
    """System-prompt suffix enforcing the project's output language."""
    code = (lang_code or "EN").strip().upper()
    if code in ("EN", ""):
        return ""
    name = _LANG_NAMES.get(code, code)
    return (
        f"\n\nOUTPUT LANGUAGE DIRECTIVE: Write all generated prose — "
        f"descriptions, table cell texts, notes, code comments — in {name}. "
        "Keep tag names, SCL keywords, Markdown table column headers and "
        "error-code mnemonics in English."
    )


def _re_search_block(doc: str, heading: str) -> str:
    """First ``` fenced block after *heading* in a prompt doc (M3 helper)."""
    fallback = ("You are a senior Siemens automation engineer writing "
                "IEC 61131-3 SCL for TIA Portal V18+.")
    idx = doc.find(heading)
    if idx == -1:
        return fallback
    m = re.search(r"```\r?\n(.*?)```", doc[idx:], re.DOTALL)
    return m.group(1).strip() if m else fallback


def _rd_status(p: Path) -> str:
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "mod"
    stripped = content.strip()
    if len(stripped) < 100:
        return "empty"
    head = content[:600].lower()
    if any(k in head for k in ("status: approved", "status: ok", "status: done", "status: final")):
        if len(stripped) < 300:
            return "empty"
        return "ok"
    if "status: draft" in head:
        return "draft"
    return "mod"


def _job_step(job: dict, step_id: str, status: str, info: str = "") -> None:
    """Update one step of a background-job step list (Send to TIA live view).

    Unknown step ids are ignored — bridges may report steps a given flow
    does not display (e.g. download in the import-only flow)."""
    for s in job.get("steps", []):
        if s["id"] == step_id:
            s["status"] = status
            if info:
                s["info"] = info
            return


_FIX_ASSIST_MODES = ("off", "hints", "suggest", "auto_propose")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _run_git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, cwd=str(cwd),
            capture_output=True, text=True, timeout=8,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# API class
# ---------------------------------------------------------------------------

class Api:
    """Bridge exposed to the front-end as window.pywebview.api."""

    _state_lock = threading.Lock()

    def __init__(self) -> None:
        self.settings = _load_settings()
        self.root = self._resolve_root()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_root(self) -> Path | None:
        lp = self.settings.get("last_project")
        if lp:
            p = Path(lp)
            if p.exists():
                return p
        return None

    def _add_cost(self, usage) -> None:
        """B8 (E2E 2026-07-07): accumulate real API spend.

        settings.total_cost_usd existed since day one but NOTHING ever wrote
        it — a full 16-step AI run left it at 0.0. Every AI call site now
        reports its UsageInfo here. Fail-quiet: cost bookkeeping must never
        break an AI response.
        """
        try:
            c = float(getattr(usage, "cost_usd", 0.0) or 0.0)
            if c > 0:
                self.settings["total_cost_usd"] = round(
                    float(self.settings.get("total_cost_usd", 0.0) or 0.0) + c, 4)
                _save_settings(self.settings)
        except Exception:
            pass

    def _project_state(self) -> dict:
        if not self.root:
            return {}
        f = self.root / "PROJECT_STATE.json"
        try:
            if f.exists():
                return json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:
            # O-1 fix: parse failure is now visible instead of silently
            # returning {}; behaviour (empty-dict fallback) is unchanged.
            _warn(
                f"PROJECT_STATE.json parse error ({f}): {exc}",
                category="parse",
            )
        return {}

    def _save_state(self, path: Path, state: dict) -> None:
        """Thread-safe PROJECT_STATE.json write."""
        with self._state_lock:
            path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _resolve_api_key(self, provider: str) -> str:
        """Return the plaintext API key for `provider`, fetched on demand.

        C-A2: Never cached on the Api instance, never returned through the
        JS bridge. Called only at the moment a backend AI call needs the key.
        """
        val = (self.settings.get("api_keys") or {}).get(provider, "")
        if val == _KEYRING_PLACEHOLDER:
            return _kr_get(provider)
        return val or ""

    def _ai_send_allowed(self, provider: str) -> tuple[bool, str]:
        """C4 gate — refuse sending CONFIDENTIAL/RESTRICTED project data to a
        public-tier AI provider. Returns (allowed, reason).

        NOTE: Callers that use _ai_send_allowed() instead of check_ai_send()
        directly lose the AIGateResult.requires_anonymization flag. Prefer
        calling check_ai_send() directly and then _anon_map_for_ai(gate) when
        you need to build the anonymization map (S-20 / B-G8).
        """
        try:
            from data_classification_guard import check_ai_send  # type: ignore
            return check_ai_send(self.root, provider, self.settings)
        except Exception:
            # If the guard cannot load, fail-closed: block the send.
            return False, "Data classification check could not be loaded — sharing refused."

    def _pii_soft_warn(self, provider: str) -> list[str]:
        """Charter §11 — soft PII/customer-name warning (non-blocking).

        Scans the open project for customer names and INTERNAL/CONFIDENTIAL
        markers that are about to be sent to a public-tier AI provider.
        Returns a list of human-readable warning strings (empty = clean).
        Caller MUST surface these warnings in the API response; it must NOT
        block the send (data_classification_guard handles hard blocking).
        """
        warnings: list[str] = []
        if not self.root:
            return warnings

        PUBLIC_TIER = {"anthropic", "openai", "google", "deepseek"}
        if provider not in PUBLIC_TIER:
            return warnings

        # 1. Customer name detection — read from PROJECT_STATE / PROJECT_MAESTRO
        customer = ""
        try:
            state = self._project_state()
            customer = (
                state.get("customer_name") or
                state.get("customer") or
                state.get("project_name") or ""
            )
        except Exception:
            pass

        if customer:
            warnings.append(
                f"⚠️  PII warning: Project contains a customer name ({customer!r}). "
                f"This data will be sent to the {provider} API — has customer consent been obtained?"
            )

        # 2. Data classification marker scan
        try:
            markers = ("CONFIDENTIAL", "RESTRICTED", "GİZLİ", "MÜŞTERİ")
            for f in self.root.rglob("PROJECT_STATE.json"):
                text = f.read_text(encoding="utf-8", errors="ignore")[:4000]
                found = [m for m in markers if m in text.upper()]
                if found:
                    warnings.append(
                        f"⚠️  Classification: {', '.join(found)} marker(s) "
                        f"detected inside PROJECT_STATE.json. "
                        f"Review the data before it is sent to the {provider} API."
                    )
                    break
        except Exception:
            pass

        return warnings

    def _anon_map_for_ai(self, gate) -> dict:
        """S-20 (B-G8): Return the anonymization map the caller MUST apply before
        sending text to any AI provider.

        gate is an AIGateResult from check_ai_send / provider_allowed.

        Rules:
          gate.requires_anonymization=True  → load map from PROJECT_STATE; return
            it even if empty (regex PII patterns in anonymize_text still run).
          gate.requires_anonymization=False → empty dict (anonymize is optional).

        Fail-safe: if requires_anonymization=True but PROJECT_STATE is missing /
        unreadable, return {} — anonymize_text({}) still applies all regex
        patterns (email, phone, address), providing partial PII protection.
        The caller must not skip the anonymize_text() call based on this being {}.
        """
        if not getattr(gate, "requires_anonymization", False):
            # PUBLIC: anonymize optional — caller decides.
            return {}
        # INTERNAL (and CONFIDENTIAL+consent): anonymize REQUIRED.
        try:
            from anonymizer import build_anon_map  # type: ignore
            state = self._project_state()
            return build_anon_map(state)
        except Exception:
            # State unreadable — return empty map; regex PII patterns still apply.
            return {}

    def _safe(self, relpath: str) -> Path | None:
        """Resolve relpath under project root, refuse path-traversal."""
        if not self.root:
            return None
        try:
            target = (self.root / relpath).resolve()
            target.relative_to(self.root.resolve())
            return target
        except Exception:
            return None

    # O-2 fix: path-sandbox helpers ----------------------------------------

    @staticmethod
    def _is_path_under(child: Path, parent: Path) -> bool:
        """Return True if *child* (resolved) is inside *parent* (resolved).

        Uses Path.relative_to() — raises ValueError if not under parent, which
        we catch and convert to False.  Symlinks are resolved before the check
        so a symlink pointing outside the allowed tree is rejected.
        """
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except (ValueError, OSError):
            return False

    def _allowed_project_roots(self) -> list[Path]:
        """Return the whitelist of directories under which projects may live.

        Roots (in priority order):
        1. ``projects_folder`` from settings (user-configurable).
        2. ``~/Documents/AUTOMATION_FACTORY_PROJECTS`` — default user area.
        3. ``FACTORY_ROOT/examples``                  — bundled demo projects.

        A root is included only if it exists on disk so that a missing
        ~/Documents path does not accidentally pass the check.
        """
        candidates: list[Path] = []

        # 1. User-configured folder (settings key "projects_folder")
        pf = self.settings.get("projects_folder", "")
        if pf:
            candidates.append(Path(pf))

        # 2. Default user documents area
        candidates.append(Path.home() / "Documents" / "AUTOMATION_FACTORY_PROJECTS")

        # 3. Bundled examples inside the factory tree
        candidates.append(FACTORY_ROOT / "examples")

        # Filter to existing directories only.
        return [p for p in candidates if p.exists() and p.is_dir()]

    def _check_open_project_path(self, p: Path) -> str | None:
        """Validate *p* against the project-root whitelist.

        Returns None if the path is allowed, or an error string if it is not.
        Fail-safe: if the whitelist is empty (no allowed roots exist on disk),
        the path is rejected — we never fall through to "allow everything".
        """
        allowed = self._allowed_project_roots()
        if not allowed:
            return (
                "No allowed project root exists on disk. "
                "Create ~/Documents/AUTOMATION_FACTORY_PROJECTS or set "
                "'projects_folder' in settings. (O-2)"
            )
        for root in allowed:
            if self._is_path_under(p, root):
                return None  # allowed
        return (
            f"Path '{p}' is outside all allowed project roots "
            f"({', '.join(str(r) for r in allowed)}). "
            "Move the project to an allowed location or add its parent to "
            "'projects_folder' in settings. (O-2)"
        )

    def _build_tree(self) -> list[dict]:
        if not self.root:
            return []
        # Load factory/system dir exclusion lists from project_manager if available
        factory_dirs: set[str] = set()
        try:
            from workbench.core.project_manager import FACTORY_DIRS  # type: ignore
            factory_dirs = FACTORY_DIRS
        except Exception:
            factory_dirs = {
                "01_GLOBAL_STANDARDS", "02_PROJECT_TYPES", "03_DOMAIN_TOOLS",
                "04_AI_PROMPTS", "05_SCRIPTS", "06_KNOWLEDGE_BASE",
                "07_PROJECT_TEMPLATE", "08_METADATA_INPUT", "09_HARDWARE_LIBRARY",
                "_archive", "docs", "examples", "workbench", "webgui",
                ".venv", "node_modules",
            }
        out: list[dict] = []
        try:
            entries = sorted(
                self.root.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except Exception:
            return out
        for p in entries:
            if p.name.startswith(".") or p.name == "__pycache__":
                continue
            # Hide factory/system dirs — only customer project files shown
            if p.is_dir() and p.name in factory_dirs:
                continue
            node = {
                "name": p.name,
                "kind": _kind(p),
                "depth": 0,
                "open": False,
                "path": p.name,
            }
            s = _status_for(p)
            if s:
                node["status"] = s
            out.append(node)
        return out

    def _prompts(self) -> list[dict]:
        pdir = FACTORY_ROOT / "04_AI_PROMPTS"
        items: list[dict] = []
        try:
            for sub in sorted(pdir.glob("**/*.md"))[:12]:
                items.append({"title": sub.stem, "gate": 4, "path": str(sub.relative_to(FACTORY_ROOT)).replace("\\", "/")})
        except Exception:
            pass
        if not items:
            items = [
                {"title": "code_gen.motor_fb", "gate": 4, "path": ""},
                {"title": "review.safety",     "gate": 5, "path": ""},
            ]
        return items

    def _library_data(self) -> list[dict]:
        try:
            from workbench.core.library_store import list_blocks  # type: ignore
            blocks = list_blocks()
            return [
                {
                    "name": b.name,
                    "category": b.category,
                    "ver": b.version,
                    "platform": b.platform,
                    "desc": b.description,
                    "ports": b.ports,
                }
                for b in blocks
            ]
        except Exception:
            return [
                {
                    "name": "FB_Motor_Standard",
                    "category": "motor",
                    "ver": "1.0.0",
                    "platform": "S7-1500",
                    "desc": "Standard motor FB (DOL drive, run feedback, fault).",
                    "ports": [
                        {"name": "Enable", "type": "BOOL", "direction": "IN"},
                        {"name": "Drive",  "type": "BOOL", "direction": "OUT"},
                        {"name": "Run",    "type": "BOOL", "direction": "IN"},
                    ],
                }
            ]

    # ------------------------------------------------------------------
    # State & settings
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        st   = self._project_state()
        # O-1 / R-O-1: collect warnings from _project_state (parse errors) via
        # _attach_warnings so the flush pattern is consistent with all other
        # API methods that can emit _warn().
        # Gate position is RD-derived (same as get_gate_model), not the raw
        # stored counter — keeps the status bar consistent with the gate nav and
        # prevents an inflated counter from showing phantom progress.
        rd_statuses: dict[str, str] = {}
        try:
            from project_analyzer import analyze_project  # type: ignore
            analysis = analyze_project(self.root) if self.root else None
            if analysis is not None:
                rd_statuses = {k: v.status for k, v in analysis.rd_statuses.items()}
        except Exception:
            pass
        gate = _effective_gate(int(st.get("gate", st.get("current_gate", 0)) or 0),
                               rd_statuses, _rd_na_set(self.root, st, rd_statuses))
        platform = st.get("target_platform") or st.get("platform") or "S7-1500"
        model    = self.settings.get("ai_model") or "claude-sonnet-4-6"
        ptype    = (st.get("project_type") or "PROJECT").upper()
        tree     = self._build_tree()
        changes  = sum(1 for n in tree if n.get("status") == "mod")
        root_for_git = self.root or FACTORY_ROOT
        branch   = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root_for_git) or "main"
        return _attach_warnings({
            "version":      APP_VERSION,
            "project_name": self.root.name if self.root else "—",
            "project_path": str(self.root) if self.root else "",
            "project_type": ptype,
            "gate": gate, "gate_max": 7,
            "gate_name": GATE_NAMES[gate - 1] if 1 <= gate <= 7 else "",
            "gate_pct":  round((gate - 1) / 7 * 100),  # completed gates, consistent with gate nav
            "platform":  platform,
            "model":     model,
            "git_branch":  branch,
            "git_changes": f"{changes} changes" if changes else "clean",
            "git_change_count": changes,
            "theme":    self.settings.get("theme",    "dark"),
            "accent":   self.settings.get("accent",   "emerald"),
            "username": self.settings.get("username", ""),
            "default_file": self.default_open(),
            "tree":     tree,
            "actions":  [
                {"id": "analyze",        "label": "Analyze Project",  "icon": "sparkles",  "hint": "", "primary": True},
                {"id": "extract_io",     "label": "Extract IO List",  "icon": "table",     "hint": ""},
                {"id": "generate_scl",   "label": "Generate SCL",     "icon": "play",      "hint": ""},
                {"id": "validate",       "label": "Validate",         "icon": "check",     "hint": ""},
                {"id": "show_standards", "label": "Show Standards",   "icon": "file-text", "hint": ""},
                {"id": "export_tia",     "label": "Export TIA",       "icon": "upload",    "hint": ""},
            ],
            "prompts":     self._prompts(),
            "library":     self._library_data(),
            "diagnostics": [
                # NOTE: the old "prompt copies to clipboard" flow was retired
                # 2026-06-29 — this boot line described a dead feature until
                # the 2026-07-06 user audit caught it.
                {"sev": "dim", "line": "Workbench ready — select a file or run an action from the right rail."},
            ],
        })

    def get_settings(self) -> dict:
        catalog: dict = {}
        try:
            from ai_client import PROVIDER_CATALOG  # type: ignore
            for k, v in PROVIDER_CATALOG.items():
                meta = _PROVIDER_META.get(k, {})
                catalog[k] = {
                    "display":              v.get("display", k),
                    "models":               list(v.get("models", []) or []),
                    "default":              v.get("default_model", ""),
                    "key_url":              v.get("key_url", ""),
                    "badge":                meta.get("badge", ""),
                    "recommended_for":      meta.get("recommended_for", []),
                    "default_max_tokens":   meta.get("default_max_tokens", 16384),
                }
        except Exception:
            catalog = {
                "anthropic": {
                    "display": "Anthropic",
                    "models":  ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
                    "default": "claude-sonnet-4-6",
                    "key_url": "https://console.anthropic.com/",
                    "badge":   "SCL generation · Code analysis · Safety",
                    "recommended_for": ["scl_generation", "default"],
                    "default_max_tokens": 32768,
                },
                "openai": {
                    "display": "OpenAI",
                    "models":  ["gpt-4o", "gpt-4o-mini", "o1"],
                    "default": "gpt-4o",
                    "key_url": "https://platform.openai.com/",
                    "badge":   "",
                    "recommended_for": [],
                    "default_max_tokens": 16384,
                },
            }
        # C-A2: NEVER ship plaintext API keys across the JS bridge. Expose only
        # a non-secret status flag per provider so the UI can show a
        # "stored / plaintext / empty" indicator.
        raw_keys = self.settings.get("api_keys", {}) or {}
        api_keys_status = {p: _api_key_status(v) for p, v in raw_keys.items()}
        settings = self.settings
        if settings.get("ai_mode") == "cursor":
            settings["ai_mode"] = "api"
        return {
            "theme":             settings.get("theme",       "dark"),
            "accent":            settings.get("accent",      "emerald"),
            "ai_mode":           settings.get("ai_mode",     "api"),
            "ai_provider":       self.settings.get("ai_provider", "anthropic"),
            "ai_model":          self.settings.get("ai_model",    ""),
            "api_keys_status":   api_keys_status,
            "keyring_available": _KEYRING_OK,
            "username":          self.settings.get("username",    ""),
            "catalog":           catalog,
            "provider_settings": self.settings.get("provider_settings") or {},
            "task_routing":      self.settings.get("task_routing") or _DEFAULT_TASK_ROUTING,
        }

    def save_settings_data(self, data: dict) -> bool:
        for k in ("theme", "accent", "ai_mode", "ai_provider", "ai_model", "username"):
            if k in data:
                self.settings[k] = data[k]
        if isinstance(data.get("provider_settings"), dict):
            ps = self.settings.setdefault("provider_settings", {})
            for prov, cfg in data["provider_settings"].items():
                if isinstance(cfg, dict):
                    ps.setdefault(prov, {})
                    if "model" in cfg:
                        ps[prov]["model"] = str(cfg["model"])
                    if "max_tokens" in cfg:
                        try:
                            ps[prov]["max_tokens"] = max(256, min(65536, int(cfg["max_tokens"])))
                        except (TypeError, ValueError):
                            pass
        if isinstance(data.get("task_routing"), dict):
            self.settings["task_routing"] = {
                k: str(v) for k, v in data["task_routing"].items() if k and v
            }
            # Keep ai_provider in sync with the default task routing entry.
            default_prov = self.settings["task_routing"].get("default")
            if default_prov:
                self.settings["ai_provider"] = default_prov
        if isinstance(data.get("api_keys"), dict):
            # C-A2: Only non-empty incoming values represent a real change.
            # An empty value from the UI means "user did not retype the key",
            # NOT "wipe the stored key". This prevents the JS bridge from
            # being able to silently delete keystore entries by sending {}.
            current = self.settings.setdefault("api_keys", {})
            for prov, key in data["api_keys"].items():
                if key:
                    current[prov] = key
        _save_settings(self.settings)
        # _save_settings replaces plaintext with the keystore sentinel on disk;
        # mirror that back into the in-memory settings so subsequent
        # get_settings() does not still see the plaintext we were just handed.
        try:
            persisted = _load_settings()
            if isinstance(persisted.get("api_keys"), dict):
                self.settings["api_keys"] = persisted["api_keys"]
        except Exception:
            pass
        return True

    def save_settings(self, data: dict) -> bool:
        """Alias used by the JS frontend (Backend.save_settings)."""
        return self.save_settings_data(data)

    def get_provider_for_task(self, task: str) -> dict:
        """Return {provider, model, max_tokens} for the given task name.

        Looks up task_routing[task], verifies the provider has a key set,
        and falls back to the default provider if not. Used by retrofit
        pre-analysis and any future multi-provider workflow steps.
        """
        routing = self.settings.get("task_routing") or _DEFAULT_TASK_ROUTING
        provider = routing.get(task) or routing.get("default") or \
                   self.settings.get("ai_provider", "anthropic")
        # Fall back to default if chosen provider has no key.
        if not self._resolve_api_key(provider):
            fallback = routing.get("default") or self.settings.get("ai_provider", "anthropic")
            if fallback != provider:
                provider = fallback
        ps = (self.settings.get("provider_settings") or {}).get(provider) or {}
        model = ps.get("model") or self.settings.get("ai_model") or ""
        max_tokens = ps.get("max_tokens") or \
                     _PROVIDER_META.get(provider, {}).get("default_max_tokens", 16384)
        out = {"provider": provider, "model": model,
               "max_tokens": int(max_tokens)}
        try:
            from ai_client import AIClient  # type: ignore
            cap = int(AIClient._PROVIDER_MAX_OUTPUT.get(provider) or 0)
        except Exception:
            cap = 0                     # unknown cap (or mocked client) — no warning
        if task in _LONG_OUTPUT_TASKS and 0 < cap < _LONG_OUTPUT_MIN_CAP:
            out["warning"] = (
                f"{provider} is hard-capped at {cap} output tokens — "
                f"'{task}' drafts (RD05/09/10 tables, SCL) can be cut "
                "mid-table. Route this task to anthropic or google in "
                "Settings → Task routing.")
        return out

    def set_theme(self, theme: str) -> bool:
        self.settings["theme"] = "light" if theme == "light" else "dark"
        _save_settings(self.settings)
        return True

    def test_api(self, provider: str, key: str) -> dict:
        try:
            from ai_client import test_api_key  # type: ignore
            # Empty key from UI means "test the stored key" (field is blank for security).
            resolved = key or self._resolve_api_key(provider)
            if not resolved:
                return {"ok": False, "msg": "No key configured — enter one above and save first."}
            ok, msg = test_api_key(provider, resolved)
            return {"ok": bool(ok), "msg": str(msg)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # File tree & file I/O
    # ------------------------------------------------------------------

    def default_open(self) -> str | None:
        if not self.root:
            return None
        for sub in ("03_PLC", "SCL", ""):
            d = (self.root / sub) if sub else self.root
            if not d.exists():
                continue
            try:
                for p in sorted(d.rglob("*.scl")):
                    return str(p.relative_to(self.root)).replace("\\", "/")
            except Exception:
                pass
        try:
            for p in sorted(self.root.iterdir()):
                if p.is_file() and not p.name.startswith("."):
                    return p.name
        except Exception:
            pass
        return None

    def list_dir(self, relpath: str) -> list[dict]:
        target = self._safe(relpath)
        if target is None or not target.is_dir():
            return []
        out: list[dict] = []
        try:
            entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception:
            return out
        for p in entries:
            if p.name.startswith(".") or p.name == "__pycache__":
                continue
            try:
                rel = str(p.relative_to(self.root)).replace("\\", "/")
            except Exception:
                continue
            node = {"name": p.name, "kind": _kind(p), "path": rel}
            s = _status_for(p)
            if s:
                node["status"] = s
            out.append(node)
        return out

    def _is_io_file(self, p: Path) -> bool:
        name_up = p.name.upper()
        return (
            "RD01" in name_up and "IO" in name_up
            and p.suffix.lower() in (".md", ".xlsx", ".xls")
        )

    def read_file(self, relpath: str) -> dict:
        target = self._safe(relpath)
        if target is None or not target.exists() or target.is_dir():
            return {"name": relpath, "kind": "text", "text": "(file not found)"}
        # Serve IO list files as structured data for the grid editor
        if self._is_io_file(target):
            return self.read_io_list(relpath)
        # In-GUI xlsx preview (2026-07-07): no engineer-facing file should
        # require leaving the app — only customer delivery goes outside.
        if target.suffix.lower() in (".xlsx", ".xls"):
            return self._read_xlsx_preview(target)
        try:
            if target.stat().st_size > 1_500_000:
                return {"name": target.name, "kind": "text", "text": "(file too large to preview — open externally)"}
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            text = f"(could not read: {e})"
        return {"name": target.name, "kind": _kind(target), "text": text}

    @staticmethod
    def _read_xlsx_preview(target: Path) -> dict:
        """First sheet as a row grid (read-only preview; capped honestly)."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(target), read_only=True,
                                        data_only=True)
            ws = wb.active
            rows, truncated = [], False
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 300:
                    truncated = True
                    break
                rows.append(["" if c is None else str(c) for c in row[:40]])
            wb.close()
            return {"name": target.name, "kind": "xlsx", "sheet": ws.title,
                    "rows": rows, "truncated": truncated,
                    "text": f"({target.name} — {len(rows)} rows preview)"}
        except Exception as e:
            return {"name": target.name, "kind": "text",
                    "text": f"(xlsx preview failed: {e} — open externally)"}

    def read_io_list(self, relpath: str) -> dict:
        """Read an IO list file (.md or .xlsx) and return structured row data."""
        target = self._safe(relpath)
        if target is None or not target.exists():
            return {"name": relpath, "kind": "io_list", "rows": [], "frontmatter": {}}
        try:
            from workbench.core.io_list_io import read_md, read_xlsx  # type: ignore
            if target.suffix.lower() in (".xlsx", ".xls"):
                rows, fm = read_xlsx(target)
            else:
                rows, fm = read_md(target)
            return {
                "name": target.name,
                "kind": "io_list",
                "rows": [vars(r) for r in rows],
                "frontmatter": _json_safe_fm(fm),
            }
        except Exception as e:
            return {"name": target.name if target else relpath, "kind": "io_list", "rows": [], "frontmatter": {}, "error": str(e)}

    def save_io_list(self, relpath: str, rows: list) -> dict:
        """Save IO list rows back to .md (and sync .xlsx alongside).

        C-A1: Preserve existing YAML frontmatter (project_id, output_language,
        customer, data_classification, source_platform, …). The GUI grid only
        edits the signal rows; dropping the frontmatter on save would silently
        lose project metadata downstream consumers (read_md, classification
        guard, language switch) rely on.
        """
        target = self._safe(relpath)
        if target is None:
            return {"ok": False, "msg": "Path not allowed"}
        try:
            from workbench.core.io_list_io import IORow, read_md, sync  # type: ignore
            io_rows = [IORow(**{k: str(v) for k, v in r.items() if k in IORow.__dataclass_fields__}) for r in (rows or [])]
            md_path = target if target.suffix.lower() == ".md" else target.with_suffix(".md")
            fm: dict = {}
            if md_path.is_file():
                try:
                    _, fm = read_md(md_path)
                    fm = dict(fm or {})
                except Exception:
                    fm = {}
            sync(md_path, io_rows, frontmatter=fm)
            return {"ok": True, "msg": f"Saved {md_path.name} ({len(io_rows)} rows)"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def validate_io_list(self, relpath: str) -> dict:
        """Validate IO list rows and return list of issues."""
        target = self._safe(relpath)
        if target is None:
            return {"ok": False, "issues": []}
        try:
            from workbench.core.io_list_io import read_md, read_xlsx  # type: ignore
            from workbench.core.io_validator import validate_rows  # type: ignore
            if target.suffix.lower() in (".xlsx", ".xls"):
                rows, _ = read_xlsx(target)
            else:
                rows, _ = read_md(target)
            st = self._project_state()
            platform = st.get("target_platform") or st.get("platform") or ""
            issues = validate_rows(rows, platform)
            # S-7 (B-P4): persist the result so _gate_advance_blockers can
            # refuse to advance on IO errors. Separate key — last_validation
            # carries the SCL/compile evidence and must not be clobbered.
            if self.root:
                err_count = sum(1 for i in issues if i.severity == "error")
                try:
                    self._update_state_fields({"last_io_validation": {
                        "errors": err_count, "file": target.name}})
                except Exception:
                    pass
            return _attach_warnings({
                "ok": True,
                "issues": [{"row": i.row_index, "column": i.column, "severity": i.severity, "message": i.message} for i in issues],
            })
        except Exception as e:
            return _attach_warnings({"ok": False, "issues": [], "error": str(e)})

    def export_io_xlsx(self, relpath: str) -> dict:
        """Export IO list to Excel in the REPORTS directory."""
        target = self._safe(relpath)
        if target is None or not self.root:
            return {"ok": False, "msg": "No project open or invalid path"}
        try:
            from workbench.core.io_list_io import read_md, read_xlsx, write_xlsx  # type: ignore
            if target.suffix.lower() in (".xlsx", ".xls"):
                rows, fm = read_xlsx(target)
            else:
                rows, fm = read_md(target)
            reports = self.root / "REPORTS"
            reports.mkdir(exist_ok=True)
            out = reports / target.with_suffix(".xlsx").name
            write_xlsx(out, rows, fm)
            rel = str(out.relative_to(self.root)).replace("\\", "/")
            return {"ok": True, "msg": f"Exported to {rel}", "path": rel}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def save_file(self, relpath: str, content: str) -> dict:
        """Save editor content back to disk (only safe extensions allowed)."""
        target = self._safe(relpath)
        if target is None:
            return {"ok": False, "msg": "Path not allowed"}
        if target.suffix.lower() not in SAFE_WRITE_EXT:
            return {"ok": False, "msg": f"Extension {target.suffix} not writable"}
        # W-A6: refuse to overwrite control-plane files. Gate state /
        # classification / audit history changes must go through the typed
        # API (advance_gate, set_classification …) which validates the input
        # and appends to gate_history with a hash chain.
        if target.name in CONTROL_FILES:
            return {"ok": False, "msg": (
                f"{target.name} is a control file and cannot be edited as raw "
                "text. Use the dedicated controls (gate advance, settings) so "
                "the change is validated and audit-logged. (W-A6)"
            )}
        try:
            target.write_text(content, encoding="utf-8")
            return {"ok": True, "msg": f"Saved {target.name}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def new_file(self, parent_rel: str, name: str) -> dict:
        """Create a new empty file in a project subfolder."""
        parent = self._safe(parent_rel) if parent_rel else self.root
        if parent is None or not parent.is_dir():
            return {"ok": False, "msg": "Invalid parent folder"}
        target = parent / name
        if target.exists():
            return {"ok": False, "msg": f"{name} already exists"}
        try:
            target.touch()
            rel = str(target.relative_to(self.root)).replace("\\", "/")
            return {"ok": True, "path": rel, "name": name}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def new_folder(self, parent_rel: str, name: str) -> dict:
        """Create a new subfolder inside a project folder."""
        parent = self._safe(parent_rel) if parent_rel else self.root
        if parent is None or not parent.is_dir():
            return {"ok": False, "msg": "Invalid parent folder"}
        target = parent / name
        if target.exists():
            return {"ok": False, "msg": f"{name} already exists"}
        try:
            target.mkdir(parents=False)
            rel = str(target.relative_to(self.root)).replace("\\", "/")
            return {"ok": True, "path": rel, "name": name}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def delete_file(self, relpath: str) -> dict:
        """Delete a file (not directories)."""
        target = self._safe(relpath)
        if target is None or not target.exists() or target.is_dir():
            return {"ok": False, "msg": "File not found or is a directory"}
        # W-A6 extension: block deletion of control-plane files (mirrors save_file guard).
        if target.name in CONTROL_FILES:
            return {"ok": False, "msg": (
                f"{target.name} is a control file and cannot be deleted directly. "
                "Use the dedicated controls (gate advance, settings) so the change "
                "is validated and audit-logged. (W-A6)"
            )}
        try:
            target.unlink()
            return {"ok": True, "msg": f"Deleted {target.name}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def rename_file(self, relpath: str, new_name: str) -> dict:
        """Rename a file within the same directory."""
        target = self._safe(relpath)
        if target is None or not target.exists():
            return {"ok": False, "msg": "File not found"}
        # W-A6 extension: block renaming to/from control-plane files.
        if target.name in CONTROL_FILES or new_name in CONTROL_FILES:
            return {"ok": False, "msg": (
                f"Renaming control files ({target.name} ↔ {new_name}) is not allowed. "
                "Use the dedicated controls (gate advance, settings). (W-A6)"
            )}
        dest = target.parent / new_name
        if dest.exists():
            return {"ok": False, "msg": f"{new_name} already exists"}
        try:
            target.rename(dest)
            rel = str(dest.relative_to(self.root)).replace("\\", "/")
            return {"ok": True, "path": rel, "name": new_name}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Pipeline / Analysis (M5)
    # ------------------------------------------------------------------

    def run_analysis(self) -> dict:
        """Run full project analysis and return structured results for the UI."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from project_analyzer import analyze_project  # type: ignore
            analysis = analyze_project(self.root)
            rd_list = [
                {
                    "rd_id": rd_id,
                    "title": rd.title,
                    "status": rd.status,
                    "can_run": rd.can_run,
                    "missing_inputs": rd.missing_inputs,
                    "human_required": rd.human_required,
                    "ai_prompt": rd.ai_prompt,
                }
                for rd_id, rd in analysis.rd_statuses.items()
            ]
            return {
                "ok": True,
                "overall_pct": analysis.overall_pct,
                "recommended_next": analysis.recommended_next,
                "rd_list": rd_list,
                "has_input": analysis.has_input,
                "has_parsed_md": analysis.has_parsed_md,
            }
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # RAG safety helpers (Aşama D)
    # ------------------------------------------------------------------

    def _rag_safety_check(self, query: str) -> tuple[list[dict], str]:
        """Query RAG index for critical(safety) records matching query.

        Works in both BM25 (offline, no API key) and semantic (OpenAI) mode.
        Returns (warnings_list, rag_mode) where rag_mode is "semantic", "bm25", or
        "unavailable" (no index / error).  warnings_list is [] when nothing found or on
        any error — never raises.
        """
        try:
            import os as _os2
            import sys as _sys2
            scripts_path = str(FACTORY_ROOT / "05_SCRIPTS")
            if scripts_path not in _sys2.path:
                _sys2.path.insert(0, scripts_path)
            from rag.retrieve import retrieve as _rag_retrieve  # type: ignore
            openai_key = (self.settings.get("api_keys") or {}).get("openai", "")
            if not openai_key:
                openai_key = _os2.environ.get("OPENAI_API_KEY", "")
            # B-00/B-01 fix: category_filter="safety" + not_verified=True
            # All KB safety records are NOT_VERIFIED by default; including them
            # with the not_verified flag ensures the warning chain is never silent.
            results = _rag_retrieve(query, top_k=10, not_verified=True,
                                    category_filter="safety",
                                    api_key=openai_key or None)
            # Derive mode from first result; fall back to "semantic" if index was
            # empty (no results means semantic ran but found nothing — still valid).
            rag_mode: str = results[0]["_rag_mode"] if results else "semantic"
            warnings = [
                {
                    "entry_id": r["entry_id"],
                    "severity": r["severity"],
                    "chunk_text": (r.get("chunk_text") or "")[:300],
                    "not_verified": r.get("not_verified", False),
                    "_rag_mode": r.get("_rag_mode", rag_mode),
                    "_rag_fallback_reason": r.get("_rag_fallback_reason"),
                }
                for r in results if r.get("rag_warning")
            ]
            return warnings, rag_mode
        except Exception as _rag_exc:
            import logging as _log_rag
            _log_rag.warning("[RAG] _rag_safety_check failed: %s", _rag_exc)
            return [], "unavailable"

    def _rag_vendor_notes(self, query: str, category_filter: str) -> list[dict]:
        """Return VERIFIED, non-safety KB entries for a given category.

        Used to inject informational context (vendor quirks, comms hints) into
        generated files as comments.  Works in BM25 mode without API key.
        Returns [] on any error — never raises.
        """
        try:
            import os as _os3
            import sys as _sys3
            scripts_path = str(FACTORY_ROOT / "05_SCRIPTS")
            if scripts_path not in _sys3.path:
                _sys3.path.insert(0, scripts_path)
            from rag.retrieve import retrieve as _rag_retrieve  # type: ignore
            openai_key = (self.settings.get("api_keys") or {}).get("openai", "")
            if not openai_key:
                openai_key = _os3.environ.get("OPENAI_API_KEY", "")
            results = _rag_retrieve(query, top_k=5, not_verified=False,
                                    category_filter=category_filter,
                                    api_key=openai_key or None)
            return [
                {
                    "entry_id": r["entry_id"],
                    "severity": r["severity"],
                    "category": r["category"],
                    "chunk_text": (r.get("chunk_text") or "").split("\n")[0].strip("# ").strip()[:120],
                }
                for r in results if not r.get("rag_warning")
            ]
        except Exception as _vn_exc:
            import logging as _log_vn
            _log_vn.warning("[RAG] _rag_vendor_notes failed: %s", _vn_exc)
            return []

    @staticmethod
    def _inject_rag_context_block(scl_path: "Path", notes: list[dict]) -> None:
        """Prepend a // RAG_CONTEXT comment block to a generated SCL file."""
        if not scl_path or not scl_path.exists() or not notes:
            return
        lines = [
            "// RAG_CONTEXT: Relevant field experience (VERIFIED KB entries)",
            "// Not a substitute for engineering judgment — review before editing",
        ]
        for n in notes[:5]:
            entry_id = n.get("entry_id", "?")
            snippet = (n.get("chunk_text") or "").strip()[:100]
            lines.append(f"//   [{entry_id}] {snippet}")
        lines.append("//")
        lines.append("")
        block = "\n".join(lines) + "\n"
        existing = scl_path.read_text(encoding="utf-8")
        scl_path.write_text(block + existing, encoding="utf-8")

    @staticmethod
    def _inject_rag_safety_box(md_path: Path, warnings: list[dict]) -> None:
        """Prepend a ⚠️ SAFETY NOTU block to a generated MD file."""
        if not md_path or not md_path.exists() or not warnings:
            return
        lines = [
            "> ⚠️ **SAFETY NOTU** — RAG sistemi aşağıdaki kritik güvenlik kayıtlarını buldu. Mühendis doğrulaması gereklidir:",
            ">",
        ]
        for w in warnings[:5]:
            entry_id = w.get("entry_id", "?")
            snippet = (w.get("chunk_text") or "").split("\n")[0].strip("# ").strip()[:100]
            lines.append(f"> - **[{entry_id}]** {snippet}")
        lines.append(">")
        lines.append("")
        box = "\n".join(lines) + "\n"
        existing = md_path.read_text(encoding="utf-8")
        md_path.write_text(box + existing, encoding="utf-8")

    # ------------------------------------------------------------------
    # Code generation + Validation (M6)
    # ------------------------------------------------------------------

    def generate_ob1(self, ob_name: str = "OB_Main", overwrite: bool = False) -> dict:
        """Generate OB1 SCL from all SCL blocks in project."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from ob1_generator import write_ob1  # type: ignore
            result = write_ob1(self.root, ob_name=ob_name, overwrite=bool(overwrite))
            fb_count = len(result.fb_blocks)
            fc_count = len(result.fc_blocks)
            lines = [f"OB1 generated: {result.ob_name}", f"FBs: {fb_count}, FCs: {fc_count}"]
            if result.warnings:
                for w in result.warnings: lines.append(f"  ! {w}")
            if result.output_path:
                lines.append(f"Written to: {result.output_path.name}")
            # RAG Aşama D: VERIFIED vendor_quirk + comms notes → SCL comments
            rag_notes = (
                self._rag_vendor_notes("vendor quirk integration workaround", "vendor_quirk")
                + self._rag_vendor_notes("PROFINET Modbus comms cycle time loop", "comms")
            )
            if rag_notes and result.output_path:
                self._inject_rag_context_block(result.output_path, rag_notes)
            # RAG Aşama D: critical(safety) warnings → returned to caller
            rag_warnings, rag_mode = self._rag_safety_check(
                "PROFINET Modbus vendor integration SCL safety"
            )
            return {
                "ok": True,
                "msg": "\n".join(lines),
                "output_path": str(result.output_path) if result.output_path else "",
                "rag_warnings": rag_warnings,
                "rag_notes": rag_notes,
                "rag_mode": rag_mode,
            }
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def generate_iec_tags(self) -> dict:
        """Parse RD01 signals and generate IEC-style tag file."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from iec_tag_generator import parse_rd01_signals, generate_tags  # type: ignore
            signals = parse_rd01_signals(self.root)
            result  = generate_tags(signals)
            lines = [f"IEC tags generated: {len(result.tags)} tags"]
            if result.duplicates:
                lines.append(f"  Duplicates: {', '.join(result.duplicates[:5])}")
            if result.warnings:
                for w in result.warnings[:5]: lines.append(f"  ! {w}")
            if result.output_path:
                lines.append(f"Written to: {result.output_path.name}")
            return {"ok": True, "msg": "\n".join(lines), "tag_count": len(result.tags)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def validate_scl_file(self, relpath: str) -> dict:
        """Validate a single SCL file; returns issues list."""
        target = self._safe(relpath)
        if target is None or not target.exists():
            return {"ok": False, "issues": [], "msg": "File not found"}
        try:
            from scl_validator import validate_scl  # type: ignore
            from code_verifier import verify  # type: ignore
            content = target.read_text(encoding="utf-8", errors="replace")
            res = validate_scl(content, target)
            issues = [{"line": i.line, "message": i.message, "severity": i.severity} for i in res.issues]
            # Also run builtin verifier
            vres = verify(content)
            for vi in vres.issues:
                issues.append({"line": getattr(vi, "line", 0), "message": vi.message, "severity": vi.severity})
            return {
                "ok": True,
                "file": target.name,
                "errors": res.error_count,
                "warnings": res.warning_count,
                "issues": issues,
            }
        except Exception as e:
            return {"ok": False, "issues": [], "msg": str(e)}

    def validate_all_scl(self) -> dict:
        """Validate all SCL files in the project."""
        if not self.root:
            return {"ok": False, "files": [], "msg": "No project open"}
        try:
            from scl_validator import validate_scl, SCOPE_WARNING  # type: ignore
            files_checked: list[dict] = []
            total_errors = 0
            for scl_path in sorted(self.root.rglob("*.scl")):
                try:
                    content = scl_path.read_text(encoding="utf-8", errors="replace")
                    res = validate_scl(content, scl_path)
                    rel = str(scl_path.relative_to(self.root)).replace("\\", "/")
                    files_checked.append({"file": rel, "errors": res.error_count, "warnings": res.warning_count})
                    total_errors += res.error_count
                except Exception:
                    pass
            return {
                "ok": True,
                "files": files_checked,
                "total_errors": total_errors,
                "scope": "structural_only",
                "scope_warning": SCOPE_WARNING,
            }
        except Exception as e:
            return {"ok": False, "files": [], "msg": str(e)}

    # ------------------------------------------------------------------
    # Export / Reports / Hardware (M7)
    # ------------------------------------------------------------------

    def generate_fat(self, test_type: str = "FAT", lang: str = "de",
                     pdf: bool = False) -> dict:
        """Generate FAT/SAT test protocol(s).

        SAT v2 (Faz 1/6): the GUI modal passes test_type (FAT|SAT|BOTH),
        lang (de|en|tr, default de) and pdf.  Defaults keep the legacy
        no-argument behaviour (single FAT document).

        B-P5 / S-17: Returns ok=False with a user-visible reason when RD05
        (Safety Requirements) is absent, empty, or template-only.  No FAT
        output is written in that case (fail-closed).
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from fat_protocol import run_protocol_set, Rd05BlockedError  # type: ignore
            results = run_protocol_set(
                self.root, test_type=test_type, lang=lang, pdf=bool(pdf),
            )
            lines: list[str] = []
            for result in results:
                lines.append(
                    f"{result.test_type} protocol: "
                    f"{result.md_path.name if result.md_path else '—'}"
                )
                if result.pdf_path:
                    lines.append(f"  PDF: {result.pdf_path.name}")
                lines.append(f"  Tests: {result.test_count}")
                for w in (result.warnings or []):
                    lines.append(f"  ! {w}")
                    # Faz 2.3: the SISTEMA-pending state is surfaced in the
                    # GUI warning feed too, not only inside the document.
                    if "SISTEMA" in w:
                        _warn(w, category="safety")
            ok = all(r.ok for r in results) and bool(results)
            # reveal_path target: the first produced MD (existing GUI pattern).
            # Paths MUST be project-relative — reveal_path (I-A3) refuses absolute.
            first_md = next((r.md_path for r in results if r.md_path), None)
            # RAG safety check: inject ⚠️ box into generated docs and surface warnings
            rag_warnings, rag_mode = self._rag_safety_check(
                "E-stop safety interlock SIL PL proof test F-CPU certificate"
            )
            if rag_warnings:
                for res in results:
                    self._inject_rag_safety_box(res.md_path, rag_warnings)
            return {
                "ok": ok,
                "msg": "\n".join(lines),
                "path": self._relpath(first_md) if first_md else "",
                "paths": [self._relpath(r.md_path) for r in results if r.md_path],
                "rag_warnings": rag_warnings,
                "rag_mode": rag_mode,
            }
        except (Rd05BlockedError,) as e:
            return {
                "ok": False,
                "msg": str(e),
                "rd05_blocked": True,
            }
        except ValueError as e:
            # invalid test_type/lang from the UI — honest message, no output
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def generate_customer_report(self) -> dict:
        """Generate customer report (MD/PDF) in REPORTS dir.

        C-2 fix: ReportPreconditionError is raised by run_report when Gate 7
        has not been approved or RD05 is still DRAFT_UNVERIFIED.  The error is
        surfaced to the UI as a structured message rather than swallowed.
        """
        if not self.root:
            return {"ok": False, "msg": "No project open", "rag_warnings": [], "rag_mode": "unavailable"}
        # RAG safety check runs first — present in ALL return paths (Aşama D)
        rag_warnings, rag_mode = self._rag_safety_check(
            "vendor device safety compliance certificate critical"
        )
        try:
            from customer_report import run_report, ReportPreconditionError  # type: ignore
            result = run_report(self.root)
            lines = [f"Customer report: {result.output_path.name if result.output_path else '—'}"]
            for w in (result.warnings or []): lines.append(f"  ! {w}")
            if rag_warnings:
                self._inject_rag_safety_box(result.output_path, rag_warnings)
            return {
                "ok": result.ok,
                "msg": "\n".join(lines),
                "path": self._relpath(result.output_path) if result.output_path else "",
                "rag_warnings": rag_warnings,
                "rag_mode": rag_mode,
            }
        except ReportPreconditionError as exc:
            return {
                "ok": False,
                "precondition_error": True,
                "reasons": exc.reasons,
                "msg": "Customer report blocked — preconditions not met:\n"
                       + "\n".join(f"  • {r}" for r in exc.reasons),
                "rag_warnings": rag_warnings,
                "rag_mode": rag_mode,
            }
        except Exception as e:
            return {"ok": False, "msg": str(e), "rag_warnings": rag_warnings, "rag_mode": rag_mode}

    # ------------------------------------------------------------------
    # SISTEMA support (Faz 2) — the software reminds and documents; the
    # engineer calculates and signs.  Records are engineer declarations
    # (same pattern as the Gate-6 manual-test confirmation).
    # ------------------------------------------------------------------

    def get_sistema_status(self) -> dict:
        """RD05 safety functions + engineer records + pending list."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from sistema_support import sistema_status  # type: ignore
            status = sistema_status(self.root)
            return _attach_warnings({"ok": True, **status})
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def add_sistema_record(self, function: str, file: str = "",
                           achieved_pl: str = "", engineer: str = "") -> dict:
        """Append an engineer declaration to PROJECT_STATE.sistema_records.

        The entire read-modify-write inside sistema_support.add_sistema_record
        is wrapped in _state_lock so it is serialised with every other
        PROJECT_STATE.json writer in this class (_save_state,
        _update_state_fields).  Single lock, no nesting — no deadlock risk.
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from sistema_support import add_sistema_record  # type: ignore
            with self._state_lock:
                record = add_sistema_record(
                    self.root, function, file=file,
                    achieved_pl=achieved_pl, engineer=engineer,
                )
            return _attach_warnings({"ok": True, "record": record})
        except ValueError as e:
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def delete_sistema_record(self, index: int) -> dict:
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from sistema_support import delete_sistema_record  # type: ignore
            with self._state_lock:
                ok = delete_sistema_record(self.root, int(index))
            return {"ok": ok, "msg": "" if ok else f"No record at index {index}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def generate_sistema_prep(self, lang: str = "de") -> dict:
        """Write _output/SISTEMA_PREP_<ts>.md (engineer's SISTEMA template)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from sistema_support import generate_sistema_prep, SistemaInputError  # type: ignore
            result = generate_sistema_prep(self.root, lang=lang)
            for w in result.warnings:
                _warn(w, category="safety")
            return _attach_warnings({
                "ok": result.ok,
                "msg": f"SISTEMA prep: {result.md_path.name if result.md_path else '—'}"
                       + (f"\n  ! {'; '.join(result.warnings)}" if result.warnings else ""),
                "path": self._relpath(result.md_path) if result.md_path else "",
                "function_count": len(result.functions),
            })
        except SistemaInputError as e:
            return {"ok": False, "msg": str(e), "rd05_missing": True}
        except ValueError as e:
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def generate_ce_assessment(self, lang: str = "de", pdf: bool = False) -> dict:
        """CE essential-modification assessment (Faz 4) — retrofit projects.

        Greenfield: produced anyway with a visible non-blocking warning
        (user decision 2026-06-12)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from ce_assessment import generate_ce_assessment  # type: ignore
            result = generate_ce_assessment(self.root, lang=lang, pdf=bool(pdf))
            for w in result.warnings:
                _warn(w, category="safety")
            msg = [f"CE assessment: {result.md_path.name if result.md_path else '—'}"]
            if result.pdf_path:
                msg.append(f"  PDF: {result.pdf_path.name}")
            for w in result.warnings:
                msg.append(f"  ! {w}")
            return _attach_warnings({
                "ok": result.ok,
                "msg": "\n".join(msg),
                "path": self._relpath(result.md_path) if result.md_path else "",
                "is_retrofit": result.is_retrofit,
            })
        except ValueError as e:
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def _relpath(self, p) -> str:
        """Project-relative path string for the UI.

        reveal_path (I-A3) refuses absolute paths, so handlers must hand the UI
        a path relative to the project root. Falls back to the bare name when
        the path is somehow outside the root (still reveal-safe via _safe)."""
        try:
            return str(Path(p).relative_to(self.root))
        except (ValueError, TypeError):
            return Path(p).name if p else ""

    def reveal_path(self, relpath: str) -> dict:
        """Open the parent folder of relpath in Windows Explorer.

        I-A3: paths are resolved against the current project root only.
        Absolute paths from JS (e.g. "C:\\Windows") are refused — the
        previous "is_absolute and exists -> open it" branch let the bridge
        open arbitrary filesystem locations, and combined with any XSS in
        the embedded webview that became a small recon primitive.
        """
        try:
            folder = None
            if relpath:
                # Reject absolute paths and traversal — only project-relative.
                # Normalize backslashes first so "..\\foo" is caught on Linux too.
                p = Path(relpath.replace("\\", "/"))
                if p.is_absolute() or ".." in p.parts:
                    return {"ok": False, "msg": (
                        "Absolute and traversal paths are not allowed. "
                        "Only paths under the current project are accepted. (I-A3)"
                    )}
                safe = self._safe(relpath)
                if safe and safe.exists():
                    folder = safe.parent if safe.is_file() else safe
            if folder is None and self.root:
                folder = self.root / "REPORTS"
                folder.mkdir(parents=True, exist_ok=True)
            if folder is None:
                return {"ok": False, "msg": "Path not found"}
            import subprocess
            subprocess.Popen(["explorer", str(folder)])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def size_hardware(self, reserve_pct: int = 20) -> dict:
        """Run hardware sizing and return recommendations."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hardware_sizer import run_sizer  # type: ignore
            result = run_sizer(self.root, reserve_pct=int(reserve_pct))
            if result is None:
                return {"ok": False, "msg": "Hardware sizing returned no result (check IO list)"}
            # C-A3: surface hard errors (e.g. SAFE_* on non-F-CPU) as ok=False
            # so the UI cannot mistake a partial result for a valid BOM.
            errors = list(result.errors or [])
            return {
                "ok": not bool(errors),
                "io_count": result.io_count,
                "reserve_pct": result.reserve_pct,
                "platform": result.platform,
                "cpu": result.cpu,
                "head_station": result.head_station,
                "total_modules": result.total_modules,
                "recommendations": result.recommendations or [],
                "warnings": result.warnings or [],
                "errors": errors,
                "safety_misconfigured": bool(getattr(result, "safety_misconfigured", False)),
                "msg": errors[0] if errors else "",
            }
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_bom_library(self) -> dict:
        """Scan hardware library and return catalog."""
        lib_root = FACTORY_ROOT / "06_HARDWARE_LIB"
        if not lib_root.exists():
            lib_root = FACTORY_ROOT / "09_HARDWARE_LIBRARY"
        try:
            from bom_manager import scan_library  # type: ignore
            catalog = scan_library(lib_root)
            devices = [{"id": k, **{kk: str(vv) if isinstance(vv, Path) else vv for kk, vv in v.items()}} for k, v in catalog.items()]
            return {"ok": True, "devices": devices}
        except Exception as e:
            return {"ok": False, "devices": [], "msg": str(e)}

    def generate_bom(self, selected_devices: list) -> dict:
        """Generate BOM Excel from selected hardware devices."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from bom_manager import scan_library, generate_bom_xlsx  # type: ignore
            lib_root = FACTORY_ROOT / "06_HARDWARE_LIB"
            if not lib_root.exists():
                lib_root = FACTORY_ROOT / "09_HARDWARE_LIBRARY"
            catalog = scan_library(lib_root) if lib_root.exists() else {}
            ok = generate_bom_xlsx(self.root, selected_devices or [], catalog)
            path = str(self.root / "_input" / "hardware_BOM.xlsx") if ok else ""
            return {"ok": bool(ok), "msg": "BOM generated — hardware_BOM.xlsx" if ok else "BOM generation failed (openpyxl required)", "path": path}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Hardware workbench (2026-07-06) — the library page becomes a real
    # workspace: read/edit device MDs, create skeletons. Every path is
    # guarded to stay inside the hardware library root; edits are the
    # engineer's human-in-the-loop step, so verified/NOT_VERIFIED stays
    # exactly what the engineer wrote (never auto-set here).
    # ------------------------------------------------------------------

    @staticmethod
    def _hw_root() -> Path:
        lib_root = FACTORY_ROOT / "06_HARDWARE_LIB"
        return lib_root if lib_root.exists() else FACTORY_ROOT / "09_HARDWARE_LIBRARY"

    def _hw_path(self, rel_path: str) -> Path | None:
        """Resolve rel_path inside the hardware library; None if it escapes."""
        root = self._hw_root()
        if not rel_path or Path(rel_path).is_absolute():
            return None
        p = root / rel_path
        try:
            p.resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            return None
        return p

    @staticmethod
    def _rebuild_bm25_index() -> str:
        """Best-effort BM25 rebuild after a library edit (offline RAG mode).
        Returns a warning string ('' on success) — never raises."""
        try:
            import sys as _sys
            _scripts = str(FACTORY_ROOT / "05_SCRIPTS")
            if _scripts not in _sys.path:
                _sys.path.insert(0, _scripts)
            from rag.ingest import (  # type: ignore
                _save_bm25_index, build_bm25_index, collect_records,
            )
            records = collect_records()
            if records:
                _save_bm25_index(build_bm25_index(records))
            return ""
        except Exception as exc:
            return f"BM25 index not rebuilt: {exc}"

    def get_hw_library(self) -> dict:
        """Catalog for the hardware workbench: categories + per-device
        metadata incl. the verified state (the GUI must show NOT_VERIFIED
        honestly, never hide it)."""
        root = self._hw_root()
        try:
            from bom_manager import scan_library  # type: ignore
            catalog = scan_library(root)
        except Exception as e:
            return {"ok": False, "devices": [], "categories": [], "msg": str(e)}
        devices = []
        for did, info in sorted(catalog.items()):
            p = Path(info["path"])
            verified = part_no = subcat = ""
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    ls = line.strip()
                    if ls.startswith("verified:"):
                        verified = ls.split(":", 1)[1].strip().strip('"')
                    elif ls.startswith("part_number:"):
                        part_no = ls.split(":", 1)[1].strip().strip('"')
                    elif ls.startswith("subcategory:"):
                        subcat = ls.split(":", 1)[1].strip().strip('"')
            except Exception:
                pass
            devices.append({
                "id": did,
                "vendor": info.get("vendor", ""),
                "model": info.get("model", ""),
                "category": info.get("category", ""),
                "subcategory": subcat,
                "part_number": part_no,
                # fail-honest: an unreadable/unset field counts as NOT_VERIFIED
                "verified": verified or "NOT_VERIFIED",
                "rel_path": str(p.resolve().relative_to(root.resolve())
                                ).replace("\\", "/"),
            })
        cats = sorted({d["category"] for d in devices if d["category"]})
        return {"ok": True, "root": str(root), "devices": devices,
                "categories": cats}

    def get_device_text(self, rel_path: str) -> dict:
        """Full MD text of one library device (workbench editor)."""
        p = self._hw_path(rel_path)
        if p is None or not p.is_file() or p.suffix.lower() != ".md":
            return {"ok": False, "msg": "Device file not found in the hardware library"}
        try:
            return {"ok": True, "rel_path": rel_path,
                    "text": p.read_text(encoding="utf-8")}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def save_device_text(self, rel_path: str, text: str) -> dict:
        """Save an engineer's edit of a device MD, then refresh the offline
        RAG index so retrieval never serves a stale spec."""
        p = self._hw_path(rel_path)
        if p is None or p.suffix.lower() != ".md" or p.name.startswith("_"):
            return {"ok": False, "msg": "Save refused — path is outside the hardware library or not an editable device MD"}
        if not p.is_file():
            return {"ok": False, "msg": "Device file no longer exists — refresh the library"}
        if not (text or "").strip():
            return {"ok": False, "msg": "Refusing to save an empty device file"}
        try:
            p.write_text(text, encoding="utf-8")
        except Exception as e:
            return {"ok": False, "msg": str(e)}
        warn = self._rebuild_bm25_index()
        out = {"ok": True, "msg": f"Saved {p.name}"}
        if warn:
            out["rag_warn"] = warn
        return out

    def create_device(self, category: str, vendor: str, model: str) -> dict:
        """Create a NOT_VERIFIED skeleton MD (same section layout as the
        library) for manual authoring; refuses to overwrite."""
        import re as _re
        category = (category or "").strip().lower()
        vendor = (vendor or "").strip()
        model = (model or "").strip()
        if not category or not vendor or not model:
            return {"ok": False, "msg": "Category, vendor and model are required"}
        cat_dir = _re.sub(r"[^\w\-]", "_", category)[:40]
        vendor_dir = _re.sub(r"[^\w\-]", "_", vendor)[:40]
        stem = _re.sub(r"[^\w\-]", "_", model)[:60]
        device_id = f"{_re.sub(r'[^A-Z0-9]', '', vendor.upper())[:3] or 'DEV'}_{stem.upper()[:24]}"
        rel_path = f"{cat_dir}/{vendor_dir}/{stem}.md"
        p = self._hw_path(rel_path)
        if p is None:
            return {"ok": False, "msg": "Computed path escapes the hardware library — refused"}
        if p.exists():
            return {"ok": False, "msg": f"{rel_path} already exists — open it instead"}
        skeleton = f"""# {vendor} {model} — {cat_dir}

## metadata
```yaml
schema_version: "1.0"
device_id: "{device_id}"
vendor: "{vendor}"
model: "{model}"
category: "{cat_dir}"
subcategory: ""
part_number: "NOT_VERIFIED"
datasheet_ref: "NOT_VERIFIED"
library_path: "{rel_path}"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
```

> **DRAFT / NOT_VERIFIED.** Fill every section from the official datasheet.
> An engineer must verify part numbers before this entry is used in a BOM.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | {model} |
| Category | {cat_dir} |

## 2. Communication

| Interface | Protocol | Telegram | Notes |
|-----------|----------|----------|-------|
|  |  |  |  |

## 3. IO / Address Example

```
(fill from datasheet)
```

## 4. Control / Status Words

(fill from datasheet)

## 5. SCL Integration

(which library FB binds to this device, and how)

## 6. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
|  |  |  |

## 7. Notes

-
"""
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(skeleton, encoding="utf-8")
        except Exception as e:
            return {"ok": False, "msg": str(e)}
        return {"ok": True, "rel_path": rel_path, "device_id": device_id,
                "msg": f"Created {rel_path}"}

    # ------------------------------------------------------------------
    # Git operations (M8)
    # ------------------------------------------------------------------

    def git_commit(self, message: str) -> dict:
        """Stage all changes and commit in the project repo.

        O-2 fix: author identity is forwarded to manual_commit so commits are
        attributable.  Identity is read from settings (same keys used by
        git_init_project).  If the user has not configured their name/email we
        use a sentinel value that makes the gap visible in git log rather than
        falling back silently to whatever the OS git config contains.
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from project_git import manual_commit  # type: ignore
            user_name  = self.settings.get("username",   "") or "anonymous"
            user_email = (
                self.settings.get("user_email", "")
                or "anonymous@factory-web.local"
            )
            if user_name == "anonymous" or user_email == "anonymous@factory-web.local":
                logging.warning(
                    "git_commit: author identity not configured in settings "
                    "(username / user_email).  Using sentinel values — "
                    "set your name and e-mail in Workbench Settings. (O-2)"
                )
            r = manual_commit(
                self.root,
                message or "update via Workbench",
                user_name=user_name,
                user_email=user_email,
            )
            return {"ok": bool(r.ok), "msg": r.message}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def git_push(self, force_classified: bool = False) -> dict:
        """Push project repo to origin.

        W-A3: by default, CONFIDENTIAL/RESTRICTED projects with a public
        remote (github.com / gitlab.com / …) are refused. The UI must
        re-issue the call with `force_classified=True` after the user
        explicitly confirms the remote is enterprise/private.
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from project_git import push_project  # type: ignore
            r = push_project(self.root, force_classified=bool(force_classified))
            return {"ok": bool(r.ok), "msg": r.message}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def git_pull(self) -> dict:
        """Pull (rebase) from origin."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from project_git import pull_project  # type: ignore
            r = pull_project(self.root)
            return {"ok": bool(r.ok), "msg": r.message}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def git_init_project(self) -> dict:
        """Initialize a git repo in the current project folder."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from project_git import init_project_repo  # type: ignore
            name  = self.settings.get("username", "")
            email = self.settings.get("user_email", "")
            r = init_project_repo(self.root, user_name=name, user_email=email)
            return {"ok": bool(r.ok), "msg": r.message}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_workflows(self) -> list[dict]:
        """Return USER-FACING AI workflows.

        B-13: the generic dev chains (Analyze→Validate, IO Extraction→SCL,
        Full Pipeline) stay in BUILTIN_WORKFLOWS for tests and scripting but
        are hidden here — in the GUI they are indistinguishable from the
        14-RD methodology and produce visibly worse output."""
        try:
            from workbench.core.ai_runner import (  # type: ignore
                BUILTIN_WORKFLOWS, DEV_ONLY_WORKFLOWS)
            return [{"name": name, "steps": len(steps)}
                    for name, steps in BUILTIN_WORKFLOWS.items()
                    if name not in DEV_ONLY_WORKFLOWS]
        except Exception:
            return []

    def run_workflow(self, workflow_name: str, file_path: str = "") -> dict:
        """Run an AI workflow synchronously (blocking). For api mode only."""
        if not self.root:
            return {"ok": False, "output": "No project open"}
        cfg      = self.settings
        provider = cfg.get("ai_provider", "anthropic")
        model    = cfg.get("ai_model", "claude-sonnet-4-6")
        api_key  = self._resolve_api_key(provider)  # C-A2: keystore on-demand
        if not api_key:
            return {"ok": False, "output": "", "msg": "No API key — add one in Settings", "mode": "api"}
        allowed, reason = self._ai_send_allowed(provider)
        if not allowed:
            # B-L3/B-G2 fix: run_workflow has no consent UI — this is correct
            # fail-safe blocking for CONFIDENTIAL projects. Surface a clear
            # user-facing message so the engineer knows how to proceed.
            _guidance = (
                " CONFIDENTIAL projects require engineer consent — "
                "use Retrofit Pre-Analysis (which has the consent dialog) "
                "or change the project classification to proceed."
                if "CONFIDENTIAL" in reason else ""
            )
            return {"ok": False, "output": "", "msg": reason + _guidance,
                    "mode": "api", "blocked": "classification"}
        pii_warns = self._pii_soft_warn(provider)  # §11 soft PII warning
        try:
            from workbench.core.ai_runner import AutoFlowRunner, BUILTIN_WORKFLOWS  # type: ignore
            from ai_client import AIClient  # type: ignore
            if workflow_name not in BUILTIN_WORKFLOWS:
                return {"ok": False, "output": f"Unknown workflow: {workflow_name}"}
            source = Path(file_path) if file_path else (self.root / "PROJECT_STATE.json")
            if not source.exists():
                # Fall back to any md file in project
                mds = list(self.root.rglob("*.md"))
                source = mds[0] if mds else self.root
            output_lines: list[str] = []
            audit_warns: list[str] = []  # R-C-2: output audit warn collector
            done_event = __import__("threading").Event()
            def on_step_start(n, name): output_lines.append(f"Step {n}: {name}")
            def on_step_chunk(chunk): output_lines.append(chunk)
            def on_step_done(n, out, p): output_lines.append(f"[done] Step {n} → {p.name}")
            def on_flow_done(): done_event.set()
            def on_error(msg): output_lines.append(f"[error] {msg}"); done_event.set()
            def on_warn(msg): audit_warns.append(msg)  # R-C-2: collect output audit warnings
            # C-1 fix: audit log before workflow starts (fail-closed)
            try:
                _audit_log(self.root, f"workflow:{workflow_name}",
                           provider, model,
                           prompt_id=f"run_workflow:{workflow_name}")
            except AuditLogError as _ae:
                return {"ok": False, "output": str(_ae), "blocked": "audit_log"}
            runner = AutoFlowRunner(
                provider=provider, model=model, api_key=api_key,
                project_root=self.root,
                on_step_start=on_step_start, on_step_chunk=on_step_chunk,
                on_step_done=on_step_done, on_flow_done=on_flow_done, on_error=on_error,
                on_warn=on_warn,  # R-C-2: propagate output audit warnings to caller
                on_usage=self._add_cost,  # B8: real spend bookkeeping
            )
            runner.run_async(workflow_name, source)
            done_event.wait(timeout=120)
            result: dict = {"ok": True, "output": "\n".join(output_lines), "mode": "api"}
            if pii_warns:
                result["_pii_warnings"] = pii_warns
            if audit_warns:
                # R-C-2: if the output hash log failed, relay it visibly to the caller
                result["_audit_warn"] = "output_hash_failed"
                result["_audit_warn_details"] = audit_warns
            return result
        except AuditLogError as e:
            return {"ok": False, "output": str(e), "blocked": "audit_log"}
        except Exception as e:
            return {"ok": False, "output": str(e)}

    # ------------------------------------------------------------------
    # Retrofit Pre-Analysis
    # ------------------------------------------------------------------

    # M1: legacy_code accepts .txt (S5/S7 for Windows text export) and .pdf
    # (print export — goes through legacy_pdf_extract + engineer confirmation).
    # Categories are FOLDER-scoped, so a PDF in _raw/legacy_code/ is a code
    # listing while a PDF in _raw/drawings/ still goes to Gemini Vision.
    _RAW_CATEGORIES: dict = {
        "drawings": [".pdf", ".svg", ".dxf", ".dwg"],
        "photos":   [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
        "docs":     [".pdf", ".docx", ".doc", ".txt", ".xlsx"],
        # .seq = STEP5 symbol table (Zuordnungsliste) — near-text, reads fine
        # with errors="replace". .s5d (binary MC5 program) is listed so the
        # engineer SEES it, but the concat loop skips binaries with a warning
        # telling them to export an AWL listing via S5/S7 for Windows.
        # .s7p (STEP7 Classic project) is likewise listed for VISIBILITY only:
        # it is a binary container and gets a format-specific export hint —
        # .zap*/.ap*/.zip archives are matched via _project_archive_kind()
        # because their version-suffixed extensions can't be enumerated here.
        "legacy_code": [".scl", ".awl", ".stl", ".s7p", ".xml", ".src",
                        ".txt", ".pdf", ".seq", ".s5d"],
    }

    @staticmethod
    def _project_archive_kind(fp: Path) -> str | None:
        """Classify project-container files that can NOT be read as text.

        Returns "s7p" (STEP7 Classic project), "zap" (STEP7/TIA archive,
        .zap14/.zap25/...), "ap" (TIA Portal project file, .ap14/.ap19/...),
        "zip" (generic archive) or None for anything else. These are the
        formats engineers most often receive a legacy project in — they must
        surface a format-specific export instruction instead of the generic
        binary-skip warning (or, worse, being invisible entirely)."""
        s = fp.suffix.lower()
        if s == ".s7p":
            return "s7p"
        if s.startswith(".zap"):
            return "zap"
        if s.startswith(".ap") and s[3:].isdigit():
            return "ap"
        if s == ".zip":
            return "zip"
        return None

    # B-02: legacy-input size thresholds (chars; ~4 chars ≈ 1 token).
    # SOFT = provider may drop the tail; HARD = context overflow certain.
    _INPUT_SOFT_LIMIT_CHARS = 240_000   # ~60k tokens
    _INPUT_HARD_LIMIT_CHARS = 600_000   # ~150k tokens

    @classmethod
    def _input_size_warning(cls, n_chars: int) -> str | None:
        """Return a pre-run warning for oversize legacy input, or None.

        A truncated analysis silently loses blocks/IO — the engineer must
        see real numbers BEFORE the tokens are spent, not discover missing
        signals in TIA weeks later."""
        est_tokens = n_chars // 4
        if n_chars > cls._INPUT_HARD_LIMIT_CHARS:
            return (
                f"Legacy input is VERY large: {n_chars:,} chars "
                f"(~{est_tokens:,} tokens) — this almost certainly exceeds "
                "the model context. The analysis WILL be incomplete (missing "
                "blocks/IO). Split the sources (per CPU / per plant section) "
                "into separate projects and analyze them one at a time."
            )
        if n_chars > cls._INPUT_SOFT_LIMIT_CHARS:
            return (
                f"Legacy input is large: {n_chars:,} chars "
                f"(~{est_tokens:,} tokens). Depending on the provider the "
                "tail of the input may be cut, leaving the IO list "
                "incomplete. Cross-check RD01 against the symbol table, or "
                "split the sources and run the analysis per section."
            )
        return None

    # Format-specific guidance shown when a project archive is found in
    # _raw/legacy_code/ — tells the engineer exactly how to get from the
    # container they have to the text sources this pipeline can read.
    _ARCHIVE_GUIDANCE: dict = {
        "s7p": ("is a STEP7 Classic project (.s7p) — it cannot be read "
                "directly. Open it in SIMATIC Manager (STEP7 V5.x), generate "
                "AWL sources for the blocks (LAD/STL/FBD editor -> File -> "
                "Generate Source), export the symbol table (.SDF/.SEQ), and "
                "drop those files here."),
        "zap": ("is a STEP7/TIA project ARCHIVE (.zap*) — it cannot be read "
                "directly. Retrieve it in SIMATIC Manager / TIA Portal "
                "(Project -> Retrieve), then export the blocks as AWL/SCL "
                "sources and drop those files here."),
        "ap":  ("is a TIA Portal project file (.ap*) — it cannot be read "
                "directly. Open it in TIA Portal and export the blocks as "
                "external sources (SCL), then drop the exported files here."),
        "zip": ("is a ZIP archive — it cannot be read directly. Unpack it "
                "and drop the contained AWL/SCL/text listings here."),
    }

    @staticmethod
    def _looks_binary(fp: Path, sample: int = 2048) -> bool:
        """True when a legacy file is binary (e.g. STEP5 .s5d MC5 code) —
        feeding it to a text LLM produces garbage, so it must be skipped
        loudly, never silently."""
        try:
            data = fp.read_bytes()[:sample]
        except Exception:
            return True
        if not data:
            return False
        printable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
        return printable / len(data) < 0.60

    @staticmethod
    def _is_extraction_sidecar(f: Path) -> bool:
        """True for <stem>.extracted.txt / .extracted.meta.json sidecars."""
        return f.name.endswith(".extracted.txt") or f.name.endswith(".extracted.meta.json")

    def get_raw_folder_status(self) -> dict:
        """Return file counts and names under _raw/ for the current project."""
        if not self.root:
            return {"ok": False, "msg": "No project open", "total": 0, "by_category": {}}
        raw_dir = self.root / "_raw"
        by_cat: dict[str, list[str]] = {c: [] for c in self._RAW_CATEGORIES}
        for cat, exts in self._RAW_CATEGORIES.items():
            cat_dir = raw_dir / cat
            if cat_dir.is_dir():
                for f in sorted(cat_dir.iterdir()):
                    if not f.is_file() or self._is_extraction_sidecar(f):
                        continue
                    # Project archives (.zap25, .ap19, .zip ...) have
                    # version-suffixed extensions not in the static list —
                    # they must still be VISIBLE so the engineer sees them
                    # and gets the export guidance at pre-analysis time.
                    if f.suffix.lower() in exts or (
                        cat == "legacy_code"
                        and self._project_archive_kind(f) is not None
                    ):
                        by_cat[cat].append(f.name)
        total = sum(len(v) for v in by_cat.values())
        return {
            "ok": True,
            "raw_dir_exists": raw_dir.is_dir(),
            "total": total,
            "by_category": by_cat,
        }

    def import_s5d(self, path: str) -> dict:
        """Direct Step5 .s5d import — converts every logic block to the
        S5W AWL dialect into _raw/legacy_code/ (proven parity, see
        s5d_import.py). Fail-honest: warnings list every skipped or
        partially-converted block; nothing is guessed."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from s5d_import import import_s5d as _run_import  # type: ignore
        except Exception as e:
            return {"ok": False, "msg": f"s5d_import module unavailable: {e}"}
        dest = self.root / "_raw" / "legacy_code"
        try:
            summ = _run_import(path, dest)
        except RuntimeError as e:
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": f"S5D import failed: {e}"}
        # provenance note next to the generated AWL (engineer-facing)
        try:
            from datetime import datetime as _dt
            info = [
                "# S5D import — provenance", "",
                f"- source file: `{Path(path).name}`",
                f"- imported: {_dt.now().isoformat(timespec='seconds')}",
                f"- blocks: {', '.join(summ.blocks_written)}",
                f"- networks: {summ.networks}",
                "- converter: DotNetSiemensPLCToolBoxLibrary (LGPL, "
                "unmodified) + Factory dialect renderer; timer constants "
                "recovered from MC5 bytes (proven 41/41).", "",
            ]
            if summ.warnings:
                info += ["## Warnings (fail-honest — review before Gate 1)",
                         ""] + [f"- {w}" for w in summ.warnings]
            (dest / "_s5d_import_info.md").write_text(
                "\n".join(info) + "\n", encoding="utf-8")
        except Exception:
            pass
        return {
            "ok": True,
            "blocks": summ.blocks_written,
            "networks": summ.networks,
            "warnings": summ.warnings,
            "seq_copied": summ.seq_copied,
            "msg": (f"Imported {len(summ.blocks_written)} blocks / "
                    f"{summ.networks} networks"
                    + (f" · {len(summ.warnings)} warnings"
                       if summ.warnings else "")),
        }

    # ------------------------------------------------------------------
    # M1 — legacy PDF extraction (pdfplumber + Gemini Vision OCR fallback)
    # ------------------------------------------------------------------

    def get_legacy_extraction_status(self) -> dict:
        """Per-PDF extraction state for the Gate-1 review panel."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open", "items": []})
        from legacy_pdf_extract import load_extraction_meta  # type: ignore
        legacy_dir = self.root / "_raw" / "legacy_code"
        items = []
        if legacy_dir.is_dir():
            for pdf in sorted(legacy_dir.glob("*.pdf")):
                meta = load_extraction_meta(pdf) or {}
                items.append({
                    "name": pdf.name,
                    "extracted": bool(meta),
                    "confirmed": bool(meta.get("confirmed")),
                    "method": meta.get("method"),
                    "quality": meta.get("quality"),
                    "page_count": meta.get("page_count"),
                })
        return _attach_warnings({"ok": True, "items": items})

    def extract_legacy_pdfs(self, opts: Optional[dict] = None) -> dict:
        """Extract text from all unconfirmed legacy-code PDFs.

        opts: {"engineer": str, "ocr_consent": bool, "force_ocr": [names]}
        Scanned PDFs (no text layer) need Gemini Vision OCR — that sends the
        document to Google, so it requires ocr_consent + engineer name and
        passes the classification guard + audit log, like pre-analysis.
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        opts = opts or {}
        ocr_consent = bool(opts.get("ocr_consent"))
        engineer = (opts.get("engineer") or "").strip()
        force_ocr = set(opts.get("force_ocr") or [])

        from legacy_pdf_extract import (  # type: ignore
            extract_pdf_text, ocr_via_vision, write_extraction,
            load_extraction_meta,
        )

        legacy_dir = self.root / "_raw" / "legacy_code"
        results: list[dict] = []
        for pdf in sorted(legacy_dir.glob("*.pdf")) if legacy_dir.is_dir() else []:
            meta = load_extraction_meta(pdf)
            if meta and meta.get("confirmed"):
                results.append({"name": pdf.name, "status": "confirmed",
                                "method": meta.get("method")})
                continue
            try:
                res = extract_pdf_text(pdf)
            except RuntimeError as exc:
                results.append({"name": pdf.name, "status": "error", "msg": str(exc)})
                continue

            wants_ocr = res.quality.needs_ocr or pdf.name in force_ocr
            if wants_ocr:
                ocr_outcome = self._ocr_legacy_pdf(pdf, res.page_count,
                                                   ocr_consent, engineer)
                if ocr_outcome.get("status") == "ocr_done":
                    res = ocr_outcome["result"]
                    if getattr(res, "truncated", False):
                        # S-5 (B-L13): a cut-off OCR must never look complete —
                        # the missing tail is usually the FB/PB blocks.
                        _warn(
                            f"OCR output for '{pdf.name}' was cut off at the "
                            "token limit — the transcription is likely "
                            "INCOMPLETE. Split the PDF and retry.",
                            category="compliance",
                        )
                else:
                    # No consent / blocked / failed — keep the (poor)
                    # pdfplumber text so the engineer can still inspect it.
                    write_extraction(pdf, res)
                    results.append({
                        "name": pdf.name,
                        "status": ocr_outcome.get("status", "needs_ocr_consent"),
                        "msg": ocr_outcome.get("msg", ""),
                        "quality": res.quality.score,
                        "method": res.method,
                    })
                    continue

            write_extraction(pdf, res)
            results.append({
                "name": pdf.name, "status": "extracted",
                "method": res.method, "quality": res.quality.score,
                "needs_review": True,
                "truncated": bool(getattr(res, "truncated", False)),
            })
        return _attach_warnings({"ok": True, "results": results})

    def _ocr_legacy_pdf(self, pdf: Path, page_count: int,
                        ocr_consent: bool, engineer: str) -> dict:
        """Gemini Vision OCR for one scanned PDF — guarded, audited."""
        if not ocr_consent or not engineer:
            return {"status": "needs_ocr_consent",
                    "msg": ("Scanned PDF — OCR sends the document to Google. "
                            "Confirm OCR consent (with engineer name) to proceed.")}
        api_key = self._resolve_api_key("google")
        if not api_key:
            return {"status": "error",
                    "msg": "No Google API key — add it in Settings to OCR scanned PDFs."}
        from data_classification_guard import check_ai_send  # type: ignore
        # B-L3/B-G1 fix: derive consent from ACTUAL function args (ocr_consent + engineer),
        # not a hardcoded True. The outer guard at :1913 already checked, but if this
        # helper is ever reached by a different path the chain stays safe.
        _ocr_consent_confirmed = bool(ocr_consent) and bool(engineer)
        gate = check_ai_send(self.root, "google", self.settings,
                             consent_confirmed=_ocr_consent_confirmed)
        if not gate.allowed:
            return {"status": "blocked", "msg": f"[C4] {gate.reason}"}
        for w in self._pii_soft_warn("google"):  # §11 soft PII warning
            _warn(w, category="privacy")
        _warn(
            f"Scanned legacy PDF '{pdf.name}' is sent to Gemini Vision for OCR "
            "WITHOUT anonymization — review the transcription before use.",
            category="privacy",
        )
        try:
            _audit_log(
                self.root, "legacy_pdf_ocr", "google", "gemini-2.5-pro",
                prompt_text=f"engineer={engineer}; file={pdf.name}; pages={page_count}",
                prompt_id="legacy_pdf_ocr:consent",
            )
        except AuditLogError as ae:
            return {"status": "error", "msg": f"[EU AI Act] Audit log failed: {ae}"}
        try:
            from ai_client import AIClient  # type: ignore
            from legacy_pdf_extract import ocr_via_vision  # type: ignore
            client = AIClient(provider="google", api_key=api_key,
                              model="gemini-2.5-pro")
            result = ocr_via_vision(pdf, client, page_count)
            return {"status": "ocr_done", "result": result}
        except Exception as exc:
            return {"status": "error", "msg": f"OCR failed: {exc}"}

    def confirm_extracted_text(self, name: str, edited_text: Optional[str] = None) -> dict:
        """Engineer confirms (optionally edits) the extracted listing text."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        pdf = self.root / "_raw" / "legacy_code" / name
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            return _attach_warnings({"ok": False, "msg": f"Not a legacy PDF: {name}"})
        from legacy_pdf_extract import confirm_extraction  # type: ignore
        try:
            meta = confirm_extraction(pdf, edited_text)
        except RuntimeError as exc:
            return _attach_warnings({"ok": False, "msg": str(exc)})
        try:
            _audit_log(
                self.root, "legacy_pdf_confirm", "local", "engineer",
                prompt_text=f"file={name}; edited={edited_text is not None}",
                prompt_id="legacy_pdf_ocr:confirm",
            )
        except AuditLogError as _ae:
            # B-G4 / S-4: audit write failure must NOT be silent even for local
            # confirmation actions — user must know the record was not persisted.
            # Onay işlemi bloklanmaz (yorumdaki gerekçe geçerli) ama sessizlik kalkar.
            _warn(
                f"audit log write failed — confirmation NOT recorded: {_ae}",
                category="compliance",
            )
        return _attach_warnings({"ok": True, "meta": meta})

    def _project_type(self) -> str:
        """retrofit / greenfield (lowercase) from PROJECT_STATE — default retrofit."""
        st = self._project_state() if self.root else {}
        return (st.get("project_type") or "retrofit").strip().lower()

    def run_discovery(self, consent_data: dict) -> dict:
        """Gate-1 generation, routed by project_type: retrofit extracts RD01/02/
        03/13 from legacy code; greenfield designs RD01/02/03 from the new
        machine's documents (P&ID/EPLAN/spec). Same engine, different prompts."""
        wf = ("Greenfield Discovery" if self._project_type() == "greenfield"
              else "Retrofit Pre-Analysis")
        return self.run_retrofit_preanalysis(consent_data, workflow_name=wf)

    def run_topic_generation(self, consent_data: dict) -> dict:
        """Gate-2 generation, routed by project_type: retrofit extracts vs
        greenfield designs the remaining topic RDs, both using the approved
        Gate-1 outputs."""
        wf = ("Greenfield Topic Design" if self._project_type() == "greenfield"
              else "Topic Extraction")
        return self.run_retrofit_preanalysis(consent_data, workflow_name=wf)

    def run_topic_extraction(self, consent_data: dict) -> dict:
        """Gate-2 retrofit generation (RD04-RD12, RD14 + RD05) from the legacy
        code AND the approved Gate-1 analysis. Kept for the retrofit path; the
        project-type-aware entry point is run_topic_generation."""
        return self.run_retrofit_preanalysis(consent_data, workflow_name="Topic Extraction")

    def run_retrofit_preanalysis(
        self, consent_data: dict, workflow_name: str = "Retrofit Pre-Analysis",
        _chain: Optional[dict] = None,
    ) -> dict:
        """Start an AI generation workflow with engineer consent.

        workflow_name:
          - "Retrofit Pre-Analysis" (Gate 1) → RD01/02/03/13 from drawings+code.
          - "Topic Extraction" (Gate 2) → RD04-12,14 + RD05, gated on the Gate-1
            RDs being approved, using those approved drafts as extra context.
        consent_data: {"engineer": str, "confirmed": bool, "auto_continue": bool}
          auto_continue (one-click full analysis): a discovery run chains
          straight into topic generation under the SAME consent — the topic
          steps then use the FRESH, UNREVIEWED Gate-1 drafts. All outputs stay
          DRAFT_UNVERIFIED; the review requirement moves to the Gate-3 lock
          instead of blocking between the two generation phases.
        _chain: INTERNAL — continuation descriptor {"job": dict, "offset": int}
          set only by the auto-continue hop; never passed from the GUI.
        Returns {"ok": bool, "output": str, "msg": str}
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        if not consent_data.get("confirmed"):
            return {"ok": False, "msg": "Consent not confirmed — operation cancelled"}
        engineer = (consent_data.get("engineer") or "").strip()
        if not engineer:
            return {"ok": False, "msg": "Engineer name is required for consent"}
        auto_continue = bool(consent_data.get("auto_continue"))

        # Gate-2 topic generation (retrofit OR greenfield) may only run AFTER the
        # engineer has approved the Gate-1 analysis — it consumes those outputs.
        # Exception: the auto-continue hop (_chain) runs on the unreviewed fresh
        # drafts by explicit engineer choice; the gap is flagged in the job.
        if workflow_name in ("Topic Extraction", "Greenfield Topic Design") and _chain is None:
            _gf = workflow_name == "Greenfield Topic Design"
            # Vites-2 (risk-based): only the CRITICAL Gate-1 outputs need the
            # engineer's approval before topic generation — RD01 (IO) + RD03
            # (flowchart). RD02/RD13 flow in as drafts; they are context, not
            # the backbone the topic prompts build on.
            _g1 = ["RD01", "RD03"]
            try:
                from project_analyzer import analyze_project  # type: ignore
                _rds = {k: v.status for k, v in analyze_project(self.root).rd_statuses.items()}
            except Exception:
                _rds = {}
            _rev = _rd_review_states(self.root, self._project_state(), _rds)
            # Approved OR explicitly N/A both satisfy the precondition.
            _need = [rd for rd in _g1
                     if not (_rev.get(rd, {}).get("reviewed") or _rev.get(rd, {}).get("na"))]
            if _need:
                _label = "Greenfield Topic Design" if _gf else "Topic Extraction"
                return {"ok": False, "msg": (
                    f"{_label} needs the Gate-1 analysis approved first — "
                    "review (approve) " + ", ".join(_need) + " before generating "
                    "the remaining RDs.")}

        # Per-task provider resolution
        task_cfg = self.get_provider_for_task("preanalysis")
        _emit_provider_warning(task_cfg)  # G-02: belt-and-suspenders — the
        # consent modal already shows provInfo.warning before this call, but
        # queuing it here too means the diagnostics log carries it even if
        # settings changed between "open modal" and "click Start", and it
        # reaches the same _attach_warnings() flush this function already
        # performs on its success/thread-launch return paths below.
        provider   = task_cfg["provider"]
        model      = task_cfg["model"]
        max_tokens = task_cfg["max_tokens"]
        api_key    = self._resolve_api_key(provider)
        if not api_key:
            return {"ok": False, "msg": f"No API key for '{provider}'. Add it in Settings → {provider} card."}

        # Step 1 (Vision) always uses Google (hardcoded in workflow definition).
        # Steps 2-6 (text-only) inherit the runner's default provider.
        # If the global provider is Google, automatically prefer Anthropic for
        # text steps — Google free tier allows only 20 requests/day, which a
        # 6-step workflow exhausts in a single run.
        text_provider = provider
        text_model    = model
        if provider == "google":
            _anth_key = self._resolve_api_key("anthropic")
            if _anth_key:
                ps_anth = (self.settings.get("provider_settings") or {}).get("anthropic") or {}
                text_provider = "anthropic"
                text_model    = (ps_anth.get("model")
                                 or self.settings.get("ai_model")
                                 or "claude-sonnet-4-6")

        # M0 fix: the workflow mixes providers (Gemini Vision + Claude) — verify
        # a key exists for EVERY step's provider up front, so the run cannot
        # die halfway through after tokens were already spent on step 1.
        try:
            from workbench.core.ai_runner import BUILTIN_WORKFLOWS as _WFS  # type: ignore
            # Steps with provider=None inherit text_provider (the runner default).
            _missing = sorted({
                (s.provider or text_provider)
                for s in _WFS.get(workflow_name, [])
                if not self._resolve_api_key(s.provider or text_provider)
            })
            if _missing:
                return {
                    "ok": False,
                    "msg": (
                        "Missing API key(s) for: " + ", ".join(_missing)
                        + " — add the key(s) in Settings → API Keys."
                    ),
                }
        except ImportError:
            pass  # runner import failure is reported by the run itself below

        # M1: legacy-code PDFs must be extracted AND engineer-confirmed before
        # the analysis may start — unreviewed OCR text corrupts addresses
        # silently (O↔0, I↔1), which would poison the whole RD01 draft. This only
        # applies when legacy-code PDFs actually exist (greenfield projects have
        # none) — a missing legacy_pdf_extract module must NOT block a project
        # that has no legacy PDFs to check.
        _legacy_dir = self.root / "_raw" / "legacy_code"
        _legacy_pdfs = sorted(_legacy_dir.glob("*.pdf")) if _legacy_dir.is_dir() else []
        if _legacy_pdfs:
            try:
                from legacy_pdf_extract import load_extraction_meta  # type: ignore
                _unconfirmed = [
                    p.name for p in _legacy_pdfs
                    if not (load_extraction_meta(p) or {}).get("confirmed")
                ]
                if _unconfirmed:
                    return {
                        "ok": False,
                        "msg": (
                            "Legacy PDF(s) without confirmed text extraction: "
                            + ", ".join(_unconfirmed)
                            + " — run 'Extract PDF text', review the transcription "
                              "and confirm it first."
                        ),
                    }
            except ImportError:
                return {"ok": False, "msg": "legacy_pdf_extract module not available "
                        "but legacy PDFs are present — install it or remove the PDFs."}

        # Classification guard — consent_confirmed overrides CONFIDENTIAL soft-block.
        # B-L3/B-G2 fix: derive from ACTUAL consent_data, not a hardcoded True.
        # Outer guards at :1980-1983 already checked, but the chain must stay
        # verifiable end-to-end even if this site is reached by a different path.
        _preanalysis_consent_confirmed = (
            bool(consent_data.get("confirmed")) and bool(engineer)
        )
        from data_classification_guard import check_ai_send  # type: ignore
        gate = check_ai_send(self.root, provider, self.settings,
                             consent_confirmed=_preanalysis_consent_confirmed)
        if not gate.allowed:
            return {"ok": False, "msg": f"[C4] {gate.reason}"}
        for w in self._pii_soft_warn(provider):  # §11 soft PII warning
            _warn(w, category="privacy")

        # S-20 (B-G8): Build anonymization map — INTERNAL/CONFIDENTIAL require
        # anonymize; _anon_map_for_ai() returns {} for PUBLIC (optional) and
        # the field-level map for INTERNAL/CONFIDENTIAL (required).
        from anonymizer import anon_map_hash, deanonymize_text  # type: ignore
        anon_map = self._anon_map_for_ai(gate)
        # getattr: tuple-style/mock gates lack the flag; real AIGateResult always
        # sets it. Read ONCE outside the per-file try so a missing attribute can
        # never silently drop files via the except below.
        _req_anon = bool(getattr(gate, "requires_anonymization", False))

        # Log consent to audit trail
        status_info = self.get_raw_folder_status()
        files_list = [
            f for cat_files in status_info.get("by_category", {}).values()
            for f in cat_files
        ]
        try:
            _audit_log(
                self.root, "retrofit_preanalysis_consent",
                provider, model,
                prompt_text=f"engineer={engineer}; files={files_list}",
                output_text=f"anon_map_hash={anon_map_hash(anon_map) if anon_map else 'empty'}",
                prompt_id="retrofit_preanalysis:consent",
            )
        except AuditLogError as ae:
            return {"ok": False, "msg": f"[EU AI Act] Audit log failed: {ae}", "blocked": "audit_log"}

        # Collect source files. Suffix matching mirrors get_raw_folder_status
        # (case-insensitive) — glob("*.seq") would silently drop "X.SEQ" on
        # case-sensitive filesystems while the status listing shows it.
        raw_dir = self.root / "_raw"
        multimodal_files: list[Path] = []
        # Gate-2 Topic Extraction is text-only (legacy code + Gate-1 drafts); it
        # has no Vision step, so drawings/photos are not collected or sent.
        _text_only = workflow_name in ("Topic Extraction", "Greenfield Topic Design")
        for cat in (("drawings", "photos") if not _text_only else ()):
            cat_dir = raw_dir / cat
            if cat_dir.is_dir():
                exts = self._RAW_CATEGORIES[cat]
                multimodal_files.extend(sorted(
                    f for f in cat_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in exts
                ))

        if multimodal_files and _req_anon:
            # INTERNAL/CONFIDENTIAL: visual files cannot be text-anonymized.
            # Block them rather than leaking customer IP to the AI provider.
            _warn(
                f"{len(multimodal_files)} visual file(s) EXCLUDED: project classification "
                f"requires anonymization but images/drawings cannot be text-anonymized. "
                "Remove customer logos, nameplates and title blocks from the files first, "
                "or change the project classification to PUBLIC for visual analysis. (AUDIT-001)",
                category="privacy",
            )
            multimodal_files = []
        elif multimodal_files:
            # PUBLIC project: visual files bypass the text anonymizer — loud warning.
            _warn(
                f"{len(multimodal_files)} visual file(s) (photos/drawings/PDFs) will be "
                f"sent to {provider} WITHOUT anonymization — only legacy code text is "
                "anonymized. Remove customer logos, nameplates and title blocks before upload.",
                category="privacy",
            )

        # Legacy code: concatenate all text files for the text step.
        # M1: .pdf entries contribute their CONFIRMED .extracted.txt sidecar
        # (presence verified above); sidecars themselves are skipped in the
        # generic loop so the listing is never concatenated twice.
        from legacy_pdf_extract import extraction_paths  # type: ignore
        legacy_parts: list[str] = []
        _archives_skipped = 0
        _s5_enriched = 0
        _s5_symbols: Optional[dict] = None  # lazy — one parse per run
        legacy_dir = raw_dir / "legacy_code"
        if legacy_dir.is_dir():
            legacy_exts = self._RAW_CATEGORIES["legacy_code"]
            for fp in sorted(
                f for f in legacy_dir.iterdir()
                if f.is_file() and (f.suffix.lower() in legacy_exts
                                    or self._project_archive_kind(f) is not None)
            ):
                if self._is_extraction_sidecar(fp):
                    continue
                _arch = self._project_archive_kind(fp)
                if _arch is not None:
                    # .s7p/.zap*/.ap*/.zip — binary project containers.
                    # Loud, format-specific export instruction; never the
                    # generic "STEP5 binary" message (misleading for S7).
                    _archives_skipped += 1
                    _warn(
                        f"'{fp.name}' {self._ARCHIVE_GUIDANCE[_arch]}",
                        category="input",
                    )
                    continue
                try:
                    if fp.suffix.lower() == ".pdf":
                        txt_path, _meta = extraction_paths(fp)
                        text = txt_path.read_text(encoding="utf-8", errors="replace")
                        label = f"{fp.name} (extracted text)"
                    elif self._looks_binary(fp):
                        # e.g. STEP5 .s5d MC5 program — loud skip, never
                        # feed binary garbage to the analysis chain.
                        _warn(
                            f"'{fp.name}' is a BINARY file (e.g. STEP5 .s5d "
                            "program) — skipped. Export the program as an "
                            "AWL/text listing (or PDF print) with "
                            "S5/S7 for Windows or STEP5 and drop that here.",
                            category="input",
                        )
                        continue
                    else:
                        text = fp.read_text(encoding="utf-8", errors="replace")
                        label = fp.name
                        # Bare S5 bracket exports carry ZERO semantics — the
                        # AI produces generic summaries from them. Enrich in
                        # memory (S7 syntax + Zuordnungsliste symbols inline);
                        # originals stay untouched. A/B/C field measurement
                        # 2026-07-03: this turns block summaries into
                        # operand-level correct analysis.
                        if fp.suffix.lower() in (".awl", ".stl"):
                            from legacy_enrich import (  # type: ignore
                                enrich_awl_text, is_s5_bracket_awl,
                                load_symbols,
                            )
                            if is_s5_bracket_awl(text):
                                if _s5_symbols is None:
                                    _s5_symbols = load_symbols(legacy_dir)
                                text = enrich_awl_text(
                                    text, _s5_symbols, fp.stem)
                                label = f"{fp.name} (S5→S7 enriched)"
                                _s5_enriched += 1
                    # S-20 (B-G8): INTERNAL requires anonymize — always call
                    # anonymize_text when requires_anonymization=True (anon_map
                    # may be {} but regex PII patterns still run). PUBLIC:
                    # anon_map={} so only regex patterns apply (lightweight).
                    if _req_anon or anon_map:
                        text, _anon_err = _anonymize_or_block(
                            text, anon_map, _req_anon, label)
                        if _anon_err:
                            return _attach_warnings({"ok": False,
                                                     "msg": _anon_err})
                    legacy_parts.append(f"--- {label} ---\n{text}")
                except Exception:
                    pass

        # Gate-2 topic generation (retrofit OR greenfield): append the APPROVED
        # Gate-1 RD drafts (IO list, data dictionary, flowchart, annotation) so
        # the topic steps can cross-reference them. RD13 only exists for retrofit
        # (greenfield → no file → skipped). Anonymized like the legacy code.
        if workflow_name in ("Topic Extraction", "Greenfield Topic Design"):
            for rd in ("RD01", "RD02", "RD03", "RD13"):
                f = _rd_main_file(self.root, rd)
                if f is None:
                    continue
                try:
                    _txt = f.read_text(encoding="utf-8", errors="replace")
                    if _req_anon or anon_map:
                        _txt, _anon_err = _anonymize_or_block(
                            _txt, anon_map, _req_anon, f"Gate-1 {rd}")
                        if _anon_err:
                            return _attach_warnings({"ok": False,
                                                     "msg": _anon_err})
                    legacy_parts.append(f"--- Gate-1 {rd} ({f.name}) ---\n{_txt}")
                except Exception:
                    pass

        # Dead-end guard: the engineer dropped ONLY project archives
        # (.s7p/.zap/...) — running the AI chain on "(no legacy code files
        # found)" would burn tokens and produce empty RD drafts. Stop here
        # with the export instructions instead (they are in the warnings).
        if (_archives_skipped and not legacy_parts and not multimodal_files
                and workflow_name == "Retrofit Pre-Analysis"):
            return _attach_warnings({
                "ok": False,
                "msg": (f"No readable legacy sources found — {_archives_skipped} "
                        "project archive(s) cannot be read directly. Follow the "
                        "export instructions above, then run Pre-Analysis again."),
            })

        # Write concatenated legacy code to a temp input file
        tmp_legacy = self.root / "_raw" / "_preanalysis_legacy_concat.txt"
        _concat = ("\n\n".join(legacy_parts) if legacy_parts
                   else "(no legacy code files found)")
        tmp_legacy.write_text(_concat, encoding="utf-8")

        # B-02: input-size pre-check. The WHOLE concat goes into a single
        # prompt — a 200-block S7 project can overflow the model context and
        # the provider then errors out or silently drops the tail, producing
        # an INCOMPLETE IO list that gets approved unnoticed. Warn up front
        # with real numbers so the engineer can split the sources per CPU /
        # per plant section BEFORE burning tokens.
        _est_tokens = len(_concat) // 4
        _size_msg = self._input_size_warning(len(_concat))
        if _size_msg:
            _warn(_size_msg, category="input")
        if _s5_enriched:
            _warn(
                f"{_s5_enriched} bare S5 AWL export(s) were enriched "
                "deterministically before analysis (S7 syntax + "
                "Zuordnungsliste symbols inline). Originals untouched. "
                "Tip: drop the FULL Zuordnungsliste (.SEQ with M/T rows) "
                "into legacy_code to enrich flags and timers too.",
                category="input",
            )

        # Run the workflow — M2: as a background job. The 6-step chain takes
        # several minutes; the old synchronous done_event.wait(300) returned
        # a false timeout. The UI polls get_preanalysis_status().
        try:
            from workbench.core.ai_runner import AutoFlowRunner, BUILTIN_WORKFLOWS  # type: ignore
            if workflow_name not in BUILTIN_WORKFLOWS:
                return {"ok": False, "msg": f"{workflow_name} workflow not found in ai_runner."}

            prev = getattr(self, "_preanalysis_job", None)
            if _chain is None and prev and prev.get("running"):
                return _attach_warnings({
                    "ok": False, "msg": "A generation run is already in progress."})

            _wf_steps = BUILTIN_WORKFLOWS[workflow_name]
            # Which topic workflow would an auto-continue hop run next?
            _next_topic = {"Retrofit Pre-Analysis": "Topic Extraction",
                           "Greenfield Discovery": "Greenfield Topic Design"
                           }.get(workflow_name)
            if _chain is not None:
                # Continuation: reuse the phase-1 job so the GUI poll keeps a
                # single, continuous step tracker across both phases.
                job = _chain["job"]
                _step_offset = int(_chain.get("offset", 0))
            else:
                _step_offset = 0
                _step_names = [s.name for s in _wf_steps]
                if auto_continue and _next_topic:
                    # Show the FULL combined step list from the start — the
                    # engineer sees one long run, not a surprise second half.
                    _step_names += [s.name for s in
                                    BUILTIN_WORKFLOWS.get(_next_topic, [])]
                job = {
                    "running": True, "done": False, "ok": None, "msg": "",
                    "lines": [], "current_step": "", "drafts": [], "warnings": [],
                    "started_at": time.time(),
                    "step_index": -1,
                    "step_total": len(_step_names),
                    "step_names": _step_names,
                    # B-02: surfaced in the progress panel so oversize input is
                    # visible while the run is in flight, not only in the banner.
                    "input_chars": len(_concat),
                    "input_est_tokens": _est_tokens,
                }
                self._preanalysis_job = job

            def on_step_start(n, name):
                job["current_step"] = f"Step {_step_offset + n + 1}: {name}"
                job["step_index"] = _step_offset + n
                job["lines"].append(f"\n▶ Step {_step_offset + n + 1}: {name}")
            def on_step_chunk(chunk):
                job["lines"].append(chunk)
            def on_step_done(n, out, p):
                job["lines"].append(f"\n✓ {p.name}")
            def _auto_regen_mermaid():
                """Called after RD03 draft is written — deterministic Mermaid from table."""
                try:
                    r = self.rd03_regen_mermaid()
                    if r.get("ok"):
                        job["lines"].append(f"\n⟳ RD03 Mermaid otomatik üretildi — {r.get('msg','')}")
                    else:
                        job["lines"].append(f"\n⚠ RD03 Mermaid üretilemedi: {r.get('error','')}")
                except Exception as _e:
                    job["lines"].append(f"\n⚠ RD03 Mermaid auto-regen hata: {_e}")

            def _auto_crosscheck_rd01():
                """Deterministic verification of the fresh RD01 draft against
                the legacy sources — catches a cheap model's two failure
                modes (omission / hallucination) the second they happen,
                not weeks later in TIA."""
                try:
                    from rd01_crosscheck import crosscheck_rd01  # type: ignore
                    cc = crosscheck_rd01(self.root)
                    job["lines"].append(f"\n⚖ {cc['summary']}")
                    # Deterministic completion: a big machine's IO table does
                    # not fit a cheap model's output window — missing operands
                    # are appended straight from the parsed symbol table
                    # (Zuordnungsliste). No AI, idempotent, rows flagged.
                    if cc["missing_in_rd01"]:
                        from rd01_autocomplete import complete_rd01  # type: ignore
                        fix = complete_rd01(self.root)
                        if fix.get("appended"):
                            job["lines"].append(
                                f"\n⚙ RD01 auto-completed: {fix['appended']} "
                                "operand(s) appended from the symbol table "
                                "(deterministic).")
                            cc = fix.get("crosscheck_after") or cc
                            job["lines"].append(f"\n⚖ {cc['summary']}")
                    # Equipment column guarantee: the assembler groups devices
                    # by this column; an AI draft that leaves it empty
                    # collapses the wiring (A/B/C field measurement
                    # 2026-07-03: 15 → 5 bound ports). Deterministic fill
                    # from the legacy device references — empty cells only.
                    try:
                        from rd01_autocomplete import enrich_equipment  # type: ignore
                        enr = enrich_equipment(self.root)
                        if enr.get("filled"):
                            job["lines"].append(
                                f"\n⚙ RD01 Equipment column: {enr['filled']} "
                                "cell(s) filled from legacy device refs "
                                "(deterministic).")
                    except Exception as _ee:
                        job["lines"].append(
                            f"\n⚠ RD01 equipment enrichment failed: {_ee}")
                    if not cc["ok"]:
                        detail = []
                        if cc["missing_in_rd01"]:
                            detail.append("missing from RD01: "
                                          + ", ".join(cc["missing_in_rd01"][:12]))
                        if cc["not_in_source"]:
                            detail.append("no legacy source: "
                                          + ", ".join(cc["not_in_source"][:12]))
                        if cc["dir_mismatch"]:
                            detail.append("; ".join(cc["dir_mismatch"][:6]))
                        _msg = cc["summary"] + " — " + " | ".join(detail)
                        job["warnings"].append(_msg)
                        on_warn(_msg)
                except Exception as _e:
                    job["lines"].append(f"\n⚠ RD01 cross-check failed to run: {_e}")

            def on_flow_done():
                # Auto-continue hop: phase 1 (discovery) done → immediately
                # start the topic workflow in the SAME job. The reviewed-check
                # is skipped by design (engineer opted in on the consent
                # modal); the gap is recorded loudly in the job warnings.
                if auto_continue and _chain is None and _next_topic:
                    job["lines"].append(
                        f"\n▶ Auto-continue: starting {_next_topic} on the "
                        "fresh (unreviewed) Gate-1 drafts…")
                    job["current_step"] = f"Continuing: {_next_topic}"
                    _gap = (f"{_next_topic} ran on UNREVIEWED Gate-1 drafts "
                            "(auto-continue). Review RD01/02/03 first — an "
                            "error there propagates into every topic RD.")
                    job["warnings"].append(_gap)
                    try:
                        r2 = self.run_retrofit_preanalysis(
                            consent_data, workflow_name=_next_topic,
                            _chain={"job": job, "offset": len(_wf_steps)})
                    except Exception as e2:
                        r2 = {"ok": False, "msg": str(e2)}
                    if not r2.get("ok"):
                        job.update(running=False, done=True, ok=False, msg=(
                            "Gate-1 drafts are written, but auto-continue "
                            f"could not start {_next_topic}: "
                            f"{r2.get('msg', 'unknown error')} — run it "
                            "manually from the Gate 2 panel."))
                    return
                _done_msg = ("Pre-analysis complete — review the RD drafts "
                             "in metadata/")
                if _chain is not None:
                    _done_msg = (
                        "Full analysis complete — all RD drafts written in "
                        "one run. Topic RDs were generated from UNREVIEWED "
                        "Gate-1 drafts: review RD01/02/03 first, then the "
                        "topic RDs, before the Gate-3 lock.")
                job.update(running=False, done=True, ok=True, msg=_done_msg)
            def on_error(msg):
                job["lines"].append(f"\n✗ {msg}")
                job.update(running=False, done=True, ok=False, msg=msg)
            def on_warn(msg):
                job["lines"].append(f"\n⚠ {msg}")
                job["warnings"].append(msg)

            def _draft_writer(step, content):
                """Place a step's output into metadata/ as a reviewable draft."""
                from rd_draft_writer import write_rd_draft  # type: ignore
                res = write_rd_draft(
                    self.root, step.metadata_target, content,
                    source_step=step.name,
                    model_id=step.model or model,
                )
                if res.warning:
                    on_warn(res.warning)
                job["drafts"].append({
                    "rd": step.metadata_target,
                    "file": res.path.name,
                    "action": res.action,
                })
                if step.metadata_target == "RD03":
                    _auto_regen_mermaid()
                if step.metadata_target == "RD01":
                    _auto_crosscheck_rd01()
                try:
                    _audit_log(
                        self.root, f"rd_draft_write:{step.metadata_target}",
                        step.provider or provider, step.model or model,
                        prompt_text=f"target={res.path.name}; action={res.action}",
                        prompt_id=f"retrofit_preanalysis:draft:{step.metadata_target}",
                    )
                except AuditLogError as ae:
                    on_warn(f"Draft audit log failed for {step.metadata_target}: {ae}")

            runner = AutoFlowRunner(
                # text_provider is Anthropic when Google is global (free-tier
                # Google limits 20 req/day; Step 1 overrides to google anyway).
                provider=text_provider, model=text_model,
                api_key=self._resolve_api_key(text_provider),
                project_root=self.root,
                on_step_start=on_step_start, on_step_chunk=on_step_chunk,
                on_step_done=on_step_done, on_flow_done=on_flow_done,
                on_error=on_error, on_warn=on_warn,
                multimodal_files=multimodal_files,
                api_key_resolver=self._resolve_api_key,
                draft_writer=_draft_writer,
                on_usage=self._add_cost,  # B8: real spend bookkeeping
                system_prompt_suffix=_lang_directive(self._output_language()),
                # B-L3/B-G1/B-G2 fix: forward engineer consent to the runner thread.
                # Without this, the guard inside _run() re-evaluates without consent
                # and kills CONFIDENTIAL workflows that the user explicitly approved.
                consent_confirmed=_preanalysis_consent_confirmed,
                # S-6 (B-L2): persisted outputs (REPORTS/ + RD drafts) get the
                # real names back — placeholders like CUSTOMER_A must never
                # reach customer-facing documents. Applied at the persistence
                # boundary only; the step chain stays anonymized.
                output_postprocess=(
                    (lambda _t: deanonymize_text(_t, anon_map))
                    if anon_map else None),
            )
            runner.run_async(workflow_name, tmp_legacy)
            return _attach_warnings({
                "ok": True,
                "started": True,
                "msg": f"{workflow_name} started — progress via get_preanalysis_status()",
                "files_processed": len(multimodal_files) + len(legacy_parts),
            })
        except Exception as exc:
            job = getattr(self, "_preanalysis_job", None)
            if job is not None:
                job.update(running=False, done=True, ok=False, msg=str(exc))
            return _attach_warnings({"ok": False, "msg": str(exc)})

    def get_preanalysis_status(self) -> dict:
        """Polling endpoint for the background pre-analysis job (M2)."""
        job = getattr(self, "_preanalysis_job", None)
        if not job:
            return _attach_warnings({"ok": True, "exists": False})
        # S-9: timeout guard — 30-minute hard ceiling on background jobs.
        # Fail-safe: if started_at is missing (legacy dict), time.time() is used
        # as fallback so the diff is ~0 and timeout is NOT triggered.
        if (
            job.get("running")
            and time.time() - job.get("started_at", time.time()) > 1800
        ):
            job["running"] = False
            job["done"] = True
            job["ok"] = False
            job["msg"] = "Preanalysis timeout (>30 min) — job was forcibly stopped"
        return _attach_warnings({
            "ok": True,
            "exists": True,
            "running": job["running"],
            "done": job["done"],
            "succeeded": job["ok"],
            "msg": job["msg"],
            "current_step": job["current_step"],
            "step_index": job.get("step_index", -1),
            "step_total": job.get("step_total", 6),
            "step_names": job.get("step_names", []),
            "drafts": list(job["drafts"]),
            "job_warnings": list(job["warnings"]),
            # B-02: input size so the GUI can flag oversize runs in flight
            "input_chars": job.get("input_chars", 0),
            "input_est_tokens": job.get("input_est_tokens", 0),
            # tail only — full text lands in REPORTS/
            "output_tail": "".join(job["lines"])[-4000:],
        })

    # ------------------------------------------------------------------
    # M3 — library-first program assembly
    # ------------------------------------------------------------------

    def get_rd01_crosscheck(self) -> dict:
        """On-demand deterministic RD01-vs-legacy-source verification."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        try:
            from rd01_crosscheck import crosscheck_rd01  # type: ignore
            return _attach_warnings({"ok": True, **crosscheck_rd01(self.root)})
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"Cross-check failed: {exc}"})

    def get_regen_delta(self) -> dict:
        """Change-management preview: current RD01 vs the last assembly
        manifest — which devices would 'Regenerate affected' touch."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        try:
            from program_assembler import compute_delta  # type: ignore
            d = compute_delta(self.root)
            return _attach_warnings({"ok": True, **d})
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"Delta scan failed: {exc}"})

    def run_delta_assembly(self) -> dict:
        """Regenerate ONLY the devices the RD01 change touched (delta mode).

        Unchanged devices' files stay byte-for-byte untouched; OB_Main.scl is
        rebuilt from the full list; removed devices are reported as orphaned
        and never deleted. Falls back to a full assembly when no manifest
        exists yet."""
        if not self.root:
            return _attach_warnings({"ok": False, "output": "No project open"})
        blocked = self._rd05_code_gen_gate("Delta Assembly")
        if blocked:
            return blocked
        try:
            from program_assembler import assemble_delta  # type: ignore
            res = assemble_delta(self.root)
        except Exception as exc:
            return _attach_warnings({"ok": False, "output": f"Delta assembly failed: {exc}"})
        return self._assembly_response(res)

    def _rd05_code_gen_gate(self, action: str) -> Optional[dict]:
        """S-1 (audit M-01): the RD05 safety gate existed for the FAT
        protocol and the customer report, but the code-generation chain
        (assemble_program / generate_scl / send_to_tia) never called it —
        a Gate-1 project could be assembled and pushed into a real TIA
        project with the safety analysis unreviewed. Same single source of
        truth as generate_fat (fat_protocol.check_rd05_ready, fail-closed).
        Returns None when ready, else a precondition_error response in the
        same shape the GUI already renders for generate_report."""
        try:
            from fat_protocol import Rd05BlockedError, check_rd05_ready  # type: ignore
        except Exception as exc:
            return _attach_warnings({
                "ok": False, "precondition_error": True,
                "msg": f"RD05 safety gate unavailable ({exc}) — blocked.",
                "output": f"BLOCKED — RD05 safety gate unavailable: {exc}",
                "reasons": [str(exc)]})
        try:
            check_rd05_ready(self.root)
            return None
        except Rd05BlockedError as exc:
            reason = str(exc)
            return _attach_warnings({
                "ok": False, "precondition_error": True,
                "msg": f"RD05 safety gate: {reason}",
                "output": (f"BLOCKED — RD05 safety gate: {reason}\n"
                           f"'{action}' generates or transfers program code; "
                           "the safety analysis must be reviewed and approved "
                           "first (Gate 3)."),
                "reasons": [reason]})
        except Exception as exc:
            # The gate itself failing must block, not fall open.
            return _attach_warnings({
                "ok": False, "precondition_error": True,
                "msg": f"RD05 safety gate check failed ({exc}) — blocked.",
                "output": f"BLOCKED — RD05 safety gate check failed: {exc}",
                "reasons": [str(exc)]})

    def assemble_program(self) -> dict:
        """Deterministic library-first assembly from the approved RD01."""
        if not self.root:
            return _attach_warnings({"ok": False, "output": "No project open"})
        blocked = self._rd05_code_gen_gate("Assemble Program")
        if blocked:
            return blocked
        try:
            from program_assembler import assemble_program  # type: ignore
            res = assemble_program(self.root)
        except Exception as exc:
            return _attach_warnings({"ok": False, "output": f"Assembly failed: {exc}"})
        return self._assembly_response(res)

    def _assembly_response(self, res) -> dict:
        """Shared response shaping for full and delta assembly runs."""
        for w in res.warnings:
            _warn(w, category="assembly")
        # Post-assembly companion reports — all deterministic, all honest:
        # interlock draft (proven S5 logic), sequence draft, assumption
        # ledger (one page of unknowns), traceability matrix, scorecard.
        companions = self._generate_companion_reports(res)
        lines = [res.msg, ""]
        if companions:
            lines.append("Companion reports: " + ", ".join(companions))
            lines.append("")
        if res.delta_mode:
            if res.affected:
                lines.append("Regenerated: " + ", ".join(sorted(set(res.affected))))
            if res.skipped:
                lines.append(f"Untouched ({len(res.skipped)}): "
                             + ", ".join(res.skipped))
            if res.orphaned:
                lines.append("⚠ Orphaned (review & delete manually): "
                             + ", ".join(res.orphaned))
            lines.append("")
        if res.matches:
            lines.append("Matched devices:")
            for m in res.matches:
                lines.append(f"  {m.device.device_id} → {m.fb_block_name} ({m.instance_db})")
        if res.unknown:
            lines.append("")
            lines.append(f"#UNKNOWN ({len(res.unknown)} item(s) need an engineer):")
            for u in res.unknown[:15]:
                lines.append(f"  ! {u['item']} — {u['reason']}")
        if res.report_path:
            lines.append("")
            lines.append(f"Full report: REPORTS/{res.report_path.name}")
        return _attach_warnings({
            "ok": res.ok,
            "output": "\n".join(lines),
            "matched": len(res.matches),
            "unknown": len(res.unknown),
            "delta_mode": res.delta_mode,
            "affected": sorted(set(res.affected)),
            "orphaned": res.orphaned,
            "report": res.report_path.name if res.report_path else None,
        })

    # Known report files, in the order an engineer reads them. Anything
    # else in REPORTS/*.md is appended after (never hidden).
    _REPORT_CATALOG = [
        ("ASSUMPTION_LEDGER.md", "Everything the factory does NOT know — scan before signing a gate"),
        ("ASSEMBLY_REPORT.md", "Device→FB mapping, bindings, verbatim proof"),
        ("INTERLOCK_DRAFT.md", "Per-device conditions extracted from the legacy code (self-proven)"),
        ("SEQUENCE_DRAFT.md", "Detected Schrittkette chains with transitions"),
        ("FLOWCHART_CROSSCHECK.md", "AI flowchart verified against the proven chain"),
        ("TRACEABILITY_MATRIX.md", "Legacy operand → new tag/port, auditable"),
        ("PROJECT_SCORECARD.md", "One line per assembly run"),
        ("TEST_SCENARIOS.md", "Gate-6 test scenarios from FB contracts"),
    ]

    def get_workdesk(self) -> dict:
        """3-part sidebar (2026-07-07): the engineer's DESK — every surface
        they EDIT or SIGN, with honest status chips — plus the read-only
        REVIEW list (reference RDs in reading mode + deterministic reports).
        One call so the sidebar refresh stays cheap."""
        if not self.root:
            return _attach_warnings({"ok": False, "desk": [], "reading": []})
        st = self._project_state()
        # _rd_review_states iterates over rd_statuses — feed it a minimal
        # "produced?" map from file presence (analyze_project would be
        # overkill for a sidebar refresh).
        _all_rds = [f"RD{i:02d}" for i in range(1, 15)]
        rd_statuses = {rd: ("done" if _rd_main_file(self.root, rd) else "")
                       for rd in _all_rds}
        rev = _rd_review_states(self.root, st, rd_statuses)

        def _rd_item(rd: str, label: str, icon: str) -> dict:
            fp = _rd_main_file(self.root, rd)
            v = rev.get(rd, {})
            state = ("na" if v.get("na") else "locked" if v.get("locked")
                     else "reviewed" if v.get("reviewed")
                     else "draft" if fp is not None else "missing")
            return {"kind": f"rd:{rd}", "label": label, "icon": icon,
                    "rd": rd, "path": self._relpath(fp) if fp else "",
                    "state": state,
                    "by": v.get("reviewed_by", "")}

        desk: list[dict] = [
            _rd_item("RD01", "IO List", "table"),
            _rd_item("RD11", "HMI Tags", "table"),
            _rd_item("RD08", "Alarms", "table"),
        ]
        # Device decisions (dossier grid / Old→Target): decided vs total rows
        try:
            from machine_dossier import load_decisions  # type: ignore
            n_dec = len(load_decisions(self.root))
        except Exception:
            n_dec = 0
        has_dossier = (self.root / "metadata" / "machine_dossier").is_dir()
        desk.append({"kind": "decisions", "label": "Device decisions",
                     "icon": "layers", "state": "grid" if has_dossier else "missing",
                     "count": n_dec})
        # HMI wiring approval: open/approved/rejected line counts
        try:
            from hmi_wiring import wiring_rows  # type: ignore
            rows = wiring_rows(self.root)
            n_open = sum(1 for r in rows
                         if r["area"] != "Sts" and r.get("approved") is None)
            desk.append({"kind": "wiring", "label": "HMI wiring approval",
                         "icon": "zap",
                         "state": ("open" if n_open else "done") if rows else "missing",
                         "count": n_open,
                         "path": "_output/HMI_WIRING_PROPOSAL.md"})
        except Exception:
            desk.append({"kind": "wiring", "label": "HMI wiring approval",
                         "icon": "zap", "state": "missing", "count": 0,
                         "path": "_output/HMI_WIRING_PROPOSAL.md"})
        # RD05: a SIGN surface (named engineer approval), not reading material
        desk.append(_rd_item("RD05", "Safety sign-off", "shield"))

        # Read-only review list: reference RDs (reading mode) + reports.
        _READING_RDS = [
            ("RD02", "Data Dictionary"), ("RD03", "Logic Flow"),
            ("RD04", "Operating Modes"), ("RD06", "Motion / Axes"),
            ("RD07", "Timing"), ("RD09", "Communications"),
            ("RD10", "FB Spec"), ("RD12", "Use Cases"),
            ("RD13", "Legacy Annotation"), ("RD14", "Modernization Map"),
        ]
        reading: list[dict] = []
        for rd, label in _READING_RDS:
            fp = _rd_main_file(self.root, rd)
            if fp is None or rev.get(rd, {}).get("na"):
                continue
            reading.append({"kind": f"rdread:{rd}", "label": label, "rd": rd,
                            "path": self._relpath(fp)})
        rep = self.list_project_reports()
        for r in (rep.get("reports") or []):
            reading.append({"kind": "report", "label": r["name"].replace(".md", ""),
                            "path": r["path"], "hint": r.get("hint", "")})
        return _attach_warnings({"ok": True, "desk": desk, "reading": reading})

    def list_project_reports(self) -> dict:
        """REPORTS/*.md with catalog hints — the sidebar quick-access list."""
        if not self.root:
            return _attach_warnings({"ok": False, "reports": []})
        rep_dir = self.root / "REPORTS"
        out: list[dict] = []
        seen: set[str] = set()
        if rep_dir.is_dir():
            from datetime import datetime as _dt

            def _entry(name: str, p, hint: str) -> dict:
                return {
                    "name": name, "path": f"REPORTS/{name}", "hint": hint,
                    "modified": _dt.fromtimestamp(
                        p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                }

            # Working files (leading underscore, e.g. the timestamped
            # _preanalysis_*_RDxx_draft.md batches) are intermediate
            # artifacts, not reports — they bloated the sidebar to 23
            # rows on the blind-test project (user audit 2026-07-06).
            # They stay on disk and in the Explorer tree.
            by_name = {p.name: p for p in rep_dir.glob("*.md")
                       if not p.name.startswith("_")}
            for name, hint in self._REPORT_CATALOG:
                p = by_name.get(name)
                if p is None:
                    continue
                seen.add(name)
                out.append(_entry(name, p, hint))
            for name, p in sorted(by_name.items()):
                if name not in seen:
                    out.append(_entry(name, p, ""))
        return _attach_warnings({"ok": True, "reports": out})

    def project_qa(self, query: str) -> dict:
        """Deterministic, source-cited project search — see project_qa.py."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        try:
            from project_qa import ask_project  # type: ignore
            r = ask_project(self.root, query or "")
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"QA failed: {exc}"})
        if r.report_path is None:
            return _attach_warnings({"ok": False, "msg": "Empty query"})
        return _attach_warnings({
            "ok": True, "hits": r.hits, "files": r.files,
            "report": "REPORTS/PROJECT_QA.md",
            "msg": (f"{r.hits} hit(s) in {r.files} document(s)"
                    if r.hits else "Not found in the project documents"),
        })

    def export_handover_package(self) -> dict:
        """Übergabemappe: ONE zip the customer/auditor can open — RD
        documents, all reports, the generated sources and a SHA-256
        manifest proving what was delivered. Deterministic; read-only
        over the project."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        import hashlib
        import zipfile
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        out_dir = self.root / "_delivery"
        out_dir.mkdir(exist_ok=True)
        zip_path = out_dir / f"Handover_{self.root.name}_{stamp}.zip"

        # Machine Dossier print copy: customer marks up the PDF/Excel, the
        # engineer edits the SAME visual (user decision 2026-07-06). The PDF
        # is a handover artifact — it is born in _delivery/, never in the
        # working dossier folder. Fail-soft — a missing Edge/dossier never
        # blocks the handover.
        dossier_pdf = None
        try:
            from machine_dossier import export_dossier_pdf  # type: ignore
            dossier_pdf = export_dossier_pdf(self.root, out_dir)
        except Exception as exc:
            _warn(f"dossier pdf skipped: {exc}", category="handover")

        # REVISION_LOG.md: refresh the delivery record (baseline ⇄ delivered
        # + every named decision) so the ZIP always carries the current
        # story. Fail-soft — a log failure never blocks the handover.
        try:
            from revision_log import generate_revision_log  # type: ignore
            generate_revision_log(self.root)
        except Exception as exc:
            _warn(f"revision log skipped: {exc}", category="handover")

        dossier_dir = self.root / "metadata" / "machine_dossier"
        dossier_files = (
            sorted(fp for fp in dossier_dir.glob("*")
                   if fp.is_file() and fp.suffix.lower() != ".pdf")
            if dossier_dir.is_dir() else [])
        if dossier_pdf is not None:
            dossier_files.append(dossier_pdf)
        groups = [
            ("metadata", sorted((self.root / "metadata").glob("RD*.md"))
             if (self.root / "metadata").is_dir() else []),
            ("machine_dossier", dossier_files),
            ("REPORTS", sorted((self.root / "REPORTS").glob("*.md"))
             if (self.root / "REPORTS").is_dir() else []),
            ("_output/scl", sorted((self.root / "_output" / "scl").glob("*"))
             if (self.root / "_output" / "scl").is_dir() else []),
        ]
        manifest: list[str] = [
            f"# HANDOVER MANIFEST — {self.root.name}",
            f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            "",
            "Label: AUTO_VERIFIED_structural | PENDING_TIA_VERIFY — TIA",
            "compile and PLCSIM run remain required before field use.",
            "",
            "| File | SHA-256 |",
            "|------|---------|",
        ]
        count = 0
        try:
            with zipfile.ZipFile(zip_path, "w",
                                 zipfile.ZIP_DEFLATED) as zf:
                for arc_prefix, files in groups:
                    for fp in files:
                        if not fp.is_file():
                            continue
                        arc = f"{arc_prefix}/{fp.name}"
                        zf.write(fp, arc)
                        sha = hashlib.sha256(fp.read_bytes()).hexdigest()
                        manifest.append(f"| {arc} | `{sha}` |")
                        count += 1
                zf.writestr("MANIFEST.md", "\n".join(manifest))
        except Exception as exc:
            return _attach_warnings({"ok": False,
                                     "msg": f"Handover export failed: {exc}"})
        if count == 0:
            zip_path.unlink(missing_ok=True)
            return _attach_warnings({
                "ok": False,
                "msg": "Nothing to deliver yet — no RD docs, reports or "
                       "generated sources found."})
        return _attach_warnings({
            "ok": True,
            "msg": f"Handover package: {count} file(s) → "
                   f"_delivery/{zip_path.name}",
            "path": str(zip_path), "files": count,
        })

    # ------------------------------------------------------------------
    # Machine Dossier (GORSEL PAKET v2) — approval-side visual pack:
    # analyze → engineer edits the DECISION columns → gate-3 → code gen.
    # Deterministic generator; AI is never called from here.
    # ------------------------------------------------------------------

    def generate_machine_dossier(self) -> dict:
        """Generate the 6-page Machine Dossier into metadata/machine_dossier."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from machine_dossier import generate_machine_dossier as _gen
            s = _gen(self.root)
            msg = (f"Machine dossier: {len(s.files)} file(s) — "
                   f"{s.chains} chain(s), {s.steps} steps, "
                   f"{s.signals} signal rows → metadata/machine_dossier/")
            return {"ok": True, "msg": msg, "files": s.files,
                    "warnings": s.warnings, "chains": s.chains,
                    "steps": s.steps}
        except Exception as e:
            return {"ok": False, "msg": f"Dossier generation failed: {e}"}

    def list_machine_dossier(self) -> dict:
        """Existing dossier files (name/relpath/kind) for the sidebar panel."""
        if not self.root:
            return {"ok": False, "files": []}
        d = self.root / "metadata" / "machine_dossier"
        files = []
        if d.is_dir():
            for fp in sorted(d.iterdir()):
                if fp.is_file():
                    files.append({
                        "name": fp.name,
                        "path": self._relpath(fp),
                        "kind": fp.suffix.lstrip(".").lower(),
                    })
        return {"ok": True, "files": files}

    def get_dossier_svg(self, name: str) -> dict:
        """SVG text for the in-app viewer (own generated content only)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        base = Path(name).name
        fp = self.root / "metadata" / "machine_dossier" / base
        if fp.suffix.lower() != ".svg" or not fp.is_file():
            return {"ok": False, "msg": f"Not an existing dossier SVG: {base}"}
        try:
            return {"ok": True, "name": base,
                    "svg": fp.read_text(encoding="utf-8")}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_decision_table(self) -> dict:
        """Rows for the in-app decision grid (deterministic + merged
        engineer decisions)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from machine_dossier import (  # type: ignore
                _DECISION_HEADERS, build_decision_rows,
            )
            rows = build_decision_rows(self.root)
            return {"ok": True, "headers": list(_DECISION_HEADERS),
                    "rows": rows}
        except Exception as e:
            return {"ok": False, "msg": f"Decision table failed: {e}"}

    def save_decision_table(self, entries: list) -> dict:
        """Persist engineer decisions (decisions.json) + refresh xlsx/md.
        entries: [{address, decision, impact}, …] — only the two engineer
        columns are writable; deterministic cells are never touched."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from machine_dossier import save_decisions  # type: ignore
            merged = {
                str(e.get("address", "")).strip(): {
                    "decision": e.get("decision", ""),
                    "impact": e.get("impact", ""),
                }
                for e in (entries or []) if str(e.get("address", "")).strip()
            }
            n = save_decisions(self.root, merged)
            return {"ok": True,
                    "msg": f"Decisions saved: {n} entr{'y' if n == 1 else 'ies'} "
                           "(decisions.json + xlsx/md refreshed)"}
        except Exception as e:
            return {"ok": False, "msg": f"Save failed: {e}"}

    def get_decision_cascade(self) -> dict:
        """Old⇄Target view of the dossier decisions — the structured
        (KEEP/REPLACE/DROP) reading plus the propagation cascade per device.
        Deterministic and read-only; shares its vocabulary and its evidence
        sources with the Gate-3 reconciliation."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from decision_cascade import compute_cascade  # type: ignore
            c = compute_cascade(self.root)
            return {"ok": True, "devices": c.get("devices", []),
                    "summary": c.get("summary", {})}
        except Exception as e:
            return {"ok": False, "msg": f"Cascade failed: {e}"}

    def open_dossier_file(self, name: str) -> dict:
        """Open a dossier file with its system default app (SVG → browser,
        XLSX → Excel). Basename-only — traversal is structurally impossible."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        base = Path(name).name
        fp = self.root / "metadata" / "machine_dossier" / base
        if not fp.is_file():
            return {"ok": False, "msg": f"Not found: {base}"}
        try:
            os.startfile(str(fp))  # noqa: S606 — project-scoped file
            return {"ok": True, "msg": f"Opened {base}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def _generate_companion_reports(self, res) -> list[str]:
        """Deterministic post-assembly reports. Each one fail-warns alone —
        a companion failure never blocks the assembly result."""
        out: list[str] = []
        try:
            from interlock_report import generate_interlock_draft  # type: ignore
            s = generate_interlock_draft(self.root)
            if s.networks:
                out.append(f"INTERLOCK_DRAFT.md ({s.parsed}/{s.networks} "
                           "networks proven)")
        except Exception as exc:
            _warn(f"interlock draft failed: {exc}", category="assembly")
        try:
            from sequence_map import generate_sequence_draft  # type: ignore
            s = generate_sequence_draft(self.root)
            if s.chains:
                out.append(f"SEQUENCE_DRAFT.md ({s.chains} chain(s), "
                           f"{s.steps_in_chains} steps)")
        except Exception as exc:
            _warn(f"sequence draft failed: {exc}", category="assembly")
        try:
            from sequence_map import crosscheck_rd03  # type: ignore
            fc = crosscheck_rd03(self.root)
            if fc.steps:
                out.append(f"FLOWCHART_CROSSCHECK.md ({fc.summary.split(': ', 1)[1]})")
            if fc.mismatches:
                _warn(f"RD03 flowchart: {len(fc.mismatches)} mismatch(es) vs "
                      "the proven step chain — see FLOWCHART_CROSSCHECK.md",
                      category="assembly")
        except Exception as exc:
            _warn(f"RD03 cross-check failed: {exc}", category="assembly")
        try:
            from traceability_matrix import generate_traceability_matrix  # type: ignore
            t = generate_traceability_matrix(self.root)
            out.append(f"TRACEABILITY_MATRIX.md ({t.bound}/{t.rows} bound)")
        except Exception as exc:
            _warn(f"traceability matrix failed: {exc}", category="assembly")
        try:
            from assumption_ledger import generate_assumption_ledger  # type: ignore
            a = generate_assumption_ledger(self.root)
            out.append(f"ASSUMPTION_LEDGER.md ({a.blockers} blocker, "
                       f"{a.reviews} review)")
        except Exception as exc:
            _warn(f"assumption ledger failed: {exc}", category="assembly")
        try:
            self._append_scorecard(res)
        except Exception as exc:
            _warn(f"scorecard failed: {exc}", category="assembly")
        return out

    def _append_scorecard(self, res) -> None:
        """One line per assembly run — the project's progress at a glance."""
        from datetime import datetime, timezone
        wired = sum(len(m.in_bindings) + len(m.out_bindings)
                    for m in res.matches)
        todos = sum(len(m.todos) for m in res.matches)
        sc = self.root / "REPORTS" / "PROJECT_SCORECARD.md"
        sc.parent.mkdir(exist_ok=True)
        if not sc.is_file():
            sc.write_text(
                "# PROJECT SCORECARD — one line per assembly run\n\n"
                "| When (UTC) | Devices | Wired ports | TODOs | #UNKNOWN |\n"
                "|---|---|---|---|---|\n",
                encoding="utf-8")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        with sc.open("a", encoding="utf-8") as f:
            f.write(f"| {now} | {len(res.matches)} | {wired} | {todos} | "
                    f"{len(res.unknown)} |\n")

    def generate_hmi_draft(self) -> dict:
        """Deterministic RD11/RD08 drafts from the wired-pulpit inventory
        (see hmi_draft.py). Never overwrites engineer-edited RDs."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_draft import generate_hmi_drafts  # type: ignore
            r = generate_hmi_drafts(self.root)
        except Exception as e:
            return {"ok": False, "msg": f"HMI draft failed: {e}"}
        msg = (f"RD drafts: {', '.join(r['written']) or 'none written'} · "
               f"{r['buttons']} buttons, {r['selectors']} selectors, "
               f"{r['numeric']} setpoints, {r['indicators']} lamps, "
               f"{r['alarms']} alarms, {r['hardwired']} stay hardwired")
        if r["refused"]:
            msg += f" · REFUSED: {'; '.join(r['refused'])}"
        return {"ok": True, "msg": msg, **r}

    def generate_hmi_interface(self) -> dict:
        """PLC-side HMI layer from RD11/RD08: DB_HMI.scl, DB_Alarm.scl,
        hmi_tags.xlsx and the (never auto-applied) wiring proposal."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_codegen import generate_hmi_interface as _gen  # type: ignore
            r = _gen(self.root)
        except Exception as e:
            return {"ok": False, "msg": f"HMI interface generation failed: {e}"}
        if not r.get("ok"):
            return r
        c = r["counts"]
        r["msg"] = (f"_output/: {', '.join(r['files'])} · Cmd {c['cmd']} / "
                    f"Set {c['set']} / Sts {c['sts']} / alarms {c['alarms']}"
                    + (f" · {len(r['problems'])} rows need review"
                       if r["problems"] else ""))
        return r

    def get_hmi_wiring(self) -> dict:
        """Wiring proposal rows joined with the persisted engineer decisions
        (metadata/hmi_wiring.json) — the approval grid's data source."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_wiring import wiring_rows_with_problems  # type: ignore
            rows, problems = wiring_rows_with_problems(self.root)
        except Exception as e:
            return {"ok": False, "msg": f"Wiring rows failed: {e}"}
        if not rows and not problems:
            return {"ok": False,
                    "msg": "No wiring rows — generate the HMI draft/interface first."}
        # S-5 (audit M-02): rows the proposal could NOT use are part of the
        # answer — "0 open items" must never hide dropped RD11 rows.
        return {"ok": True, "rows": rows,
                "approved": sum(1 for r in rows if r.get("approved") is True),
                "rejected": sum(1 for r in rows if r.get("approved") is False),
                "open": sum(1 for r in rows if r.get("approved") is None),
                "problems": problems, "dropped": len(problems)}

    def set_hmi_wiring(self, tag: str, approved: bool, by: str = "",
                       note: str = "") -> dict:
        """Record the engineer's decision for one wiring line. Approval
        needs a name (wiring changes program semantics)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_wiring import save_wiring_decision  # type: ignore
            ok, msg = save_wiring_decision(self.root, tag, bool(approved),
                                           by, note)
        except Exception as e:
            return {"ok": False, "msg": f"Wiring save failed: {e}"}
        return {"ok": ok, "msg": msg, "tag": tag}

    def generate_hmi_wiring_code(self) -> dict:
        """FC_HMI_Wiring.scl from the APPROVED wiring + proven lamp/alarm
        equations (operands translated via RD01; gaps become TODOs, never
        guesses). Also regenerates DB_HMI so Mrg members exist."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_wiring import generate_wiring_code  # type: ignore
            r = generate_wiring_code(self.root)
        except Exception as e:
            return {"ok": False, "msg": f"Wiring codegen failed: {e}"}
        if r.get("ok"):
            r["msg"] = (f"_output/{r['file']}: {r['cmd_merged']} approved "
                        f"merge(s), {r['sts_driven']} lamp drive(s), "
                        f"{r['alarms_driven']} alarm drive(s)"
                        + (f" · {len(r['todo'])} honest TODO(s)"
                           if r.get("todo") else ""))
        return r

    def generate_revision_log(self) -> dict:
        """REPORTS/REVISION_LOG.md — baseline ⇄ delivered + every named
        decision (grid edits, device decisions, waivers, wiring)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from revision_log import generate_revision_log as _gen  # type: ignore
            from revision_log import snapshot_baseline  # type: ignore
            captured = snapshot_baseline(self.root)
            fp = _gen(self.root)
        except Exception as e:
            return {"ok": False, "msg": f"Revision log failed: {e}"}
        if fp is None:
            return {"ok": False, "msg": "Revision log could not be written"}
        return {"ok": True, "path": self._relpath(fp),
                "msg": f"REPORTS/{fp.name} written"
                       + (f" · baseline captured for {len(captured)} file(s)"
                          if captured else "")}

    def read_hmi_table(self, kind: str) -> dict:
        """Structured rows for the RD11/RD08 grid editors."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_table_edit import KINDS, parse_table  # type: ignore
        except Exception as e:
            return {"ok": False, "msg": str(e)}
        spec = KINDS.get(kind)
        if not spec:
            return {"ok": False, "msg": f"Unknown table kind '{kind}'"}
        fp = self.root / "metadata" / spec["file"]
        if not fp.exists():
            return {"ok": False, "msg": f"{spec['file']} not found — run the HMI draft first"}
        cols, rows, _ = parse_table(fp.read_text(encoding="utf-8"),
                                    spec["key"])
        return {"ok": True, "kind": kind, "file": spec["file"],
                "key": spec["key"], "columns": cols,
                "editable": list(spec["editable"]), "rows": rows}

    def save_hmi_table(self, kind: str, edits: dict) -> dict:
        """Apply engineer grid edits: MD table updated in place AND the
        decisions persisted (hmi_decisions.json) so regeneration keeps
        them. Locked columns / invalid values are refused, not dropped."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from hmi_table_edit import (  # type: ignore
                KINDS, apply_edits, save_decisions,
            )
        except Exception as e:
            return {"ok": False, "msg": str(e)}
        spec = KINDS.get(kind)
        if not spec:
            return {"ok": False, "msg": f"Unknown table kind '{kind}'"}
        fp = self.root / "metadata" / spec["file"]
        if not fp.exists():
            return {"ok": False, "msg": f"{spec['file']} not found"}
        text = fp.read_text(encoding="utf-8")
        new_text, problems = apply_edits(text, kind, edits or {})
        if new_text != text:
            fp.write_text(new_text, encoding="utf-8")
            save_decisions(self.root, kind, edits or {})
        applied = sum(len(v or {}) for v in (edits or {}).values())
        return {"ok": True, "problems": problems,
                "msg": (f"Saved — {applied - len(problems)} change(s)"
                        + (f", {len(problems)} refused" if problems else ""))}

    def generate_test_scenarios(self) -> dict:
        """Generate Gate 6 test scenarios from RD01 + FB contract behaviors (read-only).

        NOTE: This is the Gate 6 SIMULATION artifact, NOT the RD13 Legacy
        Annotation (a Gate 1 pre-analysis output). The two were once conflated
        under "RD13"; see the internal RD-gate design note.
        """
        if not self.root:
            return _attach_warnings({"ok": False, "output": "No project open"})
        try:
            from rag.test_scenario_generator import generate_test_scenarios as _gen_ts  # type: ignore
            result = _gen_ts(self.root)
        except Exception as exc:
            return _attach_warnings({"ok": False, "output": f"Test scenario generation failed: {exc}"})
        if not result.get("ok"):
            return _attach_warnings({"ok": False, "output": result.get("msg", "Generation failed")})
        lines = [
            f"Test scenarios generated: {result['tc_count']} test cases, {result['device_count']} devices",
            f"  MD  : REPORTS/TEST_SCENARIOS.md",
            f"  JSON: REPORTS/gate_results/test_scenarios.json",
        ]
        return _attach_warnings({"ok": True, "output": "\n".join(lines), **result})

    def generate_sequence_fb(self, consent: Optional[dict] = None) -> dict:
        """AI-generate the project sequence FB from RD03 + the assembly map.

        The ONLY AI-generated artifact of the assembly stage. Guarded,
        audited, fence-stripped, then validated (incl. STRUCTURAL_BUG rule).
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        task_cfg = self.get_provider_for_task("scl_generation")
        _emit_provider_warning(task_cfg)  # G-02: output-ceiling risk, if any
        provider, model_name = task_cfg["provider"], task_cfg["model"]
        api_key = self._resolve_api_key(provider)
        if not api_key:
            return _attach_warnings({"ok": False,
                "msg": f"No API key for '{provider}' — add it in Settings."})
        from data_classification_guard import check_ai_send  # type: ignore
        gate = check_ai_send(self.root, provider, self.settings,
                             consent_confirmed=bool((consent or {}).get("confirmed")))
        if not gate.allowed:
            return _attach_warnings({"ok": False, "msg": f"[C4] {gate.reason}"})
        for w in self._pii_soft_warn(provider):  # §11 soft PII warning
            _warn(w, category="privacy")

        # S-1 / F-01: RAG safety check — must run before SCL generation
        # Non-blocking: rag_warnings are passed through to caller for UI surfacing.
        rag_warnings, rag_mode = self._rag_safety_check(
            "SCL sequence safety interlock E-stop F-block SIL"
        )

        # Inputs: RD03 table + device list from the assembly map
        from rd_draft_writer import find_rd_target  # type: ignore
        rd03 = find_rd_target(self.root / "metadata", "RD03")
        if not rd03.is_file():
            return _attach_warnings({"ok": False,
                "msg": "RD03 (Flowchart) not found — run pre-analysis or fill it first."})
        rd03_text = rd03.read_text(encoding="utf-8", errors="replace")

        # S-20 (B-G8): anonymize before sending to AI (required for INTERNAL).
        _anon_map_seq = self._anon_map_for_ai(gate)
        _req_anon_seq = bool(getattr(gate, "requires_anonymization", False))
        if _req_anon_seq or _anon_map_seq:
            rd03_text, _anon_err = _anonymize_or_block(
                rd03_text, _anon_map_seq, _req_anon_seq, "RD03 (sequence FB)")
            if _anon_err:
                return _attach_warnings({"ok": False, "msg": _anon_err})

        try:
            from program_assembler import assemble_program  # noqa: F401  # type: ignore
            from iec_tag_generator import parse_rd01_signals  # type: ignore
            from program_assembler import group_devices, load_contracts, _classify_device  # type: ignore
            devices, _loose = group_devices(parse_rd01_signals(self.root))
            contracts = load_contracts()
            device_lines = []
            for d in devices:
                stem = _classify_device(d)
                if stem in contracts:
                    _desc = d.description[:60]
                    if _req_anon_seq or _anon_map_seq:
                        _desc, _anon_err = _anonymize_or_block(
                            _desc, _anon_map_seq, _req_anon_seq,
                            f"device description {d.device_id}")
                        if _anon_err:
                            return _attach_warnings({"ok": False,
                                                     "msg": _anon_err})
                    device_lines.append(
                        f"{d.device_id} — {stem} — {_desc}")
            device_list = "\n".join(device_lines) or "(no mapped devices)"
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"Device map failed: {exc}"})

        prompt_doc = (FACTORY_ROOT / "04_AI_PROMPTS" / "code_gen"
                      / "PROMPT_CODE_GEN_SEQUENCE.md")
        doc = prompt_doc.read_text(encoding="utf-8", errors="replace")
        sys_m = _re_search_block(doc, "## 2. System Prompt")
        project = re.sub(r"[^A-Za-z0-9_]", "_", self.root.name)[:24]
        user_prompt = (
            f"Generate FB_Seq_{project} from this step sequence.\n\n"
            f"--- RD03 STEP SEQUENCE ---\n{rd03_text[:12000]}\n\n"
            f"--- DEVICES (from RD01 / assembly map) ---\n{device_list}\n\n"
            f"--- ADDITIONAL CONSTRAINTS ---\n"
            f"Block name MUST be FB_Seq_{project}. Use only listed devices."
        )
        try:
            _audit_log(self.root, "generate_sequence_fb", provider, model_name,
                       prompt_text=user_prompt[:2000],
                       prompt_id="assemble:sequence_fb",
                       full_prompt_text=user_prompt)
        except AuditLogError as ae:
            return _attach_warnings({"ok": False, "msg": f"[EU AI Act] {ae}"})

        try:
            from ai_client import AIClient  # type: ignore
            from workbench.core.ai_runner import _strip_code_fence  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model_name)
            response, _usage = client.chat(
                system=sys_m + _lang_directive(self._output_language()),
                user=user_prompt,
                max_tokens=65536)
            self._add_cost(_usage)
            scl = _strip_code_fence(response or "")
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"AI call failed: {exc}"})

        out_dir = self.root / "_output" / "scl"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"FB_Seq_{project}.scl"
        out_path.write_text(scl, encoding="utf-8")

        from scl_validator import validate_scl_file  # type: ignore
        vr = validate_scl_file(out_path)
        issues = [f"[{i.severity}] line {i.line}: {i.message}"
                  for i in vr.issues if i.severity == "error"]
        return _attach_warnings({
            "ok": vr.error_count == 0,
            "msg": (f"FB_Seq_{project}.scl generated — "
                    + ("validator clean (structural). Engineer review + TIA "
                       "compile still required."
                       if vr.error_count == 0 else
                       f"{vr.error_count} STRUCTURAL ERROR(S) — fix before use.")),
            "file": out_path.name,
            "errors": issues,
            "rag_warnings": rag_warnings,
            "rag_mode": rag_mode,
        })

    # ------------------------------------------------------------------
    # RD03 Flowchart — table-derived diagram + chat-based change requests
    # ------------------------------------------------------------------
    # Design rule: the Flow Steps TABLE is the single source of truth.
    # The mermaid diagram is always DERIVED deterministically from the
    # table (generate_mermaid) — never hand-edited, never AI-written.
    # The chat loop therefore asks the AI for a *table*, not a diagram.

    def _rd03_file(self) -> Path:
        from rd_draft_writer import find_rd_target  # type: ignore
        return find_rd_target(self.root / "metadata", "RD03")

    def rd03_get(self) -> dict:
        """Current RD03 for the Flowchart view: derived diagram + findings."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        rd03 = self._rd03_file()
        if not rd03.is_file():
            return _attach_warnings({"ok": False, "exists": False,
                "msg": "RD03 (Flowchart) not found — run pre-analysis or fill it first."})
        from workbench.core.rd03_flowchart import (  # type: ignore
            generate_mermaid, impact_check, parse_flow_steps, steps_to_md_table)
        text = rd03.read_text(encoding="utf-8", errors="replace")
        steps = parse_flow_steps(text)
        steps_json = [
            {"id": s.step_id, "name": s.step_name, "entry": s.entry_condition,
             "actions": s.actions, "exit": s.exit_condition,
             "next": s.next_step, "status": s.status}
            for s in steps
        ] if steps else []
        return _attach_warnings({
            "ok": True, "exists": True, "file": rd03.name,
            "step_count": len(steps),
            "steps": steps_json,
            "table": steps_to_md_table(steps) if steps else "",
            "mermaid": generate_mermaid(steps) if steps else "",
            "findings": impact_check(steps, self.root / "metadata") if steps else [],
        })

    def rd03_regen_mermaid(self) -> dict:
        """Regenerate RD03's mermaid block from its Flow Steps table and save.

        Deterministic (no AI). The previous file version is backed up to
        metadata/_history/ first.
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        rd03 = self._rd03_file()
        if not rd03.is_file():
            return _attach_warnings({"ok": False, "msg": "RD03 not found"})
        from workbench.core.rd03_flowchart import (  # type: ignore
            generate_mermaid, parse_flow_steps, replace_mermaid_block)
        text = rd03.read_text(encoding="utf-8", errors="replace")
        steps = parse_flow_steps(text)
        if not steps:
            return _attach_warnings({"ok": False,
                "msg": "No Flow Steps table found in RD03 — nothing to derive from."})
        mermaid = generate_mermaid(steps)
        # S-2 fix (anlamsal kardeş): audit BEFORE write; non-blocking on failure
        try:
            _audit_log(
                self.root,
                "rd03_regen_mermaid",
                "engineer",
                "deterministic",
                prompt_text=f"file={rd03.name}; steps_count={len(steps)}",
                prompt_id="flowchart:regen_mermaid",
            )
        except Exception as _al_exc:
            # S-2 (2026-07-10 audit): non-blocking stays, but the gap in the
            # audit chain must be SAID — a bare pass hid it entirely.
            _warn(f"Audit log entry failed (rd03_regen_mermaid): {_al_exc} — "
                  "the change went through, the audit chain has a gap.",
                  category="compliance")
        self._backup_to_history(rd03)
        rd03.write_text(replace_mermaid_block(text, mermaid), encoding="utf-8")
        return _attach_warnings({"ok": True, "mermaid": mermaid,
            "msg": f"Mermaid diagram regenerated from {len(steps)} steps (table is source of truth)."})

    def _backup_to_history(self, target: Path) -> None:
        """metadata/_history/<utc>_<name> — same convention as rd_draft_writer."""
        try:
            if target.is_file() and target.stat().st_size > 0:
                from datetime import datetime as _dt, timezone as _tz
                history = target.parent / "_history"
                history.mkdir(exist_ok=True)
                ts = _dt.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
                (history / f"{ts}_{target.name}").write_text(
                    target.read_text(encoding="utf-8", errors="replace"),
                    encoding="utf-8")
        except Exception:
            pass  # backup is best-effort; the apply itself reports its result

    _RD03_CHAT_SYSTEM = (
        "You are a PLC sequence engineer editing the Flow Steps table of an "
        "RD03 flowchart document (ISA-88 aligned step sequence).\n"
        "Rules:\n"
        "1. You will receive the CURRENT table and a change request. Apply the "
        "request and return the COMPLETE updated table — every row, not a diff.\n"
        "2. Output format: first a short explanation of what you changed and "
        "anything the engineer must verify, then the full markdown table with "
        "EXACTLY these 14 columns:\n"
        "| StepID | StepName | StepType | Description | EntryCondition | "
        "ExitCondition | Actions | NextStep | ErrorStep | TimerRef | ModeReq | "
        "ISA88Level | Notes | Status |\n"
        "3. StepID format S### (gaps of 10; suffix A/B for alternative "
        "branches). Exactly one Initial step with EntryCondition TRUE. Final "
        "steps use NextStep (end). Keep existing StepIDs stable when possible.\n"
        "4. NEVER invent safety logic (E-Stop, light curtain, F-blocks): if the "
        "request touches safety, add a Notes entry 'SAFETY — engineer review "
        "required' instead of implementing it.\n"
        "5. New steps get Status Draft. Do not delete steps unless asked.\n"
        "6. Do not output anything after the table."
    )

    def rd03_chat_propose(self, messages, consent: Optional[dict] = None) -> dict:
        """One round of the flowchart change-request chat.

        `messages` is the conversation so far:
        [{"role": "user"|"assistant", "content": "..."}]. The AI returns a
        complete replacement Flow Steps table; the mermaid preview and the
        impact findings are then derived DETERMINISTICALLY from that proposal
        (the AI never draws the diagram and never judges the impact).
        Nothing is written to disk — see rd03_chat_apply.
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        rd03 = self._rd03_file()
        if not rd03.is_file():
            return _attach_warnings({"ok": False, "msg": "RD03 not found"})
        from workbench.core.rd03_flowchart import (  # type: ignore
            generate_mermaid, impact_check, parse_flow_steps, steps_to_md_table)
        current_steps = parse_flow_steps(
            rd03.read_text(encoding="utf-8", errors="replace"))
        if not current_steps:
            return _attach_warnings({"ok": False,
                "msg": "RD03 has no Flow Steps table yet — create the table first "
                       "(pre-analysis or template)."})

        task_cfg = self.get_provider_for_task("default")
        _emit_provider_warning(task_cfg)  # G-02: output-ceiling risk, if any
        provider, model_name = task_cfg["provider"], task_cfg["model"]
        api_key = self._resolve_api_key(provider)
        if not api_key:
            return _attach_warnings({"ok": False,
                "msg": f"No API key for '{provider}' — add it in Settings."})
        from data_classification_guard import check_ai_send  # type: ignore
        gate = check_ai_send(self.root, provider, self.settings,
                             consent_confirmed=bool((consent or {}).get("confirmed")))
        if not gate.allowed:
            return _attach_warnings({"ok": False, "msg": f"[C4] {gate.reason}"})
        for w in self._pii_soft_warn(provider):  # §11 soft PII warning
            _warn(w, category="privacy")

        # S-20 (B-G8): anonymize before sending to AI (required for INTERNAL).
        _anon_map_rd03 = self._anon_map_for_ai(gate)
        _req_anon_rd03 = bool(getattr(gate, "requires_anonymization", False))
        _rd03_table_text = steps_to_md_table(current_steps)
        if _req_anon_rd03 or _anon_map_rd03:
            _rd03_table_text, _anon_err = _anonymize_or_block(
                _rd03_table_text, _anon_map_rd03, _req_anon_rd03,
                "RD03 steps table (chat)")
            if _anon_err:
                return _attach_warnings({"ok": False, "msg": _anon_err})

        convo = []
        for m in (messages or []):
            role = "Engineer" if (m.get("role") == "user") else "Assistant"
            _msg_content = (m.get('content') or '').strip()
            if _req_anon_rd03 or _anon_map_rd03:
                _msg_content, _anon_err = _anonymize_or_block(
                    _msg_content, _anon_map_rd03, _req_anon_rd03,
                    "chat message")
                if _anon_err:
                    return _attach_warnings({"ok": False, "msg": _anon_err})
            convo.append(f"{role}: {_msg_content}")
        user_prompt = (
            "--- CURRENT FLOW STEPS TABLE ---\n"
            + _rd03_table_text
            + "\n\n--- CONVERSATION (latest request last) ---\n"
            + "\n\n".join(convo[-12:])
        )
        try:
            _audit_log(self.root, "rd03_chat_propose", provider, model_name,
                       prompt_text=user_prompt[:2000],
                       prompt_id="flowchart:chat_propose",
                       full_prompt_text=user_prompt)
        except AuditLogError as ae:
            return _attach_warnings({"ok": False, "msg": f"[EU AI Act] {ae}"})

        try:
            from ai_client import AIClient  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model_name)
            response, _usage = client.chat(
                system=self._RD03_CHAT_SYSTEM + _lang_directive(self._output_language()),
                user=user_prompt,
                max_tokens=32768)
            self._add_cost(_usage)
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"AI call failed: {exc}"})

        reply = (response or "").strip()
        proposed_steps = parse_flow_steps(reply)
        if not proposed_steps:
            # Conversational turn (clarifying question etc.) — no table yet.
            return _attach_warnings({
                "ok": True, "has_proposal": False, "reply": reply,
                "msg": "No table in this reply — continue the conversation."})

        proposed_table = steps_to_md_table(proposed_steps)
        explanation = reply.split("|", 1)[0].strip()
        return _attach_warnings({
            "ok": True,
            "has_proposal": True,
            "reply": explanation,
            "proposed_table": proposed_table,
            "mermaid": generate_mermaid(proposed_steps),
            "findings": impact_check(proposed_steps, self.root / "metadata"),
            "step_count": len(proposed_steps),
            "label": "DRAFT_UNVERIFIED",
        })

    def rd03_chat_apply(self, proposed_table: str) -> dict:
        """Write an engineer-approved chat proposal into RD03.

        Swaps the Flow Steps table, regenerates the mermaid block from it,
        demotes frontmatter `status:` to DRAFT (the document must be
        re-reviewed before any approval gate) and backs the previous version
        up to metadata/_history/. The gate staleness warning will also flag
        the file if a gate had already been approved.
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        rd03 = self._rd03_file()
        if not rd03.is_file():
            return _attach_warnings({"ok": False, "msg": "RD03 not found"})
        from workbench.core.rd03_flowchart import (  # type: ignore
            demote_status_to_draft, generate_mermaid, impact_check,
            parse_flow_steps, replace_flow_steps_table, replace_mermaid_block,
            steps_to_md_table)
        steps = parse_flow_steps(proposed_table or "")
        if not steps:
            return _attach_warnings({"ok": False,
                "msg": "Proposal contains no parsable Flow Steps table — nothing applied."})
        hard = [f for f in impact_check(steps, self.root / "metadata")
                if f["severity"] == "error"]
        if hard:
            return _attach_warnings({"ok": False,
                "msg": "Proposal has structural errors — fix in chat before applying: "
                       + "; ".join(f["msg"] for f in hard[:5]),
                "findings": hard})

        text = rd03.read_text(encoding="utf-8", errors="replace")
        new_text = replace_flow_steps_table(text, steps_to_md_table(steps))
        new_text = replace_mermaid_block(new_text, generate_mermaid(steps))
        new_text = demote_status_to_draft(new_text)
        # S-2 fix: audit BEFORE write; fail-safe = log failure is non-blocking
        # (audit zinciri korunur ama dosya yazımı engellenemez — COMPLIANCE kuralı)
        try:
            _audit_log(
                self.root,
                "rd03_chat_apply",
                "engineer",
                "manual_apply",
                prompt_text=(
                    f"file={rd03.name}; steps_count={len(steps)}; "
                    f"proposed_table_len={len(proposed_table or '')}"
                ),
                prompt_id="flowchart:chat_apply",
            )
        except Exception as _al_exc:
            # S-2 (2026-07-10 audit): non-blocking stays, but the gap in the
            # audit chain must be SAID — a bare pass hid it entirely.
            _warn(f"Audit log entry failed (rd03_chat_apply): {_al_exc} — "
                  "the change went through, the audit chain has a gap.",
                  category="compliance")
        self._backup_to_history(rd03)
        rd03.write_text(new_text, encoding="utf-8")
        return _attach_warnings({
            "ok": True,
            "msg": (f"{rd03.name} updated ({len(steps)} steps). Status demoted "
                    "to DRAFT — engineer re-review required before the next "
                    "approval gate. Previous version saved to _history/."),
            "file": rd03.name,
        })

    # ------------------------------------------------------------------
    # M4 — TIA Openness direct path
    # ------------------------------------------------------------------

    def _get_bridge_manager(self):
        if getattr(self, "_bridge_mgr", None) is None:
            from bridges.bridge_manager import BridgeManager  # type: ignore
            self._bridge_mgr = BridgeManager(self.settings)
        return self._bridge_mgr

    def get_tia_bridge_status(self) -> dict:
        """Detection + settings snapshot for the Settings TIA card."""
        try:
            mgr = self._get_bridge_manager()
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"Bridge manager failed: {exc}"})
        bridges = []
        for bid in ("tia_v21", "tia_v20", "tia_v19"):
            b = mgr.get(bid)
            if b is None:
                err = next((v for k, v in mgr.load_errors().items() if bid in k), "")
                bridges.append({"id": bid, "status": "load_error", "error": err})
                continue
            try:
                st = b.detect()
            except Exception as exc:
                bridges.append({"id": bid, "status": "error", "error": str(exc)})
                continue
            bridges.append({
                "id": bid,
                "name": b.display_name,
                "status": st.value,
                "enabled": mgr.is_enabled(bid),
                "dll": str(getattr(getattr(b, "_install", None), "engineering_dll", "") or ""),
                "last_error": b.last_error,
            })
        try:
            import clr  # type: ignore  # noqa: F401
            pythonnet = True
        except Exception:
            pythonnet = False
        tia = dict(mgr.tia_settings())
        tia.setdefault("live_progress", True)
        tia.setdefault("fix_assist_mode", "hints")
        st_proj = self._project_state() if self.root else {}
        return _attach_warnings({
            "ok": True, "bridges": bridges, "pythonnet": pythonnet,
            "tia_settings": tia,
            "project": {
                "target_platform": st_proj.get("target_platform")
                                   or st_proj.get("platform") or "",
                "target_tia_version": st_proj.get("target_tia_version") or "",
                "plc_name": st_proj.get("plc_name") or tia.get("default_plc_name", "PLC_1"),
                "tia_project_path": st_proj.get("tia_project_path") or "",
                "classification": (st_proj.get("data_classification") or "").upper(),
                "output_language": (st_proj.get("output_language") or "EN").upper(),
            },
        })

    def set_tia_settings(self, d: dict) -> dict:
        """Persist TIA bridge settings. plcsim_only and skip_safety_blocks are
        hard safety defaults — NOT settable from the GUI on purpose."""
        try:
            mgr = self._get_bridge_manager()
            tia = mgr.tia_settings()
            for k in ("default_plc_name", "tia_v19_dll_path", "tia_v20_dll_path",
                      "tia_v21_dll_path", "auto_compile_after_import",
                      "plcsim_instance_name"):
                if k in (d or {}):
                    tia[k] = d[k]
            if "live_progress" in (d or {}):
                tia["live_progress"] = bool(d["live_progress"])
            if "fix_assist_mode" in (d or {}):
                mode = str(d["fix_assist_mode"])
                if mode not in _FIX_ASSIST_MODES:
                    return _attach_warnings({"ok": False,
                        "msg": f"Invalid fix_assist_mode '{mode}' — "
                               f"use one of {', '.join(_FIX_ASSIST_MODES)}."})
                tia["fix_assist_mode"] = mode
            for bid, en in ((d or {}).get("enabled") or {}).items():
                if bid in ("tia_v19", "tia_v20", "tia_v21"):
                    mgr.set_enabled(bid, bool(en))
            _save_settings(self.settings)
            return _attach_warnings({"ok": True})
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": str(exc)})

    def set_project_target(self, d: dict) -> dict:
        """Typed setter for TIA-related PROJECT_STATE fields (control plane)."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        allowed = {}
        if (d or {}).get("target_platform") in ("S7-1200", "S7-1500"):
            allowed["target_platform"] = d["target_platform"]
        if (d or {}).get("target_tia_version") in ("V19", "V20", "V21"):
            allowed["target_tia_version"] = d["target_tia_version"]
        if (d or {}).get("output_language") in ("TR", "EN", "DE"):
            allowed["output_language"] = d["output_language"]
        for k in ("plc_name", "tia_project_path"):
            if isinstance((d or {}).get(k), str):
                allowed[k] = d[k].strip()
        if not allowed:
            return _attach_warnings({"ok": False, "msg": "No valid fields to set"})
        try:
            self._update_state_fields(allowed)
            return _attach_warnings({"ok": True, "set": sorted(allowed)})
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": str(exc)})

    def _output_language(self) -> str:
        """Project output language (TR/EN/DE) from PROJECT_STATE — default EN."""
        st = self._project_state() if self.root else {}
        return (st.get("output_language") or st.get("output_lang") or "EN").upper()

    def get_output_language(self) -> dict:
        """Current analysis/output language + the supported set (for the UI)."""
        return {
            "ok": True,
            "language": self._output_language(),
            "supported": list(_LANG_NAMES.keys()),
            "names": dict(_LANG_NAMES),
        }

    def set_output_language(self, lang: str) -> dict:
        """Persist the project output language (TR/EN/DE). Generation prose
        (RD drafts, descriptions, comments, alarm/HMI texts) follows it via
        _lang_directive; tag names / SCL keywords stay English (GLOBAL_LANG_POLICY)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        code = (lang or "").strip().upper()
        if code not in _LANG_NAMES:
            return {"ok": False, "msg": f"Unsupported language: {lang!r} (use TR / EN / DE)"}
        self._update_state_fields({"output_language": code})
        return {"ok": True, "language": code}

    def _update_state_fields(self, fields: dict) -> None:
        state_file = self.root / "PROJECT_STATE.json"
        with self._state_lock:
            state = {}
            if state_file.is_file():
                try:
                    state = json.loads(state_file.read_text(encoding="utf-8"))
                except Exception:
                    state = {}
            state.update(fields)
            state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

    # ------------------------------------------------------------------
    # B-P12 / S-19 — TIA target version contract check
    # ------------------------------------------------------------------

    def _check_tia_version_contract(
        self,
        version: str,
        consent: Optional[dict],
    ) -> Optional[str]:
        """B-P12: Verify the target TIA version is listed in the project contract.

        Contract field (PROJECT_STATE.json):
            "allowed_tia_versions": ["V19", "V20"]   # explicit allowlist

        Rules (fail-closed):
        - Field absent / empty → "unlisted" (version not contractually approved).
        - Version not in list → blocked unless engineer gives explicit approval.
        - Approval: consent["version_approved"] == True AND consent["engineer"] set.
        - Completely unknown/empty version string → always blocked.

        Returns an error string on failure, None on pass.
        """
        version = (version or "").strip().upper()
        if not version:
            return (
                "TIA hedef versiyonu belirtilmemiş — gönderim durduruldu. "
                "Proje ayarlarından TIA versiyonunu seçin (örn. V19, V20, V21)."
            )

        st = self._project_state()
        allowed: list = st.get("allowed_tia_versions") or []

        if not allowed or version not in [v.strip().upper() for v in allowed]:
            # Version is unlisted in the contract (or no contract at all).
            engineer = ((consent or {}).get("engineer") or "").strip()
            approved = bool((consent or {}).get("version_approved"))
            if not approved or not engineer:
                listed_str = (
                    ", ".join(allowed) if allowed else "(kontrat listesi yok)"
                )
                return (
                    f"TIA versiyonu '{version}' kontratta listelenmemiş "
                    f"[kontrat: {listed_str}]. "
                    "Göndermek için: mühendis adı girin ve "
                    "'version_approved': true onayını ekleyin "
                    "(consent.version_approved + consent.engineer)."
                )
        return None

    def _tia_consent_gate(self, consent: Optional[dict], operation: str) -> Optional[str]:
        """Local-transfer classification gate. Returns an error message or None.

        RESTRICTED → always refused. CONFIDENTIAL → requires engineer consent
        (audited). PUBLIC/INTERNAL → allowed. Fail-closed on unknown."""
        st = self._project_state()
        cls = (st.get("data_classification") or "CONFIDENTIAL").strip().upper()
        if cls == "RESTRICTED":
            return "RESTRICTED project — TIA transfer is always blocked."
        if cls not in ("PUBLIC", "INTERNAL"):
            engineer = ((consent or {}).get("engineer") or "").strip()
            if not (consent or {}).get("confirmed") or not engineer:
                return (f"{cls or 'CONFIDENTIAL'} project — local TIA transfer "
                        "needs engineer consent (name + checkbox).")
            try:
                _audit_log(
                    self.root, f"tia_local_transfer_consent:{operation}",
                    "local", "tia_openness",
                    prompt_text=f"engineer={engineer}; classification={cls}",
                    prompt_id=f"tia:{operation}:consent",
                )
            except AuditLogError as ae:
                return f"[EU AI Act] Audit log failed: {ae}"
        return None

    def send_to_tia(self, opts: Optional[dict] = None) -> dict:
        """Import assembled sources into a TIA project + compile preflight.

        Background job (portal start takes minutes) — poll get_tia_send_status().
        opts: {version, project_path, plc_name, consent:{engineer,confirmed},
               download_plcsim: bool}
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        opts = opts or {}
        prev = getattr(self, "_tia_job", None)
        if prev and prev.get("running"):
            return _attach_warnings({"ok": False, "msg": "A TIA transfer is already running."})

        gate_err = self._tia_consent_gate(opts.get("consent"), "send_to_tia")
        if gate_err:
            return _attach_warnings({"ok": False, "msg": gate_err})

        out_dir = self.root / "_output" / "scl"
        files = (sorted(out_dir.glob("*.scl")) + sorted(out_dir.glob("*.db"))
                 if out_dir.is_dir() else [])
        if not files:
            return _attach_warnings({"ok": False,
                "msg": "_output/scl/ is empty — run Assemble Program first."})

        st = self._project_state()
        version = (opts.get("version") or st.get("target_tia_version") or "").upper()
        ap_path = (opts.get("project_path") or st.get("tia_project_path") or "").strip()
        if not ap_path:
            return _attach_warnings({"ok": False,
                "msg": "No TIA project path (.ap19/.ap20/.ap21) — set it in the TIA card."})
        ap = Path(ap_path)
        if not ap.is_file():
            return _attach_warnings({"ok": False, "msg": f"TIA project not found: {ap}"})
        if version not in ("V19", "V20", "V21"):
            # infer from the project file extension (.ap19/.ap20/.ap21)
            version = {".ap21": "V21", ".ap20": "V20"}.get(ap.suffix.lower(), "V19")
        # B-P12 / S-19 — contract version gate (fail-closed)
        ver_err = self._check_tia_version_contract(version, opts.get("consent"))
        if ver_err:
            return _attach_warnings({"ok": False, "msg": ver_err,
                                     "version_check_failed": True})
        bid = f"tia_{version.lower()}"
        mgr = self._get_bridge_manager()
        bridge = mgr.get(bid)
        if bridge is None:
            return _attach_warnings({"ok": False,
                "msg": f"Bridge {bid} could not load — is pythonnet installed?"})
        if not mgr.is_enabled(bid):
            return _attach_warnings({"ok": False,
                "msg": f"{bridge.display_name} is disabled — enable it in Settings → TIA Portal."})

        # S-1 (audit M-01): last gate before code leaves the factory — the
        # transfer into a real TIA project (and optional PLCSIM download)
        # must not run with an unreviewed safety analysis. Placed after the
        # cheap input validations so their messages stay unchanged.
        blocked = self._rd05_code_gen_gate("Send to TIA")
        if blocked:
            return blocked

        plc_name = (opts.get("plc_name") or st.get("plc_name")
                    or mgr.tia_settings().get("default_plc_name", "PLC_1"))
        download = bool(opts.get("download_plcsim"))
        import_tags = opts.get("import_tags", True)

        step_plan = [("prepare_tags", "Tag table XML"),
                     ("portal", "TIA Portal"),
                     ("open_project", "Open project"),
                     ("find_plc", "Find PLC"),
                     ("import_tags", "Import tag table"),
                     ("import_scl", "Import SCL sources"),
                     ("compile", "Compile"),
                     ("save", "Save project")]
        if download:
            step_plan.append(("download", "Download to PLCSIM Advanced"))
        job: dict = {"running": True, "done": False, "ok": None, "msg": "",
                     "lines": [], "details": [], "bridge": bid,
                     "operation": "download" if download else "import_compile",
                     "steps": [{"id": sid, "label": lbl, "status": "pending",
                                "info": ""} for sid, lbl in step_plan],
                     "error_analysis": [], "compile_errors": [],
                     "fix_proposal": None,
                     "started_at": time.time()}
        self._tia_job = job
        bridge._on_status = lambda msg, level: job["lines"].append(f"[{level}] {msg}")
        bridge._on_step = lambda sid, stt, info="": _job_step(job, sid, stt, info)

        def _worker():
            try:
                tag_xml = None
                if import_tags:
                    _job_step(job, "prepare_tags", "running")
                    tag_xml, tag_warns = self._prepare_tag_xml()
                    for w in tag_warns:
                        job["lines"].append(f"[info] {w}")
                    _job_step(job, "prepare_tags",
                              "ok" if tag_xml else "warn",
                              "" if tag_xml else "skipped — see log")
                else:
                    _job_step(job, "prepare_tags", "skip", "disabled")
                if download:
                    r = bridge.import_compile_and_download(ap, files, plc_name=plc_name,
                                                           tag_xml=tag_xml)
                else:
                    r = bridge.import_scl_to_project(ap, files, plc_name=plc_name,
                                                     do_compile=True, tag_xml=tag_xml)
                job["details"] = list(r.details) + [f"⚠ {w}" for w in r.warnings]
                job["compile_errors"] = list(getattr(r, "compile_errors", []))
                if r.success:
                    self._record_compile_success(files, version)
                else:
                    # Analyze BEFORE marking done — pollers read the job the
                    # moment done flips, so everything must be in place.
                    self._analyze_tia_errors(job, opts)
                job.update(running=False, done=True, ok=r.success, msg=r.message)
            except Exception as exc:
                job.update(running=False, done=True, ok=False, msg=str(exc))
            finally:
                # A step still "running" after the job ended means it broke
                # mid-flight — never leave it spinning in the GUI.
                if not job["ok"]:
                    for s in job["steps"]:
                        if s["status"] == "running":
                            s["status"] = "fail"

        threading.Thread(target=_worker, daemon=True).start()
        return _attach_warnings({"ok": True, "started": True,
                                 "msg": f"TIA {version} transfer started ({len(files)} files)."})

    def _prepare_tag_xml(self) -> "tuple[Optional[Path], list[str]]":
        """Generate a fresh PlcTagTable XML from RD01/HW03 for the TIA send.

        Returns (xml_path | None, messages). Never raises — the IO tag table
        is an auxiliary payload of send_to_tia; the SCL import proceeds
        without it, and every skip reason lands in the job log.
        """
        try:
            from tia_tag_export import run_export  # type: ignore
            # name_source="rd01": the assembled OB1 references the raw RD01
            # signal names, so the tag table must carry exactly those (the
            # IEC-prefixed HW03 names left 11 "Tag not defined" compile
            # errors in the 2026-06-10 live test).
            res = run_export(
                self.root,
                output_dir=self.root / "_output" / "tia_import",
                write_xlsx=False,
                timestamped=False,
                name_source="rd01",
            )
            msgs = list(res.warnings)
            if not res.ok:
                msgs.insert(0, "Tag table XML not generated — IO tags will "
                               "not be sent to TIA (RD01/HW03 missing?).")
                return None, msgs
            msgs.insert(0, f"Tag table XML: {res.xml_path.name} "
                           f"({len(res.tags)} tags)")
            return res.xml_path, msgs
        except Exception as exc:
            return None, [f"Tag table export failed — IO tags will not be "
                          f"sent to TIA: {exc}"]

    def _record_compile_success(self, files: list, version: str) -> None:
        """Compile preflight passed → honest label upgrade evidence.

        Writes REPORTS/gate_results/tia_compile.json and sets
        last_validation scope='compile' in PROJECT_STATE so the W-A5
        'accept structural-only' checkbox is no longer needed at the gate."""
        try:
            from datetime import datetime, timezone as _tz
            gate_dir = self.root / "REPORTS" / "gate_results"
            gate_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "label": "AUTO_VERIFIED_compile | PENDING_PLCSIM_VERIFY",
                "tia_version": version,
                "files": [f.name for f in files],
                "timestamp": datetime.now(_tz.utc).isoformat(timespec="seconds"),
            }
            (gate_dir / "tia_compile.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8")
            self._update_state_fields({
                "last_validation": {"errors": 0, "scope": "compile"}})
        except Exception as exc:
            _warn(f"compile evidence could not be recorded: {exc}", category="tia")

    def get_tia_send_status(self) -> dict:
        job = getattr(self, "_tia_job", None)
        if not job:
            return _attach_warnings({"ok": True, "exists": False})
        # S-9 (kardeş): timeout guard — 30-minute ceiling on TIA send jobs.
        # Fail-safe: missing started_at → fallback time.time() → diff ~0 → no timeout.
        if (
            job.get("running")
            and time.time() - job.get("started_at", time.time()) > 1800
        ):
            job["running"] = False
            job["done"] = True
            job["ok"] = False
            job["msg"] = "TIA send timeout (>30 min) — job was forcibly stopped"
            for s in job.get("steps", []):
                if s.get("status") == "running":
                    s["status"] = "fail"
        return _attach_warnings({
            "ok": True, "exists": True, "running": job["running"],
            "done": job["done"], "succeeded": job["ok"], "msg": job["msg"],
            "operation": job["operation"], "bridge": job["bridge"],
            "details": list(job["details"]),
            "log_tail": "\n".join(job["lines"][-40:]),
            "steps": [dict(s) for s in job.get("steps", [])],
            "error_analysis": list(job.get("error_analysis", [])),
            "fix_proposal": job.get("fix_proposal"),
            "fix_assist_mode": self._tia_assist_mode(),
        })

    # ------------------------------------------------------------------
    # Compile-error assistance (classification hints + FB_Seq fix proposal)
    # ------------------------------------------------------------------

    def _tia_assist_mode(self) -> str:
        try:
            mode = self._get_bridge_manager().tia_settings() \
                       .get("fix_assist_mode", "hints")
        except Exception:
            return "hints"
        return mode if mode in _FIX_ASSIST_MODES else "hints"

    def _analyze_tia_errors(self, job: dict, opts: dict) -> None:
        """Classify compile errors into job['error_analysis'] and, in
        auto_propose mode, pre-generate the FB_Seq fix proposal.

        Runs inside the send_to_tia worker thread; never raises — assistance
        must not break the transfer result."""
        try:
            mode = self._tia_assist_mode()
            if mode == "off" or not job.get("compile_errors"):
                return
            from tia_fix_assist import classify  # type: ignore
            job["error_analysis"] = classify(
                job["compile_errors"],
                kb_blocks_dir=FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "blocks")
            if mode != "auto_propose":
                return
            if not any(g["proposable"] for g in job["error_analysis"]):
                return
            # Auto mode never escalates consent: the modal's local-transfer
            # consent does NOT cover AI egress, so the gate is asked without
            # consent; if it refuses (e.g. CONFIDENTIAL + cloud provider),
            # fall back to the on-demand button (a loud note, not an error).
            r = self.tia_fix_propose({"consent": None})
            if r.get("ok"):
                job["fix_proposal"] = r.get("proposal")
            else:
                job["lines"].append(
                    f"[info] AI fix not auto-proposed: {r.get('msg','')} "
                    "(use the Propose fix button)")
        except Exception as exc:
            job["lines"].append(f"[warn] error analysis failed: {exc}")

    def tia_fix_propose(self, opts: Optional[dict] = None) -> dict:
        """AI fix PROPOSAL for compile errors in the AI-generated sequence FB.

        Hard limits (the project's safety rails):
        - target is ONLY _output/scl/FB_Seq_*.scl — library blocks (SHA-256
          verified) and assembler output are never proposable;
        - the proposal must pass scl_validator before it is shown;
        - nothing is written here — tia_fix_apply() needs engineer approval.
        """
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        mode = self._tia_assist_mode()
        if mode not in ("suggest", "auto_propose"):
            return _attach_warnings({"ok": False,
                "msg": f"AI fix proposals are disabled (mode: {mode}) — "
                       "enable them in Settings → TIA Portal."})
        job = getattr(self, "_tia_job", None) or {}
        errors = list(job.get("compile_errors") or [])

        from tia_fix_assist import (  # type: ignore
            classify_error, library_block_names, build_fix_prompt, make_diff,
            CATEGORY_AI)
        lib_names = library_block_names(
            FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "blocks")
        ai_errors = [e for e in errors
                     if classify_error(e.get("block", ""), e.get("text", ""),
                                       lib_names) == CATEGORY_AI]
        if not ai_errors:
            return _attach_warnings({"ok": False,
                "msg": "No compile errors in an AI-generated FB_Seq block — "
                       "nothing to propose."})
        block = (opts or {}).get("block") or ai_errors[0]["block"]
        # HARD GUARD: the one AI-writable file. Resolve + containment check
        # so a crafted block name can never point outside _output/scl.
        if not str(block).startswith("FB_Seq"):
            return _attach_warnings({"ok": False,
                "msg": f"'{block}' is not an AI-generated sequence FB — "
                       "fix proposals are limited to FB_Seq_* by design."})
        scl_dir = (self.root / "_output" / "scl").resolve()
        target = (scl_dir / f"{block}.scl").resolve()
        if target.parent != scl_dir or not target.is_file():
            return _attach_warnings({"ok": False,
                "msg": f"Source not found: _output/scl/{block}.scl"})

        consent = (opts or {}).get("consent")
        task_cfg = self.get_provider_for_task("scl_generation")
        _emit_provider_warning(task_cfg)  # G-02: output-ceiling risk, if any
        provider, model_name = task_cfg["provider"], task_cfg["model"]
        api_key = self._resolve_api_key(provider)
        if not api_key:
            return _attach_warnings({"ok": False,
                "msg": f"No API key for '{provider}' — add it in Settings."})
        from data_classification_guard import check_ai_send  # type: ignore
        gate = check_ai_send(self.root, provider, self.settings,
                             consent_confirmed=bool((consent or {}).get("confirmed")))
        if not gate.allowed:
            return _attach_warnings({"ok": False, "msg": f"[C4] {gate.reason}"})
        for w in self._pii_soft_warn(provider):  # §11 soft PII warning
            _warn(w, category="privacy")

        old_text = target.read_text(encoding="utf-8", errors="replace")

        # S-20 (B-G8): anonymize SCL source before sending to AI (INTERNAL required).
        _anon_map_fix = self._anon_map_for_ai(gate)
        _req_anon_fix = bool(getattr(gate, "requires_anonymization", False))
        if _req_anon_fix or _anon_map_fix:
            old_text, _anon_err = _anonymize_or_block(
                old_text, _anon_map_fix, _req_anon_fix, "SCL source (fix)")
            if _anon_err:
                return _attach_warnings({"ok": False, "msg": _anon_err})

        block_errors = [e for e in ai_errors if e["block"] == block] or ai_errors
        sys_m, user_prompt = build_fix_prompt(old_text, block_errors)
        try:
            _audit_log(self.root, "tia_fix_propose", provider, model_name,
                       prompt_text=user_prompt[:2000],
                       prompt_id="tia_fix:propose",
                       full_prompt_text=user_prompt)
        except AuditLogError as ae:
            return _attach_warnings({"ok": False, "msg": f"[EU AI Act] {ae}"})

        try:
            from ai_client import AIClient  # type: ignore
            from workbench.core.ai_runner import _strip_code_fence  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model_name)
            response, _usage = client.chat(system=sys_m, user=user_prompt,
                                           max_tokens=16384)
            self._add_cost(_usage)
            new_text = _strip_code_fence(response or "").strip() + "\n"
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"AI call failed: {exc}"})

        from scl_validator import validate_scl  # type: ignore
        vr = validate_scl(new_text, target)
        if vr.error_count > 0:
            issues = [f"line {i.line}: {i.message}"
                      for i in vr.issues if i.severity == "error"][:5]
            return _attach_warnings({"ok": False,
                "msg": ("AI proposal rejected — it fails the structural "
                        "validator: " + "; ".join(issues))})
        if new_text.strip() == old_text.strip():
            return _attach_warnings({"ok": False,
                "msg": "AI returned the source unchanged — no proposal."})

        proposal = {
            "block": block,
            "file": target.name,
            "diff": make_diff(old_text, new_text, target.name),
            "errors_addressed": [e["text"] for e in block_errors][:10],
            "provider": provider,
            "model": model_name,
        }
        self._tia_fix_proposal = {**proposal,
                                  "old_text": old_text, "new_text": new_text,
                                  "path": target}
        return _attach_warnings({
            "ok": True, "proposal": proposal,
            "msg": (f"Fix proposed for {target.name} — review the diff; "
                    "nothing is written until an engineer approves."),
        })

    def tia_fix_apply(self, approval: Optional[dict] = None) -> dict:
        """Write the approved FB_Seq fix. Engineer name + checkbox required;
        the old file is backed up to _output/scl/_history/ and the approval
        is recorded in AI_DECISION_LOG. Re-send stays MANUAL by design."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg": "No project open"})
        prop = getattr(self, "_tia_fix_proposal", None)
        if not prop:
            return _attach_warnings({"ok": False,
                "msg": "No pending fix proposal — run Propose fix first."})
        engineer = ((approval or {}).get("engineer") or "").strip()
        if not (approval or {}).get("confirmed") or not engineer:
            return _attach_warnings({"ok": False,
                "msg": "Engineer approval required (name + checkbox) before "
                       "the fix is written."})
        target: Path = prop["path"]
        from scl_validator import validate_scl  # type: ignore
        vr = validate_scl(prop["new_text"], target)
        if vr.error_count > 0:
            return _attach_warnings({"ok": False,
                "msg": "Proposal no longer passes the validator — discarded."})
        try:
            _audit_log(self.root, "tia_fix_apply", prop["provider"],
                       prop["model"],
                       prompt_text=f"engineer={engineer}; file={target.name}",
                       prompt_id="tia_fix:apply")
        except AuditLogError as ae:
            return _attach_warnings({"ok": False, "msg": f"[EU AI Act] {ae}"})
        try:
            from datetime import datetime
            hist = target.parent / "_history"
            hist.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            (hist / f"{stamp}_{target.name}").write_text(
                prop["old_text"], encoding="utf-8")
            target.write_text(prop["new_text"], encoding="utf-8")
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": f"Apply failed: {exc}"})
        self._tia_fix_proposal = None
        job = getattr(self, "_tia_job", None)
        if job:
            job["fix_proposal"] = None
        return _attach_warnings({
            "ok": True,
            "msg": (f"Fix applied to {target.name} (backup in "
                    "_output/scl/_history/). Re-run Import + Compile to "
                    "verify. NOTE: Generate SCL would overwrite this fix."),
        })

    def tia_fix_discard(self) -> dict:
        self._tia_fix_proposal = None
        job = getattr(self, "_tia_job", None)
        if job:
            job["fix_proposal"] = None
        return _attach_warnings({"ok": True, "msg": "Proposal discarded."})

    # ------------------------------------------------------------------
    # Prompt Workspace (M4)
    # ------------------------------------------------------------------

    def get_file_context(self, file_path: str) -> dict:
        """Return context-aware actions + prompts for the selected file."""
        from pathlib import Path as _P
        fp = _P(file_path) if file_path else None
        default_actions = [
            {"id": "analyze",        "label": "Analyze Project",  "icon": "sparkles",  "hint": "", "primary": True},
            {"id": "extract_io",     "label": "Extract IO List",  "icon": "table",     "hint": ""},
            {"id": "assemble_program", "label": "Assemble Program", "icon": "package", "hint": ""},
            {"id": "generate_scl",   "label": "Generate SCL",     "icon": "play",      "hint": ""},
            {"id": "validate",       "label": "Validate",         "icon": "check",     "hint": ""},
            {"id": "show_standards", "label": "Show Standards",   "icon": "file-text", "hint": ""},
            {"id": "export_tia",     "label": "Export TIA",       "icon": "upload",    "hint": ""},
        ]
        try:
            from workbench.core.file_actions import actions_for  # type: ignore
            from workbench.core.factory_reader import (  # type: ignore
                list_prompts, filter_prompts_by_context, get_context_category,
            )
            _ICON = {
                "validate_io": "check", "validate_rd": "check",
                "send_to_tia": "upload", "gen_unit_test": "flask",
                "gen_fat": "file-text", "parse_source": "search",
                "open_in_excel": "table",
            }
            raw_acts = actions_for(fp)
            # scope tells the rail whether these buttons act on the SELECTED
            # FILE or on the WHOLE PROJECT (2026-07-06 user audit: the rail
            # never said which, so "Analyze Project with an FB open" was
            # ambiguous — it always meant the whole project).
            scope = "file" if raw_acts else "project"
            actions = [
                {"id": aid, "label": label.split(" ", 1)[-1] if label[:1] in "📊✅🔌🧪📋🔍📈" else label,
                 "icon": _ICON.get(aid, "play"), "hint": "", "primary": i == 0}
                for i, (label, aid) in enumerate(raw_acts)
            ] or default_actions

            st = self._project_state()
            gate     = max(1, min(7, int(st.get("gate", st.get("current_gate", 1)) or 1)))
            platform = st.get("target_platform") or st.get("platform") or ""
            ptype    = (st.get("project_type") or "").lower()
            category = get_context_category(fp, gate)
            raw_prompts = list_prompts(category)
            filtered = filter_prompts_by_context(raw_prompts, fp, gate, platform, category, ptype)
            prompts = [
                {"title": p.get("title") or p.get("name", ""), "gate": gate,
                 "path": str(p.get("path", ""))}
                for p in filtered[:8]
            ]
        except Exception:
            actions = default_actions
            prompts = []
            scope = "project"
        return _attach_warnings({"actions": actions, "prompts": prompts,
                                 "scope": scope})

    def list_prompts_by_category(self, category: str) -> list[dict]:
        """List available prompts for a category."""
        try:
            from workbench.core.factory_reader import list_prompts  # type: ignore
            items = list_prompts(category or "analyze")
            return [{"name": p["name"], "path": str(p["path"]), "title": p.get("title", p["name"])} for p in items]
        except Exception as e:
            return []

    def get_prompt_text(self, path: str) -> dict:
        """Read full text of a prompt file by absolute path."""
        try:
            p = Path(path)
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace")
                return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "text": "", "msg": str(e)}
        return {"ok": False, "text": "", "msg": "Not found"}

    def copy_prompt(self, name: str) -> dict:
        """Full text of a prompt by its title/stem (right-rail Prompt Library).

        The GUI copies the returned text to the clipboard. This endpoint was
        referenced by the frontend but never existed — the demo fallback
        faked a "copied" success with no content (UX audit 2026-06-10)."""
        stem = (name or "").strip()
        if not stem:
            return _attach_warnings({"ok": False, "msg": "No prompt name"})
        pdir = FACTORY_ROOT / "04_AI_PROMPTS"
        try:
            match = next((p for p in sorted(pdir.glob("**/*.md"))
                          if p.stem == stem), None)
        except Exception:
            match = None
        if match is None:
            return _attach_warnings({"ok": False,
                                     "msg": f"Prompt not found: {stem}"})
        try:
            text = match.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return _attach_warnings({"ok": False, "msg": str(exc)})
        return _attach_warnings({
            "ok": True, "name": stem, "text": text, "preview": text[:800],
            "msg": f"{match.name} copied to clipboard",
        })

    def save_user_prompt(self, category: str, title: str, body: str, gate: int = 1) -> dict:
        """Save a user-written prompt to the prompts library."""
        try:
            from workbench.core.prompt_writer import save_user_prompt  # type: ignore
            path = save_user_prompt(category=category, title=title, body=body, gate=int(gate))
            return {"ok": True, "path": str(path), "msg": f"Saved to {path.name}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def normalize_prompt(self, text: str, category: str) -> dict:
        """Normalize a prompt using AIClient."""
        cfg      = self.settings
        provider = cfg.get("ai_provider", "anthropic")
        model    = cfg.get("ai_model", "claude-sonnet-4-6")
        api_key  = self._resolve_api_key(provider)  # C-A2: keystore on-demand
        if not api_key:
            return {"ok": False, "normalized": "", "msg": "No API key — add one in Settings", "mode": "api"}
        # C-A4: enforce data-classification guard on ALL AIClient call sites.
        allowed, reason = self._ai_send_allowed(provider)
        if not allowed:
            return {"ok": False, "normalized": "", "msg": reason,
                    "mode": "api", "blocked": "classification"}
        pii_warns = self._pii_soft_warn(provider)  # §11 soft PII warning
        # C-1 fix: audit log before AI call (fail-closed)
        try:
            _audit_log(self.root, "normalize_prompt",
                       provider, model,
                       prompt_text=text,
                       prompt_id="normalize_prompt")
        except AuditLogError as _ae:
            return {"ok": False, "normalized": "", "msg": str(_ae), "blocked": "audit_log"}
        try:
            from ai_client import AIClient  # type: ignore
            from workbench.core.prompt_normalizer import normalize_prompt  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model or None)
            normalized_text = normalize_prompt(raw=text, category=category or "analyze", ai_client=client)
            # R-C-2 fix: output audit log — fail-warn (visible warning, no blocking)
            _audit_out_warn: str = ""
            try:
                _audit_log(self.root, "normalize_prompt [output]",
                           provider, model,
                           output_text=normalized_text,
                           prompt_id="normalize_prompt:output")
            except AuditLogError as _out_exc:
                _audit_out_warn = "output_hash_failed"
                import logging as _log
                _log.warning("[EU AI Act] normalize_prompt output audit hash could not be written — %s", _out_exc)
            result: dict = {"ok": True, "normalized": normalized_text, "mode": "api"}
            if pii_warns:
                result["_pii_warnings"] = pii_warns
            if _audit_out_warn:
                result["_audit_warn"] = _audit_out_warn
            return result
        except Exception as e:
            return {"ok": False, "normalized": "", "msg": str(e), "mode": "api"}

    def adapt_prompt(self, text: str) -> dict:
        """Adapt a prompt to the current project context."""
        try:
            from workbench.core.prompt_adapter import adapt  # type: ignore
            result = adapt(prompt=text, project_root=self.root)
            return {"ok": True, "warnings": result.get("warnings", []), "suggestions": result.get("suggestions", []), "enhanced": result.get("enhanced", text)}
        except Exception as e:
            return {"ok": False, "warnings": [], "suggestions": [], "enhanced": text, "msg": str(e)}

    def ingest_device(self, pdf_path: str) -> dict:
        """Extract device spec from a datasheet PDF, save MD to 09_HARDWARE_LIBRARY,
        and update the RAG index if it already exists.

        pdf_path must be an absolute path to a PDF selected by the user via the
        native file dialog — never constructed by the frontend from user input.
        Source field is always set to the document filename (anonymized; local path
        is NOT stored in the generated MD).
        """
        import re as _re
        import sys as _sys

        # ── 1. Validate input ──────────────────────────────────────────────
        pdf = Path(pdf_path) if pdf_path else None
        if not pdf or not pdf.is_absolute() or pdf.suffix.lower() != ".pdf":
            return {"ok": False, "msg": "Invalid PDF path — must be an absolute .pdf file path"}
        if not pdf.exists():
            return {"ok": False, "msg": f"File not found: {pdf.name}"}

        # ── 2. Extract PDF text ────────────────────────────────────────────
        try:
            import pdfplumber  # type: ignore
        except ImportError:
            return {"ok": False, "msg": "pdfplumber not installed: pip install pdfplumber"}
        try:
            with pdfplumber.open(str(pdf)) as _pdf:
                pages_text = [p.extract_text() or "" for p in _pdf.pages]
            pdf_text = "\n\n".join(pages_text).strip()
        except Exception as exc:
            return {"ok": False, "msg": f"PDF read error: {exc}"}
        if not pdf_text or len(pdf_text) < 50:
            return {"ok": False, "msg": "PDF has no readable text layer. OCR-based extraction is not supported here — use AI chat with manual upload."}

        # ── 3. Load AI prompt ──────────────────────────────────────────────
        prompt_file = FACTORY_ROOT / "09_HARDWARE_LIBRARY" / "_PROMPT_DEVICE_SPEC_EXTRACT.md"
        if not prompt_file.exists():
            return {"ok": False, "msg": f"Prompt file missing: {prompt_file.name}"}
        prompt_md = prompt_file.read_text(encoding="utf-8")

        # Extract SYSTEM PROMPT section (between "## SYSTEM PROMPT" and the trailing "---")
        sys_match = _re.search(
            r"##\s+SYSTEM PROMPT.*?\n(.*?)\n---\s*\n##\s+USER MESSAGE",
            prompt_md, _re.DOTALL,
        )
        system_prompt = sys_match.group(1).strip() if sys_match else prompt_md

        user_message = (
            "From the device document below, produce an AUTOMATION_FACTORY device MD.\n"
            "Use the template above and apply all the rules.\n\n"
            f"{pdf_text[:12000]}"  # cap to ~12 k chars to stay within token budget
        )

        # ── 4. AI call ─────────────────────────────────────────────────────
        cfg      = self.settings
        provider = cfg.get("ai_provider", "anthropic")
        model    = cfg.get("ai_model", "claude-sonnet-4-6")
        api_key  = self._resolve_api_key(provider)
        if not api_key:
            return {"ok": False, "msg": "No API key configured. Add one in Settings."}

        # S-1 / F-03: data-classification guard — fail-closed before AI call.
        # ingest_device uses FACTORY_ROOT (public datasheet context, not customer
        # project), so self.root may be None here.  Fall back to FACTORY_ROOT so
        # the guard always reads a valid root.  FACTORY_ROOT ships a PUBLIC
        # PROJECT_STATE.json (the framework template repo is public), so the guard
        # resolves to PUBLIC and allows the call.  Without that file the guard's
        # fail-closed default (CONFIDENTIAL) would wrongly block every datasheet
        # ingest when no project is open — see test_factory_root_is_public.
        _guard_root = self.root if self.root else FACTORY_ROOT
        from data_classification_guard import check_ai_send  # type: ignore
        _ingest_gate = check_ai_send(_guard_root, provider, self.settings)
        if not _ingest_gate.allowed:
            return _attach_warnings({"ok": False, "msg": f"[C4] {_ingest_gate.reason}"})

        pii_warns = self._pii_soft_warn(provider)

        # Audit log — use FACTORY_ROOT (public datasheet, not customer project)
        try:
            _audit_log(
                FACTORY_ROOT, "ingest_device",
                provider, model,
                prompt_text=system_prompt[:500],
                full_prompt_text=system_prompt,
                prompt_id="ingest_device",
            )
        except AuditLogError as ae:
            return {"ok": False, "msg": str(ae)}

        try:
            from ai_client import AIClient  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model or None)
            device_md, _usage = client.chat(system=system_prompt, user=user_message, max_tokens=4096)
        except Exception as exc:
            return {"ok": False, "msg": f"AI error: {exc}"}

        if not device_md or len(device_md.strip()) < 100:
            return {"ok": False, "msg": "AI returned empty output — check the PDF content."}

        # Output audit
        try:
            _audit_log(
                FACTORY_ROOT, "ingest_device [output]",
                provider, model,
                output_text=device_md[:500],
                prompt_id="ingest_device:output",
            )
        except AuditLogError as _out_ae:
            import logging as _log_iae
            _log_iae.warning("[EU AI Act] ingest_device output audit hash could not be written — %s", _out_ae)

        # ── 5. Parse device_id / category / vendor / library_path ─────────
        _YAML_RE = _re.compile(r"```ya?ml\n(.*?)```", _re.DOTALL)
        meta_block = _YAML_RE.search(device_md)
        device_meta: dict = {}
        if meta_block:
            for line in meta_block.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    device_meta[k.strip()] = v.strip().strip('"').strip("'")

        device_id    = device_meta.get("device_id", "").strip()
        category     = device_meta.get("category", "").strip()
        vendor_raw   = device_meta.get("vendor", "").strip()
        library_path = device_meta.get("library_path", "").strip()

        if not device_id or not category:
            return {"ok": False, "msg": "AI output missing device_id or category — cannot save. Retry or paste the output manually."}

        # Sanitise vendor name for use as directory (letters, digits, hyphens)
        vendor_dir = _re.sub(r"[^\w\-]", "_", vendor_raw or "Unknown")[:40]

        # Derive save path from library_path (AI-supplied) or fallback
        if library_path:
            # Security: must be relative, no "..", must start with category or vendor
            lp = Path(library_path)
            if lp.is_absolute() or ".." in lp.parts:
                return {"ok": False, "msg": f"AI returned unsafe library_path: {library_path}"}
            save_path = FACTORY_ROOT / "09_HARDWARE_LIBRARY" / lp
        else:
            stem = _re.sub(r"[^\w\-]", "_", device_id)[:60]
            save_path = FACTORY_ROOT / "09_HARDWARE_LIBRARY" / category / vendor_dir / f"{stem}.md"

        # Ensure save path stays inside 09_HARDWARE_LIBRARY
        hw_root = FACTORY_ROOT / "09_HARDWARE_LIBRARY"
        try:
            save_path.resolve().relative_to(hw_root.resolve())
        except ValueError:
            return {"ok": False, "msg": "Computed save path escapes 09_HARDWARE_LIBRARY — save refused."}

        # ── 6. Anonymize: remove local PDF path from AI output ────────────
        # The local file path must never land in the committed MD.
        device_md_clean = device_md.replace(str(pdf), "[PDF_PATH_REDACTED]")
        device_md_clean = device_md_clean.replace(str(pdf.name), pdf.name)  # keep basename

        # ── 7. Save ────────────────────────────────────────────────────────
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(device_md_clean, encoding="utf-8")

        rel_path = str(save_path.relative_to(FACTORY_ROOT)).replace("\\", "/")

        # ── 8. Update RAG index (best-effort — skip if index not built) ────
        rag_warn: str = ""
        index_dir = FACTORY_ROOT / "_rag_index"
        if (index_dir / "metadata.json").exists() and (index_dir / "embeddings.npy").exists():
            try:
                _rag_scripts = str(FACTORY_ROOT / "05_SCRIPTS")
                if _rag_scripts not in _sys.path:
                    _sys.path.insert(0, _rag_scripts)
                from rag.ingest import parse_hw_file, _embed_texts  # type: ignore
                import json as _json
                import numpy as _np
                new_records = parse_hw_file(save_path)
                if new_records:
                    openai_key = (cfg.get("api_keys") or {}).get("openai", "")
                    if not openai_key:
                        import os as _os
                        openai_key = _os.environ.get("OPENAI_API_KEY", "")
                    if openai_key:
                        meta = _json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
                        embs = _np.load(str(index_dir / "embeddings.npy"))
                        new_ids = {r["entry_id"] for r in new_records}
                        keep = [(m, e) for m, e in zip(meta, embs) if m["entry_id"] not in new_ids]
                        if keep:
                            meta_k, embs_k = zip(*keep)
                            embs_k = _np.array(list(embs_k), dtype="float32")
                        else:
                            meta_k, embs_k = [], _np.zeros((0, embs.shape[1]), dtype="float32")
                        new_vecs = _np.array(
                            _embed_texts([r["chunk_text"] for r in new_records], openai_key, "text-embedding-3-small"),
                            dtype="float32",
                        )
                        final_meta = list(meta_k) + new_records
                        final_embs = _np.vstack([embs_k, new_vecs]) if len(embs_k) else new_vecs
                        (index_dir / "metadata.json").write_text(
                            _json.dumps(final_meta, ensure_ascii=False, indent=2), encoding="utf-8"
                        )
                        _np.save(str(index_dir / "embeddings.npy"), final_embs)
                    else:
                        rag_warn = "RAG index not updated (no OpenAI API key). Run ingest.py manually."
            except Exception as _re_exc:
                rag_warn = f"RAG index update skipped: {_re_exc}"

        # B-03: always rebuild BM25 index after adding a device (BM25 is the offline mode)
        try:
            _rag_scripts2 = str(FACTORY_ROOT / "05_SCRIPTS")
            import sys as _sys2b
            if _rag_scripts2 not in _sys2b.path:
                _sys2b.path.insert(0, _rag_scripts2)
            from rag.ingest import collect_records, build_bm25_index, _save_bm25_index  # type: ignore
            bm25_records = collect_records()
            if bm25_records:
                _save_bm25_index(build_bm25_index(bm25_records))
        except Exception as _bm25_exc:
            import logging as _log_bm25
            _log_bm25.warning("[RAG] BM25 rebuild after ingest_device failed: %s", _bm25_exc)

        result: dict = {
            "ok": True,
            "device_id": device_id,
            "file_path": rel_path,
            "msg": f"Device '{device_id}' saved to {rel_path}",
        }
        if rag_warn:
            result["rag_warn"] = rag_warn
        if pii_warns:
            result["_pii_warnings"] = pii_warns
        return result

    def search_project(self, query: str) -> list[dict]:
        """Full-text search across all text files in the project."""
        if not self.root or not query or len(query) < 2:
            return []
        results: list[dict] = []
        q = query.lower()
        try:
            for p in sorted(self.root.rglob("*")):
                if not p.is_file() or p.name.startswith("."):
                    continue
                if p.suffix.lower() not in KIND_BY_EXT:
                    continue
                try:
                    rel = str(p.relative_to(self.root)).replace("\\", "/")
                    # filename match
                    if q in p.name.lower():
                        results.append({"path": rel, "name": p.name, "kind": _kind(p), "match": "filename", "line": 0, "snippet": ""})
                        if len(results) >= 50:
                            break
                        continue
                    # content match (first hit per file)
                    if p.stat().st_size > 500_000:
                        continue
                    text = p.read_text(encoding="utf-8", errors="replace")
                    for i, ln in enumerate(text.splitlines(), 1):
                        if q in ln.lower():
                            snippet = ln.strip()[:80]
                            results.append({"path": rel, "name": p.name, "kind": _kind(p), "match": "content", "line": i, "snippet": snippet})
                            break
                    if len(results) >= 50:
                        break
                except Exception:
                    continue
        except Exception:
            pass
        return results

    # ------------------------------------------------------------------
    # Actions & pipeline
    # ------------------------------------------------------------------

    def run_pipeline(self, action_id: str, file_path: str = "") -> dict:
        """Execute a real pipeline action using correct backend signatures."""
        if not self.root:
            return {"ok": False, "output": "No project open"}
        try:
            if action_id == "show_standards":
                rules_dir = FACTORY_ROOT / "01_GLOBAL_STANDARDS" / "rules"
                priority = ["GLOBAL_NAMING_STANDARD.md", "GLOBAL_PLATFORM_MATRIX.md"]
                sections: list[str] = []
                # Preferred files first, then the rest
                shown: set[str] = set()
                for fname in priority:
                    p = rules_dir / fname
                    if p.exists():
                        txt = p.read_text(encoding="utf-8", errors="replace")[:1500]
                        sections.append(f"## {fname}\n\n{txt}")
                        shown.add(fname)
                if rules_dir.exists():
                    for p in sorted(rules_dir.glob("*.md")):
                        if p.name not in shown:
                            sections.append(f"## {p.name}")
                if not sections:
                    return {"ok": False, "output": "01_GLOBAL_STANDARDS/rules/ not found"}
                return {"ok": True, "output": "\n\n---\n\n".join(sections)}

            elif action_id == "generate_hmi_interface":
                # B7 (E2E): GATE_CONFIG lists this as a gate-4 action, but the
                # dispatcher didn't know it — only the GUI's special-case did.
                # Any other caller got "Unknown action".
                r = self.generate_hmi_interface()
                return {"ok": bool(r.get("ok")),
                        "output": r.get("msg") or json.dumps(r, ensure_ascii=False)}

            elif action_id == "hmi_draft":
                r = self.generate_hmi_draft()
                return {"ok": bool(r.get("ok")),
                        "output": r.get("msg") or json.dumps(r, ensure_ascii=False)}

            elif action_id == "analyze":
                from project_analyzer import analyze_project  # type: ignore
                analysis = analyze_project(self.root)
                lines = [f"Project: {self.root.name}", f"Completion: {analysis.overall_pct:.0f}%", ""]
                for rd_id, rd in analysis.rd_statuses.items():
                    lines.append(f"  {rd_id}: {rd.title} — {rd.status}")
                if analysis.recommended_next:
                    lines.append("\nRecommended next steps:")
                    for s in analysis.recommended_next:
                        lines.append(f"  • {s}")
                return {
                    "ok": True,
                    "output": "\n".join(lines),
                    "analysis": {
                        "overall_pct": analysis.overall_pct,
                        "rd_statuses": {
                            k: {"title": v.title, "status": v.status, "can_run": v.can_run}
                            for k, v in analysis.rd_statuses.items()
                        },
                        "recommended_next": analysis.recommended_next,
                    },
                }

            elif action_id == "extract_io":
                from scl_extractor import extract_all_from_project, write_blocks  # type: ignore
                results = extract_all_from_project(self.root)
                out_dir = self.root / "_output" / "scl"
                out_dir.mkdir(parents=True, exist_ok=True)
                written = write_blocks(results, out_dir, overwrite=False)
                total = sum(r.extracted_count for r in results)
                lines = []
                if not results:
                    lines.append("No SCL blocks found in _output/ or metadata/")
                else:
                    lines.append(f"Extracted {total} SCL block(s). Wrote {len(written)} file(s) to _output/scl/")
                # Backfill RD01 Address column from AWL/SEQ legacy files
                try:
                    from awl_address_extractor import backfill_rd01_addresses  # type: ignore
                    bf = backfill_rd01_addresses(self.root)
                    if bf.get("updated", 0):
                        lines.append(f"Address backfill: {bf['msg']} ({bf['legacy_signals_found']} legacy signals found)")
                    elif bf.get("legacy_signals_found", 0):
                        lines.append(f"Address backfill: {bf['msg']}")
                except Exception as bf_exc:
                    lines.append(f"Address backfill skipped: {bf_exc}")
                return {"ok": True, "output": "\n".join(lines)}

            elif action_id == "generate_scl":
                # S-1 (audit M-01): OB1 is program code — same RD05 gate as
                # assemble_program (fail-closed).
                blocked = self._rd05_code_gen_gate("Generate SCL")
                if blocked:
                    return blocked
                ob = self.generate_ob1()
                tags = self.generate_iec_tags()
                combined = (ob.get("msg", "") + "\n" + tags.get("msg", "")).strip()
                return {
                    "ok": ob.get("ok", False) or tags.get("ok", False),
                    "output": combined or "SCL generation complete",
                    "rag_warnings": ob.get("rag_warnings", []),  # B-10: surface to UI
                }

            elif action_id == "generate_sequence_fb":
                # G-03: the ONLY AI-generated code artifact (sequence FB
                # from the reviewed RD03) — guarded/audited inside.
                r = self.generate_sequence_fb()
                out = {"ok": r.get("ok", False),
                       "output": r.get("msg") or r.get("output", "")}
                for k in ("precondition_error", "reasons", "file"):
                    if k in r:
                        out[k] = r[k]
                return out

            elif action_id == "rd01_crosscheck":
                r = self.get_rd01_crosscheck()
                if "summary" not in r:
                    return {"ok": False,
                            "output": r.get("msg", "Cross-check failed")}
                lines = [r["summary"]]
                for key, title in (
                        ("missing_in_rd01", "Missing from RD01"),
                        ("not_in_source", "No legacy source (hallucination?)"),
                        ("dir_mismatch", "Direction mismatch")):
                    v = r.get(key) or []
                    if v:
                        lines.append(f"{title} ({len(v)}):")
                        lines += [f"  - {i}" for i in v[:20]]
                        if len(v) > 20:
                            lines.append(f"  ... +{len(v) - 20} more")
                # findings are the POINT of the check — the action succeeded
                # when the check RAN; the summary carries the verdict.
                return {"ok": True, "output": "\n".join(lines)}

            elif action_id == "validate":
                result = self.validate_all_scl()
                if result.get("ok"):
                    lines = [f"Validated {len(result['files'])} SCL file(s). Total errors: {result['total_errors']}"]
                    for f in result["files"][:20]:
                        status = "OK" if f["errors"] == 0 else f"ERRORS: {f['errors']}"
                        lines.append(f"  {f['file']} — {status} ({f['warnings']} warn)")
                    lines.append(f"\n! {result.get('scope_warning', '')}")
                    return {
                        "ok": result["total_errors"] == 0,
                        "output": "\n".join(lines),
                        "files": result["files"],
                        "scope": result.get("scope"),
                        "scope_warning": result.get("scope_warning"),
                        # W-A5: persist the validation scope so the gate
                        # advance gate can refuse on structural-only results.
                        "last_validation": {
                            "errors": result["total_errors"],
                            "scope": result.get("scope") or "structural_only",
                        },
                    }
                return {"ok": False, "output": result.get("msg", "Validation failed")}

            elif action_id == "assemble_program":
                return self.assemble_program()

            elif action_id == "generate_test_scenarios":
                return self.generate_test_scenarios()

            elif action_id == "generate_report":
                r = self.generate_customer_report()
                r.setdefault("output", r.get("msg", "Customer report generated"))
                return r

            elif action_id == "generate_fat":
                r = self.generate_fat()
                r.setdefault("output", r.get("msg", "FAT/SAT protocol generated"))
                return r

            elif action_id == "export_tia":
                from tia_export import prepare_tia_package  # type: ignore
                st = self._project_state()
                plc_name = st.get("plc_name", "PLC_1")
                result = prepare_tia_package(self.root, plc_name=plc_name)
                lines = [f"TIA package prepared: {result.tia_dir.name}"]
                if result.warnings:
                    for w in result.warnings:
                        lines.append(f"  ! {w}")
                lines.append(f"\nChecklist ({len(result.checklist)} items):")
                for item in result.checklist:
                    icon = "v" if item.status == "ok" else ("!" if item.status == "warn" else "o")
                    lines.append(f"  {icon} [{item.category}] {item.text}")
                return _attach_warnings({"ok": True, "output": "\n".join(lines)})

            else:
                return {"ok": False, "output": f"Unknown action: {action_id}"}

        except Exception as e:
            return {"ok": False, "output": f"Error running {action_id}: {e}"}

    # ------------------------------------------------------------------
    # Prompts / Library
    # ------------------------------------------------------------------

    def get_library_blocks(self) -> list[dict]:
        return self._library_data()

    def import_block(self, block_name: str) -> dict:
        """Copy a library block's SCL into the project's SCL/ folder."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            from workbench.core.library_store import list_blocks, import_block_to_project  # type: ignore
            blocks = list_blocks()
            block  = next((b for b in blocks if b.name == block_name), None)
            if block is None:
                return {"ok": False, "msg": f"Block '{block_name}' not found in library"}
            dest = import_block_to_project(block, self.root)
            rel  = str(dest.relative_to(self.root)).replace("\\", "/")
            return {"ok": True, "msg": f"Imported to {rel}", "path": rel}
        except FileExistsError as e:
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_block_scl(self, block_name: str) -> dict:
        """Return the SCL source of a library block for preview."""
        try:
            from workbench.core.library_store import list_blocks  # type: ignore
            blocks = list_blocks()
            block  = next((b for b in blocks if b.name == block_name), None)
            if block is None:
                return {"ok": False, "text": ""}
            text = block.scl_path.read_text(encoding="utf-8", errors="replace")
            return {"ok": True, "text": text, "name": block.scl_path.name}
        except Exception as e:
            return {"ok": False, "text": str(e)}

    # ------------------------------------------------------------------
    # Dashboard / Report / Onboarding
    # ------------------------------------------------------------------

    def get_dashboard(self) -> dict:
        st  = self._project_state()
        cur = max(1, min(7, int(st.get("gate", st.get("current_gate", 1)) or 1)))
        found: dict[str, str] = {}
        if self.root:
            try:
                for p in self.root.rglob("RD*"):
                    if p.is_file() and p.suffix.lower() == ".md":
                        code = p.stem[:4].upper()
                        if code.startswith("RD"):
                            found[code] = _rd_status(p)
            except Exception:
                pass
        rds = []
        for i, nm in enumerate(RD_NAMES, start=1):
            code = f"RD{i:02d}"
            rds.append({"code": code, "name": nm, "status": found.get(code, "draft")})
        done     = sum(1 for r in rds if r["status"] == "ok")
        platform = st.get("target_platform") or st.get("platform") or "S7-1500"
        kpis = [
            {"label": "RD Documents", "value": f"{done}/{len(rds)}", "icon": "file-text"},
            {"label": "Gate",         "value": f"{cur}/7",           "icon": "chip"},
            {"label": "Platform",     "value": platform,             "icon": "cpu"},
            {"label": "Project Type", "value": (st.get("project_type") or "—").upper(), "icon": "package"},
        ]
        return _attach_warnings({
            "project":    self.root.name if self.root else "—",
            "type":       (st.get("project_type") or "PROJECT").upper(),
            "gate":       cur, "gate_max": 7, "gate_names": GATE_NAMES,
            "kpis":       kpis, "rds": rds,
        })

    def get_report(self) -> dict:
        st  = self._project_state()
        rep: dict = {}
        if self.root:
            for candidate in (
                self.root / "REPORTS" / "customer_report.json",
                self.root / "customer_report.json",
            ):
                try:
                    if candidate.exists():
                        rep = json.loads(candidate.read_text(encoding="utf-8"))
                        break
                except Exception:
                    pass
        cur       = max(1, min(7, int(st.get("gate", st.get("current_gate", 1)) or 1)))
        name      = self.root.name if self.root else "Project"
        pfrom     = st.get("source_platform", "S5")
        pto       = st.get("target_platform", "S7-1500")
        customer  = rep.get("customer", st.get("customer", "—"))
        prep_by   = self.settings.get("username", "") or "—"
        import datetime as _dt
        today = _dt.date.today().isoformat()
        return _attach_warnings({
            "title":           rep.get("title",    f"{name} — Modernisation Quote"),
            "customer":        customer,
            "date":            rep.get("date",     today),
            "prepared_by":     rep.get("prepared_by", prep_by),
            "version":         rep.get("version",  "1.0"),
            "platform_from":   rep.get("platform_from", pfrom),
            "platform_to":     rep.get("platform_to",   pto),
            "summary":         rep.get("summary",  f"This proposal presents a complete PLC modernization from {pfrom} to {pto} for {customer}."),
            "decision_matrix": rep.get("decision_matrix", [
                {"aspect": "PLC Hardware",      "keep": f"{pfrom} reuse",     "retrofit": "ET200SP remote IO", "greenfield": f"{pto} rack"},
                {"aspect": "Safety",            "keep": "Hardwired relays",   "retrofit": "F-CPU add-on",      "greenfield": "SIL 2 PLC"},
                {"aspect": "HMI",               "keep": "Legacy panels",      "retrofit": "KTP700 panels",     "greenfield": "WinCC Unified"},
                {"aspect": "Long-term support", "keep": "None (EOL)",         "retrofit": "10 yr lifecycle",   "greenfield": "15 yr lifecycle"},
            ]),
            "cost_items":      rep.get("cost_items", rep.get("items", [
                {"label": "Engineering & software",  "value": "€ 24.000"},
                {"label": "Hardware (PLC/IO)",        "value": "€ 21.000"},
                {"label": "Commissioning (FAT/SAT)", "value": "€ 15.000"},
            ])),
            "cost_total":      rep.get("cost_total", rep.get("total", "€ 60.000")),
            # keep legacy fields for backwards compat
            "matrix": rep.get("matrix", []),
            "items":  rep.get("items",  []),
            "total":  rep.get("total",  "€ 60.000"),
            "gate": cur, "gate_max": 7,
        })

    def get_onboarding(self) -> dict:
        recents = []
        lp = self.settings.get("last_project")
        if lp:
            recents.append({"name": Path(lp).name, "path": lp})
        for r in (self.settings.get("recent_projects") or []):
            p = r.get("path") if isinstance(r, dict) else r
            if p and p != lp:
                recents.append({"name": Path(p).name, "path": p})
        return {
            "user":      self.settings.get("username", "") or "Engineer",
            "recents":   recents,
            "templates": [
                {"id": "conveyor", "name": "Conveyor Retrofit",  "desc": "Belt / conveyor line"},
                {"id": "press",    "name": "Press Line",         "desc": "Press automation"},
                {"id": "filling",  "name": "Filling Line",       "desc": "Filling / packaging"},
                {"id": "blank",    "name": "Blank Project",      "desc": "Start from scratch"},
            ],
        }

    def open_project(self, path: str) -> dict:
        """Open an existing project folder.

        O-2 fix: the requested path must resolve to a location inside one of
        the allowed project roots (whitelist).  Paths outside the whitelist —
        including system directories, the factory's own tree, and arbitrary
        user-supplied strings — are rejected with an error so the bridge cannot
        be used to "open" (and thereby expose) arbitrary filesystem locations.
        Fail-safe: if no allowed root exists on disk, every path is rejected.
        """
        try:
            p = Path(path)
        except Exception:
            return {"ok": False, "msg": "Invalid path"}
        if not p.exists() or not p.is_dir():
            return {"ok": False, "msg": "Path not found"}
        # O-2: sandbox check — must be inside an allowed project root.
        err = self._check_open_project_path(p)
        if err is not None:
            return {"ok": False, "msg": err}
        self.root = p
        self.settings["last_project"] = str(p)
        recents = self.settings.setdefault("recent_projects", [])
        entry   = {"name": p.name, "path": str(p)}
        recents[:] = [r for r in recents if r.get("path") != str(p)]
        recents.insert(0, entry)
        self.settings["recent_projects"] = recents[:10]
        _save_settings(self.settings)
        # 2026-07-07 restructure: prune the never-used template folders from
        # EXISTING projects — only when truly empty (not a single file
        # anywhere below), so a project that ever used one keeps it. Makes
        # old projects converge on the lean layout without a migration step.
        try:
            import shutil as _sh
            for _name in ("01_DOCS", "02_HARDWARE", "03_PLC", "04_HMI",
                          "05_TESTS", "06_REPORTS", "99_FACTORY_REFS"):
                _d = p / _name
                if _d.is_dir() and not any(x.is_file() for x in _d.rglob("*")):
                    _sh.rmtree(_d, ignore_errors=True)
        except Exception:
            pass
        return {"ok": True}

    def remove_from_recents(self, path: str) -> dict:
        """Remove a project from the recent-projects list without touching disk."""
        recents = self.settings.setdefault("recent_projects", [])
        recents[:] = [r for r in recents if r.get("path") != path]
        if self.settings.get("last_project") == path:
            self.settings["last_project"] = recents[0]["path"] if recents else None
        _save_settings(self.settings)
        return {"ok": True}

    def create_project(self, template_id: str, name: str, parent_path: str, meta: dict | None = None) -> dict:
        """Create a new project from a template, optionally seeding PROJECT_STATE.json with meta."""
        try:
            from workbench.core.project_manager import ProjectManager  # type: ignore
            pm     = ProjectManager()
            parent = Path(parent_path)
            if not parent.is_dir():
                return {"ok": False, "msg": "Parent folder not found"}
            result = pm.create_project(parent, name)
            if result is None:
                return {"ok": False, "msg": f"Project '{name}' already exists at that location"}
            self.root = result
            self.settings["last_project"] = str(result)
            # F-1 (real-AI field test): creating in a folder outside the O-2
            # whitelist produced a project that open_project then REFUSED.
            # Creating there was the user's explicit location choice — record
            # it as projects_folder so create/open stay consistent.
            if self._check_open_project_path(result) is not None:
                self.settings["projects_folder"] = str(parent)
            _save_settings(self.settings)
            # Persist template + meta into PROJECT_STATE.json
            if template_id or meta:
                state_path = result / "PROJECT_STATE.json"
                try:
                    import json as _json
                    state: dict = {}
                    if state_path.exists():
                        state = _json.loads(state_path.read_text(encoding="utf-8"))
                    if template_id:
                        state["project_type"] = template_id.upper()
                    # A new project starts at gate 1 — an explicit counter so
                    # _effective_gate never has to guess (F-2).
                    state.setdefault("gate", 1)
                    if meta and isinstance(meta, dict):
                        # JS sends "platform"; store as "target_platform"
                        if "platform" in meta:
                            state["target_platform"] = meta["platform"]
                        for key in ("target_platform", "tia_version", "cpu_model", "safety", "hw_modules"):
                            if key in meta:
                                state[key] = meta[key]
                        # Onboarding form (UX overhaul 3.1) — validated, never
                        # free-form: classification gates AI/TIA egress.
                        if isinstance(meta.get("customer"), str) and meta["customer"].strip():
                            state["customer"] = meta["customer"].strip()
                        if meta.get("output_language") in ("TR", "EN", "DE"):
                            state["output_language"] = meta["output_language"]
                        if meta.get("data_classification") in ("PUBLIC", "INTERNAL",
                                                               "CONFIDENTIAL", "RESTRICTED"):
                            state["data_classification"] = meta["data_classification"]
                    self._save_state(state_path, state)
                except Exception:
                    pass
            return {"ok": True, "path": str(result), "name": name}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def browse_for_folder(self) -> dict:
        """Open a native folder picker dialog."""
        try:
            import webview as _wv  # noqa: PLC0415
            win = _wv.windows[0] if _wv.windows else None
            if win:
                result = win.create_file_dialog(_wv.FOLDER_DIALOG)
                if result:
                    chosen = result[0] if isinstance(result, (list, tuple)) else result
                    return {"ok": True, "path": str(chosen)}
        except Exception:
            pass
        return {"ok": False, "path": ""}

    def browse_for_file(self, kind: str = "") -> dict:
        """Open a native file picker. ``kind`` selects the filter preset —
        the frontend never passes raw filter strings (keeps the JS bridge
        surface typed). Currently: "tia_project" → .ap19/.ap20/.ap21."""
        presets = {
            "tia_project": ("TIA Portal project (*.ap19;*.ap20;*.ap21)",
                            "All files (*.*)"),
            "pdf": ("PDF files (*.pdf)", "All files (*.*)"),
            "compile_log": ("Log files (*.txt;*.log)", "All files (*.*)"),
            "s5d": ("Step5 project (*.s5d)", "All files (*.*)"),
        }
        file_types = presets.get(kind or "", ("All files (*.*)",))
        try:
            import webview as _wv  # noqa: PLC0415
            win = _wv.windows[0] if _wv.windows else None
            if win:
                result = win.create_file_dialog(_wv.OPEN_DIALOG,
                                                file_types=file_types)
                if result:
                    chosen = result[0] if isinstance(result, (list, tuple)) else result
                    return {"ok": True, "path": str(chosen)}
        except Exception:
            pass
        return {"ok": False, "path": ""}

    # ------------------------------------------------------------------
    # Version Compare (deterministic part — no open project required:
    # the scan/diff is local and side-effect free, like browse_for_folder.
    # AI hypotheses (version_compare_hypotheses) DO require a project.)
    # ------------------------------------------------------------------

    def version_compare_scan(self, folders) -> dict:
        """File-level comparison of ≥2 engineer-picked version folders.

        Stores the validated folder list on the Api instance so that
        version_compare_diff can address files by (version index, relname)
        — the JS bridge never passes raw absolute file paths."""
        try:
            import version_compare as vcmp  # type: ignore
            if not isinstance(folders, (list, tuple)) or len(folders) < 2:
                return _attach_warnings(
                    {"ok": False, "msg": "Select at least two version folders."})
            result = vcmp.compare_versions([str(f) for f in folders])
            if result.get("ok"):
                self._vc_dirs = [v["path"] for v in result["versions"]]
            return _attach_warnings(result)
        except Exception as e:
            return _attach_warnings({"ok": False, "msg": str(e)})

    def version_compare_diff(self, index_a, index_b, relname) -> dict:
        """Content diff of one file between two scanned versions.

        *index_a*/*index_b* address the folder list of the LAST successful
        version_compare_scan; *relname* must be a plain relative name
        (path traversal is refused)."""
        try:
            import version_compare as vcmp  # type: ignore
            dirs = getattr(self, "_vc_dirs", None)
            if not dirs:
                return _attach_warnings(
                    {"ok": False, "msg": "Run a version scan first."})
            try:
                ia, ib = int(index_a), int(index_b)
                dir_a, dir_b = dirs[ia], dirs[ib]
            except (ValueError, TypeError, IndexError):
                return _attach_warnings(
                    {"ok": False, "msg": "Invalid version index."})
            rel = Path(str(relname))
            if rel.is_absolute() or ".." in rel.parts:
                return _attach_warnings(
                    {"ok": False, "msg": "Invalid file name."})
            pa, pb = Path(dir_a) / rel, Path(dir_b) / rel
            return _attach_warnings(vcmp.diff_file(
                str(pa) if pa.is_file() else None,
                str(pb) if pb.is_file() else None,
                str(relname)))
        except Exception as e:
            return _attach_warnings({"ok": False, "msg": str(e)})

    # Canonical text lives in 04_AI_PROMPTS/analyze/PROMPT_COMPARE_VERSIONS.md
    # (same pattern as _RD03_CHAT_SYSTEM: constant here, documented there).
    _VC_HYPOTHESIS_SYSTEM = (
        "You are a senior PLC retrofit engineer reviewing the differences "
        "between two versions of a legacy machine control project (Siemens "
        "S5 era). You receive a DETERMINISTIC diff summary: file-level "
        "statuses plus symbol-table and text diffs. Binary program code is "
        "never included.\n"
        "Task: propose hypotheses for WHY these changes were made.\n"
        "Rules:\n"
        "1. Base every hypothesis ONLY on evidence present in the diff "
        "summary. Never invent changes that are not listed. If the diff is "
        "too sparse to interpret, say so instead of speculating.\n"
        "2. Output one hypothesis per line, exactly in this format:\n"
        "HYPOTHESIS: <text> | CONFIDENCE: high|medium|low | EVIDENCE: <the "
        "diff lines that support it>\n"
        "3. If a change could touch safety logic (E-Stop, guards, "
        "interlocks, star-delta switching, hydraulics enable chains), "
        "append ' — SAFETY: engineer review required' to that hypothesis "
        "and use confidence low.\n"
        "4. Consider typical legacy-machine reasons: commissioning tuning "
        "(timer values/descriptions), sensor replacement, mechanical "
        "retrofit, fault workarounds, I/O re-wiring, documentation cleanup.\n"
        "5. Output nothing after the hypothesis lines."
    )

    def version_compare_hypotheses(self, folders,
                                   consent: Optional[dict] = None) -> dict:
        """AI change-hypotheses for a version comparison (DRAFT_UNVERIFIED).

        Unlike the deterministic scan/diff, this REQUIRES an open project:
        the audit log, anonymization map and data-classification consent
        chain are all rooted in the project (a user-declared classification
        without a project would pierce the fail-closed C4 gate)."""
        if not self.root:
            return _attach_warnings({"ok": False, "msg":
                "Open a project first — AI hypotheses use the open "
                "project's data classification and audit log."})
        try:
            import version_compare as vcmp  # type: ignore
        except Exception as e:
            return _attach_warnings({"ok": False, "msg": str(e)})

        result = vcmp.compare_versions([str(f) for f in (folders or [])])
        if not result.get("ok"):
            return _attach_warnings(result)
        # Content diffs for the changed files (first ↔ last version),
        # capped — summarize_for_ai truncates to its char budget anyway.
        dirs = [v["path"] for v in result["versions"]]
        diffs = []
        for f in result["files"]:
            if f["status"] == "unchanged" or len(diffs) >= 20:
                continue
            names = [p["name"] if p else None for p in f["per_version"]]
            pa = Path(dirs[0]) / (names[0] or f["name"])
            pb = Path(dirs[-1]) / (names[-1] or f["name"])
            diffs.append(vcmp.diff_file(
                str(pa) if pa.is_file() else None,
                str(pb) if pb.is_file() else None, f["name"]))
        summary = vcmp.summarize_for_ai(result, diffs)

        task_cfg = self.get_provider_for_task("default")
        _emit_provider_warning(task_cfg)  # G-02: output-ceiling risk, if any
        provider, model_name = task_cfg["provider"], task_cfg["model"]
        api_key = self._resolve_api_key(provider)
        if not api_key:
            return _attach_warnings({"ok": False,
                "msg": f"No API key for '{provider}' — add it in Settings."})
        from data_classification_guard import check_ai_send  # type: ignore
        gate = check_ai_send(self.root, provider, self.settings,
                             consent_confirmed=bool((consent or {}).get("confirmed")))
        if not gate.allowed:
            return _attach_warnings({"ok": False, "msg": f"[C4] {gate.reason}"})
        for w in self._pii_soft_warn(provider):  # §11 soft PII warning
            _warn(w, category="privacy")

        # S-20 (B-G8): anonymize before sending to AI (required for INTERNAL).
        anon_map = self._anon_map_for_ai(gate)
        if getattr(gate, "requires_anonymization", False) or anon_map:
            summary, _anon_err = _anonymize_or_block(
                summary, anon_map,
                bool(getattr(gate, "requires_anonymization", False)),
                "version-compare summary")
            if _anon_err:
                return _attach_warnings({"ok": False, "msg": _anon_err})

        try:
            _audit_log(self.root, "version_compare_hypotheses", provider,
                       model_name, prompt_text=summary[:2000],
                       prompt_id="vcompare:hypotheses",
                       full_prompt_text=summary)
        except AuditLogError as ae:
            return _attach_warnings({"ok": False, "msg": f"[EU AI Act] {ae}"})

        try:
            from ai_client import AIClient  # type: ignore
            client = AIClient(provider=provider, api_key=api_key,
                              model=model_name)
            response, _usage = client.chat(
                system=self._VC_HYPOTHESIS_SYSTEM
                       + _lang_directive(self._output_language()),
                user=summary, max_tokens=4096)
            self._add_cost(_usage)
        except Exception as exc:
            return _attach_warnings({"ok": False,
                                     "msg": f"AI call failed: {exc}"})

        raw = (response or "").strip()
        hypotheses = []
        for line in raw.splitlines():
            line = line.strip().lstrip("-*• ").strip()
            if not line.upper().startswith("HYPOTHESIS:"):
                continue
            body = line[len("HYPOTHESIS:"):]
            text, confidence, evidence = body, "", ""
            parts = [p.strip() for p in body.split("|")]
            if parts:
                text = parts[0]
            for p in parts[1:]:
                up = p.upper()
                if up.startswith("CONFIDENCE:"):
                    confidence = p.split(":", 1)[1].strip().lower()
                elif up.startswith("EVIDENCE:"):
                    evidence = p.split(":", 1)[1].strip()
            hypotheses.append({"text": text.strip(),
                               "confidence": confidence,
                               "evidence": evidence})
        # Lenient: a malformed reply becomes one raw card — no silent loss.
        if not hypotheses and raw:
            hypotheses = [{"text": raw, "confidence": "", "evidence": ""}]
        return _attach_warnings({
            "ok": True,
            "hypotheses": hypotheses,
            "raw": raw,
            "label": "DRAFT_UNVERIFIED",
        })

    # ------------------------------------------------------------------
    # Gate timeline
    # ------------------------------------------------------------------

    def get_gate_history(self) -> dict:
        st  = self._project_state()
        cur = int(st.get("gate", st.get("current_gate", 1)) or 1)
        cur = max(1, min(7, cur))
        hist  = st.get("gate_history") or []
        # R-C-1 — UI read point: check chain integrity; on violation write a
        # WARN log (do not block — this is a display-only point).
        if hist:
            try:
                from customer_report import verify_gate_chain  # type: ignore
                violations = verify_gate_chain(hist)
                hard = [v for v in violations if not v.startswith("WARNING")]
                if hard:
                    _logger.warning(
                        "R-C-1 get_gate_history: chain violation detected "
                        "(UI is not blocked, report generation will be blocked): %s",
                        "; ".join(hard),
                    )
                elif violations:
                    _logger.info(
                        "R-C-1 get_gate_history: legacy record warning: %s",
                        "; ".join(violations),
                    )
            except Exception as _e:
                _logger.debug("R-C-1 get_gate_history: chain check skipped: %s", _e)
        gates = []
        for i, name in enumerate(GATE_NAMES, start=1):
            status = "done" if i < cur else ("current" if i == cur else "pending")
            ev = next((h for h in hist if h.get("gate") == i), None) or {}
            gates.append({
                "n": i, "name": name, "status": status,
                "when": ev.get("when", ""), "who": ev.get("who", ""),
                "note": ev.get("note", ""),
            })
        return _attach_warnings({"current": cur, "max": 7, "gates": gates})

    def get_gate6_compile_status(self) -> dict:
        """Return whether tia_compile.json (TIA Openness auto-evidence) exists."""
        if not self.root:
            return {"ok": True, "tia_auto": False}
        tia_json = self.root / "REPORTS" / "gate_results" / "tia_compile.json"
        return _attach_warnings({"ok": True, "tia_auto": tia_json.is_file()})

    def advance_gate(
        self,
        signature: str = "",
        accept_structural_only: bool = False,
        compile_log_path: str = "",
        manual_test_confirmed: bool = False,
    ) -> dict:
        """Advance the project to the next gate (C5 + W-A1 + W-A2 + W-A5 + B-P2).

        Refuses to advance when:
          - a required RD is still empty/template,
          - a validate-bearing gate has known validation errors,
          - the last validation was structural-only and the caller did not
            pass `accept_structural_only=True` to acknowledge the gap (W-A5),
          - an approval gate (3/5/6/7) has no — or an invalid — sign-off,
          - an approval gate's RD05 (Safety) is still unverified (W-A2),
          - gate 6 (Simulation) is attempted without a compile log path pointing
            to an existing file AND without engineer manual-test declaration (B-P2).
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            state_path = self.root / "PROJECT_STATE.json"
            st = self._project_state()

            # S-18 / B-P8: run auto-unsign check before evaluating blockers so
            # that a previously-signed gate whose RDs have changed is treated
            # as unsigned when its downstream gate attempts to advance.
            try:
                st, _autounsign_events = _check_and_apply_autounsign(self.root, st)
                if _autounsign_events:
                    self._save_state(state_path, st)
            except Exception as _e:
                _logger.warning("S-18 auto-unsign pre-check failed (non-fatal): %s", _e)

            # Preconditions — gate completion is no longer a bare counter bump.
            rd_statuses: dict[str, str] = {}
            try:
                from project_analyzer import analyze_project  # type: ignore
                analysis = analyze_project(self.root)
                rd_statuses = {k: v.status for k, v in analysis.rd_statuses.items()}
            except Exception:
                pass

            # 3-state model: which RDs are reviewed (green) / Not Applicable.
            # Only RDs with a real file are reviewable, so the Gate-3 precondition
            # is keyed on those (an RD reported 'produced' with no file on disk
            # cannot be reviewed and must not deadlock the gate). N/A RDs are
            # excluded from every gate precondition AND from the completion count.
            _rev_states = _rd_review_states(self.root, st, rd_statuses)
            rd_reviewed = {
                k: v["reviewed"] for k, v in _rev_states.items()
                if _rd_main_file(self.root, k) is not None
            }
            rd_na = {k for k, v in _rev_states.items() if v.get("na")}

            # `cur` is the RD-derived current gate (same as the display), NOT the
            # raw stored counter — so an inflated/legacy counter neither blocks a
            # legitimate advance nor lets a phantom one through. N/A-aware so a
            # greenfield project (RD13/14 N/A) is not frozen at gate 1.
            cur = _effective_gate(int(st.get("gate", st.get("current_gate", 0)) or 0),
                                  rd_statuses, rd_na)
            if cur >= 7:
                return _attach_warnings({"ok": False, "msg": "Already at the final gate"})

            # Auto-detect tia_compile.json written by _record_compile_success()
            # (TIA Openness bridge). If present, compile evidence is satisfied
            # without requiring the engineer to manually locate a log file.
            tia_json = self.root / "REPORTS" / "gate_results" / "tia_compile.json"
            tia_auto_compile = cur == 6 and tia_json.is_file()

            # Gate 4 (Code Generation): require the IO reconciliation to be
            # validated (ack matching the current RD01 hash). Skipped when RD01
            # is absent or N/A (nothing to reconcile).
            io_reconciliation_ok = True
            if cur == 4 and "RD01" not in rd_na and _rd_main_file(self.root, "RD01") is not None:
                _ack = st.get("io_reconciliation_ack") or {}
                io_reconciliation_ok = bool(_ack) and _ack.get("rd01_hash") == _rd_file_hash(self.root, "RD01")

            # Gate 4 (Code Generation): require the IO reconciliation to be
            # validated (ack matching the current RD01 hash). Skipped when RD01
            # is absent or N/A (nothing to reconcile).
            io_reconciliation_ok = True
            if cur == 4 and "RD01" not in rd_na and _rd_main_file(self.root, "RD01") is not None:
                _ack = st.get("io_reconciliation_ack") or {}
                io_reconciliation_ok = bool(_ack) and _ack.get("rd01_hash") == _rd_file_hash(self.root, "RD01")

            # Gate-3 Reconciliation: deterministic cross-artifact consistency
            # check (gate3_consistency). A crash is surfaced as a UI warning,
            # never swallowed — but it must not deadlock the gate (same
            # non-fatal discipline as the S-18 pre-check above).
            gate3_unres = None
            if cur == 3:
                try:
                    import gate3_consistency as _g3c
                    gate3_unres = _g3c.unresolved(_g3c.run(self.root))
                except Exception as _e:
                    _warn(f"Gate-3 consistency check failed — deviations were "
                          f"NOT evaluated for this lock: {_e}", "gate3")

            blockers = _gate_advance_blockers(
                cur, rd_statuses, signature, st.get("last_validation"),
                accept_structural_only=bool(accept_structural_only),
                last_io_validation=st.get("last_io_validation"),
                compile_log_path=str(compile_log_path or ""),
                manual_test_confirmed=bool(manual_test_confirmed),
                tia_auto_compile=tia_auto_compile,
                rd_reviewed=rd_reviewed,
                rd_na=rd_na,
                io_reconciliation_ok=io_reconciliation_ok,
                gate3_unresolved=gate3_unres,
            )
            if blockers:
                return _attach_warnings({
                    "ok": False,
                    "msg": "Gate advance blocked: " + "; ".join(blockers),
                    "blockers": blockers,
                    "needs_signature": cur in APPROVAL_GATES,
                })

            from datetime import datetime as _dt
            import hashlib as _hl
            now = _dt.now().strftime("%Y-%m-%d")
            sig = (signature or "").strip()
            who = sig or (self.settings or {}).get("username", "")
            note = "approved" if cur in APPROVAL_GATES else "completed"
            # B-P2: Gate 6 evidence — embed compile log reference and manual-test
            # declaration into the note field (part of the hash-protected payload)
            # so the audit trail is tamper-evident. Also store as structural fields
            # (outside the payload) for programmatic inspection.
            if cur == 6:
                log_path_clean = (
                    str(tia_json) if tia_auto_compile
                    else (compile_log_path or "").strip()
                )
                compile_source = "tia_openness_auto" if tia_auto_compile else "manual"
                note = (
                    f"approved; compile_log={log_path_clean}; "
                    f"compile_source={compile_source}; "
                    f"manual_test_confirmed={bool(manual_test_confirmed)}"
                )
            hist = list(st.get("gate_history") or [])
            # W-A1: keep history append-only and hash-chained. Removing an
            # existing record for the same gate would erase an audit trail,
            # so we no longer drop prior entries — re-approval appends a new
            # record whose prev_hash links to the previous tip.
            prev_hash = hist[-1].get("hash", "") if hist else ""
            record: dict = {
                "gate":      cur,
                "when":      now,
                "who":       who,
                "signature": sig,
                "note":      note,
                "prev_hash": prev_hash,
            }
            payload = json.dumps(
                {k: record[k] for k in ("gate", "when", "who", "signature", "note", "prev_hash")},
                ensure_ascii=False, sort_keys=True,
            ).encode("utf-8")
            record["hash"] = _hl.sha256(payload).hexdigest()
            # M-07 (2026-07-10 audit): the chain alone proves INTERNAL
            # consistency only — it catches accidental edits, not a forger
            # rewriting PROJECT_STATE.json wholesale with recomputed hashes.
            # Cross-anchor the record hash into the hash-chained AI decision
            # log: hiding a forged signature now requires rewriting BOTH
            # files consistently, and each file exposes the other. Anchor
            # failure is non-blocking but must be said (S-2 discipline).
            try:
                # prompt_id is persisted verbatim in the log entry (prompt
                # text is only hashed) — the record hash must live there so
                # the anchor is directly greppable/verifiable.
                _audit_log(self.root, f"gate_advance:{cur}", "system",
                           "gate_chain",
                           prompt_text=(f"gate={cur}; who={who}; when={now}; "
                                        f"record_hash={record['hash']}"),
                           prompt_id=f"gate:{cur}:anchor:{record['hash']}")
                record["audit_anchor"] = True
            except Exception as _ga_exc:
                record["audit_anchor"] = False
                _warn(f"Gate record hash NOT anchored in the audit log "
                      f"({_ga_exc}) — this record is protected against "
                      "accidental edits only.", category="compliance")
            # B-P2: structural evidence fields stored outside the hash payload
            # (so they do NOT alter the chain hash of existing records). They
            # serve as queryable metadata; the tamper-evident proof is in note.
            if cur == 6:
                record["compile_log_path"] = (compile_log_path or "").strip()
                record["manual_test_confirmed"] = bool(manual_test_confirmed)
            hist.append(record)
            st["gate"] = cur + 1
            st["gate_history"] = hist
            # Staleness snapshot: remember what every RD looked like at the
            # moment this gate was approved, so later edits surface as a
            # visible "re-validate" warning in the gate view (advisory only —
            # a snapshot failure must never block an already-approved advance).
            try:
                st["rd_snapshot"] = {
                    "gate": cur,
                    "when": now,
                    "hashes": _rd_content_hashes(self.root),
                }
            except Exception:
                pass
            # S-18 / B-P8: per-gate RD snapshot for auto-unsign.
            # For approval gates, record the exact RDs this gate depends on so
            # that any later edit triggers an automatic re-sign requirement.
            # Failure must never block an already-approved advance (try/except).
            if cur in APPROVAL_GATES:
                try:
                    gate_snaps: dict = dict(st.get("gate_rd_snapshots") or {})
                    gate_snaps[str(cur)] = {
                        "gate": cur,
                        "when": now,
                        "hashes": _gate_rd_hashes_for_gate(self.root, cur, rd_na),
                    }
                    st["gate_rd_snapshots"] = gate_snaps
                except Exception:
                    pass
            # 3-state model: locking Human Review (gate 3) seals every produced
            # RD (🟢 reviewed → 🔒 locked). Vites-2: the reviewed precondition
            # covers the CRITICAL RDs (RD01/RD03/RD05); the remaining produced
            # RDs are stamped "auto-accepted" here — honestly recorded in the
            # audit trail as machine-accepted, NOT human-reviewed. Locking
            # (re)records the content hash so a later edit breaks the seal.
            if cur == 3:
                try:
                    _lock_now = _dt.now().isoformat(timespec="seconds")
                    vers = dict(st.get("rd_verifications") or {})
                    for rd_id, status in rd_statuses.items():
                        if rd_id in rd_na:
                            continue  # Not Applicable → nothing to seal
                        if (status or "").lower() in _RD_INCOMPLETE_STATUSES:
                            continue
                        rec = dict(vers.get(rd_id) or {})
                        if not rec.get("reviewed"):
                            rec["reviewed"] = True
                            rec["auto_accepted"] = True
                            rec["reviewed_by"] = "auto-accepted (Gate-3 lock)"
                            rec["reviewed_at"] = _lock_now
                        rec["locked"] = True
                        rec["content_hash"] = (
                            rec.get("content_hash") or _rd_file_hash(self.root, rd_id)
                        )
                        vers[rd_id] = rec
                    st["rd_verifications"] = vers
                except Exception:
                    pass
            self._save_state(state_path, st)
            return _attach_warnings({"ok": True, "gate": cur + 1, "name": GATE_NAMES[cur]})
        except Exception as e:
            return _attach_warnings({"ok": False, "msg": str(e)})

    def review_rd(self, rd_id: str, signature: str = "") -> dict:
        """Engineer pre-approval (🟡 → 🟢) of a single RD draft.

        One-click for most RDs (verified_by = settings username). RD05 (Safety)
        requires a named sign-off (name + role) — that named review IS the
        certified safety engineer's signature for W-A2. Records the file hash so
        a later edit demotes the RD back to draft (stale). Pre-approval only;
        the LOCK happens at the Gate-3 bulk sign-off (advance_gate).
        """
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        rd_id = (rd_id or "").strip().upper()
        if not re.fullmatch(r"RD\d{2}", rd_id):
            return {"ok": False, "msg": f"Invalid RD id: {rd_id!r}"}
        h = _rd_file_hash(self.root, rd_id)
        if not h:
            return {"ok": False, "msg": f"{rd_id} has no metadata file to review yet."}
        sig = (signature or "").strip()
        if rd_id == "RD05":
            ok, reason = _validate_signature(sig)
            if not ok:
                return {
                    "ok": False, "needs_signature": True,
                    "msg": f"RD05 (Safety) needs a certified-engineer sign-off — {reason}",
                }
            who = sig
        else:
            who = sig or (self.settings or {}).get("username", "") or "engineer"
        from datetime import datetime as _dt
        st = self._project_state()
        vers = dict(st.get("rd_verifications") or {})
        prev = vers.get(rd_id) or {}
        vers[rd_id] = {
            "reviewed": True,
            "locked": False,                       # lock is a Gate-3 action only
            "reviewed_by": who,
            "reviewed_at": _dt.now().strftime("%Y-%m-%d"),
            "author": prev.get("author") or _rd_draft_author(self.root, rd_id),
            "content_hash": h,
        }
        st["rd_verifications"] = vers
        self._save_state(self.root / "PROJECT_STATE.json", st)
        return {"ok": True, "rd": rd_id, "reviewed_by": who,
                "reviewed_at": vers[rd_id]["reviewed_at"]}

    def unreview_rd(self, rd_id: str) -> dict:
        """Revert an engineer pre-approval (🟢/🔒 → 🟡). Used when the engineer
        wants to re-open a previously reviewed RD."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        rd_id = (rd_id or "").strip().upper()
        st = self._project_state()
        vers = dict(st.get("rd_verifications") or {})
        if rd_id in vers:
            vers.pop(rd_id, None)
            st["rd_verifications"] = vers
            self._save_state(self.root / "PROJECT_STATE.json", st)
        return {"ok": True, "rd": rd_id}

    def mark_rd_na(self, rd_id: str, reason: str = "") -> dict:
        """Mark an RD Not Applicable (⊘) for this project — e.g. no HMI, or
        retrofit-only RD13/14 on a greenfield project. N/A RDs are excluded from
        every gate precondition and from code generation. A reason is required;
        RD05 (Safety) demands a NAMED justification (safety engineer decides
        'no safety functions in scope') — fail-safe, never a silent skip."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        rd_id = (rd_id or "").strip().upper()
        if not re.fullmatch(r"RD\d{2}", rd_id):
            return {"ok": False, "msg": f"Invalid RD id: {rd_id!r}"}
        reason = (reason or "").strip()
        if rd_id == "RD05":
            ok, why = _validate_signature(reason)
            if not ok:
                return {"ok": False, "needs_signature": True,
                        "msg": f"RD05 (Safety) N/A needs a named safety-engineer justification — {why}"}
        elif len(reason) < 4:
            return {"ok": False, "msg": "A short reason is required to mark an RD Not Applicable."}
        from datetime import datetime as _dt
        st = self._project_state()
        vers = dict(st.get("rd_verifications") or {})
        prev = vers.get(rd_id) or {}
        # N/A supersedes any prior review/lock — drop the reviewer/lock/hash
        # fields so the audit record is unambiguous (no stale 'reviewed_by' on an
        # N/A row). Keep only the AI author (who produced the draft).
        vers[rd_id] = {
            "na": True,
            "na_reason": reason,
            "na_by": (self.settings or {}).get("username", "") or "engineer",
            "na_at": _dt.now().strftime("%Y-%m-%d"),
            "author": prev.get("author", ""),
            "reviewed": False,
            "locked": False,
        }
        st["rd_verifications"] = vers
        self._save_state(self.root / "PROJECT_STATE.json", st)
        return {"ok": True, "rd": rd_id, "na": True}

    def unmark_rd_na(self, rd_id: str) -> dict:
        """Clear the Not-Applicable mark (⊘ → 🟡)."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        rd_id = (rd_id or "").strip().upper()
        st = self._project_state()
        vers = dict(st.get("rd_verifications") or {})
        if rd_id in vers:
            vers.pop(rd_id, None)
            st["rd_verifications"] = vers
            self._save_state(self.root / "PROJECT_STATE.json", st)
        return {"ok": True, "rd": rd_id, "na": False}

    def get_io_reconciliation(self) -> dict:
        """Cross-source IO reconciliation for RD01 (provenance + delta), plus the
        AI-written Conflicts/Review-Required sections and the current ack status.
        Deterministic — parses the produced RD01 table, no AI call."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        f = _rd_main_file(self.root, "RD01")
        if f is None:
            return {"ok": False, "msg": "RD01 (IO List) not produced yet", "exists": False}
        try:
            from workbench.core import io_list_io  # type: ignore
            rows, _fm = io_list_io.read_md(f)
        except Exception as e:
            return {"ok": False, "msg": f"Could not parse RD01: {e}"}
        report = _reconcile_io_rows(rows)
        try:
            sections = _extract_md_sections(
                f.read_text(encoding="utf-8", errors="replace"),
                ("Conflicts", "Review Required", "Source Reconciliation", "Assumptions"),
            )
        except Exception:
            sections = {}
        cur_hash = _rd_file_hash(self.root, "RD01")
        ack = (self._project_state().get("io_reconciliation_ack") or {})
        acknowledged = bool(ack) and ack.get("rd01_hash") == cur_hash
        return _attach_warnings({
            "ok": True, "exists": True, "file": f.name,
            "report": report, "sections": sections,
            "acknowledged": acknowledged,
            "ack": ack if acknowledged else {},
            "stale_ack": bool(ack) and not acknowledged,
        })

    def ack_io_reconciliation(self, note: str = "") -> dict:
        """Engineer validates the IO reconciliation → unlocks code generation
        (Gate 4). Tied to the current RD01 hash so a later edit forces re-ack."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        h = _rd_file_hash(self.root, "RD01")
        if not h:
            return {"ok": False, "msg": "RD01 (IO List) not produced yet"}
        from datetime import datetime as _dt
        st = self._project_state()
        st["io_reconciliation_ack"] = {
            "by": (self.settings or {}).get("username", "") or "engineer",
            "at": _dt.now().strftime("%Y-%m-%d"),
            "note": (note or "").strip(),
            "rd01_hash": h,
        }
        self._save_state(self.root / "PROJECT_STATE.json", st)
        return {"ok": True, "acknowledged": True}

    def get_gate3_consistency(self) -> dict:
        """Gate-3 "Reconciliation & Preview" — deterministic cross-artifact
        consistency check (RD01 ↔ RD11/RD08 ↔ dossier decisions) plus the
        pending critical signatures, with waivers applied. Management by
        exception: only deviations are listed; consistent facts are counts."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        try:
            import gate3_consistency as _g3c
            result = _g3c.run(self.root)
        except Exception as e:
            return _attach_warnings(
                {"ok": False, "msg": f"Consistency check failed: {e}"})
        # Pending critical signatures (RD01/RD03/RD05 produced but not green)
        # — enforced by the existing lock preconditions; surfaced here so the
        # reconciliation screen is the ONE honest list before the bulk sign.
        rd_statuses: dict[str, str] = {}
        try:
            from project_analyzer import analyze_project  # type: ignore
            analysis = analyze_project(self.root)
            rd_statuses = {k: v.status for k, v in analysis.rd_statuses.items()}
        except Exception:
            pass
        rev = _rd_review_states(self.root, self._project_state(), rd_statuses)
        pending: list[dict] = []
        for rd in sorted(CRITICAL_RDS):
            status = (rd_statuses.get(rd, "") or "").lower()
            if status in _RD_INCOMPLETE_STATUSES:
                continue
            v = rev.get(rd, {})
            if v.get("na") or v.get("reviewed") or v.get("locked"):
                continue
            try:
                human = RD_NAMES[int(rd[2:]) - 1]
            except Exception:
                human = rd
            pending.append({
                "id": f"pending:{rd}", "kind": "pending_signature",
                "severity": "pending", "subject": rd,
                "title": f"{rd} ({human}) awaits engineer approval",
                "detail": ("The bulk lock seals every produced RD; the critical "
                           "set must carry a human approval first. Not waivable "
                           "— approve (or N/A) it in the RD list above."),
                "fix_target": f"review:{rd}", "waivable": False, "waived": False,
            })
        findings = result.get("findings", []) + pending
        _sev_rank = {"red": 0, "pending": 1, "deviation": 2}
        findings.sort(key=lambda f: (_sev_rank.get(f.get("severity"), 3),
                                     f.get("kind", ""), f.get("subject", "")))
        unresolved_n = result.get("unresolved", 0) + len(pending)
        return _attach_warnings({
            "ok": True,
            "findings": findings,
            "consistent": result.get("consistent", {}),
            "skipped": result.get("skipped", []),
            "unresolved": unresolved_n,
            "red": result.get("red", 0),
            "lock_ready": unresolved_n == 0,
        })

    def waive_gate3_finding(self, finding_id: str, reason: str = "",
                            name: str = "") -> dict:
        """Record a conscious-choice waiver for ONE reconciliation deviation.
        Reason + name are mandatory (W-A1 signature rules); RED findings are
        refused — the safety baseline (EN ISO 13850) bends for no signature.
        The waiver is permanent (metadata/gate3_waivers.json), never asked
        again, and lands in the TRACEABILITY matrix at its next generation."""
        if not self.root:
            return {"ok": False, "msg": "No project open"}
        ok, why = _validate_signature(name)
        if not ok:
            return {"ok": False, "needs_signature": True,
                    "msg": f"Waiver needs a name: {why}"}
        try:
            import gate3_consistency as _g3c
            current = _g3c.collect_findings(self.root)
        except Exception as e:
            return {"ok": False, "msg": f"Consistency check failed: {e}"}
        finding = next((f for f in current.get("findings", [])
                        if f.get("id") == finding_id), None)
        if finding is None:
            return {"ok": False,
                    "msg": "Finding not found — the list may be stale; reload "
                           "the Gate-3 screen."}
        ok, msg = _g3c.save_waiver(self.root, finding, reason, name)
        if not ok:
            return {"ok": False, "msg": msg}
        return {"ok": True, "id": finding_id, "by": (name or "").strip()}

    def get_gate_model(self) -> dict:
        """Return gate model derived from project state (PROJECT_STATE.json is authoritative)."""
        if not self.root:
            return {"current": 1, "max": 7, "gates": []}

        # PROJECT_STATE.json holds a `gate` counter, but it is NOT trusted as the
        # completion signal — it can be inflated (advance_gate bumps it; legacy
        # data was advanced before preconditions existed). Real completion is
        # derived from the RD documents below, then reconciled via _effective_gate.
        st = self._project_state()

        # S-18 / B-P8: check if any previously-signed approval-gate RDs have
        # changed on disk; auto-unsign and persist before building the model.
        unsign_events: list = []
        try:
            st, unsign_events = _check_and_apply_autounsign(self.root, st)
            if unsign_events:
                state_path = self.root / "PROJECT_STATE.json"
                self._save_state(state_path, st)
        except Exception as _e:
            _logger.warning("S-18 auto-unsign check failed (non-fatal): %s", _e)

        stored = int(st.get("gate", st.get("current_gate", 0)) or 0)

        rd_statuses: dict[str, str] = {}
        detected_platform = ""
        try:
            from project_analyzer import analyze_project  # type: ignore
            analysis = analyze_project(self.root)
            rd_statuses = {k: v.status for k, v in analysis.rd_statuses.items()}
            if analysis.input_scan and analysis.input_scan.primary_platform:
                detected_platform = analysis.input_scan.primary_platform
        except Exception:
            pass

        # 3-state per-RD verification view (draft 🟡 / reviewed 🟢 / locked 🔒 /
        # N/A ⊘). Computed before _effective_gate so N/A RDs don't freeze the
        # gate position (a greenfield project would otherwise stick at gate 1).
        rev_states = _rd_review_states(self.root, st, rd_statuses)
        _na_set = {k for k, v in rev_states.items() if v.get("na")}
        current = _effective_gate(stored, rd_statuses, _na_set)

        # APPROVAL_GATES / GATE_CONFIG are module-level (shared with advance_gate).
        hist = st.get("gate_history") or []
        gates = []
        for i, name in enumerate(GATE_NAMES, start=1):
            status = "done" if i < current else ("current" if i == current else "pending")
            cfg = GATE_CONFIG[i - 1] if i <= len(GATE_CONFIG) else {"rds": [], "actions": []}
            ev = next((h for h in hist if h.get("gate") == i), None) or {}
            docs = []
            for rd_id in cfg["rds"]:
                rd_status = rd_statuses.get(rd_id, "draft")
                rd_path: Optional[str] = None
                if self.root:
                    md_dir = self.root / "metadata"
                    if md_dir.is_dir():
                        for pat in (f"{rd_id}_*.ai_draft.md", f"{rd_id}_*.md"):
                            _m = sorted(md_dir.glob(pat))
                            if _m:
                                rd_path = "metadata/" + _m[0].name
                                break
                rv = rev_states.get(rd_id, {})
                # B-06: RD11 (HMI) / RD12 (UseCase) rarely have source
                # material on pre-TIA machines (physical push-button panels,
                # lost operator manuals). Suggest N/A instead of letting the
                # engineer hunt for a WinCC export that never existed.
                na_hint = ""
                if (rd_id in ("RD11", "RD12")
                        and detected_platform in ("S5", "S7_300", "S7_400")
                        and not rv.get("na")
                        and rv.get("ui_state") in ("empty", "draft")):
                    na_hint = (
                        f"Detected platform {detected_platform}: machines of "
                        "this era usually have no "
                        + ("HMI export (physical push-button panels)"
                           if rd_id == "RD11" else "operator manual / use-case doc")
                        + " — mark N/A if that is true here."
                    )
                docs.append({
                    "rd": rd_id, "status": rd_status, "path": rd_path,
                    "na_hint": na_hint,
                    "ui_state": rv.get("ui_state", "draft"),
                    "reviewed": rv.get("reviewed", False),
                    "locked": rv.get("locked", False),
                    "auto_accepted": rv.get("auto_accepted", False),
                    "critical": rd_id in CRITICAL_RDS,
                    "stale": rv.get("stale", False),
                    "na": rv.get("na", False),
                    "na_reason": rv.get("na_reason", ""),
                    "reviewed_by": rv.get("reviewed_by", ""),
                    "reviewed_at": rv.get("reviewed_at", ""),
                    "author": rv.get("author", ""),
                })
            gates.append({
                "n": i,
                "name": name,
                "status": status,
                "needs_approval": i in APPROVAL_GATES and status == "current",
                "docs": docs,
                "actions": cfg["actions"],
                "when": ev.get("when", ""),
                "who": ev.get("who", ""),
            })
        # Review summary across every PRODUCED RD — drives the Gate-3 bulk-lock
        # UI ("X/N reviewed", "Lock & Proceed" enabled only when all green).
        _na = sorted(rd for rd, v in rev_states.items() if v.get("na"))
        _produced = [
            rd for rd, s in rd_statuses.items()
            if (s or "").lower() not in _RD_INCOMPLETE_STATUSES and rd not in _na
        ]
        _reviewed = [rd for rd in _produced if rev_states.get(rd, {}).get("reviewed")]
        _unreviewed = sorted(rd for rd in _produced if rd not in _reviewed)
        _stale = sorted(rd for rd in _produced if rev_states.get(rd, {}).get("stale"))
        # Vites-2: the lock only WAITS for the critical RDs; the other
        # produced-but-unreviewed ones will be auto-accepted by the lock.
        _critical_pending = sorted(rd for rd in _unreviewed if rd in CRITICAL_RDS)
        review_summary = {
            "produced": len(_produced),
            "reviewed": len(_reviewed),
            "unreviewed": _unreviewed,
            "stale": _stale,
            "na": _na,
            # All produced RDs are reviewed (N/A ones don't count) → ready to lock.
            "all_reviewed": bool(_produced) and not _unreviewed,
            "critical_pending": _critical_pending,
            # Lock is possible once the critical set is green (risk-based).
            "lock_ready": bool(_produced) and not _critical_pending,
            "auto_accept_on_lock": sorted(
                rd for rd in _unreviewed if rd not in CRITICAL_RDS),
            "locked": sorted(rd for rd in _produced if rev_states.get(rd, {}).get("locked")),
        }

        gate_pct = round((current - 1) / 7 * 100)
        if rd_statuses:
            done_rds = sum(1 for s in rd_statuses.values() if s in ("ok", "done"))
            doc_pct: int | None = round(done_rds / 14 * 100)
        else:
            doc_pct = None
        return _attach_warnings({
            "current": current, "max": 7, "gates": gates,
            "project_type": self._project_type(),
            "gate_pct": gate_pct,
            "doc_pct": doc_pct,
            "review_summary": review_summary,
            "overall_pct": gate_pct,   # alias kept for old clients; now consistent with gate nav
            "stale_rds": _stale_rds(st, self.root),
            # S-18: surface auto-unsign events to the UI so the user sees why
            # a previously-approved gate now needs re-signing.
            "auto_unsign_warnings": [e["msg"] for e in unsign_events],
        })

    def find_rd_file(self, rd_id: str) -> dict:
        """Find the most recent file for rd_id (e.g. 'RD01') in metadata/.
        Returns {found: bool, path: str|null} where path is the relpath
        suitable for read_file / openFile in the frontend."""
        if not self.root:
            return {"found": False, "path": None}
        md_dir = self.root / "metadata"
        if not md_dir.is_dir():
            return {"found": False, "path": None}
        for pat in (f"{rd_id}_*.ai_draft.md", f"{rd_id}_*.md"):
            matches = sorted(md_dir.glob(pat))
            if matches:
                return {"found": True, "path": "metadata/" + matches[0].name}
        return {"found": False, "path": None}

    # ------------------------------------------------------------------
    # Git
    # ------------------------------------------------------------------

    def git_info(self) -> dict:
        """Return real git status for the project root."""
        root = self.root or FACTORY_ROOT
        branch   = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
        status   = _run_git(["status", "--short"], root)
        log      = _run_git(["log", "--oneline", "-8"], root)
        remote   = _run_git(["remote", "get-url", "origin"], root)
        changes  = [ln for ln in status.splitlines() if ln.strip()]
        return {
            "branch":  branch  or "main",
            "remote":  remote  or "",
            "changes": changes,
            "log":     log.splitlines() if log else [],
        }

    def git_diff(self, relpath: str) -> dict:
        """Return the git diff for a single file."""
        root = self.root or FACTORY_ROOT
        diff = _run_git(["diff", "HEAD", "--", relpath], root)
        return {"diff": diff or "(no diff)"}

    # ------------------------------------------------------------------
    # AI / inline suggestion
    # ------------------------------------------------------------------

    def get_ai_suggestion(self, code_context: str, cursor_line: int) -> dict:
        """Return a short inline AI completion for the current code context."""
        cfg      = self.settings
        provider = cfg.get("ai_provider", "anthropic")
        model    = cfg.get("ai_model", "claude-sonnet-4-6")
        api_key  = self._resolve_api_key(provider)  # C-A2: keystore on-demand
        if not api_key:
            suggestion = _scl_stub_suggestion(code_context)
            return {"ok": bool(suggestion), "suggestion": suggestion, "msg": "No API key — add one in Settings"}
        allowed, reason = self._ai_send_allowed(provider)
        if not allowed:
            return {"ok": False, "suggestion": "", "msg": reason, "blocked": "classification"}
        pii_warns = self._pii_soft_warn(provider)  # §11 soft PII warning
        # C-1 fix: audit log before AI call (fail-closed)
        try:
            _audit_log(self.root, "get_ai_suggestion",
                       provider, model,
                       prompt_text=code_context,
                       prompt_id="get_ai_suggestion")
        except AuditLogError as _ae:
            return {"ok": False, "suggestion": "", "msg": str(_ae), "blocked": "audit_log"}
        try:
            from ai_client import AIClient  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model or None)
            system = "You are a PLC SCL code assistant. Complete the code concisely. Return only the completion text, no explanation."
            text, _ = client.chat(system=system, user=code_context, max_tokens=120, temperature=0.2)
            suggestion_text = (text or "").strip()
            # R-C-2 fix: output audit log — fail-warn (visible warning, no blocking)
            _audit_out_warn: str = ""
            try:
                _audit_log(self.root, "get_ai_suggestion [output]",
                           provider, model,
                           output_text=suggestion_text,
                           prompt_id="get_ai_suggestion:output")
            except AuditLogError as _out_exc:
                _audit_out_warn = "output_hash_failed"
                import logging as _log
                _log.warning("[EU AI Act] get_ai_suggestion output audit hash could not be written — %s", _out_exc)
            result: dict = {"ok": True, "suggestion": suggestion_text}
            if pii_warns:
                result["_pii_warnings"] = pii_warns
            if _audit_out_warn:
                result["_audit_warn"] = _audit_out_warn
            return result
        except Exception:
            suggestion = _scl_stub_suggestion(code_context)
            return {"ok": bool(suggestion), "suggestion": suggestion, "msg": "stub" if suggestion else "AI unavailable"}

    def run_ai_prompt(self, prompt: str, context: str = "") -> dict:
        """Run a full AI prompt via direct API."""
        cfg      = self.settings
        provider = cfg.get("ai_provider", "anthropic")
        model    = cfg.get("ai_model",    "claude-sonnet-4-6")
        api_key  = self._resolve_api_key(provider)  # C-A2: keystore on-demand
        full_prompt = (f"Project context:\n{context}\n\n---\n{prompt}" if context else prompt)
        if not api_key:
            return {"ok": False, "response": "", "msg": "No API key — add one in Settings", "mode": "api"}
        allowed, reason = self._ai_send_allowed(provider)
        if not allowed:
            return {"ok": False, "response": "", "msg": reason,
                    "mode": "api", "blocked": "classification"}
        pii_warns = self._pii_soft_warn(provider)  # §11 soft PII warning
        # C-1 fix: audit log before AI call (fail-closed)
        try:
            _audit_log(self.root, "run_ai_prompt",
                       provider, model,
                       prompt_text=full_prompt,
                       prompt_id="run_ai_prompt")
        except AuditLogError as _ae:
            return {"ok": False, "response": "", "msg": str(_ae), "blocked": "audit_log"}
        try:
            from ai_client import AIClient  # type: ignore
            client = AIClient(provider=provider, api_key=api_key, model=model or None)
            system = "You are an expert PLC automation engineer. Provide accurate, concise responses."
            text, usage = client.chat(system=system, user=full_prompt, max_tokens=2048)
            resp_text = (text or "").strip()
            # R-C-2 fix: output audit log — fail-warn (visible warning, no blocking)
            _audit_out_warn: str = ""
            try:
                _audit_log(self.root, "run_ai_prompt [output]",
                           provider, model,
                           output_text=resp_text,
                           prompt_id="run_ai_prompt:output")
            except AuditLogError as _out_exc:
                _audit_out_warn = "output_hash_failed"
                import logging as _log
                _log.warning("[EU AI Act] run_ai_prompt output audit hash could not be written — %s", _out_exc)
            self._add_cost(usage)   # B8: real spend bookkeeping
            result: dict = {
                "ok": True,
                "response": resp_text,
                "cost_usd": usage.cost_usd,
                "tokens": {"input": usage.input_tokens, "output": usage.output_tokens},
                "mode": "api",
            }
            if pii_warns:
                result["_pii_warnings"] = pii_warns
            if _audit_out_warn:
                result["_audit_warn"] = _audit_out_warn
            return result
        except Exception as e:
            return {"ok": False, "response": "", "msg": str(e), "mode": "api"}


def _scl_stub_suggestion(context: str) -> str:
    """Minimal rule-based SCL completion stub when no API key is set."""
    lines = context.strip().splitlines()
    last  = lines[-1].strip().upper() if lines else ""
    stubs = {
        "IF":           "  THEN\n    ;\nEND_IF;",
        "FOR":          " i := 1 TO 10 DO\n    ;\nEND_FOR;",
        "WHILE":        "  DO\n    ;\nEND_WHILE;",
        "FUNCTION_BLOCK": " \"FB_New\"\nVAR_INPUT\n  Enable : BOOL;\nEND_VAR\nVAR_OUTPUT\n  Done : BOOL;\nEND_VAR\nBEGIN\n\nEND_FUNCTION_BLOCK",
    }
    for kw, stub in stubs.items():
        if last.startswith(kw):
            return stub
    return ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import webview
    index = WEBGUI / "index.html"
    if not index.exists():
        print(f"ERROR: GUI not found at {index}")
        sys.exit(2)
    api    = Api()
    window = webview.create_window(
        "AUTOMATION_FACTORY — Workbench",
        url=str(index),
        js_api=api,
        width=1480, height=920,
        min_size=(1100, 700),
        background_color="#0f1216",
    )

    def _on_start() -> None:
        try:
            window.maximize()
        except Exception:
            pass

    webview.start(_on_start, debug=bool(os.environ.get("WB_DEBUG")))


if __name__ == "__main__":
    main()
