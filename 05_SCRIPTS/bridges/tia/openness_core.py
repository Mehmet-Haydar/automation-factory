"""
TIA Openness shared core.

Used by both V19 and V20 bridges. Pythonnet and Siemens.Engineering DLL
are loaded at runtime — there is NO module-level import, so the file
can still be imported when pythonnet is missing.

Typical flow:
    core = OpennessCore(dll_path)        # calls clr.AddReference
    core.start_portal(with_ui=True)
    proj = core.open_project(ap_path)
    plc  = core.find_plc(proj, "PLC_1")
    res  = core.import_scl_files(plc, [scl1, scl2, ...])
    cres = core.compile_plc(plc)
    core.close_project(proj)
    core.stop_portal()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CompileMessage:
    severity: str      # "Error" | "Warning" | "Info"
    text: str
    block: str = ""


@dataclass
class CompileSummary:
    state: str = ""    # "Success" / "SuccessWithWarnings" / "Error" / ...
    errors: int = 0
    warnings: int = 0
    infos: int = 0
    messages: list[CompileMessage] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.errors == 0


@dataclass
class ImportSummary:
    sources_added: list[str] = field(default_factory=list)
    blocks_generated: list[str] = field(default_factory=list)
    skipped_safety: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class OpennessError(RuntimeError):
    """Shared exception for all Openness-related errors."""


class OpennessCore:
    """Shared Openness wrapper for V19 and V20.

    Pythonnet is only loaded when the constructor is called. Raises
    OpennessError if the DLL path is invalid or pythonnet is missing.
    """

    def __init__(self, dll_path: Path):
        self.dll_path = Path(dll_path)
        if not self.dll_path.is_file():
            raise OpennessError(f"Siemens.Engineering.dll not found: {self.dll_path}")

        # Lazy import — this line raises if pythonnet is not installed
        try:
            import clr  # type: ignore
        except ImportError as e:
            raise OpennessError(
                "pythonnet not installed. Install: pip install pythonnet"
            ) from e

        try:
            clr.AddReference(str(self.dll_path))
            import Siemens.Engineering as tia  # type: ignore
            import Siemens.Engineering.HW as hw  # type: ignore
            import Siemens.Engineering.SW as sw  # type: ignore
            from System.IO import FileInfo, DirectoryInfo  # type: ignore
        except Exception as e:
            raise OpennessError(f"Siemens.Engineering could not load: {e}") from e

        self._tia = tia
        self._hw = hw
        self._sw = sw
        self._FileInfo = FileInfo
        self._DirectoryInfo = DirectoryInfo
        self._portal = None  # Siemens.Engineering.TiaPortal instance

    # -- portal lifecycle -------------------------------------------------
    def start_portal(self, with_ui: bool = True):
        """Start (or attach to) TIA Portal. with_ui=False is headless mode.

        A cached portal is probed first — the user may have closed the
        portal window between runs, which leaves a stale handle behind.

        Attach-before-start (2026-06-10 live finding): a previous run leaves
        the project open in the portal for inspection. A NEW process (GUI
        restart, second send) starting a second portal cannot open that
        project — "already been opened by user X". Attaching to the running
        portal reuses both the portal and the open project handle.
        """
        if self._portal is not None:
            try:
                _ = self._portal.Projects  # probe: portal process alive?
                return self._portal
            except Exception:
                self._portal = None

        try:
            candidates = []
            for proc in list(self._tia.TiaPortal.GetProcesses()):
                try:
                    portal = proc.Attach()
                    open_projects = 0
                    try:
                        open_projects = sum(1 for _ in portal.Projects)
                    except Exception:
                        pass
                    candidates.append((open_projects, portal))
                except Exception:
                    continue
            if candidates:
                # Prefer the portal that holds open projects — that is the
                # one a previous run left for inspection; an empty stray
                # portal would just hit the project lock again.
                candidates.sort(key=lambda t: t[0], reverse=True)
                self._portal = candidates[0][1]
                return self._portal
        except Exception:
            pass

        mode = self._tia.TiaPortalMode.WithUserInterface if with_ui else \
               self._tia.TiaPortalMode.WithoutUserInterface
        self._portal = self._tia.TiaPortal(mode)
        return self._portal

    def stop_portal(self) -> None:
        if self._portal is None:
            return
        try:
            self._portal.Dispose()
        except Exception:
            pass
        self._portal = None

    # -- project ----------------------------------------------------------
    def open_project(self, ap_path: Path):
        """Open an existing .ap{N} file.

        If the same project is already open in this portal (kept open from
        a previous run for inspection), the open handle is reused — Openness
        refuses to open a project twice.
        """
        if self._portal is None:
            raise OpennessError("Call start_portal() first.")
        p = Path(ap_path)
        if not p.is_file():
            raise OpennessError(f"Project file not found: {p}")
        try:
            for proj in list(self._portal.Projects):
                try:
                    if Path(str(proj.Path.FullName)).resolve() == p.resolve():
                        return proj
                except Exception:
                    continue
        except Exception:
            pass
        return self._portal.Projects.Open(self._FileInfo(str(p)))

    def close_project(self, project) -> None:
        try:
            project.Close()
        except Exception:
            pass

    def save_project(self, project) -> None:
        try:
            project.Save()
        except Exception as e:
            raise OpennessError(f"Project could not be saved: {e}") from e

    # -- find PLC ---------------------------------------------------------
    def find_plc(self, project, plc_name: str = "PLC_1"):
        """Return the PLC device item with the given name.

        PlcSoftware is not a service of DeviceItem itself — it must be
        reached through the SoftwareContainer feature service
        (Siemens.Engineering.HW.Features.SoftwareContainer). CPU items can
        also sit one level deeper (rack/rail), so the scan is recursive.
        """
        try:
            import Siemens.Engineering.HW.Features as hwf  # type: ignore
            SoftwareContainer = hwf.SoftwareContainer
        except Exception as e:
            raise OpennessError(f"SoftwareContainer could not load: {e}") from e

        def _plc_software(item):
            try:
                container = item.GetService[SoftwareContainer]()
            except Exception:
                return None
            if container is None:
                return None
            software = container.Software
            return software if isinstance(software, self._sw.PlcSoftware) else None

        def _scan(items, device):
            for item in items:
                sw_target = _plc_software(item)
                if sw_target is not None:
                    if plc_name == "" or item.Name == plc_name or device.Name == plc_name:
                        return item, sw_target
                found = _scan(item.DeviceItems, device)
                if found != (None, None):
                    return found
            return None, None

        for device in project.Devices:
            found = _scan(device.DeviceItems, device)
            if found != (None, None):
                return found
        return None, None

    # -- SCL import -------------------------------------------------------
    def _find_block(self, group, name: str):
        """Recursively find a program block by name (block groups nest)."""
        try:
            blk = group.Blocks.Find(name)
            if blk is not None:
                return blk
        except Exception:
            pass
        try:
            for sub in group.Groups:
                blk = self._find_block(sub, name)
                if blk is not None:
                    return blk
        except Exception:
            pass
        return None

    def import_scl_files(
        self,
        plc_software,
        scl_files: list[Path],
        skip_safety: bool = True,
        safety_block_names: Optional[set[str]] = None,
        on_file=None,
    ) -> ImportSummary:
        """Add SCL files to the PLC as external sources + convert to blocks.

        When ``skip_safety`` is on, F-blocks (RD05 safety) are never imported.
        ``safety_block_names`` is the authoritative list of declared safety
        block/function names (from RD05). If omitted, it is auto-discovered
        from the project's ``metadata/RD05_*.md``. Detection is **fail-closed**:
        a file that cannot be inspected is treated as safety and skipped.

        ``on_file(index, total, name)`` is an optional progress callback,
        called before each file is processed (1-based index); exceptions in
        it never abort the import.
        """
        if plc_software is None:
            raise OpennessError("PLC software handle missing (find_plc call failed).")

        summary = ImportSummary()
        ext_grp = plc_software.ExternalSourceGroup
        block_grp = plc_software.BlockGroup

        if skip_safety and safety_block_names is None:
            safety_block_names = _discover_rd05_names(scl_files)

        total = len(scl_files)
        for idx, scl in enumerate(scl_files, start=1):
            scl = Path(scl)
            if on_file:
                try:
                    on_file(idx, total, scl.name)
                except Exception:
                    pass
            if not scl.is_file():
                summary.warnings.append(f"Skipped (missing): {scl}")
                continue

            if skip_safety:
                cls = _safety_classification(scl, safety_block_names)
                if cls == "safety":
                    summary.skipped_safety.append(scl.name)
                    continue
                if cls == "uncertain":
                    # Fail-closed: cannot confirm this is a standard block.
                    summary.skipped_safety.append(
                        f"{scl.name} (uncertain — manual review)"
                    )
                    continue

            try:
                # Re-runs: a leftover source with the same name makes
                # CreateFromFile throw — drop it first.
                try:
                    existing = ext_grp.ExternalSources.Find(scl.name)
                    if existing is not None:
                        existing.Delete()
                except Exception:
                    pass
                # CreateFromFile signature: (string name, string path).
                # The name MUST keep the extension — Openness derives the
                # source type (.scl/.db/.awl) from it.
                ext_src = ext_grp.ExternalSources.CreateFromFile(
                    scl.name, str(scl)
                )
                summary.sources_added.append(scl.name)
                # External source -> block conversion
                try:
                    # Re-import contract: generated blocks are replaced on
                    # every run. A leftover block of a mismatching shape
                    # (e.g. half-generated by an earlier failed run) makes
                    # generation throw "Type conflict: ... cannot be
                    # overwritten" — drop the old block first. File names
                    # equal block names in this pipeline (FB_X.scl -> FB_X).
                    try:
                        old = self._find_block(block_grp, scl.stem)
                        if old is not None:
                            old.Delete()
                    except Exception:
                        pass
                    ext_src.GenerateBlocksFromSource()
                    summary.blocks_generated.append(scl.name)
                except Exception as e:
                    summary.failed.append(scl.name)
                    summary.warnings.append(f"Block generation error {scl.name}: {e}")
            except Exception as e:
                summary.failed.append(scl.name)
                summary.warnings.append(f"Import error {scl.name}: {e}")

        return summary

    # -- tag table import ---------------------------------------------------
    def import_tag_table(
        self, plc_software, xml_path: Path, project=None
    ) -> "tuple[list[str], list[str]]":
        """Import a PlcTagTable XML (tia_tag_export output) into the PLC.

        ImportOptions.Override replaces an existing table of the same name,
        so re-runs are idempotent. Returns (table_names, notes). Raises
        OpennessError on failure — the bridge decides whether tags are fatal
        (the send_to_tia path treats them as a loud warning, not a stop).

        Comment-culture handling (2026-06-10 live finding): Openness refuses
        the whole import when a comment Culture is not a project language
        ("culture 'de-DE' does not exist within the current project"). When
        ``project`` is given, the XML cultures are rewritten to the project's
        editing language up front; if the import still fails on a culture
        error, the comments are dropped and the import retried — tags with
        addresses always beat comments.
        """
        if plc_software is None:
            raise OpennessError("PLC software handle missing (find_plc call failed).")
        xml = Path(xml_path)
        if not xml.is_file():
            raise OpennessError(f"Tag table XML not found: {xml}")

        notes: list[str] = []
        xml_text = xml.read_text(encoding="utf-8", errors="ignore")
        work = xml

        if project is not None and "<Culture>" in xml_text:
            culture = _project_editing_culture(project)
            if culture and f"<Culture>{culture}</Culture>" not in xml_text:
                xml_text = _rewrite_tag_xml_culture(xml_text, culture)
                work = xml.with_name(xml.stem + "_adapted.xml")
                work.write_text(xml_text, encoding="utf-8")
                notes.append(
                    f"Tag comment culture adapted to project language: {culture}")

        def _do_import(path: Path):
            group = plc_software.TagTableGroup
            return group.TagTables.Import(
                self._FileInfo(str(path)), self._tia.ImportOptions.Override
            )

        try:
            imported = _do_import(work)
        except Exception as e:
            if "culture" in str(e).lower() and "<Culture>" in xml_text:
                # Last resort: ship the tags without comments.
                stripped = _strip_tag_comments(xml_text)
                work = xml.with_name(xml.stem + "_nocomments.xml")
                work.write_text(stripped, encoding="utf-8")
                try:
                    imported = _do_import(work)
                    notes.append(
                        "Tag comments DROPPED — the project accepts none of "
                        "the comment cultures. Tags + addresses imported.")
                except Exception as e2:
                    raise OpennessError(
                        f"Tag table import failed ({xml.name}): {e2}") from e2
            else:
                raise OpennessError(
                    f"Tag table import failed ({xml.name}): {e}") from e

        names: list[str] = []
        try:
            for t in imported or []:
                try:
                    names.append(str(t.Name))
                except Exception:
                    pass
        except TypeError:
            pass  # some versions return void — table name comes from the XML
        return names, notes

    # -- compile ----------------------------------------------------------
    def compile_plc(self, plc_target) -> CompileSummary:
        """Compile the PLC; return result as a CompileSummary.

        ``plc_target`` should be the PlcSoftware handle (software compile —
        validates imported blocks). A DeviceItem would only compile hardware.
        """
        try:
            ICompilable = self._tia.Compiler.ICompilable
        except Exception:
            # Namespace differs in some versions
            try:
                import Siemens.Engineering.Compiler as comp  # type: ignore
                ICompilable = comp.ICompilable
            except Exception as e:
                raise OpennessError(f"ICompilable not found: {e}") from e

        try:
            compilable = plc_target.GetService[ICompilable]()
            result = compilable.Compile()
        except Exception as e:
            raise OpennessError(f"Compile failed: {e}") from e

        return _summarize_compile_result(result)


# -- helpers --------------------------------------------------------------

import re
import xml.etree.ElementTree as _ET


def _project_editing_culture(project) -> str:
    """Read the project's editing-language culture name ('de-DE') via
    Openness; empty string when unreadable (caller falls back to retry)."""
    try:
        culture = project.LanguageSettings.EditingLanguage.Culture
    except Exception:
        return ""
    for attr in ("Name", None):
        try:
            val = str(getattr(culture, attr)) if attr else str(culture)
            if val and "-" in val:
                return val
        except Exception:
            continue
    return ""


def _rewrite_tag_xml_culture(xml_text: str, culture: str) -> str:
    """Replace every <Culture> value with the project's culture."""
    return re.sub(r"(<Culture>)[^<]*(</Culture>)",
                  rf"\g<1>{culture}\g<2>", xml_text)


