# 🤝 Contributing to AUTOMATION_FACTORY

Thanks for your interest in improving the factory! This is an actively developed,
AI-assisted industrial PLC automation framework. Contributions — whether code,
knowledge-base entries, AI-prompt tuning, or bug reports — are welcome.

Please read this guide before opening a pull request. It reflects the **actual**
conventions used in this repo, not generic boilerplate.

---

## 🔴 Read this first — the one rule that cannot be broken

> **NEVER commit real customer data, API keys, or CONFIDENTIAL/RESTRICTED material.**

This factory is published as a **PUBLIC** repository. Everything you push lives in
the open. The data-classification standard
(`01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`) governs what may and may
not appear here:

| Class | May it go in this repo? |
|-------|-------------------------|
| 🟢 PUBLIC | ✅ Yes — factory standards, synthetic examples, pattern code |
| 🟡 INTERNAL | ⚠️ Only after anonymization (customer name → `<CUSTOMER_X>`, IPs → `192.168.X.X`, etc.) |
| 🟠 CONFIDENTIAL | ❌ Never — customer code, IO lists, machine design details |
| 🔴 RESTRICTED | ❌ Never — recipes, safety passwords, F-PLC credentials, license files |

Concretely:

- **All examples must be synthetic.** Use the existing fictional customer pattern
  (e.g. `examples/Kunde_Mueller_Conveyor_Retrofit/`, "Kunde Müller GmbH"). Never
  paste real customer code, names, project IDs, or network topology — even in a
  comment or a test fixture.
- **API keys live in the OS keystore** (Windows Credential Vault / macOS Keychain
  via `keyring`). They are never committed, never hard-coded, and never written to
  JSON. The `test_settings_keys.py` test guards this.
- **Customer projects belong in a separate folder/repo** (`customer_projects/`),
  outside the factory — see `GLOBAL_GIT_DISCIPLINE.md` §1 (Two-Repository Model).

If you accidentally commit sensitive data, see the violation procedure in
`GLOBAL_DATA_CLASSIFICATION.md` §4, and report a leak privately via
[Security Advisories](https://github.com/Mehmet-Haydar/automation-factory/security/advisories)
(see [SECURITY.md](SECURITY.md)).

---

## 🛠️ Development setup

The factory **core** is pure-CLI Python and runs on Windows, macOS, and Linux. (The
optional web GUI `factory_web.py` is a pywebview desktop app and needs a system web
runtime — see [INSTALLATION.md](INSTALLATION.md) §4 — but you do **not** need it to
develop or run the tests.)

Requires **Python 3.10+** (CI tests against 3.11 and 3.12).

```bash
# 1. Clone
git clone https://github.com/Mehmet-Haydar/automation-factory.git
cd automation-factory

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
source .venv/bin/activate          # Linux / macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Sanity-check the install
python 05_SCRIPTS/script_project_init.py --help
```

Full setup details, troubleshooting, and optional industry tooling (TIA Portal,
Studio 5000, Gemini SDK, …) are in [INSTALLATION.md](INSTALLATION.md).

---

## 🧪 Running the tests

The regression suite lives in `tests/` and is run with pytest:

```bash
python -m pytest          # full suite (-q is the default via pytest.ini)
python -m pytest -v       # verbose
python -m pytest tests/test_classification_guard.py   # a single module
```

See `tests/README.md` for what each module verifies. A few highlights worth knowing
before you touch related code:

- `test_classification_guard.py` — CONFIDENTIAL → public AI is blocked; RESTRICTED
  is never sent.
- `test_safety_detection.py` — safety F-block detection is **fail-closed**.
- `test_settings_keys.py` — API keys are stored via `keyring`, not plaintext.

**CI must stay green.** Every push and pull request to `main` runs:

- **Regression Tests** (`.github/workflows/tests.yml`) — a matrix of
  **Windows + Linux × Python 3.11 / 3.12**. The Windows leg is not optional: it
  catches `keyring` API drift, PowerShell path quirks, and case-insensitive
  filename collisions that an Ubuntu-only run misses.
- **CI — Gate Check** (`.github/workflows/ci.yml`) — runs the SCL **acceptance gate**
  on all 18 library blocks; each must report `AUTO_VERIFIED_structural | PENDING_TIA_VERIFY`.

A PR will not be merged unless both workflows pass. Run `python -m pytest` locally
before pushing.

---

## ✍️ Coding & commit conventions

### Naming and style
- Follow `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md` (e.g. PascalCase SCL
  block/file names — `FB_Motor_Standard`, not `FB_MOTOR_STANDARD`).
- Python is linted with `ruff` and type-checked with `mypy` (both in
  `requirements.txt`). Keep new code clean under `ruff check`.
- System language is English; code output may be TR/EN/DE per project
  (`GLOBAL_LANG_POLICY.md`).

### Git discipline
Follow `01_GLOBAL_STANDARDS/rules/GLOBAL_GIT_DISCIPLINE.md`. Commit messages use a
**Conventional-Commits-style** prefix, as seen in `git log`:

```
<type>(<scope>): <short summary>
```

**Type enum:** `feat` / `fix` / `docs` / `refactor` / `test` / `chore`
(plus `merge` for branch merges, as used in history).

Real examples from this repo's history:

```
feat(retrofit): multi-AI pipeline — anonymizer, Gemini Vision, per-step routing
fix(workbench): repair AI autoflow + IO-list MD round-trip
docs+chore: align public release — version, paths, hygiene
chore(release): bump to v3.2.0
```

- Branch from `main`; open a PR against `main`.
- Force-push is **prohibited** (only `--force-with-lease` on your own branch).
- When a change is user-facing, update **[CHANGELOG.md](CHANGELOG.md)** — it follows
  [Keep a Changelog](https://keepachangelog.com/) + SemVer.

---

## 📚 Where to contribute (factory channels)

You don't have to write Python to help. The factory has dedicated channels for
domain knowledge:

- **Knowledge Base pitfalls** → add lessons learned to `06_KNOWLEDGE_BASE/`.
- **Project-type guides** → extend retrofit / greenfield workflows in `02_PROJECT_TYPES/`.
- **AI prompt improvements** → tune the prompt library in `04_AI_PROMPTS/`
  (analyze / code_gen / review / test_gen).
- **Standards changes** → don't edit a `GLOBAL_*` rule blind; propose it formally:

  ```bash
  python 05_SCRIPTS/script_propose_update.py \
    --target "01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md" \
    --reason "..." \
    --suggestion "..."
  ```

---

## 🤖 AI-assisted contributions

This project embraces AI assistance — but under the factory's discipline (README
§ "AI Discipline"):

1. **AI accelerates, the engineer decides, the customer signs.**
2. AI output for Safety (RD05 / SIL / PLr) is **DRAFT_UNVERIFIED** — a certified
   safety engineer must approve. Do not submit AI-estimated safety classifications.
3. AI-generated SCL stays labelled `PENDING_TIA_VERIFY` until a human compiles and
   tests it. Don't claim "TIA-verified" in a PR.

If a commit was co-authored with AI, note it in the commit body (per
`GLOBAL_GIT_DISCIPLINE.md` §3).

---

## 🐛 Reporting bugs & requesting features

- **Bugs / features** → open a
  [GitHub Issue](https://github.com/Mehmet-Haydar/automation-factory/issues).
  Include OS, Python version, steps to reproduce, and the expected vs. actual result.
  Strip any customer-specific detail first.
- **Security vulnerabilities** → do **not** file a public issue. Follow
  [SECURITY.md](SECURITY.md) and use GitHub's private "Report a vulnerability" flow.

---

Thank you for helping make the factory better — and safer. 🏭
