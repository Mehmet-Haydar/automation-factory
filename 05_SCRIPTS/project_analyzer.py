#!/usr/bin/env python3
"""
project_analyzer.py — Project Completeness + Gap Analysis

Examines active customer project status:
- What is in _input/, what is missing
- Metadata/ current state
- Which RD can be generated, which are missing
- Recommended next steps
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Import (same folder)
try:
    from platform_detector import scan_input_folder, ProjectScan, get_recommended_prompt
except ImportError:
    scan_input_folder = None
    ProjectScan = None


# Source file types each RD needs (most common)
RD_INPUT_NEEDS = {
    "RD01": {
        "title": "IO List",
        "needs": ["_parsed.md", "customer Excel or EPLAN export"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_IO_FROM_CODE.md",
        "depends_on_rds": [],
    },
    "RD02": {
        "title": "DataDict",
        "needs": ["_parsed.md", "RD01 (LinkedTag)"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md",
        "depends_on_rds": ["RD01"],
    },
    "RD03": {
        "title": "Flowchart",
        "needs": ["_parsed.md", "RD02 + operator interview"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md",
        "depends_on_rds": ["RD02"],
    },
    "RD04": {
        "title": "Mode",
        "needs": ["_parsed.md", "operator interview"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_MODE_FROM_CODE.md",
        "depends_on_rds": [],
    },
    "RD05": {
        "title": "Safety ⚠️",
        "needs": ["_parsed.md", "Risk assessment document", "Safety engineer approval"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_SAFETY_FROM_CODE.md",
        "depends_on_rds": [],
        "human_required": True,
    },
    "RD06": {
        "title": "Motion",
        "needs": ["_parsed.md", "Drive parameter files (if any)"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_MOTION_FROM_CODE.md",
        "depends_on_rds": ["RD01", "RD02"],
    },
    "RD07": {
        "title": "Timing",
        "needs": ["_parsed.md", "RD03 + RD08"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_TIMING_FROM_CODE.md",
        "depends_on_rds": ["RD03"],
    },
    "RD08": {
        "title": "Alarm",
        "needs": ["_parsed.md", "WinCC/FactoryTalk alarm DB export"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_ALARM_FROM_CODE.md",
        "depends_on_rds": ["RD05", "RD07"],
    },
    "RD09": {
        "title": "Comms",
        "needs": ["_parsed.md", "HW config export"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_COMMS_FROM_CODE.md",
        "depends_on_rds": [],
    },
    "RD10": {
        "title": "FBSpec",
        "needs": ["_parsed.md"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_FBSPEC_FROM_CODE.md",
        "depends_on_rds": [],
    },
    "RD11": {
        "title": "HMI",
        "needs": ["HMI export (WinCC .MCP or FactoryTalk)"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_HMI_FROM_CODE.md",
        "depends_on_rds": ["RD01", "RD08"],
    },
    "RD12": {
        "title": "UseCase",
        "needs": ["Operator workshop notes", "Operating manual"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_USECASE_FROM_CODE.md",
        "depends_on_rds": ["RD03", "RD04"],
        "human_required": True,
    },
    "RD13": {
        "title": "Annotation (retrofit)",
        "needs": ["_parsed.md", "Legacy code raw text"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md",
        "depends_on_rds": [],
    },
    "RD14": {
        "title": "Modernization (retrofit)",
        "needs": ["RD13 output"],
        "ai_prompt": "analyze/PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md",
        "depends_on_rds": ["RD13"],
    },
}


@dataclass
class RDStatus:
    """Status analysis of a single RD."""
    rd_id: str
    title: str
    file_exists: bool = False
    file_size: int = 0
    status: str = "empty"  # empty / template / in_progress / done / draft_unverified
    can_run: bool = False  # can it be generated with AI (are inputs ready)
    missing_inputs: list[str] = field(default_factory=list)
    blocking_rds: list[str] = field(default_factory=list)  # cannot be generated until these complete
    human_required: bool = False
    ai_prompt: str = ""


@dataclass
class ProjectAnalysis:
    """Holistic project analysis."""
    project_path: Path
    has_input: bool = False
    has_parsed_md: bool = False
    input_scan: Optional["ProjectScan"] = None
    rd_statuses: dict[str, RDStatus] = field(default_factory=dict)
    overall_pct: float = 0.0
    recommended_next: list[str] = field(default_factory=list)  # recommended next steps


def detect_rd_file_status(rd_file: Path) -> tuple[str, int]:
    """The fill-in status of an RD MD file."""
    if not rd_file.exists():
        return "empty", 0
    try:
        content = rd_file.read_text(encoding="utf-8")
        size = len(content)
        # Our own draft-writer header is authoritative: a file that carries
        # the DRAFT_UNVERIFIED banner IS a draft — template markers must not
        # override it. (Blind test 4711: the AI legitimately described
        # legacy stub FBs as "Placeholder" in prose and the bare-word marker
        # misclassified a 15 KB real draft as "template", freezing gate 1.)
        if "DRAFT_UNVERIFIED" in content and "Status: DRAFT_UNVERIFIED" in content:
            return "draft_unverified", size
        # Template markers — structural placeholders only, never bare prose
        # words. "(placeholder)" matches our template stubs; the bare word
        # appears in honest engineering text.
        markers = ["<PROJECT_CODE>", "<PROJE_KODU>", "<Engineer Name>",
                   "<Mühendis Adı>", "(placeholder)"]
        if any(m in content for m in markers):
            return "template", size
        if size < 3000:
            return "template", size
        elif size < 8000:
            return "in_progress", size
        else:
            return "done", size
    except Exception:
        return "empty", 0


def _load_state_pcts(project_path: Path) -> dict[str, float]:
    """Read the per-RD completion_pct map from PROJECT_STATE.json.

    Matching is done against the RD_INPUT_NEEDS keys (RD01..RD14); since the
    keys in state are usually like 'RD01_IO', 'RD02_DataDict', we apply
    prefix-based matching.
    """
    import json
    state_file = project_path / "PROJECT_STATE.json"
    if not state_file.exists():
        return {}
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    rd_status = state.get("rd_status") or {}
    out: dict[str, float] = {}
    for key, info in rd_status.items():
        if not isinstance(info, dict):
            continue
        pct = info.get("completion_pct")
        if not isinstance(pct, (int, float)):
            continue
        # 'RD05_Safety' -> 'RD05'
        prefix = key.split("_", 1)[0]
        out[prefix] = float(pct)
    return out


def analyze_project(project_path: Path) -> ProjectAnalysis:
    """Run a full analysis of a customer project."""
    analysis = ProjectAnalysis(project_path=project_path)

    # 1. _input/ check — S-8 (B-L10): the platform scan also covers
    # _raw/legacy_code/ so the dashboard badge and the pre-analysis
    # pipeline read the same files (they were two diverging truths).
    input_dir = project_path / "_input"
    raw_legacy_dir = project_path / "_raw" / "legacy_code"
    if input_dir.exists():
        analysis.has_input = True
    if scan_input_folder and (input_dir.exists() or raw_legacy_dir.exists()):
        analysis.input_scan = scan_input_folder(
            input_dir, extra_dirs=[raw_legacy_dir])

    # Extractor source is satisfied by EITHER the platform-parser output
    # (_input/_parsed.md) OR raw legacy code (_raw/legacy_code/), which the
    # retrofit pre-analysis pipeline reads directly. Without this, a
    # pre-analysed retrofit project (RD drafts already written from raw legacy)
    # kept reporting "missing _parsed.md (run the platform parser first)" on
    # every RD, even though the source was present (S-8 / B-L10: the scan
    # already covers both paths).
    parsed_md = input_dir / "_parsed.md"
    _has_raw_legacy = raw_legacy_dir.is_dir() and any(raw_legacy_dir.iterdir())
    analysis.has_parsed_md = parsed_md.exists() or _has_raw_legacy

    # 2. Status for each RD
    metadata_dir = project_path / "metadata"
    # Explicit completion_pct values in state.json are the primary progress
    # signal; otherwise the file-size heuristic is the fallback.
    state_pcts = _load_state_pcts(project_path)
    pct_sum = 0.0
    pct_n = 0

    for rd_id, info in RD_INPUT_NEEDS.items():
        # Find the file
        rd_files = list(metadata_dir.glob(f"{rd_id}*.md")) if metadata_dir.exists() else []
        rd_file = rd_files[0] if rd_files else None

        status = RDStatus(
            rd_id=rd_id,
            title=info["title"],
            ai_prompt=info["ai_prompt"],
            human_required=info.get("human_required", False),
        )

        # Progress contribution for this RD
        if rd_id in state_pcts:
            # if state.json explicitly gave a pct, use it
            pct_sum += state_pcts[rd_id]
            pct_n += 1
        elif rd_file:
            file_status_tmp, _ = detect_rd_file_status(rd_file)
            heur = {"done": 100.0, "draft_unverified": 50.0,
                    "in_progress": 50.0, "template": 10.0, "empty": 0.0}
            pct_sum += heur.get(file_status_tmp, 0.0)
            pct_n += 1
        else:
            pct_n += 1  # counted as empty (0 contribution)

        if rd_file:
            status.file_exists = True
            file_status, file_size = detect_rd_file_status(rd_file)
            status.status = file_status
            status.file_size = file_size
        else:
            status.status = "empty"

        # Is it runnable?
        depends_ok = True
        for dep in info["depends_on_rds"]:
            dep_files = list(metadata_dir.glob(f"{dep}*.md")) if metadata_dir.exists() else []
            if not dep_files:
                depends_ok = False
                status.blocking_rds.append(dep)
            else:
                dep_status, _ = detect_rd_file_status(dep_files[0])
                if dep_status in ("empty", "template"):
                    depends_ok = False
                    status.blocking_rds.append(dep)

        # Is _parsed.md required?
        needs_parsed = "_parsed.md" in info["needs"]
        if needs_parsed and not analysis.has_parsed_md:
            status.missing_inputs.append("_parsed.md (run the platform parser first)")
            status.can_run = False
        elif depends_ok:
            status.can_run = True
        else:
            status.can_run = False

        analysis.rd_statuses[rd_id] = status

    analysis.overall_pct = (pct_sum / pct_n) if pct_n else 0.0

    # 3. Recommended next steps
    if not analysis.has_input or (analysis.input_scan and not analysis.input_scan.files):
        analysis.recommended_next.append(
            "_input/ folder is empty. Put the customer's legacy PLC code/files in it."
        )
    elif not analysis.has_parsed_md:
        # Platform detection
        if analysis.input_scan and analysis.input_scan.primary_platform:
            plat = analysis.input_scan.primary_platform
            prompt = get_recommended_prompt(plat)
            analysis.recommended_next.append(
                f"1. Run the platform parser: {prompt}\n"
                f"   (Detected platform: {plat}, confidence: {analysis.input_scan.confidence})"
            )
        else:
            analysis.recommended_next.append(
                "1. Platform not detected — pick a prompt manually (analyze/)"
            )
    else:
        # _parsed.md exists, RDs are next
        # Highest priority (no dependency and missing)
        for rd_id, status in analysis.rd_statuses.items():
            if status.status in ("empty", "template") and status.can_run:
                analysis.recommended_next.append(
                    f"Generate {rd_id} {status.title}: {status.ai_prompt}"
                )
                if len(analysis.recommended_next) >= 3:
                    break

        if not analysis.recommended_next:
            # If all RDs are complete
            if analysis.overall_pct >= 95:
                analysis.recommended_next.append("All RDs completed. Run Gate 4 Validation.")
            else:
                analysis.recommended_next.append("Manual review + filling in #UNKNOWNS is next.")

    return analysis


def format_analysis_report(analysis: ProjectAnalysis) -> str:
    """Render the analysis as human-readable text."""
    lines = []
    lines.append(f"PROJECT: {analysis.project_path.name}")
    lines.append(f"Path: {analysis.project_path}")
    lines.append(f"Progress: {analysis.overall_pct:.0f}%")
    lines.append("")

    # _input status
    lines.append("INPUT FOLDER (_input/):")
    if not analysis.has_input:
        lines.append("   _input/ folder missing")
    elif analysis.input_scan and not analysis.input_scan.files:
        lines.append("   Folder empty — no customer data added")
    elif analysis.input_scan:
        lines.append(f"   {len(analysis.input_scan.files)} files, "
                     f"{analysis.input_scan.total_size_mb:.2f} MB")
        if analysis.input_scan.primary_platform:
            from platform_detector import PLATFORM_DISPLAY
            disp = PLATFORM_DISPLAY.get(analysis.input_scan.primary_platform, analysis.input_scan.primary_platform)
            lines.append(f"   Detected platform: {disp}")
            lines.append(f"      Confidence: {analysis.input_scan.confidence.upper()}")
    if analysis.has_parsed_md:
        lines.append("   _parsed.md present (Gate 2 started)")
    else:
        lines.append("   _parsed.md MISSING — platform parser needed first")

    lines.append("")
    lines.append("14-POINT PACK STATUS:")
    lines.append("")

    status_icon = {
        "empty": "[ ]",
        "template": "[T]",
        "in_progress": "[~]",
        "done": "[x]",
        "draft_unverified": "[!]",
    }

    for rd_id, status in analysis.rd_statuses.items():
        icon = status_icon.get(status.status, "[ ]")
        run_mark = "RUNNABLE" if status.can_run and status.status in ("empty", "template") else ""
        human_mark = "  HUMAN REQUIRED" if status.human_required else ""
        line = f"   {icon} {rd_id} {status.title:32}  {status.status:18} {run_mark}{human_mark}"
        lines.append(line)
        # Show blockers if any
        if status.blocking_rds and status.status in ("empty", "template"):
            lines.append(f"        Blocked by: {', '.join(status.blocking_rds)} must complete first")
        if status.missing_inputs:
            lines.append(f"        Missing input: {', '.join(status.missing_inputs)}")

    lines.append("")
    lines.append("RECOMMENDED NEXT STEPS:")
    if not analysis.recommended_next:
        lines.append("   (no recommendation)")
    else:
        for rec in analysis.recommended_next:
            lines.append(f"   {rec}")

    return "\n".join(lines)


# NOTE (2026-07-10 audit, M-03/S-6): the former GATE5_CODE_GEN_STEPS table
# and get_pipeline_order() were removed. They described a pre-v3.1
# prompt-driven code-generation pipeline that no runtime path ever called
# and that contradicted the locked library-first architecture: device FBs
# are copied verbatim from blocks/+contracts/ by program_assembler.py; the
# only AI-generated code artifact is the sequence FB. The prompt files
# under 04_AI_PROMPTS/code_gen/ remain as a manual-use library (see
# 04_AI_PROMPTS/_README.md).


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analysis = analyze_project(Path(sys.argv[1]))
        print(format_analysis_report(analysis))
    else:
        print("Usage: python project_analyzer.py <project path>")
