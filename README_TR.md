# 🏭 AUTOMATION_FACTORY

[![Tests](https://github.com/Mehmet-Haydar/automation-factory/actions/workflows/tests.yml/badge.svg)](https://github.com/Mehmet-Haydar/automation-factory/actions/workflows/tests.yml)
[![SCL Gate](https://github.com/Mehmet-Haydar/automation-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/Mehmet-Haydar/automation-factory/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)

[English](README.md) · **Türkçe** · [Deutsch](README_DE.md)

> **AI destekli endüstriyel PLC programlama çerçevesi.** Eski PLC kodu (S5/S7/AB/CODESYS) veya greenfield brief → standart 14 Maddelik Ham Veri Paketi → endüstri standardında AI üretimi SCL kodu.

![Workbench kokpiti](docs/img/demo/01_workbench_full.png)
*7 kapılı hat: AI 14 maddelik gereksinim paketini taslaklar, mühendis önemli yerlerde inceler ve imzalar, ardından S7-1500 için kütüphane-öncelikli SCL üretilir.*

**Sürüm:** v3.10.0 (HMI & mutabakat V2: onaylı kablolama codegen · Gate-3 mutabakat+waiver · doğrudan .s5d import)
**Platform:** Siemens TIA (S7-1200/1500, SCL) — birincil, saha hedefli. Allen-Bradley / Beckhoff / CODESYS: yalnızca analiz prompt'ları + platform matrisi (henüz doğrulanmış kod kütüphanesi yok).
**Dil:** Sistem EN. AI çıktıları (RD taslakları, sequence-FB yorumları) proje dilini izler (TR/EN/DE — proje hedef kartından seçilir); doğrulanmış kütüphane bloklarının yorumları İngilizce kalır.

> Bu çeviri bilgilendirme amaçlıdır; teknik referans olarak İngilizce [README.md](README.md) esastır.

---

## 👋 Dürüst not — bu nedir (ve ne değildir)

Ben bir **otomasyon mühendisiyim**, yazılımcı değil. Bunu öğrenirken,
**AI araçlarını yönlendirerek** kurdum — fikir verdim, denedim, yanıldım,
tekrar denedim. Python'u benim yönlendirmemle AI yazdı; benim koyduğum şey
**alan yargısı**: iyi bir mühendisin bir retrofit'e nasıl yaklaşması
gerektiği, neden *yanlış* bir kilidin *eksik* bir kilitten beter olduğu,
neden SIL'in asla tahmin edilemeyeceği, neden bakımcının SCL değil merdiven
okuduğu.

Yani bu **bitmiş bir ürün değil** ve öyle olduğunu **iddia etmiyorum**.
Uçtan uca **tek** bir gerçek, belgesiz S5 makinesinde kanıtlandı (eski bir
taşlama hattı, ~300 IO) — sıfır hatayla derlenen bir TIA projesi
ve tam 14 belgelik paket üretti. Bu bir *doğrulanmış çekirdek*, *satılan
araç* değil: üretimde güvenilmeden önce daha çok gerçek makine, canlı bir
PLCSIM koşusu ve bir pilot gerekiyor.

Bence asıl bakmaya değer olan **AI çıktısı değil, mimari** — kendi çıkarımını
**kanıtlayan** (eski bit-mantığını 128 rastgele vektörde tekrar oynatan) ve
halüsinasyon yerine **"bilmiyorum" diyen** deterministik bir doğrulama
katmanı. Bu disiplin — kendinden emin çöp yerine dürüstlük — işin özü, ve
modelden değil sahadan geliyor.

Herhangi bir kısmı işine yararsa, al kullan. Geri bildirim ve düzeltmeler
memnuniyetle karşılanır.

---

## 🎯 Bu araç size uygun mu?

Bir öğleden sonranızı yatırmadan önce dürüst kapsam:

**Uygun, eğer…**
- **Hedefiniz** Siemens **S7-1200/1500 (TIA Portal)** ise — üretilen SCL kodu `REGION` sözdizimi ve optimize blok erişimi kullanır.
- Eski kodu **metin kaynağı** olarak verebiliyorsanız: AWL/STL/SCL export'ları, sembol tabloları, PDF listeleri. `.s7p`/`.zap` proje arşivleri **doğrudan okunmaz** — önce SIMATIC Manager / TIA'dan kaynak export'u alın (GUI adımları gösterir).
- IT politikanız **bulut AI API'lerine** izin veriyorsa (Anthropic / Google / OpenAI / DeepSeek). Yerleşik veri sınıflandırma koruması *neyin* dışarı çıkacağını denetler; henüz offline model modu yoktur.
- **Belgelenmiş, denetlenebilir** bir akış istiyorsanız (14 maddelik Ham Veri Paketi, gate imzaları, EU AI Act karar kaydı) — tek atımlık kod üreteci değil.

**Henüz uygun değil, eğer…**
- Hedef donanım **S7-300/400 classic** kalacaksa — üretilen bloklar klasik CPU'larda derlenmez.
- Tamamen **offline / air-gapped** çalışıyorsanız — yerel model desteği yol haritasında, henüz yayında değil.
- Her yerde tek tık TIA import bekliyorsanız: Openness doğrudan yolu TIA Portal V19–V21 + `pythonnet` + *Siemens TIA Openness* Windows grubu ister. Yoksa GUI manuel SCL import adımlarını sunar.
- Gate 6 simülasyonu **PLCSIM Advanced** (ayrı Siemens lisansı) gerektirir; yoksa manuel test beyanı imzalarsınız.
- 10 dakikada kod lazımsa: gate'li akış (analiz → mühendis incelemesi → imza → kod üretimi) gerçek bir retrofit'te yaklaşık **yarım iş günü** sürer — denetlenebilir sonucun bedeli budur.

---

## ⚡ Hızlı Başlangıç

> 🎯 **Şablon olarak mı kullanacaksınız?** GitHub sayfasının üstündeki **"Use this template"** düğmesiyle kendi kopyanızı oluşturun, sonra aşağıdaki adımları yeni repo'nuzda izleyin.

### 1. Kurulum

Gerekli tüm araçlar + Python + AI servisleri için: **[INSTALLATION.md](INSTALLATION.md)**

> **En hızlı yol (Windows):** Python 3.10+ kur → bu repo'yu aç →
> **`install.bat`**'e bir kez çift tıkla (ortamı kurar) → sonrasında hep
> **`start.bat`** (anında açılır, hiçbir şey kurmaz).

Özet:
```bash
# 1. Git, Python 3.10+, VS Code/Cursor kurun (ayrıntılar INSTALLATION.md'de)

# 2. Çalışma alanını oluşturun
mkdir D:\automation_workspace
cd D:\automation_workspace

# 3. Fabrikayı klonlayın
git clone https://github.com/Mehmet-Haydar/automation-factory.git

# 4. Python bağımlılıklarını kurun
cd automation-factory
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows
pip install -r requirements.txt

# 5. Test edin
python 05_SCRIPTS/script_project_init.py --help
```

#### Desteklenen AI sağlayıcıları

Tek bir sağlayıcıya **bağlı değilsiniz**. Aşağıdaki anahtarlardan istediğinizi
**Settings → sağlayıcı kartlarına** ekleyin (OS keystore'da saklanır) ve
görevleri sağlayıcıya göre yönlendirin:

| Sağlayıcı | En iyi olduğu iş (varsayılan yönlendirme) | Anahtar alma | Maliyet notu |
|-----------|-------------------------------------------|--------------|--------------|
| **Anthropic Claude** | SCL üretimi, kod analizi, güvenlik incelemesi | [console.anthropic.com](https://console.anthropic.com) | ücretli API |
| **Google Gemini** | PDF/P&ID ön-analizi, fotoğraflar, çeviri | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | **ücretsiz katman çoğu retrofit ön-analizi için yeterli** |
| **DeepSeek** | düşük maliyetli template kodu (yalnızca PUBLIC projeler) | [platform.deepseek.com](https://platform.deepseek.com) | çok düşük maliyet |
| **OpenAI** | genel alternatif | [platform.openai.com](https://platform.openai.com) | ücretli API |

Başlamak için tek anahtar yeterli — **Gemini'nin ücretsiz katmanıyla** tüm
retrofit ön-analiz hattını sıfır maliyetle deneyebilirsiniz. Görev→sağlayıcı
yönlendirmesi Settings'ten yapılandırılabilir (ör. PDF'leri Gemini okur,
SCL'yi Claude yazar).

### 2. İlk Müşteri Projenizi Oluşturun

```bash
# Müşteri klasörünü fabrikanın DIŞINDA oluşturun
mkdir D:\automation_workspace\customer_projects

# Yeni proje başlatın
python 05_SCRIPTS/script_project_init.py \
  --name "TestProject_2026" \
  --type retrofit \
  --customer "Test Customer GmbH" \
  --output "D:\automation_workspace\customer_projects" \
  --output-lang DE
```

Sonuç: `D:\automation_workspace\customer_projects\TestProject_2026\` oluşur — **fabrikaya dokunulmaz**.

---

## 📐 Klasör Yapısı (Önerilen)

```
D:\automation_workspace\                    ← Çalışma alanı kökü
│
├── AUTOMATION_FACTORY\                     ← Bu repo (GitHub'da public)
│   ├── 01_GLOBAL_STANDARDS\               ← Kurallar (NAMING, DATA_CLASS, LANG, ...)
│   ├── 02_PROJECT_TYPES\                 ← Retrofit + Greenfield rehberleri
│   ├── 03_DOMAIN_TOOLS\                  ← HMI/Safety/Sürücü domain standartları
│   ├── 04_AI_PROMPTS\                      ← AI prompt kütüphanesi
│   ├── 05_SCRIPTS\                         ← Python araçları + GUI
│   ├── 06_KNOWLEDGE_BASE\                  ← Tuzaklar + saha dersleri
│   ├── 07_PROJECT_TEMPLATE\                ← Yeni proje iskelet şablonu
│   ├── 08_METADATA_INPUT\                  ← JSON doğrulama şemaları
│   ├── 09_HARDWARE_LIBRARY\               ← Sürücü + IO modül teknik kartları
│   ├── docs\                               ← Geliştirici notları
│   └── examples\                           ← SENTETİK demo proje (eğitim amaçlı)
│       └── Kunde_Mueller_Conveyor_Retrofit\   ← Kurgusal Alman müşteri
│
└── customer_projects\                      ← GERÇEK müşteri projeleri (fabrikanın DIŞINDA!)
    ├── CustomerA_Conveyor_2026\               ← Asla GitHub'a gitmez
    └── ...
```

**Kritik ayrım:**
- `examples/` = sentetik demo (herkese açık) — fabrikanın parçası
- `customer_projects/` = gerçek müşteri verisi (🟠 CONFIDENTIAL) — **fabrikadan ayrı**

---

## 🎯 14 Maddelik Ham Veri Paketi

Her projede doldurulan 14 standart doküman:

| RD | Ad | İçerik |
|----|----|--------|
| 01 | IO Listesi | Fiziksel giriş/çıkış sinyalleri |
| 02 | Veri Sözlüğü | İç değişkenler (DB/UDT/marker) |
| 03 | Akış Şeması | Sequence/SFC + Mermaid diyagramı |
| 04 | Modlar | OMAC PackML uyumlu |
| 05 | **Safety** ⚠️ | F-FB + SIL/PLr (sertifikalı mühendis onayı zorunlu) |
| 06 | Motion | PLCopen Motion v2.0 |
| 07 | Zamanlama | Timer/watchdog'lar |
| 08 | Alarmlar | ISA-18.2 çok dilli |
| 09 | Haberleşme | PROFINET/EtherCAT/Modbus/OPC UA |
| 10 | FB Spek | Yeniden kullanılabilir fonksiyon blokları |
| 11 | HMI | ISA-101 ekranlar + tag'ler |
| 12 | Kullanım Senaryoları | FAT/SAT kaynağı |
| 13 | Legacy Açıklama | Eski kodun satır satır anlamı (retrofit) |
| 14 | Modernizasyon | Anti-pattern + karar matrisi (retrofit) |

---

## 🔄 7 Kapılı Hat (7-Gate Pipeline)

```
Gate 1 KEŞİF              (müşteri brief'i + makine envanteri)
  └─ Retrofit Ön-Analiz (opsiyonel): Gemini _raw/ çizimleri, fotoğrafları,
     EPLAN PDF'leri, eski kodu okur → Gate 3 incelemesi için RD taslakları üretir
Gate 2 ÇIKARIM            (14 RD'nin AI destekli üretimi)
Gate 3 İNSAN İNCELEMESİ   (mühendis incelemesi, #UNKNOWN'ların doldurulması)
Gate 4 DOĞRULAMA          (script_consistency_check.py)
Gate 5 KOD ÜRETİMİ        (AI üretimi SCL kodu)
Gate 6 SİMÜLASYON         (offline test ortamı)
Gate 7 FAT/SAT            (fabrika + saha kabul testleri)
```

### Retrofit Ön-Analizi (`_raw/` klasörü)

Retrofit projelerinde, Gate 1'e başlamadan önce eski dokümanları `_raw/` klasörüne bırakın:

```
proje/
  _raw/
    drawings/     ← EPLAN PDF'leri, P&ID'ler, elektrik şemaları
    photos/       ← pano fotoğrafları, etiket görüntüleri
    docs/         ← kılavuzlar, teknik şartnameler
    legacy_code/  ← eski SCL/AWL/STL/metin dosyaları — veya PDF çıktıları
                    (ör. "S5/S7 for Windows" export'ları)
```

Eski kod **PDF'leri** önce metne çevrilir (pdfplumber; taranmış PDF'ler
onay-kapılı Gemini Vision OCR'a düşer) ve analizden önce mühendis
tarafından **incelenip onaylanmalıdır** — O↔0 gibi OCR karışıklıkları
adresleri sessizce bozar.

**Hangi eski proje dosyaları doğrudan çalışır?** (tipik STEP5 arşivi:
`4711st.s5d`, `4711Z0.SEQ`, `*.INI`)

| Dosya | Nedir | Doğrudan kullanılır mı? |
|-------|-------|--------------------------|
| `.SEQ` | STEP5 sembol tablosu (Zuordnungsliste) — tag + açıklama | ✅ Evet — olduğu gibi bırakın; ham IO listesinin TA KENDİSİ |
| `.awl` / `.stl` / `.txt` / `.src` | AWL/STL metin listesi | ✅ Evet |
| Listing'in PDF çıktısı | metin veya tarama | ✅ Evet (çıkarma + inceleme adımıyla) |
| `.s5d` / `.s7p` | **Binary** STEP5/STEP7 programı (MC5 kodu) | ❌ Hayır — araç bunu algılar ve önce **S5/S7 for Windows** veya STEP5 ile AWL listesi (metin ya da PDF) export etmenizi söyler |

Yani: sembol tablosu arşivden doğrudan gelir; program *mantığı* için
S5/S7 for Windows'tan tek bir export adımı yine gerekir — bu bir geçici
çözüm değil, sağlıklı yolun kendisidir.

GUI, Gate 1'de **"Start Retrofit Pre-Analysis"** düğmesi gösterir. Onay
diyaloğundan sonra 6 adımlık arka plan AI zinciri çalışır:
1. **Gemini Vision** çizim ve fotoğrafları okur → IO sinyallerini çıkarır
2. **Claude** eski kodu analiz eder → fonksiyonel blokları belirler
3–6. **Claude** ikisini RD taslaklarına birleştirir — **RD01** (IO listesi),
   **RD02** (veri sözlüğü), **RD03** (adım dizisi + Mermaid), **RD13**
   (satır açıklama) — doğrudan `metadata/` içine `DRAFT_UNVERIFIED`
   olarak yazılır (onaylı RD'ler asla ezilmez; değiştirilen taslaklar
   `metadata/_history/`'ye yedeklenir).

Mühendis bu taslakları **Gate 3'te (İnsan İncelemesi)** inceleyip onaylar.
Onaydan sonra **Assemble Program**, programı *kütüphane-öncelikli* kurar:
cihaz FB'leri doğrulanmış kütüphaneden **aynen** kopyalanır
(`REPORTS/ASSEMBLY_REPORT.md` içinde SHA-256 kanıtı), instance DB'ler +
OB1 saha-sinyali bağlamalarıyla üretilir ve her şey doğrulayıcı +
sözleşme kapılarından geçer. Eşleşmeyen cihazlar açık bir **#UNKNOWN**
listesine düşer — asla sessizce kaybolmaz. AI'nın ürettiği tek kod
parçası, incelenmiş RD03'ten türetilen proje sequence FB'sidir.

Son olarak **Send to TIA** (Openness, TIA V19/V20/V21 + pythonnet)
kaynakları içe aktarır ve **compile ön-kontrolü** koşar — temiz derleme
etiketi `AUTO_VERIFIED_compile | PENDING_PLCSIM_VERIFY` seviyesine
yükseltir. Makinede TIA yoksa **Export TIA** kopyala-yapıştır import
klasörü üretir.

**Tam olarak ne çıkar?** TIA Portal **harici kaynak dosyaları**:
`.scl` (FB'ler, OB1) + `.db` (instance DB'ler) + IEC tag tablosu — yani
TIA'nın kendisinin kullandığı metin kaynakları. Hazır bir `.ap21` proje
dosyası **değil**: o konteyneri yalnızca TIA Portal'ın kendisi üretebilir
— Openness yolunun TIA'yı kullandığı iş tam da budur (tek tık: *sizin*
`.apXX` projenize import + compile). Kod çıktısında Markdown yoktur;
`.md` yalnızca RD dokümantasyon paketi içindir.

**İnsanda kalanlar (eksik değil, bilinçli tasarım):**
- **RD05 / fonksiyonel güvenlik** — AI, mühendis onayı verilse bile
  *asla* güvenlik mantığı yazmaz veya SIL/PLr tahmin etmez. Yalnızca
  eski kodda bulduğu güvenlik sinyallerini *tespit edip raporlar*.
  F-programlarını TIA Safety'de (sertifikalı) mühendis yazar.
- **PLCSIM davranışsal koşum** — compile ön-kontrolü kodun *derlendiğini*
  kanıtlar; *mantığın doğruluğunu* kanıtlamaz. PLCSIM'e download tek tık
  (gerçek PLC'ye download donanımsal olarak bloklu), ama test
  senaryolarını watch table'da hâlâ mühendis koşar. Otomatik davranış
  test motoru yol haritasındaki sıradaki maddedir.
- **#UNKNOWN / TODO bağlantıları** — assembler yalnızca *emin olduğunu*
  bağlar (feedback'ler, overload'lar, ana çıkışlar). Belirsiz olan her
  şey `ASSEMBLY_REPORT.md` içinde mühendise listelenir — tahmin edilmiş
  IO adresi saha tehlikesidir, bu yüzden araç tahmin etmeyi reddeder.

Tam tıklama yolu: **[docs/USER_GUIDE_RETROFIT.md](docs/USER_GUIDE_RETROFIT.md)**

> **Veri gizliliği (dikkatle okuyun):** Eski **kod metni** anonimleştirilir —
> bilinen müşteri alanları (ad, proje no, mühendis) ve PII regex desenleri
> (e-posta, telefon, adres) metin bulut AI'ya gönderilmeden önce değiştirilir.
> **Görseller, çizimler ve PDF'ler otomatik anonimleştirilMEZ:** olduğu gibi
> yüklenir ve yalnızca her çağrıdan hemen sonra Google sunucularından *silinir*.
> Ön-analizi çalıştırmadan önce logoları, antet bloklarını ve isimleri
> çizim/fotoğraflardan elle temizlemelisiniz. PII regex'leri Alman formatı
> iletişim verisine ayarlıdır — diğer ülkeler için kapsamı doğrulayın.
> CONFIDENTIAL projeler açık mühendis onayı ister (soft-block, loglanır);
> RESTRICTED veri asla gönderilmez.

Ayrıntı: [PIPELINE_CODE_REWRITE.md](docs/PIPELINE_CODE_REWRITE.md)

---

## 📚 Dokümantasyon

| Dosya | Amaç |
|-------|------|
| **[INSTALLATION.md](INSTALLATION.md)** | Kurulum + gerekli araçlar (Python/Git/IDE/AI) |
| **[docs/USER_GUIDE_RETROFIT.md](docs/USER_GUIDE_RETROFIT.md)** | Retrofit uçtan uca tıklama yolu (eski kod → TIA programı) |
| **[docs/USER_GUIDE_BIG_PICTURE.md](docs/USER_GUIDE_BIG_PICTURE.md)** | Kapsamlı kullanım rehberi |
| **[docs/PROJECT_VISION.md](docs/PROJECT_VISION.md)** | Vizyon + felsefe |
| **[CHANGELOG.md](CHANGELOG.md)** | Sürüm geçmişi |
| `examples/Kunde_Mueller_Conveyor_Retrofit/README.md` | Sentetik örnek proje |

---

## 🎓 Örnek Proje

Fabrikayı somut bir örnekle görmek için:

📂 **[`examples/Kunde_Mueller_Conveyor_Retrofit/`](examples/Kunde_Mueller_Conveyor_Retrofit/)**

İçerik:
- Sentetik Alman müşteri (Kunde Müller GmbH) 1995 S7-300 retrofit senaryosu
- 14 RD'nin tamamı dolu (RD05 Safety kritik bulgu örneği dahil)
- Eski AWL kod örneği → modern SCL kod çıktısı (Almanca yorumlu)
- Müşteri sunumu için modernizasyon karar matrisi (€60K)

---

## 🛡️ Veri Sınıflandırma + Güvenlik

| Sınıf | Renk | Örnek | AI Politikası |
|-------|------|-------|---------------|
| PUBLIC | 🟢 | Bu fabrika, desen örnekleri | Herhangi bir AI |
| INTERNAL | 🟡 | Şirket içi standartlar | Cursor/Claude Team+ |
| **CONFIDENTIAL** | 🟠 | **Müşteri kodu** | **Self-hosted / Enterprise AI ZORUNLU** |
| RESTRICTED | 🔴 | ITAR/EAR, savunma | Air-gapped |

Ayrıntı: `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`

**⚠️ Müşteri kodu public AI API'lerine GÖNDERİLEMEZ.** Yerleşik
`data_classification_guard` bunu her AI çağrısında zorlar. CONFIDENTIAL
projeler self-hosted veya enterprise-tier AI sağlayıcı gerektirir.

---

## ⚖️ AI Sorumluluk Reddi

> **AUTOMATION_FACTORY, nitelikli bir mühendise yardım etmek için kod ve doküman üretir.
> Mühendislik muhakemesinin, sertifikasyonun veya insan onayının yerine GEÇMEZ.**
>
> Tam endüstriyel kullanım feragatnamesi (garanti yok, doğrulama
> yükümlülüğü, sorumluluk): **[DISCLAIMER.md](DISCLAIMER.md)**

| Konu | Beyan |
|------|-------|
| **Çıktı durumu** | Doğrulama katmanları: `AUTO_VERIFIED_structural` (yalnız yapısal kontrol) → `AUTO_VERIFIED_compile` (Openness ön-kontrolüyle TIA'da temiz derlendi) → PLCSIM davranışsal test (Gate 6, hâlâ insan eliyle). Son katmanın altındaki her şey **TASLAK** — sahaya hazır değil. |
| **Safety** | AI çıktısı, Safety-Instrumented Systems (SIS) için **asla** yetkili kaynak değildir. SIL/PLr ataması, F-blok seçimi ve güvenlik doğrulaması sertifikalı güvenlik mühendisi gerektirir (TÜV, FS Engineer). |
| **Sorumluluk** | AI üretimi kodu içe aktaran, değiştiren veya onaylayan mühendis, ortaya çıkan PLC programının tüm mesleki ve hukuki sorumluluğunu taşır. Bu yazılımın yazarları, AI üretimi çıktıların kullanımından doğan üretim kazaları, ekipman hasarı veya yaralanmalar için sorumluluk kabul etmez. |
| **Veri gizliliği** | Yerleşik `data_classification_guard`, CONFIDENTIAL/RESTRICTED proje verisinin public AI API'lerine ulaşmasını engeller. Veri sınıflandırmasını doğrulamak kullanıcının sorumluluğundadır. |
| **API anahtarları** | API anahtarları OS anahtar kasasında saklanır (Windows Credential Vault / macOS Keychain). Bu yazılımın işlettiği hiçbir sunucuya gönderilmez. |

---

## 🤖 AI Disiplini

Fabrikanın temel kuralları:

1. **AI hızlandırır, mühendis karar verir, müşteri imzalar**
2. **AI ASLA SIL/PLr seviyesi tahmin etmez** — RD05 Safety = DRAFT_UNVERIFIED, sertifikalı mühendis onayı zorunlu
3. **Müşteri verisi disiplini** — sınıflandırma kapısı her API çağrısında; CONFIDENTIAL veri public sağlayıcılara bloklu
4. **#UNKNOWN'lar asla atlanmaz** — AI çıktısında insan incelemesi bekleyen alanlar zorunludur
5. **Yalnızca doğrudan API** — pano-aktarımı yok, IDE proxy yok; tüm AI çağrıları anahtar-kasalı `AIClient` üzerinden

---

## 📊 Sürüm Yol Haritası

| Sürüm | Durum | İçerik |
|-------|-------|--------|
| v3.0.0-alpha | ✅ TAMAM | Sistem dokümanları, 14 Maddelik Paket, AI prompt'ları, rehberler |
| v3.1.0-alpha | ✅ YAYINDA | Workbench IDE, TIA Send diyaloğu, kütüphane tohumu |
| v3.2.0 | ✅ YAYINDA | Sabit-FB Kütüphanesi + Kabul Kapısı (18 blok) + CI + doğrudan API + keyring |
| **v3.3.0** | ✅ YAYINDA | Multi-AI Team — sağlayıcı bazlı ayarlar, görev yönlendirme, Retrofit Ön-Analiz hattı |
| **v3.4.0** | ✅ YAYINDA | PDF/metin eski kod girişi + OCR incelemesi, 6 adımlı ön-analiz → RD taslakları, kütüphane-öncelikli **Assemble Program**, **TIA compile ön-kontrolü** (`AUTO_VERIFIED_compile`) · **Flowchart Görünümü** — adım tablosundan türetilen RD03 diyagramı (offline mermaid), deterministik etki kontrollü değişiklik-talebi sohbeti, gate bayatlama uyarısı, İngilizce status enum'ları |
| **v3.5.0** | ✅ YAYINDA | v3.4.x saha düzeltmeleri (canlı doğrulanmış tag-table import, Send-to-TIA canlı adım görünümü + mühendis onaylı düzeltme asistanı) · **UX yenilemesi** — PROJECT/LIBRARY çalışma alanları, yönlendirilmiş onboarding, gate durumu için tek doğruluk kaynağı, dürüst butonlar, native dosya seçiciler |
| **v3.6.0** | ✅ YAYINDA | **Version Compare** — eski arşiv versiyonları arası deterministik diff (`_Versionen/` ↔ `_aktiv/`): S5 sembol-tablosu diff'i, metin diff'i, dürüst binary notları · AI değişiklik hipotezleri (`DRAFT_UNVERIFIED`, tam C4/S-20/audit güvenlik zinciri) |
| **v3.7.0** | ✅ YAYINDA | **SAT v2** (IEC 62381 hizalı, gerçek SAT ≠ FAT) · **i18n DE/EN/TR** protokol motoru · **IEC 62443 / NIS2** siber güvenlik bölümü · **IEC 62682** alarm rasyonalizasyon sütunları · **SISTEMA** yardımcı (hazırlık listesi + mühendis beyanı CRUD) · **CE wesentliche Veränderung** değerlendirmesi (DE/EN/TR) · PDF çıktısı · pasif gece TIA derleme CI (Kademe 2) |
| **v3.7.1** | ✅ YAYINDA | Ön-final denetim düzeltmeleri: protokol üretimi sonrası klasör açma, GUI log'unda proje yolu sızıntısı, CE PDF `<br>` kaçış hatası, SISTEMA hazırlık dili seçici |
| **v3.8.0** | ✅ YAYINDA | **RAG-KB hattı** (çevrimdışı-öncelikli BM25 + isteğe bağlı anlamsal): KB Giriş Sözleşmesi, `rag/ingest.py` + `rag/retrieve.py`, datasheet ingest, güvenlik uyarı zinciri (kırmızı banner + onay), OB1 vendor bağlam enjeksiyonu · **PLC doğrulama orkestratörü** (L1 yapısal + L2 mantık, hash-önbellek, oto-düzelt döngüsü) · 1378 test |
| **v3.8.1** | ✅ YAYINDA | Güvenlik sertleştirmesi (AUDIT-001..005: yol-geçişi, rıza zinciri, denetim-log, IP sızıntısı, PII) · `PROJECT_STATE.json` thread-safe yazma (`threading.Lock`) · 1383 test |
| **v3.9.0** | ✅ YAYINDA | Public-release hazırlığı — saha-uygunluk denetim düzeltmeleri + **iki-vites akışı** (tek-tık tam analiz, risk-bazlı 14→3 onay, delta assembly / değişim yönetimi) · 1584+ test |
| **v3.10.0** | ✅ YAYINDA | **HMI & Mutabakat V2** — rol-bazlı RD yerleşimi, RD11/RD08 grid editörleri, Gate-3 mutabakat+waiver, onaylı kablolama codegen, doğrudan .s5d import · bağımsız çok-ajanlı denetim geçişi (gizlilik, ölü-kod, hijyen) |
| v4.0.0 | Planlandı | PLCSIM davranışsal koşum (Kademe 3 / S-28), motion/comm kod üretimi, ilk gerçek pilot, public release cilası |

> **Doğrulama durumu:** Üretilen/derlenmiş SCL `AUTO_VERIFIED_structural | PENDING_TIA_VERIFY` ile başlar. Makinede TIA V19/V20/V21 + pythonnet varsa **Send to TIA** gerçek bir Openness **compile ön-kontrolü** koşar; temiz derleme etiketi `AUTO_VERIFIED_compile | PENDING_PLCSIM_VERIFY` yapar. PLCSIM **davranışsal** doğrulama ve gerçek bir pilot proje hâlâ **bekliyor** — Gate 6 geçilene kadar AI üretimi kodu gözden geçirilmiş taslak sayın, asla sahaya hazır değil.

---

## 🤝 Katkı

Fabrika aktif geliştirme altındadır. Geliştirme kurulumu, test/CI gereksinimleri
ve commit kuralları için **[CONTRIBUTING.md](CONTRIBUTING.md)** ve
**[Davranış Kuralları](CODE_OF_CONDUCT.md)** dosyalarına bakın.

> **Asla gerçek müşteri verisi veya API anahtarı commit etmeyin.** Tüm
> örnekler sentetik olmalıdır.

GitHub Issues: https://github.com/Mehmet-Haydar/automation-factory/issues ·
Güvenlik: [SECURITY.md](SECURITY.md)

---

## 📄 Lisans

Bkz. [LICENSE](LICENSE). Müşteri projelerinde paylaşırken:
`01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`.

---

*Endüstriyel otomasyon mühendisliği için AI destekli fabrika. Geliştiren: Mehmet Haydar.*
