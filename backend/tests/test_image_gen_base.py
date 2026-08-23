"""ImageGenAdapter 抽象基类测试"""

import pytest

from app.services.llm.exceptions import OperationNotSupportedError
from app.services.llm.image_gen_base import ImageGenAdapter


class _StubAdapter(ImageGenAdapter):
    """仅实现 generate 的最小子类"""

    SUPPORTED_OPERATIONS = frozenset({"text2img"})

    async def _do_generate(self, operation, prompt, **kw):
        return [b"fake"]

    async def test_connection(self):
        return (True, "ok")


@pytest.mark.asyncio
async def test_generate_returns_bytes():
    a = _StubAdapter()
    result = await a.generate("text2img", "a cat")
    assert result == [b"fake"]


@pytest.mark.asyncio
async def test_default_operations_raise():
    """默认操作支持为空集，调用任何 op 都抛 OperationNotSupportedError"""

    class _NoOps(ImageGenAdapter):
        async def _do_generate(self, operation, prompt, **kw):
            raise NotImplementedError

        async def test_connection(self):
            return (True, "ok")

    a = _NoOps()
    with pytest.raises(OperationNotSupportedError):
        await a.generate("inpaint", "x")


@pytest.mark.asyncio
async def test_supported_operations_check():
    """supports_operation 应基于 SUPPORTED_OPERATIONS 判断"""
    a = _StubAdapter()
    assert a.supports_operation("text2img")
