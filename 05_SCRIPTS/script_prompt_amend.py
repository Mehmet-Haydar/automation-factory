#!/usr/bin/env python3
"""
script_prompt_amend.py — Bulk AI prompt update

Purpose:
- v4.0.0 English translation (system TR -> EN)
- Bulk-update a common field across all prompts (e.g. version bump)
- Add a new AI model name (to the target_ai list)
- Add a new section to existing prompts

Dependency: pyyaml
Output: modified files (review with git diff)
Sandbox: write (warning: changes multiple files; --dry-run recommended)

Usage:
    # Version bump across all AI prompts
    python 05_SCRIPTS/script_prompt_amend.py \\
        --action bump-version \\
        --from 1.0.0 --to 1.1.0 \\
        --dry-run

    # Add a new model to the target_ai list
    python 05_SCRIPTS/script_prompt_amend.py \\
        --action add-target-ai \\
        --model "Claude Sonnet 5+" \\
        --dry-run

    # Markdown output for bulk translation (input for a cheap model)
    python 05_SCRIPTS/script_prompt_amend.py \\
        --action prepare-translation \\
        --source-lang TR --target-lang EN \\
        --output /tmp/translation_input.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    print("[ERR] Missing dependency: pyyaml. Run `pip install pyyaml`.", file=sys.stderr)
    sys.exit(2)


def find_all_prompts(root: Path) -> list[Path]:
    """Find every PROMPT_*.md file under 04_AI_PROMPTS/."""
    prompts_dir = root / "04_AI_PROMPTS"
    return sorted(prompts_dir.rglob("PROMPT_*.md"))


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split frontmatter + body."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return fm, body


def write_frontmatter(fm: dict, body: str) -> str:
    """Combine frontmatter + body."""
    fm_text = yaml.dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{fm_text}---\n{body}"


def action_bump_version(prompts: list[Path], from_v: str, to_v: str, dry_run: bool) -> int:
    """Version bump across all prompts."""
    count = 0
    for path in prompts:
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm.get("version") == from_v:
            fm["version"] = to_v
            fm["last_updated"] = "<YYYY-MM-DD>"  # engineer will fill in
            new_text = write_frontmatter(fm, body)
            print(f"  [BUMP] {path.relative_to(path.parent.parent.parent)}: {from_v} -> {to_v}")
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")
            count += 1
    print(f"[INFO] bumped {count}/{len(prompts)} files")
    return count


def action_add_target_ai(prompts: list[Path], model: str, dry_run: bool) -> int:
    """Add a new model to the target_ai list."""
    count = 0
    for path in prompts:
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        target = fm.get("target_ai")
        if isinstance(target, list) and model not in target:
            target.append(model)
            fm["target_ai"] = target
            new_text = write_frontmatter(fm, body)
            print(f"  [ADD-AI] {path.relative_to(path.parent.parent.parent)}: + {model}")
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")
            count += 1
    print(f"[INFO] model added to {count}/{len(prompts)} files")
    return count


def action_prepare_translation(prompts: list[Path], source_lang: str, target_lang: str,
                                output: Path, dry_run: bool) -> int:
    """
    Prepare an input file for bulk translation.

    Format: paragraphs are fed sequentially to a cheap model, output is marked.
    """
    chunks = []
    for path in prompts:
        chunks.append(f"=== FILE: {path.name} ({source_lang} -> {target_lang}) ===")
        chunks.append(path.read_text(encoding="utf-8"))
        chunks.append("=== END FILE ===\n")

    output_text = "\n".join(chunks)
    print(f"[INFO] {len(prompts)} prompts -> bulk translation input ({len(output_text)} chars)")

    if not dry_run:
        output.write_text(output_text, encoding="utf-8")
        print(f"[OK] Written: {output}")
    else:
        print("[DRY-RUN] Write skipped")

    return len(prompts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk AI prompt update")
    parser.add_argument("--action", required=True,
                        choices=["bump-version", "add-target-ai", "prepare-translation"],
                        help="Operation to perform")
    parser.add_argument("--from", dest="from_v", help="Old version (for bump-version)")
    parser.add_argument("--to", dest="to_v", help="New version (for bump-version)")
    parser.add_argument("--model", help="AI model name to add (for add-target-ai)")
    parser.add_argument("--source-lang", help="Source language (for prepare-translation)")
    parser.add_argument("--target-lang", help="Target language (for prepare-translation)")
    parser.add_argument("--output", type=Path, help="Output file (for prepare-translation)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write, only report")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    prompts = find_all_prompts(repo_root)
    print(f"[INFO] Found {len(prompts)} AI prompts")

    if args.action == "bump-version":
        if not args.from_v or not args.to_v:
            parser.error("bump-version requires --from and --to")
        action_bump_version(prompts, args.from_v, args.to_v, args.dry_run)

    elif args.action == "add-target-ai":
        if not args.model:
            parser.error("add-target-ai requires --model")
        action_add_target_ai(prompts, args.model, args.dry_run)

    elif args.action == "prepare-translation":
        if not args.source_lang or not args.target_lang or not args.output:
            parser.error("prepare-translation requires --source-lang, --target-lang, --output")
        action_prepare_translation(prompts, args.source_lang, args.target_lang, args.output, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
