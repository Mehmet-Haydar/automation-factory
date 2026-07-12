---
title: 05_SCRIPTS — Folder README
version: 2.1.0
last_updated: 2026-05-23
status: ACTIVE
last_validated: 2026-05
---

# `05_SCRIPTS/` — Python Tools

> **All of the factory's Python code is in this folder.**
> GUI, AI client, analyzers, generators, export tools, and CLI scripts.

---

## File Map

### CORE — Main Application
| File | What it does |
|------|--------------|
| `factory_web.py` | Main GUI — project management, pipeline, settings (pywebview + webgui/) |
| ~~`factory_gui.py`~~ | **Abandoned** — replaced by factory_web.py (tkinter GUI, not active) |
| `project_analyzer.py` | Scans the project folder, produces RD statuses + pipeline steps |

### AI — Artificial Intelligence Layer
| File | What it does |
|------|--------------|
| `ai_client.py` | Single interface for Anthropic / OpenAI / Gemini / DeepSeek |
| `ai_decision_log.py` | EU AI Act Article 12 — logs every AI step to a markdown table |
| `prompt_meta.py` | Prompt frontmatter reading + smart context injection |
| `code_verifier.py` | Looks for syntax errors in generated SCL + repair loop |

### GENERATE — Code and Document Generators
| File | What it does |
|------|--------------|
| `iec_tag_generator.py` | Generates an IEC 61131-3 compliant tag table from RD01 |
| `ob1_generator.py` | Generates OB1 skeleton code |
| `fb_templates.py` | FB/FC/DB template generator |
| `fat_protocol.py` | Creates a FAT/SAT test protocol (automatically from RD01+RD05) |
| `customer_report.py` | Customer report (PDF/MD) |
| `project_report.py` | Project summary report |

### VERIFY — Validation and Quality
| File | What it does |
|------|--------------|
| `scl_validator.py` | SCL syntax validation |
| `scl_extractor.py` | Extracts SCL blocks from MD |
| `hardware_sizer.py` | Hardware sizing calculation |
| `bom_manager.py` | Bill-of-materials management (from 09_HARDWARE_LIBRARY) |

### EXPORT — Export
| File | What it does |
|------|--------------|
| `tia_export.py` | TIA Portal XML export |
| `tia_tag_export.py` | TIA tag table export |
| `hw_config_parser.py` | TIA Openness hardware configuration reader |

### PROJECT — Project Management
| File | What it does |
|------|--------------|
| `project_git.py` | Project-folder git automation (auto-commit steps) |
| `project_archiver.py` | Project archiving |
| `platform_detector.py` | PLC platform detection (S7/AB/CODESYS) |

### SCRIPTS — CLI Tools
| File | What it does | When |
|------|--------------|------|
| `script_project_init.py` | Creates a new customer project skeleton | Project start |
| `script_consistency_check.py` | RD cross-reference + schema validation | Gate 4 |
| `script_md_schema_validator.py` | MD frontmatter format check | After every edit |
| `script_factory_audit.py` | Factory overall health audit | End of sprint |
| `script_md_to_xlsx.py` | MD template → XLSX conversion | Customer delivery |
| `script_bulk_md_edit.py` | Bulk Markdown editing | Cross-cutting changes |
| `script_propose_update.py` | Feedback proposal recording | Continuous improvement |
| `script_prompt_amend.py` | Bulk prompt update | Version transitions |
| `script_orchestrator.py` | Pipeline orchestrator (Gate 1→7) | *In development* |
| `script_excel_to_metadata.py` | Customer Excel → JSON metadata | *In development* |
| `script_openness_export.py` | TIA Openness export wrapper | *In development* |
| `script_state_validator.py` | PROJECT_STATE.json check | *In development* |

---

## Running

```bash
# Start the GUI (Windows — recommended; .venv is set up automatically on first run)
start.bat

# or directly
python 05_SCRIPTS/factory_web.py

# Create a new project
python 05_SCRIPTS/script_project_init.py --name "Project" --type retrofit --customer "Customer GmbH"

# RD validation
python 05_SCRIPTS/dev/script_consistency_check.py --project D:\...\CustomerProject
```

---

## Dependencies

```bash
pip install -r requirements.txt
```

Critical packages: `customtkinter`, `anthropic`, `openai`, `google-generativeai`, `gitpython`

---

## New Script Standard

```python
#!/usr/bin/env python3
"""
script_<name>.py — <short description>

Usage:
    python 05_SCRIPTS/script_<name>.py --help
"""
# CLI via argparse, --dry-run support, exit codes 0/1/2
```

---

*Architecture: `factory_web.py` (the active webgui, native window via pywebview + HTML/CSS frontend in `webgui/`) wraps everything visually; the underlying scripts and modules also run as standalone CLIs. The tkinter `factory_gui.py` is abandoned — see entry in the table above.*
