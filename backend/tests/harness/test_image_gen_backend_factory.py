"""ImageGenBackendFactory 单元测试

覆盖 6 个场景：
1. factory returns DifyExecutor when dify
2. factory returns HarnessExecutor when harness
3. factory returns DualExecutor when dual（含 primary/secondary 断言）
4. dual returns primary result
5. dual logs diff
6. dual primary failure returns error（不降级）
"""
import logging
from unittest.mock import AsyncMock, patch

import pytest


class TestFactoryModeSwitch:
    """工厂模式切换测试"""

    def test_factory_returns_dify_executor_when_dify(self):
        """backend=dify 应返回 DifyImageGenExecutor"""
        from app.services.harness.image_gen_backend.factory import (
            ImageGenBackendFactory,
        )
        from app.services.harness.image_gen_backend.executors import (
            DifyImageGenExecutor,
        )

        with patch("app.services.harness.image_gen_backend.factory.settings") as mock_settings:
            mock_settings.IMAGE_GEN_BACKEND = "dify"
            executor = ImageGenBackendFactory.create()
        assert isinstance(executor, DifyImageGenExecutor)

    def test_factory_returns_harness_executor_when_harness(self):
        """backend=harness 应返回 HarnessImageGenExecutor"""
        from app.services.harness.image_gen_backend.factory import (
            ImageGenBackendFactory,
        )
        from app.services.harness.image_gen_backend.executors import (
            HarnessImageGenExecutor,
        )

        with patch("app.services.harness.image_gen_backend.factory.settings") as mock_settings:
            mock_settings.IMAGE_GEN_BACKEND = "harness"
            executor = ImageGenBackendFactory.create()
        assert isinstance(executor, HarnessImageGenExecutor)

    def test_factory_returns_dual_executor_when_dual(self):
        """backend=dual 应返回 DualImageGenExecutor，且 primary/secondary 类型正确"""
        from app.services.harness.image_gen_backend.factory import (
            ImageGenBackendFactory,
        )
        from app.services.harness.image_gen_backend.executors import (
            DualImageGenExecutor,
            HarnessImageGenExecutor,
            DifyImageGenExecutor,
        )

        with patch("app.services.harness.image_gen_backend.factory.settings") as mock_settings:
            mock_settings.IMAGE_GEN_BACKEND = "dual"
            executor = ImageGenBackendFactory.create()
        assert isinstance(executor, DualImageGenExecutor)
        assert isinstance(executor.primary, HarnessImageGenExecutor)
        assert isinstance(executor.secondary, DifyImageGenExecutor)


class TestDualExecutor:
    """Dual 执行器行为测试"""

    @pytest.mark.asyncio
    async def test_dual_returns_primary_result(self):
        """Dual 执行器应返回 primary 的结果"""
        primary_result = {
            "success": True,
            "image_urls": ["https://harness.example/img.png"],
            "error": None,
            "backend": "harness",
            "elapsed_ms": 100,
            "request_id": "p-1",
        }
        secondary_result = {
            "success": True,
            "image_urls": ["https://dify.example/img.png"],
            "error": None,
            "backend": "dify",
            "elapsed_ms": 200,
            "request_id": "s-1",
        }

        primary = AsyncMock()
        primary.execute.return_value = primary_result
        secondary = AsyncMock()
        secondary.execute.return_value = secondary_result

        from app.services.harness.image_gen_backend.executors import (
            DualImageGenExecutor,
        )

        dual = DualImageGenExecutor(primary=primary, secondary=secondary)
        result = await dual.execute({"prompt": "test"}, ctx=None)

        # 返回的应该是 primary 的结果
        assert result["success"] is True
        assert result["backend"] == "harness"
        assert result["image_urls"] == ["https://harness.example/img.png"]
        # primary 和 secondary 都应被调用
        primary.execute.assert_awaited_once()
        secondary.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dual_logs_diff(self, caplog):
        """Dual 执行器应在结果不一致时记录 diff 日志"""
        primary_result = {
            "success": True,
            "image_urls": ["https://harness.example/img.png"],
            "backend": "harness",
        }
        secondary_result = {
            "success": False,
            "image_urls": [],
            "backend": "dify",
            "error": "something failed",
        }

        primary = AsyncMock()
        primary.execute.return_value = primary_result
        secondary = AsyncMock()
        secondary.execute.return_value = secondary_result

        from app.services.harness.image_gen_backend.executors import (
            DualImageGenExecutor,
        )

        dual = DualImageGenExecutor(primary=primary, secondary=secondary)

        with caplog.at_level(logging.WARNING, logger="app.services.harness.image_gen_backend.executors"):
            await dual.execute({"prompt": "test"}, ctx=None)

        # 应该记录了 success 不一致的警告
        diff_logs = [r for r in caplog.records if "success 不一致" in r.getMessage()]
        assert len(diff_logs) > 0, f"未找到 diff 日志，实际日志: {[r.getMessage() for r in caplog.records]}"

    @pytest.mark.asyncio
    async def test_dual_primary_failure_returns_error_no_fallback(self):
        """Dual primary 失败时应返回错误结果，不降级到 secondary"""
        primary_result = {
            "success": False,
            "image_urls": [],
            "error": "HarnessError: 生成失败",
            "backend": "harness",
            "elapsed_ms": 50,
            "request_id": "p-fail",
        }
        secondary_result = {
            "success": True,
            "image_urls": ["https://dify.example/img.png"],
            "error": None,
            "backend": "dify",
            "elapsed_ms": 200,
            "request_id": "s-ok",
        }

        primary = AsyncMock()
        primary.execute.return_value = primary_result
        secondary = AsyncMock()
        secondary.execute.return_value = secondary_result

        from app.services.harness.image_gen_backend.executors import (
            DualImageGenExecutor,
        )

        dual = DualImageGenExecutor(primary=primary, secondary=secondary)
        result = await dual.execute({"prompt": "test"}, ctx=None)

        # 必须返回 primary 的错误结果，不降级
        assert result["success"] is False
        assert result["backend"] == "harness"
        assert "HarnessError" in (result.get("error") or "")
