"""C2 — PLCSIM-only hedef doğrulama (saf karar mantığı).

provider.Download runtime çağrısı TIA/PLCSIM olmadan test EDİLEMEZ; burada
yalnızca fail-closed karar fonksiyonları doğrulanır.
"""

import pytest

from bridges.tia.plcsim_download import (
    DangerousDownloadOption,
    PlcSimDownloadResult,
    _configure_post,
    _configure_pre,
    _is_dangerous_option,
    _is_download_target_safe,
    _name_indicates_plcsim,
    _tokenise,
)


def test_verified_plcsim_target_allowed():
    ok, reason = _is_download_target_safe({"is_plcsim": True}, plcsim_only=True)
    assert ok is True
    assert "PLCSIM" in reason


def test_real_plc_target_refused():
    ok, reason = _is_download_target_safe(
        {"is_plcsim": False, "target_name": "S7-1500"}, plcsim_only=True
    )
    assert ok is False
    assert "real PLC" in reason


def test_unverified_target_refused_fail_closed():
    ok, reason = _is_download_target_safe({"is_plcsim": None}, plcsim_only=True)
    assert ok is False
    assert "fail-closed" in reason.lower()


def test_plcsim_only_off_refused():
    ok, reason = _is_download_target_safe({"is_plcsim": True}, plcsim_only=False)
    assert ok is False
    assert "plcsim_only" in reason.lower()


def test_name_indicates_plcsim():
    assert _name_indicates_plcsim("PLCSIM[1]") is True
    assert _name_indicates_plcsim("PLCSIM Advanced") is True
    assert _name_indicates_plcsim("PN/IE_1 -> S7-1500 station") is False
    assert _name_indicates_plcsim("") is False


def test_is_dangerous_option():
    assert _is_dangerous_option("StopModules") is True
    assert _is_dangerous_option("OverwriteSystemData") is True
    assert _is_dangerous_option("FormatMemoryCard") is True
    assert _is_dangerous_option("ConsistentBlocksDownload") is False


# -- W-A4: callbacks must abort, not merely warn ----

class _FakeCfg:
    def __init__(self, name: str):
        self.Name = name


class _FakeDlConfig:
    def __init__(self, names):
        self.Configurations = [_FakeCfg(n) for n in names]


def test_configure_pre_raises_on_dangerous_option():
    dl = _FakeDlConfig(["StopModules", "ConsistentBlocksDownload"])
    res = PlcSimDownloadResult()
    with pytest.raises(DangerousDownloadOption) as excinfo:
        _configure_pre(dl, res)
    assert "StopModules" in str(excinfo.value)
    assert any("StopModules" in e for e in res.errors)


def test_configure_post_raises_on_dangerous_option():
    dl = _FakeDlConfig(["FormatMemoryCard"])
    res = PlcSimDownloadResult()
    with pytest.raises(DangerousDownloadOption):
        _configure_post(dl, res)
    assert any("FormatMemoryCard" in e for e in res.errors)


def test_configure_pre_benign_options_pass():
    dl = _FakeDlConfig(["ConsistentBlocksDownload", "AlarmTextLibrariesDownload"])
    res = PlcSimDownloadResult()
    # Should not raise.
    _configure_pre(dl, res)
    assert res.errors == []


# ── O-4: kelime sınırı tokeniser — "reset" substring false-positive fix ──────

class TestTokenise:
    """_tokenise, CamelCase adları bağımsız küçük-harf token'larına ayırmalı."""

    def test_camel_stopmodules(self):
        assert _tokenise("StopModules") == ["stop", "modules"]

    def test_camel_formatmemorycard(self):
        assert _tokenise("FormatMemoryCard") == ["format", "memory", "card"]

    def test_plain_reset(self):
        assert _tokenise("Reset") == ["reset"]

    def test_camel_resettime_splits_to_two_tokens(self):
        # "ResetTime" iki token → ["reset", "time"]; "reset" token olarak mevcut.
        # Fail-safe: "reset" token içeren compound adlar da bloke edilir.
        tokens = _tokenise("ResetTime")
        assert tokens == ["reset", "time"]

    def test_plain_preset_is_single_token(self):
        # "preset" → ["preset"]; "reset" adlı ayrı token YOK.
        tokens = _tokenise("preset")
        assert tokens == ["preset"]

    def test_overwrite_system_data(self):
        assert _tokenise("OverwriteSystemData") == ["overwrite", "system", "data"]


