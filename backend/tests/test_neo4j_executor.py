"""Neo4j Cypher 只读执行器（executor）单元测试。

覆盖四组重点（brief Review Focus 2、3）：
1. validate_readonly：写关键字拒绝（含大小写混合、LOAD CSV）、白名单开头、
   字符串字面量 / 反引号 / 注释内的写关键字不误伤。
2. enforce_limit：各形态语句的 LIMIT 追加 / 不重复追加。
3. serialize_value：Node / Relationship / Path / 标量 / 列表 / Map 递归序列化。
4. run_query：混合行（标量 + Node + Path）结构、truncated 语义、graph 去重、
   以及只读校验在到达 driver 之前拦截写语句。
路由层错误映射（400 只读 / 400 语法 / 408 超时）也一并覆盖。
"""
import asyncio
import os
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock

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
from app.services.neo4j import executor


# ---------------------------------------------------------------------------
# 伪造的 Neo4j 值对象（与 test_neo4j_graph_api.py 同款，最小自洽）
# ---------------------------------------------------------------------------
class FakeNode(dict):
    """支持 dict(node) 的伪 Node。"""

    def __init__(self, element_id: str, labels: List[str], props: Dict[str, Any]):
        super().__init__(props)
        self.element_id = element_id
        self.labels = labels


class FakeRelationship(dict):
    """支持 dict(rel) 的伪 Relationship。"""

    def __init__(self, element_id: str, rel_type: str, start_id: str, end_id: str,
                 props: Dict[str, Any]):
        super().__init__(props)
        self.element_id = element_id
        self.type = rel_type
        self.start_element_id = start_id
        self.end_element_id = end_id


class FakePath:
    """伪 Path：nodes / relationships 两个序列。"""

    def __init__(self, nodes: List[FakeNode], relationships: List[FakeRelationship]):
        self.nodes = nodes
        self.relationships = relationships


class FakeAsyncResult:
    """可异步迭代的查询结果。"""

    def __init__(self, records: List[Dict[str, Any]]):
        self._records = records

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for record in self._records:
            yield record


class FakeAsyncTransaction:
    """伪 AsyncTransaction：run() 记录语句并返回预设结果，可注入异常。"""

    def __init__(self, records: List[Dict[str, Any]], exc: Exception | None = None):
        self._records = records
        self._exc = exc
        self.ran_cyphers: List[str] = []
        self.committed = False

    async def run(self, cypher: str, **kwargs):
        self.ran_cyphers.append(cypher)
        if self._exc is not None:
            raise self._exc
        return FakeAsyncResult(self._records)

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class FakeAsyncSession:
    """伪 AsyncSession：begin_transaction 返回伪事务。"""

    def __init__(self, tx: FakeAsyncTransaction):
        self._tx = tx
        self.session_kwargs: Dict[str, Any] = {}
        self.tx_kwargs: Dict[str, Any] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def begin_transaction(self, **kwargs):
        self.tx_kwargs = kwargs
        return self._tx


class FakeAsyncDriver:
    """伪 AsyncDriver：session() 返回伪 session。"""

    def __init__(self, session: FakeAsyncSession):
        self._session = session

    def session(self, **kwargs):
        self._session.session_kwargs = kwargs
        return self._session


# ---------------------------------------------------------------------------
# 1. validate_readonly —— 写关键字拒绝 / 白名单接受 / 字面量不误伤
# ---------------------------------------------------------------------------
class TestValidateReadonly:
    @pytest.mark.parametrize("cypher", [
        "CREATE (n:Person {name: 'x'})",
        "create (n:Person)",
        "MERGE (n:Person {name: 'x'})",
        "DELETE n",
        "DETACH DELETE n",
        "SET n.name = 'x'",
        "sEt n.name = 'x'",  # 大小写混合
        "REMOVE n.name",
        "FOREACH (x IN [1,2] | SET n.x = x)",
        "LOAD CSV FROM 'file:///x.csv' AS line CREATE (n)",
        "DROP INDEX foo",
        "GRANT READ ON GRAPH * TO role",
        "REVOKE READ ON GRAPH * FROM role",
    ])
    def test_rejects_write_keywords(self, cypher):
        with pytest.raises(executor.ReadonlyViolation) as exc_info:
            executor.validate_readonly(cypher)
        assert "只读" in str(exc_info.value)

    @pytest.mark.parametrize("cypher", [
        "MATCH (n) RETURN n",
        "match (n) return n",
        "RETURN 1",
        "// 行注释\nMATCH (n) RETURN n",
        "/* 块注释 */ MATCH (n) RETURN n",
        "  \n  MATCH (n) RETURN n",  # 前导空白
        "OPTIONAL MATCH (n)-[r]->(m) RETURN n, m",
        "UNWIND [1,2,3] AS x RETURN x",
        "WITH 1 AS x RETURN x",
        "CALL db.labels()",
        "SHOW LABELS",
        "DESCRIBE MATCH (n) RETURN n",
        "EXPLAIN MATCH (n) RETURN n",
    ])
    def test_accepts_readonly_statements(self, cypher):
        executor.validate_readonly(cypher)  # 不抛异常即通过

    def test_write_keyword_in_string_literal_not_flagged(self):
        """字符串字面量内的写关键字不得误伤（Review Focus 2 核心）。"""
        executor.validate_readonly('MATCH (n) WHERE n.name = "CREATE" RETURN n')
        executor.validate_readonly("MATCH (n) WHERE n.name = 'DELETE SET' RETURN n")
        executor.validate_readonly('MATCH (n) WHERE n.name = "LOAD CSV" RETURN n')

    def test_write_keyword_in_backticks_not_flagged(self):
        """反引号转义标识符内的关键字不误伤。"""
        executor.validate_readonly("MATCH (n:`SET`) RETURN n")

    def test_comment_then_write_rejected(self):
        """注释之后紧跟写关键字仍要拒绝。"""
        with pytest.raises(executor.ReadonlyViolation):
            executor.validate_readonly("// 注释\nCREATE (n)")

    def test_empty_or_whitespace_rejected(self):
        with pytest.raises(executor.ReadonlyViolation):
            executor.validate_readonly("")
        with pytest.raises(executor.ReadonlyViolation):
            executor.validate_readonly("   \n  ")


