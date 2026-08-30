"""Harness ORM 模型测试

TDD: 验证新模型可实例化、字段默认值正确、关系能加载。
"""
import uuid as _uuid

import pytest
from app.models.harness_models import Tool, ToolBinding, Trace, TraceStep


def test_tool_model_fields():
    """Tool 模型应有所有 spec 定义的字段，且默认值符合预期"""
    tool = Tool(
        name="test_tool",
        display_name="Test Tool",
        description="A test tool",
        type="builtin",
        config={"module": "x", "class": "Y"},
        parameters_schema={"type": "object", "properties": {}},
    )
    assert tool.name == "test_tool"
    assert tool.type == "builtin"
    assert tool.is_active is True


def test_trace_with_steps(test_db):
    """Trace 应能关联多个 TraceStep"""
    # UUID 列使用 as_uuid=True，必须传 uuid.UUID 对象
    conv_id = _uuid.UUID("00000000-0000-0000-0000-000000000001")
    agent_id = _uuid.UUID("00000000-0000-0000-0000-000000000002")
    user_id = _uuid.UUID("00000000-0000-0000-0000-000000000003")

    trace = Trace(
        conversation_id=conv_id,
        agent_id=agent_id,
        user_id=user_id,
        input_text="hello",
        status="success",
    )
    test_db.add(trace)
    test_db.commit()

    step = TraceStep(trace_id=trace.id, step_index=0, step_type="llm_call", duration_ms=100)
    test_db.add(step)
    test_db.commit()

    loaded = test_db.query(Trace).filter_by(id=trace.id).first()
    assert len(loaded.steps) == 1
    assert loaded.steps[0].step_type == "llm_call"


def test_mcp_server_command_json_column():
    """P2-①c: mcp_servers 表应有 command_json 列（stdio 启动配置）"""
    from app.models.mcp_server import McpServer

    server = McpServer(name="t", server_url="npx -y demo", transport="stdio")
    assert server.command_json is None  # 新列 nullable，默认 None
    server.command_json = '{"command": "npx", "args": ["-y", "demo"]}'
    assert '"command"' in server.command_json


def test_agent_procedural_memory_model():
    """P2-②: agent_procedural_memory 表应可存取技能记录"""
    from app.models.agent_procedural_memory import AgentProceduralMemory

    skill = AgentProceduralMemory(
        agent_id=_uuid.UUID("00000000-0000-0000-0000-000000000002"),
        user_id=_uuid.UUID("00000000-0000-0000-0000-000000000003"),
        name="deploy_check",
        trigger="用户要求部署前检查",
        content="1. 跑测试 2. 检查环境变量",
    )
    # SQLAlchemy 列默认值在 flush 时生效，故对 commit 后的 loaded 断言
    test_db.add(skill)
    test_db.commit()
    loaded = test_db.query(AgentProceduralMemory).filter_by(name="deploy_check").first()
    assert loaded is not None
    assert loaded.trigger == "用户要求部署前检查"
    assert loaded.importance == 0.5
    assert loaded.use_count == 0
    assert loaded.is_enabled is True
