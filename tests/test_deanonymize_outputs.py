"""S-6 (B-L2) — AI outputs must be deanonymized at the persistence boundary.

The forward chain existed (build_anon_map + anonymize_text before sending
legacy text to the AI), but ``deanonymize_text`` had ZERO production call
sites: RD drafts and REPORTS/ copies kept placeholders like CUSTOMER_A —
documents that go in front of the customer.

Design constraint proven here: the restore happens ONLY on persisted copies;
the inter-step chain ({out_N} prompt material) stays anonymized, otherwise a
later step would carry the real customer name back to the cloud provider.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch


ANON_MAP = {"Müller GmbH": "CUSTOMER_A", "Beispielmaschine_X": "PROJECT_001"}


def _deanon(text):
    from anonymizer import deanonymize_text
    return deanonymize_text(text, ANON_MAP)


def _make_runner(tmp_path, postprocess):
    from workbench.core.ai_runner import AutoFlowRunner
    return AutoFlowRunner(
        provider="anthropic",
        model="test-model",
        api_key="sk-test",
        project_root=tmp_path,
        on_step_start=MagicMock(),
        on_step_chunk=MagicMock(),
        on_step_done=MagicMock(),
        on_flow_done=MagicMock(),
        on_error=MagicMock(),
        on_warn=MagicMock(),
        output_postprocess=postprocess,
    )


def _run(tmp_path, runner, client):
    source = tmp_path / "input.awl"
    source.write_text("(*test*)", encoding="utf-8")
    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
         patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "ok")), \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient", return_value=client):
        runner._run("Analyze → Validate", source)


class TestPersistedCopiesRestored:
    def _client(self):
        usage = MagicMock()
        usage.truncated = False
        client = MagicMock()
        client.chat.return_value = ("Report for CUSTOMER_A (PROJECT_001).", usage)
        return client

    def test_reports_copy_is_deanonymized(self, tmp_path):
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8")
        runner = _make_runner(tmp_path, _deanon)
        _run(tmp_path, runner, self._client())
        md_files = list((tmp_path / "REPORTS").rglob("*.md"))
        assert md_files
        content = md_files[0].read_text(encoding="utf-8")
        assert "Müller GmbH" in content, "REPORTS kopyasında gerçek ad geri gelmeli"
        assert "CUSTOMER_A" not in content, (
            "yer tutucu müşteri belgesine sızdı — B-L2 geri geldi")

    def test_without_postprocess_behavior_unchanged(self, tmp_path):
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8")
        runner = _make_runner(tmp_path, None)
        _run(tmp_path, runner, self._client())
        md_files = list((tmp_path / "REPORTS").rglob("*.md"))
        assert md_files
        assert "CUSTOMER_A" in md_files[0].read_text(encoding="utf-8")

    def test_postprocess_failure_is_not_fatal(self, tmp_path):
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8")

        def _boom(_t):
            raise RuntimeError("postprocess crashed")

        runner = _make_runner(tmp_path, _boom)
        _run(tmp_path, runner, self._client())
        md_files = list((tmp_path / "REPORTS").rglob("*.md"))
        assert md_files, "postprocess hatası yazımı öldürmemeli (ham kopya kalır)"


class TestChainStaysAnonymized:
    def test_inter_step_chain_not_deanonymized(self, tmp_path):
        # Two-step workflow: the second step's prompt is built from the first
        # step's output — it must still contain the PLACEHOLDER, never the
        # restored customer name (that would re-leak it to the provider).
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8")
        usage = MagicMock()
        usage.truncated = False
        prompts_seen = []

        def _chat(system, user, **kw):
            prompts_seen.append(user)
            return ("Output mentioning CUSTOMER_A.", usage)

        client = MagicMock()
        client.chat.side_effect = _chat
        runner = _make_runner(tmp_path, _deanon)
        _run(tmp_path, runner, client)
        assert len(prompts_seen) >= 2, "iki adımlı workflow bekleniyordu"
        for p in prompts_seen[1:]:
            assert "Müller GmbH" not in p, (
                "deanonymize zincire sızdı — sonraki prompt gerçek adı AI'ya taşıyor!")

    def test_runner_source_postprocess_only_at_persistence(self):
        # Meta-guard: output_postprocess must not touch step_outputs_raw.
        from workbench.core import ai_runner
        src = inspect.getsource(ai_runner.AutoFlowRunner._run)
        assert "step_outputs_raw[i + 1] = prev_output" in src, (
            "zincir değişkeni artık ham çıktı değil — S-6 tasarım kısıtı bozuldu")


class TestFactoryWebWiring:
    def test_preanalysis_wires_deanonymize(self):
        fw = importlib.import_module("factory_web")
        src = inspect.getsource(fw.Api.run_retrofit_preanalysis)
        assert "output_postprocess" in src and "deanonymize_text" in src, (
            "pre-analysis runner'ı deanonymize hook'u olmadan kuruluyor")

    def test_deanonymize_has_production_callsite(self):
        # The original finding: zero production call sites.
        fw_src = inspect.getsource(importlib.import_module("factory_web"))
        assert fw_src.count("deanonymize_text") >= 2, (
            "deanonymize_text üretimde yine çağrısız kaldı (import + kullanım beklenir)")
