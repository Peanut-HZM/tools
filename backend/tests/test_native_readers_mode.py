"""原生读取器模式（off / shadow / on / native）的行为测试

重点：
- 模式解析与非法值回退
- 模式覆盖（脚本按固定口径回填）
- native 模式不调用任何 ccusage 子进程
- native 模式显式报告未被原生读取器覆盖的 source
"""
from unittest.mock import MagicMock, patch

import pytest


class TestNativeReadersMode:
    """模式解析"""

    def _mode(self, monkeypatch, value):
        from app.config.config import settings
        from app.services.token_usage_sync_service import _native_readers_mode

        monkeypatch.setattr(settings, "TOKEN_USAGE_NATIVE_READERS_MODE", value)
        return _native_readers_mode()

    def test_accepts_all_four_modes(self, monkeypatch):
        for value in ("off", "shadow", "on", "native"):
            assert self._mode(monkeypatch, value) == value

    def test_normalizes_case_and_whitespace(self, monkeypatch):
        assert self._mode(monkeypatch, "  NATIVE ") == "native"

    def test_invalid_mode_falls_back_to_off(self, monkeypatch):
        """写错模式名（如 compare）必须回退 off，不能被静默忽略"""
        assert self._mode(monkeypatch, "compare") == "off"
        assert self._mode(monkeypatch, "") == "off"


class TestNativeReadersModeOverride:
    """模式覆盖：脚本按固定口径执行，退出后恢复原值"""

    def test_override_and_restore(self):
        from app.config.config import settings
        from app.services.token_usage_sync_service import (
            _native_readers_mode,
            native_readers_mode_override,
        )

        original = settings.TOKEN_USAGE_NATIVE_READERS_MODE
        with native_readers_mode_override("native"):
            assert _native_readers_mode() == "native"
        assert settings.TOKEN_USAGE_NATIVE_READERS_MODE == original

    def test_restores_on_exception(self):
        from app.config.config import settings
        from app.services.token_usage_sync_service import native_readers_mode_override

        original = settings.TOKEN_USAGE_NATIVE_READERS_MODE
        with pytest.raises(RuntimeError):
            with native_readers_mode_override("on"):
                raise RuntimeError("boom")
        assert settings.TOKEN_USAGE_NATIVE_READERS_MODE == original


class TestUncoveredSources:
    """native 模式的覆盖度检查：缺口必须显式暴露，不能静默丢数据"""

    def test_reports_uncovered_sources(self):
        from app.services.token_usage_sync_service import _log_uncovered_sources

        result = {"errors": []}
        with patch("app.utils.agent_readers.READERS", {"claude": object(), "codex": object()}):
            _log_uncovered_sources(result)

        assert len(result["errors"]) == 1
        err = result["errors"][0]
        assert err["error_code"] == "SOURCE_NOT_COVERED"
        assert "opencode" in err["details"]["uncovered_sources"]
        assert "claude" not in err["details"]["uncovered_sources"]

    def test_no_error_when_all_covered(self):
        from app.services.token_usage_sync_service import (
            CCUSAGE_CAPABLE_SOURCES,
            _log_uncovered_sources,
        )

        result = {"errors": []}
        with patch("app.utils.agent_readers.READERS", dict.fromkeys(CCUSAGE_CAPABLE_SOURCES, object())):
            _log_uncovered_sources(result)

        assert result["errors"] == []


class TestNativeModeSkipsCcusage:
    """native 模式不得调用任何 ccusage 子进程"""

    def _run_sync(self, mode):
        from app.services import token_usage_sync_service as svc

        calls = {"claude": 0, "ccusage_v2": 0}

        def _claude(_days):
            calls["claude"] += 1
            return []

        def _v2(_since, _until):
            calls["ccusage_v2"] += 1
            return {"records": [], "errors": []}

        native_records = [
            {
                "record_date": "2026-01-01",
                "source": "claude",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 2,
                "total_cost": 0.0,
            }
        ]

        db = MagicMock()
        with patch.object(svc, "_native_readers_mode", return_value=mode), \
             patch.object(svc, "_fetch_claude_daily", side_effect=_claude), \
             patch.object(svc, "_fetch_ccusage_v2_records", side_effect=_v2), \
             patch.object(svc, "_fetch_native_records", return_value={
                 "records": native_records, "errors": [], "sources": ["claude"]}), \
             patch.object(svc, "SessionLocal", return_value=db), \
             patch.object(svc, "_write_native_records", return_value=1), \
             patch.object(svc, "_upsert_records", return_value=0), \
             patch.object(svc, "_log_sync", return_value=None), \
             patch.object(svc, "_log_uncovered_sources", return_value=None):
            result = svc.sync_token_usage(user_id="u1", days=30)

        return calls, result

    def test_native_mode_never_calls_ccusage(self):
        calls, _ = self._run_sync("native")
        assert calls["claude"] == 0
        assert calls["ccusage_v2"] == 0

    def test_off_mode_still_calls_ccusage(self):
        """off 模式保持原有行为（ccusage 仍负责采集）"""
        calls, _ = self._run_sync("off")
        assert calls["claude"] == 1
        assert calls["ccusage_v2"] == 1
