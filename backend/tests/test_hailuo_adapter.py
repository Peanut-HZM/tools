"""HailuoAdapter 测试"""

import pytest

from app.services.llm.hailuo_adapter import HailuoAdapter
from app.services.llm.exceptions import OperationNotSupportedError


@pytest.mark.asyncio
async def test_text2img_raises_not_implemented():
    """测试 text2img 调用抛出 NotImplementedError（占位实现）"""
    a = HailuoAdapter(api_key="x", base_url="https://x.com", model="m")

    with pytest.raises(NotImplementedError, match="待接入实际 API"):
        await a.generate("text2img", "a cat")


@pytest.mark.asyncio
async def test_unsupported_operation():
    """测试不支持的 operation（如 img2img）抛出 OperationNotSupportedError"""
    a = HailuoAdapter(api_key="x", base_url="https://x.com", model="m")

    with pytest.raises(OperationNotSupportedError):
        await a.generate("img2img", "a cat")


@pytest.mark.asyncio
async def test_test_connection():
    """测试 test_connection 返回 (True, 'ok')"""
    a = HailuoAdapter(api_key="x", base_url="https://x.com", model="m")
    ok, msg = await a.test_connection()
    assert ok is True
