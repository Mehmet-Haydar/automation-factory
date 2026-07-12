"""S-17 Proof Tests — Boş/Eksik RD05 → FAT Üretimi Bloklanır.

B-P5 domain kararı: RD05 (Güvenlik Gereksinim Dokümanı) boş veya eksikse
FAT protokol üretimi DURUR.  Jenerik güvenlik senaryolu FAT müşteriye gidemez.
Fail-closed: emin değilsen blokla.

Fix-revert contract:
- Bu testler fix VARKKEN geçmeli.
- check_rd05_ready() veya run_fat_protocol() içindeki blok kaldırılırsa
  testler KIRILMALI (smoke değil; koruyucu davranışı assert eder).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fat_protocol import (
    Rd05BlockedError,
    check_rd05_ready,
    run_fat_protocol,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_project(tmp_path: Path, *, with_metadata: bool = True) -> Path:
    proj = tmp_path / "test_proj"
    proj.mkdir()
    if with_metadata:
        (proj / "metadata").mkdir()
    return proj


def _write_rd05(proj: Path, content: str, name: str = "RD05_Safety_DRAFT_UNVERIFIED.md") -> Path:
    f = (proj / "metadata") / name
    f.write_text(content, encoding="utf-8")
    # AUDIT-004b: the DRAFT_UNVERIFIED banner/filename now blocks unless a
    # review is recorded. These tests target the CONTENT checks, so the
    # fixture records a review; the banner gate has its own tests
    # (test_rd05_code_gen_gate.py).
    import json as _json
    (proj / "PROJECT_STATE.json").write_text(_json.dumps({
        "rd_verifications": {"RD05": {"reviewed": True, "who": "T. Ester"}}}),
        encoding="utf-8")
    return f


# ===========================================================================
# Group A — check_rd05_ready: blok senaryoları
# ===========================================================================


class TestCheckRd05ReadyBlocks:
    """check_rd05_ready() Rd05BlockedError fırlatmalı — her eksik senaryoda."""

    def test_no_metadata_dir_raises(self, tmp_path):
        """metadata/ dizini yok → blokla."""
        proj = _make_project(tmp_path, with_metadata=False)
        with pytest.raises(Rd05BlockedError, match="metadata.*not found"):
            check_rd05_ready(proj)

    def test_no_rd05_file_raises(self, tmp_path):
        """metadata/ var ama RD05_Safety*.md yok → blokla."""
        proj = _make_project(tmp_path)
        with pytest.raises(Rd05BlockedError, match="no RD05_Safety"):
            check_rd05_ready(proj)

    def test_empty_file_raises(self, tmp_path):
        """RD05 dosyası 0 byte → blokla."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "")
        with pytest.raises(Rd05BlockedError, match="empty"):
            check_rd05_ready(proj)

    def test_only_heading_raises(self, tmp_path):
        """Sadece # başlık satırı → şablon, blokla."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "# RD05 Safety Requirements\n")
        with pytest.raises(Rd05BlockedError, match="substantive line"):
            check_rd05_ready(proj)

    def test_only_dividers_raises(self, tmp_path):
        """Sadece --- ve boş satırlar → şablon, blokla."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "---\n\n---\n")
        with pytest.raises(Rd05BlockedError, match="substantive line"):
            check_rd05_ready(proj)

    def test_only_todo_placeholder_raises(self, tmp_path):
        """TODO / PLACEHOLDER satırları → şablon, blokla."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "# RD05\nTODO: fill in safety requirements here\n")
        with pytest.raises(Rd05BlockedError, match="substantive line"):
            check_rd05_ready(proj)

    def test_only_blockquote_placeholder_raises(self, tmp_path):
        """> ile başlayan şablon satırı → şablon, blokla."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "> to be completed\n> fill in\n")
        with pytest.raises(Rd05BlockedError, match="substantive line"):
            check_rd05_ready(proj)

    def test_heading_plus_one_table_row_raises(self, tmp_path):
        """Başlık + tek tablo satırı → minimum 3 satır şartı karşılanmıyor."""
        proj = _make_project(tmp_path)
        # 1 anlamlı satır (tablo header), minimum 3 şart
        _write_rd05(proj, "# RD05\n| İşlev | Açıklama |\n")
        with pytest.raises(Rd05BlockedError, match="substantive line"):
            check_rd05_ready(proj)


