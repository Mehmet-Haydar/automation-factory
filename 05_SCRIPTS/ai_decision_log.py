#!/usr/bin/env python3
"""
ai_decision_log.py — AI Decision Log (Phase 31, C-1 fix)

EU AI Act Article 12 Compliance — append-only audit log with SHA256 hash chain.

Design (C-1 fix):
  - Append-only: new records are appended with open("a"), never rewrite on log_ai_action.
  - Hash chain: each record stores prev_hash = SHA256 of the preceding raw line.
  - input/output hashes (SHA256) recorded instead of raw text — no PII in log.
  - approve_entry: signoff_name required; status must be "approved" or "rejected";
    free-text note lives in separate "note" field.
  - Fail-closed: if log_ai_action cannot write, it raises AuditLogError — callers
    must catch and surface this to the user; the AI call must NOT proceed silently.

Log format: one JSON object per line (JSONL), UTF-8.
  {
    "id": "L001",
    "step_label": "...",      (max 60 chars, stripped)
    "ai_model": "...",
    "ai_provider": "...",
    "prompt_id": "...",       (optional caller-supplied stable label)
    "input_hash": "sha256:...",   (SHA256 of the full prompt sent to AI)
    "output_hash": "sha256:...",  (SHA256 of the response received)
    "timestamp": "2026-05-28T14:30:00",
    "prev_hash": "sha256:...",    (SHA256 of the raw preceding JSONL line, or "GENESIS")
    "signoff": {              (absent / null until approved/rejected)
      "engineer": "...",
      "status": "approved" | "rejected",
      "at": "2026-05-28T15:00:00",
      "note": "..."           (optional free text)
    }
  }

Usage:
  from ai_decision_log import log_ai_action, approve_entry, read_log
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_FILENAME = "AI_DECISION_LOG.jsonl"

# Module-level lock: makes the read-compute-write steps inside log_ai_action
# and _append_signoff_record atomic so the SHA-256 hash chain is not corrupted
# by concurrent threads.
_LOG_LOCK = threading.Lock()

# Status values for approve_entry
SIGNOFF_STATUSES = {"approved", "rejected"}


class AuditLogError(RuntimeError):
    """Raised when the audit log cannot be written.

    Callers must NOT proceed with an AI call if this is raised — fail-closed.
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _parse_jsonl(log_path: Path) -> list[dict]:
    """Read all valid JSON lines from the log. Silently skips corrupt lines
    (they stay on disk — append-only; corruption is detectable by hash chain)."""
    if not log_path.exists():
        return []
    records: list[dict] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            # Corrupt line — leave on disk, skip in parse
            pass
    return records


