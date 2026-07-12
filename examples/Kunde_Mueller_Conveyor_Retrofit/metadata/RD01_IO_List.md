---
title: RD01_IO_List — Kunde Müller Conveyor Retrofit
last_validated: 2026-05
status: ACTIVE
---

# RD01_IO_List — Kunde Müller Conveyor Retrofit

> AI extraction + insan inceleme (Gate 2 + Gate 3 in_progress). 47 sinyal tespit edildi.

---

## Frontmatter

```yaml
project_id: KMG-2026-001
project_name: Kunde_Mueller_Conveyor_Retrofit
customer: Kunde Müller GmbH
filled_by: AI Engine + Mehmet Haydar (review)
filled_at: 2026-05-15
output_language: DE
status: DRAFT
```

---

## Özet

- Toplam sinyal: 47
- DI: 24 | DO: 18 | AI: 3 | AO: 2
- Safety-related: 4 (E-Stop ×2, Light Curtain ×2) — ⚠️ standart PLC üzerinde
- Modül sayısı: 5

---

## Sinyaller

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | SourceModule | OldTag | Notes | Status |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|----------|----------|---------------|--------------|--------|-------|--------|
| MOT_CV01_001_START | %I0.0 | BOOL | DI | Conveyor1 | Start button push (orig: Taste Start) | NO | | | | N | DI_001 | E_Start | Operator panel — FC30 NW1 (Schritt 10 trigger, AUTO mode + S M10.0) | Active |
| MOT_CV01_001_STOP | %I0.1 | BOOL | DI | Conveyor1 | Stop button push (orig: Taste Stop) | NC | | | | N | DI_001 | E_Stop_Btn | Operator panel | Active |
| MOT_CV01_001_RUN | %I0.2 | BOOL | DI | Conveyor1 | Motor running feedback (orig: Motor läuft) | NO | | | | N | DI_001 | E_Motor_Lauf | | Active |
| MOT_CV01_002_RUN | %I0.3 | BOOL | DI | Conveyor2 | Motor running feedback | NO | | | | N | DI_001 | E_Motor_Lauf_2 | | Active |
| MOT_CV01_001_FAULT | %I0.4 | BOOL | DI | Conveyor1 | Drive fault (orig: Antriebsstörung) | NC | | | | N | DI_001 | E_Stoerung | | Active |
| PC_LOAD_001 | %I0.5 | BOOL | DI | Loading | Photocell beam (orig: Lichtschranke Beladung) | NO | | | | N | DI_001 | E_LS_Beladen | Çift rol: yükleme algılama + FC30 NW3 Schritt 20→30 sıra geçişi | Active |
| LS_LIM_001_TOP | %I0.6 | BOOL | DI | Conveyor1 | Limit switch top position | NC | | | | N | DI_001 | E_ES_Oben | | Active |
| LS_LIM_001_BOT | %I0.7 | BOOL | DI | Conveyor1 | Limit switch bottom position | NC | | | | N | DI_001 | E_ES_Unten | | Active |
| F_I_EStop_North | %I100.0 | BOOL | DI | Operator | Emergency stop NORTH panel (orig: NOT-AUS Nord) | NC | | | | **Y** | DI_safety | E_NotAus_N | ⚠️ Standart PLC — F-PLC migrasyonu gerek (FC10 NW5/NW6/NW12) | Active |
| F_I_EStop_South | %I100.1 | BOOL | DI | Operator | Emergency stop SOUTH panel | NC | | | | **Y** | DI_safety | E_NotAus_S | ⚠️ Standart PLC (FC10 NW5/NW6/NW12 — North ile paralel) | Active |
| F_I_LC_Loading | %I100.2 | BOOL | DI | Loading | Light curtain loading zone (orig: Lichtvorhang Beladung) | NC | | | | **Y** | DI_safety | E_LV_Beladung | ⚠️ Bypass var (FC10 NW8 — `AN DB10.DBX0.2` Wartungsmodus üzerinden) | Active |
| F_I_LC_Unloading | %I100.3 | BOOL | DI | Unloading | Light curtain unloading zone | NC | | | | **Y** | DI_safety | E_LV_Entladung | ⚠️ Standart PLC (FC10 NW9 — bypass yok) | Active |
| MOT_CV01_001_OUT | %Q0.0 | BOOL | DO | Conveyor1 | Motor contactor command (orig: Schütz Motor) | | | | | N | DO_001 | A_Schuetz | FC10 NW8 — Wartungsmodus aktifken LC override edilebilir | Active |
| MOT_CV01_002_OUT | %Q0.1 | BOOL | DO | Conveyor2 | Motor contactor command | | | | | N | DO_001 | A_Schuetz_2 | FC10 NW9 — LC bypass yok | Active |
| VAL_V01_OUT | %Q0.2 | BOOL | DO | Pneumatic | Valve V01 open (orig: Ventil 1 öffnen) | | | | | N | DO_001 | A_Ventil_1 | | Active |
| VAL_V02_OUT | %Q0.3 | BOOL | DO | Pneumatic | Valve V02 open | | | | | N | DO_001 | A_Ventil_2 | | Active |
| LIGHT_GREEN | %Q0.4 | BOOL | DO | Panel | Status lamp GREEN (orig: Lampe grün) | | | | | N | DO_001 | A_Lampe_Gruen | | Active |
| LIGHT_RED | %Q0.5 | BOOL | DO | Panel | Status lamp RED (orig: Lampe rot) | | | | | N | DO_001 | A_Lampe_Rot | | Active |
| SIREN_001 | %Q3.6 | BOOL | DO | Panel | Audio alarm (orig: Hupe) | | | | | N | DO_001 | A_Hupe | | Active |
| MASTER_CONTACTOR | %Q3.7 | BOOL | DO | Cabinet | Master contactor (orig: Hauptschütz) | | | | | **Y** | DO_001 | A_Hauptschuetz | ⚠️ E-Stop bu çıkıştan kesiyor (FC10 NW5: `A I100.0 & A I100.1 & AN M50.0`) — M50.0 bypass riski! | Active |
| ANALOG_TT_TK_001 | %IW64 | INT | AI | Tank1 | Temperature sensor (orig: Temperatur Tank) | | °C | -20 | 200 | N | AI_001 | EW_Temp_Tank | Pt100 sensor | Active |
| ANALOG_PT_PI_001 | %IW66 | INT | AI | Pipe | Pressure sensor (orig: Druck Leitung) | | bar | 0 | 10 | N | AI_001 | EW_Druck | 4-20mA | Active |
| ANALOG_LT_TK_001 | %IW68 | INT | AI | Tank1 | Tank level (orig: Tank-Füllstand) | | % | 0 | 100 | N | AI_001 | EW_Niveau | Ultrasonik | Active |
| ANALOG_SP_OUT_001 | %QW64 | INT | AO | Conveyor1 | Drive speed setpoint (orig: Drehzahl Sollwert) | | % | 0 | 100 | N | AO_001 | AW_Drehzahl | 0-10V | Active |
| ANALOG_HEAT_OUT_001 | %QW66 | INT | AO | Heater | Heater PWM output | | % | 0 | 100 | N | AO_001 | AW_Heizung | 4-20mA | Active |
| ...22 more signals... | | | | | | | | | | | | | (kısaltıldı, gerçek listede 47 satır) | |

