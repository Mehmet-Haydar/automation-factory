"""
project_manager.py — Manages the customer project folder.

The Factory folder (FACTORY_ROOT) and the customer project are separate.
Only customer project files are visible in the GUI.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .factory_reader import FACTORY_ROOT, detect_gate

# Canonical project folder skeleton — single source of truth is
# script_project_init.PROJECT_FOLDERS (the CLI initializer). We import it so the
# GUI's "New Project" produces the SAME layout as `script_project_init.py`.
# 2026-07-07 restructure: ONLY the living folders — a measured E2E run left
# every numbered template folder empty, so they were removed (two parallel
# worlds confused the workbench). The fallback copy is only used if that
# module can't be imported; keep it in sync.
try:  # 05_SCRIPTS is on sys.path when the webgui runs
    from script_project_init import PROJECT_FOLDERS  # type: ignore
except Exception:
    PROJECT_FOLDERS = [
        "_raw", "_raw/legacy_code", "_raw/drawings", "_raw/photos",
        "_raw/docs",
        "_input", "_output", "metadata", "REPORTS", "_delivery",
    ]

# Folders to show in customer projects (Factory folders are NEVER shown)
VISIBLE_DIRS = {"RD", "SCL", "INPUT", "REPORTS", "DOCS", "INPUT_FILES"}

# Factory's own folders — never shown in the file tree
FACTORY_DIRS = {
    "01_GLOBAL_STANDARDS", "02_PROJECT_TYPES", "03_DOMAIN_TOOLS",
    "04_AI_PROMPTS", "05_SCRIPTS", "06_KNOWLEDGE_BASE", "07_PROJECT_TEMPLATE",
    "08_METADATA_INPUT", "09_HARDWARE_LIBRARY", "_archive", "docs", "examples",
    "workbench",
}

SETTINGS_FILE = FACTORY_ROOT / ".workbench_settings.json"


class ProjectManager:
    def __init__(self) -> None:
        self.project_root: Optional[Path] = None
        self.gate: int = 1
        self._settings: dict = self._load_settings()
        last = self._settings.get("last_project")
        if last and Path(last).exists():
            self.open_project(Path(last))

    # ------------------------------------------------------------------
    # Open / create project
    # ------------------------------------------------------------------

    def open_project(self, path: Path) -> bool:
        """Opens an existing project."""
        if not path.is_dir():
            return False
        self.project_root = path
        self.gate = detect_gate(path)
        self._settings["last_project"] = str(path)
        self._save_settings()
        return True

    def create_project(self, parent: Path, name: str) -> Optional[Path]:
        """Create a new customer project with the canonical folder skeleton.

        Produces the SAME layout as `script_project_init.py` (the CLI
        initializer) so GUI-created and script-created projects are identical:
        _raw (customer inputs: legacy code / drawings / photos / docs),
        _input (hardware exchange), _output (generated code incl. _output/scl),
        metadata (RD01..RD14 + decisions), REPORTS, _delivery. The 14 RD
        templates are copied into metadata/ so the engineer/AI has files
        to fill.
        """
        target = parent / name
        if target.exists():
            return None
        target.mkdir(parents=True, exist_ok=True)
        # 1) Canonical folder skeleton (single source: PROJECT_FOLDERS).
        for folder in PROJECT_FOLDERS:
            (target / folder).mkdir(parents=True, exist_ok=True)
        # 2) Seed the 14-Point RD templates into metadata/.
        template_md = FACTORY_ROOT / "07_PROJECT_TEMPLATE" / "metadata_template"
        if template_md.is_dir():
            for tmpl in sorted(template_md.glob("RD*.md")):
                try:
                    shutil.copy2(tmpl, target / "metadata" / tmpl.name)
                except Exception:
                    pass
        # 3) Best-effort project-level docs from the template (maestro/README).
        template = FACTORY_ROOT / "07_PROJECT_TEMPLATE"
        for src_name, dst_name in (
            ("PROJECT_MAESTRO_TEMPLATE.md", "PROJECT_MAESTRO.md"),
            ("README.md", "README.md"),
        ):
            src = template / src_name
            if src.is_file() and not (target / dst_name).exists():
                try:
                    shutil.copy2(src, target / dst_name)
                except Exception:
                    pass
        self.open_project(target)
        return target

    # ------------------------------------------------------------------
    # File tree
    # ------------------------------------------------------------------

    def get_tree_items(self) -> list[dict]:
        """
        Returns visible items in the project folder.
        Each item: {path, name, is_dir, depth}
        Factory folders are filtered out.
        """
        if not self.project_root:
            return []
        return self._walk(self.project_root, depth=0)

    def _walk(self, path: Path, depth: int) -> list[dict]:
        items = []
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return items

        for entry in entries:
            if entry.name.startswith("."):
                continue
            if depth == 0 and entry.name in FACTORY_DIRS:
                continue
            if depth == 0 and entry.is_dir() and entry.name not in VISIBLE_DIRS:
                # If a folder other than RD/SCL/INPUT/REPORTS exists in the customer project,
                # show it too (the user may have created it)
                pass
            items.append({
                "path": entry,
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "depth": depth,
            })
            if entry.is_dir():
                items.extend(self._walk(entry, depth + 1))
        return items

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def relative_path(self, file_path: Path) -> str:
        if self.project_root and self.project_root in file_path.parents:
            return file_path.relative_to(self.project_root).as_posix()
        return file_path.name

    def read_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def write_file(self, path: Path, content: str) -> bool:
        try:
            path.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def create_file(self, parent: Path, name: str) -> Optional[Path]:
        new_file = parent / name
        if new_file.exists():
            return None
        try:
            new_file.touch()
            return new_file
        except Exception:
            return None

    def create_folder(self, parent: Path, name: str) -> Optional[Path]:
        new_dir = parent / name
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            return new_dir
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _load_settings(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_settings(self) -> None:
        try:
            SETTINGS_FILE.write_text(
                json.dumps(self._settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def save_api_settings(self, provider: str, model: str, api_key: str) -> None:
        self._settings["api_provider"] = provider
        self._settings["api_model"] = model
        if api_key:
            self._settings["api_key_" + provider] = api_key
        self._save_settings()

    def get_api_settings(self) -> dict:
        """Return the active provider/model/key.

        The active webgui (`05_SCRIPTS/factory_web.py`) owns the
        authoritative key store (.gui_settings.json). We prefer that file
        when it exists so the user only ever enters their API key once.
        The legacy .workbench_settings.json is consulted as a fallback for
        older installs.

        Note: post-W7 the value stored on disk for an API key is the opaque
        sentinel ``__keyring__`` — the actual key lives in the OS keystore.
        Callers that need the plaintext should go through
        ``factory_web.Api._resolve_api_key`` instead of this helper.
        """
        gui_path = FACTORY_ROOT / ".gui_settings.json"
        if gui_path.exists():
            try:
                gui = json.loads(gui_path.read_text(encoding="utf-8"))
                provider = (gui.get("ai_provider") or "anthropic").strip()
                model = (gui.get("ai_model") or "").strip() or "claude-sonnet-4-6"
                key = (gui.get("api_keys") or {}).get(provider, "")
                # I-A2: never hand the opaque keystore sentinel back as if it
                # were a real API key — downstream callers would forward the
                # literal string "__keyring__" to the provider. Resolve it
                # from the OS keystore here. If `keyring` is unavailable, we
                # simply report no key and let the caller handle it.
                if key == "__keyring__":
                    try:
                        import keyring  # type: ignore
                        key = keyring.get_password(
                            "AUTOMATION_FACTORY_webgui", provider,
                        ) or ""
                    except Exception:
                        key = ""
                return {"provider": provider, "model": model, "api_key": key}
            except Exception:
                pass
        return {
            "provider": self._settings.get("api_provider", "anthropic"),
            "model": self._settings.get("api_model", "claude-sonnet-4-6"),
            "api_key": self._settings.get(
                "api_key_" + self._settings.get("api_provider", "anthropic"), ""
            ),
        }
