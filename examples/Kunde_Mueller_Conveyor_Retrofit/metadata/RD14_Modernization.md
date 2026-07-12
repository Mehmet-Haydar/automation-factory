---
title: RD14_Modernization — Kunde Müller Conveyor Retrofit
last_validated: 2026-05
status: ACTIVE
---

# RD14_Modernization — Kunde Müller Conveyor Retrofit

> AI tarafından üretildi (PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md) — RD13 Annotation ve _parsed.md kaynak olarak.

---

## Frontmatter

```yaml
project_id: KMG-2026-001
filled_by: AI Engine + Mehmet Haydar (review)
filled_at: 2026-05-15
customer_decision: PENDING (müşteri sunumu 2026-06-01)
status: IDENTIFIED
```

---

## Özet (SummaryByCategory)

| Kategori | CRITICAL | MAJOR | MINOR | INFO | Toplam | Tahmini Çaba (saat) | TopPriority |
|----------|----------|-------|-------|------|--------|---------------------|-------------|
| SAFETY | 3 | 0 | 0 | 0 | 3 | 96 | FND001, FND008, FND009 |
| NAMING | 0 | 1 | 0 | 0 | 1 | 12 | FND002 |
| STRUCTURE | 0 | 1 | 0 | 0 | 1 | 40 | FND003 |
| OBSOLETE_PLATFORM | 0 | 1 | 0 | 0 | 1 | 16 | FND004 |
| MAINTAINABILITY | 0 | 0 | 1 | 0 | 1 | 8 | FND005 |
| ALARM | 0 | 0 | 1 | 0 | 1 | 4 | FND006 |
| HMI | 0 | 0 | 1 | 0 | 1 | 16 | FND007 |
| **TOPLAM** | **3** | **3** | **3** | **0** | **9** | **192** | |

**Donanım maliyeti:** ~€18.000 (F-PLC + F-IO + yeni HMI panel)

---

## Modernizasyon Kararı (ModernizationDecision)

| Seçenek | Uygulanabilir Bulgu | Toplam Çaba | Öneri | Gerekçe |
|---------|---------------------|-------------|-------|---------|
| **RETROFIT** | 9 | HIGH (192h + €18K) | ACCEPTABLE | NAMING ve STRUCTURE bulguları çözülebilir; F-PLC eklenebilir ama eski donanım kalır. Risk: yedek parça sorunu devam eder. FND008/FND009 (E-Stop bypass + sahte yedeklilik) zaten F-PLC migrasyonu ile çözülür. |
| **GREENFIELD** ⭐ | 9 | VERY_HIGH (256h + €45K) | **RECOMMENDED** | Donanım eskidi (1995 — 31 yıl), yedek parça yok. F-PLC zaten gerekli — yeni CPU ile gelir. TIA Portal V18 native. Modern 15+ yıllık yatırım. Üç CRITICAL bulgu da tek migrasyonla çözülür. |
| HYBRID | 9 | HIGH (216h + €30K) | NOT_RECOMMENDED | Karma yaklaşım çift maliyet getirir. Ya tam retrofit ya tam greenfield. |

**Öneri:** **GREENFIELD** — Eski donanım sorunu + F-PLC zorunluluğu birleşince total maliyet yakın, ömür çok daha uzun.

---

## Bulgular

### FND001 — Standart PLC'de E-Stop + Light Curtain (SAFETY / CRITICAL) 🛑

