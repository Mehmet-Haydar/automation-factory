#!/usr/bin/env python3
"""
prompt_meta.py — AI Prompt Frontmatter Parser + Smart File Detection

Each AUTOMATION_FACTORY AI prompt's frontmatter contains these fields:
- input_source     : Source file path (e.g. _input/_parsed.md)
- prerequisite     : Dependent factory files (GLOBAL_NAMING_STANDARD.md etc)
- output_artifacts : Artifacts to generate (RD01_IO_List.xlsx, ...)
- schema_target    : JSON validation schema path
- extracts         : Target RD ID (RD01_IO_List)

This module:
1. Parse frontmatter
2. Detect source files (_input/, combine with 99_FACTORY_REFS/)
3. Detect target file (metadata/ or 03_PLC/SCL/ etc.)
"""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# R-S-1: merkezi F-CPU tespit yardımcısı
try:
    from workbench.core.safety_utils import is_f_cpu as _is_f_cpu
except ImportError:  # pragma: no cover
    def _is_f_cpu(cpu_model):  # type: ignore[misc]
        import re as _re
        return bool(_re.search(r"(?i)(\bSF\b|^SF|\bTF\b|\dF[-\s/]|\dF$|\dTF[-\s/]|\dTF$|[-\s]F[-\s]|[-\s]F$)", cpu_model or ""))


# Target file mapping by RD ID.
# NOTE: RD05 intentionally omitted — its filename has a variable suffix
# (DRAFT_UNVERIFIED, VERIFIED, etc.).  Use _resolve_rd05_file() instead.
RD_TO_METADATA_FILE = {
    "RD01": "RD01_IO_List.md",
    "RD02": "RD02_DataDict.md",
    "RD03": "RD03_Flowchart.md",
    "RD04": "RD04_Mode.md",
    "RD06": "RD06_Motion.md",
    "RD07": "RD07_Timing.md",
    "RD08": "RD08_Alarm.md",
    "RD09": "RD09_Comms.md",
    "RD10": "RD10_FBSpec.md",
    "RD11": "RD11_HMI.md",
    "RD12": "RD12_UseCase.md",
    "RD13": "RD13_Annotation.md",
    "RD14": "RD14_Modernization.md",
}


def _resolve_rd05_file(project_path: Optional[Path]) -> Optional[Path]:
    """Return the first RD05_Safety*.md found under <project>/metadata/, or None.

    Uses glob so any suffix variant (DRAFT_UNVERIFIED, VERIFIED, etc.) is
    accepted.  Fail-closed: returns None when nothing is found; callers must
    handle the missing-file case explicitly.
    """
    if project_path is None:
        return None
    metadata = project_path / "metadata"
    if not metadata.is_dir():
        return None
    candidates = sorted(metadata.glob("RD05_Safety*.md"))
    return candidates[0] if candidates else None

# Default target folder by role
ROLE_TO_TARGET_DIR = {
    "platform_parser": "_input",          # produces _parsed.md
    "topic_extractor": "metadata",         # fills in RDs
    "code_gen": "03_PLC/SCL",              # produces SCL code
    "review": "_output/reviews",           # review reports
    "test_gen": "05_TESTS",                # test scripts
    "doc_gen": "_output/docs",             # As-built, manual
}


@dataclass
class PromptMeta:
    """Metadata parsed from an AI prompt."""
    name: str
    path: Path
    role: str = ""
    extracts: str = ""           # e.g. RD01_IO_List
    input_source: str = ""       # _input/_parsed.md
    prerequisite: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    schema_target: str = ""
    applies_to: list[str] = field(default_factory=list)
    raw_frontmatter: dict = field(default_factory=dict)


