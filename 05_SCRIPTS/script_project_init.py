#!/usr/bin/env python3
"""
script_project_init.py
========================
Creates a new customer project skeleton from Automation Factory.

USAGE:
    python script_project_init.py --name <ProjectName> --type <retrofit|greenfield> \
                                   --customer <CustomerName> --output <target_folder>

EXAMPLE:
    python script_project_init.py --name Beispielmaschine_Retrofit \
                                   --type retrofit \
                                   --customer "Customer Name" \
                                   --output ~/projects/

Script does:
1. Create project skeleton in target folder.
2. Copy 07_PROJECT_TEMPLATE contents.
3. Write metadata to PROJECT_MAESTRO.md.
4. Add relevant Factory files as references based on project type.
5. Optional: Initialize Git repo.
"""

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FACTORY_ROOT = Path(__file__).resolve().parent.parent

PROJECT_TYPES = {
    "retrofit": {
        "maestro_ref": "02_PROJECT_TYPES/RETROFIT/RETROFIT_MAESTRO.md",
        "key_docs": [
            "02_PROJECT_TYPES/RETROFIT/RETROFIT_IO_EXTRACT.md",
            "02_PROJECT_TYPES/RETROFIT/RETROFIT_HARDWARE_ANALYSIS.md",
        ],
    },
    "greenfield": {
        "maestro_ref": "02_PROJECT_TYPES/GREENFIELD/GREENFIELD_MAESTRO.md",
        "key_docs": [
            "02_PROJECT_TYPES/GREENFIELD/GREENFIELD_IO_NEWDESIGN.md",
            "02_PROJECT_TYPES/GREENFIELD/GREENFIELD_HARDWARE_SELECTION.md",
        ],
    },
}

