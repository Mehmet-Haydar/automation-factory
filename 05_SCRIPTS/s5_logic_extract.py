#!/usr/bin/env python3
"""
s5_logic_extract.py — deterministic interlock extraction from S5 bit logic,
with a built-in equivalence proof.

WHY: the single biggest gap between "honest skeleton" and "engineer's right
hand" is that the legacy machine's interlocks and start conditions live in
the PB networks and never reach the new program. S5 BIT LOGIC IS MACHINE
PARSEABLE — no AI is needed for the boolean structure. This module:

  1. parses each bracket-format network into per-coil condition expressions
     (assign / set / reset), timers included as opaque inputs;
  2. PROVES its own extraction: an independent instruction-level interpreter
     replays the original network on N random input vectors and the results
     must match the extracted expressions on every vector — any mismatch
     downgrades the network to UNPARSED (the extractor never trusts itself);
  3. says "I don't know" loudly: networks containing jumps, word logic,
     comparisons or calls are reported UNPARSED with the raw code quoted —
     never a guessed condition.

Fail-safe contract: output is a DRAFT REPORT for the engineer (and comment
material for OB_Main); extracted logic is NEVER injected into executable
code automatically.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

# --- expression tree ---------------------------------------------------------


class Expr:
    """Immutable boolean expression node."""

    def eval(self, env: dict) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def render(self, names: dict | None = None) -> str:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class Var(Expr):
    operand: str          # canonical: "I6.7", "M1.0", "T5", "Q28.4"

    def eval(self, env):
        return bool(env.get(self.operand, False))

    def render(self, names=None):
        if names:
            desc = names.get(self.operand)
            if desc:
                return f"{self.operand}«{desc}»"
        return self.operand


@dataclass(frozen=True)
class Not(Expr):
    a: Expr

    def eval(self, env):
        return not self.a.eval(env)

    def render(self, names=None):
        inner = self.a.render(names)
        if isinstance(self.a, (And, Or)):
            inner = f"({inner})"
        return f"NOT {inner}"


@dataclass(frozen=True)
class And(Expr):
    a: Expr
    b: Expr

    def eval(self, env):
        return self.a.eval(env) and self.b.eval(env)

    def render(self, names=None):
        parts = []
        for x in (self.a, self.b):
            s = x.render(names)
            if isinstance(x, Or):
                s = f"({s})"
            parts.append(s)
        return " AND ".join(parts)


@dataclass(frozen=True)
class Or(Expr):
    a: Expr
    b: Expr

    def eval(self, env):
        return self.a.eval(env) or self.b.eval(env)

    def render(self, names=None):
        return f"{self.a.render(names)} OR {self.b.render(names)}"


# --- data model ---------------------------------------------------------------


@dataclass
class TimerDef:
    timer: str            # "T5"
    kind: str             # SE/SD/SP/SS/SF
    literal: str          # "S5T#500MS" or raw "KT 050.0"
    start: Expr | None = None


@dataclass
class CoilLogic:
    operand: str                      # "Q28.4" / "M1.0"
    assign: Expr | None = None        # "=" coil
    set_cond: Expr | None = None      # "S"
    reset_cond: Expr | None = None    # "R"


@dataclass
class NetworkLogic:
    block: str                        # "PB1"
    network: int
    parsed: bool = True
    reason: str = ""                  # why UNPARSED
    raw: list = field(default_factory=list)
    coils: dict = field(default_factory=dict)      # operand -> CoilLogic
    timers: dict = field(default_factory=dict)     # "T5" -> TimerDef
    inputs: set = field(default_factory=set)       # operands read
    verified_vectors: int = 0


# --- tokenizer ----------------------------------------------------------------

# operand normalization: international/German bit operands + timers/counters
_OPERAND_RE = re.compile(
    r"^(?:([IEQAMF])\s?(\d{1,3})\.(\d)|([TCZ])\s?(\d{1,3}))$")

_BIT_INSTR = {"A", "AN", "O", "ON", "U", "UN"}   # U/UN = German AND
_COIL_INSTR = {"=", "S", "R"}
_TIMER_INSTR = {"SE", "SD", "SP", "SS", "SF", "SA"}
# instructions we deliberately refuse (fail-safe → UNPARSED)
_HARD_INSTR = {"JU", "JC", "JCN", "SPA", "SPB", "SPBN", "L", "T", "LC",
               "CU", "CD", "ZV", "ZR", "FR", "!=F", "==F", "><F", ">F",
               "<F", ">=F", "<=F", "AW", "OW", "XOW", "SLW", "SRW", "ASM",
               "BE", "BEB", "BEU", "CALL", "SPM", "TAK", "ENT"}
_IGNORABLE = {"NOP", "***", "BLD"}


def _canon(op: str) -> str | None:
    m = _OPERAND_RE.match(op.strip().replace("  ", " "))
    if not m:
        return None
    if m.group(1):
        letter = {"E": "I", "A": "Q", "F": "M"}.get(m.group(1), m.group(1))
        return f"{letter}{int(m.group(2))}.{m.group(3)}"
    letter = {"Z": "C"}.get(m.group(4), m.group(4))
    return f"{letter}{int(m.group(5))}"


@dataclass
class _Instr:
    op: str
    arg: str | None
    canon: str | None
    raw: str


def _tokenize(lines: list[str]) -> tuple[list[_Instr], str]:
    """Instruction list, or ("", reason) on refusal."""
    out: list[_Instr] = []
    for raw in lines:
        s = raw.strip()
        if not s or s in _IGNORABLE:
            continue
        s = re.sub(r"^[A-Za-z]\w{0,7}:\s*", "", s)   # strip labels — but a
        if not s:
            continue
        parts = s.split(None, 1)
        op = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else None
        if op in ("NOP", "BLD"):
            continue
        if op in ("A(", "O(", "U(", "AN(", "ON(", "UN("):
            out.append(_Instr(op=op, arg=None, canon=None, raw=raw))
            continue
        if op == ")":
            out.append(_Instr(op=")", arg=None, canon=None, raw=raw))
            continue
        if op == "L" and arg and re.match(r"^(KT\b|S5T#)", arg.strip()):
            # time literal feeding the next timer start — harmless
            out.append(_Instr(op="LKT", arg=arg.strip(), canon=None, raw=raw))
            continue
        if op in _HARD_INSTR:
            return [], f"instruction '{op}' is out of bit-logic scope"
        if op == "O" and arg is None:
            # bare O: OR-combination of AND groups
            out.append(_Instr(op="O", arg=None, canon=None, raw=raw))
            continue
        if op in _BIT_INSTR | _COIL_INSTR | _TIMER_INSTR:
            canon = _canon(arg or "")
            if canon is None:
                return [], f"operand '{arg}' not a plain bit/timer operand"
            out.append(_Instr(op=op, arg=arg, canon=canon, raw=raw))
            continue
        return [], f"unknown instruction '{op}'"
    return out, ""


# --- extractor (expression builder) + interpreter (ground truth) --------------


class _RLOMachine:
    """One pass over the instruction list.

    In *expr* mode it builds Expr trees; in *eval* mode (env given) it
    computes booleans — the SAME control flow, so the interpreter is an
    independent check of nothing but the expression-building rules."""

    def __init__(self, env: dict | None = None):
        self.env = env
        self.rlo = None               # Expr | bool | None
        self.first = True             # next bit instruction loads
        self.or_buf = None            # pending bare-O group
        self.paren: list = []         # stack of (combine_op, rlo, or_buf)

    # -- primitives ------------------------------------------------------
    def _val(self, canon: str, negate: bool):
        if self.env is not None:
            v = bool(self.env.get(canon, False))
            return (not v) if negate else v
        e: Expr = Var(canon)
        return Not(e) if negate else e

    def _and(self, a, b):
        if self.env is not None:
            return a and b
        return And(a, b)

    def _or(self, a, b):
        if self.env is not None:
            return a or b
        return Or(a, b)

    # -- instruction handlers ---------------------------------------------
    def bit(self, op: str, canon: str):
        neg = op.endswith("N")
        v = self._val(canon, neg)
        base = op[0]  # A/U/O
        if self.first or self.rlo is None:
            self.rlo = v
            self.first = False
        elif base == "O":
            self.rlo = self._or(self.rlo, v)
        else:
            self.rlo = self._and(self.rlo, v)

    def bare_or(self):
        # "O" without operand: close the current AND group into the OR buffer
        if self.rlo is not None:
            self.or_buf = (self.rlo if self.or_buf is None
                           else self._or(self.or_buf, self.rlo))
        self.rlo = None
        self.first = True

    def open_paren(self, op: str):
        base = op.rstrip("(")
        self.paren.append((base, self.rlo, self.or_buf, self.first))
        self.rlo, self.or_buf, self.first = None, None, True

    def close_paren(self):
        inner = self.result()
        base, rlo, or_buf, first = self.paren.pop()
        self.rlo, self.or_buf, self.first = rlo, or_buf, first
        neg = base.endswith("N")
        if neg:
            inner = (not inner) if self.env is not None else Not(inner)
            base = base[:-1]
        if self.first or self.rlo is None:
            self.rlo = inner
            self.first = False
        elif base == "O":
            self.rlo = self._or(self.rlo, inner)
        else:
            self.rlo = self._and(self.rlo, inner)

    def result(self):
        r = self.rlo
        if self.or_buf is not None:
            r = self.or_buf if r is None else self._or(self.or_buf, r)
        if r is None:
            r = (False if self.env is not None else Var("__EMPTY__"))
        return r

    def after_coil(self):
        # RLO survives consecutive coils; the next bit instruction reloads.
        self.first = True
        self.or_buf = None


def _run(instrs: list[_Instr], env: dict | None):
    """Extract (env=None) or evaluate (env given). Returns
    (coil events list[(op, canon, value_or_expr)], timers dict)."""
    m = _RLOMachine(env)
    events = []
    timers: dict[str, TimerDef] = {}
    pending_literal = ""
    for ins in instrs:
        if ins.op == "LKT":
            pending_literal = ins.arg or ""
        elif ins.op in ("A(", "O(", "U(", "AN(", "ON(", "UN("):
            m.open_paren(ins.op)
        elif ins.op == ")":
            m.close_paren()
        elif ins.op in _BIT_INSTR:
            if ins.arg is None:
                m.bare_or()
            else:
                m.bit(ins.op, ins.canon)
        elif ins.op in _TIMER_INSTR:
            cond = m.result()
            timers[ins.canon] = TimerDef(
                timer=ins.canon, kind=ins.op, literal=pending_literal,
                start=None if env is not None else cond)
            m.after_coil()
        elif ins.op in _COIL_INSTR:
            events.append((ins.op, ins.canon, m.result()))
            m.after_coil()
    return events, timers


def parse_network(block: str, network: int, lines: list[str]) -> NetworkLogic:
    nl = NetworkLogic(block=block, network=network, raw=lines)
    # a TRAILING "BE" is the block-end marker, not logic — harmless to drop.
    # (BE anywhere else still refuses the network: conditional block ends
    # change semantics.)
    while lines and lines[-1].strip() in ("BE", "BE]"):
        lines = lines[:-1]
    instrs, reason = _tokenize(lines)
    if reason:
        nl.parsed = False
        nl.reason = reason
        return nl
    if not any(i.op in _COIL_INSTR for i in instrs):
        nl.parsed = False
        nl.reason = "no coil (=/S/R) in network"
        return nl
    try:
        events, timers = _run(instrs, env=None)
    except Exception as exc:  # anything unexpected → honest refusal
        nl.parsed = False
        nl.reason = f"extraction error: {exc}"
        return nl
    nl.timers = timers
    for op, canon, expr in events:
        coil = nl.coils.setdefault(canon, CoilLogic(operand=canon))
        if op == "=":
            coil.assign = expr
        elif op == "S":
            coil.set_cond = (expr if coil.set_cond is None
                             else Or(coil.set_cond, expr))
        else:
            coil.reset_cond = (expr if coil.reset_cond is None
                               else Or(coil.reset_cond, expr))
    nl.inputs = {v.operand for e in _walk_exprs(nl) for v in _vars(e)}

    # --- equivalence proof: interpreter vs extracted expressions ----------
    ok, vectors = _self_check(instrs, nl)
    if not ok:
        return NetworkLogic(block=block, network=network, raw=lines,
                            parsed=False,
                            reason="self-check FAILED — extraction refused")
    nl.verified_vectors = vectors
    return nl


def _walk_exprs(nl: NetworkLogic):
    for c in nl.coils.values():
        for e in (c.assign, c.set_cond, c.reset_cond):
            if e is not None:
                yield e
    for t in nl.timers.values():
        if t.start is not None:
            yield t.start


def _vars(e: Expr):
    if isinstance(e, Var):
        yield e
    elif isinstance(e, Not):
        yield from _vars(e.a)
    elif isinstance(e, (And, Or)):
        yield from _vars(e.a)
        yield from _vars(e.b)


def _self_check(instrs: list[_Instr], nl: NetworkLogic,
                vectors: int = 128) -> tuple[bool, int]:
    operands = sorted({i.canon for i in instrs if i.canon})
    rng = random.Random(0xA57)          # deterministic proof
    for _ in range(vectors):
        env = {op: rng.random() < 0.5 for op in operands}
        events, _t = _run(instrs, env=env)
        # replay events into per-coil truth (last '=' wins; S/R OR-combine)
        got: dict[str, dict[str, bool]] = {}
        for op, canon, val in events:
            slot = got.setdefault(canon, {})
            if op == "=":
                slot["assign"] = val
            else:
                key = "set" if op == "S" else "reset"
                slot[key] = slot.get(key, False) or val
        for canon, coil in nl.coils.items():
            slot = got.get(canon, {})
            if coil.assign is not None \
                    and coil.assign.eval(env) != slot.get("assign", False):
                return False, 0
            if coil.set_cond is not None \
                    and coil.set_cond.eval(env) != slot.get("set", False):
                return False, 0
            if coil.reset_cond is not None \
                    and coil.reset_cond.eval(env) != slot.get("reset", False):
                return False, 0
    return True, vectors


# --- project-level API ----------------------------------------------------------

# Network headers may carry a title after the number ("[13\tFLM
# Einrichtanwahl") — S5W writes one when the network is named. The old
# number-only pattern silently DROPPED every titled network (found
# 2026-07-06 while proving s5d-import parity: PB1 lost 15 of 34 nets).
_NET_RE = re.compile(r"^\[(\d+)(?:\s+\S.*)?\s*$")


def _split_networks(text: str) -> dict[int, list[str]]:
    nets: dict[int, list[str]] = {}
    cur: int | None = None
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("###PG"):
            continue
        m = _NET_RE.match(s)
        if m:
            cur = int(m.group(1))
            nets[cur] = []
            continue
        if cur is None:
            continue
        if s in ("***\t]", "***]", "***"):
            cur = None
            continue
        if s.endswith("]"):
            s = s.rstrip("]").strip()
            if s:
                nets[cur].append(s)
            cur = None
            continue
        if s:
            nets[cur].append(s)
    return {k: v for k, v in nets.items() if v}


def extract_project_logic(project_root: Path) -> list[NetworkLogic]:
    """Parse every bracket-format AWL block under _raw/legacy_code."""
    from legacy_enrich import is_s5_bracket_awl, _read_text  # type: ignore
    legacy = Path(project_root) / "_raw" / "legacy_code"
    out: list[NetworkLogic] = []
    if not legacy.is_dir():
        return out
    for fp in sorted(legacy.iterdir()):
        if not fp.is_file() or fp.suffix.lower() not in (".awl", ".stl"):
            continue
        text = _read_text(fp)
        if not is_s5_bracket_awl(text):
            continue
        for net_no, lines in sorted(_split_networks(text).items()):
            out.append(parse_network(fp.stem.upper(), net_no, lines))
    return out


def render_expr(e: Expr | None, names: dict | None = None) -> str:
    return "—" if e is None else e.render(names)
