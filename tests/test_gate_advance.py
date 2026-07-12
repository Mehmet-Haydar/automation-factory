"""C5 — Gate ilerletme ön-koşul + onay imzası (saf blocker mantığı)."""

import importlib

fw = importlib.import_module("factory_web")
_blockers = fw._gate_advance_blockers


# RD statuses: project_analyzer vocabulary (empty/template/in_progress/done/draft_unverified)
ALL_DONE = {f"RD{n:02d}": "done" for n in range(1, 15)}
ALL_EMPTY = {f"RD{n:02d}": "empty" for n in range(1, 15)}


def test_empty_required_rd_blocks():
    # Gate 1 needs RD01, RD02. If empty -> blocked.
    b = _blockers(1, ALL_EMPTY)
    assert any("RD01" in x for x in b)
    assert any("RD02" in x for x in b)


def test_done_rds_non_approval_gate_advances():
    # Gate 1 is NOT an approval gate; with RDs done there are no blockers.
    assert _blockers(1, ALL_DONE) == []


def test_draft_unverified_rd_does_not_block():
    # RD05 stays draft_unverified by design (safety) — must not block extraction.
    rd = dict(ALL_DONE)
    rd["RD05"] = "draft_unverified"
    assert _blockers(2, rd) == []


def test_approval_gate_requires_signature():
    # Gate 3 (Human Review) is an approval gate.
    b = _blockers(3, ALL_DONE, signature="")
    assert any("signature" in x.lower() or "approval" in x.lower() for x in b)


def test_approval_gate_with_signature_advances():
    assert _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)") == []


def test_validation_errors_block_validate_gate():
    # Gate 3 has a 'validate' action; known validation errors must block.
    b = _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)",
                  last_validation={"errors": 2, "scope": "semantic"})
    assert any("Validation" in x for x in b)


def test_validation_clean_does_not_block():
    # Clean SEMANTIC validation: no block. (structural_only is its own case.)
    b = _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)",
                  last_validation={"errors": 0, "scope": "semantic"})
    assert b == []


# -- W-A5: structural_only validation gates must refuse to advance --

def test_structural_only_validation_blocks_even_when_clean():
    """scl_validator is structural-only (keyword/parenthesis balance).
    A 'green' result is NOT the same as a semantic compile. Must block."""
    b = _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)",
                  last_validation={"errors": 0, "scope": "structural_only"})
    assert any("yapısal" in x.lower() or "structural" in x.lower() for x in b)


def test_structural_only_can_be_acknowledged_on_non_approval_gate():
    """User can explicitly acknowledge the scope gap on a non-approval gate that
    runs validation (gate 5, Validation) — e.g. after running compile inside TIA
    manually. S-7: approval gates block structural_only even with the flag.
    Phase model: validate actions live on gate 3 (approval) and gate 5
    (non-approval); the only non-approval gate with a validate action is 5."""
    # Gate 5 is NOT an approval gate: accept_structural_only=True clears the blocker.
    b = _blockers(5, ALL_DONE,
                  last_validation={"errors": 0, "scope": "structural_only"},
                  accept_structural_only=True)
    assert b == [], f"Non-approval gate 5 should allow accept_structural_only: {b}"


def test_structural_only_acknowledged_still_blocks_approval_gate():
    """S-7: accept_structural_only=True must NOT bypass an approval gate.
    Fail-closed: structural-only validation cannot satisfy an approval gate
    regardless of the caller flag. Gate 3 (Human Review) is the only approval
    gate carrying a validate action under the phase model."""
    b = _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)",
                  last_validation={"errors": 0, "scope": "structural_only"},
                  accept_structural_only=True)
    assert any("structural" in x.lower() for x in b), (
        f"Gate 3: accept_structural_only=True must NOT bypass "
        f"approval gate structural_only blocker. Got: {b}"
    )


def test_structural_only_still_blocks_when_errors_present():
    """Acknowledgement does NOT override real errors."""
    b = _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)",
                  last_validation={"errors": 1, "scope": "structural_only"},
                  accept_structural_only=True)
    assert any("Validation" in x for x in b)


