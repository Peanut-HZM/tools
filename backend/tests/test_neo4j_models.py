# backend/tests/test_neo4j_models.py
"""Neo4j 连接模型的单测（隔离内存 SQLite，不触生产库）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.neo4j_models import (
    Neo4jConnection,
    Neo4jConnectionResponse,
)


def _make_session():
    # 内存 SQLite，仅建本任务涉及的表
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[Neo4jConnection.__table__])
    return sessionmaker(bind=engine)()


def test_model_crud_with_in_memory_sqlite():
    session = _make_session()
    conn = Neo4jConnection(
        id="conn-1",
        user_id="user-1",
        name="本地库",
        uri="bolt://localhost:7687",
        username="neo4j",
        encrypted_password="gAAAAAB_cipher",
        database="neo4j",
        readonly=True,
    )
    session.add(conn)
    session.commit()

    row = session.query(Neo4jConnection).filter_by(id="conn-1").one()
    assert row.name == "本地库"
    assert row.uri == "bolt://localhost:7687"
    assert row.database == "neo4j"
    assert row.readonly is True
    assert row.encrypted_password == "gAAAAAB_cipher"
    assert row.created_at is not None
    assert row.updated_at is not None
    session.close()


def test_response_from_attributes_excludes_password():
    session = _make_session()
    conn = Neo4jConnection(
        id="conn-2",
        user_id="user-2",
        name="只读库",
        uri="bolt://192.168.1.10:7687",
        username="reader",
        encrypted_password="gAAAAAB_secret",
        database="neo4j",
        readonly=True,
    )
    session.add(conn)
    session.commit()
    session.refresh(conn)

    resp = Neo4jConnectionResponse.model_validate(conn)
    assert resp.id == "conn-2"
    assert resp.name == "只读库"
    assert resp.username == "reader"
    # 响应模型不含任何密码/密文字段
    assert not hasattr(resp, "password")
    assert not hasattr(resp, "encrypted_password")
    assert "secret" not in resp.model_dump_json()
    session.close()
