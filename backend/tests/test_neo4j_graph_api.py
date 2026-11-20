"""Neo4j 图数据 API 集成测试（schema / sample / expand / search）。

用伪造的 AsyncDriver + AsyncSession 替换 driver_manager.get_driver 的返回，
不断言真实 Neo4j 行为，只验证路由层的参数组装、响应结构、错误降级。
"""
import asyncio
import os
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import get_db
from app.models.base import Base
from app.services.neo4j import driver_manager as dm_module


# ---------------------------------------------------------------------------
# 伪造的 Neo4j 值对象 / 结果对象
# ---------------------------------------------------------------------------
class FakeNode(dict):
    """支持 dict(node) 的伪 Node。"""

    def __init__(self, element_id: str, labels: List[str], props: Dict[str, Any]):
        super().__init__(props)
        self.element_id = element_id
        self.labels = labels


class FakeRelationship(dict):
    """支持 dict(rel) 的伪 Relationship。"""

    def __init__(self, element_id: str, rel_type: str, start_node: FakeNode, end_node: FakeNode, props: Dict[str, Any]):
        super().__init__(props)
        self.element_id = element_id
        self.type = rel_type
        self.start_node = start_node
        self.end_node = end_node


class FakeAsyncResult:
    """可异步迭代的查询结果（records 为 dict 列表）。"""

    def __init__(self, records: List[Dict[str, Any]]):
        self._records = records

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for record in self._records:
            yield record


class FakeAsyncSession:
    """伪 AsyncSession：按查询内容返回预设结果，或抛出预设异常。"""

    def __init__(self):
        self.responses: List[tuple] = []  # [(predicate, records_or_exc)]
        self.closed = False

    def add_response(self, predicate, records=None, exc=None):
        """predicate: callable(cypher) -> bool。"""
        self.responses.append((predicate, records, exc))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def run(self, cypher: str, params: Dict[str, Any] | None = None):
        for predicate, records, exc in self.responses:
            if predicate(cypher):
                if exc is not None:
                    raise exc
                return FakeAsyncResult(records)
        return FakeAsyncResult([])


class FakeAsyncDriver:
    """伪 AsyncDriver：session() 返回预配置的 FakeAsyncSession。"""

    def __init__(self, session: FakeAsyncSession):
        self._session = session
        self.closed = False

    def session(self, **kwargs):
        self.last_session_kwargs = kwargs
        return self._session

    async def close(self):
        self.closed = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    os.environ["NEO4J_CRYPTO_KEY"] = Fernet.generate_key().decode()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    fixture_user_id = str(uuid.uuid4())
    monkeypatch.setattr(
        "app.middleware.auth_middleware.get_current_user_id",
        lambda authorization=None: fixture_user_id,
    )

    fake_session = FakeAsyncSession()
    fake_driver = FakeAsyncDriver(fake_session)

    async def fake_get_driver(conn_id, uri, username, password):
        return fake_driver

    monkeypatch.setattr(
        dm_module.driver_manager, "get_driver", fake_get_driver
    )
    # 关闭真实 close_all，避免污染其他测试
    monkeypatch.setattr(dm_module.driver_manager, "close_driver", AsyncMock())
    monkeypatch.setattr(dm_module.driver_manager, "close_all", AsyncMock())

    with TestClient(app) as c:
        yield c, fake_session, fake_driver

    app.dependency_overrides.clear()


