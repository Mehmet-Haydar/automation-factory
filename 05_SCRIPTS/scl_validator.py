#!/usr/bin/env python3
"""
scl_validator.py — IEC 61131-3 SCL Basic Syntax Validator (Phase 25)

Checks the block structure of generated SCL code before loading into TIA Portal.
Supported checks:
  - FUNCTION_BLOCK / END_FUNCTION_BLOCK
  - FUNCTION / END_FUNCTION
  - ORGANIZATION_BLOCK / END_ORGANIZATION_BLOCK
  - IF / END_IF  |  FOR / END_FOR  |  WHILE / END_WHILE  |  CASE / END_CASE
  - VAR* / END_VAR (all variants)
  - TYPE / END_TYPE  |  STRUCT / END_STRUCT  |  REGION / END_REGION
  - Parenthesis balance ( / )

CLI:
  python scl_validator.py <file_or_folder.scl>
  python scl_validator.py --project PROJECT_PATH
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ValidationIssue:
    line: int           # 0 = file-level issue
    message: str
    severity: str = "error"  # error / warning / info
    keyword: str = ""


SCOPE_WARNING = (
    "UYARI — Yalnizca yapisal kontrol (keyword dengesi, parantez). "
    "Semantik, tip ve guvenlik mantigi DOGRULANMADI."
)

@dataclass
class FileResult:
    path: Path
    issues: list[ValidationIssue] = field(default_factory=list)
    scope: str = "structural_only"
    scope_warning: str = SCOPE_WARNING

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# -- Comment stripping --------------------------------------------------------

def strip_comments(content: str) -> str:
    """Replace // and (* *) comments with whitespace, preserving line structure.

    N-W5 fix: SCL string literals ('...') are now tracked.  While inside a
    string literal the comment-scanner is suspended so that keywords inside
    the string (e.g. myStr := 'END_IF;') are replaced with spaces and never
    counted by the keyword-balance checks.  A single-quote inside a string is
    escaped by doubling it ('' per IEC 61131-3); the state machine handles
    this correctly.
    """
    result: list[str] = []
    i = 0
    n = len(content)
    in_block  = False   # inside (* ... *) block comment
    in_string = False   # inside '...' string literal

    while i < n:
        ch = content[i]

        if in_string:
            # IEC 61131-3: a doubled single-quote '' is an escaped quote inside
            # the string — it does NOT end the literal.
            if ch == "'" and content[i:i+2] == "''":
                result.append("  ")   # mask both chars
                i += 2
            elif ch == "'":
                in_string = False
                result.append(" ")    # mask closing quote
                i += 1
            else:
                # Mask all string content so keywords inside are invisible
                result.append("\n" if ch == "\n" else " ")
                i += 1
        elif in_block:
            if content[i:i+2] == "*)":
                in_block = False
                result.append("  ")
                i += 2
            else:
                result.append("\n" if ch == "\n" else " ")
                i += 1
        else:
            if ch == "'":
                # Start of string literal — suspend comment scanning
                in_string = True
                result.append(" ")   # mask opening quote
                i += 1
            elif content[i:i+2] == "(*":
                in_block = True
                result.append("  ")
                i += 2
            elif content[i:i+2] == "//":
                # Whitespace until end of line
                while i < n and content[i] != "\n":
                    result.append(" ")
                    i += 1
            else:
                result.append(ch)
                i += 1

    return "".join(result)


def _count(text: str, kw: str) -> int:
    return len(re.findall(r"\b" + kw + r"\b", text, re.IGNORECASE))


# -- Stack-based nesting validation -------------------------------------------

# Opener→closer pairs that must nest correctly (order matters: longer tokens first
# so that END_FUNCTION_BLOCK is not consumed as END_FUNCTION).
_NESTING_PAIRS: list[tuple[str, str]] = [
    ("FUNCTION_BLOCK",     "END_FUNCTION_BLOCK"),
    ("ORGANIZATION_BLOCK", "END_ORGANIZATION_BLOCK"),
    ("FUNCTION",           "END_FUNCTION"),
    ("IF",                 "END_IF"),
    ("FOR",                "END_FOR"),
    ("WHILE",              "END_WHILE"),
    ("CASE",               "END_CASE"),
]

# Combined tokeniser: matches any opener or closer as a whole word.
_NESTING_OPENERS  = {p[0].upper() for p in _NESTING_PAIRS}
_NESTING_CLOSERS  = {p[1].upper() for p in _NESTING_PAIRS}
_OPENER_TO_CLOSER = {p[0].upper(): p[1].upper() for p in _NESTING_PAIRS}
_CLOSER_TO_OPENER = {p[1].upper(): p[0].upper() for p in _NESTING_PAIRS}

# Build a single regex that matches any of the keyword tokens (word-bounded).
# Longer tokens must appear before shorter prefixes (FUNCTION_BLOCK before FUNCTION).
_ALL_KW_SORTED = sorted(
    list(_NESTING_OPENERS) + list(_NESTING_CLOSERS),
    key=lambda s: -len(s),   # longest first to avoid prefix shadowing
)
_NESTING_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _ALL_KW_SORTED) + r")\b",
    re.IGNORECASE,
)


def _balanced_stack(clean: str) -> list[str]:
    """Return a list of nesting error descriptions (empty = no errors).

    N-W6 fix: instead of counting openers and closers independently, we walk
    the token stream with a stack.  This catches wrong-order nesting such as
    IF .. FOR .. END_IF .. END_FOR which balances numerically but is structurally
    invalid in IEC 61131-3 SCL.

    Rules:
      - Opener → push expected closer onto the stack.
      - Closer → pop the stack; if the top does not match, report a mismatch.
      - Closer with empty stack → report unexpected closer.
      - Non-empty stack at EOF → report each unclosed opener.
    """
    errors: list[str] = []
    stack: list[str] = []   # each entry is the expected closer

    for m in _NESTING_RE.finditer(clean):
        token = m.group(1).upper()

        if token in _NESTING_OPENERS:
            expected_close = _OPENER_TO_CLOSER[token]
            stack.append(expected_close)

        elif token in _NESTING_CLOSERS:
            if not stack:
                errors.append(
                    f"Unexpected {token} — no matching opener"
                )
            else:
                top = stack[-1]
                if token == top:
                    stack.pop()
                else:
                    # Wrong closer — report and pop anyway to keep scanning
                    stack.pop()
                    errors.append(
                        f"Nesting mismatch: expected {top} but found {token} "
                        f"(opened by {_CLOSER_TO_OPENER.get(top, '?')})"
                    )

    # Anything left on the stack is unclosed
    for unclosed in reversed(stack):
        opener = _CLOSER_TO_OPENER.get(unclosed, "?")
        errors.append(f"Unclosed {opener} — missing {unclosed}")

    return errors


# -- Block pairs --------------------------------------------------------------

# (opener_keyword, closer_keyword) — order does not matter, matched with \b
BLOCK_PAIRS: list[tuple[str, str]] = [
    ("FUNCTION_BLOCK",     "END_FUNCTION_BLOCK"),
    ("FUNCTION",           "END_FUNCTION"),
    ("ORGANIZATION_BLOCK", "END_ORGANIZATION_BLOCK"),
    ("TYPE",               "END_TYPE"),
    ("STRUCT",             "END_STRUCT"),
    ("IF",                 "END_IF"),
    ("FOR",                "END_FOR"),
    ("WHILE",              "END_WHILE"),
    ("CASE",               "END_CASE"),
    ("REGION",             "END_REGION"),
]

# END_VAR can close multiple VAR blocks — check the total equality
VAR_OPENERS: list[str] = [
    "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT",
    "VAR_TEMP", "VAR_STAT", "VAR_GLOBAL", "VAR",
]


# -- Guard-overwrite detection (STRUCTURAL_BUG) --------------------------------

_IF_RE        = re.compile(r"\bIF\b", re.IGNORECASE)
_END_IF_RE    = re.compile(r"\bEND_IF\b", re.IGNORECASE)
_ELSE_RE      = re.compile(r"\bELSE\b(?!IF)", re.IGNORECASE)  # ELSIF hariç: negative lookahead
_STEP_RE      = re.compile(r"\b\w*[sS]tep\w*\s*:=", re.IGNORECASE)
_FALSE_ASSIGN = re.compile(r"\b(\w+)\s*:=\s*FALSE\b", re.IGNORECASE)
_CASE_LABEL   = re.compile(r"^\s*(\d+|ELSE)\s*:", re.IGNORECASE)


def _check_guard_overwrite(clean: str) -> list[ValidationIssue]:
    """Detect the StarDelta step-10 bug class (2026-06-09 audit, finding 2).

    Pattern: inside a CASE step, a stop/abort guard IF-block sets outputs
    FALSE and changes the step, but has no ELSE — and the lines that follow
    it (still in the same step, before the next IF/label) unconditionally
    re-assign one of those same outputs TRUE.  The guard is then overwritten
    in the same PLC scan, so the stop never takes effect.

    Heuristic, line-based: works on comment-stripped text so string/comment
    content can't fool it.  Only IF-blocks that BOTH assign something FALSE
    and write a *step* variable are treated as guards, which keeps false
    positives low.
    """
    issues: list[ValidationIssue] = []
    lines = clean.splitlines()
    n = len(lines)
    i = 0

    while i < n:
        line = lines[i]
        if not _IF_RE.search(line) or _END_IF_RE.search(line):
            i += 1
            continue

        # Walk the IF-block, tracking nesting depth and top-level ELSE.
        depth = 0
        has_top_else = False
        guard_false_vars: set[str] = set()
        guard_sets_step = False
        j = i
        end_line = None
        while j < n:
            l = lines[j]
            closes = len(_END_IF_RE.findall(l))
            if _END_IF_RE.search(l):
                depth -= closes
                if depth <= 0:
                    end_line = j
                    break
            if _IF_RE.search(l) and not _END_IF_RE.search(l):
                depth += 1
            if depth == 1:
                if _ELSE_RE.search(l):
                    has_top_else = True
                if _STEP_RE.search(l) and not l.strip().upper().startswith("IF"):
                    guard_sets_step = True
                for m in _FALSE_ASSIGN.finditer(l):
                    guard_false_vars.add(m.group(1).lower())
            j += 1

        if end_line is None:           # unbalanced — other checks report it
            break

        if not has_top_else and guard_sets_step and guard_false_vars:
            # Scan the unconditional tail: same step, after END_IF, until the
            # next IF / CASE label / END_CASE.
            k = end_line + 1
            while k < n:
                tail = lines[k]
                up = tail.upper()
                if (_CASE_LABEL.match(tail) or _IF_RE.search(tail)
                        or "END_CASE" in up or "CASE" in up.split()):
                    break
                for var in guard_false_vars:
                    if re.search(r"\b" + re.escape(var) + r"\s*:=\s*TRUE\b",
                                 tail, re.IGNORECASE):
                        issues.append(ValidationIssue(
                            line=k + 1,
                            message=(
                                f"STRUCTURAL_BUG: '{var}' is set TRUE unconditionally "
                                f"right after a stop-guard (line {i + 1}) that set it "
                                "FALSE — the guard is overwritten in the same scan. "
                                "Move the assignment into the guard's ELSE branch."
                            ),
                            severity="error", keyword="STRUCTURAL_BUG",
                        ))
                k += 1

        i = end_line + 1

    return issues


# -- Main validation ----------------------------------------------------------

def validate_scl(content: str, path: Optional[Path] = None) -> FileResult:
    result = FileResult(path=path or Path("<string>"))
    clean = strip_comments(content)

    # -- 1. Block balance -----------------------------------------------------
    for open_kw, close_kw in BLOCK_PAIRS:
        opens  = _count(clean, open_kw)
        closes = _count(clean, close_kw)

        # Note: \b word boundaries mean END_FUNCTION does NOT match inside
        # END_FUNCTION_BLOCK (underscore is a word char, so no boundary at N_).
        # No subtraction needed — the regex already handles this correctly.

        if opens != closes:
            diff = opens - closes
            if diff > 0:
                result.issues.append(ValidationIssue(
                    line=0,
                    message=f"{open_kw}: {opens} openers, only {closes} closers (missing END_{open_kw.replace('ORGANIZATION_', 'ORG_')}: {diff})",
                    severity="error", keyword=open_kw,
                ))
            else:
                result.issues.append(ValidationIssue(
                    line=0,
                    message=f"{close_kw}: {closes} closers but only {opens} openers (extra closers: {-diff})",
                    severity="error", keyword=open_kw,
                ))

    # -- 1a. Guard-overwrite / STRUCTURAL_BUG (2026-06-09 audit) ----------------
    result.issues.extend(_check_guard_overwrite(clean))

    # -- 1b. Stack-based nesting (N-W6) ----------------------------------------
    # This catches wrong-order nesting that the count-based check above misses
    # (e.g. IF..FOR..END_IF..END_FOR — counts balance but structure is invalid).
    for nesting_error in _balanced_stack(clean):
        result.issues.append(ValidationIssue(
            line=0,
            message=f"Nesting error: {nesting_error}",
            severity="error", keyword="NESTING",
        ))

    # -- 1c. Block-comment hazard (2026-06-10 TIA V19 import test) -------------
    # TIA's source parser ends a (* *) comment at the FIRST "*)" — text like
    # "(iDB_*)" inside the comment closes it early and the rest of the comment
    # is parsed as code ("Syntax error: '.'", "'DRAFT' invalid"). Generated
    # SCL must therefore use // line comments only.
    for lineno, raw in enumerate(content.splitlines(), start=1):
        if "(*" in raw:
            result.issues.append(ValidationIssue(
                line=lineno,
                message="(* *) block comment — use // line comments in generated "
                        "SCL; text like '(iDB_*)' closes the comment early and "
                        "TIA parses the rest as code",
                severity="warning", keyword="BLOCK_COMMENT",
            ))
    for lineno, cl in enumerate(clean.splitlines(), start=1):
        if "*)" in cl:
            result.issues.append(ValidationIssue(
                line=lineno,
                message="Stray '*)' outside any comment — a (* *) block comment "
                        "probably closed early (nested '*)' in the comment text); "
                        "TIA will reject this source",
                severity="error", keyword="BLOCK_COMMENT",
            ))

    # -- 1d. Statement-free bodies (2026-06-10 live TIA V19 compile) -----------
    # TIA's external-source compiler refuses an IF body without a single
    # statement (comments do not count): "Compound part of instruction
    # expected" — reported at the END of the enclosing construct, far from
    # the culprit (FB_Watchdog cost a 6-variant live bisect). A bare ';'
    # no-op makes the body legal.
    for m in re.finditer(r"\bTHEN\s*(?:END_IF|ELSIF|ELSE)\b", clean):
        result.issues.append(ValidationIssue(
            line=clean.count("\n", 0, m.start()) + 1,
            message="Statement-free IF body (comments don't count) — TIA "
                    "external-source compile fails with 'Compound part of "
                    "instruction expected'; add a bare ';' no-op or a real "
                    "statement",
            severity="error", keyword="EMPTY_BODY",
        ))
    for m in re.finditer(
            r"\bELSE\s*END_(?:IF|CASE)\b|\bDO\s*END_(?:WHILE|FOR)\b", clean):
        result.issues.append(ValidationIssue(
            line=clean.count("\n", 0, m.start()) + 1,
            message="Statement-free ELSE/loop body — same TIA hazard as the "
                    "EMPTY_BODY IF rule; add a ';' no-op or a real statement",
            severity="warning", keyword="EMPTY_BODY",
        ))

    # -- 2. VAR balance -------------------------------------------------------
    total_var_opens = sum(_count(clean, kw) for kw in VAR_OPENERS)
    total_end_var   = _count(clean, "END_VAR")

    if total_var_opens != total_end_var:
        diff = total_var_opens - total_end_var
        if diff > 0:
            result.issues.append(ValidationIssue(
                line=0,
                message=f"VAR blocks: {total_var_opens} openers, {total_end_var} END_VAR (missing: {diff})",
                severity="error", keyword="VAR",
            ))
        else:
            result.issues.append(ValidationIssue(
                line=0,
                message=f"VAR blocks: {total_var_opens} openers but {total_end_var} END_VAR (extra: {-diff})",
                severity="error", keyword="VAR",
            ))

    # -- 3. Parenthesis balance -----------------------------------------------
    opens_p  = clean.count("(")
    closes_p = clean.count(")")
    if opens_p != closes_p:
        result.issues.append(ValidationIssue(
            line=0,
            message=f"Parenthesis balance off: {opens_p} '(' — {closes_p} ')' (diff: {opens_p - closes_p:+d})",
            severity="warning", keyword="PAREN",
        ))

    # -- 4. Line-level warnings -----------------------------------------------
    lines = content.splitlines()
    clean_lines = clean.splitlines()

    for lineno, (raw, cl) in enumerate(zip(lines, clean_lines), start=1):
        cl_up = cl.upper().strip()

        # Missing semicolon after assignment? (simple heuristic)
        if ":=" in cl and not cl.rstrip().endswith(";") and not cl.rstrip().endswith("("):
            # Only warn on long lines, for multi-line assignments
            if "END_" not in cl_up and len(cl.strip()) > 5 and not cl_up.startswith("//"):
                result.issues.append(ValidationIssue(
                    line=lineno,
                    message="':=' statement may not end with ';' — ignore if it is a multi-line assignment",
                    severity="info", keyword="SEMICOLON",
                ))

        # Empty BEGIN block?
        if cl_up == "BEGIN":
            if lineno < len(clean_lines) and clean_lines[lineno].upper().strip().startswith("END_"):
                result.issues.append(ValidationIssue(
                    line=lineno,
                    message="Empty BEGIN block — no content",
                    severity="warning", keyword="BEGIN",
                ))

    # -- 5. No FB/FC/OB at all ------------------------------------------------
    has_block = (
        _count(clean, "FUNCTION_BLOCK") > 0
        or _count(clean, "FUNCTION") > 0
        or _count(clean, "ORGANIZATION_BLOCK") > 0
    )
    if not has_block and len(content.strip()) > 50:
        result.issues.append(ValidationIssue(
            line=0,
            message="No FUNCTION_BLOCK / FUNCTION / ORGANIZATION_BLOCK found in the SCL file",
            severity="warning", keyword="STRUCTURE",
        ))

    return result


def validate_scl_file(path: Path) -> FileResult:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        res = FileResult(path=path)
        res.issues.append(ValidationIssue(0, f"Could not read file: {e}", "error"))
        return res
    return validate_scl(content, path)


def scan_project_for_scl(project_path: Path) -> list[FileResult]:
    """Validate all .scl files in the project's _output/ folder."""
    results = []
    output_dir = project_path / "_output"
    if not output_dir.exists():
        return results
    for scl_file in sorted(output_dir.rglob("*.scl")):
        results.append(validate_scl_file(scl_file))
    return results


