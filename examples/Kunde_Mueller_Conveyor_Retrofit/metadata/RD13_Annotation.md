---
title: RD13_Annotation — Kunde Müller (AI satır anotasyonu)
last_validated: 2026-05
status: ACTIVE
---

# RD13_Annotation — Kunde Müller (AI satır anotasyonu)

```yaml
status: DRAFT (50%)
plc_platform: S7_300
plc_language: STL
```

## Özet
- AI tarafından 47 kritik blok/network anote edildi
- WarningFlag: 12× Y_HARDCODED_ADDR, 8× Y_UNDOCUMENTED, **4× Y_SAFETY_CONCERN**, 2× Y_DEAD_CODE
- ConfidenceLevel: 30 HIGH, 14 MEDIUM, 3 HUMAN_REQUIRED

## Anotasyonlar (örnek 3 satır — gerçek 47)

| AnnotationID | BlockName | LineRef | OriginalCode (özet) | FunctionCategory | Explanation_TR | WarningFlag | ConfidenceLevel | Status |
|--------------|-----------|---------|---------------------|-------------------|----------------|-------------|------------------|--------|
| ANN0001 | OB1 | L001-L015 | `A I 0.0\nA I 0.1\n=  Q 0.0` | LOGIC_COMBINATIONAL | I0.0 (Start) ve I0.1 (Stop NC) AND'i ile Q0.0 (motor) sürülüyor. Klasik 90'lar tarzı mutlak adres lojik. | Y_HARDCODED_ADDR | HIGH | AI_COMPLETE |
| ANN0042 | FC10 | L080-L085 | `A I 100.0\nA I 100.1\nAN M 50.0\n= Q 3.7` | SAFETY_LOGIC | **KRITIK:** E-Stop (I100.0, I100.1) ve "Wartungs-Bypass" (M50.0) ile master kontaktör (Q3.7) sürülüyor. Bu standart PLC üzerinde safety lojik — F-PLC olmadan IEC 62061 uyumsuz. | **Y_SAFETY_CONCERN** | **MEDIUM** (güvenliğe HIGH güven verilmez) | AI_COMPLETE |
| ANN0089 | FB30 | L045-L050 | `L 100\nT MD 200\nL MD 200\n+R\nT DB31.DBD0` | DEAD_CODE | Calculation result MD200'e yazılıyor, sonra DB31.DBD0'a kopyalanıyor ama DB31.DBD0 başka yerde okunmuyor. Muhtemelen debug kalıntı. | Y_DEAD_CODE | MEDIUM | AI_COMPLETE |

## Y_SAFETY_CONCERN Özel Listesi (RD14 FND001'e aktarıldı)

| ANN ID | Block | Network | Açıklama |
|--------|-------|---------|----------|
| ANN0042 | FC10 | NW5 | E-Stop North + Master Contactor (standart PLC) |
| ANN0043 | FC10 | NW6 | E-Stop South (paralel devre) |
| ANN0051 | FC10 | NW8 | Light Curtain Loading + BYPASS logic ⚠️ |
| ANN0078 | FC10 | NW9 | Light Curtain Unloading |

## #UNKNOWNS

| Kod | Sebep |
|-----|-------|
| FC30 CASE M10.0..M10.7 | Pseudo state machine — operator workshop ile sequence belirlenmeli |
| MW100..MW150 | Sembol tablosunda yok, fonksiyon belirsiz — operator interview |

*v1.0.0 — RD14 modernizasyon analizi için kaynak.*