def test_final_approval_gate_7_requires_signature():
    b = _blockers(7, ALL_DONE, signature="")
    assert b != []
    assert _blockers(7, ALL_DONE, signature="QA sign-off") == []


def test_approval_gates_constant():
    # Phase model: Human Review (3), Code Generation (4), Simulation (6), FAT/SAT (7).
    assert fw.APPROVAL_GATES == {3, 4, 6, 7}


# -- W-A1: signature must be a plausible audit value, not "x" --

def test_signature_single_character_rejected():
    b = _blockers(3, ALL_DONE, signature="x")
    assert any("signature" in x.lower() or "short" in x.lower() or "words" in x.lower() for x in b)


def test_signature_single_word_rejected():
    b = _blockers(3, ALL_DONE, signature="approved")
    assert any("signature" in x.lower() or "words" in x.lower() for x in b)


def test_signature_dot_rejected():
    b = _blockers(3, ALL_DONE, signature=".")
    assert b != []


def test_signature_numbers_only_rejected():
    b = _blockers(3, ALL_DONE, signature="123 456")
    assert any("letter" in x.lower() or "invalid" in x.lower() for x in b)


def test_signature_name_plus_role_accepted(tmp_path):
    assert _blockers(3, ALL_DONE, signature="Hans Becker (TÜV)") == []
    # Gate 4 (Code Generation) is an approval gate with no validate action.
    assert _blockers(4, ALL_DONE, signature="QA sign-off") == []
    # Gate 6 (Simulation) additionally requires compile log + manual-test declaration (B-P2).
    # S-4: log içeriği TIA Portal build göstergesi içermeli (sadece dosya varlığı yetmez).
    log = tmp_path / "compile.log"
    log.write_text("TIA Portal compile OK — 0 errors")
    assert _blockers(6, ALL_DONE, signature="M. Yilmaz, eng.",
                     compile_log_path=str(log), manual_test_confirmed=True) == []


# -- W-A2: RD05 (Safety) must be human-approved before any approval gate --

def test_rd05_draft_unverified_blocks_approval_gate_3():
    rd = dict(ALL_DONE)
    rd["RD05"] = "draft_unverified"
    b = _blockers(3, rd, signature="Hans Becker (TÜV)")
    assert any("RD05" in x for x in b)


def test_rd05_in_progress_blocks_approval_gate_4():
    # Gate 4 (Code Generation) is an approval gate; RD05 safety review applies.
    rd = dict(ALL_DONE)
    rd["RD05"] = "in_progress"
    b = _blockers(4, rd, signature="Hans Becker (TÜV)")
    assert any("RD05" in x for x in b)


def test_rd05_draft_unverified_does_not_block_non_approval_gate_2():
    # Extraction (gate 2) may legitimately leave RD05 at DRAFT_UNVERIFIED.
    rd = dict(ALL_DONE)
    rd["RD05"] = "draft_unverified"
    assert _blockers(2, rd) == []


def test_rd05_approved_passes_approval_gate_7():
    rd = dict(ALL_DONE)
    rd["RD05"] = "approved"  # synonymous with done
    assert _blockers(7, rd, signature="QA sign-off") == []


# -- Gate completion is RD-derived, not a trusted counter (#1 re-fix) --

_completed = fw._completed_gate_count
_effective_gate = fw._effective_gate

ALL_TEMPLATE = {f"RD{n:02d}": "template" for n in range(1, 15)}


def test_completed_count_zero_when_all_template():
    # Fresh project: every RD is a template -> no gate is complete.
    assert _completed(ALL_TEMPLATE) == 0


def test_completed_count_zero_when_rd_statuses_empty():
    # analyze_project failed / no data -> fail-safe to 0 (under-claim).
    assert _completed({}) == 0


