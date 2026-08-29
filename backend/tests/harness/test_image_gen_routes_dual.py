"""Task 4 — image_generation 路由通过 ImageGenBackendFactory 选择执行器

验证 get_image_gen_executor Depends 函数按 IMAGE_GEN_BACKEND 配置返回对应执行器类型。
"""
from unittest.mock import patch

import pytest

from app.services.harness.image_gen_backend.executors import (
    DifyImageGenExecutor,
    DualImageGenExecutor,
    HarnessImageGenExecutor,
)


def _call_executor(backend_value: str, test_db):
    """patch factory 内的 settings.IMAGE_GEN_BACKEND 后调用 get_image_gen_executor"""
    from app.routes.image_generation import get_image_gen_executor

    # patch factory 模块内的 settings 引用（factory 已 from app.config.config import settings）
    with patch("app.services.harness.image_gen_backend.factory.settings") as mock_settings:
        mock_settings.IMAGE_GEN_BACKEND = backend_value
        executor = get_image_gen_executor(
            db=test_db,
            current_user={"id": "user-1"},
        )
    return executor


def test_image_generation_route_uses_harness_backend(test_db):
    """IMAGE_GEN_BACKEND=harness → HarnessImageGenExecutor"""
    executor = _call_executor("harness", test_db)
    assert isinstance(executor, HarnessImageGenExecutor)


def test_image_generation_route_uses_dify_backend(test_db):
    """IMAGE_GEN_BACKEND=dify → DifyImageGenExecutor"""
    executor = _call_executor("dify", test_db)
    assert isinstance(executor, DifyImageGenExecutor)


def test_image_generation_route_uses_dual_backend(test_db):
    """IMAGE_GEN_BACKEND=dual → DualImageGenExecutor"""
    executor = _call_executor("dual", test_db)
    assert isinstance(executor, DualImageGenExecutor)
    # 验证 primary/secondary 类型也正确
    assert isinstance(executor.primary, HarnessImageGenExecutor)
    assert isinstance(executor.secondary, DifyImageGenExecutor)


def test_image_generation_route_unknown_backend_raises(test_db):
    """IMAGE_GEN_BACKEND=unknown → ValueError"""
    with pytest.raises(ValueError, match="Unknown backend"):
        _call_executor("nonexistent_backend", test_db)


def test_image_generation_route_preserves_existing_service(test_db):
    """原有 get_image_gen_service 仍可正常工作（未破坏旧路径）"""
    from app.routes.image_generation import get_image_gen_service
    from app.services.image_generation_service import ImageGenService

    # get_image_gen_service 只依赖 db（无 current_user），直接传 test_db
    svc = get_image_gen_service(db=test_db)
    assert isinstance(svc, ImageGenService)