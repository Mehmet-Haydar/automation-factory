#!/usr/bin/env python3
"""
project_git.py — Customer Project Git Integration (Phase 30)

Per-customer-project git repo support:
  - git init + .gitignore  (keeps CONFIDENTIAL files out)
  - Auto-commit when a pipeline step completes
  - Creating a private repo on GitHub (with a PAT, via urllib — no extra packages)
  - Push (always requires manual confirmation)

Usage:
  from project_git import init_project_repo, auto_commit_step, get_git_info
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# -- .gitignore template ------------------------------------------------------

GITIGNORE_TEMPLATE = """\
# -- CONFIDENTIAL: raw customer data -- never committed ---------------------
_input/

# -- API keys / GUI settings -----------------------------------------------
.gui_settings.json
*.env
*.key

# -- Python ----------------------------------------------------------------
__pycache__/
*.pyc
*.pyo

# -- Temporary / backup ----------------------------------------------------
*.log
*.tmp
*.bak
.backup_*

# -- Operating system ------------------------------------------------------
.DS_Store
Thumbs.db
desktop.ini

# Audit log — version-controlled via auto_commit_step only
AI_DECISION_LOG.jsonl
"""


# -- Data structures ----------------------------------------------------------

@dataclass
class ProjectGitInfo:
    has_repo: bool = False
    branch: str = ""
    remote_url: str = ""
    last_commit_hash: str = ""
    last_commit_msg: str = ""
    last_commit_date: str = ""
    uncommitted: bool = False
    ahead: int = 0          # number of un-pushed commits
    error: str = ""


@dataclass
class GitOpResult:
    ok: bool = False
    message: str = ""
    repo_url: str = ""      # URL of the repo created on GitHub


# -- Low-level git helper -----------------------------------------------------

def _run(args: list[str], cwd: Path, env_extra: Optional[dict] = None) -> tuple[bool, str]:
    """
    Run a git command.
    Returns: (success, output)
    """
    import os
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        res = subprocess.run(
            ["git"] + args, cwd=str(cwd),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, env=env,
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        ok  = res.returncode == 0
        combined = out if ok else (err or out)
        return ok, combined
    except FileNotFoundError:
        return False, "git is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return False, "git command timed out (30 s)."
    except Exception as exc:
        return False, str(exc)


# -- Repo init ----------------------------------------------------------------

def init_project_repo(
    project_path: Path,
    user_name: str = "",
    user_email: str = "",
) -> GitOpResult:
    """
    Initialize a git repo in the project folder.
    Creates .gitignore + the first empty commit.
    """
    if not project_path.exists():
        return GitOpResult(message=f"Folder not found: {project_path}")

    git_dir = project_path / ".git"
    if git_dir.exists():
        return GitOpResult(ok=True, message="Repo already exists.")

    # git init
    ok, msg = _run(["init", "-b", "main"], project_path)
    if not ok:
        # an old git version may not recognize the -b flag
        ok, msg = _run(["init"], project_path)
    if not ok:
        return GitOpResult(message=f"git init failed: {msg}")

    # user.name / user.email (local config)
    if user_name:
        _run(["config", "user.name", user_name], project_path)
    if user_email:
        _run(["config", "user.email", user_email], project_path)

    # .gitignore
    gi_path = project_path / ".gitignore"
    if not gi_path.exists():
        gi_path.write_text(GITIGNORE_TEMPLATE, encoding="utf-8")

    # First commit
    _run(["add", ".gitignore"], project_path)
    ts = datetime.now().strftime("%Y-%m-%d")
    ok, msg = _run(
        ["commit", "-m", f"init: AUTOMATION FACTORY project repo ({ts})"],
        project_path,
    )
    if not ok:
        return GitOpResult(message=f"First commit failed: {msg}")

    return GitOpResult(ok=True, message="Git repo initialized and first commit created.")


# -- Status query -------------------------------------------------------------

def get_git_info(project_path: Path) -> ProjectGitInfo:
    info = ProjectGitInfo()

    if not (project_path / ".git").exists():
        return info
    info.has_repo = True

    # branch
    ok, out = _run(["rev-parse", "--abbrev-ref", "HEAD"], project_path)
    if ok:
        info.branch = out

    # remote URL
    ok, out = _run(["remote", "get-url", "origin"], project_path)
    if ok:
        info.remote_url = out

    # last commit
    ok, out = _run(
        ["log", "-1", "--pretty=format:%h|||%s|||%ci"], project_path
    )
    if ok and "|||" in out:
        parts = out.split("|||", 2)
        info.last_commit_hash = parts[0]
        info.last_commit_msg  = parts[1][:80]
        info.last_commit_date = parts[2][:19] if len(parts) > 2 else ""

    # uncommitted changes
    ok, out = _run(["status", "--porcelain"], project_path)
    if ok:
        info.uncommitted = bool(out.strip())

    # un-pushed commit count
    if info.remote_url:
        ok, out = _run(["rev-list", "--count", "HEAD", "@{u}..HEAD"], project_path)
        if ok:
            try:
                info.ahead = int(out.strip())
            except ValueError:
                pass

    return info


# -- Auto-commit --------------------------------------------------------------

def auto_commit_step(
    project_path: Path,
    step_label: str,
    user_name: str = "",
    user_email: str = "",
) -> GitOpResult:
    """
    Called when a pipeline step completes.
    Stages metadata/ + _output/ + PROJECT_STATE.json and commits.
    """
    if not (project_path / ".git").exists():
        return GitOpResult(message="No repo — run git init first.")

    env_extra = {}
    if user_name:
        env_extra["GIT_AUTHOR_NAME"] = user_name
        env_extra["GIT_COMMITTER_NAME"] = user_name
    if user_email:
        env_extra["GIT_AUTHOR_EMAIL"] = user_email
        env_extra["GIT_COMMITTER_EMAIL"] = user_email

    # Stage: metadata/ + _output/ + state files + AI decision log (B-G4 / S-4)
    for pattern in ["metadata/", "_output/", "PROJECT_STATE.json", "PROJECT_MAESTRO.md",
                    "AI_DECISION_LOG.jsonl"]:
        target = project_path / pattern.rstrip("/")
        if target.exists():
            _run(["add", pattern], project_path)

    # Are there staged changes?
    ok, out = _run(["diff", "--cached", "--name-only"], project_path)
    if not ok or not out.strip():
        return GitOpResult(ok=True, message="No changes to commit.")

    safe_label = step_label[:60]
    msg = f"pipeline: {safe_label} completed"
    ok, commit_out = _run(["commit", "-m", msg], project_path, env_extra)
    if not ok:
        return GitOpResult(message=f"Commit failed: {commit_out}")

    return GitOpResult(ok=True, message=f"Auto-commit: {msg}")


def manual_commit(
    project_path: Path,
    message: str,
    user_name: str = "",
    user_email: str = "",
) -> GitOpResult:
    """Manual commit: stage all tracked files and commit."""
    if not (project_path / ".git").exists():
        return GitOpResult(message="No repo — run git init first.")

    env_extra = {}
    if user_name:
        env_extra["GIT_AUTHOR_NAME"] = user_name
        env_extra["GIT_COMMITTER_NAME"] = user_name
    if user_email:
        env_extra["GIT_AUTHOR_EMAIL"] = user_email
        env_extra["GIT_COMMITTER_EMAIL"] = user_email

    _run(["add", "-A"], project_path)

    ok, out = _run(["diff", "--cached", "--name-only"], project_path)
    if not ok or not out.strip():
        return GitOpResult(ok=True, message="No changes to commit.")

    ok, commit_out = _run(["commit", "-m", message or "update"], project_path, env_extra)
    if not ok:
        return GitOpResult(message=f"Commit failed: {commit_out}")
    return GitOpResult(ok=True, message=f"Commit successful: {message}")


# -- Remote management --------------------------------------------------------

def set_remote(project_path: Path, url: str) -> GitOpResult:
    """Add or update the origin remote."""
    if not (project_path / ".git").exists():
        return GitOpResult(message="No repo.")

    # check if it exists
    ok, _ = _run(["remote", "get-url", "origin"], project_path)
    if ok:
        ok2, out = _run(["remote", "set-url", "origin", url], project_path)
    else:
        ok2, out = _run(["remote", "add", "origin", url], project_path)

    if not ok2:
        return GitOpResult(message=f"Could not set remote: {out}")
    return GitOpResult(ok=True, message=f"Remote -> {url}")


_PUBLIC_REMOTE_HOSTS = (
    "github.com", "gitlab.com", "bitbucket.org", "codeberg.org",
    "sr.ht", "sourceforge.net",
)


def _remote_url(project_path: Path) -> str:
    """Best-effort fetch of origin's URL ('' if none)."""
    ok, out = _run(["remote", "get-url", "origin"], project_path)
    return out.strip() if ok else ""