def _strip_tag_comments(xml_text: str) -> str:
    """Drop the MultilingualText comment objects from a PlcTagTable XML.

    Last-resort fallback when the project accepts none of the comment
    cultures — the tags themselves (name, type, address) still import.
    """
    root = _ET.fromstring(xml_text)
    for plc_tag in root.iter("SW.Tags.PlcTag"):
        for obj_list in plc_tag.findall("ObjectList"):
            plc_tag.remove(obj_list)
    _ET.indent(root, space="  ")
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            + _ET.tostring(root, encoding="unicode"))

# Strong safety-name signals (substring match on the lowercased file stem).
_SAFETY_NAME_HINTS = (
    "safety", "rd05", "f_block", "f_fb", "fb_safe", "fb_f_",
    "estop", "e_stop", "e-stop", "emergency", "notaus", "not_aus",
    "lightcurtain", "light_curtain", "lichtvorhang", "lichtgitter",
    "failsafe", "fail_safe", "f_trig", "f_estop",
)

# Content signatures scanned in the file head (uppercased).
# Deliberately compound phrases: a bare "SAFETY" matched ordinary
# engineering comments ("SAFETY FIX" in a changelog) and skipped normal
# library blocks — an over-broad gate pushes users to disable skip_safety
# entirely, which is the worse failure mode. Real safety blocks are still
# caught by RD05 declarations, the F_ naming convention and these phrases.
_SAFETY_CONTENT_HINTS = (
    "RD05", "F-BLOCK", "FAILSAFE", "FAIL-SAFE", "F_TRIG", "F_ESTOP",
    "SIL1", "SIL2", "SIL3", "EMERGENCY STOP", "LIGHT CURTAIN",
    "NOT-AUS", "NOTAUS", "SAFETY-RELATED", "SAFETY RELATED",
    "SAFETY BLOCK", "SAFETY FUNCTION", "SAFETY PROGRAM", "SAFETY CIRCUIT",
    "SAFETY INTERLOCK", "SAFETY RELAY", "SAFETY DOOR", "SAFETY GATE",
    "SAFETY INSTRUMENTED", "F-CPU",
)

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _strip_library_disclaimer(text: str) -> str:
    """Remove the standard library SAFETY NOTICE disclaimer before scanning.

    Every Factory Library block carries a boilerplate comment that explicitly
    declares the block is NOT safety-related ("NOT designed or validated for
    use in Safety Instrumented Systems..."). Its wording (SAFETY,
    SAFETY-RELATED, ...) would otherwise trip the content scan and silently
    skip the whole standard library on import. Only a comment block that
    contains the anti-safety phrase is removed; all other comments are kept.
    """
    lines = text.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        if "SAFETY NOTICE" in lines[i].upper() and lines[i].lstrip().startswith("//"):
            j = i + 1
            block: list[str] = []
            while j < n and lines[j].lstrip().startswith("//"):
                block.append(lines[j])
                j += 1
            if "NOT DESIGNED OR VALIDATED" in " ".join(block).upper():
                i = j  # drop the notice line + its comment block
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _safety_classification(
    scl_path: Path, safety_block_names: Optional[set[str]] = None
) -> str:
    """Classify an SCL file as 'safety', 'uncertain', or 'standard'.

    Fail-closed: when import skipping is on, both 'safety' and 'uncertain'
    are kept out of the standard import path. The old name-only heuristic
    silently missed real safety blocks like ``F_ESTOP1`` or
    ``FB_EmergencyStop`` (RD05 rule) — this ties detection to the F_ naming
    convention, semantic keywords, file content, and RD05-declared names.
    """
    low = scl_path.stem.lower()

    # 1) RD05-declared safety block/function names (authoritative).
    #
    # M-A2: previously this was `d == low or d in low`, an unanchored substring
    # match. A declared safety block named "fb" or "stop" would match nearly
    # every SCL filename — fail-closed becomes a denial of service for the
    # whole standard import set. We now require:
    #   - exact match (case-insensitive), OR
    #   - declared name >= 5 chars AND appears as a whole word in the filename
    #     (split on _, -, ., space).
    if safety_block_names:
        # Split the filename into word tokens so "FB_LocalStop" -> {"fb", "localstop"}.
        tokens = {t for t in re.split(r"[_\-\.\s]+", low) if t}
        for raw in safety_block_names:
            d = (raw or "").strip().lower()
            if not d:
                continue
            if d == low:
                return "safety"
            if len(d) >= 5 and d in tokens:
                return "safety"

    # 2) Naming convention: F_ prefix (see workbench/core/io_validator.py).
    if low.startswith("f_") or low.startswith("fb_f") or low.startswith("fc_f"):
        return "safety"

    # 3) Strong name hints.
    if any(h in low for h in _SAFETY_NAME_HINTS):
        return "safety"

    # 4) Content signatures. The standard library disclaimer is an explicit
    # NOT-safety declaration — strip it so its wording does not count as a
    # safety signal (it skipped 8/11 demo files in the 2026-06-10 TIA test).
    try:
        text = scl_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        # Cannot inspect the file — do not assume it is safe to import.
        return "uncertain"
    head = _strip_library_disclaimer(text)[:4000].upper()
    if any(sig in head for sig in _SAFETY_CONTENT_HINTS):
        return "safety"

    return "standard"


