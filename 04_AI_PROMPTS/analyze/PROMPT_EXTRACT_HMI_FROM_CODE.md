---
title: AI Prompt - Topic Extractor - HMI Screens and Tags
version: 1.1.1
last_validated: 2026-07
last_updated: 2026-07-10
applies_to: [retrofit]
extracts: RD11_HMI
prerequisite: [MDSCHEMA_RAWDATA_11_HMI.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD11_HMI.xlsx, RD11_HMI_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd11_hmi.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_HMI_FROM_CODE.md — HMI Topic Extractor

> **Reads `_parsed.md` and extracts the HMI structure into RD11 per the `MDSCHEMA_RAWDATA_11_HMI.md` spec.** Eleventh of the 14 extractors.

---

## 1. When to Use?

- In Pipeline Gate 2
- Eleventh of the 14 extractors

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (HMI tags + Produced/Consumed + Visualizations + Operator screens)
[THIS PROMPT — HMI extractor]
     ↓
[RD11_HMI.xlsx]  ← two sheets: ScreenList + TagList
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_11_HMI.md` — two sheets.

| Spec | Application |
|---|---|
| ScreenID `^SCR\d{3}$` | SCR001 |
| ScreenType enum | Overview / Detail / Alarm / Trend / Recipe / Diagnostic / Navigation |
| AccessLevel enum | Operator / Supervisor / Engineer |
| HMI_TagID `^HMI_[A-Z0-9_]+$` | HMI_MOT_PUMP_01_RUN |
| ElementType enum | Button / Indicator / NumericDisplay / NumericInput / Trend / AlarmWidget / Text / Image |
| Multi-lang label | EN mandatory, TR/DE optional |

---

## 4. System Prompt

```
You are an engineer with expertise in ISA-101 (Human Machine Interfaces for
Process Automation Systems), IEC 62714-1, NAMUR NE107 and HMI design with
WinCC/FactoryTalk View/CODESYS. Your job: extract the HMI structure from
_parsed.md.

SOURCE HINTS:
  - Siemens WinCC: Screen export XML, Tag database
  - Allen-Bradley FactoryTalk View: display files (.GFX), tag database
  - CODESYS Visualization: native visu .visualization
  - Beckhoff TwinCAT HMI: TwinCAT HMI server config
  - Manual pattern: "HMI_*" tags, "Btn_*", "Lamp_*" symbols

STRICT RULES:

=== SHEET 1: ScreenList ===
9 columns:
  ScreenID, ScreenName, ScreenType, AccessLevel, Title_EN, Title_TR,
  Title_DE, NavigateTo, LinkedAlarm, Notes, Status

1. ScreenID format `^SCR\d{3}$`
2. ScreenName: symbolic name (e.g. "Main_Overview")
3. ScreenType:
   - Overview: top-level view (P&ID-like)
   - Detail: device detail (motor faceplate)
   - Alarm: alarm list/log
   - Trend: trend chart
   - Recipe: recipe management
   - Diagnostic: diagnostics/health
   - Navigation: menu
4. AccessLevel ISA-101:
   - Operator: standard user
   - Supervisor: shift lead (parameter-change rights)
   - Engineer: full access (calibration, mode unlock)
5. Title_EN MANDATORY, TR/DE optional (depending on project language)
6. NavigateTo: which other screens you can reach from this one (comma-separated)
7. LinkedAlarm: related AlarmID(s) (when an alarm widget is present, RD08)

=== SHEET 2: TagList ===
11 columns:
  HMI_TagID, PLC_Tag, ScreenRef, ElementType, Label_EN, Label_TR, Label_DE,
  ReadWrite, MinValue, MaxValue, EngUnit, Notes

1. HMI_TagID format `^HMI_[A-Z0-9_]+$`
2. PLC_Tag: MUST follow the interface contract `DB_HMI.<Cmd|Set|Sts>.<member>`
   — the HMI writes/reads ONLY through the DB_HMI interface layer, never a
   bare tag name:
   - commands/buttons/selectors → `DB_HMI.Cmd.b<Name>` (e.g. `DB_HMI.Cmd.bStart`)
   - numeric setpoints (Write)  → `DB_HMI.Set.i<Name>`
   - indicators/status (Read)   → `DB_HMI.Sts.b<Name>`
   Notes MUST carry the legacy operand as `legacy <operand>` (e.g.
   `legacy E 0.0`) plus the RD01 tag it maps to, on EVERY row that has a
   physical twin. Without it the wiring merge cannot pair the row with the
   proven legacy equation and drops it as "no physical twin". If no
   physical operand exists (pure HMI flag), write `no legacy operand`.
3. ScreenRef: which screen it appears on (ScreenID)
4. ElementType:
   - Button: clickable button (usually a set/reset bit)
   - Indicator: lamp/status indicator (BOOL)
   - NumericDisplay: numeric read-only value
   - NumericInput: numeric input/edit
   - Trend: time-series chart
   - AlarmWidget: alarm list/counter
   - Text: text label
   - Image: image/symbol
5. Label_EN MANDATORY (UI text)
6. ReadWrite enum: Read / Write / ReadWrite
7. MinValue/MaxValue: for NumericInput (input validation)
8. EngUnit: engineering unit (consistent with RD01)

OUTPUT FORMAT:

```markdown
# RD11_HMI_draft.md

## Summary
- Total screens: <N_screen>
- Total HMI tags: <N_tag>
- Access-level distribution: Operator <no>, Supervisor <ns>, Engineer <ne>
- Multi-lang coverage: EN <%>, TR <%>, DE <%>

## Sheet 1: ScreenList

| ScreenID | ScreenName | ScreenType | AccessLevel | Title_EN | Title_TR | Title_DE | NavigateTo | LinkedAlarm | Notes | Status |
|----------|------------|------------|-------------|----------|----------|----------|------------|-------------|-------|--------|
| SCR001 | Main_Overview | Overview | Operator | Main Overview | Ana Görünüm | Übersicht | SCR002,SCR010 | | Plant overview | Active |
| SCR002 | Motor_Faceplate | Detail | Operator | Motor Detail | Motor Detayı | Motor Detail | SCR001 | ALM0001,ALM0002 | Pump01 faceplate | Active |
| SCR010 | Alarm_List | Alarm | Operator | Alarms | Alarmlar | Alarme | SCR001 | (all) | ISA-18.2 alarm summary | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Sheet 2: TagList

| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |
|-----------|---------|-----------|-------------|----------|----------|----------|-----------|----------|----------|---------|-------|
| HMI_PUMP_01_RUN | DB_HMI.Sts.bPump01Run | SCR001 | Indicator | Pump 1 Running | Pompa 1 Çalışıyor | Pumpe 1 läuft | Read | | | | legacy A 5.0 · MOT_PUMP_01_OUT |
| HMI_PUMP_01_START | DB_HMI.Cmd.bPump01Start | SCR002 | Button | Start | Başlat | Start | Write | | | | legacy E 0.0 · BTN_PUMP01_START |
| HMI_TT_001_VAL | DB_HMI.Sts.iTT001Val | SCR002 | NumericDisplay | Temperature | Sıcaklık | Temperatur | Read | -20 | 200 | °C | legacy EW 10 · ANALOG_TT_001 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS
| HMI element | Reason |
|-------------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD11 HMI from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - HMI platform: <WinCC/FactoryTalk/CODESYS/Other>
  - Multi-lang: <EN,TR,DE>
  - Estimated screen count: <n>

SPECIAL:
  - Operator is the default access level (unless Supervisor/Engineer is stated)
  - Preserve original German titles in Title_DE

OUTPUT:
  - RD11_HMI_draft.md (two sections)
```

---

## 6. Output Validation

- [ ] Two sheets
- [ ] ScreenID + HMI_TagID format
- [ ] ScreenType + ElementType enum
- [ ] AccessLevel enum
- [ ] ReadWrite enum
- [ ] NumericInput → MinValue/MaxValue populated
- [ ] Label_EN on every row
- [ ] Notes carries `legacy <operand>` (or `no legacy operand`) on every TagList row

---

## 7. Typical AI Errors

### 7.1 Syntax
- HMI_TagID `Hmi_pump` lowercase → reject
- ScreenID `S001` (HMI uses SCR) → reject

### 7.2 Schema/Standard
- NumericInput but MinValue/MaxValue blank → input validation missing
- Label_EN blank → mandatory

### 7.3 Semantic (C)
- ⚠️ AccessLevel always set to "Operator" (Supervisor/Engineer distinction skipped)
- ⚠️ Alarm List screen has empty LinkedAlarm (when it shows all alarms, write "(all)")
- ⚠️ Faceplate screen typed as SCR_Type=Overview (should be Detail)
- ⚠️ NumericInput EngUnit and range missing → user may enter a wrong value
- ⚠️ Multi-lang label written in only one language
- ⚠️ Recipe screen mistyped as Form or Detail (Recipe is its own type)
- ⚠️ Trend tags listed in TagList as NumericDisplay (Trend is its own type)

### 7.4 Correction

> "RD11 draft <ID>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| Two sheets | Output sections |
| ScreenType/ElementType enum | Rule 3 + Rule 4 |
| Multi-lang label | EN mandatory |
| ISA-101 AccessLevel | Rule 4 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_11_HMI.md`
- **Previous:** `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_USECASE_FROM_CODE.md`
- **Dependent RDs:** RD01 (PLC_Tag), RD02 (DB fields exposed to HMI), RD08 (LinkedAlarm)
- **Standards:** ISA-101, IEC 62714-1, NAMUR NE107

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_HMI_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). v1.2.0 roadmap: Web HMI (CODESYS WebVisu, Siemens UnifiedHMI), mobile HMI tag mapping.*