def test_completed_count_counts_leading_done_gates():
    # Phase model: gate 1 = RD01,02,03,13; gate 2 = RD04-12,14; gates 3-7 own
    # no RDs. With only the gate-1 RDs done, gate 2 is still template -> stop at 1.
    rd = dict(ALL_TEMPLATE)
    for k in ("RD01", "RD02", "RD03", "RD13"):
        rd[k] = "done"
    assert _completed(rd) == 1


def test_completed_count_all_done_is_seven():
    assert _completed(ALL_DONE) == 7


def test_effective_gate_ignores_inflated_counter():
    # neue's bug: stored counter says 7 but no RD work done -> show gate 1.
    assert _effective_gate(7, ALL_TEMPLATE) == 1


def test_effective_gate_respects_conservative_stored_counter():
    # All RDs done (rd_current would be 7) but user only advanced (signed) to
    # gate 3 -> the lower stored counter wins, so approvals aren't bypassed.
    assert _effective_gate(3, ALL_DONE) == 3


def test_effective_gate_clamped_and_safe_on_garbage():
    assert _effective_gate(0, ALL_TEMPLATE) == 1
    assert _effective_gate(99, ALL_DONE) == 7
    assert _effective_gate(None, {}) == 1  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Gate 6 compile log içerik doğrulaması (S-4) — taşındı: test_compile_log_validation.py
# ---------------------------------------------------------------------------

_validate_compile_log = fw._validate_compile_log
_GATE6_SIG = "K. Mustafa (müh.)"


class TestValidateCompileLog:
    """_validate_compile_log(path) fonksiyonu birim testleri."""

    def test_nonexistent_file_returns_false(self, tmp_path):
        assert _validate_compile_log(str(tmp_path / "ghost.log")) is False

    def test_empty_file_returns_false(self, tmp_path):
        f = tmp_path / "empty.log"
        f.write_bytes(b"")
        assert _validate_compile_log(str(f)) is False, (
            "Boş dosya (0 byte) için False bekleniyor — boyut kontrolü eksik"
        )

    def test_file_without_keywords_returns_false(self, tmp_path):
        f = tmp_path / "random_notes.txt"
        f.write_text("Toplantı notları. Proje başlangıcı bekleniyor.", encoding="utf-8")
        assert _validate_compile_log(str(f)) is False, (
            "Anahtar kelime içermeyen dosya için False bekleniyor"
        )

    def test_tia_keyword_passes(self, tmp_path):
        f = tmp_path / "tia_log.txt"
        f.write_text("TIA Portal V19 — project loaded", encoding="utf-8")
        assert _validate_compile_log(str(f)) is True

    def test_compile_keyword_passes(self, tmp_path):
        f = tmp_path / "compile_out.log"
        f.write_text("Compilation finished with 0 errors, 2 warnings.", encoding="utf-8")
        assert _validate_compile_log(str(f)) is True

    def test_build_keyword_passes(self, tmp_path):
        f = tmp_path / "build.log"
        f.write_text("Build succeeded — 0 errors detected.", encoding="utf-8")
        assert _validate_compile_log(str(f)) is True

    def test_case_insensitive_matching(self, tmp_path):
        for content, label in [
            ("COMPILE SUCCEEDED", "COMPILE"),
            ("tia portal ready", "tia"),
            ("BUILD LOG OUTPUT", "BUILD"),
        ]:
            f = tmp_path / f"log_{label[:5]}.log"
            f.write_text(content, encoding="utf-8")
            assert _validate_compile_log(str(f)) is True, (
                f"{label} içeren dosya için True bekleniyor"
            )

    def test_directory_path_returns_false(self, tmp_path):
        assert _validate_compile_log(str(tmp_path)) is False

    def test_empty_string_returns_false(self):
        assert _validate_compile_log("") is False

    def test_none_like_string_returns_false(self):
        assert _validate_compile_log("None") is False


