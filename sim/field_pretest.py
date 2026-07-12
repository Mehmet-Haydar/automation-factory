#!/usr/bin/env python3
"""
field_pretest.py — "Sahadan onceki son test" / pre-field smoke harness.

Amac: API key ile ESKI kod -> YENI SCL uretim hattini gercek
AutoFlowRunner motoru uzerinden uctan uca calistirmak ve uretilen SCL'i
scl_validator ile olcmek. Tutarliligi olcmek icin --runs N ile tekrarlanir.

Bu, GUI'deki "IO Extraction -> SCL Generation" workflow'unun ardindaki
ayni motoru (workbench/core/ai_runner.AutoFlowRunner) surer; yeni bir
implementasyon DEGILDIR.

Calisma modlari:
  * GERCEK : GEMINI_API_KEY (veya GOOGLE_API_KEY) ortam degiskeni varsa
             provider=google ile gercek Gemini cagrisi yapilir.
  * MOCK   : key yoksa, ai_runner.AIClient sahte bir istemci ile
             degistirilir (canli sabit SCL doner). Boylece model kalitesi
             haric butun zincir (oku -> prompt -> yaz -> dogrula) kanitlanir.

Kullanim:
  # Mock (key gerekmez) — zincirin saglamligini kanitlar:
  python sim/field_pretest.py --runs 1

  # Gercek Gemini — tutarlilik/hata olcumu:
  export GEMINI_API_KEY="AIza..."
  python sim/field_pretest.py --provider google --model gemini-2.5-flash --runs 5
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import threading
from pathlib import Path

# Windows console may default to cp1252 — non-ASCII project paths (e.g. a
# Turkish 'ı' in the repo folder name) would crash every print of a path.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "05_SCRIPTS"
for p in (str(ROOT), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scl_validator import validate_scl_file  # noqa: E402

# Workbench paketi (AutoFlowRunner) icin yol
sys.path.insert(0, str(ROOT))
from workbench.core import ai_runner  # noqa: E402
from workbench.core.ai_runner import AutoFlowRunner  # noqa: E402


# Ornek 1995 S7-300 legacy kodu (CONFIDENTIAL ornekten bagimsiz, sentetik)
LEGACY_AWL = (ROOT / "examples" / "Kunde_Mueller_Conveyor_Retrofit"
              / "_input" / "old_code_snippet.awl")

# MOCK modda donen sabit, gecerli SCL (scl_validator'dan gecmeli)
_MOCK_SCL = """\
FUNCTION_BLOCK "FB_EStop_Logic"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
   VAR_INPUT
      in_EStopNord_NC : Bool;   // I100.0
      in_EStopSued_NC : Bool;   // I100.1
   END_VAR
   VAR_OUTPUT
      out_MasterContactor : Bool;   // Q3.7
   END_VAR
BEGIN
   // AUTO_VERIFIED_structural | PENDING_TIA_VERIFY
   #out_MasterContactor := #in_EStopNord_NC AND #in_EStopSued_NC;
END_FUNCTION_BLOCK
"""


class _MockUsage:
    input_tokens = 1200
    output_tokens = 240

    def __str__(self):
        return "[mock] In: 1,200  Out: 240  $0.0000  0.0s"


class _MockAIClient:
    """ai_runner.AIClient yerine gecen sahte istemci. Zincir kanitidir."""

    def __init__(self, provider, api_key, model=None):
        self.provider, self.api_key, self.model = provider, api_key, model

    def chat(self, system, user, max_tokens=4096, on_chunk=None, temperature=0.3):
        # IO extraction adimi mi yoksa SCL adimi mi — basitce SCL dondur.
        text = _MOCK_SCL if "SCL" in user or "FUNCTION_BLOCK" in user or True else _MOCK_SCL
        if on_chunk:
            on_chunk(text)
        return text, _MockUsage()


def _setup_public_project(workdir: Path) -> Path:
    """Gemini'ye gidebilmesi icin PUBLIC etiketli gecici proje kurar."""
    proj = workdir / "PreField_SCL_Test"
    (proj / "metadata").mkdir(parents=True, exist_ok=True)
    (proj / "_input").mkdir(exist_ok=True)
    # PUBLIC siniflandirma — aksi halde classification guard bloklar (dogru davranis)
    (proj / "PROJECT_STATE.json").write_text(
        '{\n  "data_classification": "PUBLIC",\n'
        '  "project_name": "PreField_SCL_Test"\n}\n',
        encoding="utf-8",
    )
    src = proj / "_input" / "legacy.awl"
    src.write_text(LEGACY_AWL.read_text(encoding="utf-8", errors="ignore"),
                   encoding="utf-8")
    return src


