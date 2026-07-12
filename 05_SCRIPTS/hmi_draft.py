#!/usr/bin/env python3
"""hmi_draft.py — deterministic RD11 (HMI) + RD08 (Alarm) drafts from the
wired-pulpit inventory of a legacy S5 machine.

The insight (archive survey 2026-07-06): a machine without an HMI is not
missing one — the pulpit IS the HMI specification. Buttons (Taster),
selector switches (Wahlschalter), BCD thumbwheels (Codierschalter) and
indicator lamps (Meldeleuchten) in the symbol file map 1:1 onto RD11
Button / ModeSelector / NumericInput / Indicator rows; Störmeldung lamps
and horns map onto RD08 alarm rows.

Rules (fail-honest, same discipline as the rest of the factory):
  - every label is the VERBATIM symbol text — nothing is invented or
    translated (translation happens in the normal RD review flow);
  - signals without a symbol name are never guessed at — they simply do
    not become HMI tags;
  - NOT-AUS class devices are listed under "Hardwired" and NEVER become
    HMI tags (safety stays physical);
  - existing engineer-edited RD files are NEVER overwritten — only a
    pristine template or a previous auto-draft may be replaced;
  - output carries status DRAFT + a generated-by marker; the engineer
    reviews and approves like any other RD.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from legacy_enrich import load_symbols  # type: ignore
from s5_logic_extract import extract_project_logic, render_expr  # type: ignore

GENERATED_MARKER = "generated-by: hmi_draft (deterministic)"

# German pulpit vocabulary → HMI element class. Word-level, uppercase.
_BUTTON_WORDS = ("TASTER", "TASTE", "QUITTIER", "DRUCKTAST")
_SELECTOR_WORDS = ("WAHLSCHALTER", "WAHLSCH", "SCHLUESSELSCH",
                   "SCHLÜSSELSCH")
_BCD_WORDS = ("CODIERS", "CODIERSCH", "BCD")
_LAMP_WORDS = ("LEUCHT", "LAMPE", "MELDELEUCHTE")
_HORN_WORDS = ("HUPE", "SIRENE")
# fault vocabulary observed on real field machines (blind-test run): fault
# lamps rarely say STOERUNG — they name the condition (WARNUNG …,
# MOTORSCHUTZ …, OELFILTER VERSCHMUTZT, NOT - AUS GEDRUECKT).
_ALARM_WORDS = ("STOER", "STÖR", "SAMMELST", "UEBERLAST", "ÜBERLAST",
                "WARNUNG", "MOTORSCHUTZ", "MOTSCHUTZ", "SICHERUNG",
                "VERSCHMUTZT", "FEHLER", "DEFEKT", "AUSGEFALLEN",
                "NOT - AUS", "NOT-AUS", "NOTAUS")
_SAFETY_WORDS = ("NOT-AUS", "NOTAUS", "NOT AUS", "NOT - AUS")
_LAMPTEST_WORDS = ("LAMPENTEST",)

_BCD_BIT_RE = re.compile(r"\s*2\^\d+\s*$")


def _has(name: str, words) -> bool:
    up = name.upper()
    return any(w in up for w in words)


# Legacy-plant symbol files often start the description with a device-class prefix
# code instead of a full word ("ST START ZYKLUS", "SW EINRICHTBETRIEB",
# "H STOERUNG …") — live finding on the blind-test machine (2026-07-06):
# word matching alone found 0 of its 43 buttons. First token only.
_PREFIX_BUTTON = {"ST"}
_PREFIX_SELECTOR = {"SW"}
_PREFIX_LAMP = {"H", "ML", "LM"}
_PREFIX_HORN = {"HU", "HUPE"}


def _prefix(name: str) -> str:
    parts = name.strip().upper().split()
    return parts[0] if parts else ""


@dataclass
class HmiInventory:
    buttons: list = field(default_factory=list)        # (addr, name)
    selectors: list = field(default_factory=list)      # (addr, name)
    numeric_groups: list = field(default_factory=list)  # (stem, [(addr, name)])
    indicators: list = field(default_factory=list)     # (addr, name, cond)
    alarms: list = field(default_factory=list)         # (addr, name, cond, horn)
    hardwired: list = field(default_factory=list)      # (addr, name, reason)
    dropped: list = field(default_factory=list)        # (addr, name, reason)


def classify_pulpit(project_root: Path) -> HmiInventory:
    root = Path(project_root)
    names = load_symbols(root / "_raw" / "legacy_code")
    inv = HmiInventory()

    # proven output equations — the honest "what does this lamp show"
    q_cond: dict[str, str] = {}
    for nl in extract_project_logic(root):
        if not nl.parsed:
            continue
        for addr, coil in nl.coils.items():
            if addr.startswith("Q") and coil.assign is not None:
                q_cond[addr] = render_expr(coil.assign, names)

    bcd_groups: dict[str, list] = {}
    for addr, name in sorted(names.items()):
        if not name or name.strip().upper().startswith("RESERVE"):
            continue
        pfx = _prefix(name)
        if addr.startswith("I"):
            if _has(name, _SAFETY_WORDS):
                inv.hardwired.append(
                    (addr, name, "safety device — stays physical, never HMI"))
            elif _has(name, _LAMPTEST_WORDS):
                inv.dropped.append(
                    (addr, name, "lamp test — obsolete with an HMI"))
            elif _has(name, _BCD_WORDS) or _BCD_BIT_RE.search(name):
                stem = _BCD_BIT_RE.sub("", name).strip()
                bcd_groups.setdefault(stem, []).append((addr, name))
            elif _has(name, _SELECTOR_WORDS) or pfx in _PREFIX_SELECTOR:
                inv.selectors.append((addr, name))
            elif _has(name, _BUTTON_WORDS) or pfx in _PREFIX_BUTTON:
                inv.buttons.append((addr, name))
        elif addr.startswith("Q"):
            horn = _has(name, _HORN_WORDS) or pfx in _PREFIX_HORN
            is_lamp = _has(name, _LAMP_WORDS) or pfx in _PREFIX_LAMP
            if (is_lamp or horn) and _has(name, _ALARM_WORDS) or horn:
                inv.alarms.append((addr, name, q_cond.get(addr, "❓"), horn))
            elif is_lamp:
                inv.indicators.append((addr, name, q_cond.get(addr, "❓")))

    for stem, members in sorted(bcd_groups.items()):
        if len(members) >= 2:
            inv.numeric_groups.append((stem, members))
        else:
            inv.dropped.append((members[0][0], members[0][1],
                                "single BCD bit — group incomplete, review"))
    return inv


# ---------------------------------------------------------------------------
# RD rendering
# ---------------------------------------------------------------------------

def _tag_id(prefix: str, name: str, addr: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")[:28]
    return f"HMI_{prefix}_{slug or addr.replace('.', '_')}"


def _fm(project_id: str) -> str:
    # "Status: DRAFT_UNVERIFIED" is the analyzer's AUTHORITATIVE draft banner
    # (project_analyzer.detect_rd_file_status) — without it a small honest
    # deterministic draft falls into the <3 KB size heuristic and reads as
    # "template", freezing the gate (E2E #2 finding, mixer-line test machine).
    return ("> **Status: DRAFT_UNVERIFIED** — deterministic pulpit draft, "
            "engineer review required.\n\n"
            f"```yaml\nproject_id: {project_id}\n"
            f"filled_by: {GENERATED_MARKER} — DRAFT_UNVERIFIED\n"
            f"filled_at: {date.today().isoformat()}\n"
            "output_language: DE\nstatus: DRAFT_UNVERIFIED\n```\n")


def render_rd11(inv: HmiInventory, project_id: str) -> str:
    rows: list[str] = []
    for addr, name in inv.buttons:
        rows.append(f"| {_tag_id('BTN', name, addr)} | DB_HMI.Cmd."
                    f"{_member('b', name, addr)} | SCR002 | Button | "
                    f"{name} |  | {name} | Write | | | | legacy {addr} |")
    for addr, name in inv.selectors:
        rows.append(f"| {_tag_id('SEL', name, addr)} | DB_HMI.Cmd."
                    f"{_member('b', name, addr)} | SCR002 | Button | "
                    f"{name} |  | {name} | Write | | | | legacy {addr} · "
                    "selector position |")
    for stem, members in inv.numeric_groups:
        addrs = ", ".join(a for a, _n in members)
        unit = "s" if "SEKUND" in stem.upper() else ""
        rows.append(f"| {_tag_id('SET', stem, members[0][0])} | DB_HMI.Set."
                    f"{_member('i', stem, members[0][0])} | SCR020 | "
                    f"NumericInput | {stem} |  | {stem} | Write | 0 | 999 | "
                    f"{unit} | replaces BCD thumbwheel bits {addrs} |")
    for addr, name, cond in inv.indicators:
        rows.append(f"| {_tag_id('LMP', name, addr)} | DB_HMI.Sts."
                    f"{_member('b', name, addr)} | SCR001 | Indicator | "
                    f"{name} |  | {name} | Read | | | | legacy {addr} · "
                    f"shows: {cond} |")

    screens = ['| SCR001 | Overview | Overview | Operator | Overview |  | '
               'Übersicht | SCR002,SCR010 | | pulpit lamps | Active |']
    if inv.buttons or inv.selectors:
        screens.append('| SCR002 | Commands | Detail | Operator | Commands |'
                       '  | Bedienung | SCR001 | | pulpit buttons/selectors |'
                       ' Active |')
    if inv.alarms:
        screens.append('| SCR010 | Alarm_List | Alarm | Operator | Alarms |'
                       '  | Alarme | SCR001 | (all) | ISA-18.2 summary |'
                       ' Active |')
    if inv.numeric_groups:
        screens.append('| SCR020 | Settings | Recipe | Supervisor | Settings'
                       ' |  | Einstellungen | SCR001 | | replaces BCD '
                       'thumbwheels | Active |')

    hardwired = [f"| {a} | {n} | {r} |" for a, n, r in inv.hardwired]
    dropped = [f"| {a} | {n} | {r} |" for a, n, r in inv.dropped]
    total_tags = (len(inv.buttons) + len(inv.selectors)
                  + len(inv.numeric_groups) + len(inv.indicators))

    return f"""# RD11_HMI — {project_id}

