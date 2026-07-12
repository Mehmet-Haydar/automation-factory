# RD10_FBSpec — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_10_FBSPEC.md`. Schema: `rd10_fbspec.schema.json`.
> **Two sheets:** BlockList + ParamList.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total blocks: __ (FB: __ | FC: __)
- Total parameters: __
- Multi-instance FB: __

---

## Sheet 1: BlockList

| BlockName | BlockType | Version | Description | CalledFrom | InstanceDB | LinkedEquipment | TemplateBase | Notes | Status |
|-----------|-----------|---------|-------------|------------|------------|------------------|--------------|-------|--------|
| FB_Motor | FB | 1.0.0 | Generic DOL motor control | OB1 | DB_Mot_Pump01, DB_Mot_Conv01 | Pump01, Conveyor01 | GLOBAL_FB_TEMPLATE | Original: FB10 | Active |
| FB_Valve | FB | 1.0.0 | Solenoid valve control | OB1 | DB_Val_V01, DB_Val_V02 | V01, V02 | GLOBAL_FB_TEMPLATE | | Active |
| FC_ScanInputs | FC | 1.0.0 | Read physical inputs | OB1 | | (global) | Custom | Original: FC1 | Active |
| FB_ModeMgr | FB | 1.0.0 | Operating mode manager | OB1 | DB_ModeMgr | (singleton) | GLOBAL_FB_TEMPLATE | RD04 referenced | Active |

---

## Sheet 2: ParamList

| BlockName | ParamName | Section | Type | DefaultValue | Description | LinkedTag | Notes |
|-----------|-----------|---------|------|--------------|-------------|-----------|-------|
| FB_Motor | in_bStartCmd | IN | BOOL | FALSE | Start command | | |
| FB_Motor | in_bStopCmd | IN | BOOL | FALSE | Stop command | | |
| FB_Motor | in_rSetSpeed | IN | REAL | 0.0 | Speed setpoint (orig: Sollwert) | | |
| FB_Motor | out_bRunning | OUT | BOOL | FALSE | Motor running feedback | | |
| FB_Motor | out_iFault | OUT | INT | 0 | Fault code | | |
| FB_Motor | inout_bReset | INOUT | BOOL | FALSE | Reset (toggled by caller) | | |
| FB_Motor | stat_bInternalState | STAT | BOOL | FALSE | Internal state | | |
| FB_Motor | temp_rDelta | TEMP | REAL | | Calculation buffer | | |
| FB_Valve | in_bOpenCmd | IN | BOOL | FALSE | Open command | | |
| FB_Valve | out_bOpened | OUT | BOOL | FALSE | Open feedback | | |

---

## #UNKNOWNS

| Block | Reason |
|-------|--------|
| | |

---

## Fill-in Notes

- **BlockName format:** `^(FB|FC)_[A-Z][A-Za-z0-9_]+$`
- **Version semver:** `^\d+\.\d+\.\d+$` (e.g. 1.0.0)
- **BlockType=FB → InstanceDB MANDATORY** (comma-separated list if multi-instance)
- **ParamName format:** `^(in|out|inout|stat|temp)_[a-z][A-Za-z0-9]+$`
- **Section enum:** IN/OUT/INOUT/STAT/TEMP (must match the prefix)
- **Type:** IEC 61131-3 enum (same as RD02)
- **Multi-instance:** The interface is written once (in ParamList); instance info goes in the BlockList InstanceDB column
- **AOI (AB):** List as BlockType=FB
- **METHOD (CODESYS V3):** As BlockName_Method, put "OOP Method" in Notes
- **Standards:** IEC 61131-3 §2.5, PLCopen

---

*Template v1.0.0 — RD10 FB Spec. The direct source for Gate 5 code generation.*
