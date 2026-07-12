#!/usr/bin/env python3
"""
script_md_schema_validator.py
==============================
Checks that MD files conform to their defined schemas (MDSCHEMA_*.md).

Schemas:
  - PROMPT_CODE_GEN     -> 04_AI_PROMPTS/code_gen/**/*.md
  - DOMAIN_REFERENCE    -> 03_DOMAIN_TOOLS/*.md, 02_PROJECT_TYPES/**/*.md

USAGE:
    # Check all code-gen prompts
    python script_md_schema_validator.py --schema PROMPT_CODE_GEN

    # Check a single file
    python script_md_schema_validator.py \\
        --target "04_AI_PROMPTS/code_gen/motor/PROMPT_MOTOR_DOL.md"

    # Check the whole system (each file against its own schema)
    python script_md_schema_validator.py --all

OUTPUT:
    Missing sections, missing frontmatter fields, non-conforming format.
    Exit code: 0 = clean, 1 = has issues.
"""

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# This script lives in 05_SCRIPTS/dev/, so the repo root is three levels up.
FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# Schema definitions
SCHEMAS = {
    "PROMPT_CODE_GEN": {
        "required_frontmatter": [
            "title", "version", "last_validated", "applies_to",
            "device_type", "prerequisite", "target_ai",
            "metadata_input", "output_artifacts", "schema",
        ],
        "required_sections": [
            "## 1. When to Use",
            "## 3. Metadata Input",
            "## 4. System Prompt",
            "## 5. User Prompt Template",
            "## 6. Expected FB Name",
            "## 7. Validation Check",
            "## 8. Typical AI Errors",
            "## 9. Related Files",
            "## 10. Feedback",
        ],
        "schema_value": "PROMPT_CODE_GEN",
        "applies_to_glob": ["04_AI_PROMPTS/code_gen/**/*.md"],
        "exclude_patterns": [
            "PROMPT_CODE_GEN_FB_MOTOR.md",  # Router (not a sub-prompt)
            "PROMPT_CODE_GEN_FB_VALVE.md",  # Router
        ],
    },
    "DOMAIN_REFERENCE": {
        "required_frontmatter": [
            "title", "version", "last_validated", "applies_to",
            "prerequisite", "schema",
        ],
        "required_sections": [
            "## 1. Purpose",  # also matches "Purpose and Scope" (substring)
            "## 2. Prerequisites",
            "## 6. AI Usage",
            "## 7. Typical Errors",
            "## 8. Checklist",
            "## 9. Related Files",
            "## 10. Feedback",
        ],
        "schema_value": "DOMAIN_REFERENCE",
        "applies_to_glob": [
            "03_DOMAIN_TOOLS/*.md",
            "02_PROJECT_TYPES/**/*.md",
        ],
        "exclude_patterns": [],
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--schema", choices=list(SCHEMAS.keys()),
                   help="Check against a specific schema")
    g.add_argument("--target", help="Check a single file (schema auto-detected)")
    g.add_argument("--all", action="store_true",
                   help="Check the whole system (each file against its own schema)")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def load_file(path: Path) -> tuple[dict, str, str]:
    """Load the file, parse frontmatter, return the body.
    Return: (frontmatter_dict, body, full_text)
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text, text

    fm_text = m.group(1)
    body = text[m.end():]

    # Simple YAML parse (scalar key:value only)
    fm = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()

    return fm, body, text


def detect_schema_from_file(path: Path, fm: dict) -> str | None:
    """Detect which schema the file is subject to."""
    # 1. If stated in frontmatter, use that
    if "schema" in fm:
        return fm["schema"]

    # 2. Path-based guess
    rel = str(path.relative_to(FACTORY_ROOT))
    if rel.startswith("04_AI_PROMPTS/code_gen/"):
        return "PROMPT_CODE_GEN"
    if rel.startswith("03_DOMAIN_TOOLS/") or rel.startswith("02_PROJECT_TYPES/"):
        return "DOMAIN_REFERENCE"

    return None


def validate_file(path: Path, schema_name: str, verbose: bool = False) -> list[str]:
    """Validate a single file against the schema. Returns a list of issues."""
    if schema_name not in SCHEMAS:
        return [f"UNKNOWN_SCHEMA: {schema_name}"]

    schema = SCHEMAS[schema_name]
    issues = []

    fm, body, _ = load_file(path)

    # STUB files are checked less strictly
    is_stub = fm.get("status") == "STUB"

    # 1. Frontmatter fields
    for required_key in schema["required_frontmatter"]:
        if required_key not in fm:
            if not (is_stub and required_key in ("metadata_input", "output_artifacts", "target_ai")):
                issues.append(f"FRONTMATTER_MISSING: {required_key}")

    # 2. Is the schema value correct?
    if "schema" in fm and fm["schema"] != schema["schema_value"]:
        issues.append(f"SCHEMA_MISMATCH: expected '{schema['schema_value']}', got '{fm['schema']}'")

    # 3. Sections — skipped for STUB files
    if not is_stub:
        for required_section in schema["required_sections"]:
            # Substring match (for flexibility in heading formatting)
            if required_section not in body:
                issues.append(f"SECTION_MISSING: {required_section}")

    return issues


def find_files_for_schema(schema_name: str) -> list[Path]:
    """Find the files that apply to the schema."""
    schema = SCHEMAS[schema_name]
    files = set()
    for pattern in schema["applies_to_glob"]:
        files.update(FACTORY_ROOT.glob(pattern))

    # Apply exclude patterns
    excluded = []
    for f in files:
        for excl in schema["exclude_patterns"]:
            if f.name == excl:
                excluded.append(f)
                break

    files -= set(excluded)
    return sorted(files)


def main() -> int:
    args = parse_args()

    print(f"\nMD Schema Validator\n")

    all_issues = []

    if args.target:
        path = (FACTORY_ROOT / args.target).resolve()
        if not path.exists():
            print(f"File not found: {args.target}")
            return 1
        fm, _, _ = load_file(path)
        schema_name = detect_schema_from_file(path, fm)
        if not schema_name:
            print(f"Schema could not be detected: {args.target}")
            return 1
        print(f"{args.target}")
        print(f"   Schema: {schema_name}")
        issues = validate_file(path, schema_name, args.verbose)
        if issues:
            for issue in issues:
                print(f"   [FAIL] {issue}")
            all_issues.extend(issues)
        else:
            print(f"   [OK] Clean")

    elif args.schema:
        files = find_files_for_schema(args.schema)
        print(f"Schema: {args.schema} ({len(files)} files)\n")
        for f in files:
            issues = validate_file(f, args.schema, args.verbose)
            rel = f.relative_to(FACTORY_ROOT)
            if issues:
                print(f"   [FAIL] {rel}")
                for issue in issues:
                    print(f"      - {issue}")
                all_issues.extend([(str(rel), i) for i in issues])
            elif args.verbose:
                print(f"   [OK] {rel}")

    elif args.all:
        for schema_name in SCHEMAS:
            files = find_files_for_schema(schema_name)
            print(f"Schema: {schema_name} ({len(files)} files)")
            schema_issues = 0
            for f in files:
                issues = validate_file(f, schema_name, args.verbose)
                if issues:
                    rel = f.relative_to(FACTORY_ROOT)
                    print(f"   [FAIL] {rel}")
                    for issue in issues:
                        print(f"      - {issue}")
                    schema_issues += len(issues)
                    all_issues.extend([(str(rel), i) for i in issues])
            if schema_issues == 0:
                print(f"   [OK] All clean")
            print()

    print()
    if all_issues:
        print(f"Total {len(all_issues)} issues found.")
        return 1
    else:
        print(f"All checked files conform to schema.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
