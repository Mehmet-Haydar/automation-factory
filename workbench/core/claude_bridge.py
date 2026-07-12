"""
claude_bridge.py — Prompt template builder.

Builds ready-to-use prompt strings from gate-aware templates for use with
direct AI API calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .factory_reader import get_standards_ref


def build_command(
    action: str,
    selected_file: Optional[Path],
    project_root: Optional[Path],
    extra_context: str = "",
) -> str:
    """
    Generates a ready-to-use prompt string based on the action and selected file.
    """
    standards = get_standards_ref()
    file_ref = ""
    if selected_file and project_root:
        try:
            rel = selected_file.relative_to(project_root)
            file_ref = f"@{rel.as_posix()}"
        except ValueError:
            file_ref = f"@{selected_file.name}"

    templates = {
        "analyze": (
            f"Analyze this file and check its compliance with Factory standards:\n"
            f"{file_ref}\n\n"
            f"Standards: {standards}\n\n"
            f"Present the results in Markdown table format."
        ),
        "extract_io": (
            f"Extract all IO points from this file:\n"
            f"{file_ref}\n\n"
            f"For each IO: Tag name, Type (Bool/Int/Real), Address, Description.\n"
            f"Factory standards: {standards}"
        ),
        "generate_scl": (
            f"Generate TIA Portal V18 SCL code from this IO list:\n"
            f"{file_ref}\n\n"
            f"Factory code standards: {standards}\n\n"
            f"Use FUNCTION_BLOCK structure, must be IEC 61131-3 compliant."
        ),
        "validate": (
            f"Validate this file against Factory standards:\n"
            f"{file_ref}\n\n"
            f"Standards: {standards}\n\n"
            f"List missing or incorrect fields and provide suggestions."
        ),
        "validate_io": (
            f"Validate the IO list in this file:\n"
            f"{file_ref}\n\n"
            f"Check: every IO tag has a name, type, address, description and direction; "
            f"addresses are unique; types match the factory naming standard.\n"
            f"Standards: {standards}\n\n"
            f"Return a Markdown table of failures plus a one-line verdict."
        ),
        "validate_rd": (
            f"Validate this RD (requirements detail) document against the Factory "
            f"schema for its RD number:\n"
            f"{file_ref}\n\n"
            f"Standards: {standards}\n\n"
            f"Return: required fields present (Y/N table), missing entries, "
            f"and a #UNKNOWNS section for anything that needs human input."
        ),
        "send_to_tia": (
            f"Prepare the following SCL code for TIA Portal V18 import via "
            f"Openness:\n{file_ref}\n\n"
            f"Steps to perform:\n"
            f"  1. Confirm syntax compiles with TIA V18 SCL (IEC 61131-3).\n"
            f"  2. Wrap into an XML <SW.Blocks.FB ...> envelope so the file is "
            f"importable through Openness.\n"
            f"  3. Report any unresolved tag/UDT references.\n\n"
            f"Standards: {standards}"
        ),
        "gen_unit_test": (
            f"Generate a unit-test plan for this function block:\n"
            f"{file_ref}\n\n"
            f"Use the Factory test template at 04_AI_PROMPTS/test_gen and produce:\n"
            f"  - Test cases (input → expected output) in a Markdown table.\n"
            f"  - A short SCL test harness that exercises each case.\n"
            f"  - The #UNKNOWNS section for inputs that need the customer's confirmation.\n"
            f"Standards: {standards}"
        ),
        "gen_fat": (
            f"Generate a customer-facing FAT (Factory Acceptance Test) protocol "
            f"based on this RD12 document:\n{file_ref}\n\n"
            f"Output the standard Factory FAT layout: scope, sign-off table, "
            f"step-by-step test cases, pass/fail columns, comments column.\n"
            f"Standards: {standards}"
        ),
        "parse_source": (
            f"Parse this customer source file and produce a structured digest:\n"
            f"{file_ref}\n\n"
            f"Detect: target platform (S7-1500, S7-300, AB, CodeSys, …), program "
            f"organisation units (FB, FC, OB, DB), IO tags, used data types.\n"
            f"Return a Markdown summary plus a JSON block usable by downstream "
            f"extractors. Standards: {standards}"
        ),
        "open_in_excel": (
            f"Open this spreadsheet in your local Excel and confirm the IO sheet, "
            f"the Tag sheet and the Address sheet are present:\n{file_ref}\n\n"
            f"(No AI work needed — this is a manual step. The clipboard contains "
            f"the file reference for convenience.)"
        ),
        "generate_report": (
            f"Generate a comprehensive report for this project:\n"
            f"{file_ref}\n\n"
            f"Follow the template: {standards}"
        ),
        "fat_protocol": (
            f"Generate a FAT protocol for this project:\n"
            f"{file_ref if file_ref else ''}\n\n"
            f"Use the Factory FAT template: {standards}"
        ),
        "custom": extra_context,
    }

    cmd = templates.get(action, extra_context or "")
    return cmd.strip()