---

## #UNKNOWNS (Gate 3 — insan dolduracak)

| Eski Tag | Sebep |
|----------|-------|
| MW100..MW150 (sembolless) | Sembol tablosunda yok ama OB1'de kullanılıyor — operatör interview gerek |
| EW_Druck (PT) | Range 0-10 bar mı 0-16 bar mı belirsiz — drive datasheet gerek |
| A_Reserve_1..A_Reserve_4 | Reserve olarak işaretli ama eski koddan bağlantı görünüyor |

---

## ⚠️ KRİTİK BULGULAR (RD14'e aktarılan)

1. **F_I_EStop_* + MASTER_CONTACTOR standart PLC üzerinde:** FND001 SAFETY CRITICAL (RD14)
2. **Light curtain bypass logic (FC10 NW8):** Wartungsmodus (`DB10.DBX0.2`) aktifken LC `F_I_LC_Loading` override ediliyor — risk değerlendirme gerek
3. **47 sinyal mutlak adres + Almanca sembol karışımı:** FND002 NAMING MAJOR (RD14)
4. **🆕 E-Stop M50.0 Wartungs-Bypass (FC10 NW5):** `AN M50.0` lojiği ile her iki NOT-AUS giriş zinciri yazılım üzerinden devre dışı bırakılabiliyor → `MASTER_CONTACTOR` (Q3.7) sürekli enerjili kalır. **FND008** SAFETY CRITICAL (RD14) — snippet analizinden çıktı
5. **🆕 E-Stop yedeklilik bozuk (FC10 NW5 vs NW6):** NW5 master contactor'a `AN M50.0` ile gidiyor (bypass'lı), NW6 ise yalnızca `M50.7` dahili bayrak set ediyor — fiziksel yedeklilik değil, sadece bayrak ayna. **FND009** SAFETY CRITICAL (RD14)

---

## Doldurma Notları (Bu örnek için)

- **47 sinyalin %100'ü OldTag korundu** (Almanca isimler `(orig: ...)` formatında)
- **F-prefix sadece güvenlik PLC sinyalleri için** — RD14'e migrasyon önerisi
- **Description multi-lang:** İngilizce + (orig: Almanca) — `output_language=DE` için Almanca da hazır
- **Memory marker (M*) bu listede YOK** — RD02'ye gider
- **#UNKNOWNS 3 madde insan inceleme bekliyor**

### Snippet merge (2026-05-22)

- Kaynak: `_input/old_code_snippet.awl` (FC10 E-Stop + FC30 Sequence)
- Etkilenen 9 satırın **Notes** sütunu FC/NW cross-reference ile zenginleştirildi (`%I0.0`, `%I0.5`, `%I100.0..3`, `%Q0.0`, `%Q0.1`, `%Q3.7`)
- Snippet analizi 2 yeni KRİTİK BULGU ortaya çıkardı (RD14'e **FND008/FND009** olarak eklendi):
  - **FND008** — M50.0 E-Stop yazılım bypass'ı (NW5)
  - **FND009** — E-Stop yedekliliği bozuk (NW5 master contactor, NW6 sadece bayrak)
- Snippet ham CSV: `_output/io_table_snippet.csv` (audit izi için saklandı)
- **Not (2026-05-23):** İlk merge sırasında bu bulgular geçici olarak FND003/FND004 olarak adlandırılmıştı; ID çakışması (RD14 zaten FND003=STRUCTURE, FND004=OBSOLETE_PLATFORM kullanıyordu) düzeltildi.

---

*v1.0.0 — Bu örnek RD01 çıktısı gerçek factory'nin AI extraction sonucu üretirken oluşturduğu yapıya birebir uyar.*
