# RD05_Safety_DRAFT_UNVERIFIED — Per-Project Template

> ⚠️ **CAUTION:** This file cannot be used without **certified safety engineer approval**. The AI **does not estimate SIL/PLr/Category** — these fields are left blank. Spec: `MDSCHEMA_RAWDATA_05_SAFETY.md`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <AI Engine / Engineer Name>
filled_at: <YYYY-MM-DD>
status: DRAFT_UNVERIFIED        # does not change without SAFETY_ENGINEER_REVIEW
safety_engineer: <to be assigned>
risk_assessment_doc: <document reference>
```

---

## Summary

- Detected safety functions: __
- F-PLC present: <Y/N>
- F-FB count: __
- Safety logic on a standard PLC (CRITICAL): __

---

## Safety Functions

| FunctionID | FunctionName | SIL_Level | Category | TriggerCondition | SafeAction | ResponseTime_ms | ResetType | F_InputTag | F_OutputTag | F_DB | F_FB | ProofTestInterval_h | Verified_By | Notes | Status |
|------------|--------------|-----------|----------|------------------|------------|------------------|-----------|------------|-------------|------|------|---------------------|-------------|-------|--------|
| SF001 | EStop_North | | | E_Stop_N_Btn = FALSE (NC) | All motors STOP, F_Out_Contactor = FALSE | | Manual | F_I_EStop_N | F_Q_Contactor | F_DB_EStop | F_FB_EStop1 | | | NOT-AUS Bereich Nord | DRAFT_UNVERIFIED |
| SF002 | LightCurtain_Loading | | | F_I_LC_Loading.Detected = TRUE | Loading robot STOP | | Auto | F_I_LC_Loading | F_Q_Robot_Stop | F_DB_LC | F_FB_LCFilter | | | Schutzfeld Beladestation | DRAFT_UNVERIFIED |

---

## ⚠️ Questions for the Safety Engineer

| FunctionID | Question |
|------------|----------|
| SF001 | What is the SIL level? What is the category? Is there a risk assessment document? |
| SF002 | Is the light curtain MTTFd value known? Has the diagnostic coverage (DC) been assessed? |

---

## SAFETY_ON_STANDARD_PLC Detections (CRITICAL)

> Safety logic detected on a standard PLC → CRITICAL finding, must be carried over to RD14.

| Block | Description | Risk |
|-------|-------------|------|
| | | |

---

## #UNKNOWNS

| Old symbol | Reason |
|------------|--------|
| | |

---

## Fill-in Notes

- **FORBIDDEN:** The AI does not fill in the SIL_Level, Category, ProofTestInterval_h fields
- **FORBIDDEN:** The AI cannot write any value other than DRAFT_UNVERIFIED in the Status field
- **FORBIDDEN:** Suggestions like "this function is SIL2" — it has no authority to assess
- **MANDATORY:** The Verified_By field is filled with the certified engineer's signature, then Status=APPROVED
- **MANDATORY:** If safety logic is detected on a standard PLC, it is listed in a separate section
- **Standards:** IEC 62061, ISO 13849-1, IEC 61508, IEC 61511

---

*Template v1.0.0 — RD05 Safety. This file is NOT a safety document, it is a draft. Certified engineer approval is required.*
