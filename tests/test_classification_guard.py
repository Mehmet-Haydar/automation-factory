"""C4 — AI data classification gate."""

from data_classification_guard import (
    provider_allowed,
    normalize_classification,
    read_project_classification,
    check_ai_send,
    AIGateResult,
)


def test_confidential_public_provider_soft_block():
    result = provider_allowed("CONFIDENTIAL", "anthropic", {})
    assert isinstance(result, AIGateResult)
    assert result.allowed is False
    assert result.requires_consent is True
    assert "CONFIDENTIAL" in result.reason


def test_confidential_enterprise_override_allowed():
    settings = {"ai_provider_tier": {"anthropic": "enterprise"}}
    result = provider_allowed("CONFIDENTIAL", "anthropic", settings)
    assert result.allowed is True
    assert result.requires_consent is False


def test_confidential_self_hosted_allowed():
    result = provider_allowed("CONFIDENTIAL", "openai", {"self_hosted": True})
    assert result.allowed is True
    assert result.requires_consent is False


def test_public_allowed_anywhere():
    result = provider_allowed("PUBLIC", "openai", {})
    assert result.allowed is True
    assert result.requires_consent is False


def test_internal_allowed():
    result = provider_allowed("INTERNAL", "deepseek", {})
    assert result.allowed is True
    assert result.requires_consent is False


def test_restricted_blocked_even_enterprise():
    settings = {"self_hosted": True}
    result = provider_allowed("RESTRICTED", "anthropic", settings)
    assert result.allowed is False
    assert result.requires_consent is False
    assert "RESTRICTED" in result.reason


def test_unknown_classification_is_confidential():
    assert normalize_classification("weird") == "CONFIDENTIAL"
    assert normalize_classification(None) == "CONFIDENTIAL"
    assert normalize_classification("public") == "PUBLIC"


def test_unknown_provider_failclosed_for_confidential():
    result = provider_allowed("CONFIDENTIAL", "some_local_thing", {})
    assert result.allowed is False
    assert result.requires_consent is False


def test_read_classification_from_maestro(tmp_path):
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\nproject_name: X\ndata_classification: CONFIDENTIAL\n---\n# X\n",
        encoding="utf-8",
    )
    assert read_project_classification(tmp_path) == "CONFIDENTIAL"


def test_read_classification_state_overrides(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "PUBLIC"}', encoding="utf-8"
    )
    assert read_project_classification(tmp_path) == "PUBLIC"


def test_missing_project_is_confidential(tmp_path):
    assert read_project_classification(tmp_path) == "CONFIDENTIAL"
    assert read_project_classification(None) == "CONFIDENTIAL"


def test_check_ai_send_soft_blocks_confidential(tmp_path):
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: CONFIDENTIAL\n---\n", encoding="utf-8"
    )
    result = check_ai_send(tmp_path, "anthropic", {})
    assert result.allowed is False
    assert result.requires_consent is True


def test_check_ai_send_consent_confirmed_allows(tmp_path):
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: CONFIDENTIAL\n---\n", encoding="utf-8"
    )
    result = check_ai_send(tmp_path, "anthropic", {}, consent_confirmed=True)
    assert result.allowed is True
    assert result.requires_consent is False


def test_check_ai_send_restricted_consent_has_no_effect(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "RESTRICTED"}', encoding="utf-8"
    )
    result = check_ai_send(tmp_path, "anthropic", {}, consent_confirmed=True)
    assert result.allowed is False
    assert result.requires_consent is False


def test_backward_compat_unpack(tmp_path):
    """AIGateResult is a NamedTuple — old 2-tuple unpack still works."""
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "PUBLIC"}', encoding="utf-8"
    )
    allowed, reason = check_ai_send(tmp_path, "anthropic", {})
    assert allowed is True
    assert isinstance(reason, str)
