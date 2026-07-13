---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD10
generated_at: 2026-07-12T18:26:05+00:00
model: deepseek-chat
step: RD10 FB Specifications Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD10_FBSpec_draft.md

## Sheet 1: BlockList

| BlockName | BlockType | Version | Description | CalledFrom | InstanceDB | LinkedEquipment | TemplateBase | Notes | Status |
|-----------|-----------|---------|-------------|------------|------------|-----------------|---------------|-------|--------|
| FC_NotAus | FC | 1.0.0 | NOT-AUS / Sicherheit (NICHT AENDERN - Sicherheits-Logik) | OB1 | | MX-2 | Custom | Original: FC10 | DRAFT_UNVERIFIED |
| FC_Betriebsart | FC | 1.0.0 | Betriebsart AUTO / HAND | OB1 | | MX-2 | Custom | Original: FC20 | DRAFT_UNVERIFIED |
| FC_Schrittkette | FC | 1.0.0 | Schrittkette Mischzyklus (manuelle M-Bit-Kette, 1995er Stil) | OB1 | | MX-2 | Custom | Original: FC30 | DRAFT_UNVERIFIED |
| FC_RuehrerAnlauf | FC | 1.0.0 | Ruehrermotor Stern-Dreieck-Anlauf | OB1 | | MX-2 | Custom | Original: FC40 | DRAFT_UNVERIFIED |
| FC_Heizungsregelung | FC | 1.0.0 | Analog: Behaeltertemperatur + Heizungsregelung | OB1 | | MX-2 | Custom | Original: FC50 | DRAFT_UNVERIFIED |
| FC_Alarme | FC | 1.0.0 | Alarme / Meldungen (Alarmbits in DB30) | OB1 | | MX-2 | Custom | Original: FC60 | DRAFT_UNVERIFIED |
| FC_Foerderband | FC | 1.0.0 | Foerderband | OB1 | | MX-2 | Custom | Original: FC70 | DRAFT_UNVERIFIED |

## Sheet 2: ParamList

