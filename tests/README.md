# Regression Test Suite

## Quick start

```bash
pip install pytest
python -m pytest -q
```

## Test modules

| File | Finding | What it verifies |
|------|---------|-----------------|
| `test_smoke.py` | W6 | Import sanity — workbench.core.io_list_io, project_analyzer |
| `test_safety_detection.py` | C1 | F-block detection fail-closed; RD05-declared names; uncertain skipped |
| `test_plcsim_guard.py` | C2 | PLCSIM-only target guard; dangerous-option rejection |
| `test_io_list_roundtrip.py` | C3 | IO round-trip: #UNKNOWNS + grid-outside content preserved |
| `test_classification_guard.py` | C4 | CONFIDENTIAL→public AI blocked; enterprise override; RESTRICTED never |
| `test_gate_advance.py` | C5 | Gate blockers: empty RDs, approval signature, validation errors |
| `test_rd_names.py` | W1 | RD_NAMES matches project_analyzer.RD_INPUT_NEEDS titles |
| `test_scl_pipeline_dirs.py` | W2 | extract_io writes to `_output/scl/`; metadata/ scanned |
| `test_validator_scope.py` | W3 | FileResult.scope="structural_only"; scope_warning present |
| `test_repair_loop.py` | W4 | auto_apply=False: current_scl unchanged, diff returned |
| `test_show_standards.py` | W5 | show_standards reads real rules/; not-found → clear error |
| `test_settings_keys.py` | W7 | API keys stored via keyring, not plaintext in JSON |
| `test_io_validator_addr.py` | I3 | Bit address 0-7 range consistent across regex patterns |

## TIA Portal bridge (C1/C2) — runtime-untestable note

`openness_core.py` and `plcsim_download.py` require TIA Portal + pythonnet at runtime.
Pure logic (`_safety_classification`, `_is_download_target_safe`) is unit-tested above.
The `provider.Download()` call path is verified by code inspection only (documented in
commit messages for C1/C2).

## conftest.py

Adds `PROJECT_ROOT` and `05_SCRIPTS` to `sys.path` so all scripts import cleanly.
The `example_project` fixture copies `examples/Kunde_Mueller_Conveyor_Retrofit` to a
`tmp_path` for integration-style tests.