def parse_prompt_frontmatter(prompt_path: Path) -> PromptMeta:
    """Parse the frontmatter of an AI prompt .md file."""
    meta = PromptMeta(name=prompt_path.stem, path=prompt_path)

    if not prompt_path.exists():
        return meta

    try:
        text = prompt_path.read_text(encoding="utf-8")
    except Exception:
        return meta

    # Extract frontmatter
    if not text.startswith("---"):
        return meta
    end = text.find("---", 3)
    if end < 0:
        return meta

    fm_text = text[3:end].strip()
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        return meta

    meta.raw_frontmatter = fm

    # Pull fields
    meta.role = str(fm.get("role", "")).strip()
    meta.extracts = str(fm.get("extracts", "")).strip()
    meta.input_source = str(fm.get("input_source", "")).strip()
    meta.schema_target = str(fm.get("schema_target", "")).strip()

    # Lists
    prereq = fm.get("prerequisite", [])
    if isinstance(prereq, str):
        meta.prerequisite = [prereq]
    elif isinstance(prereq, list):
        meta.prerequisite = [str(x) for x in prereq]

    artifacts = fm.get("output_artifacts", [])
    if isinstance(artifacts, str):
        meta.output_artifacts = [artifacts]
    elif isinstance(artifacts, list):
        meta.output_artifacts = [str(x) for x in artifacts]

    apt = fm.get("applies_to", [])
    if isinstance(apt, str):
        meta.applies_to = [apt]
    elif isinstance(apt, list):
        meta.applies_to = [str(x) for x in apt]

    return meta


def resolve_source_files(
    meta: PromptMeta,
    project_path: Optional[Path] = None,
    factory_root: Optional[Path] = None,
) -> list[dict]:
    """Detect the source files this prompt needs.

    Returns: List of {"path": Path, "exists": bool, "category": str, "note": str}
    """
    files = []

    # 1. input_source (in the customer _input folder or in the factory)
    if meta.input_source:
        src = meta.input_source
        # If not an absolute path, search under the project
        if project_path and not Path(src).is_absolute():
            candidate = project_path / src
            files.append({
                "path": candidate,
                "exists": candidate.exists(),
                "category": "Input",
                "note": "from the AI prompt 'input_source' field",
            })
        elif factory_root:
            candidate = factory_root / src
            files.append({
                "path": candidate,
                "exists": candidate.exists(),
                "category": "Input",
                "note": "from the factory path",
            })

    # 2. prerequisite (under 99_FACTORY_REFS — if a project is open)
    for prereq in meta.prerequisite:
        # GLOBAL_*, MDSCHEMA_*, RETROFIT_*, GREENFIELD_*, PIPELINE_*, KB_* — factory refs
        if project_path:
            refs_dir = project_path / "99_FACTORY_REFS"
            # Root first, then subfolders
            candidates = [
                refs_dir / prereq,
                refs_dir / "md_schemas" / prereq,
                refs_dir / "ai_prompts" / prereq,
                refs_dir / "lang_glossary" / prereq,
                refs_dir / "validation" / prereq,
            ]
            for c in candidates:
                if c.exists():
                    files.append({
                        "path": c,
                        "exists": True,
                        "category": "Reference",
                        "note": f"prerequisite ({prereq})",
                    })
                    break
            else:
                # Not found -> suggest from the factory
                if factory_root:
                    # GLOBAL_*  -> 01_GLOBAL_STANDARDS/rules/
                    # MDSCHEMA_* -> 01_GLOBAL_STANDARDS/md_schemas/
                    if prereq.startswith("MDSCHEMA_"):
                        files.append({
                            "path": factory_root / "01_GLOBAL_STANDARDS" / "md_schemas" / prereq,
                            "exists": (factory_root / "01_GLOBAL_STANDARDS" / "md_schemas" / prereq).exists(),
                            "category": "Reference (factory)",
                            "note": "prerequisite (factory)",
                        })
                    elif prereq.startswith("GLOBAL_"):
                        # rules or templates
                        for sub in ["rules", "templates"]:
                            p = factory_root / "01_GLOBAL_STANDARDS" / sub / prereq
                            if p.exists():
                                files.append({
                                    "path": p, "exists": True,
                                    "category": "Reference (factory)",
                                    "note": "prerequisite (factory)",
                                })
                                break
        else:
            # No project, show from the factory only
            if factory_root:
                if prereq.startswith("MDSCHEMA_"):
                    p = factory_root / "01_GLOBAL_STANDARDS" / "md_schemas" / prereq
                    files.append({
                        "path": p, "exists": p.exists(),
                        "category": "Reference (factory)",
                        "note": "prerequisite",
                    })

    # 3. schema_target (validation schema)
    if meta.schema_target and project_path:
        # 99_FACTORY_REFS/validation/rd01_io.schema.json
        schema_name = Path(meta.schema_target).name
        candidate = project_path / "99_FACTORY_REFS" / "validation" / schema_name
        if candidate.exists():
            files.append({
                "path": candidate,
                "exists": True,
                "category": "Schema",
                "note": "JSON validation",
            })

    return files