| BlockName | ParamName | Section | Type | DefaultValue | Description | LinkedTag | Notes |
|-----------|-----------|---------|------|--------------|-------------|-----------|-------|
| FC_NotAus | in_bNotAusNord | IN | BOOL | | NOT-AUS Nord (Oeffner) | E 1.0 | |
| FC_NotAus | in_bNotAusSued | IN | BOOL | | NOT-AUS Sued (Oeffner) | E 1.1 | |
| FC_NotAus | in_bWartungsBypass | IN | BOOL | | Wartungs-Bypass (GEFAEHRLICH!) | M 50.0 | |
| FC_NotAus | out_bHauptschuetz | OUT | BOOL | | Hauptschuetz (master contactor) | A 3.7 | |
| FC_NotAus | in_bLichtvorhang | IN | BOOL | | Lichtvorhang Beladung (Oeffner) | E 1.2 | |
| FC_NotAus | out_bFreigabeBeladung | OUT | BOOL | | Freigabe Beladung | M 60.0 | |
| FC_Betriebsart | in_bWahlschalter | IN | BOOL | | Wahlschalter AUTO/HAND | E 0.2 | |
| FC_Betriebsart | out_bAutoBetrieb | OUT | BOOL | | 1 = AUTO, 0 = HAND | M 10.7 | |
| FC_Schrittkette | in_bStartTaster | IN | BOOL | | Start-Taster | E 0.0 | |
| FC_Schrittkette | in_bAutoBetrieb | IN | BOOL | | AUTO-Betrieb | M 10.7 | |
| FC_Schrittkette | in_bNotAusKetteOK | IN | BOOL | | NOT-AUS-Kette OK | A 3.7 | |
| FC_Schrittkette | in_bFuellstandMAX | IN | BOOL | | Fuellstand MAX | E 2.1 | |
| FC_Schrittkette | in_bFuellstandMIN | IN | BOOL | | Fuellstand MIN | E 2.0 | |
| FC_Schrittkette | out_bSchritt10 | OUT | BOOL | | Schritt 10 aktiv | M 20.0 | |
| FC_Schrittkette | out_bSchritt20 | OUT | BOOL | | Schritt 20 aktiv | M 20.1 | |
| FC_Schrittkette | out_bSchritt30 | OUT | BOOL | | Schritt 30 aktiv | M 20.2 | |
| FC_Schrittkette | out_bEinlaufventil | OUT | BOOL | | Einlaufventil AUF | A 0.4 | |
| FC_Schrittkette | stat_tRuehrzeit | STAT | TIME | T#30S | Einschaltverzoegerung 30s | T 5 | |
| FC_RuehrerAnlauf | in_bSchritt20 | IN | BOOL | | Schritt 20 aktiv | M 20.1 | |
| FC_RuehrerAnlauf | in_bMotorschutzRuehrer | IN | BOOL | | Motorschutz Ruehrer OK (Oeffner) | E 0.4 | |
| FC_RuehrerAnlauf | out_bRuehrerAnforderung | OUT | BOOL | | Ruehrer-Anforderung | M 30.0 | |
| FC_RuehrerAnlauf | out_bNetzschuetz | OUT | BOOL | | Netzschuetz | A 0.3 | |
| FC_RuehrerAnlauf | out_bSternschuetz | OUT | BOOL | | Sternschuetz | A 0.1 | |
| FC_RuehrerAnlauf | out_bDreieckschuetz | OUT | BOOL | | Dreieckschuetz | A 0.2 | |
| FC_RuehrerAnlauf | stat_tSternzeit | STAT | TIME | T#6S | Sternzeit T1 = 6s | T 1 | |
| FC_Heizungsregelung | in_iRohwertTemperatur | IN | INT | | Rohwert 4-20mA -> 0..27648 | EW 64 | |
| FC_Heizungsregelung | in_bRuehrenAktiv | IN | BOOL | | nur waehrend Ruehren heizen | M 20.1 | |
| FC_Heizungsregelung | out_bHeizung | OUT | BOOL | | Heizung EIN | A 0.5 | |
| FC_Heizungsregelung | stat_iSollwertUnter | STAT | INT | 15500 | Sollwert ~60 C = Rohwert ~16000, Hysterese +/- 500 | | |
| FC_Heizungsregelung | stat_iSollwertUeber | STAT | INT | 16500 | Sollwert ~60 C = Rohwert ~16000, Hysterese +/- 500 | | |
| FC_Alarme | in_bNotAusNord | IN | BOOL | | NOT-AUS Nord (Oeffner) | E 1.0 | |
| FC_Alarme | in_bNotAusSued | IN | BOOL | | NOT-AUS Sued (Oeffner) | E 1.1 | |
| FC_Alarme | in_bMotorschutzRuehrer | IN | BOOL | | Motorschutz Ruehrer ausgeloest | E 0.4 | |
| FC_Alarme | out_bALM_NotAus | OUT | BOOL | | ALM_NotAus | DB30.DBX 0.0 | |
| FC_Alarme | out_bALM_MotorschutzRuehrer | OUT | BOOL | | ALM_MotorschutzRuehrer | DB30.DBX 0.1 | |
| FC_Alarme | out_bMeldeleuchteStoerung | OUT | BOOL | | Meldeleuchte Stoerung | A 0.6 | |
| FC_Foerderband | in_bFreigabeBeladung | IN | BOOL | | Freigabe Beladung (Lichtvorhang) | M 60.0 | |
| FC_Foerderband | in_bMotorschutzBand | IN | BOOL | | Motorschutz Band OK (Oeffner) | E 0.3 | |
| FC_Foerderband | in_bNotAusKetteOK | IN | BOOL | | NOT-AUS-Kette OK | A 3.7 | |
| FC_Foerderband | out_bBandSchuetz | OUT | BOOL | | Band-Schuetz | A 0.0 | |