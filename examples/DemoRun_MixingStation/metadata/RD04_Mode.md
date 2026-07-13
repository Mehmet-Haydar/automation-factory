---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD04
generated_at: 2026-07-12T18:25:29+00:00
model: deepseek-chat
step: RD04 Operating Modes Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD04_Mode_draft.md

## Operating Modes Extraction — Mischstation MX-2

Based on legacy code analysis, the following operating modes have been identified:

| ModeID | ModeName | Priority | PackMLState | Description | EntryCondition | ExitCondition | PermittedActions | RestrictedActions | HMI_Color | HMI_Text | DB_ModeWord | Notes | Status |
|--------|----------|----------|-------------|-------------|----------------|---------------|-----------------|-------------------|-----------|----------|-------------|-------|--------|
| M00 | EMERGENCY | 0 | Aborted | NOT-AUS / Emergency Stop — Sicherheitskette unterbrochen | NOT E 1.0 OR NOT E 1.1 (NOT-AUS Nord/Sued Oeffner) | E 1.0 AND E 1.1 AND Reset | None | All operations | #FF0000 | NOT-AUS | DB30.DBX 0.0 (ALM_NotAus) | Standard-CPU, kein F-CPU; Hauptschuetz A3.7 wird direkt abgeschaltet | DRAFT_UNVERIFIED |
| M01 | AUTO | 50 | Execute | Automatikbetrieb — Automatic mode, vollautomatischer Mischzyklus | E 0.2 = 1 (Wahlschalter AUTO) AND A 3.7 = 1 (NOT-AUS-Kette OK) | E 0.2 = 0 (Wahlschalter HAND) OR NOT A 3.7 | Start, Stop, Reset | Jog, Manual_Override, Maintenance_Bypass | #00C800 | AUTO | M 10.7 | Schrittkette FC30 aktiv; Heizung nur in Schritt 20 | DRAFT_UNVERIFIED |
| M02 | MANUAL | 50 | Stopped | Handbetrieb — Manual mode, Einzelfunktionen ueber Taster | E 0.2 = 0 (Wahlschalter HAND) AND A 3.7 = 1 | E 0.2 = 1 (Wahlschalter AUTO) OR NOT A 3.7 | Jog, Manual_Valve, Manual_Heating | Auto_Sequence, Production_Cycle | #FFA500 | HAND | M 10.7 (invertiert) | Keine Schrittkette aktiv; Einzelfunktionen moeglich | DRAFT_UNVERIFIED |
| M03 | SETUP | 50 | Idle | Service/Setup-Modus — Wartungsmodus mit Bypass | M 50.0 = 1 (Wartungs-Bypass) AND A 3.7 = 1 | M 50.0 = 0 | Jog, Bypass_LightCurtain, Manual_Operations | Auto_Sequence, Safety_Functions | #FFFF00 | SETUP | M 50.0 | GEFAeHRLICH: Lichtvorhang ueberbrueckt (M50.0 bypass) | DRAFT_UNVERIFIED |
| M04 | MAINTENANCE | 50 | Stopped | Wartung — Maintenance mode | | | | | #0080FF | WARTUNG | | Nicht explizit im Code; moeglicherweise ueber M50.0 | DRAFT_UNVERIFIED |
| M05 | CLEANING | 50 | Idle | Reinigung — Cleaning mode | | | | | #0080FF | REINIGUNG | | Nicht im Code identifiziert | DRAFT_UNVERIFIED |
| M06 | LOCKOUT | 50 | Stopped | LOTO — Lockout/Tagout | | | | | #0080FF | LOTO | | Nicht im Code identifiziert | DRAFT_UNVERIFIED |

## Mode Detection Logic Summary

- **Mode selection**: E 0.2 (Wahlschalter AUTO/HAND) → M 10.7
  - M 10.7 = 1 → AUTO mode (M01)
  - M 10.7 = 0 → MANUAL mode (M02)
- **Emergency**: NOT E 1.0 OR NOT E 1.1 → DB30.DBX 0.0 (ALM_NotAus)
- **Setup/Maintenance**: M 50.0 (Wartungs-Bypass) → M03
- **Safety note**: No F-CPU present; safety logic on standard CPU

## Uncertainties / #UNKNOWNS

- M04, M05, M06: Not explicitly implemented in legacy code
- Exact HMI tag names for mode display not documented
- Mode transition logic for M03→M01/M02 not fully defined
- Physical addresses for HMI communication unknown