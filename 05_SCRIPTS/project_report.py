#!/usr/bin/env python3
"""
project_report.py — Project Status Report Generator (Phase 25-C)

Reads all project metadata, BOM, IO addressing and generated code files
and produces a comprehensive Markdown report for the customer / team.

Output: _output/PROJECT_REPORT_<YYYYMMDD_HHMMSS>.md

CLI:
  python project_report.py PROJECT_PATH [--lang EN|DE|TR]
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


FACTORY_ROOT = Path(__file__).resolve().parent.parent

# -- Translation table (multi-language by design: output_language support) -----

LABELS: dict[str, dict[str, str]] = {
    "title":          {"TR": "Proje Durum Raporu", "DE": "Projektstatus-Bericht", "EN": "Project Status Report"},
    "generated":      {"TR": "Otomatik üretildi",  "DE": "Automatisch erstellt",  "EN": "Auto-generated"},
    "project":        {"TR": "Proje",               "DE": "Projekt",               "EN": "Project"},
    "platform":       {"TR": "Hedef Platform",      "DE": "Zielplattform",         "EN": "Target Platform"},
    "cpu":            {"TR": "CPU",                 "DE": "CPU",                   "EN": "CPU"},
    "tia":            {"TR": "TIA Versiyon",        "DE": "TIA-Version",           "EN": "TIA Version"},
    "overview":       {"TR": "## 1. Genel Bakış",                 "DE": "## 1. Überblick",              "EN": "## 1. Overview"},
    "progress":       {"TR": "## 2. Veri Paketleri (RD) İlerlemesi", "DE": "## 2. Datenpakete (RD) Fortschritt", "EN": "## 2. Data Packages (RD) Progress"},
    "hardware":       {"TR": "## 3. Donanım (BOM)",              "DE": "## 3. Hardware (Stückliste)",   "EN": "## 3. Hardware (BOM)"},
    "io_summary":     {"TR": "## 4. IO Özeti",                   "DE": "## 4. IO-Übersicht",            "EN": "## 4. IO Summary"},
    "code_status":    {"TR": "## 5. Kod Üretimi Durumu",         "DE": "## 5. Codegenerierung Status",  "EN": "## 5. Code Generation Status"},
    "next_steps":     {"TR": "## 6. Sonraki Adımlar",            "DE": "## 6. Nächste Schritte",        "EN": "## 6. Next Steps"},
    "done":           {"TR": "✅ Tamamlandı",  "DE": "✅ Fertig",     "EN": "✅ Done"},
    "missing":        {"TR": "❌ Eksik",        "DE": "❌ Fehlt",      "EN": "❌ Missing"},
    "partial":        {"TR": "⚠️ Kısmi",       "DE": "⚠️ Teilweise",  "EN": "⚠️ Partial"},
    "draft":          {"TR": "📝 Taslak",       "DE": "📝 Entwurf",    "EN": "📝 Draft"},
}

RD_TITLES = {
    "RD01": {"TR": "IO Listesi",         "DE": "IO-Liste",           "EN": "IO List"},
    "RD02": {"TR": "Veri Sözlüğü",       "DE": "Datenwörterbuch",    "EN": "Data Dictionary"},
    "RD03": {"TR": "Akış Diyagramı",     "DE": "Ablaufdiagramm",     "EN": "Flowchart"},
    "RD04": {"TR": "Çalışma Modları",    "DE": "Betriebsmodi",       "EN": "Operating Modes"},
    "RD05": {"TR": "Güvenlik ⚠️",        "DE": "Sicherheit ⚠️",      "EN": "Safety ⚠️"},
    "RD06": {"TR": "Hareket",            "DE": "Bewegung",           "EN": "Motion"},
    "RD07": {"TR": "Zamanlama",          "DE": "Zeitsteuerung",      "EN": "Timing"},
    "RD08": {"TR": "Haberleşme",         "DE": "Kommunikation",      "EN": "Communications"},
    "RD09": {"TR": "Alarm",              "DE": "Alarm",              "EN": "Alarm"},
    "RD10": {"TR": "HMI",               "DE": "HMI",                "EN": "HMI"},
    "RD11": {"TR": "Kullanım Senaryosu", "DE": "Anwendungsfall",     "EN": "Use Case"},
    "RD12": {"TR": "FB Spesifikasyonu",  "DE": "FB-Spezifikation",   "EN": "FB Specification"},
    "RD13": {"TR": "Modernizasyon",      "DE": "Modernisierung",     "EN": "Modernization"},
    "RD14": {"TR": "Notlar + Açıklama",  "DE": "Anmerkungen",        "EN": "Annotations"},
}


def _t(key: str, lang: str) -> str:
    entry = LABELS.get(key, {})
    return entry.get(lang, entry.get("EN", key))


def _rd_title(rd: str, lang: str) -> str:
    entry = RD_TITLES.get(rd, {})
    return entry.get(lang, entry.get("EN", rd))


# -- Data collection ----------------------------------------------------------

def _read_state(project_path: Path) -> dict:
    state_file = project_path / "PROJECT_STATE.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _rd_status(project_path: Path, rd: str) -> str:
    """Return the RD file's presence + content status: done/draft/missing."""
    md_path = project_path / "metadata" / f"{rd}.md"
    if not md_path.exists():
        return "missing"
    try:
        content = md_path.read_text(encoding="utf-8")
        if "DRAFT" in content.upper() or "TASLAK" in content.upper():
            return "draft"
        if len(content.strip()) < 100:
            return "draft"
        return "done"
    except Exception:
        return "draft"