- **Kategori:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 1
- **PLCPlatform:** S7_300
- **BlockRef:** FC10 (Networks 5, 6, 8, 9)
- **AnnotationRef:** ANN0042, ANN0051, ANN0078 (RD13'ten)

**Anti-Pattern:**
> Acil durdurma (2× E-Stop) ve güvenlik bariyeri (2× Light Curtain) standart PLC üzerinde implement edilmiş — F-CPU yok. Master kontaktör (Q3.7) standart DO çıkışından sürülüyor. Light curtain için "Wartungsmodus" altında bypass mantığı var (FC10 NW8).
>
> Tek arıza (PLC cycle hatası, modül arızası, kablo kopuk vb.) güvenlik fonksiyonunu devre dışı bırakabilir. CE belge yenilenmesi yasal olarak mümkün değil.

**Kötü Kod Örnek (FC10 NW5):**
```
NETWORK 5: E-Stop Logik
    A     I    100.0    // NOT-AUS Nord (NC)
    A     I    100.1    // NOT-AUS Süd (NC)
    AN    M    50.0     // Wartungs-Bypass
    =     Q    3.7      // Hauptschütz
```

**Modern Alternatif:**
> F-PLC (Siemens S7-1500F veya GuardLogix) ile güvenlik fonksiyonları yeniden implement edilir. PROFIsafe telegram ile F-I/O bağlantısı. SIMATIC Safety bloğu F_ESTOP1 kullanılır.

**İyi Kod Örnek:**
```scl
// F_FB_EStop_Operator_001 (TIA Safety, F-FB)
"F_FB_EStop_OP_001"(
    E_STOP := "F_I_EStop_North" AND "F_I_EStop_South",  // Two-channel
    ACK_NEC := TRUE,                                     // Manual reset
    ACK := "DB_Safety".bResetReq,
    Q := "DB_Safety".bEStopOK,
    DIAG := "DB_Safety".dwEStopDiag
);

// Light Curtain with proper muting (no manual bypass)
"F_FB_MutingP_001"(
    AOPD := "F_I_LC_Loading",
    M1 := "F_I_Muting_S1",     // 2 muting sensor + time window
    M2 := "F_I_Muting_S2",
    Q := "DB_Safety".bLC_OK
);
```

- **Effort:** HIGH (~80 saat + donanım)
- **EffortDetail:** F-CPU programlama 40h + risk değerlendirme 16h + FAT/TÜV 24h
- **Impact:** SAFETY
- **StandardRef:** IEC 62061, ISO 13849-1, Makine Direktifi 2006/42/EC
- **LinkedRD:** RD05 (SF001-SF004)
- **Retrofit:** YES (F-CPU ek modül olarak)
- **Greenfield:** YES (yeni CPU zaten F-PLC)
- **AutoFixable:** NO (insan + sertifikalı mühendis zorunlu)
- **VerificationRequired:** SAFETY_ENGINEER
- **VerificationDetail:** Hans Becker (TÜV cert.) + risk değerlendirme + FAT response time test
- **Notes:** Light curtain bypass kaldırılmalı — alternatif olarak door interlock + muting redesign
- **Status:** IDENTIFIED (sertifikalı mühendis review bekliyor)

---

### FND002 — 47 Mutlak Adres + Almanca İsim Karışımı (NAMING / MAJOR)

- **Kategori:** NAMING
- **Severity:** MAJOR
- **Priority:** 2
- **PLCPlatform:** S7_300
- **BlockRef:** OB1, FC1, FC2, FC30
- **AnnotationRef:** ANN0001..ANN0035

**Anti-Pattern:**
> Tüm I/O ve memory marker'lar Almanca sembol + mutlak adres karışımı (E_Start, A_Schuetz, MW100). 47 mutlak adres tespit edildi. Bakım sırasında adres ↔ işlev eşleştirmesi zor.

**Modern Alternatif:**
> GLOBAL_NAMING_STANDARD.md (AUTOMATION_FACTORY): tag format `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$`. Eski Almanca isimler `OldTag` sütununda korunur, Description'da `(orig: ...)` formatında.

**İyi Kod Örnek:**
```scl
// Eski: A I 0.0 (E_Start) → A I 0.2 (E_Motor_Lauf) → = Q 0.0 (A_Schuetz)
// Yeni:
CONV_BEL_001_OUT := MOT_CV01_001_START AND NOT MOT_CV01_001_RUN;
```

- **Effort:** MEDIUM (~12 saat)
- **Impact:** MULTIPLE — MAINTAINABILITY, RELIABILITY, COMPLIANCE
- **ImpactDetail:** Bakım kolaylığı + IEC 61131-3 uyum + müşteri belgelendirme
- **LinkedRD:** RD01, RD02
- **Retrofit:** YES (PARTIAL — find-replace script ile)
- **Greenfield:** YES (zaten standart)
- **AutoFixable:** PARTIAL
- **AutoFixNote:** RD01 onaylandıktan sonra `script_tag_rename.py` ile bulk-rename; manuel doğrulama
- **VerificationRequired:** FUNCTIONAL_TEST
- **Status:** IDENTIFIED

---

### FND003 — Tüm Lojik OB1'de (STRUCTURE / MAJOR)

- **Severity:** MAJOR | **Priority:** 3 | **Effort:** HIGH (~40h)

OB1 2400+ satır, modülerlik yok. Modern alternatif: FB_Motor + FB_Valve + FB_Sequence + FB_ModeMgr modüler yapısı (RD10 FBSpec).

---

### FND004 — S7-300 Desteği Biten Platform (OBSOLETE_PLATFORM / MAJOR)

- **Severity:** MAJOR | **Priority:** 4 | **Effort:** MEDIUM (~16h)

Siemens S7-300 üretim sonu (end-of-life 2023). Yedek parça erişimi azalıyor. TIA Portal V14+ S7-300 destekliyor ama gelecek sürümlerde kaldırılacak.

---

### FND005 — %30 Yorumsuz Kod (MAINTAINABILITY / MINOR)

- **Severity:** MINOR | **Priority:** 50 | **Effort:** LOW (~8h)

Network başlık yorumları eksik, magic number'lar açıklamasız. Modern: header + inline comment.

---

### FND006 — Alarm Yönetimi ISA-18.2 Dışı (ALARM / MINOR)

- **Severity:** MINOR | **Priority:** 60 | **Effort:** LOW (~4h)

FC40'ta 32 alarm bit set ediliyor, sınıflandırma yok. Modern: RD08 ISA-18.2 (Critical/Warning/Info) + ALARM_S/ProgramAlarm.

---

### FND007 — HMI WinCC Classic ISA-101 Dışı (HMI / MINOR)

- **Severity:** MINOR | **Priority:** 70 | **Effort:** MEDIUM (~16h)

Eski HMI çok renk + access level yok + multi-lang eksik. Modern: TIA WinCC Unified + ISA-101 disiplini (RD11).

---

### FND008 — M50.0 Wartungs-Bypass E-Stop'u Devre Dışı Bırakıyor (SAFETY / CRITICAL) 🛑

- **Kategori:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 1 (FND001 ile aynı seviye — birlikte ele alınır)
- **PLCPlatform:** S7_300
- **BlockRef:** FC10 Network 5
- **AnnotationRef:** (snippet analizinden — `_input/old_code_snippet.awl`)
- **Source:** AWL snippet IO extract session (2026-05-22)

**Anti-Pattern:**
> FC10 NW5'te master kontaktör lojiği şu şekilde:
>
> ```
> A   I 100.0   // NOT-AUS Nord (NC)
> A   I 100.1   // NOT-AUS Süd  (NC)
> AN  M 50.0    // Wartungs-Bypass
> =   Q 3.7     // Hauptschütz
> ```
>
> `AN M50.0` lojiği ile her iki E-Stop giriş zinciri yazılım üzerinden devre dışı bırakılabiliyor. M50.0 = TRUE olduğunda master kontaktör (Q3.7) E-Stop basılmasına rağmen enerjili kalır. Bu, FND001'in (E-Stop standart PLC'de) somut tezahürüdür ve TÜV denetiminde ayrı bir bulgu olarak raporlanır.

