"""M-A4 regresyonu — save_user_prompt, title icindeki yeni satir / '---' /
quote karakterlerini sanitize etmeli; aksi halde dosya YAML frontmatter'i
bozulup prompt-library refresh'inde gorunmez olur.
"""

from __future__ import annotations

from pathlib import Path

import yaml

import workbench.core.factory_reader as fr
from workbench.core.prompt_writer import save_user_prompt


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"missing frontmatter delimiter in {path}"
    end = text.find("\n---", 4)
    block = text[3:end].lstrip("\n")
    return yaml.safe_load(block) or {}


def test_title_with_newline_does_not_break_frontmatter(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(fr.PROMPT_DIRS, "analyze", tmp_path)
    p = save_user_prompt(
        category="analyze",
        title="Line one\nLine two\nLine three",
        body="hello",
    )
    fm = _read_frontmatter(p)
    assert "Line one" in fm["title"]
    assert "\n" not in fm["title"]
    # downstream consumers expect known keys to exist
    assert fm["category"] == "analyze"


def test_title_with_leading_dashes_does_not_terminate_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setitem(fr.PROMPT_DIRS, "analyze", tmp_path)
    p = save_user_prompt(category="analyze", title="--- end of section", body="x")
    fm = _read_frontmatter(p)
    # Frontmatter must still be parseable and contain a title.
    assert "title" in fm
    assert "end of section" in fm["title"]


def test_title_with_colon_round_trips(tmp_path, monkeypatch):
    monkeypatch.setitem(fr.PROMPT_DIRS, "analyze", tmp_path)
    p = save_user_prompt(category="analyze", title="Bosch: north panel", body="x")
    fm = _read_frontmatter(p)
    assert fm["title"] == "Bosch: north panel"


def test_title_with_quote_round_trips(tmp_path, monkeypatch):
    monkeypatch.setitem(fr.PROMPT_DIRS, "analyze", tmp_path)
    p = save_user_prompt(category="analyze", title='the "north" panel', body="x")
    fm = _read_frontmatter(p)
    assert fm["title"] == 'the "north" panel'


def test_empty_title_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setitem(fr.PROMPT_DIRS, "analyze", tmp_path)
    p = save_user_prompt(category="analyze", title="   ", body="x")
    fm = _read_frontmatter(p)
    assert fm["title"] == "User Prompt"