def resolve_target_file(
    meta: PromptMeta,
    project_path: Optional[Path] = None,
) -> Optional[Path]:
    """Detect the target file this prompt will write."""
    if not project_path:
        return None

    # 1. If there is an extracts field (e.g. RD01_IO_List) -> metadata/RD01_*.md
    if meta.extracts:
        # Find the RD ID (RD01, RD02, ...)
        rd_match = re.match(r"(RD\d{2})", meta.extracts)
        if rd_match:
            rd_id = rd_match.group(1)
            # RD05 has a variable-suffix filename — discover it via glob.
            if rd_id == "RD05":
                return _resolve_rd05_file(project_path)
            filename = RD_TO_METADATA_FILE.get(rd_id)
            if filename:
                return project_path / "metadata" / filename

    # 2. Default folder by role
    target_dir = ROLE_TO_TARGET_DIR.get(meta.role)
    if target_dir:
        # Pick the first .md/.scl file from output_artifacts
        for artifact in meta.output_artifacts:
            if artifact.endswith((".md", ".scl", ".xlsx")):
                # Combine with the folder
                return project_path / target_dir / Path(artifact).name

    # 3. _parsed.md for platform_parser
    if meta.role == "platform_parser":
        return project_path / "_input" / "_parsed.md"

    # No guess
    return None