def _io_counts_from_hw02(project_path: Path) -> Optional[dict]:
    hw02 = project_path / "metadata" / "HW02_IO_Adresleme.md"
    if not hw02.exists():
        return None
    content = hw02.read_text(encoding="utf-8", errors="replace")
    counts: dict[str, int] = {}
    for io_type in ("DI", "DQ", "AI", "AO"):
        # Count table rows (starting with |, not the header)
        pattern = re.compile(r"^\s*\|[^|]+\|[^|]*" + io_type + r"[^|]*\|", re.MULTILINE | re.IGNORECASE)
        matches = pattern.findall(content)
        counts[io_type] = len(matches)
    if sum(counts.values()) == 0:
        return None
    return counts


def _io_counts_from_rd01(project_path: Path) -> Optional[dict]:
    rd01 = project_path / "metadata" / "RD01_IO_List.md"
    if not rd01.exists():
        # Fallback: any RD01*.md file
        candidates = list((project_path / "metadata").glob("RD01*.md"))
        if not candidates:
            return None
        rd01 = candidates[0]
    try:
        from hardware_sizer import count_from_rd01, IOCount
        count = count_from_rd01(rd01)
        if count.total == 0:
            return None
        return {"DI": count.di, "DQ": count.dq, "AI": count.ai, "AO": count.ao,
                "SAFE_DI": count.safe_di, "SAFE_DQ": count.safe_dq}
    except ImportError:
        return None


def _scl_files(project_path: Path) -> list[Path]:
    """.scl files under _output/ and _output/scl/."""
    files = []
    for d in [project_path / "_output", project_path / "_output" / "scl"]:
        if d.exists():
            files.extend(sorted(d.glob("*.scl")))
    return files


def _bom_devices(state: dict) -> list[dict]:
    return state.get("selected_devices", [])


def _pipeline_progress(state: dict) -> dict:
    """Completed step IDs."""
    return state.get("pipeline_progress", {})


# -- Report generator ---------------------------------------------------------