def _create_connection(client) -> str:
    r = client.post("/api/neo4j-tool/connections", json={
        "name": "test", "uri": "bolt://localhost:7687",
        "username": "neo4j", "password": "secret", "database": "neo4j",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Schema 接口
# ---------------------------------------------------------------------------
class TestSchemaApi:
    def test_schema_returns_full_structure(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        # SHOW LABELS
        fake_session.add_response(
            lambda q: q.strip() == "SHOW LABELS",
            records=[{"label": "Person"}, {"label": "Movie"}],
        )
        # SHOW RELATIONSHIP TYPES
        fake_session.add_response(
            lambda q: q.strip() == "SHOW RELATIONSHIP TYPES",
            records=[{"relationshipType": "ACTED_IN"}],
        )
        # SHOW PROPERTY KEYS
        fake_session.add_response(
            lambda q: q.strip() == "SHOW PROPERTY KEYS",
            records=[{"propertyKey": "name"}, {"propertyKey": "born"}],
        )
        # Label 计数
        fake_session.add_response(
            lambda q: "count(n) AS c" in q and ":Person" in q,
            records=[{"c": 2}],
        )
        fake_session.add_response(
            lambda q: "count(n) AS c" in q and ":Movie" in q,
            records=[{"c": 0}],
        )
        # sampleProperties（每 Label 前 5 条）
        fake_session.add_response(
            lambda q: "ORDER BY elementId(n) LIMIT 5" in q and ":Person" in q,
            records=[{"n": FakeNode("e1", ["Person"], {"name": "Tom", "born": 1962})}],
        )
        fake_session.add_response(
            lambda q: "ORDER BY elementId(n) LIMIT 5" in q and ":Movie" in q,
            records=[],
        )
        # 关系计数
        fake_session.add_response(
            lambda q: "count(r) AS c" in q and "ACTED_IN" in q,
            records=[{"c": 3}],
        )

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/schema")
        assert r.status_code == 200, r.text
        body = r.json()

        # labels 按字母序返回（Movie 在 Person 前），按 name 建索引断言
        labels_by_name = {item["name"]: item for item in body["labels"]}
        assert labels_by_name["Person"] == {
            "name": "Person",
            "count": 2,
            "estimated": False,
            "sampleProperties": ["born", "name"],
        }
        # 空 Label 契约：count=0、estimated=False、sampleProperties=[]
        assert labels_by_name["Movie"] == {
            "name": "Movie",
            "count": 0,
            "estimated": False,
            "sampleProperties": [],
        }
        assert body["relationshipTypes"] == [{"name": "ACTED_IN", "count": 3}]
        assert body["propertyKeys"] == ["born", "name"]

    def test_schema_count_timeout_degrades_to_estimate(self, client):
        """计数查询超时 → 采样估算并标记 estimated=True。"""

        async def timeout_run(cypher, params=None):
            raise asyncio.TimeoutError()

        c, fake_session, _ = client
        conn_id = _create_connection(c)

        # 用会抛 TimeoutError 的 run 覆盖（仅对 count 查询生效）
        original_run = fake_session.run

        async def selective_timeout_run(cypher, params=None):
            if "count(n) AS c" in cypher:
                raise asyncio.TimeoutError()
            return await original_run(cypher, params)

        fake_session.run = selective_timeout_run

        fake_session.add_response(
            lambda q: q.strip() == "SHOW LABELS",
            records=[{"label": "Person"}],
        )
        fake_session.add_response(
            lambda q: q.strip() == "SHOW RELATIONSHIP TYPES",
            records=[],
        )
        fake_session.add_response(
            lambda q: q.strip() == "SHOW PROPERTY KEYS",
            records=[{"propertyKey": "name"}],
        )
        # 采样估算（超时后的 fallback）
        fake_session.add_response(
            lambda q: "MATCH (n:Person) RETURN n LIMIT 100" in q,
            records=[{"n": FakeNode("e1", ["Person"], {"name": "A"})} for _ in range(3)],
        )
        # sampleProperties 采样
        fake_session.add_response(
            lambda q: "ORDER BY elementId(n) LIMIT 5" in q and ":Person" in q,
            records=[{"n": FakeNode("e1", ["Person"], {"name": "A"})}],
        )

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/schema")
        assert r.status_code == 200, r.text
        body = r.json()

        assert body["labels"][0]["estimated"] is True
        assert body["labels"][0]["count"] == 3  # 采样 3 条
        assert body["labels"][0]["sampleProperties"] == ["name"]

    def test_schema_empty_database(self, client):
        """空库：三个数组均为空。"""
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        fake_session.add_response(lambda q: q.strip() == "SHOW LABELS", records=[])
        fake_session.add_response(lambda q: q.strip() == "SHOW RELATIONSHIP TYPES", records=[])
        fake_session.add_response(lambda q: q.strip() == "SHOW PROPERTY KEYS", records=[])

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/schema")
        assert r.status_code == 200
        body = r.json()
        assert body == {"labels": [], "relationshipTypes": [], "propertyKeys": []}

    def test_schema_404_for_other_user(self, client):
        c, _, _ = client
        r = c.get(f"/api/neo4j-tool/connections/{uuid.uuid4()}/schema")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Sample 接口
# ---------------------------------------------------------------------------
class TestSampleApi:
    def test_sample_returns_unified_graph(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        node_a = FakeNode("e1", ["Person"], {"name": "Tom"})
        node_b = FakeNode("e2", ["Person"], {"name": "Alice"})
        rel = FakeRelationship("r1", "ACTED_IN", node_a, node_b, {"roles": ["Neo"]})

        fake_session.add_response(
            lambda q: "CALL" in q and "MATCH (n:Person)" in q,
            records=[{"sampled": [node_a, node_b], "r": rel}],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/sample",
            json={"labels": ["Person"], "relTypes": [], "nodeLimitPerLabel": 200, "relLimit": 500},
        )
        assert r.status_code == 200, r.text
        body = r.json()

        assert len(body["nodes"]) == 2
        assert body["nodes"][0]["id"] == "e1"
        assert body["nodes"][0]["labels"] == ["Person"]
        assert body["nodes"][0]["properties"]["name"] == "Tom"

        assert len(body["relationships"]) == 1
        assert body["relationships"][0]["id"] == "r1"
        assert body["relationships"][0]["type"] == "ACTED_IN"
        assert body["relationships"][0]["source"] == "e1"
        assert body["relationships"][0]["target"] == "e2"
        assert "truncated" in body

    def test_sample_empty_result(self, client):
        """空数据：节点与关系均为空数组，不报错。"""
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        fake_session.add_response(
            lambda q: "CALL" in q,
            records=[],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/sample",
            json={"labels": ["NonExistent"], "relTypes": [], "nodeLimitPerLabel": 10, "relLimit": 10},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["nodes"] == []
        assert body["relationships"] == []
        assert body["truncated"] is False

    def test_sample_deduplicates_nodes_and_rels(self, client):
        """同一节点/关系在多条记录中重复出现时按 elementId 去重。"""
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        node_a = FakeNode("e1", ["Person"], {"name": "Tom"})
        node_b = FakeNode("e2", ["Person"], {"name": "Alice"})
        rel = FakeRelationship("r1", "ACTED_IN", node_a, node_b, {})

        fake_session.add_response(
            lambda q: "CALL" in q,
            records=[
                {"sampled": [node_a], "r": rel},
                {"sampled": [node_b], "r": rel},
            ],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/sample",
            json={"labels": ["Person"], "relTypes": [], "nodeLimitPerLabel": 10, "relLimit": 10},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["nodes"]) == 2
        assert len(body["relationships"]) == 1

    def test_sample_rel_types_filter(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        node_a = FakeNode("e1", ["Person"], {"name": "Tom"})
        node_b = FakeNode("e2", ["Movie"], {"title": "M"})
        rel = FakeRelationship("r1", "ACTED_IN", node_a, node_b, {})

        fake_session.add_response(
            lambda q: "MATCH (a)-[r:ACTED_IN]->(b)" in q,
            records=[{"sampled": [node_a, node_b], "r": rel}],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/sample",
            json={"labels": ["Person", "Movie"], "relTypes": ["ACTED_IN"], "nodeLimitPerLabel": 10, "relLimit": 10},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["relationships"]) == 1


# ---------------------------------------------------------------------------
# Expand 接口
# ---------------------------------------------------------------------------
class TestExpandApi:
    def test_expand_returns_graph_and_total(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        center = FakeNode("center-1", ["Person"], {"name": "Tom"})
        neighbor = FakeNode("n2", ["Movie"], {"title": "M"})
        rel = FakeRelationship("r1", "ACTED_IN", center, neighbor, {})

        # 主查询（取邻居）
        fake_session.add_response(
            lambda q: "SKIP $offset LIMIT $limit" in q,
            records=[{"n": center, "r": rel, "m": neighbor}],
        )
        # total 统计查询
        fake_session.add_response(
            lambda q: "count(r) AS total" in q,
            records=[{"total": 5}],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/expand",
            json={"nodeId": "center-1", "direction": "out", "relTypes": [], "limit": 50, "offset": 0},
        )
        assert r.status_code == 200, r.text
        body = r.json()

        assert body["total"] == 5
        assert len(body["graph"]["nodes"]) == 2
        assert len(body["graph"]["relationships"]) == 1
        assert body["graph"]["relationships"][0]["source"] == "center-1"

    def test_expand_total_none_when_count_times_out(self, client):
        """total 统计超时 → total 为 null，graph 数据不受影响（前端显示"继续加载"）。"""
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        center = FakeNode("center-1", ["Person"], {"name": "Tom"})
        neighbor = FakeNode("n2", ["Movie"], {"title": "M"})
        rel = FakeRelationship("r1", "ACTED_IN", center, neighbor, {})

        # 主查询正常返回
        fake_session.add_response(
            lambda q: "SKIP $offset LIMIT $limit" in q,
            records=[{"n": center, "r": rel, "m": neighbor}],
        )

        # total 统计查询超时
        original_run = fake_session.run

        async def timeout_on_count_run(cypher, params=None):
            if "count(r) AS total" in cypher:
                raise asyncio.TimeoutError()
            return await original_run(cypher, params)

        fake_session.run = timeout_on_count_run

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/expand",
            json={"nodeId": "center-1", "direction": "both", "relTypes": [], "limit": 50, "offset": 0},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] is None
        assert len(body["graph"]["nodes"]) == 2
        assert len(body["graph"]["relationships"]) == 1

    def test_expand_empty_result(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        fake_session.add_response(
            lambda q: "SKIP $offset LIMIT $limit" in q,
            records=[],
        )
        fake_session.add_response(
            lambda q: "count(r) AS total" in q,
            records=[{"total": 0}],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/expand",
            json={"nodeId": "center-1", "direction": "both", "relTypes": [], "limit": 50, "offset": 0},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["graph"]["nodes"] == []
        assert body["graph"]["relationships"] == []
        assert body["total"] == 0

    def test_expand_deduplicates_across_pages(self, client):
        """已存在于画布的节点/关系由前端去重，但后端也要对返回结果去重。"""
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        center = FakeNode("center-1", ["Person"], {})
        n2 = FakeNode("n2", ["Movie"], {})
        r1 = FakeRelationship("r1", "ACTED_IN", center, n2, {})
        r2 = FakeRelationship("r2", "ACTED_IN", center, n2, {})

        fake_session.add_response(
            lambda q: "SKIP $offset LIMIT $limit" in q,
            records=[
                {"n": center, "r": r1, "m": n2},
                {"n": center, "r": r2, "m": n2},
            ],
        )
        fake_session.add_response(
            lambda q: "count(r) AS total" in q,
            records=[{"total": 2}],
        )

        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/graph/expand",
            json={"nodeId": "center-1", "direction": "both", "relTypes": [], "limit": 50, "offset": 0},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["graph"]["nodes"]) == 2
        assert len(body["graph"]["relationships"]) == 2
        assert body["total"] == 2


# ---------------------------------------------------------------------------
# Search 接口
# ---------------------------------------------------------------------------
class TestSearchApi:
    def test_search_returns_nodes(self, client):
        c, fake_session, fake_driver = client
        conn_id = _create_connection(c)

        node = FakeNode("e1", ["Person"], {"name": "Tom"})

        fake_session.add_response(
            lambda q: "CONTAINS $q" in q,
            records=[{"n": node}],
        )

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/nodes/search?q=Tom&limit=20")
        assert r.status_code == 200, r.text
        body = r.json()

        assert len(body["nodes"]) == 1
        assert body["nodes"][0]["id"] == "e1"
        assert body["nodes"][0]["properties"]["name"] == "Tom"
        assert body["relationships"] == []
        assert "truncated" in body

        # 所有图数据接口都必须走只读 session
        assert fake_driver.last_session_kwargs["default_access_mode"] == "READ"

    def test_search_empty_result(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        fake_session.add_response(
            lambda q: "CONTAINS $q" in q,
            records=[],
        )

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/nodes/search?q=zzz")
        assert r.status_code == 200
        body = r.json()
        assert body["nodes"] == []
        assert body["relationships"] == []

    def test_search_deduplicates_nodes(self, client):
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        node = FakeNode("e1", ["Person"], {"name": "Tom"})

        fake_session.add_response(
            lambda q: "CONTAINS $q" in q,
            records=[{"n": node}, {"n": node}],
        )

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/nodes/search?q=Tom")
        assert r.status_code == 200
        body = r.json()
        assert len(body["nodes"]) == 1

    def test_search_limit_enforced(self, client):
        """limit 超过 500 上限应返回 422（FastAPI Query 校验）。"""
        c, _, _ = client
        conn_id = _create_connection(c)

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/nodes/search?q=Tom&limit=1000")
        assert r.status_code == 422

    def test_search_limit_max_ok(self, client):
        """limit=500 边界值应通过。"""
        c, fake_session, _ = client
        conn_id = _create_connection(c)

        fake_session.add_response(
            lambda q: "CONTAINS $q" in q,
            records=[],
        )

        r = c.get(f"/api/neo4j-tool/connections/{conn_id}/nodes/search?q=Tom&limit=500")
        assert r.status_code == 200
        body = r.json()
        assert body["nodes"] == []
