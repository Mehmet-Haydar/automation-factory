---
title: RD05_Safety_DRAFT_UNVERIFIED — Kunde Müller Conveyor Retrofit
last_validated: 2026-05
status: DRAFT_UNVERIFIED
review_pending: safety_engineer
---

# RD05_Safety_DRAFT_UNVERIFIED — Kunde Müller Conveyor Retrofit

> ⚠️ **DİKKAT:** Bu dosya AI tarafından çıkartılmıştır. Sertifikalı güvenlik mühendisi (Hans Becker, TÜV) onayı OLMADAN KULLANILAMAZ. Tüm SIL/PLr/Category alanları BOŞ — insan dolduracak.

---

## Frontmatter

```yaml
project_id: KMG-2026-001
filled_by: AI Engine (DRAFT)
filled_at: 2026-05-15
status: DRAFT_UNVERIFIED                 # AI tarafından ASLA değişmez
safety_engineer: Hans Becker (TÜV cert. #DE-001234)
risk_assessment_doc: KMG-RA-2026-001 (2026-05-08)
review_pending: TRUE
```

---

## Özet

- **Tespit edilen güvenlik fonksiyonu: 4**
- **F-PLC mevcut: NO** (CPU 315-2 DP standart)
- **F-FB sayısı: 0** (hiçbir F-blok yok)
- **Standart PLC üzerinde güvenlik mantığı: 4 fonksiyon (KRİTİK)** 🛑

---

## Güvenlik Fonksiyonları

| FunctionID | FunctionName | SIL_Level | Category | TriggerCondition | SafeAction | ResponseTime_ms | ResetType | F_InputTag | F_OutputTag | F_DB | F_FB | ProofTestInterval_h | Verified_By | Notes | Status |
|------------|--------------|-----------|----------|------------------|------------|------------------|-----------|------------|-------------|------|------|---------------------|-------------|-------|--------|
| SF001 | EStop_North_Panel | | | F_I_EStop_North = FALSE (NC) | All motor outputs OFF, Q3.7 = FALSE | | Manual | F_I_EStop_North | Q3.7 (MASTER_CONTACTOR) | (standart DB10) | FC10 NW5 (standart kod) | | | ⚠️ **STANDARD PLC — F-PLC migrasyonu zorunlu** | DRAFT_UNVERIFIED |
| SF002 | EStop_South_Panel | | | F_I_EStop_South = FALSE (NC) | Aynı (paralel devre) | | Manual | F_I_EStop_South | Q3.7 | - | FC10 NW6 | | | ⚠️ Standart PLC | DRAFT_UNVERIFIED |
| SF003 | LightCurtain_Loading | | | F_I_LC_Loading = TRUE (beam broken) | Conveyor STOP (Q0.0 = FALSE) | | Auto | F_I_LC_Loading | Q0.0 | - | FC10 NW8 | | | ⚠️ **BYPASS VAR (Wartungsmodus aktifken)** — risk değerlendirme gerek | DRAFT_UNVERIFIED |
| SF004 | LightCurtain_Unloading | | | F_I_LC_Unloading = TRUE (beam broken) | Conveyor2 STOP | | Auto | F_I_LC_Unloading | Q0.1 | - | FC10 NW9 | | | ⚠️ Standart PLC | DRAFT_UNVERIFIED |

---

## ⚠️ Güvenlik Mühendisine Sorular

| FunctionID | Soru |
|------------|------|
| SF001 | E-Stop için SIL ne olmalı? (mevcut risk grafiğine göre tahmin: SIL2 / PLr_d) |
| SF001 | Response time gereksinimi nedir? Müşteri specsi var mı? |
| SF002 | Yedek (redundancy) gerekli mi? İki E-Stop birbirine paralel devrede şu an |
| SF003 | **Light curtain bypass kabul edilebilir mi?** EN 61496-1 ihlali olabilir |
| SF003 | Muting yerine farklı koruma stratejisi mümkün mü? (örn. door interlock) |
| SF004 | Unloading zone'da operatör tehlike alanına ne kadar yaklaşır? |
| TÜM | F-PLC migrasyonu için süre + bütçe onayı alındı mı? |

