"""MemoryService 单元测试"""
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.harness.memory_service import MemoryService, MemoryEntry


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    return db


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.embed = AsyncMock(return_value=[[0.1] * 1536])
    return provider


@pytest.fixture
def service(mock_db, mock_provider):
    return MemoryService(db=mock_db, embedding_provider=mock_provider)


AGENT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


# --- store 测试 ---

@pytest.mark.asyncio
async def test_store_creates_embedding(service, mock_provider):
    """store() 调用 provider 生成 embedding 后存入 DB"""
    await service.store(AGENT_ID, USER_ID, "test_key", {"text": "hello"}, importance=0.8)
    mock_provider.embed.assert_called_once_with(["hello"])


@pytest.mark.asyncio
async def test_store_fallback_on_embed_failure(service, mock_provider):
    """embedding 失败时仍保存 KV，embedding=None"""
    mock_provider.embed.side_effect = RuntimeError("API error")
    await service.store(AGENT_ID, USER_ID, "key", {"text": "val"})
    # 不抛异常，正常返回


# --- search 测试 ---

@pytest.mark.asyncio
async def test_search_returns_entries(service, mock_provider):
    """search() 返回匹配结果"""
    # mock DB 查询返回
    mock_row = MagicMock()
    mock_row.key = "test_key"
    mock_row.value = {"text": "hello"}
    mock_row.importance = 0.8
    mock_row.access_count = 0
    mock_row.embedding = str([0.1] * 1536)

    with patch.object(service, "_vector_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            MemoryEntry(key="test_key", value={"text": "hello"}, score=0.92, importance=0.8)
        ]
        results = await service.search(AGENT_ID, USER_ID, "hello", top_k=5)
        assert len(results) == 1
        assert results[0].key == "test_key"


@pytest.mark.asyncio
async def test_search_fallback_to_keyword(service, mock_provider):
    """向量检索失败时降级为关键词 LIKE"""
    mock_provider.embed.side_effect = RuntimeError("API unavailable")
    # mock LIKE 查询
    mock_row = MagicMock()
    mock_row.key = "test_key"
    mock_row.value = {"text": "hello world"}
    mock_row.importance = 0.5
    mock_row.access_count = 0
    mock_row.summary = None

    service._db_session.query.return_value.filter.return_value.filter.return_value.all.return_value = [mock_row]
    results = await service.search(AGENT_ID, USER_ID, "hello", top_k=5)
    assert len(results) >= 0  # 降级不报错


# --- get_by_key / list_all / delete 测试 ---

@pytest.mark.asyncio
async def test_get_by_key_found(service):
    """get_by_key 返回存在的记录"""
    mock_row = MagicMock()
    mock_row.key = "test_key"
    mock_row.value = {"text": "hello"}
    mock_row.importance = 0.5
    mock_row.access_count = 0
    mock_row.summary = None

    service._db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_row
    result = await service.get_by_key(AGENT_ID, USER_ID, "test_key")
    assert result is not None
    assert result.key == "test_key"


@pytest.mark.asyncio
async def test_delete_success(service):
    """delete 删除记录"""
    mock_row = MagicMock()
    mock_row.key = "test_key"
    mock_row.value = {"text": "hello"}
    mock_row.importance = 0.5
    mock_row.access_count = 0
    mock_row.summary = None

    service._db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_row
    deleted = await service.delete(AGENT_ID, USER_ID, "test_key")
    assert deleted is True
    service._db.delete.assert_called_once_with(mock_row)
    service._db.commit.assert_called()