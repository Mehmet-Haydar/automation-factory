"""S-8 fix proof test — APP_VERSION sabiti ve get_state() dönüş değeri.

Proof kriterleri:
1. APP_VERSION modül düzeyinde tanımlı ve v{MAJOR}.{MINOR}.{PATCH} formatında.
2. get_state() dönüş değerindeki "version" anahtarı APP_VERSION ile EŞİT —
   hardcoded literal değil; sabitten okunuyor.
3. Regresyon koruyucusu: "version" key'i eskimiş "v3.6.0" literal'i içermez.

Fix geri alınırsa (APP_VERSION kaldırılırsa veya get_state'te tekrar literal
kullanılırsa) bu testler KIRILIR — smoke değil, koruyucu proof testlerdir.
"""
from __future__ import annotations

import re

import factory_web as fw


# ---------------------------------------------------------------------------
# 1. APP_VERSION sabiti
# ---------------------------------------------------------------------------

def test_app_version_constant_exists():
    """APP_VERSION modül düzeyinde tanımlı olmalı."""
    assert hasattr(fw, "APP_VERSION"), (
        "APP_VERSION sabiti factory_web.py modül kapsamında bulunamadı. "
        "S-8 fix uygulandı mı?"
    )


def test_app_version_format():
    """APP_VERSION 'v{MAJOR}.{MINOR}.{PATCH}' formatına uymalı."""
    pattern = re.compile(r"^v\d+\.\d+\.\d+$")
    assert pattern.match(fw.APP_VERSION), (
        f"APP_VERSION='{fw.APP_VERSION}' beklenen format 'vX.Y.Z' ile eşleşmiyor."
    )


def test_app_version_is_not_stale_v360():
    """APP_VERSION eski hardcoded değer 'v3.6.0' olmamalı (S-8 bulgusunun köküdür)."""
    assert fw.APP_VERSION != "v3.6.0", (
        "APP_VERSION hâlâ 'v3.6.0' — S-8 fix uygulanmamış veya geri alınmış."
    )


# ---------------------------------------------------------------------------
# 2. get_state() "version" anahtarı APP_VERSION ile eşleşmeli
# ---------------------------------------------------------------------------

def test_get_state_version_equals_app_version():
    """get_state() -> 'version' değeri APP_VERSION sabitiyle aynı olmalı.

    root=None (proje açılmamış) durumunda da get_state() çalışır.
    """
    api = fw.Api()
    state = api.get_state()

    assert "version" in state, "get_state() dönüşünde 'version' anahtarı yok."
    assert state["version"] == fw.APP_VERSION, (
        f"get_state()['version']='{state['version']}' != APP_VERSION='{fw.APP_VERSION}'. "
        "get_state() içindeki hardcoded literal kaldırılmadı veya APP_VERSION'dan okunmuyor."
    )


def test_get_state_version_not_hardcoded_v360():
    """get_state() 'version' alanı asla 'v3.6.0' döndürmemeli (regresyon koruması)."""
    api = fw.Api()
    state = api.get_state()

    assert state.get("version") != "v3.6.0", (
        "get_state()['version'] == 'v3.6.0' — S-8 fix geri alınmış ya da uygulama "
        "versiyonu yanlış güncellendi."
    )


def test_get_state_version_matches_semver_pattern():
    """get_state() 'version' değeri semver formatında olmalı."""
    api = fw.Api()
    state = api.get_state()

    version = state.get("version", "")
    pattern = re.compile(r"^v\d+\.\d+\.\d+$")
    assert pattern.match(version), (
        f"get_state()['version']='{version}' semver formatı 'vX.Y.Z' ile eşleşmiyor."
    )
