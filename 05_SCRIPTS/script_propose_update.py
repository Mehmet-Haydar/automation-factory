#!/usr/bin/env python3
"""
script_propose_update.py
==========================
Sends feedback from a field customer project back to the factory.

USAGE:
    python script_propose_update.py \\
        --target "01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md" \\
        --reason "Encoder naming is missing" \\
        --suggestion "ENC_<location>_<axis>"

WHAT IT DOES:
    1. Adds a new entry to KB_FEEDBACK_LOG.md (date + proposer + target + reason + suggestion)
    2. Adds a 'PROPOSED_UPDATE' comment to the target file (HTML comment)
    3. Optional: opens a new Git branch (with --git)

PURPOSE:
    Gaps/errors found in the field flow back to the factory systematically.
    No suggestion is lost; everything is versioned.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FACTORY_ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_LOG = FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "KB_FEEDBACK_LOG.md"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True,
                   help="Target factory file (relative to the factory root)")
    p.add_argument("--reason", required=True, help="Problem/gap description")
    p.add_argument("--suggestion", required=True, help="Proposed fix")
    p.add_argument("--proposer", default=os.environ.get("USER", "unknown"),
                   help="Person making the proposal (default: $USER)")
    p.add_argument("--project", default="(unknown project)",
                   help="Which project this was found during")
    p.add_argument("--severity", choices=["info", "warning", "critical"], default="warning")
    p.add_argument("--git", action="store_true",
                   help="Open a new branch in the factory repo")
    return p.parse_args()


def ensure_feedback_log() -> None:
    """Create KB_FEEDBACK_LOG.md if it does not exist."""
    if FEEDBACK_LOG.exists():
        return
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_LOG.write_text(
        """---
title: Knowledge Base - Feedback Log
version: 1.0.0
last_validated: 2026-05
auto_generated: true
---

# KB_FEEDBACK_LOG.md

> Feedback coming from field projects back to the factory.
> Each entry is added automatically by `script_propose_update.py`.

---

""",
        encoding="utf-8",
    )


def append_to_log(args: argparse.Namespace) -> str:
    """Add a new entry to the feedback log and return the entry ID."""
    ensure_feedback_log()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry_id = datetime.now().strftime("FB-%Y%m%d-%H%M%S")

    severity_label = {"info": "[INFO]", "warning": "[WARNING]", "critical": "[CRITICAL]"}[args.severity]

    entry = f"""## {entry_id} — {ts}

- **Severity:** {severity_label} {args.severity.upper()}
- **Proposer:** {args.proposer}
- **Project:** {args.project}
- **Target:** `{args.target}`
- **Status:** PENDING_REVIEW

### Reason
{args.reason}

### Suggested change
{args.suggestion}

---

"""
    with FEEDBACK_LOG.open("a", encoding="utf-8") as f:
        f.write(entry)

    return entry_id


def annotate_target(target_rel: str, entry_id: str, args: argparse.Namespace) -> bool:
    """Add a marker to the target file as an HTML comment."""
    target = FACTORY_ROOT / target_rel
    if not target.exists():
        print(f"Target file not found: {target_rel}")
        print(f"  Recorded in the feedback log only.")
        return False

    if target.suffix not in (".md",):
        print(f"  -> Target is not .md; no marker added to the file.")
        return True

    annotation = (
        f"\n<!-- PROPOSED_UPDATE {entry_id} ({args.severity}): "
        f"{args.reason[:80]}{'...' if len(args.reason) > 80 else ''} -->\n"
    )
    with target.open("a", encoding="utf-8") as f:
        f.write(annotation)
    return True


def create_git_branch(entry_id: str) -> bool:
    """Open a new branch in the factory repo."""
    branch = f"feedback/{entry_id.lower()}"
    try:
        # Repo check
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=FACTORY_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=FACTORY_ROOT, check=True, capture_output=True,
        )
        print(f"  Git branch opened: {branch}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Git operation failed: "
              f"{e.stderr.decode(errors='replace') if e.stderr else e}")
        return False
    except FileNotFoundError:
        print(f"  Git is not installed or this is not a repo.")
        return False


def main() -> int:
    args = parse_args()

    print(f"Creating factory feedback")
    print(f"   Target  : {args.target}")
    print(f"   Reason  : {args.reason[:60]}{'...' if len(args.reason) > 60 else ''}")
    print(f"   Severity: {args.severity}")
    print(f"   Proposer: {args.proposer}")
    print()

    entry_id = append_to_log(args)
    print(f"  Added to KB_FEEDBACK_LOG.md: {entry_id}")

    annotate_target(args.target, entry_id, args)

    if args.git:
        create_git_branch(entry_id)

    print()
    print(f"Feedback recorded: {entry_id}")
    print(f"   Next step: review this proposal in the factory and update the relevant .md.")
    print(f"   After approval: set status to APPLIED in KB_FEEDBACK_LOG.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
