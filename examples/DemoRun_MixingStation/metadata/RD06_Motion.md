---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD06
generated_at: 2026-07-12T18:25:38+00:00
model: deepseek-chat
step: RD06 Motion / Drives Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD06_Motion_draft.md

| AxisID | AxisName | DriveType | DriveModel | Motor_Tag | Feedback_Tag | MaxVelocity | MaxAcceleration | MaxDeceleration | EngUnit | TorqueLimit_pct | HomeMethod | HomePosition | SoftLimit_Neg | SoftLimit_Pos | DriveDB | PLCopenFBs | Notes | Status |
|--------|----------|-----------|------------|-----------|--------------|-------------|-----------------|-----------------|---------|-----------------|------------|--------------|---------------|---------------|---------|------------|-------|--------|
| AX001 | BandMotor | VFD_Analog | #UNKNOWNS | A 0.0 | E 0.3 | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | Conveyor belt motor; controlled via contactor (A 0.0); no VFD FB in code; motor protection via E 0.3 | DRAFT_UNVERIFIED |
| AX002 | RuehrerMotor | Other | #UNKNOWNS | A 0.1, A 0.2, A 0.3 | E 0.4 | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | Star-delta starter; three contactors (star A 0.1, delta A 0.2, line A 0.3); motor protection via E 0.4; no VFD/servo | DRAFT_UNVERIFIED |
| AX003 | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | #UNKNOWNS | No additional motion axes identified in legacy code | DRAFT_UNVERIFIED |
