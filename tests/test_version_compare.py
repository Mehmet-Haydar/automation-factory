"""version_compare.py — deterministic version-diff engine.

Covers both real-world .SEQ dialects (\\x1a+\\x00 records and TAB-separated
lines), the symbol-level diff, folder scanning with guard rails, the
multi-version status matrix and the AI summary (which must never carry
binary content).
"""

from __future__ import annotations

import pytest

import version_compare as vc

# \x1a + \x00 dialect (same sample as test_legacy_pdf_extract)
SEQ_SAMPLE = (
    b"\x1aE    4.0\x00E 4.0\x00KE HYDR.MOTOR NETZSCHUETZ\r\n"
    b"\x1aE    4.1\x00E 4.1\x00KE HYDR.MOTOR DREIECKS.\r\n"
    b"\x1aE    4.2\x00E 4.2\x00KE HYDR.MOTOR STERNSCHUETZ\r\n"
) * 20

# TAB dialect — exact shape of the real 104711Z0.SEQ archive file
SEQ_TAB = (
    b"\tE    4.0\tE 4.0\tKE HYDR.MOTOR NETZSCHUETZ\r\n"
    b"\tT   40\tT 40\tNachlaufzeit Rotation\r\n"
    b"\tF  108.3\tF 108.3\tSCHUTZT\x9aR AUF\r\n"   # 0x9A = Ü in cp437
)


class TestParseSeq:
    def test_ctrl_dialect(self):
        syms, errors = vc.parse_seq(SEQ_SAMPLE)
        assert errors == 0
        assert syms["E 4.0"] == "KE HYDR.MOTOR NETZSCHUETZ"
        assert syms["E 4.2"] == "KE HYDR.MOTOR STERNSCHUETZ"
        assert len(syms) == 3  # *20 repeats collapse onto the same operands

    def test_tab_dialect_and_umlaut(self):
        syms, errors = vc.parse_seq(SEQ_TAB)
        assert errors == 0
        assert syms["T 40"] == "Nachlaufzeit Rotation"
        assert syms["F 108.3"] == "SCHUTZTÜR AUF", "cp437 umlauts must survive"

    def test_eof_padding_is_not_an_error(self):
        # real ZF.SEQ files end in \x1a + dozens of \x00 padding bytes
        syms, errors = vc.parse_seq(SEQ_TAB + b"\x1a" + b"\x00" * 60)
        assert errors == 0
        assert len(syms) == 3

    def test_non_symbol_text_yields_zero_symbols(self):
        # translation logs / arbitrary text → 0 symbols, counted as errors,
        # so diff_file can fall back to text mode
        syms, errors = vc.parse_seq(b"Uebersetzung Zuord.liste D:\\X\\Y.SEQ\r\n"
                                    b"*** 654 Zeilen bearbeitet ***\r\n")
        assert syms == {}
        assert errors > 0


class TestDiffSeq:
    def test_all_four_states(self):
        old = (b"\tE    1.0\tE 1.0\tMOTOR EIN\r\n"
               b"\tE    1.1\tE 1.1\tALT WIRD ENTFERNT\r\n"
               b"\tE    1.2\tE 1.2\tBLEIBT GLEICH\r\n")
        new = (b"\tE    1.0\tE 1.0\tMOTOR AUS\r\n"
               b"\tE    1.2\tE 1.2\tBLEIBT GLEICH\r\n"
               b"\tE    1.3\tE 1.3\tNEU DAZU\r\n")
        d = vc.diff_seq(old, new)
        assert d["added"] == [{"operand": "E 1.3", "desc": "NEU DAZU"}]
        assert d["removed"] == [{"operand": "E 1.1", "desc": "ALT WIRD ENTFERNT"}]
        assert d["changed"] == [{"operand": "E 1.0",
                                 "old_desc": "MOTOR EIN",
                                 "new_desc": "MOTOR AUS"}]
        assert d["unchanged"] == 1
        assert d["parse_errors_old"] == 0
        assert d["parse_errors_new"] == 0