# ---------------------------------------------------------------------------
# 2. enforce_limit —— LIMIT 强制
# ---------------------------------------------------------------------------
class TestEnforceLimit:
    def test_appends_limit_when_missing(self):
        new_cypher, appended = executor.enforce_limit("MATCH (n) RETURN n", 500)
        assert appended is True
        assert new_cypher.rstrip().endswith("LIMIT 500")

    def test_no_duplicate_limit(self):
        new_cypher, appended = executor.enforce_limit(
            "MATCH (n) RETURN n LIMIT 10", 500
        )
        assert appended is False
        assert "LIMIT 10" in new_cypher
        assert "LIMIT 500" not in new_cypher

    def test_case_insensitive_existing_limit(self):
        new_cypher, appended = executor.enforce_limit(
            "MATCH (n) RETURN n limit 10", 500
        )
        assert appended is False

    def test_call_subquery_heuristic_fallback(self):
        """CALL { ... } 子查询等复杂语句：启发式失败时安全追加 LIMIT。"""
        cypher = "CALL { MATCH (n) RETURN n LIMIT 5 } RETURN *"
        new_cypher, appended = executor.enforce_limit(cypher, 500)
        assert appended is True
        assert new_cypher.rstrip().endswith("LIMIT 500")
        # 原语句内容必须保持原样（只追加，不破坏）
        assert cypher in new_cypher

    def test_limit_in_string_not_counted(self):
        """字符串字面量里的 LIMIT 不算已有限制。"""
        new_cypher, appended = executor.enforce_limit(
            'MATCH (n) WHERE n.tip = "use LIMIT wisely" RETURN n', 500
        )
        assert appended is True
        assert new_cypher.rstrip().endswith("LIMIT 500")


