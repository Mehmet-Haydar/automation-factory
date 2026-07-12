"""S-16 / B-P2 — Gate 6 compile log + mühendis beyanı zorunlu (proof testleri).

Her test hem fix varken GEÇMELİ hem de fix geri alınırsa KIRILMALI davranışı
assert eder — smoke testi değil; fail-closed koruyucu davranışın kanıtı.

Kapsam:
  1. Compile log yolu verilmemiş → blocker üretilmeli
  2. Compile log yolu verilmiş ama dosya yok → blocker üretilmeli
  3. Mühendis beyanı yapılmamış → blocker üretilmeli
  4. Her ikisi de sağlanmış (dosya var + beyan=True) → blocker üretilmemeli
  5. Diğer gate'ler (3, 5, 7) bu yeni kuraldan ETKİLENMEMELİ
  6. advance_gate() gerçek çağrısında gate 6 kaydı kanıt alanlarını içermeli
  7. advance_gate() gerçek çağrısında gate 6 kanıt note payloada gömülü → hash zinciri korumalı
  8. Gate 6 kaydı: note alanında compile_log ve manual_test_confirmed görünmeli
"""

from __future__ import annotations

import importlib
import json
import os
import hashlib
from pathlib import Path

import pytest

fw = importlib.import_module("factory_web")
_blockers = fw._gate_advance_blockers

ALL_DONE = {f"RD{n:02d}": "done" for n in range(1, 15)}
VALID_SIG = "M. Yilmaz (müh.)"


# ---------------------------------------------------------------------------
# TEST 1: Compile log yolu verilmemiş → blocker
# ---------------------------------------------------------------------------

def test_gate6_missing_compile_log_blocks():
    """Compile log yolu boş → blocker üretilmeli.

    Fix geri alınırsa (gate 6 özel kuralı kaldırılırsa) bu test kırılır.
    """
    b = _blockers(6, ALL_DONE, signature=VALID_SIG,
                  compile_log_path="",
                  manual_test_confirmed=True)
    assert any("compile_log" in x.lower() or "compile log" in x.lower() for x in b), (
        f"Compile log yolu eksikken blocker bekleniyor; blockers={b}"
    )


# ---------------------------------------------------------------------------
# TEST 2: Compile log yolu verilmiş ama dosya disk'te yok → blocker
# ---------------------------------------------------------------------------

def test_gate6_nonexistent_compile_log_blocks():
    """Var olmayan compile log yolu → blocker üretilmeli (fail-closed).

    Fix geri alınırsa bu test kırılır.
    """
    b = _blockers(6, ALL_DONE, signature=VALID_SIG,
                  compile_log_path="/nonexistent/path/compile_log.txt",
                  manual_test_confirmed=True)
    assert any("not found" in x.lower() or "bulunamadı" in x.lower() or "exist" in x.lower()
               for x in b), (
        f"Var olmayan dosya için blocker bekleniyor; blockers={b}"
    )


# ---------------------------------------------------------------------------
# TEST 3: Mühendis beyanı False → blocker
# ---------------------------------------------------------------------------

def test_gate6_missing_manual_test_declaration_blocks(tmp_path):
    """manual_test_confirmed=False → blocker üretilmeli.

    Fix geri alınırsa bu test kırılır.
    """
    log_file = tmp_path / "compile.log"
    log_file.write_text("Compile OK")
    b = _blockers(6, ALL_DONE, signature=VALID_SIG,
                  compile_log_path=str(log_file),
                  manual_test_confirmed=False)
    assert any("manual" in x.lower() or "beyan" in x.lower() or "declaration" in x.lower()
               for x in b), (
        f"Mühendis beyanı eksikken blocker bekleniyor; blockers={b}"
    )


# ---------------------------------------------------------------------------
# TEST 4: Her ikisi sağlandı → blocker YOK (fail-open değil; bu geçiş koşulu)
# ---------------------------------------------------------------------------