class TestDiffText:
    def test_unified_diff_and_truncation(self):
        old = b"line A\r\nline B\r\n"
        new = b"line A\r\nline C\r\n"
        d = vc.diff_text(old, new)
        assert not d["truncated"]
        assert any(ln.startswith("-line B") for ln in d["lines"])
        assert any(ln.startswith("+line C") for ln in d["lines"])

    def test_truncation_flag(self, monkeypatch):
        monkeypatch.setattr(vc, "MAX_DIFF_LINES", 10)
        old = b"\r\n".join(b"x%d" % i for i in range(200))
        new = b"\r\n".join(b"y%d" % i for i in range(200))
        d = vc.diff_text(old, new)
        assert d["truncated"]
        assert d["lines"][-1] == "… diff truncated …"
        assert len(d["lines"]) == 11


class TestDiffFile:
    def test_seq_skips_binary_heuristic(self, tmp_path):
        # \x00 bytes would trip _looks_binary — .seq must parse instead
        a = tmp_path / "a.SEQ"; a.write_bytes(SEQ_SAMPLE)
        b = tmp_path / "b.SEQ"; b.write_bytes(SEQ_SAMPLE)
        d = vc.diff_file(str(a), str(b), "a.SEQ")
        assert d["ok"] and d["mode"] == "seq"
        assert d["unchanged"] == 3

    def test_seq_with_zero_records_falls_back(self, tmp_path):
        a = tmp_path / "zf.seq"; a.write_bytes(b"Uebersetzung log\r\n")
        b = tmp_path / "zf2.seq"; b.write_bytes(b"Uebersetzung log 2\r\n")
        d = vc.diff_file(str(a), str(b), "zf.seq")
        assert d["ok"] and d["mode"] == "text"

    def test_s5d_binary_note(self, tmp_path):
        a = tmp_path / "a.s5d"; a.write_bytes(bytes(range(256)) * 4)
        b = tmp_path / "b.s5d"; b.write_bytes(bytes(range(256)) * 4)
        d = vc.diff_file(str(a), str(b), "a.s5d")
        assert d["ok"] and d["mode"] == "binary"
        assert "AWL" in d["msg"], "must tell the engineer how to compare logic"
        assert d["identical"] is True

    def test_generic_binary(self, tmp_path):
        a = tmp_path / "a.ini"; a.write_bytes(bytes(range(256)) * 4)
        b = tmp_path / "b.ini"; b.write_bytes(bytes(range(255, -1, -1)) * 4)
        d = vc.diff_file(str(a), str(b), "a.ini")
        assert d["ok"] and d["mode"] == "binary"
        assert d["identical"] is False

    def test_too_large(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vc, "MAX_DIFF_BYTES", 10)
        a = tmp_path / "a.txt"; a.write_bytes(b"x" * 100)
        b = tmp_path / "b.txt"; b.write_bytes(b"y" * 100)
        d = vc.diff_file(str(a), str(b), "a.txt")
        assert d["ok"] and d["mode"] == "too_large"

    def test_added_and_removed_only(self, tmp_path):
        a = tmp_path / "a.txt"; a.write_bytes(b"x")
        assert vc.diff_file(None, str(a), "a.txt")["mode"] == "added_only"
        assert vc.diff_file(str(a), None, "a.txt")["mode"] == "removed_only"
        assert not vc.diff_file(None, None, "a.txt")["ok"]

    def test_never_raises_on_unreadable(self, tmp_path):
        d = vc.diff_file(str(tmp_path / "no.txt"), str(tmp_path / "no2.txt"), "no.txt")
        assert d["ok"] is False
        assert "no.txt" in d["msg"]


class TestScanVersionDir:
    def test_missing_folder(self, tmp_path):
        r = vc.scan_version_dir(str(tmp_path / "nope"))
        assert r["ok"] is False

    def test_casefold_keys_and_metadata(self, tmp_path):
        (tmp_path / "104711Z0.SEQ").write_bytes(SEQ_TAB)
        r = vc.scan_version_dir(str(tmp_path))
        assert r["ok"]
        entry = r["files"]["104711z0.seq"]
        assert entry["name"] == "104711Z0.SEQ"
        assert entry["size"] == len(SEQ_TAB)
        assert len(entry["sha256"]) == 64

    def test_depth_and_file_limits(self, tmp_path, monkeypatch):
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "too_deep.txt").write_text("x")
        (tmp_path / "ok.txt").write_text("x")
        r = vc.scan_version_dir(str(tmp_path))
        assert "ok.txt" in r["files"]
        assert not any("too_deep" in k for k in r["files"])

        monkeypatch.setattr(vc, "MAX_SCAN_FILES", 2)
        for i in range(4):
            (tmp_path / f"f{i}.txt").write_text("x")
        r = vc.scan_version_dir(str(tmp_path))
        assert r["truncated"] is True
        assert len(r["files"]) == 2


