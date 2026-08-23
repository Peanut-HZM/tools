"""BackendRegistry 测试"""

import pytest

from app.services.image_gen.backends import BackendRegistry
from app.services.image_gen.base import BackendResult, IImageGenerationBackend


class _StubBackend(IImageGenerationBackend):
    async def run(self, ctx):
        return BackendResult()


@pytest.fixture(autouse=True)
def reset_registry():
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


def test_register_and_get():
    b = _StubBackend()
    BackendRegistry.register("stub", b)
    assert BackendRegistry.get("stub") is b


def test_get_unregistered_raises():
    from app.services.image_gen.backends import BackendNotConfiguredError
    with pytest.raises(BackendNotConfiguredError):
        BackendRegistry.get("nonexistent")
