"""IMAGE_GEN_BACKEND 配置项测试

验证 feature flag 的默认值、显式切换和非法值拒绝行为。
"""
import importlib
import os
import pytest


def _reload_settings(env_value: str | None = None):
    """设置/清除环境变量后重新加载 config 模块，返回 Settings 类。"""
    if env_value is None:
        os.environ.pop("IMAGE_GEN_BACKEND", None)
    else:
        os.environ["IMAGE_GEN_BACKEND"] = env_value

    import app.config.config as cfg_mod
    importlib.reload(cfg_mod)
    return cfg_mod.Settings


class TestImageGenBackendConfig:
    """IMAGE_GEN_BACKEND feature flag 行为验证"""

    def teardown_method(self):
        """每个用例结束后清理环境变量并恢复模块。"""
        os.environ.pop("IMAGE_GEN_BACKEND", None)
        import app.config.config as cfg_mod
        importlib.reload(cfg_mod)

    def test_default_is_dual(self):
        """未设置环境变量时，默认值应为 'dual'（阶段 1 双写验证，dify 为安全回滚位）。"""
        Settings = _reload_settings(None)
        s = Settings()
        assert s.IMAGE_GEN_BACKEND == "dual"

    def test_explicit_harness(self):
        """显式设置 IMAGE_GEN_BACKEND=harness 应被接受。"""
        Settings = _reload_settings("harness")
        s = Settings()
        assert s.IMAGE_GEN_BACKEND == "harness"

    def test_explicit_dual(self):
        """显式设置 IMAGE_GEN_BACKEND=dual 应被接受。"""
        Settings = _reload_settings("dual")
        s = Settings()
        assert s.IMAGE_GEN_BACKEND == "dual"

    def test_invalid_value_rejected(self):
        """非法值应触发 ValidationError。"""
        from pydantic import ValidationError
        os.environ["IMAGE_GEN_BACKEND"] = "unknown_backend"
        import app.config.config as cfg_mod
        with pytest.raises(ValidationError, match="IMAGE_GEN_BACKEND"):
            # reload 会执行模块级 settings = get_settings()，ValidationError 在此抛出
            importlib.reload(cfg_mod)
