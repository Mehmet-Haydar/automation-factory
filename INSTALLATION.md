---
title: AUTOMATION_FACTORY Installation Guide
version: 1.0.0
last_updated: 2026-05-30
status: ACTIVE
last_validated: 2026-05
---

# INSTALLATION.md — Setup + Required Tools Guide

> The single reference for all tools and installation steps needed to run AUTOMATION_FACTORY. Covers Windows / Linux / macOS.

---

## 1. Quick Start (Summary)

Install in this order:
1. **Git** (required — to clone the repository)
2. **Python 3.10+** (required — to run the scripts)
3. **An AI API key** (required — Anthropic, OpenAI, Google Gemini, or DeepSeek)
4. **VS Code** (optional — for editing; no AI IDE plugin required)
5. **TIA Portal** (for Siemens projects — optional)
6. **Studio 5000** (for Allen-Bradley projects — optional)

Details below.

---

## 2. Required Tools

### 2.1 Git (Version Control)

**Windows:**
- Download: https://git-scm.com/download/win
- Default options during setup are sufficient
- Verify after installation in PowerShell:
  ```powershell
  git --version
  # Expected: git version 2.40.x or higher
  ```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install git
git --version
```

**macOS:**
```bash
# With Homebrew (recommended)
brew install git
# Or: xcode-select --install
```

---

### 2.2 Python 3.10+ (For Scripts)

**Windows — Microsoft Store (FASTEST PATH):**
1. Press Win key → open "Microsoft Store"
2. Search: **"Python 3.12"**
3. Click "Install"
4. **CLOSE AND REOPEN** PowerShell
5. Verify:
   ```powershell
   python --version
   # Expected: Python 3.12.x
   pip --version
   ```

**Windows — python.org (alternative):**
1. Download: https://www.python.org/downloads/
2. Click "Download Python 3.12.x"
3. Run the installer
4. ⚠️ **CHECK "Add python.exe to PATH"** on the first screen — this is mandatory
5. Click "Install Now"
6. Reopen PowerShell and verify

**Linux:**
```bash
# Python 3 is available on most systems — check first:
python3 --version
# If < 3.10:
sudo apt install python3.12 python3-pip
```

**macOS:**
```bash
brew install python@3.12
python3 --version
```

---

### 2.3 Python Dependencies (requirements.txt)

> **Windows shortcut:** double-click **`install.bat`** once — it creates the
> `.venv` and installs everything below automatically. Afterwards launch with
> `start.bat`. The manual steps below are the equivalent for other platforms
> (or if you prefer doing it yourself).

After cloning the factory:

```bash
# Navigate to the factory folder
cd path/to/AUTOMATION_FACTORY

# Create a virtual environment (recommended)
python -m venv .venv

# Activate it
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**If you encounter errors:**
- "Permission denied" → run PowerShell as Administrator
- "SSL error" → your corporate network may require VPN/proxy configuration
- "Microsoft Visual C++ required" → needed for `lxml`; workaround: `pip install --only-binary=:all: -r requirements.txt`

#### Optional: Google Gemini (Retrofit Pre-Analysis)

To enable PDF/image analysis for retrofit projects, install the Gemini SDK and add your API key in Settings:

```bash
pip install google-genai
```

Then in the factory GUI: **Settings → Google Gemini card → paste your API key → Test → Save**.
If the key is set, the **Retrofit Pre-Analysis** button appears automatically in Gate 1 when files are present in the `_raw/` folder.

Get a Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). The free tier is sufficient for most retrofit pre-analyses.

---

### 2.4 Editor (optional — VS Code recommended)

AUTOMATION_FACTORY uses a built-in web GUI (`factory_web.py`) with direct AI API calls. No AI IDE plugin is required.

**VS Code:**
- Download: https://code.visualstudio.com
- Recommended extensions (editing only, not AI):
  - **Python** (Microsoft)
  - **YAML** (Red Hat) — for frontmatter
  - **Markdown All in One**
  - **GitLens**
  - **Mermaid Preview** (for RD03 diagrams)

> **Note:** Cursor and Claude Code are not required. All AI calls go through the `AIClient` layer in `factory_web.py`, which uses your API key stored in the OS keystore.

---

## 3. Optional Industry Tools

Depending on your target platform:

### 3.1 Siemens

**TIA Portal V18+:**
- Requires a customer license (obtain from Siemens; 21-day trial available)
- Download: https://support.industry.siemens.com → TIA Portal
- Version: V19, V20 or V21 (the direct "Send to TIA" bridge supports V19/V20/V21; V21 recommended)
- Add-ons:
  - **Openness API** (required for the direct Send-to-TIA path; install `pythonnet` in the factory venv)
  - **SCL editor**
  - **TIA Safety** (for F-PLC projects)
  - **PLCSIM Advanced** (for Gate 6 simulation — **separate paid Siemens license**; without it Gate 6 falls back to a signed manual-test declaration)

