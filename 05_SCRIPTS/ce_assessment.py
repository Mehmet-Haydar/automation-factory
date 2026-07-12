#!/usr/bin/env python3
"""
ce_assessment.py — CE "essential modification" (wesentliche Veränderung)
assessment document for retrofit projects.

Produces an i18n (DE default / EN / TR) assessment template:
- machine identification (PROJECT_STATE + fill-in fields),
- the BMAS-style assessment questions (performance/function change, new
  hazard, sufficiency of existing protective measures, simple restoration),
- result field (essential modification YES/NO — the ENGINEER ticks it),
- overall rationale + signature block.

The mandatory disclaimer states that the template does not replace a legal
assessment — decision and signature belong to the responsible engineer.
The tool NEVER pre-answers a question or pre-ticks the result.

Greenfield projects: the document is still produced (non-blocking), with a
visible "not a retrofit" note (user decision: warn, don't block).

Output: MD always; PDF optional via pdf_common (PDF failure → MD + loud
warning, same fail-safe as the protocol generators).

CLI:
  python ce_assessment.py --project PROJECT_PATH [--lang de|en|tr] [--pdf]
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from protocol_i18n import (  # noqa: E402
    DEFAULT_LANG, SUPPORTED_LANGS, force_utf8_stdout, normalize_lang, t,
)


@dataclass
class CeAssessmentResult:
    md_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    lang: str = DEFAULT_LANG
    is_retrofit: bool = True
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.md_path is not None


def _read_state(project_path: Path) -> dict:
    f = project_path / "PROJECT_STATE.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_QUESTIONS = ("ce.q1", "ce.q2", "ce.q3", "ce.q4")


def generate_ce_assessment(
    project_path: Path,
    lang: str = DEFAULT_LANG,
    pdf: bool = False,
) -> CeAssessmentResult:
    """Write `_output/CE_ASSESSMENT_<ts>.md` (+ optional PDF)."""
    lang = normalize_lang(lang)
    result = CeAssessmentResult(lang=lang)

    if not project_path.exists():
        # Log hygiene: do NOT embed the real path — it propagates to the GUI
        # log via factory_web's str(e). The name alone is enough to act on.
        raise FileNotFoundError("Project folder not found")

    state = _read_state(project_path)
    ptype = (state.get("project_type") or "").strip().lower()
    result.is_retrofit = ptype == "retrofit"

    ts_label = datetime.now().strftime("%Y-%m-%d %H:%M")
    ts_file = datetime.now().strftime("%Y%m%d_%H%M")
    proj_name = state.get("project_name", project_path.name)
    customer = state.get("customer", "")
    p_from = state.get("source_platform", state.get("platform_from", ""))
    p_to = state.get("target_platform", "")
    platform_line = f"{p_from or '______'} → {p_to or '______'}"

    lines: list[str] = [
        f"# {t('ce.title', lang)}",
        "",
        f"**{t('common.project', lang)}:** {proj_name}",
        f"**{t('common.date', lang)}:** {ts_label}",
        "",
    ]
    # Faz 4.2 — mandatory disclaimer in ALL THREE languages (DE/EN/TR), the
    # selected language first. A legal disclaimer carried only in one language
    # is not a disclaimer for the other recipients.
    _disc_langs = [lang] + [l for l in SUPPORTED_LANGS if l != lang]
    for dl in _disc_langs:
        lines.append(f"> ⚖ **{t('ce.disclaimer', dl)}**")
    lines.append("")

    if not result.is_retrofit:
        warn = t("ce.not_retrofit_warning", lang, ptype=ptype or "—")
        lines += [f"> ⚠ {warn}", ""]
        result.warnings.append(warn)

    lines += [
        f"## 1. {t('ce.machine_identity', lang)}",
        "",
        "| | |",
        "|---|---|",
        f"| {t('ce.field_machine', lang)} | {proj_name} |",
        f"| {t('common.customer_rep', lang)} | {customer or '______'} |",
        f"| {t('ce.field_manufacturer', lang)} | ______ |",
        f"| {t('ce.field_serial', lang)} | ______ |",
        f"| {t('ce.field_year', lang)} | ______ |",
        f"| {t('ce.field_platform', lang)} | {platform_line} |",
        "",
        f"## 2. {t('ce.modification_desc', lang)}",
        "",
        f"> {t('ce.modification_hint', lang)}",
        "",
        "_______________________________________________",
        "",
        "_______________________________________________",
        "",
        f"## 3. {t('ce.questions_title', lang)}",
        "",
        f"| {t('col.no', lang)} | {t('ce.col_question', lang)} "
        f"| {t('ce.col_answer', lang)} | {t('ce.col_notes', lang)} |",
        "|---|---|---|---|",
    ]
    for idx, qkey in enumerate(_QUESTIONS, start=1):
        # answer column is deliberately a blank checkbox pair — the tool
        # never pre-answers
        lines.append(
            f"| {idx} | **{t(qkey, lang)}**<br>_{t(qkey + '.hint', lang)}_ "
            f"| ☐ / ☐ | ______ |"
        )

    lines += [
        "",
        f"## 4. {t('ce.result_title', lang)}",
        "",
        f"**{t('ce.result_essential', lang)}**",
        "",
        f"- {t('ce.result_consequence_yes', lang)}",
        f"- {t('ce.result_consequence_no', lang)}",
        "",
        f"### {t('ce.rationale', lang)}",
        "",
        "_______________________________________________",
        "",
        "_______________________________________________",
        "",
        f"## 5. {t('common.signatures', lang)}",
        "",
        "| | |",
        "|---|---|",
        f"| {t('ce.signature_engineer', lang)} | ________________________ |",
        f"| {t('common.date', lang)} | ________________________ |",
        f"| {t('col.signature', lang)} | ________________________ |",
        "",
        "---",
        f"*AUTOMATION FACTORY — ce_assessment.py | {ts_label}*",
        "",
    ]

    body = "\n".join(lines)
    out_dir = project_path / "_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"CE_ASSESSMENT_{ts_file}.md"
    dest.write_text(body, encoding="utf-8")
    result.md_path = dest

    if pdf:
        try:
            from pdf_common import markdown_to_pdf
            result.pdf_path = markdown_to_pdf(
                body, dest.with_suffix(".pdf"),
                f"{t('ce.title', lang)} — {proj_name}",
            )
        except Exception as exc:
            result.warnings.append(f"{t('status.pdf_failed', lang)} ({exc})")

    return result


def format_ce_summary(result: CeAssessmentResult) -> str:
    lines = ["CE Assessment Summary", ""]
    if result.md_path:
        lines.append(f"  File    : {result.md_path.name}")
    if result.pdf_path:
        lines.append(f"  PDF     : {result.pdf_path.name}")
    lines.append(f"  Language: {result.lang}")
    lines.append(f"  Retrofit: {result.is_retrofit}")
    for w in result.warnings:
        lines.append(f"  ! {w}")
    return "\n".join(lines)


def main():
    force_utf8_stdout()
    import argparse
    p = argparse.ArgumentParser(
        description="CE essential-modification assessment generator")
    p.add_argument("--project", metavar="PROJECT_PATH", required=True)
    p.add_argument("--lang", choices=["de", "en", "tr"], default=DEFAULT_LANG)
    p.add_argument("--pdf", action="store_true")
    args = p.parse_args()
    result = generate_ce_assessment(Path(args.project), lang=args.lang,
                                    pdf=args.pdf)
    print(format_ce_summary(result))


if __name__ == "__main__":
    main()