class TestGate6CompileLogBlockers:
    """Gate 6 blocker'larının içerik doğrulamasını entegre test eder."""

    def test_empty_file_blocks_gate6(self, tmp_path):
        empty_log = tmp_path / "empty_compile.log"
        empty_log.write_bytes(b"")
        b = _blockers(
            6, ALL_DONE, signature=_GATE6_SIG,
            compile_log_path=str(empty_log),
            manual_test_confirmed=True,
        )
        assert b, f"Boş compile log ile Gate 6 geçmemeli — blockers={b}"
        assert any(
            "tia portal build log" in x.lower()
            or "non-empty" in x.lower()
            or "does not appear" in x.lower()
            for x in b
        ), f"Blocker mesajı içerik sorununu açıklamalı; blockers={b}"

    def test_wrong_content_file_blocks_gate6(self, tmp_path):
        wrong_log = tmp_path / "readme.txt"
        wrong_log.write_text(
            "Bu bir okuma beni belgesidir. Hiçbir derleme çıktısı yoktur.",
            encoding="utf-8",
        )
        b = _blockers(
            6, ALL_DONE, signature=_GATE6_SIG,
            compile_log_path=str(wrong_log),
            manual_test_confirmed=True,
        )
        assert b, f"Yanlış içerikli dosya ile Gate 6 geçmemeli — blockers={b}"

    def test_valid_tia_log_does_not_block(self, tmp_path):
        valid_log = tmp_path / "tia_compile_output.log"
        valid_log.write_text(
            "TIA Portal V19 — Compile completed successfully\n"
            "Errors: 0  Warnings: 3\nBuild duration: 12.4 s",
            encoding="utf-8",
        )
        b = _blockers(
            6, ALL_DONE, signature=_GATE6_SIG,
            compile_log_path=str(valid_log),
            manual_test_confirmed=True,
        )
        assert b == [], f"Geçerli TIA log + beyan → blocker olmamalı; blockers={b}"

    def test_valid_build_log_does_not_block(self, tmp_path):
        build_log = tmp_path / "build_output.log"
        build_log.write_text(
            "Build report generated at 2026-06-14 08:00\nStatus: PASS",
            encoding="utf-8",
        )
        b = _blockers(
            6, ALL_DONE, signature=_GATE6_SIG,
            compile_log_path=str(build_log),
            manual_test_confirmed=True,
        )
        assert b == [], f"Build log + beyan → blocker olmamalı; blockers={b}"

    def test_nonexistent_file_still_blocks_gate6(self, tmp_path):
        b = _blockers(
            6, ALL_DONE, signature=_GATE6_SIG,
            compile_log_path=str(tmp_path / "does_not_exist.log"),
            manual_test_confirmed=True,
        )
        assert b, f"Var olmayan compile log → blocker bekleniyor; blockers={b}"

    def test_missing_path_still_blocks_gate6(self):
        b = _blockers(
            6, ALL_DONE, signature=_GATE6_SIG,
            compile_log_path="",
            manual_test_confirmed=True,
        )
        assert any(
            "compile_log" in x.lower() or "compile log" in x.lower()
            for x in b
        ), f"Boş yol → compile log blocker bekleniyor; blockers={b}"

    def test_gate6_content_check_does_not_affect_other_gates(self):
        for gate in (3, 4, 5, 7):
            b = _blockers(
                gate, ALL_DONE, signature=_GATE6_SIG,
                compile_log_path="",
                manual_test_confirmed=False,
            )
            content_blockers = [
                x for x in b
                if "tia portal build log" in x.lower()
                or "does not appear" in x.lower()
                or "non-empty" in x.lower()
            ]
            assert content_blockers == [], (
                f"Gate {gate} içerik doğrulama blocker'ı içermemeli; "
                f"content_blockers={content_blockers}"
            )


# ---------------------------------------------------------------------------
# Approval gate structural_only bypass kapatıldı (S-7) — taşındı: test_structural_only_gate_bypass.py
# ---------------------------------------------------------------------------

_APPROVAL_GATES = fw.APPROVAL_GATES
_S7_SIG = "Hans Becker (TÜV)"
_STRUCTURAL_ONLY_VALIDATION = {"errors": 0, "scope": "structural_only"}


