# RD01_IO_List — Per-Project Template

> **This file is copied and filled in for each project.** The XLSX equivalent is generated automatically with `script_md_to_xlsx.py`. Spec: `MDSCHEMA_RAWDATA_01_IO.md`. Schema: `08_METADATA_INPUT/schema/rd01_io.schema.json`.

---

## Frontmatter (per project)

```yaml
project_id: <PROJECT_CODE>
project_name: <Project Name>
customer: <Customer>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
output_language: <TR | EN | DE>
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total signals: __
- DI: __ | DO: __ | AI: __ | AO: __
- Safety-related: __
- Module count: __

---

## Signals

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | SourceModule | OldTag | Notes | Status |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|----------|----------|---------------|--------------|--------|-------|--------|
| MOT_CV01_001_DRIVE | %Q0.0 | BOOL | DO | Conveyor1 | Direct-on-line motor drive output | | | | | N | PLC1_DO_001 | A_Rollenbahn_1 | | Active |
| MOT_CV01_001_RUN | %I0.0 | BOOL | DI | Conveyor1 | Motor running feedback | NO | | | | N | PLC1_DI_001 | E_Lauf_Forderer | | Active |
| ANALOG_TT_001 | %IW64 | INT | AI | Tank01 | Tank temperature | | °C | -20 | 200 | N | PLC1_AI_001 | EW_Temp_Tank | | Active |
| F_I_EStop_N | %I600.0 | BOOL | DI | SafetyBus | Emergency stop north (NC) | NC | | | | Y | F_DI_001 | F_NotAus_Nord | | Active |

---

## #UNKNOWNS (Gate 3 — to be filled by a human)

| Old Tag | Reason |
|---------|--------|
| | |

---

## Fill-in Notes

- **Tag format:** `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$` — e.g. `MOT_CV01_001_DRIVE`
- **OldTag:** Original name (German/Turkish kept AS-IS)
- **Description:** English + in `(orig: <original>)` format
- **F-prefix:** Only for safety PLC signals (SafetyRelated=Y mandatory)
- **Memory marker (%M):** Does NOT appear in this list — goes to RD02 DataDict
- **Don't leave blank:** Do NOT write `?` or `TODO`; move it to #UNKNOWNS

---

*Template v1.0.0 — RD01 IO List. If the spec changes, this file is updated too.*