def _looks_like_safety(
    scl_path: Path, safety_block_names: Optional[set[str]] = None
) -> bool:
    """True when a file must be kept out of the standard import path (RD05).

    Fail-closed: 'uncertain' (file unreadable) also returns True.
    """
    return _safety_classification(scl_path, safety_block_names) != "standard"


def _read_rd05_safety_names(project_root: Path) -> set[str]:
    """Collect declared safety block/function names from metadata/RD05_*.md.

    Reads the safety-functions table and gathers identifier-like values from
    the FunctionName / F_FB / F_DB / F_InputTag / F_OutputTag columns.
    Returns an empty set when no RD05 file is present (best-effort).
    """
    names: set[str] = set()
    try:
        meta = Path(project_root) / "metadata"
        rd05_files = sorted(meta.glob("RD05*.md")) if meta.is_dir() else []
        if not rd05_files:
            return names
        text = rd05_files[0].read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return names

    target_cols = {
        "functionname", "f_fb", "f_db", "f_inputtag", "f_outputtag", "f_block",
    }
    header: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = []
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        lowered = [c.lower() for c in cells]
        # Markdown separator row (|----|----|)
        if all(set(c) <= set("-: ") for c in cells if c):
            continue
        if target_cols & set(lowered):
            header = lowered
            continue
        if not header:
            continue
        for col, val in zip(header, cells):
            if col not in target_cols or not val:
                continue
            token = val.split("(")[0].strip()  # drop "(standart db10)" notes
            for piece in token.replace(",", " ").split():
                if _IDENT_RE.match(piece) and not piece.lower().startswith(
                    ("fc", "ob", "nw", "db")
                ):
                    names.add(piece)
            if val.upper().startswith("F_"):
                names.add(val.split()[0])
    return names


