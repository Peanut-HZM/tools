"""K8s 客户端工厂测试"""
import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.k8s_client_factory import build_client, ClientBundle


@pytest.fixture
def mock_config():
    """模拟数据库配置记录"""
    return {
        "id": "test-id",
        "user_id": "u1",
        "server": "https://k8s.example.com:6443",
        "auth_type": "bearer_token",
        "auth_data_encrypted": "encrypted_data",
        "ca_cert_encrypted": None,
    }


@pytest.mark.asyncio
async def test_build_client_bearer_token(mock_config):
    """bearer_token 模式构造客户端，验证 bundle 结构及 ApiClient 自动关闭"""
    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s:

        # 模拟解密返回 token JSON
        mock_enc.decrypt.return_value = json.dumps({"token": "my-token"})

        # 模拟 ApiClient 实例（close 是协程，需返回已完成的 Future）
        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client

        async with build_client(mock_config) as bundle:
            assert isinstance(bundle, ClientBundle)
            assert bundle.core_v1 is not None
            assert bundle.apps_v1 is not None
            assert bundle.batch_v1 is not None
            assert bundle.custom_objects is not None

        # 退出上下文后，ApiClient.close 必须被调用
        mock_api_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_build_client_missing_auth_raises(mock_config):
    """auth_data_encrypted 为 None 时，build_client 应抛出 ValueError"""
    mock_config["auth_data_encrypted"] = None
    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc:
        with pytest.raises(ValueError, match="auth"):
            async with build_client(mock_config):
                pass
    # 不应调用解密（提前抛出）
    mock_enc.decrypt.assert_not_called()


@pytest.mark.asyncio
async def test_build_client_bearer_token_sets_api_key_correctly(mock_config):
    """验证 bearer_token 模式下 api_key 字典使用 BearerToken key"""
    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s:

        mock_enc.decrypt.return_value = json.dumps({"token": "my-token"})

        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client

        async with build_client(mock_config) as bundle:
            # 验证 Configuration 被正确构造
            config_call = mock_k8s.Configuration.return_value
            assert config_call.api_key == {"BearerToken": "my-token"}
            assert config_call.host == mock_config["server"]


@pytest.mark.asyncio
async def test_build_client_client_cert(mock_config):
    """验证 client_cert 模式下 cert_file 和 key_file 被正确设置"""
    mock_config["auth_type"] = "client_cert"

    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s, \
         patch("app.services.k8s_client_factory._write_temp_file") as mock_write:

        mock_enc.decrypt.return_value = json.dumps({
            "client_cert": "CERT_CONTENT",
            "client_key": "KEY_CONTENT"
        })
        mock_write.side_effect = ["/tmp/cert.crt", "/tmp/key.key"]

        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client

        async with build_client(mock_config) as bundle:
            config_call = mock_k8s.Configuration.return_value
            assert config_call.cert_file == "/tmp/cert.crt"
            assert config_call.key_file == "/tmp/key.key"

            # 验证临时文件被写入
            assert mock_write.call_count == 2


@pytest.mark.asyncio
async def test_build_client_basic_auth(mock_config):
    """验证 basic_auth 模式下 username 和 password 被正确设置"""
    mock_config["auth_type"] = "basic_auth"

    with patch("app.services.k8s_client_factory.EncryptionUtils") as mock_enc, \
         patch("app.services.k8s_client_factory.k8s_client") as mock_k8s:

        mock_enc.decrypt.return_value = json.dumps({
            "username": "admin",
            "password": "secret"
        })

        mock_api_client = MagicMock()
        fut = asyncio.Future()
        fut.set_result(None)
        mock_api_client.close.return_value = fut
        mock_k8s.ApiClient.return_value = mock_api_client

        async with build_client(mock_config) as bundle:
            config_call = mock_k8s.Configuration.return_value
            assert config_call.username == "admin"
            assert config_call.password == "secret"
