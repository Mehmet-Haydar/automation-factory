# RD13_Annotation — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_13_ANNOTATION.md`. Schema: `rd13_annotation.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <AI Engine / Engineer Name>
filled_at: <YYYY-MM-DD>
plc_platform: <S5 | S7_300 | S7_1500 | AB_L5X | CODESYS>
plc_language: <STL | SCL | LD | ST | SFC>
status: <DRAFT | AI_COMPLETE | HUMAN_REVIEWED | APPROVED>
```

---

## Summary

- Total annotations: __
- WarningFlag: N __ | Y_MAGIC_NUMBER __ | Y_HARDCODED_ADDR __ | Y_UNDOCUMENTED __ | Y_SAFETY_CONCERN __
- ConfidenceLevel: HIGH __ | MEDIUM __ | LOW __ | HUMAN_REQUIRED __

---

## Annotations

| AnnotationID | BlockName | BlockType | PLCPlatform | PLCLanguage | LineRef | NetworkRef | OriginalCode (summary) | FunctionCategory | Explanation_TR | DataFlowIn | DataFlowOut | LinkedRD | WarningFlag | WarningDetail | ConfidenceLevel | ConfidenceNote | Status |
|--------------|-----------|-----------|-------------|-------------|---------|------------|------------------------|-------------------|----------------|------------|-------------|----------|-------------|---------------|------------------|------------------|--------|
| ANN0001 | FC10 | FC | S7_300 | STL | L001-L008 | NW001 | A I 0.0\nAN M 10.5\n= Q 0.0 | LOGIC_COMBINATIONAL | I0.0 (Start) ve M10.5 (NOT motor running) AND ile Q0.0 (kontaktör) Active. Mutlak adres tipik 90'lar standardı. | I0.0, M10.5 | Q0.0 | RD01 | Y_HARDCODED_ADDR | Unnamed absolute addresses | MEDIUM | M10.5 function unclear | AI_COMPLETE |

---

## Special Findings

### Y_SAFETY_CONCERN detections (HIGH priority)

| AnnotationID | Block | Description |
|--------------|-------|-------------|
| | | |

### Y_DEAD_CODE detections

| AnnotationID | Block | Description |
|--------------|-------|-------------|
| | | |

---

## #UNKNOWNS

| Code snippet | Reason |
|--------------|--------|
| | |

---

## Fill-in Notes

- **AnnotationID format:** `^ANN\d{4}$`
- **LineRef format:** `^L\d{3,6}(-L\d{3,6})?$`
- **OriginalCode preserved VERBATIM** (max 2000 chars)
- **Explanation_TR min 10 chars**, Turkish (multi-language field, kept Turkish by design)
- **FunctionCategory enum:** 28 values (IO_READ/IO_WRITE/LOGIC_COMBINATIONAL/...)
- **WarningFlag ≠ N → WarningDetail MANDATORY**
- **ConfidenceLevel=LOW/HUMAN_REQUIRED → ConfidenceNote MANDATORY**
- **NEVER assign HIGH confidence to safety code** (MEDIUM at most)
- **Status:** DRAFT/AI_COMPLETE/HUMAN_REVIEWED/APPROVED/OBSOLETE

---

*Template v1.1.0 — RD13 Legacy Annotation. Full English body (2026-05-23). Explanation_TR cells stay Turkish by design (multi-language engineer-review field).*
