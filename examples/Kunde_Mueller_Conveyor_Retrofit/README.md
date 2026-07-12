---
title: Kunde Müller Conveyor Retrofit — Örnek Proje
last_validated: 2026-05
status: ACTIVE
---

# Kunde Müller Conveyor Retrofit — Örnek Proje

> ⚠️ **Bu sentetik bir örnek projedir.** Müşteri verisi değil — AUTOMATION_FACTORY'nin nasıl çalıştığını göstermek için tasarlanmış uçtan uca demo.

---

## Proje Senaryosu

**Müşteri:** Kunde Müller GmbH (Almanya, Düsseldorf)
**Makine:** 1995 yılında kurulmuş eski konveyör hattı
**Eski platform:** Siemens S7-300 (CPU 315-2DP, STEP 7 V5.5 Classic)
**Yeni platform:** Siemens S7-1500F (CPU 1515F-2 PN, TIA Portal V18)
**Proje türü:** Retrofit
**Dil:** Alman müşteri → kod yorumu + HMI = DE
**Veri sınıfı:** 🟠 CONFIDENTIAL

**Senaryo:**
- Müşteri eski PLC'sini yenilemek istiyor (yedek parça yok)
- E-Stop standart Q çıkışından sürülüyor (F-PLC yok) → SAFETY CRITICAL bulgu
- Konveyör motor + paletizör servo + 2 light curtain
- HMI panel yenilenecek (eski WinCC Classic → TIA WinCC Unified)

---

## Klasör Yapısı

```
Kunde_Mueller_Conveyor_Retrofit/
├── README.md                          ← bu dosya
├── PROJECT_MAESTRO.md                 ← proje orkestratör
├── PROJECT_STATE.json                 ← makine-okunabilir durum
│
├── _input/                            ← eski kod (synthetic)
│   ├── _parsed.md                     ← platform parser çıktısı
│   ├── old_code_snippet.awl           ← örnek AWL kod parçası
│   └── operator_manual_excerpt.md     ← operatör notları
│
├── metadata/                          ← 14-Point Raw Data Pack (doldurulmuş)
│   ├── RD01_IO_List.md             ✅ ÖRNEK
│   ├── RD02_DataDict.md               ✅ ÖRNEK
│   ├── RD03_Flowchart.md              (yer tutucu)
│   ├── RD04_Mode.md                   ✅ ÖRNEK
│   ├── RD05_Safety_DRAFT_UNVERIFIED.md ✅ ÖRNEK (kritik bulgu)
│   ├── RD06_Motion.md                 (yer tutucu)
│   ├── RD07_Timing.md                 (yer tutucu)
│   ├── RD08_Alarm.md                  ✅ ÖRNEK
│   ├── RD09_Comms.md                  (yer tutucu)
│   ├── RD10_FBSpec.md                 ✅ ÖRNEK
│   ├── RD11_HMI.md                    (yer tutucu)
│   ├── RD12_UseCase.md                (yer tutucu)
│   ├── RD13_Annotation.md             ✅ ÖRNEK
│   └── RD14_Modernization.md          ✅ ÖRNEK (karar matrisi)
│
└── _output/
    └── FB_Motor_Conveyor.scl          ✅ Gate-5 örnek SCL (AUTO_VERIFIED_structural | PENDING_TIA_VERIFY)
```

> ⚠️ **Bu sentetik bir örnektir.** Metadata (RD*) dosyaları elle/AI ile hazırlanmış
> taslaklardır; gerçek bir müşteri projesi değildir ve insan onayından geçmemiştir.
> **Gate 5 çıktısı (`_output/FB_Motor_Conveyor.scl`) yapısal olarak doğrulanmıştır
> (`AUTO_VERIFIED_structural`) ancak `PENDING_TIA_VERIFY`** — TIA Portal derleme +
> PLCSIM koşumu YAPILMAMIŞTIR. Üretime alınmadan önce bir mühendis derleyip
> simüle etmelidir. Örnek, Gate 1–3 + örnek bir Gate 5 SCL taslağını gösterir.

---

## Nasıl İncelenir?

### 1. PROJECT_MAESTRO.md
Proje genel durumu ve referansları gösteren ana belge.

### 2. _input/_parsed.md
Eski S7-300 koddan platform parser AI'ın ürettiği proje özeti. **Bu factory'nin "ilk anlama" çıktısı.**

### 3. metadata/RD01_IO_List.md
47 sinyal — eski mutlak adresler **yeni naming standardına** dönüştürülmüş.

### 4. metadata/RD05_Safety_DRAFT_UNVERIFIED.md ⚠️
**KRİTİK BULGU:** Standart PLC'de E-Stop tespit edildi. AI bu bulguyu RD14'e CRITICAL olarak aktardı.