> **Direct Send-to-TIA prerequisites (all four, or the bridge stays
> `not configured` and the GUI offers manual SCL import instead):**
> 1. TIA Portal V19/V20/V21 installed on the same Windows machine
> 2. TIA **Openness** option installed
> 3. `pip install pythonnet` inside the factory venv
> 4. Your Windows user added to the **"Siemens TIA Openness"** local group
>    (Computer Management → Local Users and Groups → Groups → log off/on)
>
> No TIA at all? The factory still works end-to-end up to code generation —
> the generated `.scl` files import into any TIA via *External source files*.

**STEP 7 V5.6 (S7-300/400 Classic):**
- Needed to EXPORT legacy sources: `.s7p`/`.zap` project archives are **not
  read directly** by the factory — generate AWL sources + symbol table in
  SIMATIC Manager first and drop those into `_raw/legacy_code/`
- License required

### 3.2 Allen-Bradley (Rockwell)

**Studio 5000 Logix Designer V34+:**
- Requires Rockwell account + license
- Download: https://rockwellautomation.com → Studio 5000
- Add-ons:
  - **FactoryTalk View Studio** (for HMI)
  - **Emulate 5000** (simulation)

### 3.3 Beckhoff

**TwinCAT 3 XAE:**
- Free to download (engineering environment)
- Runtime: license required
- Download: https://beckhoff.com → TwinCAT 3

### 3.4 CODESYS

**CODESYS Development System V3.5:**
- Free (supports Beckhoff/Wago/Schneider runtimes)
- Download: https://store.codesys.com

### 3.5 Schneider EcoStruxure

**Machine Expert / Control Expert:**
- Requires Schneider license

---

## 4. AI Service Accounts

Required to run the factory's AI prompts:

### 4.1 Anthropic Claude (recommended — Opus 4 available)
- API key: https://console.anthropic.com
- For customer data (🟠 CONFIDENTIAL): use **AWS Bedrock** or **Anthropic API enterprise tier**
- ChatGPT.com / claude.ai **web versions are PROHIBITED for customer data**

### 4.2 Google Gemini (free tier available)
- API key: https://aistudio.google.com/apikey — **the free tier is sufficient
  for most retrofit pre-analyses** (PDF/photo/P&ID reading, translation)
- SDK: `pip install google-genai` (see §2.3)
- Default task routing uses Gemini for `preanalysis` and `translation`
- Enterprise tier (Vertex AI) required for 🟠 CONFIDENTIAL data

### 4.3 DeepSeek (low-cost alternative)
- API key: https://platform.deepseek.com
- Suitable for low-cost template code on 🟢 PUBLIC projects **only** — the
  classification guard blocks CONFIDENTIAL data for this provider tier

### 4.4 OpenAI GPT (alternative)
- API key: https://platform.openai.com
- Enterprise tier required for 🟠 CONFIDENTIAL data

### 4.5 API Key Setup in the Workbench

```bash
python 05_SCRIPTS/factory_web.py   # launch the GUI
# Settings → AI Provider → paste your key → Save
# Key is stored in the OS keystore (Windows Credential Vault / macOS Keychain)
```

> **Platform support for the GUI.** `factory_web.py` is a **desktop application**
> (pywebview): it needs a system web runtime — Edge WebView2 on Windows, WebKit
> on macOS, or GTK/Qt WebKit on Linux. On a **headless server or a Linux box
> without GTK/Qt** it will raise `WebViewException` and cannot start. The factory
> core — `script_project_init.py`, the Gate-4 validators in `05_SCRIPTS/dev/`,
> and the whole test suite — is **pure CLI and runs anywhere** (Windows, macOS,
> Linux, CI). Headless users should drive the factory through the CLI scripts.

---

## 5. Clone the Factory

```bash
# 1. Create the workspace folder (recommended structure)
mkdir D:\automation_workspace
cd D:\automation_workspace

# 2. Clone the factory
git clone https://github.com/Mehmet-Haydar/automation-factory.git

# 3. Resulting folder structure:
# D:\automation_workspace\
# ├── AUTOMATION_FACTORY\      ← Factory lives here
# └── customer_projects\        ← Customer projects go here (you create this)

mkdir D:\automation_workspace\customer_projects
```

---

## 6. First Test — Verify the Factory Works

