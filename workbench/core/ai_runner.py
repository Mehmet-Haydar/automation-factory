"""
ai_runner.py — Mode 2: Automatic flow runner via direct API.

Executes predefined step sequences (workflows) in order,
no user intervention required. Results are saved to the project folder.
"""

from __future__ import annotations

import logging
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "05_SCRIPTS"
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from ai_client import AIClient, PROVIDER_CATALOG
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    from ai_decision_log import log_ai_action, AuditLogError  # type: ignore
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False

try:
    from data_classification_guard import check_ai_send  # type: ignore
    CLASSIFICATION_GUARD_AVAILABLE = True
except ImportError:
    CLASSIFICATION_GUARD_AVAILABLE = False


# ---------------------------------------------------------------------------
# I-2 fix: _sanitize_chain_output — chained prompt injection protection
# ---------------------------------------------------------------------------

# Control tokens used for prompt injection (case-insensitive)
_INJECTION_TOKENS = re.compile(
    r"(<\s*/?system\s*>|<\s*/?inst\s*>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>)",
    re.IGNORECASE,
)

# Markdown structural control tokens (separator, heading) — prevents re-parsing of the output
_MD_CONTROL = re.compile(r"^(---+|###\s)", re.MULTILINE)

# ---------------------------------------------------------------------------
# K-1 fix: _strip_code_fence — LLM markdown fence stripper (for code outputs)
# ---------------------------------------------------------------------------

# Capture the first markdown code-fence block in the LLM response
# Supported openings: ```scl  ```iec  ```st  ```  etc.
_CODE_FENCE_RE = re.compile(
    r"```[a-zA-Z0-9_+\-]*\r?\n"   # opening fence line (lang tag optional)
    r"(.*?)"                        # code body (captured)
    r"\r?\n[ \t]*```",              # closing fence line
    re.DOTALL,
)

# Steps with these output suffixes get the fence stripped before being written
_CODE_OUTPUT_SUFFIXES: frozenset = frozenset({".scl", ".st", ".awl"})

# Transient provider failures worth ONE-step retries (read timeouts, dropped
# connections, rate limits, 5xx). Anything else fails fast — a genuine auth
# or prompt error must not loop.
_TRANSIENT_API_RE = re.compile(
    r"timed?\s?out|timeout|connection|verbindung|reset|abgebrochen|"
    r"geschlossen|closed|429|rate.?limit|overload|bad gateway|50[234]",
    re.IGNORECASE)
_API_MAX_ATTEMPTS = 3


def _strip_code_fence(text: str) -> str:
    """Extract the first markdown code fence from the LLM output; if there is no fence, return the text as-is."""
    m = _CODE_FENCE_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def _sanitize_chain_output(text: str) -> str:
    """Prepare a step's output for safe injection into the next step's prompt.

    - Neutralizes prompt-injection control tokens (``<system>``, ``[INST]`` etc.)
    - Escapes markdown separator / heading line starts (prevents structure corruption in the second step)
    - Escapes ``{`` and ``}`` characters with respect to Python format strings
      (prevents stray ``{placeholder}``s from hijacking the template)
    - Wraps multi-line blocks in a code fence to preserve the template boundary
    """
    if not text:
        return ""

    # 1. Strip prompt-injection control tokens
    sanitized = _INJECTION_TOKENS.sub(
        lambda m: "[REMOVED:" + m.group(0).replace("<", "&lt;").replace(">", "&gt;") + "]",
        text,
    )

    # 2. Escape markdown structural control tokens
    sanitized = _MD_CONTROL.sub(
        lambda m: "\\" + m.group(0),
        sanitized,
    )

    # 3. Escape Python .format() placeholders: { → {{ and } → }}
    #    (only things that look like real format placeholders: {word})
    sanitized = re.sub(r"\{([^{}]*)\}", r"{{\1}}", sanitized)

    # 4. Wrap multi-line blocks in a code fence (template boundary integrity)
    if "\n" in sanitized:
        sanitized = "```\n" + sanitized.rstrip("\n") + "\n```"

    return sanitized


# Note: a CRLF-aware _CODE_FENCE_RE + _strip_code_fence (K-1 fix) is defined above
# and is what the save path uses. The earlier gemini-branch helper
# (_extract_code_block / a \n-only fence regex) was dropped on merge to avoid a
# duplicate, non-CRLF-aware definition shadowing the K-1 one.


def _step_output_path(output_dir, stem: str, suffix: str):
    """(name, path) of a step's persisted copy — STABLE, one living file.

    Report hygiene (E2E finding 2026-07-07): copies live in
    REPORTS/_ai_steps/<stem><suffix> and each run REPLACES the previous one.
    Timestamped leftovers of the same artifact from the old naming scheme
    (<stem>_YYYYMMDD_HHMM<suffix>, straight in REPORTS/) are deleted so a
    regeneration leaves exactly ONE copy behind, not a growing pile.
    """
    steps_dir = output_dir / "_ai_steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{stem}{suffix}"
    for _old in output_dir.glob(f"{stem}_2*{suffix}"):
        try:
            _old.unlink()
        except Exception:
            pass
    return out_name, steps_dir / out_name


@dataclass
class WorkflowStep:
    name: str
    prompt_template: str
    output_suffix: str        # suffix for the output file (e.g. "_analysis.md")
    system_prompt: str = "You are a PLC automation engineer. Respond in accordance with Factory standards."
    max_tokens: int = 16384   # token budget; raise for large code-generation steps
                               # (4× 2026-07-07 — the AI client clamps to each
                               # provider's real output ceiling, so a generous
                               # budget can never cause an API error)
                               # Note: thinking-enabled models (Gemini 2.5, Claude 3.7) consume
                               # thinking tokens from this budget — set higher for complex FBs.
    provider: Optional[str] = None    # None → use AutoFlowRunner global provider
    model: Optional[str] = None       # None → use AutoFlowRunner global model
    use_multimodal: bool = False      # True → AIClient.chat_with_files() (Gemini Vision)
    metadata_target: Optional[str] = None  # M2: RD id ("RD01"…) — step output is
                                           # also offered to the caller's
                                           # draft_writer for metadata/ placement


# B-13 (field audit): generic single-prompt chains kept for tests/dev
# tooling but HIDDEN from the GUI — a new user can't tell them apart from
# the 14-RD methodology, runs one, gets a low-quality draft and concludes
# the whole tool is bad. The gate panels are the only user-facing entry.
DEV_ONLY_WORKFLOWS = {
    "Analyze → Validate",
    "IO Extraction → SCL Generation",
    "Full Pipeline",
}

