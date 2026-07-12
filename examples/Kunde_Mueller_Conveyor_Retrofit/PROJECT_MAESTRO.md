---
project_id: KMG-2026-001
project_name: Kunde_Mueller_Conveyor_Retrofit
customer: Kunde Müller GmbH
project_type: retrofit
created: 2026-05-15
factory_version: v3.0.0-alpha
data_classification: CONFIDENTIAL
output_language: DE
safety_engineer: Eng. Hans Becker (TÜV cert. #DE-001234)
last_validated: 2026-05
---

# PROJECT_MAESTRO.md — Kunde_Mueller_Conveyor_Retrofit

> Bu proje **AUTOMATION_FACTORY** v3.0.0-alpha standartlarına göre yönetilir.

---

## 1. Proje Meta

| Alan | Değer |
|------|-------|
| Project ID | KMG-2026-001 |
| Müşteri | Kunde Müller GmbH (Düsseldorf, DE) |
| Tip | RETROFIT |
| Başlangıç | 2026-05-01 |
| Hedef SAT | 2026-09-30 |
| Veri sınıfı | 🟠 CONFIDENTIAL |
| Output language | DE (Deutsch) |
| Project Lead | Mehmet Haydar |
| Safety Engineer | Hans Becker (TÜV sert.) |

---

## 2. Factory Referansları

| Tip | Dosya | Sürüm |
|-----|-------|-------|
| Pipeline | `PIPELINE_CODE_REWRITE.md` | v1.0.0 |
| Naming | `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md` | v1.0 |
| Data classification | `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md` | v1.0 |
| Lang policy | `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md` | v1.0.0 |
| Retrofit maestro | `02_PROJECT_TYPES/RETROFIT/RETROFIT_MAESTRO.md` | v1.0 |
| FB template | `01_GLOBAL_STANDARDS/code_templates/GLOBAL_FB_TEMPLATE.scl` | v1.0 |
| Glossary | `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_DE.md` | v1.0.0 |

---

## 3. Pipeline Gate İlerleme

```
Gate 1 KEŞIF             [completed]  2026-05-01
Gate 2 ÇIKARTIM          [completed]  2026-05-15 (AI extraction + parsing)
Gate 3 HUMAN REVIEW      [in_progress] 2026-05-15..06-15 (RD05 safety eng.)
Gate 4 VALIDATION        [pending]
Gate 5 KOD ÜRETİMİ       [in_progress] (örnek FB_Motor üretildi)
Gate 6 SİMÜLASYON        [pending]    PLCSIM Advanced ortamı kurulacak
Gate 7 FAT/SAT           [pending]    FAT 2026-09-01, SAT 2026-09-15
```

---

## 4. 14-Point Raw Data Pack Durumu

| RD | Dosya | Status | Kaynak | Yüzde |
|----|-------|--------|--------|-------|
| RD01 | RD01_IO_List.md | DRAFT (AI) | AI extractor (S7-300 parser) | 90% |
| RD02 | RD02_DataDict.md | DRAFT (AI) | AI extractor | 85% |
| RD03 | RD03_Flowchart.md | DRAFT | (placeholder) | 20% |
| RD04 | RD04_Mode.md | DRAFT (AI) | AI + operatör görüşmesi | 80% |
| RD05 | RD05_Safety_DRAFT_UNVERIFIED.md | **DRAFT_UNVERIFIED** | AI — **Eng. Becker inceleme** | 60% |
| RD06 | RD06_Motion.md | DRAFT | (placeholder) | 30% |
| RD07 | RD07_Timing.md | DRAFT | (placeholder) | 30% |
| RD08 | RD08_Alarm.md | DRAFT (AI) | AI + WinCC export | 75% |
| RD09 | RD09_Comms.md | DRAFT | (placeholder) | 40% |
| RD10 | RD10_FBSpec.md | DRAFT (AI) | AI + manuel | 70% |
| RD11 | RD11_HMI.md | DRAFT | (placeholder) | 30% |
| RD12 | RD12_UseCase.md | DRAFT | (placeholder, workshop bekliyor) | 25% |
| RD13 | RD13_Annotation.md | DRAFT (AI) | AI annotation | 50% |
| RD14 | RD14_Modernization.md | DRAFT (AI) | AI + müşteri kararı | 80% |

**Kapsamlı RD durumu (örnek için):** 5 RD detaylı doldurulmuş, 9 RD placeholder.

---

## 5. Proje-Özel Kararlar

| Tarih | Karar | Sebep | Karar Sahibi |
|-------|-------|-------|--------------|
| 2026-05-02 | Output lang: DE | Müşteri Alman, operatörler Almanca konuşuyor | Müşteri |
| 2026-05-08 | F-PLC migrasyonu zorunlu | RD05 SAFETY CRITICAL bulgu | Safety Eng. + Müşteri |
| 2026-05-10 | GREENFIELD önerildi (Retrofit yerine) | Donanım eskidi + F-PLC ek maliyet zaten gerekli | RD14 karar matrisi |

---

## 6. Veri Sınıflandırma + AI Politikası

```
data_classification: CONFIDENTIAL (🟠)
```

| Sınıf | Uygulanan |
|-------|-----------|
| 🟠 CONFIDENTIAL | Self-hosted Claude API (Anthropic Bedrock) kullanılıyor |
| 🟠 CONFIDENTIAL | Cursor Enterprise tier (kod) |
| 🟠 CONFIDENTIAL | Public AI servisleri (ChatGPT.com, claude.ai web) **YASAK** |

---

## 7. Safety (RD05) İzleme ⚠️

```yaml
safety_engineer:
  name: Hans Becker
  certification: TÜV Süd, IEC 61508
  cert_number: DE-001234
  contact: hans.becker@example.com

risk_assessment:
  document_id: KMG-RA-2026-001
  date: 2026-05-08
  iso_12100: COMPLETED
  result: SIL2 / PLr_d gereksinim (E-Stop)

sil_requirements:
  - function: SF001 EStop_Operator_Panel
    required: SIL2 / PLr_d
    achieved: PENDING (F-PLC migrasyonu sonrası)
    status: DRAFT_UNVERIFIED
  - function: SF002 LightCurtain_Loading_Zone
    required: SIL3 / PLr_e
    achieved: PENDING
    status: DRAFT_UNVERIFIED
```

---

## 8. Ekip + Sorumluluk

| Rol | İsim |
|-----|------|
| Project Lead | Mehmet Haydar |
| Lead Engineer | Mehmet Haydar |
| Safety Engineer | Hans Becker (external consultant, TÜV) |
| HMI Designer | (TBD) |
| Customer Contact | Klaus Müller (production manager) |

---

## 9. Risk Kaydı

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| F-PLC tedariki gecikme | Orta | Yüksek | Önceden sipariş (Siemens lead time 8-12 hafta) |
| Almanca terminoloji tutarsızlığı | Düşük | Orta | Glossary kullan + müşteri review |
| Eski kod yorumsuz | Yüksek | Orta | RD13 Annotation + operatör görüşmesi |
| TÜV süreci uzaması | Orta | Yüksek | Erken safety eng. sürece dahil |

---

## 10. Sprint Kaydı

| Sprint | Hedef | Status |
|--------|-------|--------|
| 2026-W18 | Müşteri brief + Gate 1 | ✅ |
| 2026-W19 | _input toplama + AI extraction | ✅ |
| 2026-W20-21 | Gate 3 review + safety analiz | 🔵 |
| 2026-W22-23 | RD14 final + müşteri karar | ⏳ |
| 2026-W24-30 | Gate 5 kod üretimi | ⏳ |
| 2026-W31-35 | Gate 6 simülasyon | ⏳ |
| 2026-W36 | Gate 7 FAT | ⏳ |
| 2026-W39 | SAT + teslim | ⏳ |

---

## 11. Notlar

- Müşteri Alman dilinde tüm dokümantasyon istiyor (FAT report + Operator Manual)
- F-PLC migrasyonu için ek bütçe onaylandı (€18K donanım + ~80h mühendislik)
- Eski makinenin elektrik şemaları EPLAN P8 (.zw1) elimizde

---

*Bu dosya canlıdır. Her gate ilerlemesinde güncellenir.*
