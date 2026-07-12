#!/usr/bin/env python3
"""
code_verifier.py — SCL Code Verification + Repair Loop Engine (Phase 26)

Implements Generate -> Verify -> Repair closed loop.

Verification tool chain (priority order):
  1. PLCreX   (pip install plcrex  — skipped if not installed)
  2. Builtin  (scl_validator.py    — always available)

Siemens SCL is a superset of IEC 61131-3. Siemens-specific extensions
are normalized before sending to PLCreX.

CLI:
  python code_verifier.py FILE.scl
  python code_verifier.py --project PROJECT_PATH [--repair --max-iter 3]
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


FACTORY_ROOT = Path(__file__).resolve().parent.parent


# -- Data structures ----------------------------------------------------------

@dataclass
class VerificationIssue:
    line: int           # 0 = file level
    message: str
    severity: str = "error"   # error / warning / info


@dataclass
class VerificationResult:
    tool: str                                    # "plcrex" / "builtin" / "none"
    issues: list[VerificationIssue] = field(default_factory=list)
    scl_content: str = ""

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def error_lines(self) -> list[str]:
        return [
            f"[line {i.line}] {i.message}" if i.line > 0 else i.message
            for i in self.issues
            if i.severity == "error"
        ]

    def summary(self) -> str:
        if not self.issues:
            return f"[OK] {self.tool}: no errors"
        return (f"{'[FAIL]' if self.has_errors else '[WARN]'} "
                f"{self.tool}: {self.error_count} errors, {self.warning_count} warnings")


# -- Siemens SCL -> IEC 61131-3 Normalizer ------------------------------------

# Siemens-specific attribute tags (single-line and multi-line)
_ATTR_BLOCK_RE   = re.compile(r'\{[^{}]*\}', re.DOTALL)
_REGION_OPEN_RE  = re.compile(r'^\s*REGION\b.*$', re.IGNORECASE | re.MULTILINE)
_REGION_CLOSE_RE = re.compile(r'^\s*END_REGION\b.*$', re.IGNORECASE | re.MULTILINE)
# Siemens data types -> temporary IEC equivalent
_TYPE_MAP = [
    (re.compile(r'\bLTIME_OF_DAY\b', re.IGNORECASE), "TIME_OF_DAY"),
    (re.compile(r'\bLTIME\b',        re.IGNORECASE), "TIME"),
    (re.compile(r'\bLWORD\b',        re.IGNORECASE), "DWORD"),
    (re.compile(r'\bVARIANT\b',      re.IGNORECASE), "ANY"),
]


def normalize_for_iec(content: str) -> str:
    """Simple normalizer from Siemens SCL to IEC 61131-3-compatible ST."""
    # Remove {attribute := 'value'} blocks
    content = _ATTR_BLOCK_RE.sub('', content)
    # REGION / END_REGION -> blank line
    content = _REGION_OPEN_RE.sub('', content)
    content = _REGION_CLOSE_RE.sub('', content)
    # Type mappings
    for pat, repl in _TYPE_MAP:
        content = pat.sub(repl, content)
    return content


# -- PLCreX Integration -------------------------------------------------------

def _plcrex_available() -> bool:
    """Check whether the PLCreX command-line tool is installed."""
    try:
        result = subprocess.run(
            ["plcrex", "--version"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _parse_plcrex_output(output: str) -> list[VerificationIssue]:
    """Convert PLCreX output into a list of VerificationIssue."""
    issues: list[VerificationIssue] = []
    # Typical PLCreX output format: "error: file.st:10:5: message" or "warning: ..."
    line_re = re.compile(
        r'(?P<sev>error|warning|note):\s*[^:]*:(?P<lineno>\d+):.*?:\s*(?P<msg>.+)',
        re.IGNORECASE,
    )
    for raw_line in output.splitlines():
        m = line_re.search(raw_line)
        if m:
            sev = "error" if m.group("sev").lower() == "error" else "warning"
            issues.append(VerificationIssue(
                line=int(m.group("lineno")),
                message=m.group("msg").strip(),
                severity=sev,
            ))
        elif "error" in raw_line.lower() and raw_line.strip():
            issues.append(VerificationIssue(0, raw_line.strip(), "error"))
    return issues


def verify_with_plcrex(content: str) -> Optional[VerificationResult]:
    """
    Verify with PLCreX.
    Returns None if PLCreX is not installed (caller should fall back to builtin).
    """
    if not _plcrex_available():
        return None

    normalized = normalize_for_iec(content)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".st", delete=False
    ) as tmp:
        tmp.write(normalized)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["plcrex", "--check", tmp_path],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        raw_out = result.stdout + "\n" + result.stderr
        issues = _parse_plcrex_output(raw_out)

        # returncode 0 with no output -> clean
        if result.returncode == 0 and not issues:
            return VerificationResult(tool="plcrex", issues=[], scl_content=content)

        return VerificationResult(tool="plcrex", issues=issues, scl_content=content)

    except subprocess.TimeoutExpired:
        return VerificationResult(
            tool="plcrex",
            issues=[VerificationIssue(0, "PLCreX timed out (>30s)", "warning")],
            scl_content=content,
        )
    except Exception as e:
        return VerificationResult(
            tool="plcrex",
            issues=[VerificationIssue(0, f"Could not run PLCreX: {e}", "warning")],
            scl_content=content,
        )
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


# -- Builtin Validator (always available) -------------------------------------

def verify_with_builtin(content: str) -> VerificationResult:
    """Builtin validator based on scl_validator.py."""
    try:
        from scl_validator import validate_scl
        res = validate_scl(content)
        return VerificationResult(
            tool="builtin",
            issues=[
                VerificationIssue(i.line, i.message, i.severity)
                for i in res.issues
            ],
            scl_content=content,
        )
    except ImportError:
        return VerificationResult(
            tool="none",
            issues=[VerificationIssue(0, "scl_validator.py not found", "warning")],
            scl_content=content,
        )


# -- Main entry point ---------------------------------------------------------

def verify(content: str) -> VerificationResult:
    """
    Verify with the best available tool.
    Use PLCreX if available, otherwise fall back to the builtin validator.
    """
    plcrex = verify_with_plcrex(content)
    if plcrex is not None:
        return plcrex
    return verify_with_builtin(content)


def verify_file(path: Path) -> VerificationResult:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return VerificationResult(
            tool="none",
            issues=[VerificationIssue(0, f"Could not read file: {e}", "error")],
        )
    return verify(content)


# -- SCL Extraction (MD -> raw SCL) -------------------------------------------

_SCL_FENCE_RE = re.compile(
    r"```[ \t]*(?:scl|iec|iec61131|st|structured[ \t]+text)[ \t]*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def extract_scl_from_md(md_content: str) -> list[str]:
    """Extract ```scl ... ``` blocks from markdown text."""
    return [m.group(1).strip() for m in _SCL_FENCE_RE.finditer(md_content)
            if len(m.group(1).strip()) > 20]


def verify_md_content(md_content: str) -> Optional[VerificationResult]:
    """
    Verify the SCL blocks inside an AI response.
    Returns None if there is no SCL.
    """
    blocks = extract_scl_from_md(md_content)
    if not blocks:
        return None

    # Verify all blocks combined (there can be multiple)
    combined = "\n\n".join(blocks)
    return verify(combined)


# -- Repair Prompt Builder ----------------------------------------------------

REPAIR_SYSTEM_PROMPT = """\
You are an IEC 61131-3 Structured Control Language (SCL/ST) expert.
You will be given a list of detected errors in some SCL code, plus the original code.
Your task: fix all the errors and produce complete, compilable SCL code.

