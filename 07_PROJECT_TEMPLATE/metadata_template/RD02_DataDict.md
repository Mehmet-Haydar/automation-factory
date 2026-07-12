# RD02_DataDict — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_02_DATADICT.md`. Schema: `rd02_datadict.schema.json`.

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

- Total variables: __
- Scope: GlobalDB __ | InstanceDB __ | UDT __ | MemoryMarker __ | TempVar __
- UDT count: __
- With Retain: __

---

## Variables

| VarName | Scope | ParentBlock | Type | Offset | InitValue | Retain | Description | LinkedTag | OldVar | Notes | Status |
|---------|-------|-------------|------|--------|-----------|--------|-------------|-----------|--------|-------|--------|
| stat_bMotorRunning | InstanceDB | FB_Motor_Pump01 | BOOL | 0.0 | FALSE | N | Motor running (orig: Motor läuft) | | M_Pumpe_Lauft | | Active |
| stat_iStepCounter | InstanceDB | FB_Sequence_Main | INT | 2 | 0 | N | Active sequence step | | MW100 | | Active |
| iActiveRecipe | GlobalDB | DB_Recipe | INT | 0 | 0 | Y | Active recipe ID | | DB10.DBW0 | Recipe must persist | Active |
| rSetSpeed | UDT | UDT_Motor | REAL | OPT | 0.0 | N | Set speed (RPM) | | | | Active |
| diProductCount | GlobalDB | DB_System | DINT | 4 | 0 | Y | Total products produced | | MD200 | Counter retain Y | Active |

---

## #UNKNOWNS

| Old VarName | ParentBlock | Reason |
|-------------|-------------|--------|
| | | |

---

## Fill-in Notes

- **VarName prefix:** `in_/out_/inout_/stat_/temp_` (FB variables)
- **Type prefix abbreviations:** b=BOOL, w=WORD, i=INT, di=DINT, r=REAL, t=TIME, s=STRING, u=UDT
- **Scope=MemoryMarker or TempVar → Retain=N/A** (mandatory)
- **Optimized DB → Offset=OPT** (S7-1500/1200 default)
- **UDT members:** Each member on a SEPARATE row (don't write the UDT on one row)
- **LinkedTag:** In the "signal copy" pattern, the new RD01 tag name

---

*Template v1.0.0 — RD02 Data Dictionary.*
