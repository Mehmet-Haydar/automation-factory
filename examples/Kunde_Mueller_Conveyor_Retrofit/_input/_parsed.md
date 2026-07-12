---
title: Parsed Project Summary - Siemens S7-300/400 Classic (STL Platform Parser)
version: 1.0.0
last_validated: 2026-05
applies_to: [retrofit]
platform: S7-300
platform_version: STEP 7 V5.5 Classic
parser: PROMPT_ANALYZE_S7_300_STL.md
project_id: KMG-2026-001
data_classification: CONFIDENTIAL
source_quality: AWL_PARTIAL_SNIPPET
output_language: DE
---

# _parsed.md — S7-300/400 Classic Project Analysis

> Von AI erzeugt (`PROMPT_ANALYZE_S7_300_STL.md`) — Gate-2-Plattformparser.  
> **Umfang:** Nur `_input/old_code_snippet.awl` (FC10 + FC30, abgeschnitten). Kein S7P/ZAP, keine HW Config, keine Symboltabelle. Leere Abschnitte: `(leer)`. CPU/STEP-7-Angaben aus Projekt-Brief (README/MAESTRO), im Code **nicht** verifiziert.  
> **Datenklasse:** CONFIDENTIAL — nicht in öffentliche AI-Dienste hochladen.

## 0. Meta

| Feld | Wert |
|------|------|
| **Project name** | Förderlinie_Müller_1995 (Kunde_Mueller_Conveyor_Retrofit) |
| **Customer** | Kunde Müller GmbH |
| **Project ID** | KMG-2026-001 |
| **STEP 7 version** | V5.5 Classic (Brief — in Gegendatei nicht verifiziert) |
| **CPU type** | CPU 315-2 DP (Brief — keine HW Config) |
| **Firmware** | UNKNOWN |
| **Safety** | disabled — kein F-CPU; Standard-SPS-E-Stop über Q 3.7 |
| **Analyzed at** | 2026-05-16 |
| **Datenklassifikation** | CONFIDENTIAL |
| **Analysierte Eingaben** | `_input/old_code_snippet.awl` (FC10, FC30) |
| **Fehlende Eingaben** | S7P/ZAP, `.sdf`/Symbol-Export, HW Config, UDT/DB-Listing, OB-Quellen, GRAPH 7 (`.gr7`) |

## 1. Hardware Configuration

| Rack | Slot | Module | Order Number | Address Range | Notes |
|------|------|--------|--------------|---------------|-------|
| — | — | — | — | — | (leer) — kein HW-Config-Print / `.cfg` |

**Brief (unverifiziert):** CPU 315-2 DP; I/O-Modul-Adressierung aus Snippet nicht ableitbar (I 0.x vs. I 100.x deuten auf getrennte Eingangsbereiche).

## 2. Network

| Interface | Type (MPI/PROFIBUS/PN) | Address | Devices | Notes |
|-----------|-------------------------|---------|---------|-------|
| — | — | — | — | (leer) — keine Netzwerkkonfiguration |

**Code-Hinweis:** FC10-Kopf *2012-11 (Modbus entfernt)* — früher Modbus; aktuelles Feldbus UNKNOWN.

## 3. Symbol Table Summary

| Kennzahl | Wert |
|----------|------|
| **Total symbols (Datei)** | 0 — keine `.sdf`/Symbol-Export-Datei |
| **I / Q / M / T / C (tabellarisch)** | 0 / 0 / 0 / 0 / 0 |
| **DB / FB / FC ref (tabellarisch)** | 0 / 0 / 0 |
| **Symbollose Absolute im Snippet** | **19** eindeutige Operanden; **29** Operandenreferenzen in AWL-Zeilen |
| **Symbollose im Gesamtprojekt (Brief)** | ~47 (Demo-README/RD01 — **nicht** aus diesem Snippet gezählt) |

**Im Snippet verwendete Absolute (keine symbolischen Operanden):**

| Adresse | Kontext (Originalkommentar / Verwendung) |
|---------|------------------------------------------|
| I 100.0 | NOT-AUS Nord (NC) |
| I 100.1 | NOT-AUS Süd (NC) |
| I 100.2 | Lichtvorhang Beladung (NC) |
| I 100.3 | Lichtvorhang Entladung |
| I 0.0 | Start button |
| I 0.5 | Photocell |
| Q 3.7 | Hauptschütz (master contactor) |
| Q 0.0 | Motor 1 enable |
| Q 0.1 | Motor 2 enable |
| M 50.0 | Wartungs-Bypass |
| M 50.7 | Internal E-Stop flag |
| MB 50 | Bypass-Bits (Byte-Init, NW1) |
| M 10.0 | Schritt 10 |
| M 10.1 | Schritt 20 |
| M 10.2 | Schritt 30 |
| T 1 | Timer (Kommentar: 3 s — Preset nicht in AWL) |
| DB10.DBX 0.1 | AUTO mode |
| DB10.DBX 0.2 | Wartungsmodus aktiv |
| DB30.DBX 0.0 | ALM_EStop |

**Ziel-Mapping (GLOBAL_NAMING_STANDARD, nur Snippet-Adressen — RD01-Abgleich):**