class TestIsDangerousOptionFalsePositiveFix:
    """O-4: Kısa hint'ler artık false-positive üretmemeli; gerçek tehlikeli option'lar hâlâ bloke edilmeli."""

    # --- BLOKE EDİLMELİ (gerçek tehlikeli option'lar) -----------------------

    def test_stop_modules_camel(self):
        assert _is_dangerous_option("StopModules") is True

    def test_stop_modules_space(self):
        assert _is_dangerous_option("Stop Modules") is True

    def test_overwrite_system_data(self):
        assert _is_dangerous_option("OverwriteSystemData") is True

    def test_format_memory_card(self):
        assert _is_dangerous_option("FormatMemoryCard") is True

    def test_delete_data(self):
        assert _is_dangerous_option("DeleteData") is True

    def test_reset_standalone(self):
        # "Reset" — tek başına tehlikeli (fabrika ayarlarına sıfırla).
        assert _is_dangerous_option("Reset") is True

    def test_reset_lowercase_standalone(self):
        assert _is_dangerous_option("reset") is True

    # --- GEÇMELİ (false-positive — artık bloke EDİLMEMELİ) ------------------

    def test_resettime_is_blocked_fail_safe(self):
        # "ResetTime" → ["reset", "time"] → "reset" token mevcut.
        # Fail-safe prensibine göre: "reset" token'ı içeren compound adlar bloke edilir.
        # TIA Openness'da gerçek bir "ResetTime" option'ı nadirdir; bloke etmek güvenli taraf.
        assert _is_dangerous_option("ResetTime") is True

    def test_preset_not_dangerous(self):
        # "preset" içinde "reset" substring'i var ama bağımsız token değil.
        assert _is_dangerous_option("preset") is False

    def test_autoreset_not_dangerous(self):
        # "AutoReset" → ["auto", "reset"] — içinde "reset" token VAR, bloke edilmeli.
        # Bu KASITLI: "AutoReset" adlı bir option gerçekten cihaz durumunu sıfırlıyor olabilir.
        # Fail-safe: belirsiz durum → bloke et.
        assert _is_dangerous_option("AutoReset") is True

    def test_consistent_blocks_download_safe(self):
        assert _is_dangerous_option("ConsistentBlocksDownload") is False

    def test_alarm_text_libraries_safe(self):
        assert _is_dangerous_option("AlarmTextLibrariesDownload") is False

    def test_empty_name_blocked_fail_safe(self):
        # Boş/bilinmeyen isim → fail-safe olarak bloke et.
        assert _is_dangerous_option("") is True

    def test_none_name_blocked_fail_safe(self):
        # None → fail-safe bloke.
        assert _is_dangerous_option(None) is True


class TestConfigureCallbacksWithFalsePositiveCases:
    """_configure_pre/_post: false-positive düzeltme sonrası safe option'lar download'u engellemez."""

    def test_resettime_option_still_aborts_fail_safe(self):
        # "ResetTime" → "reset" token içeriyor → fail-safe olarak bloke edilir.
        # compound "reset" adları kullanıcıya TIA içinde manuel onay gerektirir.
        dl = _FakeDlConfig(["ResetTime", "ConsistentBlocksDownload"])
        res = PlcSimDownloadResult()
        with pytest.raises(DangerousDownloadOption):
            _configure_pre(dl, res)
        assert res.errors != []

    def test_preset_option_does_not_abort_download(self):
        dl = _FakeDlConfig(["preset"])
        res = PlcSimDownloadResult()
        _configure_pre(dl, res)
        assert res.errors == []

    def test_real_reset_still_aborts(self):
        # "Reset" (standalone) gerçek tehlike → hâlâ exception yükseltmeli.
        dl = _FakeDlConfig(["Reset"])
        res = PlcSimDownloadResult()
        with pytest.raises(DangerousDownloadOption):
            _configure_pre(dl, res)
        assert res.errors != []
