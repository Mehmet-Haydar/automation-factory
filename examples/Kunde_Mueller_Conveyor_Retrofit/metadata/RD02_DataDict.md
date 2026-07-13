---
title: RD02 — Data Dictionary
project: Kunde_Mueller_Conveyor_Retrofit
project_id: KMG-2026-001
generated: 2026-05-16
source: _input/_parsed.md
filter: Status=Active
output_language: DE
data_classification: CONFIDENTIAL
status: DRAFT
schema: RD02
last_validated: 2026-05
---

# RD02_DataDict — Kunde Müller Conveyor Retrofit

> Automatisch aus `_input/_parsed.md` erzeugt (`PROMPT_EXTRACT_DATADICT_FROM_CODE.md`). Gate 3 — menschliche Prüfung ausstehend.  
> **Umfang:** Nur aus AWL-Snippet (FC10, FC30) ableitbare **interne** Variablen. Keine physischen I/O (→ RD01). Kein vollständiges S7P/DB-Dump.

## Frontmatter

```yaml
project_id: KMG-2026-001
project_name: Kunde_Mueller_Conveyor_Retrofit
customer: Kunde Müller GmbH
filled_by: AI Engine (topic extractor)
filled_at: 2026-05-16
output_language: DE
status: DRAFT
source_quality: AWL_PARTIAL_SNIPPET
```

## 1. Summary

| Kennzahl | Wert |
|----------|------|
| **Total variables (snippet)** | 8 |
| **GlobalDB** | 3 |
| **InstanceDB** | 0 |
| **UDT** | 0 |
| **MemoryMarker** | 5 |
| **TempVar** | 0 |
| **Retain (Y)** | 0 (im Snippet nicht belegt) |
| **Retain unbekannt** | 3 (GlobalDB — Retain leer) |

**Hinweis:** Demo-RD01 nennt ~47 IO-Signale; RD02 listet nur **interne** Speicher aus dem Parser-Snippet. Vollständige DB-Struktur (DB10/DB30 Restbytes, Instance-DBs, Rezept-Zähler) fehlt in `_parsed.md` → #UNKNOWNS.

## 2. Variables

| VarName | Scope | ParentBlock | Type | Offset | InitValue | Retain | Description | LinkedTag | OldVar | Notes | Status |
|---------|-------|-------------|------|--------|-----------|--------|-------------|-----------|--------|-------|--------|
| bAutoMode | GlobalDB | DB10 | BOOL | 0.1 | DEFAULT | | Automatikbetrieb aktiv (orig: AUTO mode) | | DB10.DBX0.1 | FC30 Schritt 10; Ziel-DB: DB_MODE_STATE (Modernisierung) | Active |
| bMaintModeActive | GlobalDB | DB10 | BOOL | 0.2 | DEFAULT | | Wartungsmodus aktiv (orig: Wartungsmodus aktiv) | | DB10.DBX0.2 | FC10 NW8 Bypass Lichtvorhang; Safety-Review RD05 | Active |
| bAlmEStop | GlobalDB | DB30 | BOOL | 0.0 | DEFAULT | | Not-Aus-Alarm aktiv (orig: ALM_EStop) | | DB30.DBX0.0 | FC10 NW12; Ziel-DB: DB_ALARM | Active |
| bMaintBypass | MemoryMarker | FC10 | BOOL | | FALSE | N/A | Wartungs-Bypass aktiv (orig: Wartungs-Bypass) | | M50.0 | FC10 NW5; TEHLIKELI — Gate 3 Safety | Active |
| bInternalEStop | MemoryMarker | FC10 | BOOL | | FALSE | N/A | Internes Not-Aus-Flag (orig: Internal E-Stop flag) | | M50.7 | FC10 NW6; parallel zu Q3.7 — Redundanz prüfen | Active |
| bSeqStep010 | MemoryMarker | FC30 | BOOL | | FALSE | N/A | Ablaufschritt 10 aktiv (orig: Schritt 10) | MOT_CV01_001_START | M10.0 | FC30; Start + AUTO + Timer T1 | Active |
| bSeqStep020 | MemoryMarker | FC30 | BOOL | | FALSE | N/A | Ablaufschritt 20 aktiv (orig: Schritt 20) | | M10.1 | FC30; Übergang 10→20 via T1 | Active |
| bSeqStep030 | MemoryMarker | FC30 | BOOL | | FALSE | N/A | Ablaufschritt 30 aktiv (orig: Schritt 30) | PC_LOAD_001 | M10.2 | FC30; Übergang 20→30 via I0.5 | Active |

