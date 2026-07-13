---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD01
generated_at: 2026-07-12T18:24:25+00:00
model: deepseek-chat
step: RD01 Draft Consolidation
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

| Tag | Address | Type | Dir | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | Safety | SrcModule | OldTag | Notes | Status |
|-----|---------|------|-----|-----------|-------------|-------------|---------|----------|----------|--------|----------|--------|-------|--------|
| StartTaster | %E0.0 | DI | IN | | Start pushbutton | | | | | NO | FC30 | E 0.0 | | DRAFT_UNVERIFIED |
| StopTaster | %E0.1 | DI | IN | | Stop pushbutton | | | | | NO | | E 0.1 | Not used in code | DRAFT_UNVERIFIED |
| WahlschalterAutoHand | %E0.2 | DI | IN | | Mode selector switch AUTO/HAND | | | | | NO | FC20 | E 0.2 | | DRAFT_UNVERIFIED |
| MotorschutzBand | %E0.3 | DI | IN | M1 | Motor protection conveyor | NC | | | | NO | FC70 | E 0.3 | | DRAFT_UNVERIFIED |
| MotorschutzRuehrer | %E0.4 | DI | IN | M2 | Motor protection stirrer | NC | | | | NO | FC40 | E 0.4 | | DRAFT_UNVERIFIED |
| NotAusNord | %E1.0 | DI | IN | | Emergency stop north (NC) | NC | | | | YES | FC10, FC60 | E 1.0 | | DRAFT_UNVERIFIED |
| NotAusSued | %E1.1 | DI | IN | | Emergency stop south (NC) | NC | | | | YES | FC10, FC60 | E 1.1 | | DRAFT_UNVERIFIED |
| LichtvorhangBeladung | %E1.2 | DI | IN | | Light curtain loading (NC) | NC | | | | YES | FC10 | E 1.2 | | DRAFT_UNVERIFIED |
| FuellstandMin | %E2.0 | DI | IN | | Level minimum | | | | | NO | FC30 | E 2.0 | | DRAFT_UNVERIFIED |
| FuellstandMax | %E2.1 | DI | IN | | Level maximum | | | | | NO | FC30 | E 2.1 | | DRAFT_UNVERIFIED |
| Temperatur | %EW64 | AI | IN | | Temperature 4-20mA (vessel) | | °C | 0 | 100 | NO | FC50 | EW 64 | | DRAFT_UNVERIFIED |
| BandSchuetz | %A0.0 | DQ | OUT | M1 | Conveyor contactor | | | | | NO | FC70 | A 0.0 | | DRAFT_UNVERIFIED |
| RuehrerStern | %A0.1 | DQ | OUT | M2 | Stirrer star contactor | | | | | NO | FC40 | A 0.1 | | DRAFT_UNVERIFIED |
| RuehrerDreieck | %A0.2 | DQ | OUT | M2 | Stirrer delta contactor | | | | | NO | FC40 | A 0.2 | | DRAFT_UNVERIFIED |
| RuehrerNetz | %A0.3 | DQ | OUT | M2 | Stirrer line contactor | | | | | NO | FC40 | A 0.3 | | DRAFT_UNVERIFIED |
| Einlaufventil | %A0.4 | DQ | OUT | Y1 | Inlet valve | | | | | NO | FC30 | A 0.4 | | DRAFT_UNVERIFIED |
| Heizung | %A0.5 | DQ | OUT | | Heater | | | | | NO | FC50 | A 0.5 | | DRAFT_UNVERIFIED |
| MeldeleuchteStoerung | %A0.6 | DQ | OUT | | Fault indicator lamp | | | | | NO | FC60 | A 0.6 | | DRAFT_UNVERIFIED |
| Hauptschuetz | %A3.7 | DQ | OUT | | Main contactor (emergency stop chain) | | | | | YES | FC10 | A 3.7 | | DRAFT_UNVERIFIED |

## Conflicts
- No drawing analysis was provided, so no conflicts between drawing and code analysis exist.

## Review Required
- E0.1 (Stop-Taster) is declared but not used in any code block — verify if this is intentional or missing logic.
- Safety functions (E1.0, E1.1, E1.2, A3.7) are implemented on a standard CPU, not a safety PLC — review for safety compliance.
- Equipment assignment for conveyor (M1) and stirrer (M2) is inferred from description; verify against physical device tags.
- Heater (A0.5) has no associated equipment tag — confirm if it is a standalone device or part of a larger assembly.
- Analog input EW64 (Temperatur) range is assumed (0-100°C); verify actual sensor range and scaling.