#!/usr/bin/env python3
"""
program_assembler.py — library-first program assembly (M3).

Builds a complete TIA-importable program skeleton from the approved RD01
IO list, WITHOUT regenerating device logic with AI:

1. Group RD01 signals into devices (naming standard SCOPE_EQUIP_NNN_SUFFIX).
2. Map each device to a curated library block via its .contract.json
   (rule-based, conservative — anything uncertain lands in #UNKNOWN,
   never silently dropped).
3. Copy matched library .scl files VERBATIM into _output/scl/ and record
   source==dest SHA-256 so "never AI-regenerated" is verifiable.
4. Generate one single-instance DB per device (.db external source) and an
   OB1 that calls them with real parameter bindings (field signals only:
   feedbacks, overloads, main outputs — control/HMI ports are left at
   their contract defaults and listed as TODOs).
5. Validate everything: scl_validator (incl. STRUCTURAL_BUG rule) on all
   sources + fb_acceptance_check gate for each copied block against its
   contract (catches library drift at assembly time).
6. Write REPORTS/ASSEMBLY_REPORT.md.

The ONLY AI-generated artifact of the assembly stage is the project
sequence FB — that runs separately (factory_web.generate_sequence_fb) and
is excluded from this module on purpose.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

FACTORY_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "blocks"
CONTRACTS_DIR = FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "contracts"

# Naming standard: SCOPE_EQUIPMENT_NNN[_SUFFIX]  (GLOBAL_NAMING_STANDARD.md)
_TAG_RE = re.compile(r"^([A-Za-z]+)_([A-Za-z0-9]+)_(\d{2,4})(?:_([A-Za-z0-9_]+))?$")

_FB_NAME_RE = re.compile(r"FUNCTION_BLOCK\s+\"?([\w]+)\"?", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Device:
    device_id: str                 # MOT_CONV_001
    prefix: str                    # MOT
    description: str               # first signal description
    signals: list[dict] = field(default_factory=list)   # parse_rd01_signals rows


@dataclass
class DeviceMatch:
    device: Device
    contract_stem: str             # FB_Motor_DOL
    scl_path: Path
    contract_path: Path
    fb_block_name: str = ""        # FUNCTION_BLOCK name parsed from SCL
    instance_db: str = ""
    in_bindings: dict = field(default_factory=dict)
    out_bindings: dict = field(default_factory=dict)
    todos: list = field(default_factory=list)


@dataclass
class AssemblyResult:
    ok: bool = True
    msg: str = ""
    matches: list[DeviceMatch] = field(default_factory=list)
    unknown: list[dict] = field(default_factory=list)     # device/signal + reason
    copied: list[dict] = field(default_factory=list)      # name, sha256, verbatim
    generated: list[str] = field(default_factory=list)    # generated file names
    validation: list[dict] = field(default_factory=list)  # per-file validator result
    gate_results: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_path: Optional[Path] = None
    # Delta mode (change management): which devices were re-written, which
    # were left untouched, and which manifest devices vanished from RD01.
    delta_mode: bool = False
    affected: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    orphaned: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1) Device grouping
# ---------------------------------------------------------------------------

# B-03 fallback: a device-like Equipment cell (M1, P1, Y2, MOT_CONV_001 …).
# Deliberately rejects plant/station ids with separators ("MA-3", "Linie 2").
_EQUIP_ID_RE = re.compile(r"^[A-Za-z]{1,4}\d{1,4}$|^[A-Za-z]+_[A-Za-z0-9]+_\d{2,4}$")
# An equipment group bigger than this is probably a station, not a device —
# grouping it would classify a whole plant as one motor. Stay #UNKNOWN.
_EQUIP_GROUP_MAX_SIGNALS = 6


# F4 (E2E #2): 295 flat "unknown" lines are unreadable for an engineer.
# Classify each unknown so the report can say "these are operator-panel
# items the HMI chain already covers / these are internal flags / ONLY
# these may hide a real device gap". Conservative: unmatched -> device_gap.
_PANEL_KW = re.compile(
    r"TASTER|TASTE\b|DRUCKTASTER|SCHALTER|WAHLSCHALTER|SCHLUESSEL|"
    r"LEUCHTMELDER|MELDELEUCHTE|LAMPE|BLINK|HUPE|SUMMER|SIRENE|"
    r"QUITTIER|\bPULT|PULPIT|\bBTN_|\bLAMP_|\bSW_|POTENTIOMETER|"
    r"BEDIEN|PANEL", re.IGNORECASE)
_FLAG_KW = re.compile(
    r"BETRIEBSART|AUTOMATIK|\bHAND\b|EINRICHT|TIPP|\bMODE\b|\bBA[_ ]|"
    r"FREIGABE|MERKER|HILFS|IMPULS|TAKT|FLANKE|VERRIEGEL", re.IGNORECASE)

UNKNOWN_CLASSES = {
    "operator_panel": ("Operator-panel items — already covered by the HMI "
                       "draft chain (RD11/RD08); no device block expected"),
    "internal_flag": ("Internal mode/auxiliary flags — live inside program "
                      "logic; no device block expected"),
    "device_gap": ("Possible device gaps — REVIEW: naming issue or missing "
                   "library block"),
}


def classify_unknown(sig: dict) -> str:
    """operator_panel / internal_flag / device_gap for one unknown item."""
    text = " ".join(str(sig.get(k) or "") for k in
                    ("name", "desc", "equipment"))
    if _PANEL_KW.search(text):
        return "operator_panel"
    addr = str(sig.get("address") or "").upper().lstrip("%").replace(" ", "")
    if _FLAG_KW.search(text) or addr.startswith(("M", "F")):
        return "internal_flag"
    return "device_gap"


def group_devices(signals: list[dict]) -> tuple[list[Device], list[dict]]:
    """Group RD01 signal rows into devices.

    Primary key: the SCOPE_EQUIP_NNN tag naming standard. Fallback (field
    audit B-03 — real legacy tags are "K1", "F_M1", "LSL_B1"): the RD01
    **Equipment** column, when it carries a device-like id (M1, P1, Y2).
    Oversized equipment groups (> _EQUIP_GROUP_MAX_SIGNALS) stay loose so a
    station id can never be classified as a single motor. Anything ungrouped
    is returned separately (→ #UNKNOWN, never silently dropped)."""
    by_id: dict[str, Device] = {}
    loose: list[dict] = []
    equip_groups: dict[str, list[dict]] = {}
    for sig in signals:
        m = _TAG_RE.match((sig.get("name") or "").strip())
        if not m:
            eq = (sig.get("equipment") or "").strip()
            if not eq:
                # Assembly-time safety net (A/B/C field measurement
                # 2026-07-03): an AI-drafted RD01 may leave Equipment empty —
                # the legacy description often still carries the device ref
                # ("… * 7-M3"). Same deterministic extraction as the RD01
                # enrichment pass, applied in memory.
                eq = equipment_from_text(sig.get("desc") or "")
            if eq and _EQUIP_ID_RE.match(eq):
                equip_groups.setdefault(eq.upper(), []).append(sig)
            else:
                loose.append(sig)
            continue
        device_id = f"{m.group(1)}_{m.group(2)}_{m.group(3)}".upper()
        dev = by_id.get(device_id)
        if dev is None:
            dev = Device(device_id=device_id, prefix=m.group(1).upper(),
                         description=sig.get("desc", ""))
            by_id[device_id] = dev
        dev.signals.append({**sig, "suffix": (m.group(4) or "").upper()})

    # Equipment-column fallback groups (legacy naming, B-03)
    for eq_id, sigs in equip_groups.items():
        if len(sigs) > _EQUIP_GROUP_MAX_SIGNALS or eq_id in by_id:
            loose.extend(sigs)
            continue
        pm = re.match(r"^([A-Za-z]+)", eq_id)
        dev = Device(device_id=eq_id, prefix=(pm.group(1) if pm else eq_id).upper(),
                     description=sigs[0].get("desc", ""))
        # Suffix for port matching: derive from the legacy tag's last token
        # ("K1_RM" -> RM, "LSL_B1" -> LSL prefix heuristic falls back to name).
        for s in sigs:
            nm = (s.get("name") or "").strip()
            token = nm.split("_")[-1] if "_" in nm else nm
            dev.signals.append({**s, "suffix": token.upper()})
        by_id[eq_id] = dev
    return list(by_id.values()), loose


# ---------------------------------------------------------------------------
# 2) Device → library block mapping (conservative)
# ---------------------------------------------------------------------------

# Device classification + port vocabulary live in the bilingual lexicon
# (device_lexicon.py) — data-driven, German-compound aware, umlaut folded.
# This module only orchestrates. (Was: a handful of ad-hoc regexes — the
# real-AI field test showed they cover a demo, not a plant.)
from device_lexicon import (  # type: ignore  # noqa: E402
    classify_text, equipment_from_text, port_synonyms,
)


def _classify_device(dev: Device) -> Optional[str]:
    """Return the library contract stem for a device, or None (→ #UNKNOWN)."""
    text = " ".join([dev.description] + [s.get("desc", "") for s in dev.signals])
    all_analog = bool(dev.signals) and all(
        s.get("type") == "AI" for s in dev.signals)
    return classify_text(text, prefix=dev.prefix, all_analog=all_analog)


_KNOWN_LIFECYCLE_VALUES = frozenset({
    "DRAFT",
    "AUTO_VERIFIED_structural",
    "AUTO_VERIFIED_structural_plcrex",
    "PENDING_TIA_VERIFY",
    "VALIDATED",
    "FROZEN",
})


def _get_lifecycle_from_entry(entry: dict) -> str:
    """Safely extract the lifecycle value from a contract entry.

    Fail-safe: returns ``"DRAFT"`` when the field is missing, the parse fails or
    the value is unrecognized. Guarantees unknown blocks always emit a DRAFT
    warning.
    """
    try:
        raw = (entry.get("data") or {}).get("block", {}).get("lifecycle", "DRAFT")
        if raw not in _KNOWN_LIFECYCLE_VALUES:
            return "DRAFT"
        return raw
    except Exception:
        return "DRAFT"


def load_contracts() -> dict[str, dict]:
    """{contract_stem: {"contract_path": Path, "scl_path": Path, "data": dict}}
    — stem taken from the contract FILENAME (FB_Motor_DOL.contract.json),
    matched case-insensitively to the block .scl file."""
    scl_by_stem_ci = {p.stem.lower(): p for p in BLOCKS_DIR.rglob("*.scl")}
    out: dict[str, dict] = {}
    for cpath in CONTRACTS_DIR.rglob("*.contract.json"):
        stem = cpath.name[: -len(".contract.json")]
        scl = scl_by_stem_ci.get(stem.lower())
        if scl is None:
            continue  # contract without a block (schema etc.) — skip
        try:
            data = json.loads(cpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        out[stem] = {"contract_path": cpath, "scl_path": scl, "data": data}
    return out


# ---------------------------------------------------------------------------
# 3) Field-signal binding (feedbacks / overloads / main outputs only)
# ---------------------------------------------------------------------------

# Port-name token → acceptable signal tokens (suffix parts or description words)
_CAMEL_RE = re.compile(r"[A-Z][a-z0-9]*")

# Only these port families are wired to FIELD IO; commands/enables/modes are
# control-logic concerns and stay at contract defaults (listed as TODOs).
_BINDABLE_IN = re.compile(r"feedback|overload", re.IGNORECASE)
_BINDABLE_OUT = re.compile(r"run|open|close|output|main|star|delta|valve", re.IGNORECASE)
# Status/HMI outputs (out_bReadyOpen, out_bReadyClosed …) must NEVER take a
# field output: D-run 2026-07-03 mis-wired the valve CLOSE solenoid onto
# out_bReadyClosed via the "closed" token. Fail-safe: skip, leave as TODO.
_NONFIELD_OUT = re.compile(r"ready|status|lamp|error|fault|alarm", re.IGNORECASE)
# Analog raw-value input ports (FB_AnalogScale.in_iRawValue and friends)
_ANALOG_RAW_IN = re.compile(r"raw|istwert|actual|processvalue", re.IGNORECASE)


def _port_tokens(port: str) -> list[str]:
    base = re.sub(r"^(in|out|inout)_[a-z]", "", port)
    return [t.lower() for t in _CAMEL_RE.findall(base)]


def _signal_tokens(sig: dict) -> set[str]:
    toks = set()
    for part in (sig.get("suffix") or "").split("_"):
        if part:
            toks.add(part.lower())
    for w in re.findall(r"[A-Za-zÄÖÜäöüß]+", sig.get("desc", "")):
        toks.add(w.lower())
    # The tag itself carries port semantics ("Rollenbahn11Rueckm") — AI
    # drafts write CamelCase without underscores, so split it too.
    # (D-run 2026-07-03: without this, feedback tags scored 0.)
    for w in _CAMEL_RE.findall(sig.get("name", "")):
        toks.add(w.lower())
    return toks


def _fuzzy_hit(stoks: set[str], syns: frozenset) -> bool:
    """Exact token hit, or a compound-word hit for synonyms >= 5 chars.

    German plant vocabulary compounds relentlessly ("NETZSCHUETZ",
    "MOTORSCHUTZUEBERW.") — exact set intersection alone misses it
    (D-run 2026-07-03). Only the FULL synonym inside a longer token
    counts ("schuetz" ⊂ "netzschuetz"); prefix matching is deliberately
    NOT done — a generic token ("motor") must never trigger a longer
    synonym ("motorschutz"). Abbreviations ("rueckm") are listed
    explicitly in the lexicon instead. Short synonyms (<5 chars: "rm",
    "ein", "auf") stay exact-only."""
    if stoks & syns:
        return True
    for s in syns:
        if len(s) < 5:
            continue
        for t in stoks:
            if len(t) > len(s) and s in t:
                return True
    return False


def _score(port: str, sig: dict) -> int:
    ptoks = _port_tokens(port)
    stoks = _signal_tokens(sig)
    score = 0
    for pt in ptoks:
        if _fuzzy_hit(stoks, port_synonyms(pt)):
            score += 1
    # Discriminating-token rule: "feedback" alone must not qualify a signal
    # for a SPECIFIC feedback port (D-run 2026-07-03: a run feedback landed
    # on in_bFeedbackOverload). If the port carries semantic tokens beyond
    # the generic 'feedback', at least one of THOSE must hit.
    specific = [pt for pt in ptoks if pt != "feedback"]
    if specific and not any(
            _fuzzy_hit(stoks, port_synonyms(pt)) for pt in specific):
        return 0
    return score


def bind_device(match: DeviceMatch) -> None:
    """Fill in/out bindings for one matched device (conservative: a port is
    bound only when exactly one signal holds the top score)."""
    iface = (match_contract(match).get("interface") or {})
    dev = match.device
    di = [s for s in dev.signals if s.get("type") == "DI"]
    dq = [s for s in dev.signals if s.get("type") == "DQ"]
    bound_signals: set[str] = set()

    def _bind(ports: list[dict], pool: list[dict], bindable: re.Pattern,
              target: dict) -> None:
        for port in ports:
            name = port.get("name", "")
            if port.get("iec_type") != "Bool" or not bindable.search(name):
                continue
            if target is match.out_bindings and _NONFIELD_OUT.search(name):
                continue  # status/HMI output — never wire field IO to it
            scored = [(s, _score(name, s)) for s in pool
                      if s["name"] not in bound_signals]
            scored = [(s, sc) for s, sc in scored if sc > 0]
            if not scored:
                if port.get("required"):
                    match.todos.append(
                        f"{name} not wired — no matching {dev.device_id} signal in RD01")
                continue
            top = max(sc for _s, sc in scored)
            best = [s for s, sc in scored if sc == top]
            if len(best) != 1:
                match.todos.append(
                    f"{name} ambiguous — candidates: "
                    + ", ".join(s["name"] for s in best) + " (wire manually)")
                continue
            target[name] = best[0]["name"]
            bound_signals.add(best[0]["name"])

    _bind(iface.get("inputs", []), di, _BINDABLE_IN, match.in_bindings)
    _bind(iface.get("outputs", []), dq, _BINDABLE_OUT, match.out_bindings)

    # Analog raw-value inputs (Int ports named Raw/Istwert/Actual) take the
    # device's AI signal. Conservative: a single AI binds directly; several
    # AIs need a unique token winner, else an honest TODO.
    ai = [s for s in dev.signals if s.get("type") == "AI"]
    for port in iface.get("inputs", []):
        name = port.get("name", "")
        if port.get("iec_type") != "Int" \
                or not _ANALOG_RAW_IN.search(name):
            continue
        pool = [s for s in ai if s["name"] not in bound_signals]
        if not pool:
            if port.get("required"):
                match.todos.append(
                    f"{name} not wired — no AI signal on {dev.device_id}")
            continue
        if len(pool) == 1:
            best = pool
        else:
            scored = [(s, _score(name, s)) for s in pool]
            top = max(sc for _s, sc in scored)
            best = [s for s, sc in scored if sc == top and top > 0]
        if len(best) != 1:
            match.todos.append(
                f"{name} ambiguous — candidates: "
                + ", ".join(s["name"] for s in pool) + " (wire manually)")
            continue
        match.in_bindings[name] = best[0]["name"]
        bound_signals.add(best[0]["name"])

    # Unwired field outputs are dangerous to forget — surface them.
    for s in dq:
        if s["name"] not in bound_signals:
            match.todos.append(
                f"output signal {s['name']} not bound to any {match.contract_stem} port")
    for s in ai:
        if s["name"] not in bound_signals:
            match.todos.append(
                f"analog signal {s['name']} not bound to any "
                f"{match.contract_stem} port")


_contract_cache: dict[str, dict] = {}


def match_contract(match: DeviceMatch) -> dict:
    key = str(match.contract_path)
    if key not in _contract_cache:
        _contract_cache[key] = json.loads(
            match.contract_path.read_text(encoding="utf-8"))
    return _contract_cache[key]


# ---------------------------------------------------------------------------
# 4) Assembly
# ---------------------------------------------------------------------------

# Copied into every project (no per-device mapping needed). OBs are copied
# but never called from OB1.
_ALWAYS_INCLUDE = ["FB_ModeManager", "FB_Watchdog", "FB_AlarmHandler"]
_ALWAYS_INCLUDE_OBS = ["OB_Startup_OB100", "OB_Diagnostic_OB82", "OB_RackFailure_OB86"]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Delta assembly — change management ("add one motor" must not mean
# regenerating and re-reviewing the whole program)
# ---------------------------------------------------------------------------

MANIFEST_NAME = "_assembly_manifest.json"


def _device_row_hash(dev: Device) -> str:
    """Stable content hash over a device's RD01 rows — the change detector."""
    rows = sorted(
        (s.get("name", ""), s.get("type", ""), s.get("address", ""),
         s.get("desc", ""), s.get("suffix", ""))
        for s in dev.signals
    )
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()


def _manifest_path(project_root: Path) -> Path:
    return project_root / "_output" / "scl" / MANIFEST_NAME


def _write_manifest(project_root: Path, devices: list[Device],
                    matches: list["DeviceMatch"]) -> None:
    by_id = {m.device.device_id: m for m in matches}
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "devices": {
            d.device_id: {
                "row_hash": _device_row_hash(d),
                "fb": by_id[d.device_id].contract_stem if d.device_id in by_id else None,
                "instance_db": by_id[d.device_id].instance_db if d.device_id in by_id else None,
            }
            for d in devices
        },
    }
    p = _manifest_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def compute_delta(project_root: Path,
                  signals: Optional[list[dict]] = None) -> dict:
    """Compare the current RD01 against the last assembly manifest.

    Returns {"manifest_exists", "added", "changed", "removed", "unchanged",
    "generated_at"} — device-id lists, deterministic, no side effects. This
    is the preview the engineer sees BEFORE clicking "Regenerate affected"."""
    mp = _manifest_path(project_root)
    if signals is None:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        signals = parse_rd01_signals(project_root)
    devices, _loose = group_devices(signals or [])
    cur = {d.device_id: _device_row_hash(d) for d in devices}
    if not mp.is_file():
        return {"manifest_exists": False, "added": sorted(cur), "changed": [],
                "removed": [], "unchanged": [], "generated_at": ""}
    try:
        man = json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return {"manifest_exists": False, "added": sorted(cur), "changed": [],
                "removed": [], "unchanged": [], "generated_at": ""}
    old = {k: (v or {}).get("row_hash", "") for k, v in (man.get("devices") or {}).items()}
    return {
        "manifest_exists": True,
        "generated_at": man.get("generated_at", ""),
        "added": sorted(k for k in cur if k not in old),
        "changed": sorted(k for k in cur if k in old and cur[k] != old[k]),
        "removed": sorted(k for k in old if k not in cur),
        "unchanged": sorted(k for k in cur if k in old and cur[k] == old[k]),
    }


def assemble_delta(project_root: Path,
                   signals: Optional[list[dict]] = None) -> AssemblyResult:
    """Regenerate ONLY what the RD01 change touched.

    - added/changed devices: their instance DBs are (re)written
    - unchanged devices: files left byte-for-byte alone (manual tweaks survive)
    - OB_Main.scl: always regenerated (it is derived from the full device list)
    - removed devices: NEVER deleted automatically — listed as orphaned for
      the engineer to review and delete by hand (fail-safe)
    Falls back to a full assembly when no manifest exists yet."""
    delta = compute_delta(project_root, signals)
    if not delta["manifest_exists"]:
        return assemble_program(project_root, signals)
    affected = set(delta["added"]) | set(delta["changed"])
    return assemble_program(project_root, signals,
                            delta_only=affected,
                            orphaned=delta["removed"],
                            skipped=delta["unchanged"])


def assemble_program(project_root: Path,
                     signals: Optional[list[dict]] = None,
                     delta_only: Optional[set] = None,
                     orphaned: Optional[list] = None,
                     skipped: Optional[list] = None) -> AssemblyResult:
    """Run the deterministic assembly. *signals* may be injected for tests;
    defaults to parse_rd01_signals(project_root).

    delta_only (change management): device-ids whose files may be (re)written.
    All matches are still recomputed (OB_Main is derived from the FULL device
    list), but unchanged devices' files are left byte-for-byte alone and
    removed devices are only REPORTED as orphaned — never deleted."""
    res = AssemblyResult()
    _contract_cache.clear()
    res.delta_mode = delta_only is not None
    res.orphaned = sorted(orphaned or [])
    res.skipped = sorted(skipped or [])

    if signals is None:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        signals = parse_rd01_signals(project_root)
    if not signals:
        res.ok = False
        res.msg = ("RD01 IO list is empty or missing — approve the RD01 draft "
                   "(Gate 3) before assembling.")
        return res

    contracts = load_contracts()
    devices, loose = group_devices(signals)
    for sig in loose:
        res.unknown.append({
            "item": sig.get("name") or sig.get("raw", "?"),
            "reason": "tag does not follow SCOPE_EQUIP_NNN naming — cannot group",
            "class": classify_unknown(sig),
        })

    # -- map + bind ---------------------------------------------------------
    for dev in devices:
        stem = _classify_device(dev)
        if stem is None or stem not in contracts:
            res.unknown.append({
                "item": dev.device_id,
                "reason": (f"no library block for prefix '{dev.prefix}' / "
                           f"description '{dev.description[:60]}'"
                           if stem is None else
                           f"classified as {stem} but no contract+block found"),
                "signals": [s["name"] for s in dev.signals],
                "class": classify_unknown(
                    {"name": dev.device_id, "desc": dev.description}),
            })
            continue
        entry = contracts[stem]
        m = DeviceMatch(device=dev, contract_stem=stem,
                        scl_path=entry["scl_path"],
                        contract_path=entry["contract_path"],
                        instance_db=f"iDB_{dev.device_id}")
        bind_device(m)
        res.matches.append(m)

    # -- copy library blocks verbatim ----------------------------------------
    out_dir = project_root / "_output" / "scl"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_stems = sorted({m.contract_stem for m in res.matches}
                       | set(_ALWAYS_INCLUDE) | set(_ALWAYS_INCLUDE_OBS))
    if res.delta_mode:
        # Delta: copy only the blocks that serve an affected device, plus any
        # block file that is missing on disk (first-time need / deleted).
        _affected_stems = {m.contract_stem for m in res.matches
                           if m.device.device_id in (delta_only or set())}
        needed_stems = sorted(
            s for s in all_stems
            if s in _affected_stems or not (out_dir / f"{s}.scl").is_file())
    else:
        needed_stems = all_stems
    for stem in needed_stems:
        entry = contracts.get(stem)
        if entry is None:
            # locate block without contract (OBs may not need gating)
            src = next((p for p in BLOCKS_DIR.rglob(f"{stem}.scl")), None)
            if src is None:
                res.warnings.append(f"library block {stem} not found — skipped")
                continue
            cpath = None
            block_lifecycle = "DRAFT"  # fail-safe: kontratsız blok → DRAFT
        else:
            src, cpath = entry["scl_path"], entry["contract_path"]
            block_lifecycle = _get_lifecycle_from_entry(entry)

        # S-15 / B-P1: DRAFT lifecycle uyarısı — üretimi DURDURMA, sadece uyar.
        if block_lifecycle != "VALIDATED":
            res.warnings.append(
                f"WARNING [S-15/B-P1] library block '{stem}' lifecycle={block_lifecycle!r} — "
                "PLCSIM/test kanıtlı doğrulama tamamlanmamış. "
                "VALIDATED değilse saha kullanımı öncesi mühendis onayı gerekir. "
                "(promote_to_validated() ile lifecycle yükseltilebilir)"
            )

        dst = out_dir / src.name
        dst.write_bytes(src.read_bytes())
        src_sha, dst_sha = _sha256(src), _sha256(dst)
        res.copied.append({
            "name": src.name, "sha256": dst_sha,
            "verbatim": src_sha == dst_sha,
            "contract": cpath.name if cpath else None,
            "lifecycle": block_lifecycle,
        })

    # -- FB block names from the copied sources ------------------------------
    # Read from ALL stems present in _output/scl (delta mode: unchanged
    # devices' blocks were copied by an earlier run) — OB_Main needs them all.
    fb_names: dict[str, str] = {}
    for stem in all_stems:
        p = out_dir / f"{stem}.scl"
        if p.is_file():
            m = _FB_NAME_RE.search(p.read_text(encoding="utf-8", errors="replace"))
            if m:
                fb_names[stem] = m.group(1)

    # -- instance DBs + OB1 ---------------------------------------------------
    from ob1_generator import (  # type: ignore
        InstanceCall, generate_instance_db, generate_ob1_from_instances,
    )
    calls: list[InstanceCall] = []
    for m in res.matches:
        m.fb_block_name = fb_names.get(m.contract_stem, m.contract_stem)
        db_path = out_dir / f"{m.instance_db}.db"
        _write_db = (not res.delta_mode
                     or m.device.device_id in (delta_only or set())
                     or not db_path.is_file())
        if _write_db:
            db_path.write_text(
                generate_instance_db(m.instance_db, m.fb_block_name),
                encoding="utf-8")
            res.generated.append(db_path.name)
            if res.delta_mode:
                res.affected.append(m.device.device_id)
        calls.append(InstanceCall(
            instance_db=m.instance_db, fb_name=m.fb_block_name,
            comment=f"{m.device.device_id} — {m.device.description} ({m.fb_block_name})",
            in_bindings=m.in_bindings, out_bindings=m.out_bindings,
            todos=m.todos,
        ))
    # system singletons
    for stem in _ALWAYS_INCLUDE:
        fbn = fb_names.get(stem)
        if not fbn:
            continue
        inst = f"iDB_{stem.replace('FB_', '')}"
        _sys_db = out_dir / f"{inst}.db"
        if not res.delta_mode or not _sys_db.is_file():
            _sys_db.write_text(generate_instance_db(inst, fbn), encoding="utf-8")
            res.generated.append(f"{inst}.db")
        calls.append(InstanceCall(
            instance_db=inst, fb_name=fbn,
            comment=f"system block {fbn}",
            todos=[f"configure {fbn} parameters for this project"],
        ))

    ob1_src = generate_ob1_from_instances(calls, ob_name="OB_Main")
    ob1_path = out_dir / "OB_Main.scl"
    ob1_path.write_text(ob1_src, encoding="utf-8")
    res.generated.append(ob1_path.name)

    # -- validation -----------------------------------------------------------
    from scl_validator import validate_scl_file  # type: ignore
    for p in sorted(out_dir.glob("*.scl")):
        vr = validate_scl_file(p)
        res.validation.append({
            "file": p.name, "errors": vr.error_count, "warnings": vr.warning_count,
            "issues": [f"[{i.severity}] {i.message}" for i in vr.issues
                       if i.severity == "error"],
        })
    try:
        from fb_acceptance_check import run_gate  # type: ignore
        for c in res.copied:
            if not c["contract"]:
                continue
            gr = run_gate(out_dir / c["name"],
                          CONTRACTS_DIR / _find_contract_rel(c["contract"]))
            res.gate_results.append({
                "file": c["name"], "overall": gr.overall, "label": gr.label,
            })
    except Exception as exc:
        res.warnings.append(f"acceptance gate could not run: {exc}")

    # Orphaned devices (delta): still in _output but gone from RD01 — the
    # engineer decides; auto-deleting a .db that TIA may reference is unsafe.
    for dev_id in res.orphaned:
        res.warnings.append(
            f"ORPHANED: device {dev_id} is no longer in RD01 but its files "
            f"(iDB_{dev_id}.db and its FB call) were NOT deleted — remove "
            "them manually after review, and re-import OB_Main.scl (already "
            "regenerated without the device).")

    if any(v["errors"] for v in res.validation):
        res.ok = False
        res.msg = "Assembly produced SCL with structural errors — see report."
    elif any(g["overall"] == "FAIL" for g in res.gate_results):
        res.ok = False
        res.msg = "A copied library block FAILED its contract gate (library drift?)."
    elif res.delta_mode:
        res.msg = (f"Delta assembly: {len(set(res.affected))} device(s) "
                   f"regenerated, {len(res.skipped)} untouched, "
                   f"{len(res.orphaned)} orphaned (manual review), "
                   "OB_Main.scl rebuilt.")
    else:
        gaps = sum(1 for u in res.unknown
                   if u.get("class", "device_gap") == "device_gap")
        res.msg = (f"Assembled {len(res.matches)} device instance(s), "
                   f"{len(res.unknown)} unknown item(s) "
                   f"({gaps} possible device gap(s) to review, the rest are "
                   "operator-panel/internal-flag items).")

    # Manifest = the delta baseline for the NEXT run. Only a clean result may
    # move the baseline — a failed run must stay visible as a pending change.
    if res.ok:
        try:
            _write_manifest(project_root, devices, res.matches)
        except Exception as exc:
            res.warnings.append(f"assembly manifest not written: {exc}")

    res.report_path = _write_report(project_root, res)
    return res


def _find_contract_rel(contract_name: str) -> Path:
    for p in CONTRACTS_DIR.rglob(contract_name):
        return p.relative_to(CONTRACTS_DIR)
    raise FileNotFoundError(contract_name)


# ---------------------------------------------------------------------------
# 5) Report
# ---------------------------------------------------------------------------

def _write_report(project_root: Path, res: AssemblyResult) -> Path:
    reports = project_root / "REPORTS"
    reports.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L: list[str] = [
        "# ASSEMBLY REPORT — library-first program assembly",
        "",
        f"Generated: {now}",
        f"Result: {'OK' if res.ok else 'FAILED'} — {res.msg}",
        "",
    ]
    if res.delta_mode:
        L += [
            "## Delta run (change management)",
            "",
            f"- Regenerated devices: {', '.join(sorted(set(res.affected))) or '—'}",
            f"- Untouched devices (files preserved): {', '.join(res.skipped) or '—'}",
            f"- Orphaned (in _output but no longer in RD01 — **review & delete "
            f"manually**): {', '.join(res.orphaned) or '—'}",
            "- OB_Main.scl was rebuilt from the full current device list.",
            "",
        ]
    L += [
        "Label: `AUTO_VERIFIED_structural | PENDING_TIA_VERIFY` — TIA compile",
        "and PLCSIM run are still required before field use.",
        "",
        "## Device → Library mapping",
        "",
        "| Device | Library FB | Instance DB | Bound inputs | Bound outputs |",
        "|--------|-----------|-------------|--------------|---------------|",
    ]
    for m in res.matches:
        L.append(
            f"| {m.device.device_id} | {m.fb_block_name} | {m.instance_db} | "
            f"{', '.join(f'{k}←{v}' for k, v in m.in_bindings.items()) or '—'} | "
            f"{', '.join(f'{k}→{v}' for k, v in m.out_bindings.items()) or '—'} |")
    L += ["", "### Engineering TODOs (unwired ports)"]
    any_todo = False
    for m in res.matches:
        for t in m.todos:
            L.append(f"- **{m.device.device_id}**: {t}")
            any_todo = True
    if not any_todo:
        L.append("- none")
    L += ["", "## #UNKNOWN — needs an engineer (never silently dropped)"]
    if res.unknown:
        # Grouped by failure class (F4): the engineer reads three short
        # lists instead of one 295-line wall, and only device_gap items
        # actually demand action.
        for cls in ("device_gap", "operator_panel", "internal_flag"):
            items = [u for u in res.unknown
                     if u.get("class", "device_gap") == cls]
            if not items:
                continue
            L += ["", f"### {UNKNOWN_CLASSES[cls]} ({len(items)})", ""]
            for u in items:
                sigs = (f" (signals: {', '.join(u.get('signals', []))})"
                        if u.get("signals") else "")
                L.append(f"- **{u['item']}** — {u['reason']}{sigs}")
    else:
        L.append("- none")
    L += ["", "## Copied library blocks (verbatim proof)",
          "", "| File | SHA-256 (first 16) | Verbatim | Lifecycle | Contract |",
          "|------|--------------------|----------|-----------|----------|"]
    for c in res.copied:
        lc = c.get("lifecycle", "DRAFT")
        lc_mark = lc if lc == "VALIDATED" else f"**{lc}** (DRAFT-WARN)"
        L.append(f"| {c['name']} | `{c['sha256'][:16]}` | "
                 f"{'✓' if c['verbatim'] else '✗ MODIFIED!'} | {lc_mark} | {c['contract'] or '—'} |")
    L += ["", "## Generated sources", ""]
    for g in res.generated:
        L.append(f"- {g}")
    L += ["", "## Validation", "",
          "| File | Errors | Warnings |", "|------|--------|----------|"]
    for v in res.validation:
        L.append(f"| {v['file']} | {v['errors']} | {v['warnings']} |")
        for issue in v["issues"]:
            L.append(f"|  └ {issue} | | |")
    if res.gate_results:
        L += ["", "## Contract gate (copied blocks)", "",
              "| File | Overall | Label |", "|------|---------|-------|"]
        for g in res.gate_results:
            L.append(f"| {g['file']} | {g['overall']} | {g['label']} |")
    if res.warnings:
        L += ["", "## Warnings", ""]
        for w in res.warnings:
            L.append(f"- {w}")
    path = reports / "ASSEMBLY_REPORT.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path