# ===========================================================================
# Group B — check_rd05_ready: geçen senaryolar
# ===========================================================================


class TestCheckRd05ReadyPasses:
    """Dolu RD05 → check_rd05_ready() dosya yolunu döner, exception yok."""

    def test_filled_table_passes(self, tmp_path):
        """Tablo başlığı + veri satırları olan RD05 → geçer."""
        proj = _make_project(tmp_path)
        rd05 = _write_rd05(proj, (
            "# RD05 Safety Requirements\n"
            "| İşlev Adı | Açıklama | SIL |\n"
            "|---|---|---|\n"
            "| EStop_Main | Ana acil durdurma butonu | SIL 2 |\n"
            "| DoorInterlock | Kapı kilitleme fonksiyonu | SIL 1 |\n"
        ))
        result = check_rd05_ready(proj)
        assert result == rd05

    def test_prose_content_passes(self, tmp_path):
        """Düz metin gereksinimler (tablo olmasa da) → geçer."""
        proj = _make_project(tmp_path)
        rd05 = _write_rd05(proj, (
            "# RD05 Safety Requirements\n"
            "1. E-stop butonu kategori 0 durdurmayı tetikler.\n"
            "2. Koruyucu kapı açıldığında PLC güvenli duruma geçer.\n"
            "3. Güvenlik rölesi çift kanal izleme yapar.\n"
        ))
        result = check_rd05_ready(proj)
        assert result == rd05

    def test_alternate_filename_suffix_passes(self, tmp_path):
        """RD05_Safety_VERIFIED.md de kabul edilir."""
        proj = _make_project(tmp_path)
        rd05 = _write_rd05(proj, (
            "# RD05\n"
            "| Func | Desc | Cat |\n"
            "|---|---|---|\n"
            "| EStop | E-stop | Cat 0 |\n"
            "| Door | Door interlock | Cat 1 |\n"
        ), name="RD05_Safety_VERIFIED.md")
        result = check_rd05_ready(proj)
        assert result.name == "RD05_Safety_VERIFIED.md"

    def test_returns_path_object(self, tmp_path):
        """Dönüş tipi Path olmalı."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, (
            "E-stop: aktif\nKapı kilidi: aktif\nBaskı sensörü limiti: 10 bar\n"
        ))
        result = check_rd05_ready(proj)
        assert isinstance(result, Path)


# ===========================================================================
# Group C — run_fat_protocol: RD05 yokken BLOKLANIR
# ===========================================================================


class TestRunFatProtocolRd05Block:
    """run_fat_protocol() RD05 eksikken FAT dosyası YAZMAMALIYDI."""

    def test_no_rd05_raises_and_no_file_written(self, tmp_path):
        """RD05 yoksa Rd05BlockedError fırlatılır, _output/ oluşmaz."""
        proj = _make_project(tmp_path)  # metadata/ var ama RD05 yok
        out = tmp_path / "out"

        with pytest.raises(Rd05BlockedError):
            run_fat_protocol(proj, out)

        # Çıktı dizini oluşturulmamış olmalı (veya FAT dosyası yok)
        fat_files = list(out.glob("FAT_PROTOCOL_*.md")) if out.exists() else []
        assert fat_files == [], (
            f"FAT protocol was written despite missing RD05: {fat_files}. "
            "Fail-closed contract broken."
        )

    def test_empty_rd05_raises_and_no_file_written(self, tmp_path):
        """Boş RD05 → blok, dosya yazılmaz."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "")
        out = tmp_path / "out"

        with pytest.raises(Rd05BlockedError):
            run_fat_protocol(proj, out)

        fat_files = list(out.glob("FAT_PROTOCOL_*.md")) if out.exists() else []
        assert fat_files == [], "FAT written despite empty RD05"

    def test_template_rd05_raises_and_no_file_written(self, tmp_path):
        """Şablon/sadece başlık RD05 → blok, dosya yazılmaz."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "# RD05 Safety Requirements\n---\n")
        out = tmp_path / "out"

        with pytest.raises(Rd05BlockedError):
            run_fat_protocol(proj, out)

        fat_files = list(out.glob("FAT_PROTOCOL_*.md")) if out.exists() else []
        assert fat_files == [], "FAT written despite template-only RD05"

    def test_error_message_is_informative(self, tmp_path):
        """Hata mesajı kullanıcıya ne yapması gerektiğini söylemeli."""
        proj = _make_project(tmp_path)  # RD05 yok

        with pytest.raises(Rd05BlockedError) as exc_info:
            run_fat_protocol(proj, tmp_path / "out")

        msg = str(exc_info.value).lower()
        # Mesaj "rd05" ve "metadata" ya da yönlendirici bilgi içermeli
        assert "rd05" in msg, f"Error message does not mention RD05: {msg}"
        assert any(kw in msg for kw in ("metadata", "blocked", "fat protocol")), (
            f"Error message is not informative enough: {msg}"
        )


# ===========================================================================
# Group D — run_fat_protocol: dolu RD05'te üretim GEÇER
# ===========================================================================


class TestRunFatProtocolRd05Filled:
    """Dolu RD05 → run_fat_protocol() normal çalışır, FAT üretilir."""

    def test_filled_rd05_produces_protocol(self, tmp_path):
        """Yeterli içerikli RD05 varsa FAT protokolü üretilir."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, (
            "# RD05 Safety Requirements\n"
            "| İşlev Adı | Açıklama | SIL |\n"
            "|---|---|---|\n"
            "| EStop_Main | Ana acil durdurma | SIL 2 |\n"
            "| DoorLock | Kapı kilitleme | SIL 1 |\n"
        ))
        out = tmp_path / "out"
        result = run_fat_protocol(proj, out)

        assert result.ok, "FAT protocol should be produced when RD05 is filled"
        assert result.md_path is not None
        assert result.md_path.exists()

    def test_filled_rd05_fat_contains_safety_section(self, tmp_path):
        """Dolu RD05 → üretilen FAT güvenlik bölümü içerir."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, (
            "# RD05\n"
            "| Func | Desc |\n"
            "|---|---|\n"
            "| EStop | E-stop function |\n"
            "| Door | Door interlock |\n"
        ))
        # SAT v2 Faz 1: varsayılan dil DE oldu — bölüm başlığını dil-bilinçli
        # doğrula (EN üretiminde eski başlık hâlâ var).
        result = run_fat_protocol(proj, tmp_path / "out", lang="en")
        text = result.md_path.read_text(encoding="utf-8")
        assert "Safety Function Tests" in text

        result_de = run_fat_protocol(proj, tmp_path / "out_de")
        text_de = result_de.md_path.read_text(encoding="utf-8")
        assert "Sicherheitsfunktionstests" in text_de, (
            "default-language (DE) FAT must contain the DE safety section title"
        )


# ===========================================================================
# Group E — script_protocol_generator: RD05 blok
# ===========================================================================


class TestScriptProtocolGeneratorRd05Block:
    """script_protocol_generator.generate_protocol() da aynı bloku uygulamalı."""

    def test_missing_rd05_raises(self, tmp_path):
        """generate_protocol() RD05 eksikken Rd05BlockedError fırlatmalı."""
        proj = _make_project(tmp_path)  # RD05 yok
        from script_protocol_generator import generate_protocol
        with pytest.raises(Rd05BlockedError):
            generate_protocol(proj)

    def test_empty_rd05_raises(self, tmp_path):
        """Boş RD05 → generate_protocol() bloklamalı."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, "")
        from script_protocol_generator import generate_protocol
        with pytest.raises(Rd05BlockedError):
            generate_protocol(proj)

    def test_filled_rd05_passes(self, tmp_path):
        """Dolu RD05 → generate_protocol() çalışır, ProtocolResult döner."""
        proj = _make_project(tmp_path)
        _write_rd05(proj, (
            "# RD05\n"
            "| Func | Desc |\n"
            "|---|---|\n"
            "| EStop | Emergency stop |\n"
            "| Door | Door interlock |\n"
        ))
        from script_protocol_generator import generate_protocol
        result = generate_protocol(proj)
        assert result is not None
        assert result.project_name == proj.name