| Classic-Adresse | Ziel-Tag (Beispiel) | Regex-konform |
|-----------------|---------------------|---------------|
| I 100.0 | `F_I_EStop_North` → RD01 | Teilweise (Safety-Präfix abweichend) |
| I 100.1 | `F_I_EStop_South` | wie oben |
| I 100.2 | `F_I_LC_Loading` | wie oben |
| I 100.3 | `F_I_LC_Unloading` | wie oben |
| I 0.0 | `MOT_CV01_001_START` | `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$` |
| I 0.5 | `PC_LOAD_001` | ja |
| Q 3.7 | `MASTER_CONTACTOR` | ja |
| Q 0.0 / Q 0.1 | `MOT_CV01_001_OUT` / `MOT_CV01_002_OUT` | ja |

## 4. UDT Inventory

| Name | Members | Used In |
|------|---------|---------|
| — | — | (leer) — kein UDT-Dump |

## 5. DB Inventory

| Name | Type (Instance/Global) | UDT/Type | Optimized | Description |
|------|------------------------|----------|-----------|-------------|
| DB10 | Global (Abgeleitet) | UNKNOWN | Non-optimized (Classic-Default) | DBX 0.1 AUTO; DBX 0.2 Wartungsmodus |
| DB30 | Global (Abgeleitet) | UNKNOWN | Non-optimized | DBX 0.0 ALM_EStop |

**Hinweis:** DB1 (System) und Instance-DBs außerhalb des Snippets — UNKNOWN.

## 6. OB Inventory

| Number | Name | Trigger | Description |
|--------|------|---------|-------------|
| OB1 | UNKNOWN | Main cycle | Hauptzyklus — keine Quelle (S7-300 Standard) |
| OB10..OB17 | — | Time-of-day | (leer) |
| OB20..OB23 | — | Time-delay | (leer) |
| OB30..OB38 | — | Cyclic | (leer) |
| OB40..OB47 | — | Hardware interrupt | (leer) |
| OB80..OB87 | — | Error | (leer) |
| OB100..OB102 | — | Startup | (leer) |
| OB121/122 | — | Programming/access error | (leer) |

## 7. FB Inventory

| Name | Interface (IN/OUT/INOUT/STAT) | Called From | Language (AWL/SCL/GR7) | Description |
|------|------------------------------|-------------|--------------------------|-------------|
| — | — | — | — | (leer) — im Snippet keine FB |

## 8. FC Inventory

| Name | Interface | Called From | Language | Description |
|------|-----------|-------------|----------|-------------|
| FC10 | VOID | UNKNOWN | AWL | E-Stop Logik (Standard-SPS, kein F-CPU vorhanden) |
| FC30 | VOID | UNKNOWN | AWL | Sequence Control — Pseudo State Machine (M-Bit-Schritte) |

## 9. Safety Blocks (F-blocks, if F-CPU)

**(Kein F-CPU)** — Snippet: *kein F-CPU vorhanden*. Keine F_FB / F_FC / F_DB.

| Name | Type | F-DB | Description |
|------|------|------|-------------|
| — | — | — | (leer) |

**Sicherheitsrelevante Standard-PLC-Logik (kein F-Block, für RD05):**

| Block | NW | Kurzbeschreibung |
|-------|-----|------------------|
| FC10 | NW5 | `A I 100.0` ∧ `A I 100.1` ∧ `AN M 50.0` → `= Q 3.7` Hauptschütz |
| FC10 | NW6 | Gleiche Eingänge → `= M 50.7` (internes E-Stop-Flag) |
| FC10 | NW8 | `A I 100.2` ∧ `AN DB10.DBX 0.2` → `= Q 0.0` (Bypass Wartungsmodus) |
| FC10 | NW9 | `A I 100.3` → `= Q 0.1` |
| FC10 | NW12 | E-Stop-Alarm → `DB30.DBX 0.0` |

## 10. Call Tree (özet)

```
UNKNOWN (OB1 und vollständiger Aufrufbaum fehlen)

Aus Snippet erkennbar:
├── FC10 "E-Stop Logik"
│   ├── NW1:  L B#16#0 → T MB 50
│   ├── NW5:  NOT-AUS → Q 3.7
│   ├── NW6:  NOT-AUS → M 50.7
│   ├── NW8:  Lichtvorhang Beladung → Q 0.0
│   ├── NW9:  Lichtvorhang Entladung → Q 0.1
│   └── NW12: ALM_EStop → DB30.DBX 0.0
└── FC30 "Sequence Control"
    ├── Schritt 10:  I 0.0 ∧ DB10.DBX 0.1 ∧ ¬M 10.1 ∧ ¬M 10.2 → S M 10.0
    ├── 10→20:       M 10.0 ∧ T 1 → R M 10.0, S M 10.1
    ├── 20→30:       M 10.1 ∧ I 0.5 → R M 10.1, S M 10.2
    └── ... (abgeschnitten — M 10.3..M 10.7 fehlen)

Interrupt-OB-Zweige: (leer)
```

## 11. Comments / Lessons from Original Code