def run_once(provider: str, model: str, api_key: str, run_idx: int) -> dict:
    """Tek kosu: workflow'u calistir, uretilen SCL'i dogrula, sonuc dondur."""
    result = {"run": run_idx, "ok": False, "scl_path": None,
              "errors": None, "warnings": None, "note": ""}

    with tempfile.TemporaryDirectory() as td:
        src = _setup_public_project(Path(td))
        proj_root = src.parent.parent

        done = threading.Event()
        errors_box: list[str] = []
        produced: list[Path] = []

        def on_step_start(i, name): print(f"    [{run_idx}] adim {i+1}: {name} ...")
        def on_step_chunk(t): pass
        def on_step_done(i, name, path):
            if str(path).endswith(".scl"):
                produced.append(Path(path))
        def on_flow_done(): done.set()
        def on_error(msg): errors_box.append(msg); done.set()
        def on_warn(msg): print(f"    [{run_idx}] WARN: {msg}")

        runner = AutoFlowRunner(
            provider=provider, model=model, api_key=api_key,
            project_root=proj_root,
            on_step_start=on_step_start, on_step_chunk=on_step_chunk,
            on_step_done=on_step_done, on_flow_done=on_flow_done,
            on_error=on_error, on_warn=on_warn,
        )
        runner.run_async("IO Extraction → SCL Generation", src)
        if not done.wait(timeout=120):
            result["note"] = "TIMEOUT (120s)"
            return result

        if errors_box:
            result["note"] = errors_box[0]
            return result
        if not produced:
            result["note"] = "SCL uretilmedi (REPORTS/*.scl yok)"
            return result

        scl = produced[-1]
        # Uretilen SCL kalici kalsin diye disari kopyala (sim/_out)
        out_dir = ROOT / "sim" / "_out"
        out_dir.mkdir(exist_ok=True)
        persisted = out_dir / f"run{run_idx}_{scl.name}"
        persisted.write_text(scl.read_text(encoding="utf-8", errors="ignore"),
                             encoding="utf-8")

        vr = validate_scl_file(persisted)
        result.update(ok=not vr.has_errors, scl_path=str(persisted),
                      errors=vr.error_count, warnings=vr.warning_count)
        return result


def main():
    ap = argparse.ArgumentParser(description="Pre-field SCL generation smoke test")
    ap.add_argument("--provider", default="google")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--runs", type=int, default=1)
    args = ap.parse_args()

    api_key = (os.environ.get("GEMINI_API_KEY")
               or os.environ.get("GOOGLE_API_KEY") or "")
    mock = not api_key

    print("=" * 64)
    print("  AUTOMATION_FACTORY — Sahadan Onceki Son Test (SCL uretimi)")
    print("=" * 64)
    print(f"  Girdi (eski kod) : {LEGACY_AWL.name}")
    print(f"  Saglayici/Model  : {args.provider} / {args.model}")
    print(f"  Mod              : {'MOCK (key yok — zincir kaniti)' if mock else 'GERCEK API'}")
    print(f"  Kosu sayisi      : {args.runs}")
    print("-" * 64)

    if mock:
        ai_runner.AIClient = _MockAIClient   # motoru sahte istemciyle besle
        api_key = "MOCK"

    rows = []
    for i in range(1, args.runs + 1):
        rows.append(run_once(args.provider, args.model, api_key, i))

    print("-" * 64)
    print("  SONUCLAR")
    ok_n = sum(1 for r in rows if r["ok"])
    for r in rows:
        status = "PASS" if r["ok"] else "FAIL"
        detail = (f"err={r['errors']} warn={r['warnings']}"
                  if r["errors"] is not None else r["note"])
        print(f"   kosu {r['run']}: {status:4}  {detail}")
    print("-" * 64)
    print(f"  TUTARLILIK: {ok_n}/{args.runs} kosu yapisal olarak gecerli SCL uretti")
    if rows and rows[0]["scl_path"]:
        print(f"  Ornek cikti: {rows[0]['scl_path']}")

    # ------------------------------------------------------------------
    # M5: library-first assembler smoke — deterministic, key gerektirmez.
    # Sentetik RD01 sinyalleri -> verbatim blok kopyalari + iDB'ler + OB1,
    # hepsi scl_validator + contract gate'ten gecmeli.
    # ------------------------------------------------------------------
    print("-" * 64)
    print("  ASSEMBLER SMOKE (library-first, deterministik)")
    assemble_ok = run_assembler_smoke()
    print("=" * 64)
    sys.exit(0 if (ok_n == args.runs and assemble_ok) else 1)


def run_assembler_smoke() -> bool:
    """Drive program_assembler end-to-end on a temp project."""
    from program_assembler import assemble_program  # noqa: E402
    signals = [
        {"name": "MOT_MAIN_001_FB",  "type": "DI", "address": "%I0.0",
         "desc": "Main drive run feedback", "raw": ""},
        {"name": "MOT_MAIN_001_OL",  "type": "DI", "address": "%I0.1",
         "desc": "Main drive overload", "raw": ""},
        {"name": "MOT_MAIN_001_RUN", "type": "DQ", "address": "%Q0.0",
         "desc": "Main drive motor contactor", "raw": ""},
        {"name": "VLV_AIR_001_OPEN", "type": "DQ", "address": "%Q1.0",
         "desc": "Air valve open solenoid", "raw": ""},
        {"name": "MYSTERY_DEV_001_X", "type": "DI", "address": "%I9.0",
         "desc": "must land in #UNKNOWN", "raw": ""},
    ]
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "proj"
        proj.mkdir()
        res = assemble_program(proj, signals=signals)
        v_err = sum(v["errors"] for v in res.validation)
        gate_fail = [g for g in res.gate_results if g["overall"] != "PASS"]
        unknown_ok = any(u["item"] == "MYSTERY_DEV_001" for u in res.unknown)
        print(f"   eslesme={len(res.matches)}  #UNKNOWN={len(res.unknown)}  "
              f"validator_err={v_err}  gate_fail={len(gate_fail)}")
        ok = bool(res.ok and res.matches and v_err == 0
                  and not gate_fail and unknown_ok)
        print(f"   assembler: {'PASS' if ok else 'FAIL'}  ({res.msg})")
        return ok


if __name__ == "__main__":
    main()