def test_gate6_with_valid_compile_log_and_declaration_passes(tmp_path):
    """Compile log var + beyan True → gate 6 blockerı olmamalı.

    Fix varken GEÇMELİ; bu testin doğru koşul altında geçtiğini kanıtlar.
    """
    log_file = tmp_path / "compile.log"
    log_file.write_text("TIA Portal compile completed successfully")
    b = _blockers(6, ALL_DONE, signature=VALID_SIG,
                  compile_log_path=str(log_file),
                  manual_test_confirmed=True)
    assert b == [], f"Tüm koşullar sağlandığında blocker olmamalı; blockers={b}"


# ---------------------------------------------------------------------------
# TEST 5: Diğer gate'ler (3, 5, 7) compile log kuralından ETKİLENMEMELİ
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("gate", [3, 5, 7])
def test_other_approval_gates_unaffected_by_gate6_rule(gate):
    """Gate 3/5/7 için compile log ve beyan parametresi verilmeden de geçmeli.

    Bu test, B-P2 kuralının YALNIZCA gate 6'yı etkilediğini kanıtlar.
    Fix, diğer gate davranışını değiştirmiş olsaydı bu test kırılırdı.
    """
    b = _blockers(gate, ALL_DONE, signature=VALID_SIG,
                  compile_log_path="",
                  manual_test_confirmed=False)
    # compile log / manual test mesajı olmamalı
    gate6_msgs = [x for x in b
                  if "compile_log" in x.lower() or "compile log" in x.lower()
                  or "manual" in x.lower() or "declaration" in x.lower()]
    assert gate6_msgs == [], (
        f"Gate {gate} gate-6'ya özgü blocker mesajı içermemeli; gate6_msgs={gate6_msgs}"
    )


# ---------------------------------------------------------------------------
# TEST 6: advance_gate() kaydında compile_log_path ve manual_test_confirmed var
# ---------------------------------------------------------------------------

