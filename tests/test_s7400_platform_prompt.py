"""S-21 (B-L6/L7/L14) — dedicated S7-400 analyze prompt + platform wiring.

Domain decision: the S7-400 platform
gets its own platform-parser prompt instead of piggybacking on the S7-300
one. Beckhoff/Schneider were explicitly deferred — their CODESYS fallback
mapping must stay untouched.

Covers:
* the prompt file exists and carries platform_parser frontmatter,
* platform_detector routes S7_400 to the new prompt (S7_300 unchanged),
* factory_reader's PLATFORM_PROMPTS routes S7_400 to the new prompt,
* content detection recognises CPU 41x / S7-400(H) fingerprints,
* an S7-400 source folder scan recommends the new prompt end-to-end.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = (PROJECT_ROOT / "04_AI_PROMPTS" / "analyze"
               / "PROMPT_ANALYZE_S7_400_STL.md")


class TestPromptFile:
    def test_prompt_file_exists(self):
        assert PROMPT_PATH.is_file(), PROMPT_PATH

    def test_frontmatter_declares_platform_parser(self):
        text = PROMPT_PATH.read_text(encoding="utf-8")
        head = text.split("---", 2)[1]  # frontmatter block
        assert "role: platform_parser" in head
        assert "schema: PROMPT_ANALYZE" in head
        assert "S7-400" in head

    def test_covers_s7_400_specifics(self):
        """The prompt must address real S7-400 differences, not be a copy."""
        text = PROMPT_PATH.read_text(encoding="utf-8")
        for marker in ("S7-400H", "OB86", "CFC", "PCS7", "multicomputing",
                       "DP master"):
            assert marker.lower() in text.lower(), f"missing: {marker}"


class TestPlatformDetectorMapping:
    def test_s7_400_maps_to_new_prompt(self):
        from platform_detector import PLATFORM_TO_PROMPT
        assert PLATFORM_TO_PROMPT["S7_400"] == \
            "analyze/PROMPT_ANALYZE_S7_400_STL.md"

    def test_s7_300_mapping_unchanged(self):
        from platform_detector import PLATFORM_TO_PROMPT
        assert PLATFORM_TO_PROMPT["S7_300"] == \
            "analyze/PROMPT_ANALYZE_S7_300_STL.md"

    def test_get_recommended_prompt(self):
        from platform_detector import get_recommended_prompt
        assert get_recommended_prompt("S7_400") == \
            "analyze/PROMPT_ANALYZE_S7_400_STL.md"

    def test_mapped_prompt_file_exists(self):
        """Mapping must never point at a non-existent prompt file."""
        from platform_detector import PLATFORM_TO_PROMPT
        for plat, rel in PLATFORM_TO_PROMPT.items():
            path = PROJECT_ROOT / "04_AI_PROMPTS" / rel
            assert path.is_file(), f"{plat} -> {rel} missing"

    def test_deferred_platforms_untouched(self):
        """Beckhoff/Schneider were deferred — they keep the CODESYS parser."""
        from platform_detector import PLATFORM_TO_PROMPT
        assert PLATFORM_TO_PROMPT["BECKHOFF"] == \
            "analyze/PROMPT_ANALYZE_CODESYS.md"
        assert PLATFORM_TO_PROMPT["SCHNEIDER"] == \
            "analyze/PROMPT_ANALYZE_CODESYS.md"


class TestFactoryReaderMapping:
    def test_s7_400_maps_to_new_prompt(self):
        from workbench.core.factory_reader import PLATFORM_PROMPTS
        assert PLATFORM_PROMPTS["S7_400"] == "PROMPT_ANALYZE_S7_400_STL"

    def test_s7_300_mapping_unchanged(self):
        from workbench.core.factory_reader import PLATFORM_PROMPTS
        assert PLATFORM_PROMPTS["S7_300"] == "PROMPT_ANALYZE_S7_300_STL"


class TestContentDetection:
    def test_cpu_41x_pattern_detected(self, tmp_path):
        from platform_detector import detect_platform_from_content
        src = tmp_path / "hw.awl"
        src.write_text("// HW: CPU 416-3 PN/DP, rack UR2\nCALL FB 10\n",
                       encoding="utf-8")
        assert "S7_400" in detect_platform_from_content(src)

    def test_h_system_pattern_detected(self, tmp_path):
        from platform_detector import detect_platform_from_content
        src = tmp_path / "hw.awl"
        src.write_text("// Redundant pair, SIMATIC S7-400H\n",
                       encoding="utf-8")
        assert "S7_400" in detect_platform_from_content(src)

    def test_s7_300_not_misdetected_as_400(self, tmp_path):
        from platform_detector import detect_platform_from_content
        src = tmp_path / "prog.awl"
        src.write_text("// SIMATIC S7-300, CPU 315-2 DP\nCALL FB 1\n",
                       encoding="utf-8")
        assert "S7_400" not in detect_platform_from_content(src)


class TestEndToEndScan:
    def test_s7_400_folder_recommends_new_prompt(self, tmp_path):
        from platform_detector import (scan_input_folder,
                                       get_recommended_prompt)
        inp = tmp_path / "_input"
        inp.mkdir()
        # .awl extension votes for S5/S7_300/S7_400 alike; the .txt HW
        # listing has no extension mapping, so its content match votes for
        # S7_400 ALONE and breaks the tie deterministically.
        (inp / "OB1.AWL").write_text(
            "// Project X — SIMATIC S7-400, CPU 416-2\n"
            "U E 516.0\n= A 4.0\n", encoding="utf-8")
        (inp / "HWConfig.txt").write_text(
            "Station: SIMATIC S7-400\nRack UR2, CPU 416-3 PN/DP, 6ES7 416-3ES07-0AB0\n",
            encoding="utf-8")
        scan = scan_input_folder(inp)
        assert "S7_400" in scan.detected_platforms, scan.detected_platforms
        assert scan.primary_platform == "S7_400", scan.detected_platforms
        assert get_recommended_prompt(scan.primary_platform) == \
            "analyze/PROMPT_ANALYZE_S7_400_STL.md"
