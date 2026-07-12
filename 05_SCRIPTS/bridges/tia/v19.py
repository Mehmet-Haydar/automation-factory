"""
TIA Portal V19 Openness bridge.

API is 99% identical to V20. The only differences:
  - DLL path:  Portal V19\\PublicAPI\\V19\\Siemens.Engineering.dll
  - Project:   .ap19 extension
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..base import BridgeBase, BridgeStatus, BridgeResult
from .version_detect import find_one, is_user_in_openness_group


class TiaV19Bridge(BridgeBase):
    bridge_id = "tia_v19"
    display_name = "TIA Portal V19 (Openness)"
    category = "tia"

    _TARGET_VERSION = "V19"
    _PROJECT_EXT = ".ap19"

    def __init__(self, settings, on_status=None):
        super().__init__(settings, on_status)
        self._install = None
        self._core = None  # OpennessCore (lazy)

    # -- detect -----------------------------------------------------------
    def detect(self) -> BridgeStatus:
        # Manual DLL path provided?
        manual = (self.settings.get("bridges", {})
                                .get("tia", {})
                                .get(f"tia_{self._TARGET_VERSION.lower()}_dll_path", ""))
        if manual:
            dll = Path(manual)
            if dll.is_file():
                self._install = _ManualInstall(self._TARGET_VERSION, dll, self._PROJECT_EXT)
                return self._preflight_status()
            self.remember_error(f"Manual DLL path invalid: {dll}")
            return BridgeStatus.NOT_CONFIGURED

        inst = find_one(self._TARGET_VERSION)
        if inst is None:
            return BridgeStatus.NOT_INSTALLED
        self._install = inst
        return self._preflight_status()

    def _preflight_status(self) -> BridgeStatus:
        """READY only when the send path can actually run.

        Field-audit B-09: detect() used to return READY with the Openness
        group missing ("warning only") — the engineer then hit the failure
        at send time, deep in a modal, with no fallback hint. Every known
        dead-end must be NOT_CONFIGURED here, with an actionable message
        that also names the manual-export escape hatch."""
        import importlib.util
        if importlib.util.find_spec("clr") is None:
            self.remember_error(
                "pythonnet is not installed — run 'pip install pythonnet'. "
                "Until then use the manual path: the generated .scl files in "
                "_output/ import via TIA -> External source files."
            )
            return BridgeStatus.NOT_CONFIGURED
        if self.settings.get("bridges", {}).get("tia", {}).get("openness_user_check", True):
            grp = is_user_in_openness_group()
            if grp is False:
                self.remember_error(
                    "User not in 'Siemens TIA Openness' Windows group — TIA "
                    "refuses the Openness connection. Add your user to the "
                    "group (Computer Management -> Local Users and Groups), "
                    "log off/on, then retry. Until then use the manual path: "
                    "the generated .scl files in _output/ import via "
                    "TIA -> External source files."
                )
                return BridgeStatus.NOT_CONFIGURED
        return BridgeStatus.READY

    # -- core loader (lazy pythonnet) -------------------------------------
    def _get_core(self):
        if self._core is not None:
            return self._core
        if self._install is None:
            if self.detect() != BridgeStatus.READY:
                raise RuntimeError(f"TIA {self._TARGET_VERSION} not found.")
        from .openness_core import OpennessCore  # lazy
        self._core = OpennessCore(self._install.engineering_dll)
        return self._core

    # -- tag table import (shared by both flows) ---------------------------
    def _import_tags(self, core, proj, plc_sw, tag_xml: Optional[Path],
                     result) -> None:
        """Import the IO tag table; failure warns loudly but never aborts.

        Missing tags surface as compile errors on symbolic references anyway
        — aborting here would also block projects that use direct addressing.
        ``proj`` lets the core adapt the comment culture to the project's
        editing language (2026-06-10 live finding).
        """
        if not tag_xml:
            self.step("import_tags", "skip", "no tag XML")
            return
        self.status("Tag table import...", "info")
        self.step("import_tags", "running")
        try:
            tables, notes = core.import_tag_table(plc_sw, Path(tag_xml),
                                                  project=proj)
            shown = ", ".join(tables) if tables else Path(tag_xml).stem
            result.details.append(f"Tag table imported: {shown}")
            for n in notes:
                result.warnings.append(n)
            self.status(f"Tag table imported: {shown}", "ok")
            self.step("import_tags", "ok", shown)
        except Exception as e:
            result.warnings.append(
                f"Tag table import FAILED — IO tags missing in TIA, "
                f"blocks continue: {e}")
            self.status("Tag table import failed (continuing).", "warn")
            self.step("import_tags", "warn", "failed — blocks continue")

    # -- main actions -----------------------------------------------------
    def import_scl_to_project(
        self,
        project_ap_path: Path,
        scl_files: list[Path],
        plc_name: Optional[str] = None,
        do_compile: Optional[bool] = None,
        with_ui: bool = True,
        tag_xml: Optional[Path] = None,
    ) -> BridgeResult:
        """Open a TIA project, import tag table + SCL files, compile, close.

        ``tag_xml`` is an optional PlcTagTable XML (tia_tag_export output);
        it is imported BEFORE the SCL sources so symbolic IO references
        resolve at compile time. A tag failure is a loud warning, not a stop
        — the blocks still import.
        """
        tia_settings = self.settings["bridges"]["tia"]
        plc_name = plc_name or tia_settings.get("default_plc_name", "PLC_1")
        do_compile = (do_compile if do_compile is not None
                      else tia_settings.get("auto_compile_after_import", True))
        skip_safety = tia_settings.get("skip_safety_blocks", True)

        result = BridgeResult(success=False)

        if not self.is_enabled():
            result.message = f"{self.display_name} toggle is OFF."
            return result

        try:
            core = self._get_core()
        except Exception as e:
            result.message = f"Openness could not load: {e}"
            result.warnings.append("Is pythonnet installed? `pip install pythonnet`")
            return result

        self.status(f"{self.display_name} starting...", "info")

        try:
            self.step("portal", "running")
            core.start_portal(with_ui=with_ui)
            self.status("TIA Portal opened.", "ok")
            self.step("portal", "ok")
            self.step("open_project", "running")
            proj = core.open_project(Path(project_ap_path))
            self.status(f"Project opened: {Path(project_ap_path).name}", "ok")
            self.step("open_project", "ok", Path(project_ap_path).name)

            self.step("find_plc", "running")
            plc_item, plc_sw = core.find_plc(proj, plc_name)
            if plc_sw is None:
                result.message = f"PLC not found: {plc_name}"
                result.warnings.append(
                    "Project left open in TIA Portal for inspection.")
                self.step("find_plc", "fail", plc_name)
                return result
            self.step("find_plc", "ok", plc_name)

            self._import_tags(core, proj, plc_sw, tag_xml, result)

            self.status(f"SCL import started ({len(scl_files)} files)...", "info")
            self.step("import_scl", "running", f"0/{len(scl_files)}")
            imp = core.import_scl_files(
                plc_sw, scl_files, skip_safety=skip_safety,
                on_file=lambda i, t, n: self.step("import_scl", "running",
                                                  f"{i}/{t} {n}"))
            result.details.append(f"Sources added: {len(imp.sources_added)}")
            result.details.append(f"Blocks generated: {len(imp.blocks_generated)}")
            if imp.skipped_safety:
                result.warnings.append(
                    f"RD05 Safety skipped ({len(imp.skipped_safety)}): "
                    + ", ".join(imp.skipped_safety[:5])
                )
            for w in imp.warnings:
                result.warnings.append(w)

            if imp.failed or not imp.blocks_generated:
                if imp.failed:
                    result.message = (f"Import failed for {len(imp.failed)} "
                                      f"file(s): {', '.join(imp.failed[:5])} — "
                                      "project NOT saved.")
                else:
                    result.message = ("No blocks were imported — see warnings "
                                      "(all files failed or were safety-skipped).")
                result.warnings.append(
                    "Project left open in TIA Portal for inspection.")
                self.step("import_scl", "fail",
                          f"{len(imp.failed)} failed" if imp.failed
                          else "no blocks imported")
                return result
            self.step("import_scl", "ok",
                      f"{len(imp.blocks_generated)} blocks")

            if do_compile and plc_sw is not None:
                self.status("Compile started...", "info")
                self.step("compile", "running")
                cs = core.compile_plc(plc_sw)
                result.details.append(
                    f"Compile: {cs.state} (errors={cs.errors}, warnings={cs.warnings})"
                )
                result.compile_errors = [
                    {"block": m.block, "severity": m.severity, "text": m.text}
                    for m in cs.messages if m.severity == "Error"
                ]
                # First 10 messages, ERRORS FIRST — the 2026-06-10 live run
                # buried the single real error under 10 benign warnings.
                ordered = sorted(cs.messages,
                                 key=lambda m: m.severity != "Error")
                for m in ordered[:10]:
                    prefix = "[ERROR]" if m.severity == "Error" else "[WARN]"
                    blk = f" ({m.block})" if m.block else ""
                    result.warnings.append(f"{prefix}{blk} {m.text}")
                if cs.errors > 0:
                    result.message = f"Compile finished with ERRORS ({cs.errors} errors)."
                    self.step("compile", "fail", f"{cs.errors} errors")
                    self.step("save", "skip", "compile errors — not saved")
                else:
                    self.step("compile", "ok",
                              f"0 errors, {cs.warnings} warnings")
                    self.step("save", "running")
                    core.save_project(proj)
                    self.step("save", "ok")
                    result.message = "Import + compile successful, project saved."
                    result.success = True
            else:
                result.message = "Import successful (compile skipped)."
                self.step("compile", "skip")
                result.success = True

            # Keep the project open in TIA Portal so the engineer can
            # inspect the result; the next run reuses the open handle.
            result.details.append("Project left open in TIA Portal.")

        except Exception as e:
            result.message = f"ERROR: {e}"
            self.remember_error(str(e))

        return result


    # -- PLCSIM Advanced download (Phase 37-B) -----------------------------
    def import_compile_and_download(
        self,
        project_ap_path: Path,
        scl_files: list[Path],
        plc_name: Optional[str] = None,
        with_ui: bool = True,
        tag_xml: Optional[Path] = None,
    ) -> BridgeResult:
        """Import + compile + download to PLCSIM Advanced (full flow).

        Only downloads to a PLCSIM Advanced target; never to a real PLC.
        Refuses if plcsim_only is False.
        """
        from .plcsim_download import download_to_plcsim

        tia_settings = self.settings["bridges"]["tia"]
        plc_name = plc_name or tia_settings.get("default_plc_name", "PLC_1")
        result = BridgeResult(success=False)

        if not self.is_enabled():
            result.message = f"{self.display_name} toggle is OFF."
            return result

        if not tia_settings.get("plcsim_only", True):
            result.message = (
                "SAFETY REFUSAL: plcsim_only is off — risk of real PLC. "
                "Bridge refusing (RD05 + memory rule)."
            )
            return result

        try:
            core = self._get_core()
        except Exception as e:
            result.message = f"Openness could not load: {e}"
            return result

        try:
            self.step("portal", "running")
            core.start_portal(with_ui=with_ui)
            self.status("TIA Portal opened.", "ok")
            self.step("portal", "ok")
            self.step("open_project", "running")
            proj = core.open_project(Path(project_ap_path))
            self.step("open_project", "ok", Path(project_ap_path).name)
            self.step("find_plc", "running")
            plc_item, plc_sw = core.find_plc(proj, plc_name)
            if plc_sw is None:
                result.message = f"PLC not found: {plc_name}"
                self.step("find_plc", "fail", plc_name)
                return result
            self.step("find_plc", "ok", plc_name)

            self._import_tags(core, proj, plc_sw, tag_xml, result)

            # 1) Import
            self.status(f"SCL import ({len(scl_files)} files)...", "info")
            self.step("import_scl", "running", f"0/{len(scl_files)}")
            imp = core.import_scl_files(
                plc_sw, scl_files,
                skip_safety=tia_settings.get("skip_safety_blocks", True),
                on_file=lambda i, t, n: self.step("import_scl", "running",
                                                  f"{i}/{t} {n}"),
            )
            result.details.append(f"Import: {len(imp.blocks_generated)} blocks")
            if imp.skipped_safety:
                result.warnings.append(
                    f"RD05 Safety skipped: {', '.join(imp.skipped_safety[:5])}"
                )
            if imp.failed or not imp.blocks_generated:
                result.message = ("Import incomplete — download cancelled "
                                  f"({len(imp.failed)} failed file(s)).")
                for w in imp.warnings[:5]:
                    result.warnings.append(w)
                self.step("import_scl", "fail",
                          f"{len(imp.failed)} failed" if imp.failed
                          else "no blocks imported")
                self.step("download", "skip", "import incomplete")
                return result
            self.step("import_scl", "ok",
                      f"{len(imp.blocks_generated)} blocks")

            # 2) Compile
            self.status("Compile...", "info")
            self.step("compile", "running")
            cs = core.compile_plc(plc_sw)
            result.details.append(
                f"Compile: {cs.state} (errors={cs.errors}, warnings={cs.warnings})"
            )
            result.compile_errors = [
                {"block": m.block, "severity": m.severity, "text": m.text}
                for m in cs.messages if m.severity == "Error"
            ]
            if cs.errors > 0:
                result.message = "Compile ERROR — download cancelled."
                for m in cs.messages[:5]:
                    if m.severity == "Error":
                        result.warnings.append(f"[ERROR] {m.text}")
                self.step("compile", "fail", f"{cs.errors} errors")
                self.step("download", "skip", "compile errors")
                return result
            self.step("compile", "ok", f"0 errors, {cs.warnings} warnings")

            self.step("save", "running")
            core.save_project(proj)
            self.step("save", "ok")

            # 3) Download
            self.status("Download to PLCSIM Advanced...", "info")
            self.step("download", "running")
            dl = download_to_plcsim(core, proj, plc_item, plc_sw, tia_settings)
            for d in dl.details:
                result.details.append(d)
            for w in dl.warnings:
                result.warnings.append(w)

            if dl.success:
                result.message = "Import + compile + download completed."
                result.success = True
                self.step("download", "ok")
            else:
                result.message = f"Download failed: {dl.message}"
                if dl.manual_fallback:
                    result.warnings.append(f"Manual: {dl.manual_fallback}")
                self.step("download", "fail")

            # Keep the project open in TIA Portal so the engineer can
            # inspect the result; the next run reuses the open handle.
            result.details.append("Project left open in TIA Portal.")

        except Exception as e:
            result.message = f"ERROR: {e}"
            self.remember_error(str(e))

        return result


class _ManualInstall:
    """Used in place of version_detect.TiaInstall when a manual DLL path is given."""
    def __init__(self, version: str, dll: Path, ext: str):
        self.version = version
        self.engineering_dll = dll
        self.portal_root = dll.parent.parent.parent
        self.project_ext = ext