> {GENERATED_MARKER} — from the wired-pulpit inventory (symbol file +
> proven lamp equations). DRAFT: labels are VERBATIM German symbol text;
> translate + review before approval. Nothing here was invented.

---

## Frontmatter

{_fm(project_id)}
---

## Summary

- Total screens: {len(screens)}
- Total HMI tags: {total_tags}
- Access: Operator {len(inv.buttons) + len(inv.indicators)} | Supervisor {len(inv.numeric_groups)} | Engineer 0
- Multi-lang: EN 0% | TR 0% | DE 100% (verbatim legacy symbols)

---

## Sheet 1: ScreenList

| ScreenID | ScreenName | ScreenType | AccessLevel | Title_EN | Title_TR | Title_DE | NavigateTo | LinkedAlarm | Notes | Status |
|----------|------------|------------|-------------|----------|----------|----------|------------|-------------|-------|--------|
{chr(10).join(screens)}

---

## Sheet 2: TagList

| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |
|-----------|---------|-----------|-------------|----------|----------|----------|-----------|----------|----------|---------|-------|
{chr(10).join(rows) if rows else '| | | | | | | | | | | |'}

---

## Hardwired (stays physical — NEVER moved to HMI)

| Legacy addr | Symbol | Reason |
|-------------|--------|--------|
{chr(10).join(hardwired) if hardwired else '| | | |'}