BUILTIN_WORKFLOWS = {
    "Analyze → Validate": [
        WorkflowStep(
            name="File Analysis",
            prompt_template="Analyze the following file and check its compliance with Factory standards:\n\n{content}\n\nPresent the results in Markdown table format.",
            output_suffix="_analysis.md",
        ),
        WorkflowStep(
            name="Validation",
            prompt_template="Based on the previous analysis, list the missing items and provide correction suggestions:\n\n{prev_output}",
            output_suffix="_validation.md",
        ),
    ],
    "IO Extraction → SCL Generation": [
        WorkflowStep(
            name="IO Extraction",
            prompt_template="Extract all IO points from the following file:\n\n{content}\n\nFor each IO: Tag name, Type, Address, Description.",
            output_suffix="_io_list.md",
        ),
        WorkflowStep(
            name="SCL Code Generation",
            prompt_template="Generate TIA Portal V18 SCL FUNCTION_BLOCK code from this IO list:\n\n{prev_output}\n\nMust be IEC 61131-3 compliant. Return ONLY the SCL code, no explanation.",
            output_suffix="_generated.scl",
            max_tokens=65536,
        ),
    ],
    "Full Pipeline": [
        WorkflowStep(
            name="Analysis",
            prompt_template="Analyze the following file:\n\n{content}",
            output_suffix="_analysis.md",
        ),
        WorkflowStep(
            name="IO Extraction",
            prompt_template="Extract IO points:\n\n{prev_output}",
            output_suffix="_io_list.md",
        ),
        WorkflowStep(
            name="SCL Generation",
            prompt_template="Generate TIA Portal V18 SCL FUNCTION_BLOCK code:\n\n{prev_output}\n\nReturn ONLY the SCL code, no explanation.",
            output_suffix="_generated.scl",
            max_tokens=65536,
        ),
        WorkflowStep(
            name="Validation",
            prompt_template="Validate the generated code:\n\n{prev_output}",
            output_suffix="_validation.md",
        ),
    ],
    # Retrofit Pre-Analysis: Gemini reads drawings/photos, Claude consolidates.
    # Step 1 uses multimodal (Gemini Vision) — source_files must be provided.
    # Step 2 reads legacy text code from {content} (plain text).
    # Step 3 consolidates both outputs into a structured RD01 draft.
    "Retrofit Pre-Analysis": [
        WorkflowStep(
            name="Drawing & Photo Analysis",
            provider="google",
            model=None,
            use_multimodal=True,
            max_tokens=65536,
            system_prompt=(
                "You are an industrial automation engineer analysing legacy machine "
                "documentation for a retrofit project. Extract all IO signals, "
                "hardware components, and functional descriptions you can identify. "
                "Be precise about signal types (DI/DQ/AI/AO) and safety-related signals."
            ),
            prompt_template=(
                "Analyse the attached drawings and photos from a legacy machine. "
                "Extract every IO signal you can identify.\n\n"
                "Return a Markdown table with columns: "
                "Tag | Description | IO_Type | Address_Hint | SafetyRelated | Source\n\n"
                "IO_Type must be one of: DI, DQ, AI, AO, SAFE_DI, SAFE_DQ.\n"
                "SafetyRelated: Y or N.\n"
                "Address_Hint: best guess from drawing (e.g. E-Stop panel left side).\n"
                "Source: filename of the drawing/photo where you found this signal.\n\n"
                "After the table add a ## Hardware Notes section listing any PLC racks, "
                "motor starters, drives, or safety relays you can identify."
            ),
            output_suffix="_drawings_analysis.md",
        ),
        WorkflowStep(
            name="Legacy Code Analysis",
            provider=None,
            model=None,
            use_multimodal=False,
            # Big machines exceed 8k output easily. Providers with a larger
            # window (Claude 64k / Gemini 65k) get the full budget; ai_client
            # clamps to each provider's hard cap (DeepSeek stays at 8k and
            # the truncation warning + RD01 autocomplete cover the gap).
            # 2026-07-03 A/B/C: enriched S5 inputs truncated even at 16k on
            # Google — raised to 32k (still far below the 65k cap).
            max_tokens=65536,
            system_prompt=(
                "You are a PLC engineer analysing legacy automation code "
                "for a retrofit project. Extract functional blocks, IO usage, "
                "and describe what each part of the program does.\n\n"
                "DACH legacy shorthand you MUST interpret correctly: "
                "E=digital input, A=digital output, M=flag/merker (internal, "
                "NOT IO), EW/PEW=analog input word, AW/PAW=analog output "
                "word, T=timer, Z=counter (internal). "
                "RM/Rueckmeldung=feedback, Schuetz(K1,K2)=contactor, "
                "Motorschutz/Bimetall=overload protection, "
                "FU/Frequenzumrichter=variable frequency drive, "
                "NotAus=emergency stop, LSL/LSH=level switch low/high, "
                "ZSO/ZSC=position switch open/closed, Stoerung=fault, "
                "Freigabe=enable, Stern/Dreieck=star/delta starting, "
                "Quittierung=acknowledge. NEVER count every occurrence of an "
                "operand as a separate signal — one address = one signal."
            ),
            prompt_template=(
                "Analyse this legacy PLC code or export file:\n\n{content}\n\n"
                "Return:\n"
                "1. ## IO Usage — table: Tag | IO_Type | Description | Used_In_Block\n"
                "   Include EVERY physical E/A/EW/AW operand exactly once; "
                "do NOT list M-flags, timers or counters as IO.\n"
                "2. ## Function Blocks — list each FB/FC with a one-line description\n"
                "3. ## Safety Functions — list any safety-relevant logic found\n"
                "4. ## Modernization Notes — what needs updating for TIA Portal V18"
            ),
            output_suffix="_legacy_analysis.md",
        ),
        WorkflowStep(
            name="RD01 Draft Consolidation",
            provider=None,
            model=None,
            use_multimodal=False,
            # A ~190-row IO table needs >8k output tokens — see the note on
            # Legacy Code Analysis above. 32k for the same reason as there.
            max_tokens=65536,
            system_prompt=(
                "You are a senior automation engineer creating a structured "
                "IO list document from multiple analysis sources. "
                "Resolve conflicts by preferring drawing analysis for addresses "
                "and code analysis for tag names."
            ),
            prompt_template=(
                "Consolidate these two analyses into a single RD01 IO List draft.\n\n"
                "--- DRAWING & PHOTO ANALYSIS (step 1) ---\n{out_1}\n\n"
                "--- LEGACY CODE ANALYSIS (step 2) ---\n{out_2}\n\n"
                "Produce ONLY a single Markdown table with EXACTLY these columns "
                "(no extra sections, no template stubs, no repeated headers):\n\n"
                "| Tag | Address | Type | Dir | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | Safety | SrcModule | OldTag | Notes | Status |\n"
                "|-----|---------|------|-----|-----------|-------------|-------------|---------|----------|----------|--------|----------|--------|-------|--------|\n\n"
                "Rules:\n"
                "- Tag: S7 tag name (CamelCase, e.g. BandMotorRueckm)\n"
                "- Address: S7 format (%I1.4, %Q4.3, %IW10, etc.)\n"
                "- Type: DI / DQ / AI / AO\n"
                "- Dir: IN / OUT\n"
                "- Equipment: REQUIRED for every drive/valve/pump field "
                "signal — the PHYSICAL DEVICE id as a SHORT id (M1, P1, Y2; "
                "NEVER a prose name). Group every signal of one device under "
                "the SAME id (contactor, feedback, overload of motor M1 all "
                "get Equipment=M1). Panel references inside the description "
                "give the id directly: '… * 7-M3 (EINLAUF)' -> M3, "
                "'… 5-M1' -> M1. Valve descriptions sharing one actuator "
                "(e.g. 'GREIFER I - AUF' output + 'GREIFER I OBEN' feedback) "
                "get the same Yn id from the related output. An EMPTY "
                "Equipment cell means the signal CANNOT be auto-wired to a "
                "library block — leave it empty ONLY for station-level "
                "signals (operator buttons, horn, lamps) or when the device "
                "is genuinely unidentifiable.\n"
                "- Safety: YES or NO\n"
                "- Status: DRAFT_UNVERIFIED for every row\n"
                "- Leave columns blank if unknown — do NOT invent values\n\n"
                "After the table add ONLY:\n"
                "## Conflicts\n"
                "(contradictions between drawing and code analysis)\n"
                "## Review Required\n"
                "(items needing engineer verification)"
            ),
            output_suffix="_RD01_draft.md",
            metadata_target="RD01",
        ),
        # M2 — the chain no longer stops at RD01: the same legacy analysis
        # feeds RD02 (data dictionary), RD03 (flowchart) and RD13 (line
        # annotation) drafts, written into metadata/ as DRAFT_UNVERIFIED.
        WorkflowStep(
            name="RD02 Data Dictionary Draft",
            provider=None,
            model=None,
            # 2026-07-03: truncated at 8k on enriched inputs — doubled.
            max_tokens=65536,
            system_prompt=(
                "You are a PLC engineer building a data dictionary for a "
                "TIA Portal retrofit. Extract INTERNAL data (not physical IO): "
                "data blocks, markers/flags, timers, counters, computed values."
            ),
            prompt_template=(
                "From this legacy PLC code and its analysis, draft the RD02 "
                "Data Dictionary.\n\n"
                "--- LEGACY CODE ---\n{content}\n\n"
                "--- CODE ANALYSIS (step 2) ---\n{out_2}\n\n"
                "Produce a Markdown table:\n"
                "Name | LegacyAddress | DataType | Scope | Description | Status\n\n"
                "Scope is one of: DB, MARKER, TIMER, COUNTER, TEMP, UDT_CANDIDATE.\n"
                "Status must be DRAFT_UNVERIFIED for every row.\n"
                "After the table add a ## UDT Candidates section grouping "
                "related fields that should become a UDT in the new program."
            ),
            output_suffix="_RD02_draft.md",
            metadata_target="RD02",
        ),
        WorkflowStep(
            name="RD03 Flowchart Draft",
            provider=None,
            model=None,
            max_tokens=65536,
            system_prompt=(
                "You are a controls engineer reconstructing the control "
                "sequence of a legacy machine from its PLC code. Be faithful "
                "to the code — mark anything inferred as ASSUMPTION."
            ),
            prompt_template=(
                "Reconstruct the machine's control sequence from this legacy "
                "code and analysis, as the RD03 Flowchart draft.\n\n"
                "--- LEGACY CODE ---\n{content}\n\n"
                "--- CODE ANALYSIS (step 2) ---\n{out_2}\n\n"
                "Produce EXACTLY these sections:\n\n"
                "## Step Sequence\n"
                "A Markdown table with these EXACT columns (no extras, no "
                "Mermaid — the diagram is auto-generated from this table):\n"
                "| StepID | StepName | EntryCondition | Actions | ExitCondition "
                "| NextStep | Status |\n"
                "Rules: StepID = S001, S002 … S999. NextStep = next StepID or "
                "(end). Status = DRAFT_UNVERIFIED for every row. "
                "No pipes inside cell text.\n\n"
                "## Modes\n"
                "Automatic / manual / setup behaviour found in code.\n\n"
                "## Assumptions\n"
                "Everything inferred rather than read directly from code."
            ),
            output_suffix="_RD03_draft.md",
            metadata_target="RD03",
        ),
        WorkflowStep(
            name="RD13 Legacy Annotation Draft",
            provider=None,
            model=None,
            max_tokens=65536,
            system_prompt=(
                "You are a senior PLC engineer documenting legacy code "
                "block-by-block for a retrofit handover. Precision over "
                "completeness: skip nothing silently — mark unclear parts."
            ),
            prompt_template=(
                "Annotate this legacy PLC code block by block, as the RD13 "
                "Annotation draft.\n\n"
                "--- LEGACY CODE ---\n{content}\n\n"
                "Produce a Markdown table:\n"
                "Block | Networks/Lines | Meaning | Modern Equivalent | Risk | Status\n\n"
                "Risk: NONE / LOW / HIGH (HIGH = timing-critical, safety-"
                "related, or unclear semantics).\n"
                "Status must be DRAFT_UNVERIFIED for every row.\n"
                "After the table add ## Unclear Sections listing code you "
                "could not interpret with confidence."
            ),
            output_suffix="_RD13_draft.md",
            metadata_target="RD13",
        ),
    ],
}


