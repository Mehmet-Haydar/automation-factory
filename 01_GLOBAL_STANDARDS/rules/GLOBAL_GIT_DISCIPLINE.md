---
title: Git Workflow Discipline
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-16
applies_to: [factory_internal]
status: ACTIVE
---

# GLOBAL_GIT_DISCIPLINE.md — Git Workflow Standard

> Git usage discipline for Factory and customer projects.

---

## 1. Two Separate Repository Model

```
AUTOMATION_FACTORY/          ← Public/Private repo
└── git remote: github.com/Mehmet-Haydar/automation-factory

customer_projects/CustomerA_*/   ← Private (or not versioned)
└── git remote: SEPARATE repo (agreed with customer) or local-only

⚠️ NEVER: Commit customer code in factory repo.
```

---

## 2. Branch Strategy

### Factory
- `main` — production ready
- (future) `dev` — development
- Currently **no branches**, direct commits to main
- Push is **manual** (user decision)

### Customer Project
- `main` — field status
- (future) feature branches based on project complexity

---

## 3. Commit Message Format

```
<type>(<version>): <short summary>

<detailed explanation (optional but recommended)>

<co-author signature (if AI)>
```

Examples:
```
feat(v3.0.0-alpha): added new AI prompt (PROMPT_REVIEW_SAFETY)
fix(v3.0.0): fixed script_project_init.py output-lang argument
docs: expanded INSTALLATION.md
refactor: clarified 14-Point Pack RD05 discipline
```

**Type enum:** `feat` / `fix` / `docs` / `refactor` / `test` / `chore`

---

## 4. .gitignore Discipline

Factory:
```
.venv/
__pycache__/
*.pyc
.DS_Store
Thumbs.db
*.swp
.vscode/
.idea/

# AI cache
.cursor/cache/
.claude/

# Test outputs
.pytest_cache/
htmlcov/

# OS specific
desktop.ini
```

Customer project (additional):
```
_input/customer_proprietary/   # Customer proprietary files
_output/customer_specific/      # Customer-specific code
*.bak
*.tmp
```

---

## 5. Customer Data Discipline

❌ **NEVER commit customer code to factory repo**

Check:
```bash
# Pre-commit hook (future)
git diff --cached --name-only | xargs grep -l "customer_proprietary"
# If match found, commit is rejected
```

🟠 CONFIDENTIAL data leakage = legal liability.

---

## 6. Pre-commit Hooks (Future v3.0.0-beta)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff lint
        entry: ruff check
        language: system
      - id: md-schema-validator
        name: MD schema check
        entry: python 05_SCRIPTS/dev/script_md_schema_validator.py
        language: system
      - id: no-customer-data
        name: customer data commit check
        entry: python 05_SCRIPTS/check_no_customer_leak.py
        language: system
```

---

## 7. Version Tags

Major milestones are tagged:
```bash
git tag -a v3.0.0-alpha -m "v3.0.0-alpha — 14-Point Pack completed"
git push --tags
```

Tag name format: `v<MAJOR>.<MINOR>.<PATCH>[-prerelease]`

---

## 8. Push Discipline

- Factory: **manual push** (not required after every commit)
- At minimum once per sprint end
- Before push: verify `git log --oneline -5`
- Force push **PROHIBITED** (`git push --force-with-lease` exception, own branch only)

---

## 9. Audit + Log

For each major change:
- `CHANGELOG.md` must be updated
- `PROGRESS_TRACKER.md` must be updated
- `_BUILD_LOG.md` (session-based) must be updated

---

## 10. Customer Project Git Structure (Recommended)

```bash
cd <customer_project>
git init
echo "_input/_proprietary/" >> .gitignore
git add .
git commit -m "feat: <project> initialized from AUTOMATION_FACTORY v3.0.0-alpha"

# If agreement with customer on private remote:
git remote add origin <private_repo_url>
git push -u origin main
```

---

## 11. Related Files

- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`
- **AI policy:** `GLOBAL_AI_INTERFACE.md`
- **Scripts:** `05_SCRIPTS/script_propose_update.py`

---

*v1.0.0 — Git discipline = foundation of factory + customer data security.*