def _discover_rd05_names(scl_files: list[Path]) -> set[str]:
    """Find the factory project root (an ancestor containing metadata/) from
    the SCL files and read RD05-declared safety names from it."""
    for scl in scl_files:
        try:
            for parent in Path(scl).resolve().parents:
                if (parent / "metadata").is_dir():
                    found = _read_rd05_safety_names(parent)
                    if found:
                        return found
        except Exception:
            continue
    return set()


def _summarize_compile_result(result: Any) -> CompileSummary:
    """TIA CompilerResult -> CompileSummary."""
    s = CompileSummary()
    try:
        s.state = str(result.State)
    except Exception:
        s.state = "Unknown"
    try:
        s.errors = int(result.ErrorCount)
    except Exception:
        pass
    try:
        s.warnings = int(result.WarningCount)
    except Exception:
        pass

    # Collect messages — CompilerResultMessage nests child messages in
    # .Messages (the block-level errors live one or two levels deep), so
    # walk the tree instead of only reading the top level.
    def _walk(messages) -> None:
        for m in messages:
            try:
                sev = str(m.State)
            except Exception:
                sev = "Info"
            try:
                txt = str(m.Description)
            except Exception:
                txt = str(m)
            blk = ""
            try:
                blk = str(m.Path) if hasattr(m, "Path") else ""
            except Exception:
                pass
            if txt and txt.strip():
                s.messages.append(CompileMessage(severity=sev, text=txt, block=blk))
                if sev == "Information":
                    s.infos += 1
            try:
                _walk(m.Messages)
            except Exception:
                pass

    try:
        _walk(result.Messages)
    except Exception:
        pass
    return s
