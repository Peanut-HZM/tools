"""Provider Registry 测试"""
import pytest
from unittest.mock import MagicMock

from app.services.harness.image_provider.base import ImageGenError, ImageModelProvider
from app.services.harness.image_provider.registry import resolve_provider, _PROVIDER_MAP


class StubProvider(ImageModelProvider):
    """测试用 stub provider"""
    async def text2img(self, prompt, params):
        pass
    async def img2img(self, prompt, reference_image, params):
        pass
    async def inpaint(self, prompt, image_url, mask_url, params):
        pass
    async def upload_edit(self, image_url, instruction, params):
        pass
    def validate_config(self):
        pass


class TestResolveProvider:
    def test_known_provider_type(self, monkeypatch):
        """已知 provider_type 能解析到对应实现"""
        monkeypatch.setitem(_PROVIDER_MAP, "test_type", StubProvider)
        mock_llm_provider = MagicMock()
        mock_llm_provider.provider_type = "test_type"
        mock_llm_provider.base_url = "https://api.example.com"
        mock_llm_provider.api_key_encrypted = "encrypted_key"

        # mock decrypt 函数
        import app.services.harness.image_provider.registry as reg
        monkeypatch.setattr(reg, "decrypt_api_key", lambda k: "decrypted_key")

        result = resolve_provider(mock_llm_provider)
        assert isinstance(result, StubProvider)
        assert result.base_url == "https://api.example.com"
        assert result.api_key == "decrypted_key"

    def test_unknown_provider_type_raises(self):
        """未知 provider_type 抛出 ImageGenError"""
        mock_llm_provider = MagicMock()
        mock_llm_provider.provider_type = "unknown_type"

        with pytest.raises(ImageGenError, match="不支持"):
            resolve_provider(mock_llm_provider)

    def test_oss_client_passed_through(self, monkeypatch):
        """oss_client 透传给 provider"""
        monkeypatch.setitem(_PROVIDER_MAP, "test_type2", StubProvider)
        mock_llm_provider = MagicMock()
        mock_llm_provider.provider_type = "test_type2"
        mock_llm_provider.base_url = "https://api.example.com"
        mock_llm_provider.api_key_encrypted = "key"

        import app.services.harness.image_provider.registry as reg
        monkeypatch.setattr(reg, "decrypt_api_key", lambda k: "key")

        mock_oss = MagicMock()
        result = resolve_provider(mock_llm_provider, oss_client=mock_oss)
        assert result.oss_client is mock_oss
