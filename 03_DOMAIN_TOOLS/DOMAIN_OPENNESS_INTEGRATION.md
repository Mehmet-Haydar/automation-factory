---
title: TIA Portal Openness Integration
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [factory_internal]
prerequisite: [GLOBAL_NAMING_STANDARD.md]
status: FILLED
---

# DOMAIN_OPENNESS_INTEGRATION

Reference document for the TIA Portal Openness bridge implemented in Phase 37.

---

## Summary

The AUTOMATION_FACTORY → TIA Portal V19/V20 bridge imports generated SCL files
directly into the TIA project (instead of manual copy-paste), compiles them, and
(optionally) downloads to PLCSIM Advanced.

**Module:** `05_SCRIPTS/bridges/tia/`

| File | Role |
|------|------|
| `version_detect.py` | Scans TIA V14..V20 installations, finds the DLL path |
| `openness_core.py` | pythonnet + Siemens.Engineering wrapper (shared by V19/V20) |
| `v19.py` | TIA V19 bridge (`.ap19`, V19 DLL) |
| `v20.py` | TIA V20 bridge (`.ap20`, V20 DLL) — inherits from v19 |
| `plcsim_download.py` | Download to PLCSIM Advanced (Openness DownloadProvider) |

---

## License

**TIA Openness has been FREE since V14 SP1.** A Siemens TIA Engineering
license is enough — no separate purchase required.

Only condition: the user must be a member of the **Siemens TIA Openness** local
user group on Windows.

**Check:**
```
lusrmgr.msc → Groups → "Siemens TIA Openness" → Add member
```

The "🔍 Test Path" button in the GUI performs this check automatically.

---

## Dependencies

| Component | Install |
|-----------|---------|
| **pythonnet** | `pip install pythonnet` (calls .NET DLLs from Python) |
| **TIA Portal V19 or V20** | Official Siemens installation |
| **PLCSIM Advanced** (optional) | Required for the download flow |

The GUI lazy-imports the `bridges/` package; the GUI does not break even if
pythonnet is not installed. The TIA bridges simply show a "could not load"
status in that case.

---

## Flow: SCL → TIA → PLCSIM

```
┌──────────────────┐
│  AI generates    │
│  _output/scl/    │  *.scl files
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ TiaV20Bridge     │  import_scl_to_project()
│ - core.start_portal()
│ - core.open_project(.ap20)
│ - core.find_plc("PLC_1")
│ - core.import_scl_files() ← RD05 Safety skipped
│ - core.compile_plc()      ← optional
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ plcsim_download  │  download_to_plcsim()
│ - DownloadProvider
│ - PLCSIM Advanced target
│ - REAL PLC NEVER          ← plcsim_only lock
└──────────────────┘
```

---

## Safety Gates (constraints_critical rule from memory)

| Gate | Default | Behaviour |
|------|---------|-----------|
| `skip_safety_blocks` | ON | RD05 Safety / F-blocks are NEVER included in the import |
| `plcsim_only` | ON | Automatic download to a real PLC is REJECTED |
| `auto_compile_after_import` | ON | Triggers compile after import (error report) |

The user can change these gates from the **General Settings** panel on the
Bridges screen of the GUI; turning `plcsim_only` off shows a "violates memory
rule" warning.

---

## CLI Usage (for testing)

```bash
# List installed TIA versions
python 05_SCRIPTS/bridges/tia/version_detect.py

# Import Factory I/O scene tag CSV (separate bridge)
python -m bridges.factoryio.scene_importer --csv scene.csv --project project_path/
```

---

## GUI Integration

A **"🔌 Bridges"** menu item was added to the sidebar. The screen has:

1. **General Settings panel** — 3 safety toggles (Skip Safety, PLCSIM-only, auto-compile)
2. **One card per bridge:**
   - Status pill (READY / NOT INSTALLED / CONFIG MISSING / ERROR)
   - Enabled/Disabled switch
   - Action buttons (for TIA: Test, Send SCL, +Compile+Download)

3. **Un-loadable bridges** are listed in a red warning card.

---

## Difference Between TIA V19 and V20

The API surface is 99% identical. The differences:

| | V19 | V20 |
|---|-----|-----|
| DLL path | `Portal V19\PublicAPI\V19\` | `Portal V20\PublicAPI\V20\` |
| Project extension | `.ap19` | `.ap20` |
| Stability | Good | Better (recommended) |
| F-block support | Limited (read-only) | Limited (read-only) — unchanged |

V20 is the primary target; V19 is the alternative (eases customer migration).

---

## Limitations

1. **F-blocks cannot be written** — unchanged even in Openness V20. Safety
   logic is always written by hand inside TIA.
2. **Download API differs between V19 ↔ V20** — `plcsim_download.py` is
   defensively written; if the signature changes the error is caught and the
   user is offered a manual workaround.
3. **Conflict if the user touches the TIA UI while a session is open** — the
   bridge starts with `with_ui=True` so the user sees TIA but must not
   intervene (indicator: "Openness session active" text in the TIA window).

---

## Related Files

- `05_SCRIPTS/bridges/` — bridge package
- `05_SCRIPTS/factory_web.py` (TIA bridge action / Send-to-TIA in the active webgui; the tkinter `factory_gui.py` referenced in older docs is abandoned)
- `05_SCRIPTS/tia_export.py` (manual folder-import package — old method,
  still usable; lives alongside the bridge, not as a replacement)
- `05_SCRIPTS/tia_tag_export.py` (Tag Table XML)

---

*v1.1.0 — Full English body (2026-05-23). Written together with Phase 37.*
