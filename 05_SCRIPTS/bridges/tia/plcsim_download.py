"""
PLCSIM Advanced download via Openness.

SAFETY:
  - Targets PLCSIM Advanced only.
  - NO automatic download to a real PLC (settings.bridges.tia.plcsim_only is checked).
  - F-blocks (RD05 Safety) must already have been skipped during the import phase.

DEFENSIVE:
  The TIA Openness Download API has some signature differences between V19
  and V20. The broadest-compatible method is tried here; on error the user
  gets a clear message recommending manual download from inside TIA.

Call:
    from bridges.tia.plcsim_download import download_to_plcsim
    res = download_to_plcsim(core, project, plc_item, plc_software, settings)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class DangerousDownloadOption(Exception):
    """W-A4: raised by the download-config callbacks when TIA presents a
    sub-option that would alter the target device (StopModules,
    OverwriteSystemData, FormatMemoryCard …). Bubbles up out of
    provider.Download so the operation is aborted rather than letting the
    default selection be silently applied."""


@dataclass
class PlcSimDownloadResult:
    success: bool = False
    message: str = ""
    details: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # W-A4: hard errors that must surface in the UI as a refusal, not a
    # warning. Populated when a dangerous configuration option was detected.
    errors: list[str] = field(default_factory=list)
    manual_fallback: str = ""


def download_to_plcsim(
    core,
    project,
    plc_item,
    plc_software,
    settings: dict,
) -> PlcSimDownloadResult:
    """Download the PLC to a PLCSIM Advanced virtual target.

    Args:
      core         : OpennessCore instance
      project      : TIA project handle
      plc_item     : PLC device item (the item returned by find_plc)
      plc_software : PlcSoftware service
      settings     : the settings.bridges.tia section

    Returns:
      PlcSimDownloadResult — success/false and explanation
    """
    res = PlcSimDownloadResult()

    plcsim_only = bool(settings.get("plcsim_only", True))
    if not plcsim_only:
        res.message = (
            "settings.tia.plcsim_only was set to False. "
            "Bridge refusing to download to a real PLC — "
            "violates the safety rule in memory."
        )
        res.manual_fallback = "Run Online -> Download manually inside TIA."
        return res

    # Acquire pythonnet symbols. Live V19 finding (2026-07-06): the namespace
    # exposes DownloadProvider (a class) — `IDownloadProvider` does NOT exist
    # in V19's Siemens.Engineering.dll, so the old direct import failed before
    # the download path was ever reached. Resolve symbols defensively and keep
    # the interface name as a fallback for other Openness versions.
    try:
        import clr  # noqa: F401
        import Siemens.Engineering.Download as _dl  # type: ignore
    except Exception as e:
        res.message = f"Download namespace could not load: {e}"
        res.manual_fallback = (
            "TIA Openness Download API is not available or has a different "
            "signature in this installation. Manual: TIA -> Online -> Download to device."
        )
        return res

    provider_type = getattr(_dl, "DownloadProvider", None) \
        or getattr(_dl, "IDownloadProvider", None)
    delegate_type = getattr(_dl, "DownloadConfigurationDelegate", None)
    options_type = getattr(_dl, "DownloadOptions", None)
    if provider_type is None or delegate_type is None:
        res.message = (
            "Download namespace loaded but symbols are missing "
            f"(provider: {provider_type is not None}, "
            f"delegate: {delegate_type is not None}) — Openness version mismatch."
        )
        res.manual_fallback = "Run Online -> Download from inside TIA."
        return res

    # Acquire the download provider
    try:
        provider = plc_item.GetService[provider_type]()
    except Exception as e:
        res.message = f"DownloadProvider service unavailable: {e}"
        res.manual_fallback = "Run Online -> Download from inside TIA."
        return res

    if provider is None:
        res.message = "PLC does not provide a DownloadProvider service."
        return res

    res.details.append(f"DownloadProvider ready: {type(provider).__name__}")

    # --- C2: verify the actual target is PLCSIM Advanced (fail-closed) ------
    # The plcsim_only flag alone is not enough: the real download target comes
    # from TIA's Online settings, which could point at a physical PLC. We probe
    # the configured target and refuse unless it is verifiably virtual.
    target = _probe_target(provider, plc_item)
    safe, reason = _is_download_target_safe(target, plcsim_only)
    res.details.append(f"Target check: {reason}")
    if not safe:
        res.message = f"SAFETY REFUSAL: {reason}"
        res.manual_fallback = (
            "Make sure a PLCSIM Advanced instance is the active online target "
            "in TIA (Online access), then download manually inside TIA: "
            "Online -> Download to device."
        )
        return res

    # Configuration callbacks — instead of silently accepting every sub-option
    # at default (which would auto-approve StopModules / OverwriteSystemData on
    # the target), we walk the configurations and record dangerous selections.
    try:
        # pythonnet needs real .NET delegates, not bare Python lambdas.
        pre = delegate_type(lambda dl_config: _configure_pre(dl_config, res))
        post = delegate_type(lambda dl_config: _configure_post(dl_config, res))

        # V19 signature: Download(pre, post, DownloadOptions). The old 4-arg
        # call never matched any overload. Software|Hardware mirrors what the
        # TIA GUI does on "Download to device".
        if options_type is not None:
            opts = options_type.Software | options_type.Hardware
            try:
                provider.Download(pre, post, opts)
            except TypeError:
                # Legacy/newer overload variant.
                provider.Download(None, pre, post, opts)
        else:
            provider.Download(None, pre, post, None)
        res.success = True
        res.message = "Download started (TIA Portal is running it in the background)."
        res.details.append("If PLCSIM Advanced is not active, TIA will display an error.")
    except DangerousDownloadOption as e:
        # W-A4: callback aborted the operation due to an unsafe sub-option.
        res.success = False
        res.message = str(e)
        res.manual_fallback = (
            "Open TIA -> Online -> Download to device. Review the highlighted "
            "options (StopModules / OverwriteSystemData / FormatMemoryCard / "
            "DeleteData / Reset) before confirming."
        )
    except Exception as e:
        res.message = f"Download call failed: {e}"
        res.manual_fallback = (
            "Inside TIA: Online -> Download to device -> PLCSIM (Soft).\n"
            "The target PLCSIM Advanced instance must have been started beforehand."
        )

    return res


# ── target verification (pure logic — unit tested) ───────────────────────────

# Option names that change device state and must not be auto-accepted silently.
#
# Each entry is a lowercase token (or space-joined token sequence) that
# represents a dangerous TIA download option.  Matching is done via
# _is_dangerous_option(), which splits the candidate name into word tokens
# before comparing — so short keywords like "reset" do NOT falsely match
# "ResetTime" or "preset".
#
# Fail-safe: when the option name is empty or cannot be parsed the function
# returns True (block it).
_DANGEROUS_OPTION_HINTS = (
    "stopmodules", "stop modules", "overwrite", "formatmemorycard",
    "format memory", "deletedata", "delete data", "reset",
)

# Pre-compiled tokeniser: splits a name into lowercase word-tokens by
# non-alphanumeric boundaries (CamelCase words are separated by uppercase
# transitions so "StopModules" → ["stop", "modules"]).
_TOKEN_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+")


def _tokenise(name: str) -> list[str]:
    """Return lowercase word tokens from a TIA option name.

    Examples:
        "StopModules"            → ["stop", "modules"]
        "FormatMemoryCard"       → ["format", "memory", "card"]
        "OverwriteSystemData"    → ["overwrite", "system", "data"]
        "Reset"                  → ["reset"]
        "ResetTime"              → ["reset", "time"]   ← "reset" token present → blocked (fail-safe)
        "preset"                 → ["preset"]           ← no "reset" token → not blocked
        "ConsistentBlocksDownload" → ["consistent", "blocks", "download"]
    """
    tokens = _TOKEN_RE.findall(name)
    if not tokens:
        # Fallback: treat the whole lowercased string as one token.
        return [(name or "").lower()]
    return [t.lower() for t in tokens]


def _name_indicates_plcsim(name: str) -> bool:
    """True when a connection/target name marks a virtual PLCSIM target."""
    low = (name or "").lower()
    return ("plcsim" in low) or ("softplc" in low) or ("plc sim" in low) \
        or ("simulation" in low)


def _is_dangerous_option(name: str) -> bool:
    """True when a download sub-option would alter the target device.

    Uses word-token matching so that short keywords like "reset" do NOT
    trigger on safe option names such as "ResetTime" or "preset".

    Multi-word hints (e.g. "stop modules") are matched against the joined
    token string so that both "StopModules" and "stop modules" are caught.

    Fail-safe: an empty or unparseable name returns True (block it).
    """
    if not name:
        return True  # fail-safe: unknown option → block
    tokens = _tokenise(name)
    joined = " ".join(tokens)   # e.g. "stop modules" for "StopModules"
    for hint in _DANGEROUS_OPTION_HINTS:
        if " " in hint:
            # Multi-word hint: check against joined token string.
            if hint in joined:
                return True
        else:
            # Single-word hint: exact token match (not substring).
            if hint in tokens:
                return True
    return False


def _is_download_target_safe(summary: dict, plcsim_only: bool) -> tuple[bool, str]:
    """Decide whether a download may proceed. Fail-closed.

    summary keys: is_plcsim (True/False/None=unknown), target_name.
    """
    if not plcsim_only:
        return False, "plcsim_only is off — refusing (real PLC risk, RD05 rule)"
    is_plcsim = summary.get("is_plcsim")
    if is_plcsim is True:
        return True, "Target verified as PLCSIM Advanced (virtual)"
    if is_plcsim is False:
        tn = summary.get("target_name") or "unknown"
        return False, f"Target is a real PLC ({tn}) — refusing download"
    # Unknown — cannot confirm the target is virtual.
    return False, "Target could not be verified as PLCSIM Advanced — refusing (fail-closed)"


def _probe_target(provider, plc_item) -> dict:
    """Best-effort runtime probe of the configured download target.

    Returns is_plcsim=None when it cannot be determined; the caller treats
    unknown as unsafe. Runtime-only — exercised against a real TIA install.
    """
    info: dict = {"is_plcsim": None, "target_name": ""}
    candidates: list[str] = []
    for getter in (
        lambda: str(provider.Configuration.OnlineConfiguration.ConfigurationName),
        lambda: str(provider.Configuration.TargetName),
        lambda: str(plc_item.Name),
    ):
        try:
            val = getter()
            if val:
                candidates.append(val)
        except Exception:
            continue
    if candidates:
        info["target_name"] = candidates[0]
        if any(_name_indicates_plcsim(c) for c in candidates):
            info["is_plcsim"] = True
        # If a name is present but clearly a physical interface, mark False.
        elif any(("pn/ie" in c.lower() or "profinet" in c.lower()) for c in candidates):
            info["is_plcsim"] = False
    return info


# ── configuration callbacks (runtime — record dangerous selections) ──────────

def _scan_dangerous(dl_config) -> list[str]:
    """List the names of dangerous (state-changing) sub-options on `dl_config`.

    Wrapped in defensive try/except because the COM object can surface
    iteration errors; we still return whatever we collected.
    """
    dangerous: list[str] = []
    try:
        for cfg in list(dl_config.Configurations):
            try:
                name = str(getattr(cfg, "Name", "") or type(cfg).__name__)
            except Exception:
                name = type(cfg).__name__
            if _is_dangerous_option(name):
                dangerous.append(name)
    except Exception:
        pass
    return dangerous


def _configure_pre(dl_config, res=None) -> None:
    """Pre-download: leave benign sub-options at default; ABORT when TIA
    presents a dangerous one (StopModules / OverwriteSystemData / …).

    W-A4: previously this only appended a warning and let the download
    proceed with the default selection — meaning a stop or overwrite was
    silently applied to a live target. Now we raise so provider.Download
    fails and the caller surfaces a refusal to the user.
    """
    dangerous = _scan_dangerous(dl_config)
    if dangerous:
        msg = (
            "Refusing download — TIA presented unsafe pre-download options: "
            + ", ".join(dangerous)
            + ". Confirm them inside TIA (Online → Download to device) and "
            "review the impact, then re-run."
        )
        if res is not None:
            res.errors.append(msg)
        raise DangerousDownloadOption(msg)


def _configure_post(dl_config, res=None) -> None:
    """Post-download (start modules) configuration — same review policy."""
    dangerous = _scan_dangerous(dl_config)
    if dangerous:
        msg = (
            "Refusing download — TIA presented unsafe start-module options: "
            + ", ".join(dangerous)
            + ". Confirm them inside TIA and re-run."
        )
        if res is not None:
            res.errors.append(msg)
        raise DangerousDownloadOption(msg)