# ---------------------------------------------------------------------------
# B1 — Schema-driven topic extractors (Gate 2: "Topic Extraction")
# ---------------------------------------------------------------------------
# Generation is two-staged and gated by engineer approval:
#   Gate 1 "Retrofit Pre-Analysis" (above) produces RD01/RD02/RD03/RD13.
#   Gate 2 "Topic Extraction" (this block) produces the remaining topic RDs —
#   Mode, Safety, Motion, Timing, Alarm, Comms, FBSpec, HMI, UseCase,
#   Modernization (RD04-RD12, RD14) — and ONLY runs once the engineer has
#   approved the Gate-1 RDs, USING those approved outputs as input.
# Each extractor already exists as a rich, schema-coupled prompt on the shelf
# (04_AI_PROMPTS/analyze/PROMPT_EXTRACT_*_FROM_CODE.md, mapped per RD in
# project_analyzer.RD_INPUT_NEEDS). Re-inlining them would duplicate ~2000
# lines and drift from the MD schemas, so each step loads its System Prompt
# block straight from the shelf file and feeds it the combined source the
# caller builds ({content} = legacy code + the approved Gate-1 RD drafts).
# Every output is written to metadata/ as DRAFT_UNVERIFIED — INCLUDING RD05
# Safety: the AI assists by detecting/reporting the safety signals it finds,
# but the gate engine (W-A2) and the FAT / customer-report preconditions block
# every approval gate until a certified safety engineer signs RD05 off. The AI
# never has the final word, and the shelf safety prompt forbids guessing SIL/PLr.

_PROMPTS_ROOT = SCRIPT_DIR.parent / "04_AI_PROMPTS"

