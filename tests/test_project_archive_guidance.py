"""Proof tests — project archives (.s7p/.zap*/.ap*/.zip) in _raw/legacy_code/.

Field-audit finding B-01/B-05: `.s7p` was listed as an accepted legacy format
but silently skipped as "binary" with a misleading STEP5 message, and `.zap25`
files were completely invisible (extension not in the static list — no listing,
no warning). A DACH retrofit almost always arrives as an .s7p / .zap archive,
so this dead-end must be loud and actionable.

Proof criteria:
1. `_project_archive_kind()` classifies every archive family; text sources
   stay None.
2. `get_raw_folder_status()` LISTS archive files (visibility — engineer sees
   what they dropped).
3. `_ARCHIVE_GUIDANCE` has a format-specific, actionable export instruction
   for every kind returned by `_project_archive_kind()` — and the .s7p text
   never mentions STEP5 (the old misleading message).
4. platform_detector: archives get a "not read" note and that note does NOT
   double their platform vote (weight boost is content-confirmation only).
"""
from __future__ import annotations

from pathlib import Path

import factory_web as fw
import platform_detector as pd


# ---------------------------------------------------------------------------
# 1. Classification
# ---------------------------------------------------------------------------

def test_archive_kind_families():
    k = fw.Api._project_archive_kind
    assert k(Path("Machine.s7p")) == "s7p"
    assert k(Path("Project.ZAP25")) == "zap"   # case-insensitive
    assert k(Path("Project.zap14")) == "zap"
    assert k(Path("Anlage.ap19")) == "ap"
    assert k(Path("export.zip")) == "zip"


def test_archive_kind_ignores_text_sources():
    k = fw.Api._project_archive_kind
    for name in ("OB1.awl", "FB10.scl", "prog.stl", "tags.seq",
                 "prog.s5d", "listing.txt", "doc.pdf", "app.apk"):
        assert k(Path(name)) is None, f"{name} yanlışlıkla arşiv sayıldı"


# ---------------------------------------------------------------------------
# 2. Visibility in get_raw_folder_status
# ---------------------------------------------------------------------------

def test_raw_folder_status_lists_archives(tmp_path):
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    # ZIP header bytes — would fail the old suffix-list check entirely
    (legacy / "Project.zap25").write_bytes(b"PK\x03\x04" + b"\x00" * 64)
    (legacy / "Machine.s7p").write_bytes(b"\x00\x01\x02" * 100)
    (legacy / "OB1.awl").write_text("CALL FB 10", encoding="utf-8")

    api = fw.Api()
    api.root = tmp_path
    status = api.get_raw_folder_status()

    names = status["by_category"]["legacy_code"]
    assert "Project.zap25" in names, (
        ".zap25 dosyası raw-folder listesinde görünmüyor — mühendis için "
        "görünmez (B-01 regresyonu)."
    )
    assert "Machine.s7p" in names
    assert "OB1.awl" in names


# ---------------------------------------------------------------------------
# 3. Guidance completeness + no misleading STEP5 text
# ---------------------------------------------------------------------------

def test_guidance_covers_every_kind():
    kinds = {
        fw.Api._project_archive_kind(Path(n))
        for n in ("a.s7p", "a.zap25", "a.ap19", "a.zip")
    }
    for kind in kinds:
        assert kind in fw.Api._ARCHIVE_GUIDANCE, f"'{kind}' için rehber metni yok"
        text = fw.Api._ARCHIVE_GUIDANCE[kind]
        # Actionable: must tell the engineer to export/unpack sources
        assert any(w in text.lower() for w in ("export", "generate", "unpack",
                                               "retrieve")), (
            f"'{kind}' rehberi eyleme dönük değil: {text}"
        )


def test_s7p_guidance_is_not_step5_message():
    text = fw.Api._ARCHIVE_GUIDANCE["s7p"]
    assert "STEP5" not in text and "S5/S7 for Windows" not in text, (
        ".s7p için hâlâ yanıltıcı STEP5 mesajı gösteriliyor (B-05 regresyonu)."
    )
    assert "SIMATIC Manager" in text


# ---------------------------------------------------------------------------
# 4. platform_detector — archive note + honest vote weight
# ---------------------------------------------------------------------------

def test_platform_detector_archive_note_and_vote(tmp_path):
    inp = tmp_path / "_input"
    inp.mkdir()
    (inp / "Machine.s7p").write_bytes(b"\x00\x01" * 200)

    scan = pd.scan_input_folder(inp)
    fi = next(f for f in scan.files if f.extension == ".s7p")
    assert "NOT read" in fi.notes, (
        "Arşiv dosyasına 'content NOT read' notu düşülmüyor — tarama raporu "
        "arşivin okunduğu izlenimini veriyor."
    )
    # .s7p votes for S7_300 + S7_400 with weight 1 (not 2 — no content proof)
    assert scan.detected_platforms.get("S7_300") == 1
    assert scan.detected_platforms.get("S7_400") == 1