```bash
cd D:\automation_workspace\AUTOMATION_FACTORY

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1     # Windows
# or
source .venv/bin/activate          # Linux/macOS

# Check Python version
python --version
# Expected: Python 3.12.x

# Check dependencies installed
pip list | findstr "openpyxl"
# Expected: openpyxl 3.x.x

# Test script — show help output
python 05_SCRIPTS/script_project_init.py --help
# Expected: argument list (--name, --type, --customer, --output, --output-lang)
```

---

## 7. Create Your First Customer Project

```bash
# From inside the factory folder:
python 05_SCRIPTS/script_project_init.py \
  --name "TestProject_2026" \
  --type retrofit \
  --customer "Test Customer GmbH" \
  --output "D:\automation_workspace\customer_projects" \
  --output-lang DE
```

**Result:**
```
D:\automation_workspace\customer_projects\TestProject_2026\
├── PROJECT_MAESTRO.md
├── PROJECT_STATE.json
├── 01_DOCS\
├── 02_HARDWARE\
├── 03_PLC\
│   ├── SCL\
│   └── exports\
├── 04_HMI\
├── 05_TESTS\
├── 06_REPORTS\
├── 99_FACTORY_REFS\         ← Factory reference lives here
└── (metadata_template copies — future script update)
```

The customer project is created **outside the factory** in its own folder. The factory itself is not touched.

---

## 8. Troubleshooting

### "python is not recognized"
PATH is not set. Re-run the Python installer and check "Add to PATH". Or set it manually:
```powershell
# PowerShell (temporary — current session only)
$env:Path += ";C:\Users\<username>\AppData\Local\Programs\Python\Python312\"
```

### "pip install fails on lxml"
C++ build tools are missing on Windows. Fix:
```bash
pip install --only-binary=:all: lxml
# Or
pip install --only-binary=:all: -r requirements.txt
```

### "Permission denied" on git clone
SSH key missing or incorrect. Use HTTPS instead:
```bash
git clone https://github.com/Mehmet-Haydar/automation-factory.git
```

### "Cursor AI not responding"
- Check internet connection
- Verify API key is entered correctly (Cursor → Settings → AI)
- Check account credit balance

### German characters appear garbled
- Set terminal encoding to UTF-8:
  ```powershell
  chcp 65001     # For PowerShell
  ```

---

## 9. Recommended Folder Structure

```
D:\automation_workspace\                    ← Workspace root
│
├── AUTOMATION_FACTORY\                     ← Factory (GitHub repo, public)
│   ├── 01_GLOBAL_STANDARDS\
│   ├── 02_PROJECT_TYPES\
│   ├── 03_DOMAIN_TOOLS\
│   ├── 04_AI_PROMPTS\
│   ├── 05_SCRIPTS\
│   ├── 06_KNOWLEDGE_BASE\
│   ├── 07_PROJECT_TEMPLATE\
│   ├── 08_METADATA_INPUT\
│   ├── examples\                           ← Synthetic demo (public OK)
│   │   └── Kunde_Mueller_Conveyor_Retrofit\
│   ├── .venv\                              ← Python virtual environment
│   └── ...
│
└── customer_projects\                      ← REAL CUSTOMERS (private, never goes to GitHub)
    ├── CustomerA_Conveyor_2026\               ← Customer 1
    │   ├── PROJECT_MAESTRO.md
    │   ├── _input\          (🟠 CONFIDENTIAL customer code)
    │   ├── metadata\RD01..RD14
    │   ├── _output\
    │   └── 99_FACTORY_REFS\
    │
    ├── Arcelik_Press_2026\                ← Customer 2
    └── Customer_X\                         ← Customer 3
```

**Rule:** The factory is committed and pushed with `git`. Customer projects are NEVER committed (or kept in a separate private repo).

---

## 10. Security

### Customer Data Discipline
- Do **NOT** upload 🟠 CONFIDENTIAL customer code to public AI services
- Use Cursor Business / Anthropic Enterprise / AWS Bedrock
- The customer folder must NOT share the same git repository as the factory

### Backup
- Factory: Every push to GitHub is a backup
- Customer projects: Weekly backup to an external drive is recommended

---

## 11. Links

- **Factory GitHub:** https://github.com/Mehmet-Haydar/automation-factory
- **User Guide (comprehensive):** `USER_GUIDE_BIG_PICTURE.md`
- **Pipeline:** `PIPELINE_CODE_REWRITE.md`
- **Example project:** `examples/Kunde_Mueller_Conveyor_Retrofit/README.md`

---

## 12. Questions

GitHub Issues: https://github.com/Mehmet-Haydar/automation-factory/issues
(Or contact the repository owner directly)

---

*v1.0.0 — This guide covers installation only. For usage, see README for summary and the relevant guide files for details.*