def _last_raw_line(log_path: Path) -> Optional[str]:
    """Return the last non-empty raw line of the log file, or None."""
    if not log_path.exists():
        return None
    for line in reversed(log_path.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            return line.strip()
    return None


def _next_id(records: list[dict]) -> str:
    nums = []
    for r in records:
        eid = r.get("id", "")
        if re.match(r"^L\d{3,}$", eid):
            nums.append(int(eid[1:]))
    return f"L{(max(nums) + 1):03d}" if nums else "L001"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_ai_action(
    project_path: Path,
    step_label: str,
    ai_model: str = "manual/cursor",
    ai_provider: str = "-",
    prompt_text: str = "",
    output_text: str = "",
    prompt_id: str = "",
    full_prompt_text: Optional[str] = None,
) -> dict:
    """Append one AI action record to the audit log.

    Parameters
    ----------
    project_path : Path
        Root directory of the project (log file is placed here).
    step_label : str
        Human-readable step name (max 60 chars).
    ai_model : str
        Model identifier (e.g. "claude-sonnet-4-6").
    ai_provider : str
        Provider name (e.g. "anthropic").
    prompt_text : str
        Display excerpt of the prompt (may be truncated). Used for human
        review only — its content does NOT affect input_hash when
        full_prompt_text is provided.
    output_text : str
        Full response from the AI — only its SHA256 hash is stored.
    prompt_id : str
        Optional stable identifier for the prompt template.
    full_prompt_text : str | None
        When provided, input_hash is computed from this complete text
        (S-3 fix: audit hash must cover the exact bytes sent to the AI,
        not a display-truncated slice). prompt_text may still be a
        [:N] slice for display purposes. When None, falls back to
        hashing prompt_text (backward-compatible behaviour).

    Returns
    -------
    dict
        The newly appended record.

    Raises
    ------
    AuditLogError
        If the log directory is not writable or the write fails.
        Callers must NOT proceed with the AI call after this exception.
    """
    log_path = project_path / LOG_FILENAME

    # input_hash: always computed from the full (untruncated) prompt text.
    # If full_prompt_text is supplied, use it; otherwise fall back to
    # prompt_text (backward-compatible for callers that pass the full text
    # directly without truncation).
    _hash_source = full_prompt_text if full_prompt_text is not None else prompt_text

    with _LOG_LOCK:
        # Compute prev_hash from the last raw line on disk (chain integrity)
        last_line = _last_raw_line(log_path)
        prev_hash = _sha256(last_line) if last_line is not None else "GENESIS"

        # Determine next ID
        records = _parse_jsonl(log_path)
        entry_id = _next_id(records)

        record = {
            "id": entry_id,
            "step_label": step_label[:60].strip(),
            "ai_model": ai_model[:40].strip(),
            "ai_provider": ai_provider[:20].strip(),
            "prompt_id": prompt_id[:80].strip(),
            "input_hash": _sha256(_hash_source) if _hash_source else "",
            "output_hash": _sha256(output_text) if output_text else "",
            "timestamp": _now_iso(),
            "prev_hash": prev_hash,
            "signoff": None,
        }

        raw_line = json.dumps(record, ensure_ascii=False)

        try:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(raw_line + "\n")
        except OSError as exc:
            raise AuditLogError(
                f"AI audit log is not writable: {log_path} — {exc}. "
                "AI call blocked (EU AI Act Article 12 fail-closed)."
            ) from exc

    return record


def _last_line_hash(log_path: Path) -> str:
    last_line = _last_raw_line(log_path)
    return _sha256(last_line) if last_line is not None else "GENESIS"


def _peek_next_sequence(log_path: Path) -> int:
    records = _parse_jsonl(log_path)
    return int(_next_id(records)[1:])


def _existing_signoff_ref_ids(log_path: Path) -> set[str]:
    """Return ref_ids of all existing signoff records (for idempotency)."""
    out: set[str] = set()
    if not log_path.exists():
        return out
    for line in log_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "signoff" and rec.get("ref_id"):
            out.add(rec["ref_id"])
    return out


def _entry_exists(log_path: Path, entry_id: str) -> bool:
    if not log_path.exists():
        return False
    for line in log_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if rec.get("type") != "signoff" and rec.get("id") == entry_id:
            return True
    return False


def _append_signoff_record(
    project_path: Path,
    ref_id: str,
    engineer_name: str,
    status: str,
    note: str,
) -> dict:
    """Append a signoff record as a NEW chained entry (FSA-003 fix).

    Sign-off is itself an append-only audit event — it does NOT rewrite the
    original record's bytes. This preserves the SHA256 hash chain across
    sign-off operations.
    """
    log_path = project_path / LOG_FILENAME
    with _LOG_LOCK:
        prev_hash = _last_line_hash(log_path)
        next_seq = _peek_next_sequence(log_path)

        record = {
            "id": f"L{next_seq:03d}",
            "type": "signoff",
            "ref_id": ref_id,
            "at": _now_iso(),
            "engineer": engineer_name,
            "status": status,
            "note": note,
            "prev_hash": prev_hash,
        }
        raw_line = json.dumps(record, ensure_ascii=False)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(raw_line + "\n")
        except OSError as exc:
            raise AuditLogError(
                f"AI audit log is not writable: {log_path} — {exc}. "
                "Sign-off blocked (EU AI Act Article 12 fail-closed)."
            ) from exc
    return record


def approve_entry(
    project_path: Path,
    entry_id: str,
    engineer_name: str,
    status: str,
    note: str = "",
) -> bool:
    """Append an engineer sign-off as a new chained record (FSA-003).

    Sign-off is itself an append-only event linked by hash chain. The
    referenced original record is never modified, so verify_chain() stays
    intact across sign-off operations.

    Returns True when a NEW signoff record was appended; False when the
    referenced entry does not exist or is already signed off.
    """
    engineer_name = engineer_name.strip()
    status = status.strip().lower()
    if not engineer_name:
        raise ValueError("engineer_name must not be empty for approve_entry")
    if status not in SIGNOFF_STATUSES:
        raise ValueError(
            f"status must be one of {sorted(SIGNOFF_STATUSES)!r}, got {status!r}"
        )

    log_path = project_path / LOG_FILENAME
    if not _entry_exists(log_path, entry_id):
        return False
    if entry_id in _existing_signoff_ref_ids(log_path):
        return False

    _append_signoff_record(project_path, entry_id, engineer_name, status, note.strip())
    return True


def approve_all_pending(
    project_path: Path,
    engineer_name: str,
    status: str = "approved",
    note: str = "",
) -> int:
    """Append signoff records for every unsigned non-signoff entry (FSA-003).

    Each signoff is its own chained append; original records are not rewritten.
    Returns the count of newly appended signoff records.
    """
    engineer_name = engineer_name.strip()
    status = status.strip().lower()
    if not engineer_name:
        raise ValueError("engineer_name must not be empty for approve_all_pending")
    if status not in SIGNOFF_STATUSES:
        raise ValueError(
            f"status must be one of {sorted(SIGNOFF_STATUSES)!r}, got {status!r}"
        )

    log_path = project_path / LOG_FILENAME
    if not log_path.exists():
        return 0

    existing_signoffs = _existing_signoff_ref_ids(log_path)
    pending_ids: list[str] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "signoff":
            continue
        rid = rec.get("id")
        if rid and rid not in existing_signoffs:
            pending_ids.append(rid)

    count = 0
    for rid in pending_ids:
        _append_signoff_record(project_path, rid, engineer_name, status, note.strip())
        count += 1
    return count


def read_log(project_path: Path) -> list[dict]:
    """Return parsed records with sign-offs merged onto their referenced entries.

    Signoff records (type=="signoff") are removed from the output and their
    payload is attached to the referenced original record's ``signoff`` field
    — keeping the public read shape stable across FSA-003 (where signoffs
    moved from in-place patches to append-only chained records).
    """
    records = _parse_jsonl(project_path / LOG_FILENAME)
    signoffs_by_ref: dict[str, dict] = {}
    for rec in records:
        if rec.get("type") == "signoff" and rec.get("ref_id"):
            signoffs_by_ref[rec["ref_id"]] = {
                "engineer": rec.get("engineer", ""),
                "status": rec.get("status", ""),
                "at": rec.get("at", ""),
                "note": rec.get("note", ""),
            }
    out: list[dict] = []
    for rec in records:
        if rec.get("type") == "signoff":
            continue
        rid = rec.get("id")
        if rid and rid in signoffs_by_ref:
            rec = {**rec, "signoff": signoffs_by_ref[rid]}
        out.append(rec)
    return out


def verify_chain(project_path: Path) -> list[str]:
    """Verify the SHA256 hash chain. Returns a list of violation messages
    (empty list = chain intact)."""
    log_path = project_path / LOG_FILENAME
    if not log_path.exists():
        return []

    violations: list[str] = []
    raw_lines = [
        line for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    prev_raw: Optional[str] = None
    for i, raw in enumerate(raw_lines):
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            violations.append(f"Line {i+1}: JSON parse error — possible tampering")
            prev_raw = raw
            continue

        stored_prev = rec.get("prev_hash", "")
        if prev_raw is None:
            expected = "GENESIS"
        else:
            expected = _sha256(prev_raw)

        if stored_prev != expected:
            violations.append(
                f"Line {i+1} id={rec.get('id','?')}: prev_hash mismatch "
                f"(stored={stored_prev!r}, expected={expected!r})"
            )
        prev_raw = raw

    return violations


def format_log_summary(project_path: Path) -> str:
    """Return a human-readable summary of the audit log."""
    records = read_log(project_path)
    if not records:
        return "AI Decision Log is empty — it fills as pipeline steps complete."

    total = len(records)
    approved = sum(1 for r in records if (r.get("signoff") or {}).get("status") == "approved")
    rejected = sum(1 for r in records if (r.get("signoff") or {}).get("status") == "rejected")
    pending = total - approved - rejected

    lines = [
        f"Total entries : {total}",
        f"  Approved    : {approved}",
        f"  Rejected    : {rejected}",
        f"  Pending     : {pending}",
    ]
    if pending:
        lines.append("\nSteps pending sign-off:")
        for r in records:
            if not r.get("signoff"):
                lines.append(
                    f"  {r['id']}  {r.get('step_label','?')[:50]}  ({r.get('timestamp','')})"
                )

    chain_errors = verify_chain(project_path)
    if chain_errors:
        lines.append("\nHASH CHAIN VIOLATIONS (possible tampering):")
        for err in chain_errors:
            lines.append(f"  ! {err}")

    return "\n".join(lines)
