"""W-A3 regresyonu — push_project, CONFIDENTIAL/RESTRICTED veriyi public
git remote'a (github.com vb.) sessizce push etmemeli.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import project_git


def _make_repo(tmp_path: Path, *, classification: str = "PUBLIC", remote: str = "") -> Path:
    """Fake project directory with a .git folder and an optional PROJECT_STATE."""
    (tmp_path / ".git").mkdir()
    if classification:
        (tmp_path / "PROJECT_STATE.json").write_text(
            json.dumps({"data_classification": classification}), encoding="utf-8",
        )
    return tmp_path


def _patch_git(monkeypatch, *, remote_url: str = "", push_succeeds: bool = True):
    """Stub project_git._run so no real git executable is needed."""
    def fake_run(args, project_path):
        if args[:3] == ["remote", "get-url", "origin"]:
            if remote_url:
                return (True, remote_url)
            return (False, "")
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return (True, "main")
        if args[:1] == ["push"]:
            return (push_succeeds, "ok" if push_succeeds else "rejected")
        return (False, "unhandled in test")
    monkeypatch.setattr(project_git, "_run", fake_run)


def test_confidential_to_github_is_refused(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, classification="CONFIDENTIAL")
    _patch_git(monkeypatch, remote_url="https://github.com/me/secret.git")
    r = project_git.push_project(repo)
    assert r.ok is False
    assert "github.com" in r.message
    assert "CONFIDENTIAL" in r.message


def test_restricted_to_gitlab_is_refused(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, classification="RESTRICTED")
    _patch_git(monkeypatch, remote_url="git@gitlab.com:org/proj.git")
    r = project_git.push_project(repo)
    assert r.ok is False
    assert "RESTRICTED" in r.message


def test_confidential_to_private_remote_allowed(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, classification="CONFIDENTIAL")
    _patch_git(monkeypatch, remote_url="git@gitlab.internal.acme:org/proj.git")
    r = project_git.push_project(repo)
    assert r.ok is True


def test_public_classification_pushes_anywhere(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, classification="PUBLIC")
    _patch_git(monkeypatch, remote_url="https://github.com/me/oss.git")
    r = project_git.push_project(repo)
    assert r.ok is True


def test_no_remote_with_confidential_is_refused(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, classification="CONFIDENTIAL")
    _patch_git(monkeypatch, remote_url="")
    r = project_git.push_project(repo)
    assert r.ok is False
    assert "no origin remote" in r.message.lower()


def test_force_classified_bypass(tmp_path, monkeypatch):
    """Explicit user confirmation overrides the guard (e.g. private GitHub
    Enterprise that happens to use github.com URL form)."""
    repo = _make_repo(tmp_path, classification="CONFIDENTIAL")
    _patch_git(monkeypatch, remote_url="https://github.com/me/secret.git")
    r = project_git.push_project(repo, force_classified=True)
    assert r.ok is True


def test_missing_classification_treated_as_confidential(tmp_path, monkeypatch):
    """Fail-closed: no PROJECT_STATE.json at all -> treat as CONFIDENTIAL."""
    (tmp_path / ".git").mkdir()
    _patch_git(monkeypatch, remote_url="https://github.com/me/oops.git")
    r = project_git.push_project(tmp_path)
    assert r.ok is False
    assert "CONFIDENTIAL" in r.message