### 2.1 Scope-Notizen

- **GlobalDB:** Classic S7-300, Non-optimized (Offset byte.bit). Nur im Snippet referenzierte Bits.
- **MemoryMarker:** M-Bereich als Pseudo-State-Machine (FC30) und Safety-Hilfsbits (FC10). `ParentBlock` = logischer Quell-FC.
- **InstanceDB / UDT:** In `_parsed.md` Abschnitt 4/5/7 leer — keine FB-Instanzen im Snippet.

### 2.2 LinkedTag-Logik

| VarName | LinkedTag | Begründung |
|---------|-----------|------------|
| bSeqStep010 | MOT_CV01_001_START | Schritt-10-Startbedingung nutzt I0.0 (RD01) — Prozesskopplung, keine Speicher-Spiegelung |
| bSeqStep030 | PC_LOAD_001 | Schritt-20→30 nutzt I0.5 (Lichtschranke) |
| übrige | | Kein 1:1 IO-Spiegel im Snippet |

## 3. DB-Übersicht (aus Parser)

| ParentBlock | Typ | Optimized | Bekannte Bits | Unbekannt |
|-------------|-----|-----------|---------------|-----------|
| DB10 | Global | Non-optimized | 0.1, 0.2 | 0.0, 0.3..7, Wörter/Rest |
| DB30 | Global | Non-optimized | 0.0 | 0.1..7, Wörter/Rest |

## 4. Validierung (Extractor-Checkliste)

- [x] 12 Pflichtspalten in fester Reihenfolge
- [x] VarName, Scope, ParentBlock, Type, Description, Status je Zeile
- [x] MemoryMarker: Retain = N/A
- [x] Keine physischen I/O-Zeilen (nur DB + M)
- [x] UDT: keine (leer dokumentiert)
- [x] OldVar: Absolute/Adresse aus Originalcode
- [x] #UNKNOWNS vorhanden
- [ ] Vollständigkeit: **Snippet-begrenzt** — kein vollständiges Projekt

---

## #UNKNOWNS

| Old VarName / Address | ParentBlock | Reason |
|------------------------|-------------|-------|
| DB10.DBX0.0 | DB10 | Im Snippet nicht referenziert; vollständige Bitkarte fehlt (UNK-005) |
| DB10 (Rest) | DB10 | Wortlänge, weitere Modi/Rezept-Felder — nur Demo-RD02-Entwurf (~32 Vars) spekulativ |
| DB30 (Rest) | DB30 | Nur ALM_EStop bekannt; weitere Alarmbits unbekannt |
| M10.3..M10.7 | FC30 | FC30 abgeschnitten — Schritte 40..70 fehlen (UNK-007) |
| MB50 | FC10 | Byte-Init NW1 (`L B#16#0` → `T MB50`); Einzelbits M50.0/M50.7 erfasst, Rest ungenutzt? |
| T1 | FC30 | Timer-Instanz, Preset „3 s“ nur im Kommentar — kein VAR_TEMP/DB-Feld (UNK-006) |
| Instance-DBs | — | Keine FB im Snippet → keine STAT/IN/OUT (UNK-012) |
| UDT | — | `_parsed.md` Abschnitt 4 leer — Modernisierung UDT empfohlen |
| Retain DB10/DB30 | DB10, DB30 | STEP-7-Retain-Attribut nicht in Gegendatei — Retain-Spalte leer gelassen |
| MW100..MW150 | (M-area) | **Nicht** in `_parsed.md` — alter RD02-Platzhalter; nicht extrahiert |

---

## 5. Kritische Querverweise

| Thema | RD | Hinweis |
|-------|-----|---------|
| Wartungs-Bypass + Lichtvorhang | RD05 | `bMaintBypass`, `bMaintModeActive` |
| Pseudo-State-Machine | RD03 | `bSeqStep010`..`030`, fehlende M10.3..7 |
| IO vs. intern | RD01 | I/Q nicht in RD02; LinkedTag nur Prozessbezug |
| Modernisierung | RD14 | M-Bit-Sequencer → FB/GRAPH; DB10→`DB_MODE_STATE` |

---

*v1.0.0 — RD02 aus partiellem `_parsed.md`. Gate 3: Retain, DB-Vollständigkeit und M10.3..7 nach Lieferung S7P/Symbol-Export prüfen.*