**Modern Alternatif:**
> F-PLC (F-CPU) ile iki kanallı E-Stop. Bypass mantığı kaldırılır; bakım modu ayrı bir sertifikalı F-FB ile yönetilir (door interlock + key switch ile garantili).

**İyi Kod Örnek:**
```scl
// Bypass yok — bakım modu donanımsal key switch ile
"F_FB_EStop_OP_001"(
    E_STOP  := "F_I_EStop_North" AND "F_I_EStop_South",
    ACK_NEC := TRUE,
    ACK     := "DB_Safety".bResetReq,
    Q       := "DB_Safety".bEStopOK
);
// Wartungsmodus yalnızca F-IO key switch ile, yazılım marker'ı ile DEĞİL
```

- **Effort:** MEDIUM (~8 saat — FND001 ile birlikte ele alınırsa ek 0h)
- **EffortDetail:** Anti-pattern tespiti + risk değerlendirme + F-FB doğrulama
- **Impact:** SAFETY (insan can güvenliği)
- **StandardRef:** IEC 62061, ISO 13849-1, Makine Direktifi 2006/42/EC
- **LinkedRD:** RD01 (MASTER_CONTACTOR Q3.7, F_I_EStop_*), RD05 (SF001), RD14 (FND001 ile bağ)
- **Retrofit:** YES (F-CPU migrasyonu ile otomatik çözülür)
- **Greenfield:** YES
- **AutoFixable:** NO
- **VerificationRequired:** SAFETY_ENGINEER
- **VerificationDetail:** Hans Becker (TÜV cert.) — bypass'ın gerçekten kaldırıldığını + bakım modunun donanım kilidiyle korunduğunu test eder
- **Notes:** FND001'in alt bulgusudur; ayrı raporlama, müşterinin somut riski görmesini sağlar
- **Status:** IDENTIFIED (sertifikalı mühendis review bekliyor)

---

### FND009 — E-Stop Yedekliliği Bozuk: NW5 vs NW6 Asimetrisi (SAFETY / CRITICAL) 🛑

- **Kategori:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 1 (FND001 ile aynı seviye)
- **PLCPlatform:** S7_300
- **BlockRef:** FC10 Networks 5 ve 6
- **AnnotationRef:** (snippet analizinden — `_input/old_code_snippet.awl`)
- **Source:** AWL snippet IO extract session (2026-05-22)

