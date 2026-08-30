"""EvalService 单元测试（P3-⑨，Fake bridge 注入）"""
import uuid
from types import SimpleNamespace

import pytest

from app.services.harness.eval_service import EvalService, parse_judge_output

AID = uuid.uuid4()
UID = uuid.uuid4()


def _agent(system_prompt="You are helpful."):
    return SimpleNamespace(id=AID, system_prompt=system_prompt)


class FakeBridge:
    """可编程 Fake：answer 回复按序出队；judge 固定返回"""

    def __init__(self, answers, judge_outputs):
        self.answers = list(answers)
        self.judge_outputs = list(judge_outputs)
        self.calls = []

    async def generate(self, messages, tools=None, **kw):
        self.calls.append(messages)
        # 消息里带"评估员"标记的是 judge 调用
        system = messages[0]["content"] if messages else ""
        if "评估员" in system:
            out = self.judge_outputs.pop(0)
            if isinstance(out, Exception):
                raise out
            return SimpleNamespace(text_part=out)
        out = self.answers.pop(0)
        if isinstance(out, Exception):
            raise out
        return SimpleNamespace(text_part=out)


def _svc(db, bridge):
    return EvalService(db, bridge)


@pytest.mark.asyncio
async def test_run_eval_all_passed(test_db):
    bridge = FakeBridge(
        answers=["回答1", "回答2"],
        judge_outputs=['{"score": 0.9, "reasoning": "很好"}', '{"score": 0.7, "reasoning": "可以"}'],
    )
    run = await _svc(test_db, bridge).run_eval(
        _agent(), UID, "评测1",
        cases=[{"input": "q1", "expected": "e1"}, {"input": "q2", "expected": "e2"}],
    )
    assert run.status == "completed"
    assert run.total_cases == 2
    assert run.passed_cases == 2  # 0.9 与 0.7（==threshold 边界）均计入
    assert abs(run.avg_score - 0.8) < 1e-6
    cases = run.__dict__.get("_cases") or []
    # 通过详情查询复核
    from app.models.agent_eval import AgentEvalCase

    rows = test_db.query(AgentEvalCase).filter_by(run_id=run.id).all()
    assert rows[0].actual_output == "回答1"
    assert rows[0].score == 0.9
    assert rows[1].score == 0.7


@pytest.mark.asyncio
async def test_judge_invalid_json_degrades(test_db):
    bridge = FakeBridge(answers=["答"], judge_outputs=["这不是 JSON"])
    run = await _svc(test_db, bridge).run_eval(
        _agent(), UID, "评测2", cases=[{"input": "q", "expected": "e"}]
    )
    from app.models.agent_eval import AgentEvalCase

    row = test_db.query(AgentEvalCase).filter_by(run_id=run.id).first()
    assert row.score == 0.0
    assert "解析失败" in (row.judge_reasoning or "")
    assert run.status == "completed"


@pytest.mark.asyncio
async def test_single_case_error_does_not_block(test_db):
    bridge = FakeBridge(
        answers=[RuntimeError("LLM down"), "回答2"],
        judge_outputs=['{"score": 1.0, "reasoning": "ok"}'],
    )
    run = await _svc(test_db, bridge).run_eval(
        _agent(), UID, "评测3",
        cases=[{"input": "q1", "expected": "e1"}, {"input": "q2", "expected": "e2"}],
    )
    assert run.status == "completed"
    assert run.total_cases == 2
    assert run.passed_cases == 1
    from app.models.agent_eval import AgentEvalCase

    rows = test_db.query(AgentEvalCase).filter_by(run_id=run.id).all()
    assert rows[0].status == "error"
    assert rows[0].score == 0.0
    assert rows[1].status == "success"


def test_parse_judge_output_variants():
    assert parse_judge_output('{"score": 0.8, "reasoning": "r"}') == (0.8, "r")
    # 前后有噪声：正则兜底提取
    score, reasoning = parse_judge_output('评估结果：{"score": 0.5, "reasoning": "一般"} 完毕')
    assert score == 0.5
    assert reasoning == "一般"
    # 越界 clamp
    assert parse_judge_output('{"score": 5, "reasoning": "x"}')[0] == 1.0
    assert parse_judge_output('{"score": -1, "reasoning": "x"}')[0] == 0.0
    # 完全不可解析
    assert parse_judge_output("no json")[0] == 0.0
