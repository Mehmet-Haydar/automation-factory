---
title: RD13_Annotation — Kunde Müller (AI line-by-line annotation)
last_validated: 2026-05
status: ACTIVE
---

# RD13_Annotation — Kunde Müller (AI line-by-line annotation)

```yaml
status: DRAFT (50%)
plc_platform: S7_300
plc_language: STL
```

## Summary
- 47 critical blocks/networks annotated by the AI
- WarningFlag: 12× Y_HARDCODED_ADDR, 8× Y_UNDOCUMENTED, **4× Y_SAFETY_CONCERN**, 2× Y_DEAD_CODE
- ConfidenceLevel: 30 HIGH, 14 MEDIUM, 3 HUMAN_REQUIRED

## Annotations (3 example rows shown — 47 total)

| AnnotationID | BlockName | LineRef | OriginalCode (excerpt) | FunctionCategory | Explanation_EN | WarningFlag | ConfidenceLevel | Status |
|--------------|-----------|---------|---------------------|-------------------|----------------|-------------|------------------|--------|
| ANN0001 | OB1 | L001-L015 | `A I 0.0\nA I 0.1\n=  Q 0.0` | LOGIC_COMBINATIONAL | Q0.0 (motor) is driven by an AND of I0.0 (Start) and I0.1 (Stop NC). Classic 1990s-style absolute-address logic. | Y_HARDCODED_ADDR | HIGH | AI_COMPLETE |
| ANN0042 | FC10 | L080-L085 | `A I 100.0\nA I 100.1\nAN M 50.0\n= Q 3.7` | SAFETY_LOGIC | **CRITICAL:** the master contactor (Q3.7) is driven by the E-Stop (I100.0, I100.1) combined with a "maintenance bypass" (M50.0). This is safety logic on a standard PLC — not IEC 62061 compliant without an F-PLC. | **Y_SAFETY_CONCERN** | **MEDIUM** (safety findings are never given HIGH confidence) | AI_COMPLETE |
| ANN0089 | FB30 | L045-L050 | `L 100\nT MD 200\nL MD 200\n+R\nT DB31.DBD0` | DEAD_CODE | A calculation result is written to MD200, then copied to DB31.DBD0, but DB31.DBD0 is never read elsewhere. Likely a debug leftover. | Y_DEAD_CODE | MEDIUM | AI_COMPLETE |

## Y_SAFETY_CONCERN Dedicated List (carried into RD14 FND001)

| ANN ID | Block | Network | Description |
|--------|-------|---------|----------|
| ANN0042 | FC10 | NW5 | E-Stop North + Master Contactor (standard PLC) |
| ANN0043 | FC10 | NW6 | E-Stop South (parallel circuit) |
| ANN0051 | FC10 | NW8 | Light Curtain Loading + BYPASS logic ⚠️ |
| ANN0078 | FC10 | NW9 | Light Curtain Unloading |

## #UNKNOWNS

| Code | Reason |
|-----|-------|
| FC30 CASE M10.0..M10.7 | Pseudo state machine — sequence needs confirmation via operator workshop |
| MW100..MW150 | Not in the symbol table, function unclear — operator interview needed |

*v1.0.0 — Source for the RD14 modernization analysis.*