# 2026-07-07 restructure (E2E measurement): a full retrofit run left every
# numbered folder (01_DOCS…06_REPORTS, 99_FACTORY_REFS) EMPTY — the product
# writes to _raw/_input/_output/metadata/REPORTS/_delivery. A project now
# creates ONLY the living structure; two parallel worlds confused everyone.
# 99_FACTORY_REFS is created on demand by link_factory_refs (CLI flow only).
PROJECT_FOLDERS = [
    "_raw",                   # Customer inputs (CONFIDENTIAL)
    "_raw/legacy_code",       #   legacy PLC sources (AWL/SEQ/S5D…)
    "_raw/drawings",          #   schematics / P&ID (PDF, DXF…)
    "_raw/photos",            #   pulpit / plant photos
    "_raw/docs",              #   manuals, specs
    "_input",                 # Hardware exchange (hardware_config.xlsx, BOM)
    "_output",                # Generated code (SCL, HMI layer, TIA import)
    "metadata",               # 14-Point Raw Data Pack (RD01..RD14) + decisions
    "REPORTS",                # Deterministic reports (+ _ai_steps drafts)
    "_delivery",              # Handover packages (ZIP, dossier PDF)
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Automation Factory project initializer")
    p.add_argument("--name", required=True, help="Project name (no spaces)")
    p.add_argument("--type", required=True, choices=PROJECT_TYPES.keys())
    p.add_argument("--customer", required=True, help="Customer name (will be in PROJECT_MAESTRO)")
    p.add_argument("--output", required=True, help="Parent folder where project will be created")
    p.add_argument("--git", action="store_true", help="Initialize git repo")
    p.add_argument("--symlink", action="store_true",
                   help="Symlink Factory refs (default: copy)")
    p.add_argument("--output-lang", default="EN", choices=["TR", "EN", "DE"],
                   help="Code output language for comments + HMI (default: EN). "
                        "This is only the per-project code-comment + HMI text language. "
                        "See GLOBAL_LANG_POLICY.md for details.")
    return p.parse_args()


def create_project_skeleton(project_path: Path) -> None:
    """Create the empty project folder skeleton."""
    project_path.mkdir(parents=True, exist_ok=True)
    for folder in PROJECT_FOLDERS:
        (project_path / folder).mkdir(parents=True, exist_ok=True)
    print(f"  + Created folder skeleton at {project_path}")


def write_project_maestro(project_path: Path, args: argparse.Namespace) -> None:
    """Write PROJECT_MAESTRO.md with the project metadata."""
    project_type_cfg = PROJECT_TYPES[args.type]
    today = date.today().isoformat()

    content = f"""---
project_name: {args.name}
customer: {args.customer}
project_type: {args.type}
created: {today}
factory_version: see FACTORY_MAESTRO.md
data_classification: CONFIDENTIAL
output_language: {args.output_lang}
---

# PROJECT_MAESTRO.md — {args.name}

> This project is managed per the **Automation Factory** standard.
> Factory reference: `99_FACTORY_REFS/`

---

## Project Info

- **Customer:** {args.customer}
- **Type:** {args.type.upper()}
- **Start:** {today}
- **Data class:** CONFIDENTIAL (see GLOBAL_DATA_CLASSIFICATION.md)

## Primary References

- `99_FACTORY_REFS/{Path(project_type_cfg['maestro_ref']).name}` — Project-type maestro
- `99_FACTORY_REFS/GLOBAL_NAMING_STANDARD.md` — Naming
- `99_FACTORY_REFS/GLOBAL_FB_TEMPLATE.scl` — FB skeleton
- `99_FACTORY_REFS/GLOBAL_DATA_CLASSIFICATION.md` — Data security

## Folder Structure

```
{args.name}/
├── _raw/            <- Customer inputs: legacy PLC code, drawings, photos (CONFIDENTIAL)
├── _input/          <- Hardware exchange files (hardware_config.xlsx, BOM)
├── metadata/        <- 14-Point Raw Data Pack (RD01..RD14) + decision files
├── _output/         <- Generated code (SCL in _output/scl, HMI layer, TIA import)
├── REPORTS/         <- Deterministic reports; AI step drafts under REPORTS/_ai_steps
└── _delivery/       <- Handover packages (ZIP, dossier PDF)
```

## AI Usage Note

When using AI on this project, the **CONFIDENTIAL** rule applies:
- Public AI (free/pro tier) is not used.
- Anonymized code snippets may be shared.
- In screenshots, the customer logo/IP/project name is masked.

## Feedback Commitment

At least **one** piece of feedback will be sent back to the Factory at project end:

```bash
python <factory>/05_SCRIPTS/script_propose_update.py \\
  --target <factory_file> \\
  --reason "..." \\
  --suggestion "..."
```

---

## Project Status

See `PROJECT_STATE.md` (updated weekly).
"""
    (project_path / "PROJECT_MAESTRO.md").write_text(content, encoding="utf-8")
    print(f"  + Wrote PROJECT_MAESTRO.md")


def write_project_state(project_path: Path, args: argparse.Namespace) -> None:
    """Empty PROJECT_STATE.md."""
    today = date.today().isoformat()
    content = f"""# PROJECT_STATE.md — {args.name}

> Updated weekly. First task Monday morning.

## {today} — Week 1

### Completed
- Project skeleton created (Automation Factory).

### In progress
- (TODO)

### Blocked / Risk
- (TODO)

### AI usage notes
- (TODO — which prompts were used, what worked, what did not)
"""
    (project_path / "PROJECT_STATE.md").write_text(content, encoding="utf-8")
    print(f"  + Wrote PROJECT_STATE.md")


def link_factory_refs(project_path: Path, args: argparse.Namespace) -> None:
    """Link the Factory reference files into the project (symlink or copy).

    v3.0.0-alpha update: includes the 14 RD specs + AI prompts + glossary + JSON schemas.
    """
    refs_path = project_path / "99_FACTORY_REFS"
    # Created on demand (no longer part of the base skeleton — the GUI flow
    # never fills it; only this CLI ref-copy path does).
    for sub in ("", "md_schemas", "ai_prompts", "lang_glossary", "validation"):
        (refs_path / sub if sub else refs_path).mkdir(parents=True, exist_ok=True)
    project_type_cfg = PROJECT_TYPES[args.type]

    # Root-level factory files (to every project)
    factory_files = [
        ("docs/FACTORY_MAESTRO.md", ""),
        ("docs/PIPELINE_CODE_REWRITE.md", ""),
        ("docs/USER_GUIDE_BIG_PICTURE.md", ""),
        ("01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md", ""),
        ("01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md", ""),
        ("01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md", ""),
        ("01_GLOBAL_STANDARDS/rules/GLOBAL_AI_INTERFACE.md", ""),
        ("01_GLOBAL_STANDARDS/rules/GLOBAL_METADATA_SCHEMA.md", ""),
        ("01_GLOBAL_STANDARDS/templates/GLOBAL_FB_TEMPLATE.scl", ""),
        (project_type_cfg["maestro_ref"], ""),
    ]
    for kd in project_type_cfg["key_docs"]:
        factory_files.append((kd, ""))

    # 14 RD specs -> md_schemas/ subfolder
    md_schemas_dir = FACTORY_ROOT / "01_GLOBAL_STANDARDS" / "md_schemas"
    if md_schemas_dir.exists():
        for spec_file in sorted(md_schemas_dir.glob("MDSCHEMA_RAWDATA_*.md")):
            factory_files.append((f"01_GLOBAL_STANDARDS/md_schemas/{spec_file.name}", "md_schemas"))

    # Glossaries
    glossary_dir = FACTORY_ROOT / "01_GLOBAL_STANDARDS" / "lang_glossary"
    if glossary_dir.exists():
        for g in sorted(glossary_dir.glob("GLOSSARY_*.md")):
            factory_files.append((f"01_GLOBAL_STANDARDS/lang_glossary/{g.name}", "lang_glossary"))

    # AI prompts (analyze folder)
    analyze_dir = FACTORY_ROOT / "04_AI_PROMPTS" / "analyze"
    if analyze_dir.exists():
        for p in sorted(analyze_dir.glob("PROMPT_*.md")):
            factory_files.append((f"04_AI_PROMPTS/analyze/{p.name}", "ai_prompts"))

    # JSON validation schemas
    schema_dir = FACTORY_ROOT / "08_METADATA_INPUT" / "schema"
    if schema_dir.exists():
        for s in sorted(schema_dir.glob("rd*.schema.json")):
            factory_files.append((f"08_METADATA_INPUT/schema/{s.name}", "validation"))

    # Copy/link
    for rel_path, subdir in factory_files:
        src = FACTORY_ROOT / rel_path
        if not src.exists():
            print(f"  ! Factory file missing: {rel_path}")
            continue
        target_dir = refs_path / subdir if subdir else refs_path
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / src.name
        if args.symlink:
            try:
                dst.symlink_to(src)
            except OSError as e:
                shutil.copy2(src, dst)
        else:
            shutil.copy2(src, dst)

    # Count report
    total_copied = sum(1 for _ in refs_path.rglob("*") if _.is_file())
    print(f"  + {total_copied} factory reference files copied (99_FACTORY_REFS/)")


def copy_metadata_templates(project_path: Path, args: argparse.Namespace) -> None:
    """Copy the 14 RD MD templates into the metadata/ folder.

    v3.0.0-alpha new feature: the customer project now includes the RD files
    to be filled in. The engineer (or AI) fills them in.
    """
    metadata_dir = project_path / "metadata"
    template_dir = FACTORY_ROOT / "07_PROJECT_TEMPLATE" / "metadata_template"

    if not template_dir.exists():
        print(f"  ! Template dir not found: {template_dir}")
        return

    copied = 0
    for tmpl in sorted(template_dir.glob("RD*.md")):
        dst = metadata_dir / tmpl.name
        shutil.copy2(tmpl, dst)
        copied += 1
    print(f"  + {copied} RD templates copied (metadata/)")


def write_readme(project_path: Path, args: argparse.Namespace) -> None:
    """Create a guide-style README in the customer project."""
    today = date.today().isoformat()
    readme = f"""# {args.name} — Customer Project

> Created with AUTOMATION_FACTORY v3.0.0-alpha.

## Project Info
- **Customer:** {args.customer}
- **Type:** {args.type.upper()}
- **Output language:** {args.output_lang}
- **Data class:** CONFIDENTIAL
- **Start:** {today}

## Folder Structure

```
{args.name}/
├── PROJECT_MAESTRO.md          <- Project orchestrator (read this!)
├── PROJECT_STATE.md            <- Weekly status
├── _raw/                       <- Customer inputs: legacy PLC code, drawings, photos (CONFIDENTIAL)
├── _input/                     <- Hardware exchange files (hardware_config.xlsx, BOM)
├── metadata/                   <- 14-Point Raw Data Pack (RD01..RD14) + decision files
│   ├── RD01_IO_List.md          (fill in or have the AI fill in)
│   ├── RD02_DataDict.md
│   ├── ...
│   └── RD14_Modernization.md
│
├── _output/                    <- Generated code: _output/scl (SCL + instance DBs),
│                                  HMI layer, tia_import staging
├── REPORTS/                    <- Deterministic reports; AI step drafts in REPORTS/_ai_steps
└── _delivery/                  <- Handover packages (ZIP, dossier PDF)
```

## Pipeline Flow (7-Gate)

1. **Gate 1 DISCOVERY** — Customer brief, legacy system inventory (`_raw/`)
2. **Gate 2 EXTRACTION** — Fill RD01..RD14 with AI (`metadata/`)
3. **Gate 3 HUMAN REVIEW** — Engineer review, reconciliation, fill in #UNKNOWNS
4. **Gate 4 CODE GENERATION** — library-first assembly into `_output/scl/`
5. **Gate 5 VALIDATION** — structural SCL validation
6. **Gate 6 SIMULATION** — TIA compile evidence / PLCSIM
7. **Gate 7 FAT/SAT** — Customer acceptance (`REPORTS/`, `_delivery/`)

## Next Steps

1. Read `PROJECT_MAESTRO.md`, verify the project metadata
2. Put the customer source data in the `_input/` folder
3. Start AI extraction:
   - Give Cursor/Claude `99_FACTORY_REFS/ai_prompts/PROMPT_ANALYZE_<platform>.md`
   - Have it analyze the `_input/` content -> produce `_input/_parsed.md`
   - Run `PROMPT_EXTRACT_*_FROM_CODE.md` in order -> fill `metadata/RD01..RD14.md`
4. Engineer review (Gate 3)
5. Validation (Gate 4)

## More Information
- `99_FACTORY_REFS/USER_GUIDE_BIG_PICTURE.md` (comprehensive guide)
- `99_FACTORY_REFS/PIPELINE_CODE_REWRITE.md` (gate details)

---
*This project is managed per the AUTOMATION_FACTORY standard. Factory discipline = predictable delivery.*
"""
    (project_path / "README.md").write_text(readme, encoding="utf-8")
    print(f"  + Wrote README.md")


def init_git(project_path: Path) -> None:
    """Initialize a git repo."""
    import subprocess
    try:
        subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
        gitignore = project_path / ".gitignore"
        gitignore.write_text(
            "# TIA Portal binary\n*.ap18\n*.ap19\n*.zal*\n"
            "# IDE\n.vscode/\n.cursor/\n"
            "# OS\n.DS_Store\nThumbs.db\n"
            "# Logs\n*.log\n",
            encoding="utf-8",
        )
        print(f"  + Git initialized")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  ! Git init failed: {e}")


def main() -> int:
    args = parse_args()
    output_root = Path(args.output).expanduser().resolve()
    project_path = output_root / args.name

    if project_path.exists():
        print(f"Project path already exists: {project_path}")
        return 1

    print(f"Initializing Automation Factory project: {args.name}")
    print(f"   Type    : {args.type}")
    print(f"   Customer: {args.customer}")
    print(f"   Path    : {project_path}")
    print()

    create_project_skeleton(project_path)
    write_project_maestro(project_path, args)
    write_project_state(project_path, args)
    write_readme(project_path, args)
    copy_metadata_templates(project_path, args)
    link_factory_refs(project_path, args)

    if args.git:
        init_git(project_path)

    print()
    print(f"Project ready: {project_path}")
    print(f"   Next: cd {project_path} && open in Cursor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