### 5. metadata/RD14_Modernization.md
**Karar matrisi:** Retrofit vs Greenfield vs Hybrid önerisi. SAFETY için F-PLC migrasyonu zorunlu.

### 6. _output/FB_Motor_Conveyor.scl
Gate 5 örnek SCL çıktısı — RD10 FBSpec'ten türetilmiş, FB_Motor_DOL kütüphane
pattern'ine dayanan örnek kod (Almanca yorumlu). **Etiket:
`AUTO_VERIFIED_structural | PENDING_TIA_VERIFY`** — yapısal gate geçti, ama TIA
derleme + PLCSIM YAPILMADI; üretime almadan önce mühendis doğrulaması şart.

---

## Pipeline'da Hangi Aşamadayız?

```
Gate 1 KEŞIF              ✅ Müşteri brief alındı (sentetik)
Gate 2 ÇIKARTIM           ✅ AI tüm 14 RD taslağını üretti (sentetik)
Gate 3 HUMAN REVIEW       🔵 İnceleme yapılıyor (RD05 safety mühendis bekliyor)
Gate 4 VALIDATION         ⏸ RD05 onaylanınca
Gate 5 KOD ÜRETİMİ        🟡 Örnek SCL üretildi — AUTO_VERIFIED_structural | PENDING_TIA_VERIFY
Gate 6 SİMÜLASYON         ⏸ Gate 6 (TIA compile + PLCSIM) henüz uygulanmadı
Gate 7 FAT/SAT            ⏸
```

---

## Tespit Edilen Bulgular

| ID | Severity | Kategori | Özet |
|----|----------|----------|------|
| FND001 | CRITICAL | SAFETY | Standart PLC'de E-Stop — F-PLC migrasyonu zorunlu |
| FND002 | MAJOR | NAMING | 47 mutlak adres → semantik tag |
| FND003 | MAJOR | STRUCTURE | Tüm lojik OB1'de — modüler FB yapısı |
| FND004 | MAJOR | OBSOLETE_PLATFORM | S7-300 desteği biten platform |
| FND005 | MINOR | MAINTAINABILITY | %30 yorumsuz kod |
| FND006 | MINOR | ALARM | FC40 32 alarm bit, ISA-18.2 dışı |
| FND007 | MINOR | HMI | WinCC Classic, ISA-101 dışı |
| FND008 | **CRITICAL** | SAFETY | M50.0 Wartungs-Bypass E-Stop'u devre dışı bırakıyor (FC10 NW5) |
| FND009 | **CRITICAL** | SAFETY | E-Stop yedekliliği sahte: NW5/NW6 asimetrisi |

**Toplam çaba tahmini:** ~192 saat + donanım maliyeti (F-PLC ~€18K)

**Öneri:** GREENFIELD recommended — 3 CRITICAL bulgu (FND001/008/009) F-PLC migrasyonu ile tek seferde çözülür; donanım zaten yenileniyor.

---

## Regenerate / Verify this demo (deterministic, no API key)

> Bu bölüm tamamen **deterministik** (AI gerektirmeyen) adımları listeler. Aşağıdaki
> komutlar **API anahtarı olmadan** çalışır ve fresh bir kullanıcı bu örneği uçtan
> uca doğrulayabilir. AI gate'leri (Gate 1 KEŞIF / Gate 2 ÇIKARTIM / Gate 5 KOD
> ÜRETİMİ — Claude/Gemini ile üretim) **API anahtarı ister ve bu runbook'un dışındadır.**
>
> Komutlar repo kökünden (`automation-factory/`) çalıştırılır. Bir test venv
> varsayılır; yoksa: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
> Aşağıda `python` = o venv'in python'u.

### 1. Fresh bir iskelet projeyi scaffold et (init smoke-test)

```bash
python 05_SCRIPTS/script_project_init.py \
  --name TestRetrofit --type retrofit \
  --customer "Test Customer" --output /tmp/init_test --output-lang DE
```

Beklenen: exit 0, `metadata/` altında **14 RD şablonu** (`RD01..RD14`) + factory
referansları. (Bu, bu örneğin türetildiği iskeletin aynısıdır.)

### 2. Gate-4 naming consistency check (RD01 IO listesi)

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project examples/Kunde_Mueller_Conveyor_Retrofit \
  --check-naming \
  --io-file examples/Kunde_Mueller_Conveyor_Retrofit/metadata/RD01_IO_List.xlsx