---

## #UNKNOWNS

| HMI element | Reason |
|-------------|--------|
{chr(10).join(dropped) if dropped else '| | |'}

---

*Deterministic draft — engineer review + translation required (RD flow).*
"""


def _member(prefix: str, name: str, addr: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_",
                  name.title().replace(" ", ""))[:24].strip("_")
    return f"{prefix}{slug or addr.replace('.', '_')}"


def render_rd08(inv: HmiInventory, project_id: str) -> str:
    rows = []
    for i, (addr, name, cond, horn) in enumerate(inv.alarms, 1):
        crit = horn or _has(name, ("SAMMELST", "NOT"))
        cls = "Critical" if crit else "Warning"
        prio = i if crit else 50 + i
        rows.append(
            f"| ALM{i:04d} | {_member('A', name, addr)} | {cls} | {prio} | "
            f"{addr} | {addr} = TRUE | | | {name} |  | {name} | "
            f"{'Y' if crit else 'N'} | | | | | legacy lamp/horn · "
            f"condition: {cond} | Active |")
    return f"""# RD08_Alarm — {project_id}

> {GENERATED_MARKER} — from Störmeldung lamps/horns of the wired pulpit.
> DRAFT: texts are VERBATIM German symbols (AlarmText_EN column carries
> the German text until translated in review). RecommendedAction is left
> for the engineer — no generic filler is invented.

---

## Frontmatter

{_fm(project_id)}
---

## Summary

- Total alarms: {len(inv.alarms)}
- Class: Critical {sum(1 for a in inv.alarms if a[3] or _has(a[1], ('SAMMELST', 'NOT')))} | Warning {sum(1 for a in inv.alarms if not (a[3] or _has(a[1], ('SAMMELST', 'NOT'))))} | Info 0
- AcknRequired: per class rule
- Multi-lang coverage: EN 0% | TR 0% | DE 100%

---

## Alarms

| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | LimitValue | LimitUnit | AlarmText_EN | AlarmText_TR | AlarmText_DE | AcknRequired | SuppressCondition | LinkedTimer | LinkedSF | RecommendedAction | Notes | Status |
|---------|-----------|-------|----------|------------|------------------|------------|-----------|--------------|--------------|--------------|--------------|-------------------|-------------|----------|-------------------|-------|--------|
{chr(10).join(rows) if rows else '| | | | | | | | | | | | | | | | | | |'}

---

## #UNKNOWNS

| Old alarm | Reason |
|-----------|--------|
| | |

---