def _remote_looks_public(url: str) -> bool:
    """Heuristic: does this remote URL point at a well-known public host?"""
    u = (url or "").lower()
    if not u:
        return False
    return any(host in u for host in _PUBLIC_REMOTE_HOSTS)


def push_project(project_path: Path, *, force_classified: bool = False) -> GitOpResult:
    """git push origin main (or master).

    W-A3: a CONFIDENTIAL or RESTRICTED customer project must not be pushed to
    a public hosting service (github.com / gitlab.com / …) without an
    explicit override. The previous code happily pushed customer IO lists,
    SCL, BOM, customer reports etc. anywhere the user had configured a
    remote — including a default-public personal GitHub.

    The override `force_classified=True` is reserved for callers who can
    prove the remote is enterprise/private (e.g. self-hosted GitLab) and
    have collected explicit human confirmation. The webgui surfaces this as
    an extra modal confirmation; CLI users pass it on the command line.
    """
    if not (project_path / ".git").exists():
        return GitOpResult(message="No repo.")

    if not force_classified:
        try:
            # Local import keeps project_git importable in environments without
            # the rest of the 05_SCRIPTS package.
            from data_classification_guard import (  # type: ignore
                normalize_classification, read_project_classification,
            )
            level = normalize_classification(read_project_classification(project_path))
        except Exception:
            # Fail-closed: if we cannot read the classification, treat the
            # project as CONFIDENTIAL.
            level = "CONFIDENTIAL"

        if level in ("CONFIDENTIAL", "RESTRICTED"):
            url = _remote_url(project_path)
            if _remote_looks_public(url):
                return GitOpResult(message=(
                    f"Push refused: project data_classification={level} but "
                    f"origin remote '{url}' is a public hosting service. "
                    "Move the project to an enterprise/private remote, or "
                    "pass force_classified=True after confirming the remote "
                    "is private. (W-A3, fail-closed)"
                ))
            if not url:
                return GitOpResult(message=(
                    f"Push refused: project data_classification={level} and "
                    "no origin remote is configured. Set a private remote "
                    "first. (W-A3, fail-closed)"
                ))

    # Get the branch name
    _, branch = _run(["rev-parse", "--abbrev-ref", "HEAD"], project_path)
    branch = branch.strip() or "main"

    ok, out = _run(["push", "-u", "origin", branch], project_path)
    if not ok:
        return GitOpResult(message=f"Push failed: {out}")
    return GitOpResult(ok=True, message=f"Push done -> origin/{branch}")