def build_smart_brief(
    meta: PromptMeta,
    prompt_body: str,
    project_path: Optional[Path] = None,
    factory_root: Optional[Path] = None,
    extra_files: Optional[list[Path]] = None,
    custom_target: Optional[Path] = None,
    user_context: str = "",
) -> str:
    """Build a smart brief package for Cursor.

    Args:
        meta: parsed prompt metadata
        prompt_body: full prompt content (system prompt)
        project_path: active customer project (if any)
        factory_root: factory root path
        extra_files: manually added files
        custom_target: target overridden by the user
        user_context: extra context

    Returns:
        Full brief in Markdown format
    """
    # File detection
    source_files = resolve_source_files(meta, project_path, factory_root)
    target_file = custom_target or resolve_target_file(meta, project_path)

    if extra_files:
        for f in extra_files:
            source_files.append({
                "path": f, "exists": f.exists(),
                "category": "Manually Added",
                "note": "added by the user",
            })

    # Build the brief
    lines = []
    lines.append("# AUTOMATION_FACTORY — Cursor Brief")
    lines.append("")
    lines.append(f"## TASK: {meta.name}")
    if meta.extracts:
        lines.append(f"**Target RD:** {meta.extracts}")
    lines.append("")

    if project_path:
        lines.append("## ACTIVE PROJECT")
        lines.append(f"- **Path:** `{project_path}`")
        # Metadata from PROJECT_MAESTRO.md frontmatter
        maestro = project_path / "PROJECT_MAESTRO.md"
        if maestro.exists():
            try:
                content = maestro.read_text(encoding="utf-8")
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        fm = yaml.safe_load(content[3:end].strip()) or {}
                        if fm.get("customer"):
                            lines.append(f"- **Customer:** {fm['customer']}")
                        if fm.get("project_type"):
                            lines.append(f"- **Type:** {fm['project_type']}")
                        if fm.get("output_language"):
                            lines.append(f"- **Output Language:** {fm['output_language']}")
            except Exception:
                pass
        lines.append("")

        # === TARGET PLATFORM (Phase 19 — from PROJECT_STATE.json) ===
        state_file = project_path / "PROJECT_STATE.json"
        if state_file.exists():
            try:
                import json as _json
                state = _json.loads(state_file.read_text(encoding="utf-8"))
                tp = state.get("target_platform", "")
                tc = state.get("target_cpu", "")
                tv = state.get("target_tia_version", "")
                tf = state.get("target_firmware", "")
                if tp or tc:
                    lines.append("## TARGET PLATFORM (generated code will run on this CPU)")
                    if tp:
                        lines.append(f"- **Platform:** {tp}")
                    if tc:
                        lines.append(f"- **CPU Model:** {tc}")
                    if tv and tv != "N/A":
                        lines.append(f"- **TIA Portal:** {tv}")
                    if tf:
                        lines.append(f"- **Firmware:** {tf}")
                    # F-CPU warning
                    is_safety = _is_f_cpu(tc)  # R-S-1: merkezi F-CPU tespiti
                    if is_safety:
                        lines.append("- **F-CPU (Safety):** F-FB / F-DB supported. Safety functions "
                                     "will be generated as F-blocks (TUV approval mandatory).")
                    lines.append("- **Rule:** Generated SCL must follow this CPU family's syntax rules "
                                 "(S7-1500: optimized access TRUE, S7-300: legacy access). "
                                 "TIA version-specific instructions (e.g. V19+ `IS_VALID()`) must be used correctly.")
                    lines.append("")
            except Exception:
                pass

        # === IO PHYSICAL ADDRESS (Phase 22 — from HW02_IO_Adresleme.md) ===
        hw02_path = project_path / "metadata" / "HW02_IO_Adresleme.md"
        if hw02_path.exists():
            try:
                hw_content = hw02_path.read_text(encoding="utf-8")
                lines.append("## IO PHYSICAL ADDRESS MAPPING (from hardware_config.xlsx)")
                # Summary lines
                for line in hw_content.splitlines():
                    if line.startswith("- **Total IO:**") or line.startswith("- Digital") or \
                       line.startswith("- Analog") or line.startswith("- **RD01"):
                        lines.append(line)
                lines.append("")
                # First 20 rows of the DI table (most critical for SCL code gen)
                in_table = False
                table_lines = 0
                for line in hw_content.splitlines():
                    if line.startswith("## Digital Inputs") or line.startswith("## Digital Outputs"):
                        in_table = True
                        lines.append(line)
                    elif in_table and line.startswith("##"):
                        in_table = False
                        if table_lines > 0:
                            break
                    elif in_table and line:
                        lines.append(line)
                        if line.startswith("|") and not line.startswith("| Tag") and not line.startswith("|---"):
                            table_lines += 1
                            if table_lines >= 20:
                                lines.append("| _(... remaining rows in the HW02 file)_ | | | | | |")
                                in_table = False
                                break
                lines.append("")
                lines.append(f"- **Full list:** `@metadata/HW02_IO_Adresleme.md`")
                lines.append("- **Rule:** When generating SCL, take %I/%Q/%IW addresses from this table — do NOT write placeholders")
                lines.append("")
            except Exception:
                pass

        # === SELECTED DEVICES (Phase 23 — PROJECT_STATE.json + HW01_BOM.md) ===
        hw01_path = project_path / "metadata" / "HW01_BOM.md"
        if hw01_path.exists():
            try:
                import json as _json2
                state2_file = project_path / "PROJECT_STATE.json"
                selected_devs = []
                if state2_file.exists():
                    state2 = _json2.loads(state2_file.read_text(encoding="utf-8"))
                    selected_devs = state2.get("selected_devices", [])

                if selected_devs:
                    lines.append("## PROJECT DEVICES (from the library — SCL template reference)")
                    lines.append("")
                    lines.append(f"This project uses **{len(selected_devs)} devices**. "
                                 f"When generating SCL code, use these devices' protocol/telegram info:")
                    lines.append("")
                    for dev in selected_devs:
                        dev_id = dev.get("device_id", "?")
                        qty    = dev.get("quantity", 1)
                        lines.append(f"- `{dev_id}` (Quantity: {qty})")
                    lines.append("")

                    # Device detail sections from HW01 (max 3 devices, keep it short)
                    hw01_content = hw01_path.read_text(encoding="utf-8")
                    lines.append("**Device technical details** (full list: `@metadata/HW01_BOM.md`):")
                    lines.append("")

                    # Extract section headers (### device_id ...)
                    in_detail = False
                    detail_count = 0
                    detail_lines_count = 0
                    MAX_DEVICES = 3
                    MAX_LINES_PER_DEVICE = 60

                    for hw_line in hw01_content.splitlines():
                        if hw_line.startswith("### ") and "Quantity:" in hw_line:
                            if detail_count >= MAX_DEVICES:
                                lines.append(f"_(... {len(selected_devs) - MAX_DEVICES} more devices — in HW01_BOM.md)_")
                                break
                            in_detail = True
                            detail_count += 1
                            detail_lines_count = 0
                            lines.append(hw_line)
                        elif in_detail:
                            if hw_line == "---":
                                in_detail = False
                                lines.append("")
                            elif detail_lines_count < MAX_LINES_PER_DEVICE:
                                lines.append(hw_line)
                                detail_lines_count += 1
                            elif detail_lines_count == MAX_LINES_PER_DEVICE:
                                lines.append("_(... trimmed — full content in HW01_BOM.md)_")
                                detail_lines_count += 1
                    lines.append("")
                    lines.append("- **Rule:** Use the STW1/ZSW1 bit definitions and SCL templates above")
                    lines.append("- **Priority:** project-local `_hardware/` > Factory `09_HARDWARE_LIBRARY/`")
                    lines.append("")
            except Exception:
                pass

    # Source files (Cursor @ references)
    if source_files:
        lines.append("## SOURCE FILES (read with Cursor @)")
        for sf in source_files:
            mark = "OK" if sf["exists"] else "MISSING"
            try:
                rel = sf["path"].relative_to(project_path) if project_path else sf["path"]
            except (ValueError, AttributeError):
                rel = sf["path"]
            lines.append(f"- {sf['category']} `@{rel}` [{mark}]  _{sf['note']}_")
        lines.append("")

    # Target file
    if target_file:
        try:
            rel = target_file.relative_to(project_path) if project_path else target_file
        except (ValueError, AttributeError):
            rel = target_file
        exists_mark = "(exists, to be filled in)" if target_file.exists() else "(to be created)"
        lines.append("## TARGET FILE (AI will WRITE / UPDATE this file)")
        lines.append(f"- `@{rel}` {exists_mark}")
        lines.append("")

    # Rules
    lines.append("## RULES")
    lines.append("- Follow GLOBAL_NAMING_STANDARD (regex: `^[A-Z]+_[A-Z0-9]+_\\d{3}(_[A-Z]+)?$`)")
    lines.append("- Customer data is CONFIDENTIAL — do not upload to public AI")
    if meta.extracts and "RD05" in meta.extracts:
        lines.append("- RD05 Safety — NEVER guess SIL/PLr (DRAFT_UNVERIFIED)")
    lines.append("- Add a '#UNKNOWNS' section for any uncertainties")
    lines.append("")

    if user_context:
        lines.append("## USER CONTEXT")
        lines.append(user_context)
        lines.append("")

    # System prompt
    lines.append("## SYSTEM PROMPT")
    lines.append("")
    lines.append(prompt_body)
    lines.append("")

    # Instructions
    lines.append("## STEPS (for Cursor)")
    lines.append("1. Read the source files referenced with @ above")
    lines.append("2. Produce output per the system prompt")
    if target_file:
        lines.append(f"3. WRITE the output to **`{rel}`** (update the existing content)")
    else:
        lines.append("3. Write the output to the appropriate file (the user did not specify a path)")
    lines.append("4. Add a #UNKNOWNS section for any uncertainties")
    lines.append("5. When done, say 'Done' + give a short summary")

    return "\n".join(lines)


