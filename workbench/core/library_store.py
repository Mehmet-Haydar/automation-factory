"""
library_store.py — Discover reusable function blocks under
06_KNOWLEDGE_BASE/blocks/<category>/*.scl with optional .meta.json sidecars.

Bootstraps the directory from examples/ on first run so the Library panel
isn't empty for new installations.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
BLOCKS_ROOT = FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "blocks"
CONTRACTS_ROOT = FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "contracts"

# ---------------------------------------------------------------------------
# Lifecycle yönetimi (S-15 / B-P1)
# ---------------------------------------------------------------------------

_LIFECYCLE_VALUES = frozenset({
    "DRAFT",
    "AUTO_VERIFIED_structural",
    "AUTO_VERIFIED_structural_plcrex",
    "PENDING_TIA_VERIFY",
    "VALIDATED",
    "FROZEN",
})


class LifecyclePromoteError(Exception):
    """Geçersiz veya kanıtsız lifecycle yükseltme girişimi (fail-closed)."""


def get_block_lifecycle(block_name: str) -> str:
    """Bloğun kontrattaki lifecycle değerini döndür.

    Kontrat bulunamazsa, okunamazsa veya alan yoksa fail-safe: ``"DRAFT"`` döner.
    Bu, bilinmeyen blokların her zaman DRAFT uyarısı üretmesini garantiler.

    Args:
        block_name: Kontrat dosyası stem'i (örn. ``"FB_Motor_DOL"``).

    Returns:
        Lifecycle string; geçersiz/eksik durumda ``"DRAFT"``.
    """
    try:
        candidates = list(CONTRACTS_ROOT.rglob(f"{block_name}.contract.json"))
        if not candidates:
            return "DRAFT"
        data = json.loads(candidates[0].read_text(encoding="utf-8"))
        raw = (data.get("block") or {}).get("lifecycle", "DRAFT")
        if raw not in _LIFECYCLE_VALUES:
            return "DRAFT"
        return raw
    except Exception:
        return "DRAFT"


def promote_to_validated(
    block_name: str,
    evidence_path: str,
    engineer_name: str,
) -> Path:
    """Promote a block's lifecycle to VALIDATED.

    Fail-closed: if the evidence_path is empty or does not exist, the promotion
    is refused (``LifecyclePromoteError`` is raised).

    Args:
        block_name:    Contract file stem (e.g. ``"FB_Motor_DOL"``).
        evidence_path: Path to a PLCSIM run log or test report file.
                       Empty string or non-existent path → refused.
        engineer_name: Name of the engineer approving the promotion (empty → refused).

    Returns:
        Path to the updated contract file.

    Raises:
        LifecyclePromoteError: if the evidence path or engineer name is missing.
        FileNotFoundError: if the contract file is not found.
    """
    # --- fail-closed: evidence and engineer name required ---
    if not evidence_path or not evidence_path.strip():
        raise LifecyclePromoteError(
            f"Lifecycle yükseltme reddedildi: '{block_name}' için kanıt yolu boş. "
            "PLCSIM koşum logu veya test raporu yolu zorunludur (B-P1 politikası)."
        )
    if not engineer_name or not engineer_name.strip():
        raise LifecyclePromoteError(
            f"Lifecycle yükseltme reddedildi: '{block_name}' için mühendis adı boş. "
            "Yükseltmeyi onaylayan mühendis adı zorunludur (B-P1 politikası)."
        )
    evidence = Path(evidence_path)
    if not evidence.exists():
        raise LifecyclePromoteError(
            f"Lifecycle yükseltme reddedildi: '{block_name}' — kanıt dosyası bulunamadı: "
            f"'{evidence_path}'. Gerçek bir PLCSIM/test raporu yolu belirtilmelidir."
        )

    candidates = list(CONTRACTS_ROOT.rglob(f"{block_name}.contract.json"))
    if not candidates:
        raise FileNotFoundError(
            f"Kontrat dosyası bulunamadı: '{block_name}.contract.json'"
        )
    contract_path = candidates[0]
    try:
        data = json.loads(contract_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LifecyclePromoteError(
            f"Kontrat okunamadı: '{contract_path}' — {exc}"
        ) from exc

    if "block" not in data:
        raise LifecyclePromoteError(
            f"Kontrat yapısı geçersiz: 'block' alanı yok — '{contract_path}'"
        )

    data["block"]["lifecycle"] = "VALIDATED"
    data["block"]["validated_by"] = engineer_name.strip()
    data["block"]["validated_date"] = str(date.today())
    data["block"]["validated_evidence"] = str(evidence_path).strip()

    contract_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return contract_path

# ---------------------------------------------------------------------------
# IP Sınıflandırma Koruyucusu (I-1 fix)
# ---------------------------------------------------------------------------

_RESTRICTED_LEVELS = {"CONFIDENTIAL", "RESTRICTED"}
_KNOWN_LEVELS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}


class IPClassificationError(Exception):
    """CONFIDENTIAL/RESTRICTED kaynak kütüphaneye eklenemez (IP sızıntı koruyucusu)."""


def _check_source_classification(src_path: Path, project_root: Path) -> None:
    """Kaynak dosyanın proje sınıflandırmasını kontrol et; CONFIDENTIAL/RESTRICTED ise reddet.

    Fail-closed: PROJECT_STATE.json yoksa, alan yoksa veya parse hatası olursa
    CONFIDENTIAL varsayılır ve kopyalama reddedilir.

    Args:
        src_path:     Kütüphaneye kopyalanmak istenen kaynak .scl dosyası.
        project_root: PROJECT_STATE.json'ı içeren proje kök dizini.

    Raises:
        IPClassificationError: Sınıflandırma CONFIDENTIAL veya RESTRICTED ise.
    """
    classification = "CONFIDENTIAL"  # fail-closed varsayılan
    try:
        state_file = project_root / "PROJECT_STATE.json"
        if state_file.is_file():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            raw = (state.get("data_classification") or "").strip().upper()
            if raw in _KNOWN_LEVELS:
                classification = raw
            # Tanınmayan değer → fail-closed: CONFIDENTIAL kalır
    except Exception:
        pass  # Parse hatası → fail-closed: CONFIDENTIAL kalır

    if classification in _RESTRICTED_LEVELS:
        raise IPClassificationError(
            f"CONFIDENTIAL/RESTRICTED kaynak kütüphaneye eklenemez: "
            f"{src_path.name!r} (sınıflandırma={classification!r}, "
            f"proje={project_root}). "
            "IP sızıntısı koruması aktif — yalnızca PUBLIC veya INTERNAL "
            "sınıflandırmalı kaynaklar global kütüphaneye kopyalanabilir."
        )


@dataclass
class LibraryBlock:
    name: str
    category: str
    version: str
    platform: str
    scl_path: Path
    meta_path: Optional[Path]
    description: str
    ports: list[dict] = field(default_factory=list)


def list_blocks(category: Optional[str] = None) -> list[LibraryBlock]:
    """Scan BLOCKS_ROOT and return discovered blocks. Optionally filter by category."""
    _bootstrap_if_empty()
    if not BLOCKS_ROOT.is_dir():
        return []
    out: list[LibraryBlock] = []
    cats = [BLOCKS_ROOT / category] if category else [
        p for p in BLOCKS_ROOT.iterdir() if p.is_dir()
    ]
    for cat_dir in cats:
        if not cat_dir.is_dir():
            continue
        for scl in sorted(cat_dir.glob("*.scl")):
            meta_path = scl.with_suffix(".meta.json")
            meta = _read_meta(meta_path) if meta_path.exists() else {}
            out.append(LibraryBlock(
                name=meta.get("name") or scl.stem,
                category=cat_dir.name,
                version=meta.get("version", "1.0.0"),
                platform=meta.get("platform", ""),
                scl_path=scl,
                meta_path=meta_path if meta_path.exists() else None,
                description=meta.get("description", _scl_one_liner(scl)),
                ports=meta.get("ports", []),
            ))
    return out


def import_block_to_project(block: LibraryBlock, project_root: Path) -> Path:
    """Copy block.scl into <project>/SCL/. Returns the destination path.

    Raises FileExistsError if the destination already exists — caller decides
    whether to overwrite.
    Raises IPClassificationError if the project is CONFIDENTIAL/RESTRICTED —
    caller must not silently swallow this; it is a hard IP-protection gate.
    """
    # I-1 fix: reverse-direction classification check — before the project sends
    # data to the library, the project's classification is checked; a
    # CONFIDENTIAL/RESTRICTED project is refused.
    _check_source_classification(block.scl_path, project_root)

    target_dir = project_root / "SCL"
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / block.scl_path.name
    if dest.exists():
        raise FileExistsError(f"{dest.name} already exists in SCL/")
    shutil.copy2(str(block.scl_path), str(dest))
    return dest


# ─────────────────────────────────────────────────────────────────────────────

def _read_meta(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _scl_one_liner(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:20]:
            line = line.strip()
            if line.startswith("//") and len(line) > 2:
                return line.lstrip("/").strip()
    except Exception:
        pass
    return path.stem.replace("_", " ")


_BOOTSTRAP_SEEDS = (
    (
        "motor",
        FACTORY_ROOT / "examples" / "Kunde_Mueller_Conveyor_Retrofit" / "_output" / "FB_Motor_Conveyor.scl",
        {
            "name": "FB_Motor_Standard",
            "version": "1.0.0",
            "platform": "S7_1500",
            "description": "Standard motor FB (DOL drive, run feedback, fault).",
            "ports": [
                {"name": "Enable", "type": "BOOL", "direction": "IN"},
                {"name": "Drive",  "type": "BOOL", "direction": "OUT"},
                {"name": "Run",    "type": "BOOL", "direction": "IN"},
            ],
        },
    ),
)


def _bootstrap_if_empty() -> None:
    """On first run, seed blocks/ with a sample so the panel isn't empty.

    I-1 fix: for each seed the source file's project classification is checked.
    A CONFIDENTIAL/RESTRICTED source is silently skipped (bootstrap is
    best-effort; it is not an IP leak).
    """
    try:
        if BLOCKS_ROOT.exists() and any(BLOCKS_ROOT.iterdir()):
            return
        BLOCKS_ROOT.mkdir(parents=True, exist_ok=True)
        for category, src, meta in _BOOTSTRAP_SEEDS:
            if not src.exists():
                continue
            # I-1 fix: Seed'in geldiği proje dizinini proje root olarak kullan.
            # Kaynak CONFIDENTIAL/RESTRICTED ise bu seed atlanır (sessiz skip —
            # bootstrap best-effort; IPClassificationError yutulur, not fırlatılır).
            project_root_for_seed = src.parent
            # Seed dosyası projenin içindeyse _output altında olabilir; gerçek proje
            # root'unu bul: PROJECT_STATE.json olan en yakın ata dizin.
            for ancestor in [src.parent, *src.parents]:
                if (ancestor / "PROJECT_STATE.json").is_file():
                    project_root_for_seed = ancestor
                    break
            try:
                _check_source_classification(src, project_root_for_seed)
            except IPClassificationError:
                # CONFIDENTIAL/RESTRICTED seed atlanır — IP koruması aktif.
                continue

            dest_dir = BLOCKS_ROOT / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{meta['name']}.scl"
            shutil.copy2(str(src), str(dest))
            (dest.with_suffix(".meta.json")).write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
    except Exception:
        # Bootstrap is best-effort; the empty panel is acceptable.
        pass