Rules:
1. Your answer must contain ONLY the fixed SCL code (inside a ```scl ... ``` block).
2. Preserve the original logic and variable names.
3. Add missing END_IF / END_FOR / END_WHILE / END_FUNCTION_BLOCK.
4. Add undefined variables to a VAR_TEMP block.
5. Do NOT write any explanation, summary, or extra text.
"""


def build_repair_prompt(original_scl: str, errors: list[str]) -> str:
    error_block = "\n".join(f"- {e}" for e in errors)
    return (
        f"{len(errors)} errors were detected in the SCL code below:\n\n"
        f"**Errors:**\n{error_block}\n\n"
        f"**Original Code:**\n```scl\n{original_scl}\n```\n\n"
        "Fix all errors and regenerate the complete SCL code inside a ```scl ... ``` block."
    )


# -- Repair Loop --------------------------------------------------------------

@dataclass
class RepairSession:
    iterations: int = 0
    max_iterations: int = 3
    original_scl: str = ""
    current_scl: str = ""
    proposed_scl: str = ""   # AI proposal when auto_apply=False
    diff: str = ""            # unified diff of proposed vs current when auto_apply=False
    history: list[VerificationResult] = field(default_factory=list)
    final_result: Optional[VerificationResult] = None
    repaired: bool = False


def _simple_diff(a: str, b: str) -> str:
    """Minimal line-level diff (--- / +++ format, no external deps)."""
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    out = ["--- current\n", "+++ proposed\n"]
    import difflib
    out.extend(difflib.unified_diff(a_lines, b_lines, lineterm=""))
    return "".join(out)


def repair_loop(
    scl_content: str,
    ai_call_fn,               # fn(system_prompt, user_msg) -> (response_text, usage)
    max_iterations: int = 3,
    on_iteration: Optional[callable] = None,  # fn(iter_no, result, repaired_scl)
    auto_apply: bool = False,
) -> RepairSession:
    """
    Closed-loop repair engine.

    auto_apply=False (default): after the first AI repair, the proposed SCL is stored
    in session.proposed_scl and session.diff — current_scl is NOT modified.
    The caller must review and apply the proposal explicitly.

    auto_apply=True: legacy behaviour — current_scl is updated in-place each iteration.

    ai_call_fn(system, user) -> (response_str, usage_obj)
    on_iteration(iter_no, result, current_scl) -> None   (progress callback)
    """
    session = RepairSession(
        max_iterations=max_iterations,
        original_scl=scl_content,
        current_scl=scl_content,
    )

    for iteration in range(1, max_iterations + 1):
        session.iterations = iteration

        # Verify
        result = verify(session.current_scl)
        session.history.append(result)
        session.final_result = result

        if on_iteration:
            on_iteration(iteration, result, session.current_scl)

        # Stop if no errors
        if not result.has_errors:
            session.repaired = (iteration > 1)
            break

        # Exit if there are still errors on the last iteration
        if iteration == max_iterations:
            break

        # Build the repair prompt and send to the AI
        errors = result.error_lines()
        repair_msg = build_repair_prompt(session.current_scl, errors)

        try:
            response, _usage = ai_call_fn(REPAIR_SYSTEM_PROMPT, repair_msg)
        except Exception as e:
            session.final_result = VerificationResult(
                tool="none",
                issues=[VerificationIssue(0, f"Repair AI call failed: {e}", "error")],
            )
            break

        # Extract the SCL from the response
        repaired_blocks = extract_scl_from_md(response)
        candidate = repaired_blocks[0] if repaired_blocks else response.strip()

        if auto_apply:
            session.current_scl = candidate
        else:
            session.proposed_scl = candidate
            session.diff = _simple_diff(session.current_scl, candidate)
            break  # surface proposal; caller decides whether to apply

    return session


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="SCL Code Verifier")
    p.add_argument("file", nargs="?", help=".scl file")
    p.add_argument("--project", metavar="PROJECT_PATH")
    args = p.parse_args()

    if args.file:
        result = verify_file(Path(args.file))
        print(result.summary())
        for i in result.issues:
            sev = {"error": "x", "warning": "!", "info": "."}.get(i.severity, ".")
            loc = f"[{i.line}] " if i.line else ""
            print(f"  {sev} {loc}{i.message}")
        print(f"\nTool: {result.tool}  "
              f"| PLCreX: {'installed' if _plcrex_available() else 'not installed'}")
        sys.exit(0 if not result.has_errors else 1)

    if args.project:
        scl_dir = Path(args.project) / "_output" / "scl"
        if not scl_dir.exists():
            print(f"_output/scl/ not found: {scl_dir}")
            sys.exit(1)
        total_errors = 0
        for scl_file in sorted(scl_dir.glob("*.scl")):
            res = verify_file(scl_file)
            print(f"{res.summary()}  ({scl_file.name})")
            total_errors += res.error_count
        print(f"\nTotal errors: {total_errors}  |  Tool: "
              f"{'plcrex' if _plcrex_available() else 'builtin'}")
        sys.exit(0 if total_errors == 0 else 1)

    p.print_help()


if __name__ == "__main__":
    main()