def format_result(res: FileResult, show_info: bool = False) -> str:
    lines = []
    icon = "[FAIL]" if res.has_errors else ("[WARN]" if res.warning_count else "[OK]")
    lines.append(f"{icon} {res.path.name}  ({res.error_count} errors, {res.warning_count} warnings)")

    for issue in res.issues:
        if issue.severity == "info" and not show_info:
            continue
        sev_icon = {"error": "  x", "warning": "  !", "info": "  ."}[issue.severity]
        loc = f"[line {issue.line}] " if issue.line > 0 else ""
        lines.append(f"{sev_icon} {loc}{issue.message}")

    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="SCL Syntax Validator")
    p.add_argument("target", nargs="?", help=".scl file or folder")
    p.add_argument("--project", metavar="PROJECT_PATH", help="Scan the project _output/ folder")
    p.add_argument("--info", action="store_true", help="Show info messages too")
    args = p.parse_args()

    results: list[FileResult] = []

    if args.project:
        results = scan_project_for_scl(Path(args.project))
        if not results:
            print(f"No .scl files found in _output/: {args.project}")
            return
    elif args.target:
        t = Path(args.target)
        if t.is_file():
            results = [validate_scl_file(t)]
        elif t.is_dir():
            results = [validate_scl_file(f) for f in sorted(t.rglob("*.scl"))]
        else:
            print(f"Not found: {t}")
            sys.exit(1)
    else:
        p.print_help()
        return

    total_errors = 0
    for res in results:
        print(format_result(res, show_info=args.info))
        print()
        total_errors += res.error_count

    print(f"{'-' * 50}")
    print(f"Total: {len(results)} files  -  {total_errors} errors")
    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