def generate_report(project_path: Path, lang: str = "EN") -> str:
    state     = _read_state(project_path)
    ts        = datetime.now().strftime("%Y-%m-%d %H:%M")
    proj_name = project_path.name

    platform   = state.get("target_platform") or state.get("platform", "—")
    cpu        = state.get("target_cpu", "—")
    tia_ver    = state.get("target_tia_version", "—")
    firm_ver   = state.get("target_firmware", "—")

    lines: list[str] = []

    # -- Header ---------------------------------------------------------------
    lines.append(f"# {_t('title', lang)}: {proj_name}")
    lines.append("")
    lines.append("```yaml")
    lines.append(f"project   : {proj_name}")
    lines.append(f"platform  : {platform}")
    lines.append(f"cpu       : {cpu}")
    lines.append(f"tia_version: {tia_ver}")
    lines.append(f"firmware  : {firm_ver}")
    lines.append(f"date      : {ts}")
    lines.append(f"lang      : {lang}")
    lines.append(f"generator : AUTOMATION_FACTORY project_report.py")
    lines.append("```")
    lines.append("")

    # -- 1. Overview ----------------------------------------------------------
    lines.append(_t("overview", lang))
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| {_t('project', lang)} | `{proj_name}` |")
    lines.append(f"| {_t('platform', lang)} | {platform} |")
    lines.append(f"| {_t('cpu', lang)} | {cpu} |")
    lines.append(f"| {_t('tia', lang)} | {tia_ver} |")

    # Project date
    created = state.get("created", "")
    if created:
        lines.append(f"| Created date | {created[:10]} |")

    # IO count
    io = _io_counts_from_hw02(project_path) or _io_counts_from_rd01(project_path)
    if io:
        io_str = "  ".join(f"{k}: {v}" for k, v in io.items() if v > 0)
        lines.append(f"| IO Total | {io_str} |")

    # Device count
    devices = _bom_devices(state)
    if devices:
        lines.append(f"| Selected Devices | {len(devices)} items |")

    lines.append("")

    # -- 2. RD Progress -------------------------------------------------------
    lines.append(_t("progress", lang))
    lines.append("")
    lines.append(f"| RD | Title | Status |")
    lines.append("|-----|-------|--------|")

    done_count = 0
    for rd in [f"RD{str(i).zfill(2)}" for i in range(1, 15)]:
        status = _rd_status(project_path, rd)
        rd_name = _rd_title(rd, lang)
        if status == "done":
            badge = _t("done", lang)
            done_count += 1
        elif status == "draft":
            badge = _t("draft", lang)
        else:
            badge = _t("missing", lang)
        lines.append(f"| `{rd}` | {rd_name} | {badge} |")

    lines.append("")
    pct = int(done_count / 14 * 100)
    lines.append(f"**Progress: {done_count}/14 RDs completed ({pct}%)**")
    lines.append("")

    # -- 3. Hardware BOM ------------------------------------------------------
    lines.append(_t("hardware", lang))
    lines.append("")

    if devices:
        lines.append(f"| # | Device ID | Quantity | Notes |")
        lines.append("|---|-----------|----------|-------|")
        for i, dev in enumerate(devices, 1):
            did = dev.get("device_id", "?")
            qty = dev.get("quantity", 1)
            notes = dev.get("notes", "")
            lines.append(f"| {i} | `{did}` | {qty} | {notes} |")
        lines.append("")
    else:
        lines.append("_No devices selected — add them in the New Project form or via the Hardware Library._")
        lines.append("")

    # If a proposed BOM exists
    proposed = project_path / "_output" / "HW_proposed_BOM.md"
    if proposed.exists():
        lines.append(f"Proposed hardware sizing available: `_output/HW_proposed_BOM.md`")
        lines.append("")

    # -- 4. IO Summary --------------------------------------------------------
    lines.append(_t("io_summary", lang))
    lines.append("")

    hw02_md = project_path / "metadata" / "HW02_IO_Adresleme.md"
    if hw02_md.exists():
        lines.append(f"IO physical addressing available: `metadata/HW02_IO_Adresleme.md`")
        if io:
            lines.append("")
            lines.append(f"| IO Type | Channel Count |")
            lines.append("|---------|---------------|")
            for k, v in io.items():
                if v > 0:
                    lines.append(f"| {k} | {v} |")
        lines.append("")
    elif io:
        lines.append(f"IO count (from RD01):")
        lines.append("")
        lines.append(f"| IO Type | Channels |")
        lines.append("|---------|----------|")
        for k, v in io.items():
            if v > 0:
                lines.append(f"| {k} | {v} |")
        lines.append("")
        lines.append("_Fill in hardware_config.xlsx for physical address mapping (Excel Tools -> IO Mapping)._")
        lines.append("")
    else:
        lines.append("_IO list not found — RD01 or hardware_config.xlsx is required._")
        lines.append("")

    # -- 5. Code Generation Status --------------------------------------------
    lines.append(_t("code_status", lang))
    lines.append("")

    scl_files = _scl_files(project_path)
    md_outputs = sorted((project_path / "_output").glob("*.md")) if (project_path / "_output").exists() else []

    if scl_files:
        lines.append(f"Extracted SCL files (`_output/scl/`):")
        lines.append("")
        for sf in scl_files:
            size_kb = sf.stat().st_size / 1024
            lines.append(f"- `{sf.name}` ({size_kb:.1f} KB)")
        lines.append("")
    elif md_outputs:
        lines.append(f"AI output .md files (`_output/`) — SCL not yet extracted:")
        lines.append("")
        for mf in md_outputs:
            if mf.name.startswith("PROJECT_REPORT"):
                continue
            size_kb = mf.stat().st_size / 1024
            lines.append(f"- `{mf.name}` ({size_kb:.1f} KB)")
        lines.append("")
        lines.append("_To extract SCL: Excel Tools -> MD -> SCL Extractor_")
        lines.append("")
    else:
        lines.append("_No code generation done yet._")
        lines.append("")

    # -- 6. Next Steps --------------------------------------------------------
    lines.append(_t("next_steps", lang))
    lines.append("")

    next_steps = []

    # Missing RDs
    missing_rds = [rd for rd in [f"RD{str(i).zfill(2)}" for i in range(1, 15)]
                   if _rd_status(project_path, rd) == "missing"]
    if missing_rds:
        next_steps.append(f"Complete the missing RDs: {', '.join(missing_rds)}")

    # IO mapping
    if not hw02_md.exists():
        next_steps.append("Fill in hardware_config.xlsx -> generate HW02_IO_Adresleme.md")

    # Device selection
    if not devices:
        next_steps.append("Select the devices to use (New Project -> Devices or Dashboard -> Edit Devices)")

    # SCL generation
    if not scl_files and not md_outputs:
        next_steps.append("Start code generation (Pipeline -> Gate 5)")

    # Verification
    if scl_files:
        next_steps.append("Import into TIA Portal and check for compile errors")
        next_steps.append("Run the FAT tests")

    if not next_steps:
        next_steps.append("Project appears complete — ready for FAT/SAT approval")

    for i, step in enumerate(next_steps, 1):
        lines.append(f"{i}. {step}")

    lines.append("")
    lines.append("---")
    lines.append(f"*{_t('generated', lang)}: AUTOMATION_FACTORY project_report.py — {ts}*")
    lines.append(f"*{_t('project', lang)}: {project_path}*")

    return "\n".join(lines)


def write_report(project_path: Path, lang: str = "EN") -> Path:
    """Write the report as _output/PROJECT_REPORT_<ts>.md."""
    content = generate_report(project_path, lang=lang)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = project_path / "_output" / f"PROJECT_REPORT_{ts}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="Project Status Report Generator")
    p.add_argument("project", nargs="?", help="Project path")
    p.add_argument("--lang", choices=["TR", "DE", "EN"], default="EN",
                   help="Report language (default: EN)")
    p.add_argument("--print", dest="print_only", action="store_true",
                   help="Print to screen without writing a file")
    args = p.parse_args()

    if not args.project:
        p.print_help()
        return

    project_path = Path(args.project)
    if not project_path.exists():
        print(f"Project not found: {project_path}")
        return

    if args.print_only:
        print(generate_report(project_path, lang=args.lang))
    else:
        out = write_report(project_path, lang=args.lang)
        print(f"Report written: {out}")


if __name__ == "__main__":
    main()