def test_gate6_advance_record_contains_evidence_fields(tmp_path):
    """advance_gate() gate 6 kaydında compile_log_path + manual_test_confirmed alanları olmalı.

    Fix geri alınırsa (bu alanlar saklanmasaydı) bu test kırılır.
    """
    # Minimal proje dizisi kur
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 6, "gate_history": []}), encoding="utf-8"
    )

    # Compile log oluştur
    log_file = tmp_path / "tia_compile.log"
    log_file.write_text("TIA Portal compile OK")

    # RD14 oluştur (gate 6 config: ["RD13"]; gate 7: ["RD14"])
    # Gate 6 = index 5 = {"rds": ["RD13"], "actions": ["export_tia","send_to_tia"]}
    # Bütün RD'leri "done" say → proje_analyzer yerine direct state kullan
    # Factory nesnesini kurmak yerine advance_gate mantığını _gate_advance_blockers
    # üzerinden test ettik; bu test advance_gate'in record'ına odaklanıyor.
    # Factory'yi doğrudan çağırmak için bir stub oluşturalım.

    import sys
    import types

    # project_analyzer mock — advance_gate içindeki try/except'te kullanılır
    mock_pa = types.ModuleType("project_analyzer")

    class MockRDStatus:
        status = "done"

    class MockAnalysis:
        rd_statuses = {f"RD{n:02d}": MockRDStatus() for n in range(1, 15)}

    mock_pa.analyze_project = lambda root: MockAnalysis()
    sys.modules["project_analyzer"] = mock_pa

    # Api() çağırıp root'u override et (test_gate_staleness.py deseniyle aynı)
    api = fw.Api()
    api.root = project_dir
    api.settings = {"username": "test"}

    # advance_gate çağır
    result = api.advance_gate(
        signature=VALID_SIG,
        accept_structural_only=False,
        compile_log_path=str(log_file),
        manual_test_confirmed=True,
    )

    assert result.get("ok"), f"advance_gate başarısız olmamalıydı; result={result}"

    # Kaydı kontrol et
    state = json.loads((project_dir / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    hist = state.get("gate_history", [])
    assert hist, "gate_history boş olmamalı"
    last = hist[-1]
    assert last.get("compile_log_path") == str(log_file), (
        f"compile_log_path kaydedilmeli; last={last}"
    )
    assert last.get("manual_test_confirmed") is True, (
        f"manual_test_confirmed=True kaydedilmeli; last={last}"
    )


# ---------------------------------------------------------------------------
# TEST 7: Gate 6 note alanı hash payloaduna gömülü → zincir korumalı
# ---------------------------------------------------------------------------

def test_gate6_advance_note_contains_evidence_in_payload(tmp_path):
    """Gate 6 kaydının note alanı compile_log ve manual_test_confirmed içermeli.

    Note alanı SHA-256 hash payload'una dahil olduğundan, kanıt hash-zinciri
    tarafından korunur — kurcalanırsa verify_gate_chain() hard ihlal üretir.

    Fix geri alınırsa (note sadece 'approved' olsaydı) bu test kırılır.
    """
    project_dir = tmp_path / "proj2"
    project_dir.mkdir()
    (project_dir / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 6, "gate_history": []}), encoding="utf-8"
    )

    log_file = tmp_path / "compile2.log"
    log_file.write_text("Compile output here")

    import sys, types

    mock_pa2 = types.ModuleType("project_analyzer")

    class MockRDStatus2:
        status = "done"

    class MockAnalysis2:
        rd_statuses = {f"RD{n:02d}": MockRDStatus2() for n in range(1, 15)}

    mock_pa2.analyze_project = lambda root: MockAnalysis2()
    sys.modules["project_analyzer"] = mock_pa2

    api = fw.Api()
    api.root = project_dir
    api.settings = {"username": "test"}

    result = api.advance_gate(
        signature=VALID_SIG,
        accept_structural_only=False,
        compile_log_path=str(log_file),
        manual_test_confirmed=True,
    )

    assert result.get("ok"), f"advance_gate başarısız: {result}"
    state = json.loads((project_dir / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    last = state["gate_history"][-1]
    note = last.get("note", "")
    assert "compile_log=" in note, f"note alanında compile_log= bekleniyor; note={note!r}"
    assert "manual_test_confirmed=True" in note, (
        f"note alanında manual_test_confirmed=True bekleniyor; note={note!r}"
    )

    # Hash tutarlılığını doğrula: note payload'da olduğundan hash da tutarlı olmalı
    payload_fields = ("gate", "when", "who", "signature", "note", "prev_hash")
    payload = json.dumps(
        {k: last[k] for k in payload_fields},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    expected_hash = hashlib.sha256(payload).hexdigest()
    assert last["hash"] == expected_hash, (
        f"Hash tutarsız — kanıt note payload'da; beklenen={expected_hash}, gerçek={last['hash']}"
    )


# ---------------------------------------------------------------------------
# TEST 8: Gate 6 için hem compile log hem beyan eksikken iki ayrı blocker
# ---------------------------------------------------------------------------

def test_gate6_both_missing_gives_two_blockers():
    """Her ikisi de eksikken iki blocker üretilmeli (birinin eksikliği diğerini gizlememeli).

    Fix geri alınırsa bu test kırılır.
    """
    b = _blockers(6, ALL_DONE, signature=VALID_SIG,
                  compile_log_path="",
                  manual_test_confirmed=False)
    compile_blockers = [x for x in b
                        if "compile_log" in x.lower() or "compile log" in x.lower()]
    manual_blockers = [x for x in b
                       if "manual" in x.lower() or "declaration" in x.lower()]
    assert compile_blockers, f"Compile log blocker bekleniyor; all_blockers={b}"
    assert manual_blockers, f"Mühendis beyanı blocker bekleniyor; all_blockers={b}"
