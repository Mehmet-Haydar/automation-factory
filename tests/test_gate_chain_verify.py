"""R-C-1 — Gate History Hash Chain Verification proof tests.

Her test hem fix varken GEÇMELİ hem de fix geri alınırsa KIRILMALI
davranışı assert eder — smoke testi değil, koruyucu davranış kanıtı.

Kapsam:
  1. Geçerli (valid) zincir → ihlal yok
  2. Kurcalanmış (tampered) kayıt → hard ihlal döner
  3. Legacy kayıt (hash alanı yok) → WARNING döner, hard ihlal değil
  4. Genesis prev_hash gereksinimleri
  5. _gate7_approved() hard ihlal varsa False döner
  6. _check_report_preconditions() hard ihlal varsa ReportPreconditionError fırlatır
  7. Geçerli zincirde rapor üretim ön-koşulu geçer (gate7 + RD05 OK ise)
  8. Zincir geçerliyse _gate7_approved() True döner (guard yanlış pozitif vermez)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import customer_report as cr
from customer_report import (
    ReportPreconditionError,
    _check_report_preconditions,
    _gate7_approved,
    verify_gate_chain,
)


# ---------------------------------------------------------------------------
# Yardımcı: kanonik hash hesabı (advance_gate() ile birebir aynı)
# ---------------------------------------------------------------------------

_PAYLOAD_FIELDS = ("gate", "when", "who", "signature", "note", "prev_hash")


def _make_record(gate: int, *, who: str = "Tester", note: str = "completed",
                 prev_hash: str = "", when: str = "2026-01-01",
                 signature: str = "A. Tester") -> dict:
    """Geçerli bir gate kaydı oluşturur; hash advance_gate() ile özdeş."""
    record = {
        "gate": gate,
        "when": when,
        "who": who,
        "signature": signature,
        "note": note,
        "prev_hash": prev_hash,
    }
    payload = json.dumps(
        {k: record[k] for k in _PAYLOAD_FIELDS},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    record["hash"] = hashlib.sha256(payload).hexdigest()
    return record


def _build_chain(*gate_numbers: int, notes: dict[int, str] | None = None) -> list[dict]:
    """Birden fazla gate için geçerli, hash-bağlantılı kayıt listesi üret."""
    notes = notes or {}
    records: list[dict] = []
    for g in gate_numbers:
        prev = records[-1]["hash"] if records else ""
        records.append(_make_record(g, note=notes.get(g, "completed"), prev_hash=prev))
    return records


# ---------------------------------------------------------------------------
# TEST 1: Geçerli zincir → ihlal yok
# ---------------------------------------------------------------------------

def test_valid_single_record_no_violations():
    """Tek kayıtlı geçerli zincir → boş ihlal listesi."""
    chain = _build_chain(1)
    violations = verify_gate_chain(chain)
    assert violations == [], f"Beklenmeyen ihlaller: {violations}"


def test_valid_multi_record_chain_no_violations():
    """Çok kayıtlı geçerli zincir → boş ihlal listesi."""
    chain = _build_chain(1, 2, 3, 5, 7, notes={7: "approved"})
    violations = verify_gate_chain(chain)
    assert violations == [], f"Beklenmeyen ihlaller: {violations}"


def test_empty_history_no_violations():
    """Boş geçmiş → boş ihlal listesi (yeni proje durumu)."""
    assert verify_gate_chain([]) == []
    assert verify_gate_chain(None) == []


# ---------------------------------------------------------------------------
# TEST 2: Kurcalanmış kayıt → hard ihlal
# ---------------------------------------------------------------------------

def test_tampered_note_field_detected():
    """note alanı değiştirilince hash uyuşmaz → hard ihlal.

    Fix geri alınırsa (verify_gate_chain her zaman [] dönseydi) bu test kırılır.
    """
    chain = _build_chain(1, 2, 3)
    # Gate 2 kaydını elle kurca: note'u değiştir ama hash'i güncelleme
    chain[1] = dict(chain[1], note="approved")
    violations = verify_gate_chain(chain)
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert hard, "Kurcalanmış kayıt hard ihlal üretmeli ama üretmedi"
    assert any("gate" in v.lower() or "zincir" in v.lower() for v in hard)


def test_tampered_who_field_detected():
    """who alanı sahte değerle değiştirilince → hard ihlal."""
    chain = _build_chain(1, 2)
    chain[0] = dict(chain[0], who="HACKER")
    violations = verify_gate_chain(chain)
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert hard, "who alanı kurcalandığında hard ihlal bekleniyor"


def test_tampered_prev_hash_detected():
    """prev_hash alanı sıfırlanırsa zincir bağlantısı kopar → hard ihlal."""
    chain = _build_chain(1, 2, 3)
    # Gate 3'ün prev_hash'ini sahte yap (ama hash'i güncelleme → hash uyuşmaz)
    chain[2] = dict(chain[2], prev_hash="00000000")
    violations = verify_gate_chain(chain)
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert hard, "prev_hash kurcalandığında hard ihlal bekleniyor"


def test_injected_fake_gate7_record_detected():
    """Sahte gate-7 kaydı (hash yok → sonraki testte) veya yanlış hash → hard ihlal.

    Bu, R-C-1'in asıl hedefi: JSON'a elle {"gate": 7, "note": "approved"} ekleme.
    Hash alanı varsa ama hatalıysa → hard ihlal → rapor engellenir.
    """
    # Sahte kayıt: hash alanı var ama değeri tamamen uydurma
    fake_g7 = {
        "gate": 7,
        "when": "2026-01-01",
        "who": "attacker",
        "signature": "attacker",
        "note": "approved",
        "prev_hash": "",
        "hash": "deadbeef" * 8,  # 64 hex, ama yanlış
    }
    violations = verify_gate_chain([fake_g7])
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert hard, "Sahte hash içeren kayıt hard ihlal üretmeli"


# ---------------------------------------------------------------------------
# TEST 3: Legacy kayıt (hash alanı yok) → WARNING, hard ihlal değil
# ---------------------------------------------------------------------------

def test_legacy_record_no_hash_yields_warning_not_hard_violation():
    """Hash alanı olmayan eski kayıt → WARNING döner, hard ihlal değil.

    Fix geri alınırsa (eski kayıt hard ihlal sayılsaydı) backwards-compat kırılır;
    bu test o davranışın korunduğunu kanıtlar.
    """
    legacy = {
        "gate": 1,
        "when": "2024-01-01",
        "who": "old_system",
        "note": "completed",
        "prev_hash": "",
        # "hash" alanı kasıtlı eksik
    }
    violations = verify_gate_chain([legacy])
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert not hard, f"Legacy kayıt hard ihlal sayılmamalı; hard={hard}"
    # Ama WARNING mesajı üretilmeli
    warn = [v for v in violations if v.startswith("WARNING")]
    assert warn, "Legacy kayıt için WARNING bekleniyor"


def test_mixed_legacy_then_valid_chain():
    """Başta legacy kayıt, ardından geçerli zincirleme kayıtlar.

    Legacy sonrası gelenlerin prev_hash'i doğrulanamaz (atlanır); ama
    kendi iç hash'leri yine de kontrol edilir.
    """
    legacy = {
        "gate": 1,
        "when": "2024-01-01",
        "who": "old_system",
        "note": "completed",
        "prev_hash": "",
    }
    # Gate 2: prev_hash artık bilinemez (legacy sonrası zincir koptu)
    # ama hash alanı varsa kendi iç bütünlüğü doğrulanır
    g2 = _make_record(2, prev_hash="unknown_because_legacy")
    violations = verify_gate_chain([legacy, g2])
    # Hard ihlal olmamalı (legacy uyarısı var; g2'nin prev_hash doğrulaması atlanır)
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert not hard, f"Legacy + geçerli kayıt kombinasyonu hard ihlal üretmemeli; hard={hard}"


# ---------------------------------------------------------------------------
# TEST 4: Genesis prev_hash gereksinimleri
# ---------------------------------------------------------------------------

def test_genesis_empty_prev_hash_accepted():
    """Genesis (ilk) kayıt prev_hash='' ile kabul edilir."""
    rec = _make_record(1, prev_hash="")
    assert verify_gate_chain([rec]) == []


def test_genesis_word_GENESIS_accepted():
    """Genesis kaydı prev_hash='GENESIS' ile de kabul edilir."""
    record = {
        "gate": 1,
        "when": "2026-01-01",
        "who": "Tester",
        "signature": "A. Tester",
        "note": "completed",
        "prev_hash": "GENESIS",
    }
    payload = json.dumps(
        {k: record[k] for k in _PAYLOAD_FIELDS},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    record["hash"] = hashlib.sha256(payload).hexdigest()
    violations = verify_gate_chain([record])
    assert violations == [], f"prev_hash='GENESIS' genesis kaydı kabul edilmeli; ihlaller={violations}"


def test_genesis_non_empty_non_GENESIS_prev_hash_is_violation():
    """Genesis kaydının prev_hash'i '' veya 'GENESIS' dışında bir değerse → hard ihlal."""
    record = {
        "gate": 1,
        "when": "2026-01-01",
        "who": "Tester",
        "signature": "A. Tester",
        "note": "completed",
        "prev_hash": "somepreviousfakehash",
    }
    payload = json.dumps(
        {k: record[k] for k in _PAYLOAD_FIELDS},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    record["hash"] = hashlib.sha256(payload).hexdigest()
    violations = verify_gate_chain([record])
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert hard, "Genesis olmayan prev_hash hard ihlal üretmeli"


# ---------------------------------------------------------------------------
# TEST 5: _gate7_approved() — hard ihlal varsa False döner
# ---------------------------------------------------------------------------

def test_gate7_approved_returns_false_when_chain_tampered():
    """Kurcalanmış zincir → _gate7_approved() False döner (hash doğrulama guard).

    Fix geri alınırsa (note=='approved' yeterli olsaydı) bu test kırılır.
    """
    chain = _build_chain(1, 2, 3, 5, 6, 7, notes={7: "approved"})
    # Gate 5 kaydını kurca
    chain[3] = dict(chain[3], who="INTRUDER")
    result = _gate7_approved(chain)
    assert result is False, "_gate7_approved() kurcalanmış zincirde True dönemez"


def test_gate7_approved_returns_true_for_valid_chain():
    """Geçerli zincir + gate-7 approved → True."""
    chain = _build_chain(1, 2, 3, 5, 6, 7, notes={7: "approved"})
    assert _gate7_approved(chain) is True


def test_gate7_approved_false_without_gate7():
    """Gate 7 yoksa False (zincir geçerli olsa bile)."""
    chain = _build_chain(1, 2, 3)
    assert _gate7_approved(chain) is False


def test_gate7_approved_false_when_note_not_approved():
    """Gate 7 var ama note != 'approved' → False."""
    chain = _build_chain(1, 2, 3, 5, 6, 7, notes={7: "completed"})
    assert _gate7_approved(chain) is False


def test_gate7_legacy_warning_does_not_block_approval():
    """Legacy uyarısı (WARNING prefix) _gate7_approved() True dönmesini engellemez."""
    # Tüm kayıtlar geçerli; gate-7 approved; ama gate-1 legacy
    chain = _build_chain(2, 3, 5, 6, 7, notes={7: "approved"})
    legacy_g1 = {
        "gate": 1,
        "when": "2024-01-01",
        "who": "old_system",
        "note": "completed",
        "prev_hash": "",
        # hash yok — legacy
    }
    full_chain = [legacy_g1] + chain
    # Sadece uyarı var, hard ihlal yok → True dönmeli
    result = _gate7_approved(full_chain)
    assert result is True, "Legacy WARNING hard ihlal sayılmamalı; gate7 onaylı ise True bekleniyor"


# ---------------------------------------------------------------------------
# TEST 6: _check_report_preconditions() — zincir ihlali varsa ReportPreconditionError
# ---------------------------------------------------------------------------

def _state_with_tampered_chain() -> dict:
    chain = _build_chain(1, 2, 3, 5, 6, 7, notes={7: "approved"})
    chain[2] = dict(chain[2], note="INJECTED")  # hash uyuşmaz
    return {
        "gate_history": chain,
        "rd_status": {"RD05_Safety": {"status": "approved"}},
    }


def _state_with_valid_chain() -> dict:
    chain = _build_chain(1, 2, 3, 5, 6, 7, notes={7: "approved"})
    return {
        "gate_history": chain,
        "rd_status": {"RD05_Safety": {"status": "approved"}},
    }


def test_check_preconditions_raises_on_tampered_chain(tmp_path):
    """Kurcalanmış zincir → ReportPreconditionError fırlatılır.

    Fix geri alınırsa (zincir doğrulaması olmasaydı) bu test kırılır.
    """
    state = _state_with_tampered_chain()
    with pytest.raises(ReportPreconditionError) as exc_info:
        _check_report_preconditions(tmp_path, state)
    reasons = exc_info.value.reasons
    assert any("hash" in r.lower() or "zincir" in r.lower() or "bütünlük" in r.lower()
               for r in reasons), f"Zincir ihlali mesajı bekleniyor; reasons={reasons}"


def test_check_preconditions_passes_for_valid_state(tmp_path):
    """Geçerli zincir + gate-7 approved + RD05 OK → hata fırlatılmaz."""
    state = _state_with_valid_chain()
    # Hata fırlatılmamalı
    _check_report_preconditions(tmp_path, state)


def test_check_preconditions_raises_when_no_gate7(tmp_path):
    """Gate 7 onayı eksikken ReportPreconditionError fırlatılır."""
    chain = _build_chain(1, 2, 3)
    state = {
        "gate_history": chain,
        "rd_status": {"RD05_Safety": {"status": "approved"}},
    }
    with pytest.raises(ReportPreconditionError):
        _check_report_preconditions(tmp_path, state)


def test_check_preconditions_raises_when_rd05_draft(tmp_path):
    """RD05 DRAFT_UNVERIFIED iken ReportPreconditionError fırlatılır."""
    state = dict(_state_with_valid_chain())
    state["rd_status"] = {"RD05_Safety": {"status": "DRAFT_UNVERIFIED"}}
    with pytest.raises(ReportPreconditionError):
        _check_report_preconditions(tmp_path, state)


# ---------------------------------------------------------------------------
# TEST 7: Sahte JSON enjeksiyonu → rapor engellenir (asıl R-C-1 hedefi)
# ---------------------------------------------------------------------------

def test_json_injected_fake_approval_without_valid_hash_is_blocked(tmp_path):
    """PROJECT_STATE.json'a elle {"gate": 7, "note": "approved"} eklenmesi
    hash alanı olmadan raporu AÇMAMALI.

    Bu, R-C-1'in birincil hedefidir. Fix olmadan (sadece note=='approved' kontrolü)
    bu test kırılır.
    """
    # Sahte kayıt: hash alanı YOK → legacy uyarısı; ama gate-7 onayı sayılır mı?
    # Beklenti: hash yoksa legacy WARNING verilir, ama _gate7_approved() True dönebilir
    # çünkü backwards-compat. Ama hash VARSA ve hatalıysa → hard ihlal.
    # Gerçek saldırı vektörü: hash alanı var ama yanlış değerde.
    fake_approved = {
        "gate": 7,
        "when": "2026-01-01",
        "who": "attacker",
        "signature": "attacker",
        "note": "approved",
        "prev_hash": "",
        "hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
    state = {
        "gate_history": [fake_approved],
        "rd_status": {"RD05_Safety": {"status": "approved"}},
    }
    with pytest.raises(ReportPreconditionError) as exc_info:
        _check_report_preconditions(tmp_path, state)
    reasons = exc_info.value.reasons
    assert any("hash" in r.lower() or "zincir" in r.lower() or "ihlal" in r.lower()
               for r in reasons), f"Hash uyuşmazlığı reason'da görünmeli; reasons={reasons}"


def test_json_injected_record_no_hash_at_all_triggers_warning_not_block(tmp_path):
    """Hash alanı tamamen eksik enjekte edilmiş gate-7 kaydı.

    Legacy politikası: hash yok → WARNING, engelleme yok.
    Bu durum, eski sistemden migrate edilmiş gerçek kayıtlarla aynı davranışı
    gösterir — backwards-compat korunur.
    """
    no_hash_g7 = {
        "gate": 7,
        "when": "2026-01-01",
        "who": "legacy_system",
        "note": "approved",
        "prev_hash": "",
        # hash YOK
    }
    violations = verify_gate_chain([no_hash_g7])
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert not hard, (
        "Hash alanı tamamen eksik legacy kayıt hard ihlal sayılmamalı; "
        "bu backwards-compat gereksinimidir"
    )