**Anti-Pattern:**
> FC10'da E-Stop iki ayrı network'te işleniyor ama mantıksal yedeklilik sahte:
>
> - **NW5:** `A I100.0 & A I100.1 & AN M50.0 = Q3.7` — master contactor'ı sürer (bypass'lı)
> - **NW6:** `A I100.0 & A I100.1 = M50.7` — yalnızca dahili bayrak set eder, hiçbir donanım çıkışını sürmez
>
> NW6, NW5'in **fiziksel yedeği değil**, sadece bir bayrak aynası. PLC NW5 çalıştırmayı atlarsa (cycle hatası, jump, dispatcher bug) E-Stop hiçbir donanım çıkışına ulaşmaz — NW6'nın çıktısı kullanılmıyor. Bu, görsel olarak "iki kanallı görünen ama tek noktada başarısız olan" klasik bir anti-pattern.

**Modern Alternatif:**
> F-PLC'de E-Stop iki donanım kanalından okunur, F-CPU otomatik diversite + cross-comparison yapar. Bayrak-mirror gibi sahte yedeklilik mümkün değil (compiler reddeder).

**İyi Kod Örnek:**
```scl
// İki kanal F-IO girişinden, F-FB tarafından otomatik karşılaştırılır
// Yazılım yedekliliği değil, F-CPU diversity ile garantili
"F_FB_EStop_OP_001"(
    E_STOP_CH1 := "F_I_EStop_North_K1",  // F-IO modül 1
    E_STOP_CH2 := "F_I_EStop_North_K2",  // F-IO modül 2 (farklı CPU çekirdeği)
    Q          := "DB_Safety".bEStopOK   // CCC zaman aşımı F-CPU'da
);
```

- **Effort:** MEDIUM (~8 saat — FND001 ile birlikte ele alınırsa ek 0h)
- **EffortDetail:** NW5/NW6 lojik analizi + diversity desgin + F-IO katman seçimi
- **Impact:** SAFETY (PFH/SIL hesaplaması yapılmamış, fiili PLr azalmış)
- **StandardRef:** ISO 13849-1 Category 3/4 (diversity requirement), IEC 62061
- **LinkedRD:** RD01 (F_I_EStop_*, MASTER_CONTACTOR), RD05 (SF001), RD14 (FND001 ile bağ)
- **Retrofit:** YES (F-CPU migrasyonu ile otomatik çözülür)
- **Greenfield:** YES
- **AutoFixable:** NO
- **VerificationRequired:** SAFETY_ENGINEER
- **VerificationDetail:** Hans Becker (TÜV cert.) — PFH/Category hesabı + F-IO diversity doğrulaması
- **Notes:** Snippet analizi olmasaydı tespit edilemezdi — "kod okuma" disiplininin somut faydası
- **Status:** IDENTIFIED (sertifikalı mühendis review bekliyor)

---

## #UNKNOWNS

| Bulgu | Sebep |
|-------|-------|
| Müşteri bütçe kararı | RETROFIT €32K vs GREENFIELD €60K — müşteri tercihi belirsiz |
| TÜV süreci süresi | Müşteri bölgesine göre 4-12 hafta arası — netleşmesi gerek |

---

## Müşteri Sunumu Özet (2026-06-01)

```
KUNDE MÜLLER GMBH — MODERNIZASYON RAPORU
============================================

9 modernizasyon bulgusu tespit edildi (3 CRITICAL, 3 MAJOR, 3 MINOR).

CRITICAL bulgular:
  FND001 — F-PLC YOK (E-Stop + Light Curtain standart PLC'de)
  FND008 — M50.0 Wartungs-Bypass E-Stop'u yazılım üzerinden devre dışı bırakıyor
  FND009 — E-Stop yedekliliği sahte (NW5/NW6 asimetrisi)

Üçü de aynı kök nedene bağlı: F-PLC migrasyonu üçünü birden çözer.
CE belgesi mevcut yapıda yenilenemez.

3 Seçenek:
  A) RETROFIT — €32K, 4 ay, F-PLC ek modül
  B) GREENFIELD — €60K, 6 ay, tam yenileme (ÖNERİ ⭐)
  C) HYBRID — €45K, 5 ay (önerilmez)

Bizim önerimiz: GREENFIELD
  - Donanım zaten eski (1995)
  - F-PLC native
  - 15+ yıl ömür
  - TIA Portal V18 modern platform

Lütfen seçiminizi 2026-06-15'e kadar bildirin.
```

---

*v1.0.0 — Bu örnek RD14 müşteriye sunulacak gerçek bir karar belgesidir. Factory'nin değer önerisinin somut özetidir.*