# ---------------------------------------------------------------------------
# 3. serialize_value —— 各类型序列化（§6.5 表）
# ---------------------------------------------------------------------------
class TestSerializeValue:
    def test_node(self):
        node = FakeNode("e1", ["Person"], {"name": "Tom", "born": 1962})
        assert executor.serialize_value(node) == {
            "__type": "node",
            "elementId": "e1",
            "labels": ["Person"],
            "properties": {"name": "Tom", "born": 1962},
        }

    def test_relationship(self):
        rel = FakeRelationship("r1", "ACTED_IN", "e1", "e2", {"roles": ["Neo"]})
        assert executor.serialize_value(rel) == {
            "__type": "relationship",
            "elementId": "r1",
            "type": "ACTED_IN",
            "startElementId": "e1",
            "endElementId": "e2",
            "properties": {"roles": ["Neo"]},
        }

    def test_path(self):
        n1 = FakeNode("e1", ["Person"], {"name": "Tom"})
        n2 = FakeNode("e2", ["Movie"], {"title": "M"})
        rel = FakeRelationship("r1", "ACTED_IN", "e1", "e2", {})
        path = FakePath([n1, n2], [rel])
        result = executor.serialize_value(path)
        assert result["__type"] == "path"
        assert len(result["nodes"]) == 2
        assert result["nodes"][0]["__type"] == "node"
        assert result["nodes"][0]["elementId"] == "e1"
        assert len(result["relationships"]) == 1
        assert result["relationships"][0]["__type"] == "relationship"
        assert result["relationships"][0]["elementId"] == "r1"

    @pytest.mark.parametrize("value", [
        42, 3.14, "hello", True, None,
    ])
    def test_scalars_passthrough(self, value):
        assert executor.serialize_value(value) == value

    def test_list_recursive(self):
        node = FakeNode("e1", ["Person"], {"name": "Tom"})
        result = executor.serialize_value([1, "x", node])
        assert result[0] == 1
        assert result[1] == "x"
        assert result[2]["__type"] == "node"

    def test_dict_recursive(self):
        node = FakeNode("e1", ["Person"], {"name": "Tom"})
        result = executor.serialize_value({"n": node, "tags": ["a", 1]})
        assert result["n"]["__type"] == "node"
        assert result["tags"] == ["a", 1]

    def test_bytes_fallback(self):
        """无法 JSON 化的类型（如 bytes）退化为字符串表示，不抛异常。"""
        result = executor.serialize_value(b"\x01\x02")
        assert isinstance(result, str)

    def test_properties_serialized_recursively(self):
        """Node/Relationship 的 properties 必须递归序列化：datetime/bytes 等
        非 JSON 原生类型属性值要经 serialize_value 处理（退化为 str），
        否则 JSON 编码会抛 TypeError（浅拷贝问题）。"""
        class FakeDatetime:
            """模拟 neo4j.time.DateTime 等非 JSON 原生类型（有 __str__）。"""

            def __str__(self):
                return "2024-01-01T00:00:00"

        node = FakeNode("e1", ["Person"], {"name": "Tom", "created": FakeDatetime()})
        result = executor.serialize_value(node)
        # 属性值被递归处理（退化为 str），不再是原始对象
        assert result["properties"]["created"] == "2024-01-01T00:00:00"
        assert not isinstance(result["properties"]["created"], FakeDatetime)

        rel = FakeRelationship("r1", "KNOWS", "e1", "e2", {"since": FakeDatetime()})
        rel_result = executor.serialize_value(rel)
        assert rel_result["properties"]["since"] == "2024-01-01T00:00:00"


# ---------------------------------------------------------------------------
# 4. run_query —— 混合行 / truncated 语义 / graph 去重 / 写语句提前拦截
# ---------------------------------------------------------------------------
def _make_driver_with_records(records: List[Dict[str, Any]], exc: Exception | None = None):
    tx = FakeAsyncTransaction(records, exc=exc)
    session = FakeAsyncSession(tx)
    driver = FakeAsyncDriver(session)
    return driver, session, tx


class TestRunQuery:
    def test_readonly_violation_before_driver(self):
        """写语句在到达 driver 之前就被拒（driver 根本不会被调用）。"""
        driver, session, tx = _make_driver_with_records([])
        with pytest.raises(executor.ReadonlyViolation):
            asyncio.run(executor.run_query(
                driver, "neo4j", "CREATE (n) RETURN n", 500, 30000
            ))
        assert tx.ran_cyphers == []

    def test_mixed_rows_structure(self):
        """标量 + Node + Path 混合行：columns/rows/graph 结构正确。"""
        node_a = FakeNode("e1", ["Person"], {"name": "Tom"})
        node_b = FakeNode("e2", ["Movie"], {"title": "M"})
        rel = FakeRelationship("r1", "ACTED_IN", "e1", "e2", {})
        path = FakePath([node_a, node_b], [rel])
        records = [
            {"count": 1, "n": node_a},
            {"count": 2, "n": path},
        ]
        driver, session, tx = _make_driver_with_records(records)

        result = asyncio.run(executor.run_query(
            driver, "neo4j", "MATCH (n) RETURN count, n", 500, 30000
        ))

        # 列名来自第一条记录
        assert result["columns"] == ["count", "n"]
        assert len(result["rows"]) == 2
        assert result["rows"][0]["count"] == 1
        assert result["rows"][0]["n"]["__type"] == "node"
        assert result["rows"][0]["n"]["elementId"] == "e1"
        assert result["rows"][1]["n"]["__type"] == "path"

        # graph 聚合节点/关系列，按 elementId 去重
        assert len(result["graph"]["nodes"]) == 2
        assert len(result["graph"]["relationships"]) == 1

        # truncated：行数未达到 limit
        assert result["truncated"] is False
        assert result["elapsedMs"] >= 0

        # 只读兜底：session 与事务层均为 READ / 无写
        assert session.session_kwargs.get("default_access_mode") == "READ"

    def test_truncated_when_rows_reach_limit(self):
        """truncated 语义：返回行数达到 limit 即 True。"""
        records = [{"x": i} for i in range(3)]
        driver, _, _ = _make_driver_with_records(records)
        result = asyncio.run(executor.run_query(
            driver, "neo4j", "RETURN x", 3, 30000
        ))
        assert len(result["rows"]) == 3
        assert result["truncated"] is True

    def test_not_truncated_below_limit(self):
        records = [{"x": i} for i in range(2)]
        driver, _, _ = _make_driver_with_records(records)
        result = asyncio.run(executor.run_query(
            driver, "neo4j", "RETURN x", 500, 30000
        ))
        assert result["truncated"] is False

    def test_graph_dedup_by_element_id(self):
        """同一节点在多条记录里重复出现时，graph 中去重。"""
        node = FakeNode("e1", ["Person"], {"name": "Tom"})
        records = [{"n": node}, {"n": node}]
        driver, _, _ = _make_driver_with_records(records)
        result = asyncio.run(executor.run_query(
            driver, "neo4j", "MATCH (n) RETURN n", 500, 30000
        ))
        assert len(result["graph"]["nodes"]) == 1

    def test_empty_result(self):
        driver, _, _ = _make_driver_with_records([])
        result = asyncio.run(executor.run_query(
            driver, "neo4j", "MATCH (n) RETURN n", 500, 30000
        ))
        assert result["columns"] == []
        assert result["rows"] == []
        assert result["graph"] == {"nodes": [], "relationships": []}
        assert result["truncated"] is False

    def test_limit_appended_to_cypher(self):
        """无 LIMIT 的语句执行前被追加 LIMIT。"""
        records = [{"x": 1}]
        driver, _, tx = _make_driver_with_records(records)
        asyncio.run(executor.run_query(
            driver, "neo4j", "MATCH (n) RETURN n", 500, 30000
        ))
        assert len(tx.ran_cyphers) == 1
        assert tx.ran_cyphers[0].rstrip().endswith("LIMIT 500")


