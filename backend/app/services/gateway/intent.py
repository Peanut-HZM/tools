"""意图路由（对齐 magpie 的 Intent routing，但**不调用外部模型**）

magpie 用小模型读每一轮再决定落哪个模型；那需要额外一次 LLM 调用与一个可用的
小模型。本工具用**确定性规则**实现同等目标（测试走强模型、闲聊走便宜模型），
好处是零额外开销、零额外 Key、行为可预测可测试。

规则按顺序匹配，命中即停；未命中时用默认组。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class IntentRule:
    """一条意图规则"""

    name: str
    #: 命中后路由到的目标（``provider/model`` 或 ``group/xxx``）
    target: str
    #: 关键词（大小写不敏感，任一命中即可）
    keywords: tuple[str, ...] = ()
    #: 正则（任一命中即可）
    patterns: tuple[str, ...] = ()
    #: 该规则期望的能力
    capability: Optional[str] = None


@dataclass
class IntentResult:
    rule: str
    target: str
    matched_by: str
    #: 命中的关键词/正则
    token: Optional[str] = None


DEFAULT_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        name="test",
        target="group/coding",
        keywords=(
            "test", "pytest", "vitest", "jest", "unit test", "coverage",
            "测试", "单测", "跑测试", "断言",
        ),
        capability="coding",
    ),
    IntentRule(
        name="code",
        target="group/coding",
        keywords=(
            "refactor", "implement", "bug", "fix", "compile", "typescript",
            "python", "代码", "重构", "实现", "报错", "修复", "编译",
        ),
        patterns=(r"\b(def |class |function |import )",),
        capability="coding",
    ),
    IntentRule(
        name="long-context",
        target="group/long-context",
        keywords=("整个仓库", "全部文件", "全文", "梳理", "review the whole", "whole repo"),
        capability="long_context",
    ),
    IntentRule(
        name="chat",
        target="group/fast",
        keywords=("你好", "hi", "hello", "闲聊", "随便聊聊", "translate", "翻译"),
        capability="fast",
    ),
)


def _last_user_text(messages: list[dict]) -> str:
    """取最后一条 user 消息的文本（兼容 Anthropic / OpenAI 两种结构）"""
    for message in reversed(messages or []):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(block, str):
                    parts.append(block)
            if parts:
                return "\n".join(parts)
    return ""


def classify(
    messages: list[dict],
    rules: tuple[IntentRule, ...] = DEFAULT_RULES,
    default_target: Optional[str] = None,
) -> Optional[IntentResult]:
    """判断这一轮该走哪个目标；无规则命中时返回 ``default_target`` 对应的结果"""
    text = _last_user_text(messages)
    lowered = text.lower()

    for rule in rules:
        for keyword in rule.keywords:
            if keyword.lower() in lowered:
                return IntentResult(
                    rule=rule.name, target=rule.target, matched_by="keyword", token=keyword
                )
        for pattern in rule.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return IntentResult(
                    rule=rule.name, target=rule.target, matched_by="pattern", token=match.group(0)
                )

    if default_target:
        return IntentResult(rule="default", target=default_target, matched_by="default")
    return None


def group_target(target: str) -> Optional[str]:
    """``group/coding`` → ``coding``；不是组前缀时返回 None"""
    if target.startswith("group/"):
        return target[len("group/") :]
    return None