class TestCompareVersions:
    def _mk(self, root, name, files):
        d = root / name
        d.mkdir()
        for fname, content in files.items():
            (d / fname).write_bytes(content)
        return str(d)

    def test_requires_two_folders(self, tmp_path):
        assert not vc.compare_versions([])["ok"]
        assert not vc.compare_versions([str(tmp_path)])["ok"]

    def test_missing_folder_propagates(self, tmp_path):
        r = vc.compare_versions([str(tmp_path), str(tmp_path / "nope")])
        assert r["ok"] is False

    def test_three_versions_statuses(self, tmp_path):
        v1 = self._mk(tmp_path, "2018-08-18", {
            "same.txt": b"s", "mod.txt": b"v1", "gone.txt": b"g",
            "hole.txt": b"h"})
        v2 = self._mk(tmp_path, "2018-10-26", {
            "same.txt": b"s", "mod.txt": b"v2"})
        v3 = self._mk(tmp_path, "_aktiv", {
            "same.txt": b"s", "mod.txt": b"v3", "new.txt": b"n",
            "hole.txt": b"h"})
        r = vc.compare_versions([v1, v2, v3])
        assert r["ok"]
        by = {f["key"]: f["status"] for f in r["files"]}
        assert by["same.txt"] == "unchanged"
        assert by["mod.txt"] == "modified"
        assert by["gone.txt"] == "removed"
        assert by["new.txt"] == "added"
        assert by["hole.txt"] == "mixed", "present-absent-present is not a clean add"
        assert r["summary"]["total"] == 5
        assert [v["name"] for v in r["versions"]] == [
            "2018-08-18", "2018-10-26", "_aktiv"]

    def test_dos_case_variants_line_up(self, tmp_path):
        v1 = self._mk(tmp_path, "v1", {"104711Z0.SEQ": SEQ_TAB})
        v2 = self._mk(tmp_path, "v2", {"104711z0.seq": SEQ_TAB})
        r = vc.compare_versions([v1, v2])
        assert r["summary"]["total"] == 1
        assert r["files"][0]["status"] == "unchanged"

    def test_duplicate_folder_names_stay_distinct(self, tmp_path):
        a = tmp_path / "x" / "_aktiv"; a.mkdir(parents=True)
        b = tmp_path / "y" / "_aktiv"; b.mkdir(parents=True)
        (a / "f.txt").write_bytes(b"1")
        (b / "f.txt").write_bytes(b"2")
        r = vc.compare_versions([str(a), str(b)])
        names = [v["name"] for v in r["versions"]]
        assert len(set(names)) == 2


class TestSummarizeForAI:
    def test_text_only_and_truncation(self, tmp_path):
        v1 = tmp_path / "v1"; v1.mkdir()
        v2 = tmp_path / "v2"; v2.mkdir()
        binary_payload = bytes(range(256)) * 4
        (v1 / "prog.s5d").write_bytes(binary_payload)
        (v2 / "prog.s5d").write_bytes(binary_payload[::-1])
        (v1 / "syms.seq").write_bytes(SEQ_TAB)
        (v2 / "syms.seq").write_bytes(SEQ_TAB.replace(b"Rotation", b"Translat."))
        r = vc.compare_versions([str(v1), str(v2)])
        diffs = [
            vc.diff_file(str(v1 / "prog.s5d"), str(v2 / "prog.s5d"), "prog.s5d"),
            vc.diff_file(str(v1 / "syms.seq"), str(v2 / "syms.seq"), "syms.seq"),
        ]
        text = vc.summarize_for_ai(r, diffs)
        assert "prog.s5d" in text and "[binary]" in text
        assert "\x00" not in text and "\x1a" not in text, "no binary bytes ever"
        assert "Rotation" in text and "Translat." in text, "seq diff content present"

        short = vc.summarize_for_ai(r, diffs, max_chars=80)
        assert len(short) <= 80 + len("\n… summary truncated …")
        assert short.endswith("… summary truncated …")