```

Beklenen: exit **1** ve **bulgu listesi** — bu **tasarım gereğidir**. RD01 bir
Gate-3 `DRAFT`'tır ve **eski (legacy) isimlendirmeyi bilerek içerir**; checker
`GLOBAL_NAMING_STANDARD.md`'in `TYPE_LOC_NUM_FUNC` formatına uymayan tag'leri
raporlar (`PC_LOAD_001`, `VAL_V01_OUT`, `LIGHT_GREEN`, `ANALOG_*`, `F_I_EStop_*`
vb.). Bu tam olarak **FND002 (NAMING / MAJOR)** bulgusudur — retrofit/greenfield
migrasyonunda çözülür (bkz. `metadata/RD14_Modernization.md`). Standarda zaten uyan
`MOT_CV01_001_*` tag'leri temiz geçer. **Bu bulgular örneğin pedagojik içeriğidir;
"düzeltilmemelidir".**

### 3. Address conflict check (henüz TODO)

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project examples/Kunde_Mueller_Conveyor_Retrofit --check-addresses
```

Beklenen: exit 1 + "`--check-naming or --check-addresses required.`" — `--check-addresses`
bayrağı henüz **implement edilmemiş bir TODO**'dur (checker'ın `--help`'inde de
`(TODO)` olarak işaretli). Bu bir örnek-veri hatası değil, araç sınırlamasıdır.

### 4. IO-list MD ↔ XLSX round-trip

```bash
python - <<'PY'
import sys; sys.path.insert(0, "workbench/core")
import io_list_io as io
from pathlib import Path
md   = Path("examples/Kunde_Mueller_Conveyor_Retrofit/metadata/RD01_IO_List.md")
xlsx = Path("examples/Kunde_Mueller_Conveyor_Retrofit/metadata/RD01_IO_List.xlsx")
md_rows, fm = io.read_md(md)
x_rows,  _  = io.read_xlsx(xlsx)
assert [r.tag for r in md_rows] == [r.tag for r in x_rows], "MD/XLSX tag mismatch"
print(f"OK: {len(md_rows)} rows, MD and XLSX tags match")
PY
```

Beklenen: exit 0, `OK: 26 rows, MD and XLSX tags match`. (Örnek RD01 tablosu 26
gösterim satırı içerir + "…22 more signals…" yer tutucusu; gerçek listede 47 sinyal.)

### 5. Schema validator — kapsam notu

`05_SCRIPTS/dev/script_md_schema_validator.py` yalnızca `PROMPT_CODE_GEN` ve
`DOMAIN_REFERENCE` şemalarını bilir; **RD metadata (RAWDATA) şemaları bu deterministik
araçta kayıtlı değildir**, dolayısıyla bu örneğin `metadata/RD*.md` dosyaları bu
validator kapsamı dışındadır (bir örnek-veri hatası değil, araç kapsamıdır).

### 6. Tüm test paketi

```bash
python -m pytest -q
```

Beklenen: **725 passed, 1 skipped**.

---

## Bu Örnek Sayesinde Görebilecekleriniz

1. **AI extraction nasıl bir _parsed.md üretir** → `_input/_parsed.md`
2. **14-Point Pack nasıl görünür** → `metadata/RD*.md`
3. **Almanca/Türkçe/İngilizce multi-lang nasıl korunur** → her dosyada `(orig: ...)` formatı
4. **Safety neden insan onayı gerektirir** → `RD05_Safety_DRAFT_UNVERIFIED.md`
5. **Modernizasyon kararı nasıl verilir** → `RD14_Modernization.md` ModernizationDecision tablosu
6. **Gate 5 SCL çıktısı nasıl görünür** → `_output/FB_Motor_Conveyor.scl` (yapısal-doğrulanmış örnek)

> Not: Gate 6 (TIA derleme + PLCSIM) ve sonrası bu sentetik örneğe dahil değildir;
> Gate 5 SCL örneği `PENDING_TIA_VERIFY` etiketlidir (mühendis doğrulaması gerekir).

---

## Gerçek Müşteri Projesi vs Bu Örnek

| | Bu Örnek | Gerçek Proje |
|--|----------|--------------|
| Müşteri adı | "Kunde Müller GmbH" (uydurma) | Gerçek müşteri |
| Veriler | Sentetik (47 sinyal demo) | Yüzlerce/binlerce sinyal |
| Süre | Tek günde üretildi (factory demo) | 2-6 ay (proje complexity'sine göre) |
| Onaylar | İnsan onayı YOK (örnek) | Her gate'te insan onayı zorunlu |
| Safety | Demo amaçlı | Sertifikalı mühendis + TÜV süreci |

---

*Bu örnek factory'nin kapasitesini gösterir. Gerçek müşteri projeleri bu kalıba uyar ama her zaman insan mühendis denetiminde yürütülür.*