def write_ai_result_to_file(
    target_file: Path,
    content: str,
    backup: bool = True,
) -> dict:
    """Write the AI output to the target file. Takes a backup.

    Returns: {"success": bool, "backup": Path|None, "message": str}
    """
    result = {"success": False, "backup": None, "message": ""}

    try:
        # Create the target folder
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Backup (if the file already exists)
        if backup and target_file.exists():
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = target_file.parent / f".{target_file.stem}.backup_{ts}{target_file.suffix}"
            backup_path.write_bytes(target_file.read_bytes())
            result["backup"] = backup_path

        # Write
        target_file.write_text(content, encoding="utf-8")
        result["success"] = True
        result["message"] = f"Written: {target_file}"
        if result["backup"]:
            result["message"] += f"\nBackup: {result['backup'].name}"
    except Exception as e:
        result["message"] = f"Error: {type(e).__name__}: {e}"

    return result


# -- Phase 26-D: Topic-Aware Context Injection --------------------------------

# Topic -> RD files to include (None = include all)
TOPIC_RD_FILTER: dict[str, Optional[list[str]]] = {
    "motor":    ["RD01", "RD02", "RD03", "RD06", "RD07", "RD10"],
    "valve":    ["RD01", "RD02", "RD03", "RD07", "RD08", "RD10"],
    "safety":   ["RD01", "RD05", "RD06", "RD10"],
    "hmi":      ["RD11", "RD12", "RD13", "RD08"],
    "alarm":    ["RD08", "RD11", "RD01"],
    "comms":    ["RD09", "RD01", "RD02"],
    "timing":   ["RD07", "RD03", "RD01"],
    "ob1":      ["RD01", "RD02", "RD03", "RD04", "RD10"],
    "mode":     ["RD04", "RD03", "RD01"],
    "doc":      ["RD01", "RD02", "RD03", "RD14"],
    "test":     ["RD01", "RD08", "RD12"],
    "default":  None,
}