# ---------------------------------------------------------------------------
# 5. 路由层：POST /connections/{id}/query 错误映射（§8 错误表）
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

    fake_session = FakeAsyncSession(FakeAsyncTransaction([]))
    fake_driver = FakeAsyncDriver(fake_session)

    async def fake_get_driver(conn_id, uri, username, password):
        return fake_driver

    monkeypatch.setattr(
        dm_module.driver_manager, "get_driver", fake_get_driver
    )
    monkeypatch.setattr(dm_module.driver_manager, "close_driver", AsyncMock())
    monkeypatch.setattr(dm_module.driver_manager, "close_all", AsyncMock())

    # 可注入状态：records 控制返回，exc 控制事务 run 抛出的异常
    state = {"records": [], "exc": None}

    def fake_session_factory(**kwargs):
        fake_session.session_kwargs = kwargs
        fake_session._tx = FakeAsyncTransaction(state["records"], exc=state["exc"])
        return fake_session

    monkeypatch.setattr(fake_driver, "session", fake_session_factory)

    with TestClient(app) as c:
        yield c, state

    app.dependency_overrides.clear()


def _create_connection(client) -> str:
    r = client.post("/api/neo4j-tool/connections", json={
        "name": "test", "uri": "bolt://localhost:7687",
        "username": "neo4j", "password": "secret", "database": "neo4j",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


class TestQueryApi:
    def test_readonly_violation_returns_400(self, client):
        c, _ = client
        conn_id = _create_connection(c)
        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/query",
            json={"cypher": "CREATE (n) RETURN n"},
        )
        assert r.status_code == 400
        assert "只读" in r.json()["detail"]

    def test_syntax_error_returns_400_with_neo4j_message(self, client):
        from neo4j.exceptions import CypherSyntaxError
        c, state = client
        conn_id = _create_connection(c)

        state["exc"] = CypherSyntaxError("Invalid input 'XYZ'")
        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/query",
            json={"cypher": "MATCH XYZ"},
        )
        assert r.status_code == 400
        assert "Invalid input" in r.json()["detail"]

    def test_timeout_returns_408(self, client):
        c, state = client
        conn_id = _create_connection(c)

        # 模拟 driver 层超时异常
        state["exc"] = asyncio.TimeoutError()
        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/query",
            json={"cypher": "MATCH (n) RETURN n"},
        )
        assert r.status_code == 408
        assert "超时" in r.json()["detail"]

    def test_success_returns_result_structure(self, client):
        c, state = client
        conn_id = _create_connection(c)
        node = FakeNode("e1", ["Person"], {"name": "Tom"})
        state["records"] = [{"n": node}]
        r = c.post(
            f"/api/neo4j-tool/connections/{conn_id}/query",
            json={"cypher": "MATCH (n) RETURN n", "limit": 500, "timeoutMs": 30000},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["columns"] == ["n"]
        assert body["rows"][0]["n"]["__type"] == "node"
        assert body["graph"]["nodes"][0]["elementId"] == "e1"
        assert "truncated" in body
        assert "elapsedMs" in body

    def test_404_for_other_user(self, client):
        c, _ = client
        r = c.post(
            f"/api/neo4j-tool/connections/{uuid.uuid4()}/query",
            json={"cypher": "RETURN 1"},
        )
        assert r.status_code == 404
