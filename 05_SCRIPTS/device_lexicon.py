#!/usr/bin/env python3
"""
device_lexicon.py — bilingual (DE/EN) industrial device vocabulary.

The deterministic brain behind device classification and port binding in
`program_assembler`. Field reality (real-AI field test 2026-07-02): legacy
DACH projects name things in German compound nouns ("Dosierpumpe",
"Abluftgebläse") and classic electrical shorthand ("Schuetz", "RM",
"Motorschutz") — a handful of English regexes covers a demo, not a plant.

Design rules
------------
1. DATA over code: vocabulary lives in frozen sets; matching logic is tiny
   and uniform. Extending the lexicon = adding a word, not writing a regex.
2. Compound-noun aware: German compounds carry the head noun at the END
   ("Kreisel|pumpe", "Abluft|gebläse") — stems match by word-suffix.
   Short/ambiguous tokens (FU, RM, K1) match only as EXACT words.
3. Umlaut tolerant: every stem is stored in its base form; matching folds
   ä→ae/a, ö→oe/o, ü→ue/u, ß→ss on BOTH sides.
4. Fail-safe: no match → None (#UNKNOWN downstream) — never guess.

The curated FB library itself (06_KNOWLEDGE_BASE/blocks) is untouched; this
module only decides WHICH library block a device maps to and HOW field
signals bind to its ports.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_UMLAUTS = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "s",
                          "Ä": "a", "Ö": "o", "Ü": "u"})


def fold(text: str) -> str:
    """Lowercase + umlaut-fold + collapse 'ae/oe/ue' digraphs to 'a/o/u'.

    Both "Gebläse", "Geblaese" and "Geblase" normalize to the same string,
    so one stored stem covers every spelling found in real exports."""
    t = (text or "").lower().translate(_UMLAUTS)
    t = t.replace("ae", "a").replace("oe", "o").replace("ue", "u").replace("ss", "s")
    return t


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", fold(text))


# ---------------------------------------------------------------------------
# Device-class stems (suffix-match on folded words, len >= 4)
# ---------------------------------------------------------------------------

# Motor-driven loads → FB_Motor_* family. Head nouns only; compounds match
# by suffix ("dosierpumpe".endswith("pumpe")).
MOTOR_STEMS = frozenset(fold(w) for w in (
    # pumps
    "pumpe", "pump",
    # fans / blowers
    "lüfter", "ventilator", "gebläse", "blower", "exhauster", "saugzug",
    # conveyors
    "förderband", "förderer", "conveyor", "bandantrieb", "gurtförderer",
    "rollgang", "kettenförderer", "schnecke", "schneckenförderer", "elevator",
    "becherwerk",
    # compressors
    "kompressor", "compressor", "verdichter",
    # mixing / process drives
    "rührwerk", "agitator", "mixer", "mischer", "kneter", "zentrifuge",
    "centrifuge", "extruder", "granulator", "brecher", "crusher", "mühle",
    "shredder", "zerkleinerer",
    # machine axes / hoisting
    "spindel", "spindle", "hubwerk", "winde", "winch", "hoist", "aufzug",
    "fahrwerk", "drehwerk", "wickler", "abwickler", "aufwickler", "haspel",
    # generic drive words (still motor family)
    "antrieb", "motor", "getriebemotor",
))

# Exact-word motor hints (too short/ambiguous for suffix matching)
MOTOR_WORDS = frozenset(fold(w) for w in ("fan", "band", "säge", "saw"))

# Valves / actuated fittings → FB_Valve_* family
VALVE_STEMS = frozenset(fold(w) for w in (
    "ventil", "valve", "magnetventil", "stellventil", "regelventil",
    "kugelhahn", "hahn", "klappe", "drosselklappe", "absperrklappe",
    "schieber", "absperrschieber", "damper", "zylinder",  # pneum. actuator
))
VALVE_WORDS = frozenset(fold(w) for w in ("mv", "ev"))

# Starter variant hints (checked inside the motor family)
VFD_STEMS = frozenset(fold(w) for w in (
    "umrichter", "frequenzumrichter", "inverter", "drehzahlregler",
))
VFD_WORDS = frozenset(fold(w) for w in ("fu", "vfd", "fc", "drive", "hız"))
STAR_DELTA_STEMS = frozenset(fold(w) for w in ("stern", "dreieck", "star",
                                               "delta", "yıldız", "üçgen"))
SOFTSTART_STEMS = frozenset(fold(w) for w in ("softstarter", "sanftanlauf",
                                              "sanftanlasser", "softstart"))

# Modulating/3-way valve hints. Matched as SUBSTRINGS of the folded text —
# "3-Wege-Ventil" tokenizes to ("3","wege","ventil") and would slip through
# word matching; the digit+wege pattern is unambiguous enough for substring
# search.
VALVE_3WAY = frozenset(fold(w) for w in ("3-wege", "3wege", "3 wege",
                                         "dreiwege", "3-way", "3way",
                                         "3 way", "3-yol", "3 yollu"))
VALVE_MODULATING_STEMS = frozenset(fold(w) for w in (
    "stellventil", "regelventil", "proportionalventil", "modulating",
    "oransal", "stellklappe", "regelklappe",
))

PID_WORDS = frozenset(("pid",))

# Tag prefixes (first token of SCOPE_EQUIP_NNN or an Equipment id)
MOTOR_PREFIXES = frozenset(fold(w) for w in (
    "MOT", "MTR", "MOTOR", "M",
    "PUMP", "PUMPE", "PMP", "P",
    "FAN", "LUEFTER", "VENT",
    "CONV", "CNV", "FB",          # FB = Förderband in many DACH plants
    "COMP", "KOMP", "VERD",
    "RW",                          # Rührwerk
))
VALVE_PREFIXES = frozenset(fold(w) for w in ("VLV", "VAL", "VALVE", "Y",
                                             "MV", "EV", "V"))


def _suffix_hit(token: str, stems: frozenset) -> bool:
    """Compound-aware: the token ends with a stem of length >= 4."""
    return any(len(s) >= 4 and token.endswith(s) for s in stems)


def _text_hits(text: str, stems: frozenset, exact: frozenset = frozenset()) -> bool:
    for w in words(text):
        if w in exact or _suffix_hit(w, stems):
            return True
    return False


def classify_text(text: str, prefix: str = "",
                  all_analog: bool = False) -> Optional[str]:
    """Map a device's pooled description text (+ optional tag prefix) to a
    library contract stem, or None (→ #UNKNOWN). Conservative by design."""
    pfx = fold(prefix)

    def motor_variant() -> str:
        if _text_hits(text, VFD_STEMS, VFD_WORDS):
            return "FB_Motor_VFD"
        # star/delta words compound in the wild ("STERNSCHUETZ",
        # "DREIECKS.") — suffix matching misses them (D-run 2026-07-03),
        # so these two stems also match as substrings of folded words.
        folded_words = words(text)
        if _text_hits(text, STAR_DELTA_STEMS) or any(
                ("stern" in w or "dreieck" in w) for w in folded_words):
            return "FB_Motor_StarDelta"
        if _text_hits(text, SOFTSTART_STEMS):
            return "FB_Motor_SoftStarter"
        return "FB_Motor_DOL"

    def valve_variant() -> str:
        folded = fold(text)
        if any(p in folded for p in VALVE_3WAY):
            return "FB_Valve_3Way"
        if _text_hits(text, VALVE_MODULATING_STEMS):
            return "FB_Valve_Modulating"
        return "FB_Valve_OnOff"

    # 1. Explicit prefix vote (strongest signal when present)
    if pfx and pfx in MOTOR_PREFIXES and pfx not in VALVE_PREFIXES:
        return motor_variant()
    if pfx and pfx in VALVE_PREFIXES and pfx not in MOTOR_PREFIXES:
        return valve_variant()

    # 2. PID / pure-analog devices before the generic text vote
    if _text_hits(text, frozenset(), PID_WORDS):
        return "FB_PID_Wrapper"
    if all_analog:
        return "FB_AnalogScale"

    # 3. Description vote (valve first: "Pumpenventil" is a valve)
    if _text_hits(text, VALVE_STEMS, VALVE_WORDS):
        return valve_variant()
    if _text_hits(text, MOTOR_STEMS, MOTOR_WORDS):
        return motor_variant()

    # 4. Ambiguous single-letter prefixes (M/P/V) resolved by text only —
    #    reaching here means the text gave no vote → honest None.
    return None


# ---------------------------------------------------------------------------
# Port-binding synonyms (contract port token → acceptable signal tokens)
# ---------------------------------------------------------------------------
# Sources: Siemens S7-300/400 era wiring conventions, DACH panel-builder
# shorthand, IEC device letters. Note: "schuetz" (contactor) is the RUN/MAIN
# output of a starter; "…schutz" (protection) is the OVERLOAD input — the
# folded forms stay distinct ("schutz" vs "schuz" after ss→s? no: schuetz →
# schutz? fold: 'schuetz' -> ue->u => 'schutz'; 'motorschutz' -> 'motorschutz'.
# COLLISION after folding! Therefore contactor words are stored UNFOLDED
# as exact tokens and matching for _SYN uses raw lowercase tokens, not fold().
PORT_SYNONYMS: dict[str, frozenset] = {
    "feedback": frozenset({
        "fb", "fbk", "rm", "feedback", "rueckmeldung", "ruckmeldung",
        "rückmeldung", "rueckm", "quittung", "laufmeldung",
        "betriebsmeldung", "bm", "running", "laeuft", "läuft",
    }),
    "run": frozenset({
        "run", "on", "running", "ein", "start", "betrieb", "schuetz",
        "schütz", "contactor", "k1", "freigabe", "enable",
        # Rückmeldung on a motor = contactor/run confirmation — the RUN
        # feedback, never the overload (D-run 2026-07-03 mis-bind).
        "rm", "rueckm", "rueckmeldung", "ruckmeldung", "rückmeldung",
    }),
    "overload": frozenset({
        "ol", "ovl", "overload", "th", "therm", "thermal", "bimetal",
        "bimetall", "motorschutz", "motorschutzrelais", "kaltleiter",
        "thermokontakt", "uberlast", "überlast", "ueberlast", "mschutz",
    }),
    "open": frozenset({
        "open", "opened", "zso", "lso", "auf", "offen", "ge_offen",
        "endschalter_auf", "geoeffnet", "geöffnet", "oeffnen", "öffnen",
    }),
    "closed": frozenset({
        "close", "closed", "zsc", "lsc", "zu", "geschlossen",
        "endschalter_zu", "schliessen", "schließen",
    }),
    "main": frozenset({"main", "k1", "schuetz", "schütz", "netz", "haupt"}),
    "star": frozenset({"star", "stern", "k2", "y"}),
    "delta": frozenset({"delta", "dreieck", "k3", "d"}),
    "fault": frozenset({
        "fault", "stoerung", "störung", "sto", "err", "error", "alarm",
    }),
}


def port_synonyms(port_token: str) -> frozenset:
    """Acceptable signal tokens for a contract-port token (plus itself)."""
    return PORT_SYNONYMS.get(port_token, frozenset()) | {port_token}


# ---------------------------------------------------------------------------
# Equipment id from legacy description text
# ---------------------------------------------------------------------------
# DACH Zuordnungsliste comments carry panel-page/device references:
# "KE ROLLENBAHN 1.1 * 7-M3 (EINLAUF)" → M3, "MOTORSCHUTZUEBERW. HYDRM. 5-M1"
# → M1. The page number prefix ("7-") disambiguates a real device reference
# from prose; a bare "M3" in text is NOT matched (too ambiguous).
# A/B/C benchmark (Beispielmaschine 4711 demo): the AI leaves
# the RD01 Equipment column empty in ~half the runs — wiring then collapses
# (15 → 5 bound ports). This deterministic extraction is the guarantee.
_DEVREF_RE = re.compile(r"\b\d+\s*-\s*([MKYFP]\d{1,3})\b", re.I)


def equipment_from_text(text: str) -> str:
    """Deterministic device id from a legacy description ('' when none)."""
    m = _DEVREF_RE.search(text or "")
    return m.group(1).upper() if m else ""