- `// Programmierer: A. Schmidt, 1995-08`
- `// Letzte Änderung: 2012-11 (Modbus entfernt)`
- `// NICHT ÄNDERN - Sicherheits-Logik`
- `TITLE = E-Stop Logik (Standard-SPS, kein F-CPU vorhanden)`
- `// E-Stop ist über Q3.7 verkabelt - kein F-PLC vorhanden`
- `// Wartungs-Bypass (TEHLIKELI!)` — M 50.0 (gemischte Sprache im Kommentar)
- `// Lichtvorhang Zone Beladung - Bypass im Wartungsmodus`
- `// Aynı lojik tekrar (yedeklilik?)` — NW6 vs. NW5 (Türkisch — nicht übersetzen)
- `TITLE = Sequence Control - Pseudo State Machine`
- `// ... (devamı — sequence devam eder M10.0..M10.7)` — Datei abgeschnitten
- Datei-Fußnote: Demo-Projekt; Gesamtliste ~47 Absolute (Projekt-Brief — **nicht** in diesem Snippet gezählt)

## 12. Unknowns / TODO for Human Review

- Vollständiges Projekt fehlt: S7P/ZAP, HW Config, Symboltabelle (`.sdf`), OB1, FB/GRAPH7, DB-Dumps.
- CPU / Firmware / Rack-Slot: ohne HW Config nicht verifizierbar.
- OB1 → Aufrufreihenfolge FC10/FC30: UNKNOWN.
- DB10 / DB30: Symbolnamen, Wortlänge, vollständige Bitkarte: UNKNOWN.
- T 1: Preset/Zeitbasis (Kommentar „3 s“) — nicht in AWL.
- FC30: Schritte M 10.3..M 10.7 und Folge-Netzwerke fehlen.
- FC10 NW8: Lichtvorhang-Bypass bei Wartungsmodus (`AN DB10.DBX 0.2`) — Safety-Risiko (RD05).
- FC10 NW5/NW6: Doppelte NOT-AUS-Logik Q 3.7 vs. M 50.7 — Redundanz oder Redundanzfehler?
- I 100.x vs. I 0.x: HW-Zuordnung / IO-Liste erforderlich.
- FB / Multiinstance / GRAPH7: keine Gegendatei — RD03 unvollständig.
- Snippet: 100 % symbollose Operanden; Abgleich mit vollständiger Symboltabelle nach Lieferung der `.sdf`.

---

# UNKNOWNS

Zusammenfassung aller offenen Punkte (Gate 3 / menschliche Prüfung):

| ID | Kategorie | Beschreibung | Priorität |
|----|-----------|--------------|-----------|
| UNK-001 | Gegendatei | Kein S7P/ZAP, keine OB-Quellen | Hoch |
| UNK-002 | HW | Rack/Slot/Order-Nr., I/O-Adressbereiche | Hoch |
| UNK-003 | Netzwerk | MPI/PROFIBUS/PN nach Modbus-Entfernung | Mittel |
| UNK-004 | Aufrufbaum | OB1 ruft FC10/FC30? Reihenfolge? | Hoch |
| UNK-005 | DB | DB10/DB30 Struktur und Benennung in STEP 7 | Mittel |
| UNK-006 | Timer | T 1 Preset, Zeitbasis, Zuordnung zu Schritt 10→20 | Mittel |
| UNK-007 | Ablauf | FC30 M 10.3..M 10.7 und Rest-Sequenz | Hoch |
| UNK-008 | Safety | Wartungs-Bypass M 50.0 + DB10.DBX 0.2 — SIL/PL ungeklärt | Kritisch |
| UNK-009 | Safety | E-Stop über Standard-Q 3.7 ohne F-CPU (FND001) | Kritisch |
| UNK-010 | Symbolik | 19 (Snippet) vs. ~47 (Projekt-Brief) — vollständige IO-Liste fehlt | Hoch |
| UNK-011 | Firmware | CPU-Firmware-Stand | Niedrig |
| UNK-012 | GRAPH7 | Keine `.gr7` — SFC/Sequencer evtl. nur M-Bit-FC30 | Mittel |

---

## Validierung (Parser-Checkliste)

- [x] Frontmatter vollständig (Projekt, STEP 7, CPU, Safety)
- [x] 12 Abschnitte vorhanden
- [ ] Abschnitt 1: CPU + mindestens 1 Modul — **nur Brief, keine HW Config**
- [x] Abschnitt 3: Symbollose Anzahl im Snippet dokumentiert
- [x] Abschnitt 5: Optimized/Non-optimized Spalte (Classic = Non-optimized)
- [x] Abschnitt 7 FB: (leer) korrekt markiert
- [x] Abschnitt 8 FC: Language = AWL
- [x] Abschnitt 9: „Kein F-CPU“ dokumentiert
- [x] Abschnitt 10: Call Tree mit FC-Zweigen; Interrupt (leer)
- [x] Abschnitt 12 + # UNKNOWNS: symbollose Adressen und offene Punkte

---

*v1.0.0 — S7-300 Classic Platform Parser. Eingabe: partielles AWL-Snippet. Abschnitt 12 und # UNKNOWNS vor Gate 3 verbindlich prüfen.*
