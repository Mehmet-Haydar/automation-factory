---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD03
generated_at: 2026-07-12T18:24:41+00:00
model: deepseek-chat
step: RD03 Flowchart Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

## Step Sequence
| StepID | StepName | EntryCondition | Actions | ExitCondition | NextStep | Status |
|--------|----------|----------------|---------|---------------|----------|--------|
| S001 | Behaelter fuellen | Start-Taster (E0.0) pressed AND AUTO mode (M10.7=1) AND Hauptschuetz (A3.7) active AND NOT in step 20 (M20.1) AND NOT in step 30 (M20.2) | Set step 10 active (M20.0) AND Open Einlaufventil (A0.4) | Fuellstand MAX (E2.1) reached | S002 | DRAFT_UNVERIFIED |
| S002 | Ruehren | Step 10 active (M20.0) AND Fuellstand MAX (E2.1) | Reset step 10 (M20.0) AND Set step 20 active (M20.1) AND Start timer T5 for 30 seconds AND Enable stirrer motor (M30.0) AND Enable heater (A0.5) when temperature below 15500 | Timer T5 elapsed (30s) | S003 | DRAFT_UNVERIFIED |
| S003 | Entleeren | Step 20 active (M20.1) AND Timer T5 elapsed | Reset step 20 (M20.1) AND Set step 30 active (M20.2) | Fuellstand MIN (E2.0) reached | (end) | DRAFT_UNVERIFIED |

## Modes
- **Automatic mode (AUTO)**: Selected when Wahlschalter (E0.2) is ON, setting M10.7=1. The step chain (FC30) only executes when M10.7=1. The mixing cycle runs automatically from filling through stirring to emptying.
- **Manual mode (HAND)**: Selected when Wahlschalter (E0.2) is OFF, setting M10.7=0. The step chain (FC30) is disabled. Individual components (conveyor belt, stirrer, heater) can be operated independently via manual control (not shown in code but implied by the mode selection).
- **Maintenance mode**: Activated by M50.0 (Wartungs-Bypass). This dangerous bypass overrides both emergency stop buttons (E1.0, E1.1) and the light curtain (E1.2), allowing operation during maintenance. This is a significant safety concern as it bypasses critical safety functions.

## Assumptions
- The stop button (E0.1) is declared but never used in the code; it is assumed to be wired in series with the start button or handled externally (e.g., in hardware or a higher-level safety circuit).
- The step chain (FC30) uses manual M-bit sequencing (M20.0, M20.1, M20.2) typical of 1990s PLC programming; no automatic reset or cycle counter is implemented.
- The temperature control (FC50) uses raw analog values (0-27648) with hysteresis thresholds of 15500 and 16500, assumed to correspond to approximately 60°C with ±500 hysteresis based on typical 4-20mA scaling.
- The star-delta starter (FC40) uses a fixed 6-second star time (T1) before switching to delta, with interlocking to prevent both contactors being on simultaneously.
- The conveyor belt (FC70) runs continuously when enabled by the light curtain (M60.0) and motor protection (E0.3) and Hauptschuetz (A3.7) are OK; no start/stop logic is implemented beyond these conditions.
- The alarm system (FC60) uses DB30.DBX bits for alarm storage; no acknowledgment or reset logic is present in the code.
- The Hauptschuetz (A3.7) is controlled by the emergency stop chain and must be active for any machine operation; it is assumed to be a master contactor that powers all downstream components.
- The light curtain (E1.2) is a normally-closed (Oeffner) input that enables loading (M60.0) when not interrupted; it can be bypassed in maintenance mode (M50.0).