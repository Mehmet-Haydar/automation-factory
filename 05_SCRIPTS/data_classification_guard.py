"""Data-classification gate for AI calls (audit finding C4).

Enforces 01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md at runtime.
Project data is CONFIDENTIAL by default (see script_project_init.py), and the
standard forbids sending CONFIDENTIAL/RESTRICTED data to public-tier AI. Before
C4 nothing checked this — confidential customer code could reach public AI.

Guard behaviour (Phase 10 / Retrofit Pre-Analysis update):
  RESTRICTED   → always hard-block (never overridable)
  CONFIDENTIAL → soft-block: returns requires_consent=True.
                 Passable with engineer approval (consent_confirmed=True).
                 Liability transfers to the engineer; consent is written to
                 AI_DECISION_LOG.
  INTERNAL     → allowed, PII soft-warn (handled by factory_web)
  PUBLIC       → directly allowed

Backward compat: AIGateResult is a NamedTuple — legacy code may unpack it as
  `allowed, reason = check_ai_send(...)`.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from dataclasses import dataclass

# O-1 fix: module-local logger so parse failures in read_project_classification
# are visible in stderr/log rather than swallowed silently.
_logger = logging.getLogger("data_classification_guard")


def _warn(msg: str) -> None:
    """Emit a recoverable warning to stderr via logging."""
    _logger.warning("[parse] %s", msg)

# Providers reached over their public (free/pro) endpoints by default.
PUBLIC_PROVIDERS = {"anthropic", "openai", "google", "gemini", "deepseek"}

# Tiers that satisfy the CONFIDENTIAL "enterprise/self-hosted only" rule.
_ENTERPRISE_TIERS = {"enterprise", "self_hosted", "self-hosted", "private", "local"}

_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED")


@dataclass
class AIGateResult:
    """Guard decision result.

    allowed=True  → the AI call may proceed (consent may not be required).
    allowed=False → the AI call may not proceed.
    requires_consent=True → CONFIDENTIAL: passable with engineer approval.
    requires_consent=False + allowed=False → RESTRICTED: never passable.
    requires_anonymization=True → the data MUST be anonymized before being sent
        to the AI. PUBLIC → False, INTERNAL → True.
        CONFIDENTIAL: already consent-gated; the caller must anonymize.

    Backward compat: unpackable as `allowed, reason = result`
    (custom __iter__ yields only (allowed, reason) — 2-tuple behaviour).
    """
    allowed: bool
    reason: str
    requires_consent: bool = False
    requires_anonymization: bool = False

    def __iter__(self):
        yield self.allowed
        yield self.reason


def normalize_classification(value) -> str:
    """Upper-case a known level; unknown/missing -> CONFIDENTIAL (fail-closed)."""
    v = (value or "").strip().upper()
    return v if v in _LEVELS else "CONFIDENTIAL"


def _provider_is_enterprise(provider: str, settings: dict) -> bool:
    """A provider counts as enterprise/self-hosted only when explicitly marked
    in settings (`self_hosted: true` or `ai_provider_tier[provider]`)."""
    if not settings:
        return False
    if settings.get("self_hosted") is True:
        return True
    tiers = settings.get("ai_provider_tier") or {}
    return str(tiers.get(provider, "")).strip().lower() in _ENTERPRISE_TIERS


def provider_allowed(classification, provider, settings=None) -> AIGateResult:
    """Whether data of `classification` may be sent to `provider`.

    Returns AIGateResult (NamedTuple: allowed, reason, requires_consent).
    Backward-compatible: `allowed, reason = provider_allowed(...)` still works.
    """
    settings = settings or {}
    level = normalize_classification(classification)
    prov = (provider or "").strip().lower()

    if level == "RESTRICTED":
        return AIGateResult(
            allowed=False,
            reason="RESTRICTED veri hiçbir AI ile paylaşılamaz (reçete/parola/lisans/topoloji).",
            requires_consent=False,
        )
    if level == "PUBLIC":
        return AIGateResult(
            allowed=True,
            reason="PUBLIC veri — AI paylaşımına izin var.",
            requires_consent=False,
            requires_anonymization=False,
        )
    if level == "INTERNAL":
        # S-20 (B-G8): INTERNAL projects also require anonymization. Sending is
        # allowed, but the caller MUST anonymize the data before sending it.
        return AIGateResult(
            allowed=True,
            reason=(
                "INTERNAL veri — AI paylaşımına izin var, "
                "ancak gönderim öncesi anonymize ZORUNLU (B-G8 / S-20)."
            ),
            requires_consent=False,
            requires_anonymization=True,
        )

    # CONFIDENTIAL
    if _provider_is_enterprise(prov, settings):
        return AIGateResult(
            allowed=True,
            reason=f"CONFIDENTIAL — '{prov}' enterprise/self-hosted olarak işaretli.",
            requires_consent=False,
        )
    if prov in PUBLIC_PROVIDERS:
        return AIGateResult(
            allowed=False,
            reason=(
                f"CONFIDENTIAL veri '{prov}' ile paylaşmak için mühendis onayı gerekiyor. "
                "Onay verirseniz sorumluluk size geçer ve AI_DECISION_LOG'a kaydedilir. "
                "(RESTRICTED veriler için onay seçeneği yoktur.)"
            ),
            requires_consent=True,
        )
    # Unknown provider — cannot confirm it is safe.
    return AIGateResult(
        allowed=False,
        reason=(
            f"CONFIDENTIAL — '{prov}' sağlayıcısı güvenli (enterprise/self-hosted) "
            "olarak doğrulanamadı; paylaşım reddedildi (fail-closed)."
        ),
        requires_consent=False,
    )


def read_project_classification(project_root) -> str:
    """Read data_classification from PROJECT_STATE.json then PROJECT_MAESTRO.md.

    Missing project / field -> CONFIDENTIAL (fail-closed).
    """
    if not project_root:
        return "CONFIDENTIAL"
    root = Path(project_root)
    try:
        f = root / "PROJECT_STATE.json"
        if f.is_file():
            st = json.loads(f.read_text(encoding="utf-8"))
            if st.get("data_classification"):
                return normalize_classification(st["data_classification"])
    except Exception as exc:
        # O-1 fix: parse failure logged; fail-closed (CONFIDENTIAL) is unchanged.
        _warn(f"PROJECT_STATE.json parse error ({root / 'PROJECT_STATE.json'}): {exc}")
    try:
        f = root / "PROJECT_MAESTRO.md"
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"(?mi)^data_classification:\s*([A-Za-z]+)", text)
            if m:
                return normalize_classification(m.group(1))
    except Exception as exc:
        # O-1 fix: parse failure logged; fail-closed (CONFIDENTIAL) is unchanged.
        _warn(f"PROJECT_MAESTRO.md read error ({root / 'PROJECT_MAESTRO.md'}): {exc}")
    return "CONFIDENTIAL"


def check_ai_send(
    project_root,
    provider,
    settings=None,
    *,
    consent_confirmed: bool = False,
) -> AIGateResult:
    """Read the project classification and apply the gate.

    consent_confirmed=True: engineer explicitly approved sharing CONFIDENTIAL
    data with this provider. Only applies when requires_consent=True; has no
    effect on RESTRICTED (always blocked) or PUBLIC/INTERNAL (always allowed).
    The caller is responsible for logging the consent to AI_DECISION_LOG.
    """
    level = read_project_classification(project_root)
    result = provider_allowed(level, provider, settings)
    if result.requires_consent and consent_confirmed:
        # CONFIDENTIAL + engineer approval: allowed, anonymization required.
        return AIGateResult(
            allowed=True,
            reason=result.reason,
            requires_consent=False,
            requires_anonymization=True,
        )
    return result