def pull_project(project_path: Path) -> GitOpResult:
    """git pull --rebase origin current-branch."""
    if not (project_path / ".git").exists():
        return GitOpResult(message="No repo.")
    _, branch = _run(["rev-parse", "--abbrev-ref", "HEAD"], project_path)
    branch = branch.strip() or "main"
    ok, out = _run(["pull", "--rebase", "origin", branch], project_path)
    if not ok:
        return GitOpResult(message=f"Pull failed: {out}")
    return GitOpResult(ok=True, message=f"Up to date with origin/{branch}")


# -- GitHub API ---------------------------------------------------------------

def create_github_repo(
    name: str,
    token: str,
    username: str,
    private: bool = True,
    description: str = "",
) -> GitOpResult:
    """
    Create a new private repo on GitHub with a PAT.
    Returns the clone URL on success.
    """
    if not token or not username:
        return GitOpResult(message="GitHub username and token required.")

    safe_name = re.sub(r"[^\w\-.]", "-", name)[:100]
    payload = json.dumps({
        "name": safe_name,
        "private": private,
        "description": description or f"AUTOMATION FACTORY — {safe_name}",
        "auto_init": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=payload, method="POST",
    )
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "AUTOMATION-FACTORY/3.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            clone_url = data.get("clone_url", "")
            return GitOpResult(
                ok=True,
                message=f"GitHub repo created: {clone_url}",
                repo_url=clone_url,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            err_msg = json.loads(body).get("message", body)
        except Exception:
            err_msg = body[:200]
        return GitOpResult(message=f"GitHub API error ({exc.code}): {err_msg}")
    except Exception as exc:
        return GitOpResult(message=f"Connection error: {exc}")


def test_github_token(token: str) -> GitOpResult:
    """Check whether the PAT is valid."""
    if not token:
        return GitOpResult(message="Token is empty.")
    req = urllib.request.Request("https://api.github.com/user")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "AUTOMATION-FACTORY/3.0")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            login = data.get("login", "?")
            return GitOpResult(ok=True, message=f"Token valid — user: {login}")
    except urllib.error.HTTPError as exc:
        return GitOpResult(message=f"Token invalid ({exc.code}).")
    except Exception as exc:
        return GitOpResult(message=f"Connection error: {exc}")
