"""
Factory I/O scene tag importer.

In Factory I/O: File -> Drivers -> (S7 driver selected) -> Export tag list
produces a CSV. This module reads that CSV and:
  1. Generates metadata/RD15_FactoryIO_Scene.md (scene summary + tag table)
  2. Enriches RD01_IO_List.md if present (adds new tags / comments)

Because CSV columns can vary between Factory I/O versions, flexible header
detection is used. Known format:
  Name,Description,DataType,Default Value,IO Type,Address

Unknown columns are ignored; at minimum "Name" and "DataType" are required.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..base import BridgeBase, BridgeStatus, BridgeResult


@dataclass
class SceneTag:
    name: str
    data_type: str = ""
    io_type: str = ""       # DI/DQ/AI/AQ or Input/Output
    address: str = ""
    description: str = ""

    @property
    def signal_type(self) -> str:
        """Short signal type compatible with RD01."""
        d = (self.data_type or "").lower()
        io = (self.io_type or "").lower()
        if "bool" in d:
            return "DI" if "in" in io else "DQ"
        if any(x in d for x in ("int", "real", "float", "word", "dword")):
            return "AI" if "in" in io else "AQ"
        return "UNK"


@dataclass
class SceneImportResult:
    tags: list[SceneTag] = field(default_factory=list)
    md_path: Optional[Path] = None
    rd01_enriched: bool = False
    warnings: list[str] = field(default_factory=list)


def parse_factoryio_csv(csv_path: Path) -> list[SceneTag]:
    """Parse a Factory I/O export CSV."""
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    # Delimiter detection: , ; or \t
    delim = ","
    first_line = text.splitlines()[0] if text else ""
    for d in [";", "\t", ","]:
        if d in first_line:
            delim = d
            break

    reader = csv.DictReader(text.splitlines(), delimiter=delim)
    tags: list[SceneTag] = []
    # Normalize column names: lower + trim + spaces -> _
    field_map = {}
    if reader.fieldnames:
        for fn in reader.fieldnames:
            norm = (fn or "").strip().lower().replace(" ", "_")
            field_map[norm] = fn

    def _get(row, *keys) -> str:
        for k in keys:
            real = field_map.get(k)
            if real and row.get(real) is not None:
                v = str(row[real]).strip()
                if v:
                    return v
        return ""

    for row in reader:
        name = _get(row, "name", "tag", "tag_name")
        if not name:
            continue
        tag = SceneTag(
            name=name,
            data_type=_get(row, "datatype", "data_type", "type"),
            io_type=_get(row, "io_type", "iotype", "direction", "sense"),
            address=_get(row, "address", "addr", "logical_address"),
            description=_get(row, "description", "desc", "comment"),
        )
        tags.append(tag)
    return tags


def render_rd15_markdown(
    tags: list[SceneTag],
    scene_name: str,
    project_name: str = "",
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "---",
        "rd_code: RD15",
        "title: Factory I/O Scene Tag List",
        f"scene_name: {scene_name}",
        f"project: {project_name}",
        f"generated: {ts}",
        "status: AUTO_GENERATED",
        "source: factoryio_scene_importer.py",
        "---",
        "",
        f"# RD15 — Factory I/O Scene: `{scene_name}`",
        "",
        f"Total tags: **{len(tags)}**",
        "",
        "## Tag Table",
        "",
        "| Tag | Type | I/O | Address | Signal Class | Description |",
        "|---|---|---|---|---|---|",
    ]
    for t in tags:
        lines.append(
            f"| `{t.name}` | {t.data_type or '-'} | {t.io_type or '-'} | "
            f"{t.address or '-'} | {t.signal_type} | {t.description or '-'} |"
        )

    # Grouped summary
    groups: dict[str, int] = {}
    for t in tags:
        groups[t.signal_type] = groups.get(t.signal_type, 0) + 1
    if groups:
        lines.extend([
            "",
            "## Signal Class Distribution",
            "",
        ])
        for k, v in sorted(groups.items()):
            lines.append(f"- **{k}**: {v}")

    lines.extend([
        "",
        "## Notes",
        "",
        "- This file was auto-generated from a Factory I/O scene tag CSV.",
        "- This file is included in the AI brief: SCL code generation uses",
        "  Factory I/O-compatible tag names and addresses.",
        "- If RD01_IO_List.md already exists, this file is complementary;",
        "  in case of conflict, RD01 takes precedence.",
    ])
    return "\n".join(lines) + "\n"


def enrich_rd01_with_scene(rd01_path: Path, tags: list[SceneTag]) -> bool:
    """Append a section to RD01 with scene tags.

    Does not modify the existing RD01; only appends a 'Factory I/O Scene
    Additions' section (idempotent: skips if section already present).
    """
    if not rd01_path.is_file():
        return False
    content = rd01_path.read_text(encoding="utf-8", errors="ignore")
    marker = "## Factory I/O Scene Additions"
    if marker in content:
        return False  # already present

    addendum = ["", "", marker, "",
                "_Automatically added by factoryio_bridge._",
                "",
                "| Tag | Type | I/O | Address |",
                "|---|---|---|---|"]
    for t in tags:
        addendum.append(
            f"| `{t.name}` | {t.data_type or '-'} | "
            f"{t.io_type or '-'} | {t.address or '-'} |"
        )
    addendum.append("")
    rd01_path.write_text(content.rstrip() + "\n".join(addendum) + "\n",
                          encoding="utf-8")
    return True


class FactoryIoSceneImporterBridge(BridgeBase):
    bridge_id = "factoryio_scene_importer"
    display_name = "Factory I/O Scene Importer"
    category = "factoryio"

    def detect(self) -> BridgeStatus:
        # Pure Python — no installation required, always ready
        return BridgeStatus.READY

    def import_scene_csv(
        self,
        csv_path: Path,
        project_path: Path,
        scene_name: Optional[str] = None,
    ) -> BridgeResult:
        result = BridgeResult(success=False)

        if not self.is_enabled():
            result.message = f"{self.display_name} toggle is OFF."
            return result

        csv_path = Path(csv_path)
        project_path = Path(project_path)

        if not csv_path.is_file():
            result.message = f"CSV file not found: {csv_path}"
            return result
        if not project_path.is_dir():
            result.message = f"Project folder not found: {project_path}"
            return result

        scene_name = scene_name or csv_path.stem
        try:
            tags = parse_factoryio_csv(csv_path)
        except Exception as e:
            result.message = f"CSV parse error: {e}"
            return result

        if not tags:
            result.message = "No tags found (CSV empty or format unrecognized)."
            return result

        self.status(f"{len(tags)} tags found, writing RD15...", "info")

        meta_dir = project_path / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        md_path = meta_dir / "RD15_FactoryIO_Scene.md"
        md_path.write_text(
            render_rd15_markdown(tags, scene_name, project_path.name),
            encoding="utf-8",
        )

        cfg = self.settings.get("bridges", {}).get("factoryio", {})
        if cfg.get("enrich_rd01_on_import", True):
            rd01 = meta_dir / "RD01_IO_List.md"
            try:
                enriched = enrich_rd01_with_scene(rd01, tags)
            except Exception as e:
                enriched = False
                result.warnings.append(f"RD01 enrich failed: {e}")
        else:
            enriched = False

        result.artifacts.append(md_path)
        result.details.append(f"RD15 written: {md_path.name}")
        result.details.append(f"Tag count: {len(tags)}")
        if enriched:
            result.details.append("RD01 enriched.")
        result.message = f"Scene import successful ({len(tags)} tags)."
        result.success = True
        return result


def main():
    import argparse
    p = argparse.ArgumentParser(description="Factory I/O Scene Importer")
    p.add_argument("--csv", required=True, help="Path to scene tag CSV")
    p.add_argument("--project", required=True, help="AUTOMATION_FACTORY project")
    p.add_argument("--scene-name", help="Scene name (default: CSV file stem)")
    args = p.parse_args()

    settings = {
        "bridges": {
            "enabled": {"factoryio_scene_importer": True},
            "factoryio": {"enrich_rd01_on_import": True},
        }
    }
    bridge = FactoryIoSceneImporterBridge(settings)
    res = bridge.import_scene_csv(
        Path(args.csv), Path(args.project), scene_name=args.scene_name,
    )
    print(res.message)
    for d in res.details:
        print(f"  - {d}")
    for w in res.warnings:
        print(f"  ! {w}")


if __name__ == "__main__":
    main()