class TestStructuralOnlyGateBypass:
    """S-7: accept_structural_only=True bayrağı approval gate'lerde bypass yapamaz."""

    def test_gate3_blocks_even_with_flag(self):
        b = _blockers(
            3, ALL_DONE, signature=_S7_SIG,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=True,
        )
        assert any("structural" in x.lower() for x in b), (
            f"S-7 HATA: Gate 3 (approval) structural_only blocker bypass edildi! blockers={b}"
        )

    def test_gate5_non_approval_allows_flag(self):
        # Phase model: gate 5 (Validation) is NON-approval, so the explicit
        # accept_structural_only acknowledgement legitimately clears the blocker.
        b = _blockers(
            5, ALL_DONE,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=True,
        )
        assert [x for x in b if "structural" in x.lower()] == [], (
            f"Gate 5 (non-approval): accept_structural_only=True should clear "
            f"the structural blocker. blockers={b}"
        )
        assert b == [], f"Gate 5 non-approval + flag → no blockers. blockers={b}"

    def test_gate7_no_validate_action_not_affected(self):
        b = _blockers(
            7, ALL_DONE, signature=_S7_SIG,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=True,
        )
        structural_blockers = [x for x in b if "structural" in x.lower()]
        assert structural_blockers == [], (
            f"Gate 7'de validate action yok; structural blocker beklenmiyordu: {b}"
        )

    def test_gate4_approval_no_validate_action_no_structural_blocker(self):
        # Phase model: gate 4 (Code Generation) is an approval gate but has NO
        # validate action, so structural_only validation never produces a
        # structural blocker there (signature alone gates it).
        b = _blockers(
            4, ALL_DONE, signature=_S7_SIG,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=False,
        )
        assert [x for x in b if "structural" in x.lower()] == [], (
            f"Gate 4 has no validate action; no structural blocker expected: {b}"
        )
        assert b == [], f"Gate 4 approval + valid signature → no blockers. blockers={b}"

    def test_gate3_blocks_without_flag(self):
        b = _blockers(
            3, ALL_DONE, signature=_S7_SIG,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=False,
        )
        assert any("structural" in x.lower() for x in b)

    def test_gate5_blocks_without_flag(self):
        b = _blockers(
            5, ALL_DONE, signature=_S7_SIG,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=False,
        )
        assert any("structural" in x.lower() for x in b)

    def test_gate7_structural_blocker_without_flag(self):
        """Gate 7 validate action yok; structural blocker üretilmez, imza var, blocker yok."""
        b = _blockers(
            7, ALL_DONE, signature=_S7_SIG,
            last_validation=_STRUCTURAL_ONLY_VALIDATION,
            accept_structural_only=False,
        )
        structural_blockers = [x for x in b if "structural" in x.lower()]
        assert structural_blockers == [], (
            f"Gate 7 validate action yok; structural blocker üretilmemeli: {b}"
        )

    def test_gate3_semantic_scope_no_structural_blocker(self):
        b = _blockers(
            3, ALL_DONE, signature=_S7_SIG,
            last_validation={"errors": 0, "scope": "semantic"},
            accept_structural_only=True,
        )
        assert [x for x in b if "structural" in x.lower()] == []
        assert b == [], f"Gate 3 semantic + clean → no blockers. blockers={b}"

    def test_gate5_compile_scope_no_structural_blocker(self):
        b = _blockers(
            5, ALL_DONE, signature=_S7_SIG,
            last_validation={"errors": 0, "scope": "compile"},
            accept_structural_only=False,
        )
        assert b == [], f"Gate 5 compile scope + clean → no blockers. blockers={b}"

    def test_gate3_errors_block_regardless_of_flag(self):
        b = _blockers(
            3, ALL_DONE, signature=_S7_SIG,
            last_validation={"errors": 3, "scope": "structural_only"},
            accept_structural_only=True,
        )
        assert any("Validation" in x for x in b), (
            f"Validation hataları her koşulda bloklamalı. blockers={b}"
        )