# Keywords for topic detection (Turkish keywords kept to match Turkish step labels)
_TOPIC_KEYWORDS: list[tuple[str, list[str]]] = [
    ("motor",   ["motor", "pump", "pompa", "kompresör", "fan", "fb_motor", "motor_fb"]),
    ("valve",   ["valve", "valf", "vanai", "kelebek", "fb_valve", "valf_fb"]),
    ("safety",  ["safety", "güvenlik", "sil", "plr", "rd05", "f_fb", "f-fb"]),
    ("hmi",     ["hmi", "scada", "panel", "operatör", "rd11", "rd12", "rd13"]),
    ("alarm",   ["alarm", "hata", "fault", "rd08"]),
    ("comms",   ["profinet", "profibus", "comms", "iletişim", "rd09", "ethercat"]),
    ("timing",  ["timing", "zaman", "zamanlama", "rd07", "delay", "gecikme"]),
    ("ob1",     ["ob1", "ob_main", "organization_block", "ana_program", "main"]),
    ("mode",    ["mode", "mod", "rd04", "operasyon modu", "işletim"]),
    ("doc",     ["doc", "belge", "manual", "rd14", "modernizasyon"]),
    ("test",    ["test", "fbt", "unit", "rd12"]),
]


def detect_step_topic(step_label: str, prompt_name: str = "") -> str:
    """Detect the topic of a pipeline step -> returns a TOPIC_RD_FILTER key."""
    combined = (step_label + " " + prompt_name).lower()
    for topic, keywords in _TOPIC_KEYWORDS:
        if any(kw in combined for kw in keywords):
            return topic
    return "default"


def build_context_for_step(
    project_path: Path,
    step_label: str,
    prompt_name: str = "",
    max_chars: int = 6000,
) -> str:
    """
    Based on the topic of the pipeline step, read the relevant RD files and
    return the context text to inject into the AI.

    The returned text is appended to user_msg. Limited to max_chars in total.
    """
    if not project_path or not project_path.exists():
        return ""

    topic = detect_step_topic(step_label, prompt_name)
    rd_filter = TOPIC_RD_FILTER.get(topic)  # None = include all

    metadata_dir = project_path / "metadata"
    if not metadata_dir.exists():
        return ""

    # Collect the relevant RD files
    rd_files: list[Path] = []
    for rd_file in sorted(metadata_dir.glob("RD*.md")):
        if rd_filter is None:
            rd_files.append(rd_file)
        else:
            # Filter by rd_file.name prefix (RD01, RD02, ...)
            for rd_id in rd_filter:
                if rd_file.name.startswith(rd_id):
                    rd_files.append(rd_file)
                    break

    if not rd_files:
        return ""

    parts: list[str] = [
        f"\n## PROJECT CONTEXT ({topic.upper()} STEP — relevant RD files)\n"
    ]
    remaining = max_chars
    included_count = 0

    for rd_file in rd_files:
        try:
            content = rd_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        header = f"\n### {rd_file.name}\n"
        # Trim very long files
        available = remaining - len(header) - 100
        if available <= 0:
            parts.append(f"\n_(... {rd_file.name} and others — context limit exceeded)_\n")
            break

        snippet = content[:available]
        if len(content) > available:
            snippet += f"\n_(... trimmed — full content: {rd_file.name})_"
        parts.append(header + snippet)
        remaining -= len(header) + len(snippet)
        included_count += 1

    if included_count == 0:
        return ""

    parts.append(
        f"\n**Context:** Topic=`{topic}`, {included_count}/{len(rd_files)} RD files included. "
        f"Use the context above in code generation.\n"
    )
    return "".join(parts)


if __name__ == "__main__":
    # Self-test
    import sys
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        m = parse_prompt_frontmatter(path)
        print(f"Name: {m.name}")
        print(f"Role: {m.role}")
        print(f"Extracts: {m.extracts}")
        print(f"Input: {m.input_source}")
        print(f"Prerequisite: {m.prerequisite}")
        print(f"Output: {m.output_artifacts}")
        print(f"Schema: {m.schema_target}")
    else:
        print("Usage: python prompt_meta.py <prompt_path.md>")