*Deterministic draft — engineer review + translation required (RD flow).*
"""


# ---------------------------------------------------------------------------
# write with overwrite guard
# ---------------------------------------------------------------------------

def _data_rows_text(text: str) -> int:
    """Markdown table DATA rows (headers/separators/empty placeholders out)."""
    n = 0
    for ln in text.splitlines():
        s = ln.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue                       # separator row
        if not any(cells):
            continue                       # empty placeholder row
        n += 1
    return max(0, n)


def _data_rows(fp: Path) -> int:
    if not fp.exists():
        return 0
    try:
        return _data_rows_text(fp.read_text(encoding="utf-8",
                                            errors="replace"))
    except Exception:
        return 0

def _may_overwrite(fp: Path, project_root: Path | None = None) -> bool:
    if not fp.exists():
        return True
    text = fp.read_text(encoding="utf-8", errors="replace")
    if (GENERATED_MARKER in text                        # our own old draft
            or "<PROJECT_CODE>" in text                 # pristine template
            or "filled_by: <Engineer Name>" in text):
        return True
    # B1a (E2E finding 2026-07-07): an AI topic-extraction draft is NOT
    # engineer content — refusing to replace it killed the whole HMI chain
    # (the AI draft ignored the DB_HMI contract and the deterministic,
    # proof-based pulpit draft could not step in). An AI draft may be
    # replaced UNLESS the engineer has already reviewed/locked that RD
    # (then it is signed work, hands off).
    if "source: ai_preanalysis" in text and project_root is not None:
        rd_id = fp.name[:4].upper()          # "RD11_HMI.md" → "RD11"
        try:
            state = json.loads((Path(project_root) / "PROJECT_STATE.json")
                               .read_text(encoding="utf-8"))
            rec = (state.get("rd_verifications") or {}).get(rd_id) or {}
            return not (rec.get("reviewed") or rec.get("locked"))
        except Exception:
            return True                       # no review record → replaceable
    return False


def generate_hmi_drafts(project_root: Path,
                        project_id: str = "") -> dict:
    root = Path(project_root)
    meta = root / "metadata"
    meta.mkdir(exist_ok=True)
    pid = project_id or root.name
    inv = classify_pulpit(root)

    written, refused = [], []
    from hmi_table_edit import apply_saved_decisions  # type: ignore
    for kind, name, text in (("rd11", "RD11_HMI.md", render_rd11(inv, pid)),
                             ("rd08", "RD08_Alarm.md", render_rd08(inv, pid))):
        fp = meta / name
        if not _may_overwrite(fp, root):
            refused.append(f"{name}: engineer content present — not touched")
            continue
        # Richness guard (E2E #2 finding, mixer-line test machine): on a big machine
        # the AI extracts alarms from the CODE (hundreds of networks) — far
        # richer than the pulpit's lamp/horn list. Replacing a fuller draft
        # with a poorer one froze the gate. Keep whichever carries more rows.
        old_rows = _data_rows(fp)
        new_rows = _data_rows_text(text)
        _old_text = (fp.read_text(encoding="utf-8", errors="replace")
                     if fp.exists() else "")
        _is_own_or_template = (GENERATED_MARKER in _old_text
                               or "<PROJECT_CODE>" in _old_text
                               or "filled_by: <Engineer Name>" in _old_text)
        if fp.exists() and not _is_own_or_template and old_rows > new_rows:
            refused.append(
                f"{name}: existing draft is richer ({old_rows} rows vs "
                f"{new_rows} deterministic) — kept. Delete it first if you "
                "want the pulpit draft.")
            continue
        # Never lose the replaced draft — same _history discipline as the
        # AI draft writer.
        if fp.exists() and fp.stat().st_size > 0:
            try:
                from datetime import datetime as _dt, timezone as _tz
                hist = meta / "_history"
                hist.mkdir(exist_ok=True)
                ts = _dt.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
                (hist / f"{ts}_{name}").write_text(
                    fp.read_text(encoding="utf-8", errors="replace"),
                    encoding="utf-8")
            except Exception:
                pass
        # regeneration can NEVER erase engineer grid edits — persisted
        # decisions are re-applied on top of the fresh draft
        fp.write_text(apply_saved_decisions(root, kind, text),
                      encoding="utf-8")
        written.append(name)
    # Delivery baseline: first version of the drafts, for REVISION_LOG.
    try:
        from revision_log import snapshot_baseline  # type: ignore
        snapshot_baseline(root)
    except Exception:
        pass
    return {
        "written": written, "refused": refused,
        "buttons": len(inv.buttons), "selectors": len(inv.selectors),
        "numeric": len(inv.numeric_groups),
        "indicators": len(inv.indicators), "alarms": len(inv.alarms),
        "hardwired": len(inv.hardwired),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: hmi_draft.py <project_root>")
        raise SystemExit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    print(generate_hmi_drafts(Path(sys.argv[1])))
