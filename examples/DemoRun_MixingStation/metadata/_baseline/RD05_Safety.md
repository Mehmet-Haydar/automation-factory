---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD05
generated_at: 2026-07-12T18:25:34+00:00
model: deepseek-chat
step: RD05 Safety Functions Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD05_Safety_DRAFT_UNVERIFIED.md
> ⚠️ WARNING: this file was produced by AI.
> NOT USABLE without sign-off from a certified safety engineer.
> All SIL/PLr/Category fields BLANK — a human will fill them.

## Safety Functions Extraction

| FunctionID | FunctionName | TriggerCondition | SafeAction | ResponseTime_ms | ResetType | F_InputTag | F_OutputTag | F_DB | F_FB | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SF001 | NOT-AUS_Kette | E 1.0 (NOT-AUS Nord) = FALSE OR E 1.1 (NOT-AUS Sued) = FALSE (NC contact open) OR M 50.0 (Wartungs-Bypass) = TRUE | Drop Hauptschuetz (A 3.7) | | Manual | | | | | DRAFT_UNVERIFIED | SAFETY_ON_STANDARD_PLC; WARNING: Bypass M 50.0 bypasses safety function |
| SF002 | Lichtvorhang_Beladung | E 1.2 (Lichtvorhang) = FALSE (NC contact open) OR M 50.0 (Wartungs-Bypass) = TRUE | Set M 60.0 (Freigabe Beladung) = FALSE | | Manual | | | | | DRAFT_UNVERIFIED | SAFETY_ON_STANDARD_PLC; WARNING: Bypass M 50.0 bypasses safety function |
| SF003 | Band_Motor_Freigabe | M 60.0 (Freigabe Beladung) = FALSE OR E 0.3 (Motorschutz Band) = TRUE (NC contact open) OR A 3.7 (NOT-AUS-Kette) = FALSE | Drop Band-Schuetz (A 0.0) | | Auto | | | | | DRAFT_UNVERIFIED | SAFETY_ON_STANDARD_PLC; INTERLOCK_NOT_VERIFIED_AS_SAFETY |
| SF004 | Ruehrer_Motorschutz | E 0.4 (Motorschutz Ruehrer) = TRUE (NC contact open) | Set M 30.0 (Ruehrer-Anforderung) = FALSE; stop Ruehrer | | Auto | | | | | DRAFT_UNVERIFIED | SAFETY_ON_STANDARD_PLC; INTERLOCK_NOT_VERIFIED_AS_SAFETY |
