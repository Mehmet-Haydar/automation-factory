---
title: Retrofit HMI Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD11_HMI
prerequisite: [MDSCHEMA_RAWDATA_11_HMI.md, RETROFIT_EXTRACT_DATADICT.md, GLOBAL_LANG_POLICY.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_HMI_FROM_CODE.md
---

# RETROFIT_EXTRACT_HMI.md — HMI Extraction Procedure

> **Goal:** extract screen and tag information from the legacy HMI project, make it ISA-101 compliant, and add multi-language text support.

---

## 1. Prerequisites

- [ ] Legacy HMI project at hand:
  - Siemens WinCC: `.MCP` or export XML
  - Allen-Bradley FactoryTalk View: `.MED` (Studio Edition)
  - CODESYS Visualization: inside `.project`
  - 3rd-party (B&R, Beijer, Beckhoff): vendor format
- [ ] RD01 IO + RD02 DataDict complete (for the PLC_Tag reference)
- [ ] Customer language defined (TR/EN/DE)

---

## 2. HMI Export Methods

### 2.1 Siemens WinCC (Classic)
- Configuration → Tools → Export → Variables (CSV)
- Screen objects: each screen reviewed manually

### 2.2 TIA WinCC Unified
- Project → Tools → Export → HMI Tags
- Screens: TIA Openness XML

### 2.3 Allen-Bradley FactoryTalk View
- Tools → Application Manager → Export Tags (.xml)
- Displays (`*.GFX`) → manual review

### 2.4 CODESYS Visualization
- Project → Export → Visualization XML

---

## 3. Workflow

```
[1] HMI export + _parsed.md ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_HMI_FROM_CODE.md
       ↓
[3] RD11_HMI_draft.md (two sheets: ScreenList + TagList)
       ↓
[4] Human review:
   ├─ Review operator HMI screens (screenshots)
   ├─ Translate multi-lang text using the glossary
   ├─ Assign AccessLevel (operator/supervisor/engineer)
   └─ Check ISA-101 compliance
       ↓
[5] RD11_HMI.xlsx
```

---

## 4. Multi-Language Text Strategy

If the legacy HMI is in German, retrofit does a 3-layer conversion:

```
[Original: German]
       ↓ kept AS-IS
[Title_DE / Label_DE]
       ↓ AI translation
[Title_EN / Label_EN]    (always mandatory)
       ↓ (if project is TR)
[Title_TR / Label_TR]
```

Use the glossary: `lang_glossary/GLOSSARY_BASE.md` → EN/TR/DE mappings.

---

## 5. Human Review Checklist

#### A. Sheet 1: ScreenList
- [ ] ScreenID format `^SCR\d{3}$`
- [ ] ScreenType correct (Overview/Detail/Alarm/Trend/Recipe/Diagnostic/Navigation)
- [ ] AccessLevel assignment (ISA-101: Operator/Supervisor/Engineer)
- [ ] Title_EN on every row
- [ ] Title_DE preserves the original (from legacy WinCC)
- [ ] Title_TR translated (if project is TR)
- [ ] NavigateTo reflects screen-to-screen navigation

#### B. Sheet 2: TagList
- [ ] HMI_TagID format `^HMI_[A-Z0-9_]+$`
- [ ] PLC_Tag exists in RD01 or RD02
- [ ] ElementType enum (Button/Indicator/NumericDisplay/NumericInput/…)
- [ ] ReadWrite enum correct
- [ ] NumericInput → MinValue/MaxValue populated (input validation)
- [ ] EngUnit (for analog)
- [ ] Multi-lang Label_EN mandatory

#### C. ISA-101 Compliance
- [ ] Color usage standardized (Critical red, Warning yellow, Info blue)
- [ ] Access hierarchy reasonable
- [ ] Alarm widget lives on a dedicated screen like SCR010

---

## 6. Common Pitfalls

- ❌ **AccessLevel always Operator:** the Supervisor/Engineer distinction is lost
- ❌ **Treating a faceplate screen as Overview:** must be Detail
- ❌ **Treating a Recipe screen as Form:** Recipe is its own type
- ❌ **Empty Min/Max on NumericInput:** the operator can enter wrong values
- ❌ **Multi-lang in one language only:** customer may reject
- ❌ **PLC_Tag as an absolute address:** use the symbolic tag (RD01)

---

## 7. Gate 3 Checklist

- [ ] All screens listed
- [ ] All HMI tags listed
- [ ] AccessLevel assignments verified with operator + supervisor
- [ ] Multi-lang text (project language + EN + DE)
- [ ] ISA-101 color + type standards applied
- [ ] Cross-reference (PLC_Tag) present in RD01/RD02

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_11_HMI.md`
- **AI prompt:** `PROMPT_EXTRACT_HMI_FROM_CODE.md`
- **Language policy:** `GLOBAL_LANG_POLICY.md`
- **Glossary:** `01_GLOBAL_STANDARDS/lang_glossary/`
- **Standards:** ISA-101, IEC 62714-1, NAMUR NE107

---

*v1.1.0 — Full English body (2026-05-23). The HMI is the operator's window into the machine. Old-vs-new HMI difference = operator-training cost.*