_SYSTEM_PROMPT_SECTION_RE = re.compile(r"^##\s*4\.\s*System Prompt\b.*$", re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r"^##\s", re.MULTILINE)


def _extract_system_prompt_block(md_text: str) -> str:
    """Return the '## 4. System Prompt' body of a shelf extractor prompt.

    Slices the text between the section-4 header and the next '## ' header and
    drops a single wrapping ``` fence if the block is fully fenced (an inner
    OUTPUT FORMAT fence is kept as literal instruction text). Returns "" when
    the section is absent so the caller can fall back to a built-in prompt.
    """
    m = _SYSTEM_PROMPT_SECTION_RE.search(md_text)
    if not m:
        return ""
    rest = md_text[m.end():]
    nxt = _NEXT_SECTION_RE.search(rest)
    body = (rest[:nxt.start()] if nxt else rest).strip()
    lines = body.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _load_extractor_system_prompt(rd_id: str, fallback: str) -> str:
    """System prompt for an RD extractor, read from its shelf prompt file.

    Resolves rd_id -> file via project_analyzer.RD_INPUT_NEEDS[rd_id]
    ['ai_prompt']. Any failure (missing module / file / section) returns
    *fallback*, so a workflow definition can never break at import time.
    """
    try:
        from project_analyzer import RD_INPUT_NEEDS  # type: ignore
        rel = (RD_INPUT_NEEDS.get(rd_id, {}) or {}).get("ai_prompt", "")
        if rel:
            block = _extract_system_prompt_block(
                (_PROMPTS_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            )
            if block:
                return block
    except Exception:
        pass
    return fallback


def _topic_extract_user_template(rd_id: str, title: str) -> str:
    """Uniform user prompt for a Gate-2 topic extractor step. Only ``{content}``
    is a runtime placeholder (the caller builds it from the legacy code + the
    approved Gate-1 RD drafts); rd_id/title are baked in here so the template
    stays safe for ai_runner's .format() call."""
    return (
        f"Extract the {rd_id} ({title}) topic for a TIA Portal retrofit, using "
        f"the legacy PLC code and the approved Gate-1 analysis (IO list, data "
        f"dictionary, flowchart, annotation) provided below. This is a first-pass "
        f"DRAFT for engineer review.\n\n"
        "{content}\n\n"
        "Follow EXACTLY the rules, column set and output format defined in your "
        "system instructions. Output ONLY the draft Markdown (the table plus any "
        "small sections that format defines — no extra commentary). Set every "
        "row's Status column to DRAFT_UNVERIFIED. Leave a cell blank rather than "
        "invent a value; never guess safety levels (SIL/PLr) or physical addresses."
    )


# (rd_id, title, fallback system prompt used only if the shelf file is missing).
_TOPIC_EXTRACT_SPECS: list[tuple[str, str, str]] = [
    ("RD04", "Operating Modes",
     "You extract OMAC PackML operating modes (ModeID, ModeName, Priority, "
     "PackMLState, entry/exit conditions, HMI color/text) from legacy PLC code "
     "into the RD04 schema. Mark every row DRAFT_UNVERIFIED."),
    ("RD05", "Safety Functions",
     "You DETECT and REPORT existing safety functions (E-stop, guards, light "
     "curtains, two-hand control) found in legacy PLC code into the RD05 "
     "schema. NEVER guess SIL/PLr — leave them blank unless explicit in the "
     "code. Every row stays DRAFT_UNVERIFIED; a certified safety engineer must "
     "sign off. Do NOT write safety logic."),
    ("RD06", "Motion / Drives",
     "You extract motion and drive axes (axis id, drive type, control mode, "
     "limits) from legacy PLC code into the RD06 schema. Mark every row "
     "DRAFT_UNVERIFIED."),
    ("RD07", "Timing",
     "You extract timing and performance data (cycle times, timers, watchdogs, "
     "sequence durations) from legacy PLC code into the RD07 schema. Mark every "
     "row DRAFT_UNVERIFIED."),
    ("RD08", "Alarms",
     "You extract alarms and faults (IEC 62682: alarm id, text, class, "
     "priority, cause) from legacy PLC code into the RD08 schema. Mark every "
     "row DRAFT_UNVERIFIED."),
    ("RD09", "Communication",
     "You extract communication interfaces (protocol, partner, address, "
     "payload) from legacy PLC code and hardware config into the RD09 schema. "
     "Mark every row DRAFT_UNVERIFIED."),
    ("RD10", "FB Specifications",
     "You extract function block specifications (FB name, IN/OUT/INOUT "
     "interface, purpose) from legacy PLC code into the RD10 schema. Mark every "
     "row DRAFT_UNVERIFIED."),
    ("RD11", "HMI",
     "You extract HMI screens and tags (screen id, element, linked tag, "
     "action) from legacy PLC code and HMI export into the RD11 schema. "
     "PLC_Tag MUST follow the interface contract "
     "DB_HMI.<Cmd|Set|Sts>.<member>: commands/buttons write to "
     "DB_HMI.Cmd.b<Name>, numeric setpoints to DB_HMI.Set.i<Name>, "
     "indicators read from DB_HMI.Sts.b<Name> — never a bare tag name. Mark "
     "every row DRAFT_UNVERIFIED."),
    ("RD12", "Use Cases",
     "You extract operator use cases / workflows (use-case id, actor, trigger, "
     "steps) from legacy PLC code and operation into the RD12 schema. Mark "
     "every row DRAFT_UNVERIFIED."),
    ("RD14", "Modernization",
     "You extract modernization findings (finding id, legacy issue, modern "
     "recommendation, effort/risk) from the legacy code and its RD13 "
     "annotation into the RD14 schema. Mark every row DRAFT_UNVERIFIED."),
]

BUILTIN_WORKFLOWS["Topic Extraction"] = [
    WorkflowStep(
        name=f"{_rd_id} {_title} Draft",
        provider=None,
        model=None,
        # 2026-07-03 A/B/C: RD09/RD10 truncated at 8k on enriched inputs.
        max_tokens=65536,
        system_prompt=_load_extractor_system_prompt(_rd_id, _fallback),
        prompt_template=_topic_extract_user_template(_rd_id, _title),
        output_suffix=f"_{_rd_id}_draft.md",
        metadata_target=_rd_id,
    )
    for _rd_id, _title, _fallback in _TOPIC_EXTRACT_SPECS
]


# ---------------------------------------------------------------------------
# GREENFIELD — DESIGN pipeline (unified engine, different "brain")
# ---------------------------------------------------------------------------
# Same machinery as retrofit (Vision + text steps + RD draft writer + 3-state
# review + gates), but the prompts DESIGN from the new machine's documents
# (P&ID, EPLAN/electrical schematic, mechanical GA, functional spec/URS,
# datasheets) instead of EXTRACTing from legacy code. The two prompt families
# are kept strictly separate — a greenfield run never loads a retrofit EXTRACT
# prompt and vice-versa. RD13 (legacy annotation) and RD14 (modernization) are
# retrofit-only → marked N/A for greenfield by the gate layer, not generated.
#
# Discipline shared with retrofit: the AI never invents physical reality. If a
# document is missing it leaves cells blank / writes ASSUMPTION and the row
# stays DRAFT_UNVERIFIED for engineer review; it never guesses SIL/PLr.

def _greenfield_topic_user_template(rd_id: str, title: str) -> str:
    """User prompt for a Gate-2 greenfield DESIGN step. Only ``{content}`` is a
    runtime placeholder (caller builds it from the functional spec + the
    approved Gate-1 design)."""
    return (
        f"Design the {rd_id} ({title}) for a NEW (greenfield) machine, using the "
        f"functional spec and the approved Gate-1 design (IO list, data "
        f"dictionary, flowchart) provided below. This is a first-pass DRAFT for "
        f"engineer review.\n\n"
        "{content}\n\n"
        "Apply best-practice design per the schema in your system instructions. "
        "Output ONLY the draft Markdown (the table plus any small sections the "
        "format defines). Set every row's Status to DRAFT_UNVERIFIED. Where the "
        "spec is silent, write ASSUMPTION or leave the cell blank — never invent "
        "a value, and never guess safety levels (SIL/PLr) or physical addresses."
    )


# (rd_id, title, DESIGN system prompt). Same RD set as retrofit topics EXCEPT
# RD14 (Modernization) which is retrofit-only.
_GREENFIELD_TOPIC_SPECS: list[tuple[str, str, str]] = [
    ("RD04", "Operating Modes",
     "You DESIGN OMAC PackML operating modes for a new machine from its "
     "functional spec into the RD04 schema (ModeID, ModeName, Priority, "
     "PackMLState, entry/exit conditions, HMI color/text). M00=Emergency, "
     "Priority unique. Mark every row DRAFT_UNVERIFIED."),
    ("RD05", "Safety Functions",
     "You DESIGN the safety functions a new machine needs from its risk "
     "assessment / spec into the RD05 schema (E-stop, guards, light curtains). "
     "NEVER assign SIL/PLr yourself — leave them blank for the certified safety "
     "engineer. Every row stays DRAFT_UNVERIFIED. Do NOT write safety logic."),
    ("RD06", "Motion / Drives",
     "You DESIGN motion/drive axes from the spec + drive list into the RD06 "
     "schema (axis id, drive type, control mode, limits). Mark every row "
     "DRAFT_UNVERIFIED."),
    ("RD07", "Timing",
     "You DESIGN timing/performance targets from the spec into the RD07 schema "
     "(cycle times, timers, watchdogs, sequence durations). Mark every row "
     "DRAFT_UNVERIFIED."),
    ("RD08", "Alarms",
     "You DESIGN the alarm list (IEC 62682) from the equipment + spec into the "
     "RD08 schema (alarm id, text, class, priority, cause). Mark every row "
     "DRAFT_UNVERIFIED."),
    ("RD09", "Communication",
     "You DESIGN the communication architecture from the network topology + "
     "spec into the RD09 schema (protocol, partner, address, payload). Mark "
     "every row DRAFT_UNVERIFIED."),
    ("RD10", "FB Specifications",
     "You DESIGN the function block specifications from the equipment + spec "
     "into the RD10 schema (FB name, IN/OUT/INOUT interface, purpose). Mark "
     "every row DRAFT_UNVERIFIED."),
    ("RD11", "HMI",
     "PLC_Tag MUST follow the interface contract "
     "DB_HMI.<Cmd|Set|Sts>.<member> (commands DB_HMI.Cmd.b<Name>, setpoints "
     "DB_HMI.Set.i<Name>, indicators DB_HMI.Sts.b<Name>) — never a bare tag. "
     "You DESIGN the HMI screens/tags from the spec + IO into the RD11 schema "
     "(screen id, element, linked tag, action). Mark every row DRAFT_UNVERIFIED."),
    ("RD12", "Use Cases",
     "You DESIGN operator use cases / workflows from the spec into the RD12 "
     "schema (use-case id, actor, trigger, steps). Mark every row "
     "DRAFT_UNVERIFIED."),
]

BUILTIN_WORKFLOWS["Greenfield Topic Design"] = [
    WorkflowStep(
        name=f"{_rd_id} {_title} Design",
        provider=None,
        model=None,
        max_tokens=65536,
        system_prompt=_sys,
        prompt_template=_greenfield_topic_user_template(_rd_id, _title),
        output_suffix=f"_{_rd_id}_draft.md",
        metadata_target=_rd_id,
    )
    for _rd_id, _title, _sys in _GREENFIELD_TOPIC_SPECS
]

# Gate-1 greenfield Discovery: Vision reads the design documents, text reads the
# functional spec, then RD01/RD02/RD03 are designed from those.
BUILTIN_WORKFLOWS["Greenfield Discovery"] = [
    WorkflowStep(
        name="Design Document Analysis",
        provider="google", model=None, use_multimodal=True, max_tokens=65536,
        system_prompt=(
            "You are an automation engineer reading the design documents of a "
            "NEW machine (P&ID, electrical schematic / EPLAN, mechanical GA, "
            "instrument list). Extract the equipment inventory and IO universe "
            "that the documents define. Be precise about signal types "
            "(DI/DQ/AI/AO) and safety-related signals. Never invent equipment "
            "that is not in the documents."
        ),
        prompt_template=(
            "Analyse the attached design documents of a new machine.\n\n"
            "Return a Markdown table: "
            "Tag | Description | IO_Type | Address_Hint | SafetyRelated | Source\n\n"
            "IO_Type one of DI, DQ, AI, AO, SAFE_DI, SAFE_DQ. SafetyRelated Y/N. "
            "Source = the document where you found it. Then add a "
            "## Equipment Inventory section (motors, valves, drives, sensors) and "
            "a ## Process Structure section (areas / units from the P&ID)."
        ),
        output_suffix="_design_docs_analysis.md",
    ),
    WorkflowStep(
        name="Functional Spec Analysis",
        provider=None, model=None, max_tokens=65536,
        system_prompt=(
            "You are a controls engineer reading a new machine's functional "
            "specification / URS. Extract the intended process sequence, "
            "operating modes and requirements. Mark anything not stated in the "
            "spec as ASSUMPTION — do not invent behaviour."
        ),
        prompt_template=(
            "Read this functional spec / requirements text:\n\n{content}\n\n"
            "Return:\n"
            "1. ## Process Sequence — ordered steps with entry/exit conditions\n"
            "2. ## Operating Modes — auto / manual / setup behaviour required\n"
            "3. ## Requirements — production rate, recipes, safety, standards\n"
            "4. ## Assumptions — everything inferred rather than stated"
        ),
        output_suffix="_spec_analysis.md",
    ),
    WorkflowStep(
        name="RD01 IO List Design",
        provider=None, model=None, max_tokens=65536,
        system_prompt=(
            "You are a senior automation engineer designing an IO list for a "
            "new machine to GLOBAL_NAMING_STANDARD, from the equipment inventory "
            "(document analysis) and the spec. Assign clean S7 tag names and "
            "plausible address blocks; mark unknowns rather than invent them."
        ),
        prompt_template=(
            "Design the RD01 IO List from these inputs.\n\n"
            "--- DESIGN DOCUMENT ANALYSIS (step 1) ---\n{out_1}\n\n"
            "--- FUNCTIONAL SPEC ANALYSIS (step 2) ---\n{out_2}\n\n"
            "Produce ONLY a Markdown table with EXACTLY these columns:\n\n"
            "| Tag | Address | Type | Dir | Equipment | Description | NormalState "
            "| EngUnit | RangeMin | RangeMax | Safety | SrcModule | OldTag | Notes "
            "| Status |\n"
            "Rules: Type DI/DQ/AI/AO; Dir IN/OUT; Safety YES/NO; OldTag blank "
            "(greenfield — no legacy); Status DRAFT_UNVERIFIED for every row; "
            "leave a cell blank if unknown — do NOT invent. After the table add "
            "## Assumptions and ## Review Required."
        ),
        output_suffix="_RD01_draft.md",
        metadata_target="RD01",
    ),
    WorkflowStep(
        name="RD02 Data Dictionary Design",
        provider=None, model=None, max_tokens=65536,
        system_prompt=(
            "You design the internal data dictionary (DBs, markers, timers, "
            "counters, UDT candidates) a new machine's program needs, from the "
            "spec and the IO list. Not physical IO — internal data."
        ),
        prompt_template=(
            "Design the RD02 Data Dictionary from the spec analysis and IO.\n\n"
            "--- SPEC ANALYSIS (step 2) ---\n{out_2}\n\n"
            "Produce a Markdown table: Name | DataType | Scope | Description | "
            "Status. Scope one of DB, MARKER, TIMER, COUNTER, TEMP, "
            "UDT_CANDIDATE. Status DRAFT_UNVERIFIED. Add a ## UDT Candidates "
            "section grouping related fields."
        ),
        output_suffix="_RD02_draft.md",
        metadata_target="RD02",
    ),
    WorkflowStep(
        name="RD03 Flowchart Design",
        provider=None, model=None, max_tokens=65536,
        system_prompt=(
            "You design the control sequence (flowchart) of a new machine from "
            "its functional spec. Be faithful to the spec; mark anything "
            "inferred as ASSUMPTION."
        ),
        prompt_template=(
            "Design the RD03 control sequence from the spec analysis.\n\n"
            "--- SPEC ANALYSIS (step 2) ---\n{out_2}\n\n"
            "Produce EXACTLY these sections:\n\n"
            "## Step Sequence\n"
            "A Markdown table with these EXACT columns (no Mermaid — the diagram "
            "is auto-generated from this table):\n"
            "| StepID | StepName | EntryCondition | Actions | ExitCondition | "
            "NextStep | Status |\n"
            "Rules: StepID = S001, S002 … ; NextStep = next StepID or (end); "
            "Status = DRAFT_UNVERIFIED; no pipes inside cell text.\n\n"
            "## Modes\nAutomatic / manual / setup behaviour from the spec.\n\n"
            "## Assumptions\nEverything inferred rather than stated."
        ),
        output_suffix="_RD03_draft.md",
        metadata_target="RD03",
    ),
]


class AutoFlowRunner:
    """
    Runs the selected workflow sequentially via the API.
    on_step_done is called when each step completes.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        project_root: Path,
        on_step_start: Callable[[int, str], None],
        on_step_chunk: Callable[[str], None],
        on_step_done: Callable[[int, str, Path], None],
        on_flow_done: Callable[[], None],
        on_error: Callable[[str], None],
        on_warn: Optional[Callable[[str], None]] = None,
        multimodal_files: Optional[list] = None,
        api_key_resolver: Optional[Callable[[str], Optional[str]]] = None,
        draft_writer: Optional[Callable[[WorkflowStep, str], None]] = None,
        system_prompt_suffix: str = "",
        consent_confirmed: bool = False,
        output_postprocess: Optional[Callable[[str], str]] = None,
        on_usage: Optional[Callable[[object], None]] = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.project_root = project_root
        self.on_step_start = on_step_start
        self.on_step_chunk = on_step_chunk
        self.on_step_done = on_step_done
        self.on_flow_done = on_flow_done
        self.on_error = on_error
        self.on_warn = on_warn  # R-C-2: optional warning channel (output audit warn)
        self.multimodal_files = multimodal_files or []  # files for use_multimodal steps
        # M0 fix: per-step provider key lookup. Without it, a workflow that
        # mixes providers (e.g. Retrofit Pre-Analysis: google + anthropic)
        # would send the global key to every provider and fail.
        self.api_key_resolver = api_key_resolver
        # M2: steps with metadata_target hand their output to this callback
        # (factory_web wires it to rd_draft_writer). REPORTS/ copy is always
        # written first as the audit trail.
        self.draft_writer = draft_writer
        # GLOBAL_LANG_POLICY §7: callers append e.g. an OUTPUT LANGUAGE
        # directive (from PROJECT_STATE.output_language) to EVERY step's
        # system prompt — workflow templates stay language-neutral.
        self.system_prompt_suffix = system_prompt_suffix
        # B-L3/B-G1/B-G2 fix: engineer consent forwarded from the GUI layer.
        # Fail-safe default False: unknown/missing consent → CONFIDENTIAL blocked.
        self.consent_confirmed: bool = bool(consent_confirmed)
        # S-6 (B-L2): applied to PERSISTED copies only (REPORTS/ + draft_writer)
        # — factory_web wires deanonymize_text here so RD drafts show real
        # customer names again. The inter-step chain (step_outputs_raw / {out_N})
        # deliberately stays anonymized: a later prompt must never carry the
        # restored values back to the cloud provider.
        self.output_postprocess = output_postprocess
        # B8 (E2E 2026-07-07): per-step UsageInfo callback — factory_web wires
        # the cost accumulator here (settings.total_cost_usd stayed 0.0
        # because nothing ever recorded spend).
        self.on_usage = on_usage
        self._stop = False

    def run_async(self, workflow_name: str, source_file: Path) -> None:
        """Starts the workflow in a separate thread."""
        t = threading.Thread(
            target=self._run,
            args=(workflow_name, source_file),
            daemon=True,
        )
        t.start()

    def stop(self) -> None:
        self._stop = True

    def _run(self, workflow_name: str, source_file: Path) -> None:
        if not AI_AVAILABLE:
            self.on_error("Could not load ai_client module.")
            return

        steps = BUILTIN_WORKFLOWS.get(workflow_name, [])
        if not steps:
            self.on_error(f"Workflow not found: {workflow_name}")
            return

        # ------------------------------------------------------------------
        # I-2 fix: Classification guard — fail-closed
        # Unknown/missing classification → assume CONFIDENTIAL → block.
        # ------------------------------------------------------------------
        if CLASSIFICATION_GUARD_AVAILABLE:
            _allowed, _reason = check_ai_send(
                self.project_root, self.provider,
                consent_confirmed=self.consent_confirmed,
            )
            if not _allowed:
                _block_msg = (
                    f"[IP_LEAKAGE] Data classification gate blocked — "
                    f"workflow cannot start: {_reason}. "
                    f"CONFIDENTIAL projects require engineer consent — "
                    f"use Retrofit Pre-Analysis or change the project classification."
                )
                self.on_error(_block_msg)
                if AUDIT_AVAILABLE:
                    try:
                        log_ai_action(
                            project_path=self.project_root,
                            step_label="[BLOCKED] classification guard",
                            ai_model=self.model,
                            ai_provider=self.provider,
                            prompt_text=f"workflow={workflow_name}; reason={_reason}",
                            prompt_id=f"autoflow:{workflow_name}:BLOCKED",
                        )
                    except Exception:
                        pass
                return
        else:
            # Guard module could not be loaded → fail-closed: block the operation
            self.on_error(
                "[IP_LEAKAGE] data_classification_guard module could not be loaded — "
                "fail-closed: workflow cannot start."
            )
            return

        # Build a client cache keyed by (provider, model) to reuse connections.
        _client_cache: dict[tuple[str, str], AIClient] = {}

        def _get_client(prov: str, mdl: str, key: str) -> Optional[AIClient]:
            cache_key = (prov, mdl)
            if cache_key not in _client_cache:
                try:
                    _client_cache[cache_key] = AIClient(provider=prov, api_key=key, model=mdl)
                except Exception as exc:
                    self.on_error(f"Could not create AI client ({prov}/{mdl}): {exc}")
                    return None
            return _client_cache[cache_key]

        # Default client (used for steps without per-step provider override)
        default_client = _get_client(self.provider, self.model, self.api_key)
        if default_client is None:
            return

        try:
            source_content = source_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.on_error(f"Could not read source file: {e}")
            return

        prev_output = ""
        # M0 fix: a flow that stopped on an error must not also report
        # success — on_flow_done now fires only after a clean run.
        failed = False
        # M0 fix: raw output of every completed step, keyed by 1-based index.
        # Lets later templates reference any earlier step via {out_1}, {out_2}…
        # — previously only {prev_output} existed, so e.g. the RD01 consolidation
        # step never saw the drawing analysis from step 1.
        step_outputs_raw: dict[int, str] = {}
        output_dir = self.project_root / "REPORTS"
        output_dir.mkdir(exist_ok=True)

        for i, step in enumerate(steps):
            if self._stop:
                break

            self.on_step_start(i, step.name)

            # Resolve per-step provider / model (falls back to global)
            step_provider = step.provider or self.provider
            step_model    = step.model    or self.model
            # M0 fix: resolve the key for the STEP's provider. The old code
            # passed self.api_key to every provider, so a mixed-provider
            # workflow sent e.g. the Gemini key to Anthropic and failed.
            if self.api_key_resolver is not None:
                step_key = self.api_key_resolver(step_provider) or ""
            elif step_provider == self.provider:
                step_key = self.api_key
            else:
                step_key = ""
            if not step_key:
                self.on_error(
                    f"[Step {i+1}] No API key for provider '{step_provider}' — "
                    f"step '{step.name}' requires it. "
                    f"Add the key in Settings → {step_provider} card."
                )
                failed = True
                break
            if step_provider == self.provider and step_model == self.model:
                step_client = default_client
            else:
                step_client = _get_client(step_provider, step_model, step_key)
                if step_client is None:
                    # M0 fix: do NOT silently fall back to the default client —
                    # that would send this step's data to a different provider.
                    failed = True
                    break

            # Per-step classification guard check
            if CLASSIFICATION_GUARD_AVAILABLE and step_provider != self.provider:
                _step_result = check_ai_send(
                    self.project_root, step_provider,
                    consent_confirmed=self.consent_confirmed,
                )
                if not _step_result.allowed:
                    self.on_error(
                        f"[IP_LEAKAGE] Step '{step.name}': classification guard blocked "
                        f"provider '{step_provider}' — {_step_result.reason}"
                    )
                    failed = True
                    break

            # I-2 fix: prev_output must not enter the format() call unsanitized
            prev_output_sanitized = _sanitize_chain_output(prev_output)

            # M0 fix: every earlier step is addressable as {out_N} (sanitized),
            # so consolidation steps can combine multiple sources.
            fmt_kwargs = {
                "content": source_content,
                "prev_output": prev_output_sanitized,
                "file_name": source_file.name,
            }
            for n, raw in step_outputs_raw.items():
                fmt_kwargs[f"out_{n}"] = _sanitize_chain_output(raw)

            try:
                prompt = step.prompt_template.format(**fmt_kwargs)
            except KeyError as ke:
                self.on_error(
                    f"[Step {i+1}] Prompt template references unknown placeholder "
                    f"{{{ke.args[0]}}} — earlier steps available: "
                    f"{', '.join(sorted(k for k in fmt_kwargs if k.startswith('out_')))or 'none'}"
                )
                failed = True
                break

            chunks: list[str] = []

            def _collect(text: str) -> None:
                chunks.append(text)
                self.on_step_chunk(text)

            # C-1 fix: fail-closed audit log — block AI call if log is unwritable
            if AUDIT_AVAILABLE:
                try:
                    log_ai_action(
                        project_path=self.project_root,
                        step_label=step.name,
                        ai_model=step_model,
                        ai_provider=step_provider,
                        prompt_text=prompt,
                        prompt_id=f"autoflow:{workflow_name}:{step.name}",
                    )
                except AuditLogError as _log_exc:
                    self.on_error(
                        f"[EU AI Act] Audit log write failed — AI call blocked: {_log_exc}"
                    )
                    failed = True
                    break

            usage = None  # K-2 fix: keep usage defined on every path (prevents NameError)
            if step.use_multimodal and hasattr(step_client, "chat_with_files"):
                mm_files = self.multimodal_files  # drawings/photos only — never fall back to text
                if not mm_files:
                    # No visual files: skip this step gracefully and continue chain.
                    step_outputs_raw[i + 1] = "(no drawings or photos — visual analysis skipped)"
                    prev_output = step_outputs_raw[i + 1]
                    self.on_step_done(i, prev_output, source_file)
                    continue
            # Transient-error retry: providers time out / drop connections
            # mid-run (field measurement 2026-07-03: two 10-step chains died
            # at steps 8 and 10 on one read-timeout each). Retrying the ONE
            # step is cheap; losing the whole chain costs the full run.
            _api_err: Optional[Exception] = None
            for _attempt in range(1, _API_MAX_ATTEMPTS + 1):
                try:
                    if step.use_multimodal and hasattr(step_client, "chat_with_files"):
                        response, usage = step_client.chat_with_files(
                            system=step.system_prompt + self.system_prompt_suffix,
                            user=prompt,
                            files=self.multimodal_files,
                            max_tokens=step.max_tokens,
                        )
                    else:
                        response, usage = step_client.chat(
                            system=step.system_prompt + self.system_prompt_suffix,
                            user=prompt,
                            max_tokens=step.max_tokens,
                            on_chunk=_collect,
                        )
                    _api_err = None
                    break
                except Exception as e:
                    _api_err = e
                    if (_attempt < _API_MAX_ATTEMPTS
                            and _TRANSIENT_API_RE.search(str(e))):
                        _wait = 5 * (3 ** (_attempt - 1))
                        _msg = (f"[Step {i+1}] transient API error "
                                f"(attempt {_attempt}/{_API_MAX_ATTEMPTS}): "
                                f"{str(e)[:160]} — retrying in {_wait}s")
                        logging.warning(_msg)
                        if self.on_warn is not None:
                            self.on_warn(_msg)
                        chunks.clear()  # discard the partial stream
                        time.sleep(_wait)
                        continue
                    break
            if _api_err is not None:
                self.on_error(f"[Step {i+1}] API error: {_api_err}")
                failed = True
                break

            # B8: report real spend to the caller (settings.total_cost_usd)
            if usage is not None and self.on_usage is not None:
                try:
                    self.on_usage(usage)
                except Exception:
                    pass

            # C-1 fix: update output hash after response received
            if AUDIT_AVAILABLE and (response or chunks):
                _resp_text = response or "".join(chunks)
                try:
                    log_ai_action(
                        project_path=self.project_root,
                        step_label=f"{step.name} [output]",
                        ai_model=step_model,
                        ai_provider=step_provider,
                        output_text=_resp_text,
                        prompt_id=f"autoflow:{workflow_name}:{step.name}:output",
                    )
                except AuditLogError as _out_log_exc:
                    # R-C-2 fix: fail-warn — an output hash log failure is made visible.
                    # Input logging stays fail-closed; an output log failure does not stop
                    # the process, but it does not pass silently either: the EU AI Act audit
                    # chain reports the "input logged, output not" state to the operator and caller.
                    _warn_msg = (
                        f"[EU AI Act] Output audit hash could not be written for step "
                        f"'{step.name}' — {_out_log_exc}"
                    )
                    logging.warning(_warn_msg)
                    if self.on_warn is not None:
                        self.on_warn(_warn_msg)

            # K-2 + S-5 fix: truncation warning for EVERY step output — the old
            # suffix filter silently dropped truncation on .md drafts (RD02/RD03),
            # so large legacy archives produced half a data dictionary with no hint.
            if getattr(usage, "truncated", False):
                _is_code = Path(step.output_suffix).suffix in _CODE_OUTPUT_SUFFIXES
                _tag = "SCL_TRUNCATION" if _is_code else "OUTPUT_TRUNCATION"
                _what = "generated SCL" if _is_code else "step output"
                # Report the ACTUAL cut point, not just the step budget — the
                # provider's own ceiling can be far below max_tokens and the
                # old message sent people raising the wrong number
                # (field measurement 2026-07-03).
                try:
                    _actual = int(getattr(usage, "output_tokens", 0) or 0)
                except Exception:
                    _actual = 0
                _prov = str(getattr(usage, "provider", "") or step.provider
                            or "?")
                _trunc_msg = (
                    f"[{_tag}] Step '{step.name}' was cut off after "
                    f"{_actual or '?'} output tokens "
                    f"(provider={_prov}, step budget max_tokens="
                    f"{step.max_tokens}) — the {_what} may be incomplete. "
                    + ("The provider's own output ceiling ended the response; "
                       "switch this step to a larger-output provider."
                       if _actual and _actual < step.max_tokens * 0.9
                       else "Increase WorkflowStep.max_tokens.")
                )
                logging.warning(_trunc_msg)
                if self.on_warn is not None:
                    self.on_warn(_trunc_msg)

            raw_output = response or "".join(chunks)

            # K-1 fix: strip the LLM markdown fence from code outputs
            # .md outputs are left untouched; .scl/.st/.awl are stripped
            out_suffix = Path(step.output_suffix).suffix
            if out_suffix in _CODE_OUTPUT_SUFFIXES:
                prev_output = _strip_code_fence(raw_output)
            else:
                prev_output = raw_output
            step_outputs_raw[i + 1] = prev_output

            # Report hygiene (E2E finding 2026-07-07): ONE living copy per
            # artifact. Step copies live under REPORTS/_ai_steps/ with STABLE
            # names — a new run REPLACES the previous draft instead of piling
            # up timestamped siblings (15 duplicates per run drowned the real
            # reports). Old-style timestamped leftovers of the SAME artifact
            # are removed the first time it is regenerated.
            out_name, out_path = _step_output_path(
                output_dir, source_file.stem, step.output_suffix)

            # prev_output is already fence-stripped above for code suffixes
            # (.scl/.st/.awl) via _strip_code_fence, so a .scl file holds only
            # code and imports cleanly into TIA Portal. .md outputs stay raw.
            # S-6: persisted copies may be postprocessed (deanonymized); the
            # chain variable prev_output stays untouched (see __init__ note).
            _persisted = prev_output
            if self.output_postprocess is not None:
                try:
                    _persisted = self.output_postprocess(prev_output)
                except Exception as _pp_exc:
                    logging.warning("output_postprocess failed: %s", _pp_exc)
                    _persisted = prev_output
            # Audit copy (REPORTS/_ai_steps). A failed write may not stay
            # silent — this file IS the audit trail of the step (same
            # discipline as the draft_writer block below).
            try:
                out_path.write_text(_persisted, encoding="utf-8")
            except Exception as _wr_exc:
                _wr_msg = (f"Step audit copy NOT written "
                           f"(REPORTS/_ai_steps/{out_name}): {_wr_exc}")
                logging.warning(_wr_msg)
                if self.on_warn is not None:
                    self.on_warn(_wr_msg)

            # M2: place the draft into metadata/ via the caller's writer.
            # Failure must not kill the flow — REPORTS/ already has the copy.
            if step.metadata_target and self.draft_writer is not None:
                try:
                    self.draft_writer(step, _persisted)
                except Exception as _dw_exc:
                    _dw_msg = (
                        f"Draft writer failed for {step.metadata_target} "
                        f"('{step.name}'): {_dw_exc} — output remains in "
                        f"REPORTS/_ai_steps/{out_name}"
                    )
                    logging.warning(_dw_msg)
                    if self.on_warn is not None:
                        self.on_warn(_dw_msg)

            self.on_step_done(i, step.name, out_path)

        if not self._stop and not failed:
            self.on_flow_done()
