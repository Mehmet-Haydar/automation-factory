# Nightly TIA Compile CI — Setup Guide (Kademe 2)

> **Status: PREP / DORMANT.** The workflow `.github/workflows/nightly-tia.yml`
> ships disabled-by-default (dispatch-only, no schedule). Nothing runs on your
> machine until **you** register a self-hosted runner following this guide.
> No system change was made on your PC by the night run.

This sets up an on-demand pipeline that imports the 18 library SCL blocks into
a scratch TIA project, compiles them with Openness, and reports one PASS/FAIL
line per block. It is the bridge to **Kademe 3** (PLCSIM behavioural CI, S-28).

---

## 0. Before you start — security

- **Never** attach a self-hosted runner to a *public, fork-enabled* repo.
  A pull request from anyone could execute arbitrary code on your engineering
  PC. Keep this repo **private**, or restrict workflows to the protected
  branch and disable PR runs from forks.
- The runner runs as a Windows user. Use a **dedicated, least-privilege**
  account that has Openness access but is not your daily admin login.
- `nightly_tia_check.py` is written to print **only block names + PASS/FAIL** —
  no project path or customer data. Do not add `set -x`/path echoes to the
  workflow.

---

## 1. Prerequisites on the runner PC

| Requirement | Notes |
|---|---|
| Windows 10/11 | Same machine that has TIA Portal |
| TIA Portal V19 (and/or V20/V21) | Matching Openness version |
| TIA Openness | Install via the TIA setup "Openness" option |
| **Siemens TIA Openness** user group | Add the runner's Windows user to this local group, else Openness refuses to start |
| Python 3.11 + `pythonnet` | `pip install pythonnet` |
| A scratch TIA project | One PLC device (default name `PLC_1`); see §4 |

The bridge auto-detects the `Siemens.Engineering.dll`; if detection fails set
`bridges.tia.tia_v19_dll_path` (or `_v20`/`_v21`) in settings.

---

## 2. Register the self-hosted runner

1. GitHub → repo **Settings → Actions → Runners → New self-hosted runner**
   → Windows.
2. Follow the download/configure commands GitHub shows. During `config.cmd`,
   when asked for **labels**, add `tia`:
   ```
   ./config.cmd --url https://github.com/<owner>/<repo> --token <TOKEN> --labels tia
   ```
   The `tia` label is what `runs-on: [self-hosted, tia]` targets.
3. Run it as a service so it survives reboots:
   ```
   ./svc.cmd install
   ./svc.cmd start
   ```
4. Confirm the runner shows **Idle** (green) in Settings → Runners.

> Private-repo note: self-hosted runners are intended for private repos. If
> this repo is or becomes public, **remove the runner** first.

---

## 3. Run it

Manual trigger (GitHub → Actions → *Nightly TIA Compile* → **Run workflow**):

- **Leave `project` empty** → only the `preflight` job runs (inventory smoke
  check on `ubuntu-latest`; confirms all 18 blocks are present). Good for a
  first dry run — needs no runner.
- **Set `project`** to the scratch project path on the runner (e.g.
  `C:\tia-ci\scratch\Scratch.ap19`) → the `compile` job runs on the `tia`
  runner: import → compile → PASS/FAIL per block.

CLI equivalent on the runner, for local debugging:
```
python 05_SCRIPTS/nightly_tia_check.py --preflight
python 05_SCRIPTS/nightly_tia_check.py --project "C:\tia-ci\scratch\Scratch.ap19" --plc PLC_1
```

---

## 4. Creating the scratch project

1. New TIA project, add one PLC (CPU type matching your library, e.g.
   `1518-4 PN/DP`), name it `PLC_1`.
2. Save it somewhere stable on the runner (e.g. `C:\tia-ci\scratch\`).
3. Empty is fine — the nightly run imports the blocks each time. (Safety
   F-blocks are skipped by design, RD05 rule.)

---

## 5. Multi-version loop (V19 / V20 / V21)

To compile against several TIA versions, keep one scratch project per version
(`Scratch.ap19`, `Scratch.ap20`, `Scratch.ap21`) and add a matrix to the
`compile` job:

```yaml
  compile:
    needs: preflight
    if: ${{ github.event.inputs.project != '' }}
    runs-on: [self-hosted, tia]
    strategy:
      matrix:
        ver: [ap19, ap20, ap21]
    steps:
      - uses: actions/checkout@v4
      - shell: pwsh
        run: |
          python 05_SCRIPTS/nightly_tia_check.py `
            --project "C:\tia-ci\scratch\Scratch.${{ matrix.ver }}" --plc PLC_1
```

Each version needs its matching Openness installed on the runner.

---

## 6. Switching to a real nightly schedule

Once the runner is stable, add a schedule trigger to
`.github/workflows/nightly-tia.yml`:

```yaml
on:
  workflow_dispatch:
    # ... existing inputs ...
  schedule:
    - cron: "0 2 * * *"   # 02:00 UTC daily
```

A scheduled run has empty inputs, so it would run preflight only. To compile on
a schedule, give the script a default project via an env var / repo variable
and read it in the workflow instead of `github.event.inputs.project`.

---

## 7. Next: Kademe 3 (S-28, PLCSIM behavioural CI)

This package only **compiles**. The next step escalates Gate-6 evidence: run
the FAT catalogue scenarios against PLCSIM Advanced automatically (download to
PLCSIM only — never a real PLC, per the `plcsim_only` rule). Start that after
this runner is proven stable. Tracked as backlog **S-28**.
