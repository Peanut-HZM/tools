"""EvalService — Agent 评估框架

P3-⑨ Agent 评估框架
评估闭环：用例集 → 逐 case 生成回答（agent 的 system_prompt + 模型路径）
→ LLM Judge 打分（0-1 + reasoning）→ run/case 落库 → 聚合报告。

单 case 失败不阻断整体；judge 输出解析失败降级 score=0。
"""
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

# judge 输出中提取 JSON 的正则（容忍前后噪声）
_JSON_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)

_JUDGE_SYSTEM_PROMPT = (
    "你是严格的 Agent 回答质量评估员。给定【用户输入】【期望标准】【实际回答】，"
    "评估实际回答是否满足期望标准。只输出一个 JSON 对象，"
    '格式：{"score": 0到1之间的数字, "reasoning": "评分理由（中文，一句话）"}，'
    "不要输出任何其他内容。"
)


def parse_judge_output(raw: str) -> Tuple[float, str]:
    """解析 judge 输出为 (score, reasoning)。

    容忍前后噪声（正则提取首个 JSON 对象）；score 越界 clamp 到 [0,1]；
    完全不可解析返回 (0.0, "judge 输出解析失败")。
    """
    fallback: Tuple[float, str] = (0.0, "judge 输出解析失败")
    if not raw or not isinstance(raw, str):
        return fallback
    match = _JSON_RE.search(raw)
    if not match:
        return fallback
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return fallback
    try:
        score = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        return fallback
    score = max(0.0, min(1.0, score))
    reasoning = str(data.get("reasoning") or "")[:500]
    return score, reasoning


class EvalService:
    """评估服务：生成回答 + judge 打分 + 聚合落库"""

    def __init__(self, db: DBSession, bridge):
        """
        Args:
            db: DB session
            bridge: LLMFunctionBridge（测试注入 Fake；需支持
                generate(messages, tools=[]) -> 含 text_part 的响应）
        """
        self._db = db
        self._bridge = bridge

    async def run_eval(
        self,
        agent,
        user_id: uuid.UUID,
        name: str,
        cases: List[dict],
        judge_threshold: float = 0.7,
    ):
        """执行一次评测批次，返回落库后的 AgentEvalRun

        Args:
            agent: Agent ORM（使用 system_prompt 与模型路径）
            user_id: 发起评测的用户
            name: 批次名称
            cases: [{"input": str, "expected": str}]
            judge_threshold: score >= threshold 计入 passed
        """
        from app.models.agent_eval import AgentEvalRun, AgentEvalCase

        run = AgentEvalRun(
            agent_id=uuid.UUID(str(agent.id)),
            user_id=user_id,
            name=name,
            status="running",
            total_cases=len(cases),
        )
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)

        started = time.monotonic()
        scores: List[float] = []
        passed = 0
        try:
            for case_def in cases:
                case_input = str(case_def.get("input") or "")
                expected = str(case_def.get("expected") or "")
                case_row = AgentEvalCase(
                    run_id=run.id, input=case_input, expected=expected
                )
                case_started = time.monotonic()
                try:
                    # 1. 生成回答
                    answer = await self._generate_answer(agent, case_input)
                    # 2. judge 打分
                    score, reasoning = await self._judge(case_input, expected, answer)
                    case_row.actual_output = answer
                    case_row.score = score
                    case_row.judge_reasoning = reasoning
                    case_row.status = "success"
                    scores.append(score)
                    if score >= judge_threshold:
                        passed += 1
                except Exception as e:
                    # 单 case 失败不阻断整体
                    logger.warning(
                        "eval case 失败 run=%s: %s", run.id, type(e).__name__
                    )
                    case_row.status = "error"
                    case_row.score = 0.0
                    case_row.judge_reasoning = f"执行失败: {type(e).__name__}"
                    scores.append(0.0)
                case_row.latency_ms = int((time.monotonic() - case_started) * 1000)
                self._db.add(case_row)

            run.status = "completed"
            run.passed_cases = passed
            run.avg_score = sum(scores) / len(scores) if scores else 0.0
        except Exception as e:
            logger.error("eval run 失败 run=%s: %s", run.id, type(e).__name__, exc_info=True)
            run.status = "failed"
            run.error = f"批次执行失败: {type(e).__name__}"
        finally:
            run.total_duration_ms = int((time.monotonic() - started) * 1000)
            run.completed_at = datetime.utcnow()
            self._db.commit()
            self._db.refresh(run)
        return run

    async def _generate_answer(self, agent, case_input: str) -> str:
        """用 agent 的 system_prompt + 模型路径生成回答"""
        messages = [
            {"role": "system", "content": getattr(agent, "system_prompt", "") or ""},
            {"role": "user", "content": case_input},
        ]
        resp = await self._bridge.generate(messages=messages, tools=[])
        return getattr(resp, "text_part", "") or ""

    async def _judge(
        self, case_input: str, expected: str, actual: str
    ) -> Tuple[float, str]:
        """LLM Judge 打分，解析失败降级 (0.0, 解析失败标注)"""
        judge_messages = [
            {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"【用户输入】\n{case_input}\n\n"
                    f"【期望标准】\n{expected}\n\n"
                    f"【实际回答】\n{actual}"
                ),
            },
        ]
        resp = await self._bridge.generate(messages=judge_messages, tools=[])
        raw = getattr(resp, "text_part", "") or ""
        return parse_judge_output(raw)