---

## SAFETY_ON_STANDARD_PLC Tespitleri (KRİTİK) 🛑

> Bu bölüm RD14_Modernization.md → FND001'e aktarılmıştır.

| Block | Network | Description | Risk Seviyesi |
|-------|---------|-------------|---------------|
| FC10 | NW5 | E-Stop North → MASTER_CONTACTOR (Q3.7) | **CRITICAL** — tek arıza E-Stop'u devre dışı bırakabilir |
| FC10 | NW6 | E-Stop South → MASTER_CONTACTOR | **CRITICAL** |
| FC10 | NW8 | Light curtain + BYPASS logic | **CRITICAL** — bypass yetkilendirmesi belirsiz |
| FC10 | NW9 | Light curtain (unloading) | **CRITICAL** |

**Sonuç:** F-CPU eklenmeden bu makineye CE belge yenilenmesi mümkün değil.

---

## Müşteriye Sunulacak Bulgu Raporu

```
GÜVENLİK BULGUSU — KUNDE MÜLLER GMBH (KMG-2026-001)
====================================================

Tarih: 2026-05-15
Hazırlayan: Mehmet Haydar (proje mühendisi) + Hans Becker (TÜV)
Gizlilik: 🟠 CONFIDENTIAL

Tespit:
  Makinenizin 4 güvenlik fonksiyonu (2× E-Stop, 2× Light Curtain) standart
  PLC üzerinde implement edilmiştir. F-CPU (SIL-değerlendirmeli güvenlik PLC)
  bulunmamaktadır.

Etki:
  - CE belge yenilenmesi mümkün değil (Makine Direktifi 2006/42/EC)
  - SIL/PLr seviyesi ölçülemez/atanamaz
  - Tek nokta arıza riski (PLC çevrim hatası = E-Stop devre dışı kalır)
  - Light curtain bypass mevcut — operatör risk değerlendirmesi yapılmalı

Öneri:
  F-PLC migrasyonu (RD14_Modernization.md FND001):
  - Donanım: S7-1500F + F-DI + F-DO ≈ €18.000
  - Mühendislik: ~80 saat
  - TÜV belgelendirme: ~€8.000
  - Toplam: ~€32.000 + zaman: 8-12 hafta

  ALTERNATIF: Greenfield (tüm sistem yenileme) — daha uzun vadeli yatırım,
  hem F-PLC hem güncel donanım. RD14 ModernizationDecision GREENFIELD
  öneriyor.

Yasal Not:
  Bu bulgu Türk ve Alman Makine Direktifi gereği müşteriye bildirilmek
  zorundadır. Aksiyon alınmazsa, makine üzerinde çalışmaya devam etmek
  yasal risk taşır.
```

---

## #UNKNOWNS

| Eski sembol | Sebep |
|-------------|-------|
| (NW8 Bypass logic) | Kim bypass yetkisi alıyor? Belgelenmiş bir prosedür var mı? |
| (Response time) | Mevcut sistemin response time'ı ölçülmemiş — oscilloscope test gerek |

---

## Doldurma Notları (Bu örnek için)

- **SIL_Level, Category, ProofTestInterval_h alanları BOŞ** (AI dolduramaz)
- **Tüm satırlar Status=DRAFT_UNVERIFIED** (AI'ın yetki sınırı)
- **Verified_By BOŞ** — Hans Becker imza atınca APPROVED'a geçecek
- **SAFETY_ON_STANDARD_PLC bulguları ayrı bölümde** + RD14'e aktarıldı

---

*v1.0.0 — Bu örnek RD05 disiplinin somut hâli. AI sadece tespit eder, mühendis karar verir, müşteri imzalar.*
