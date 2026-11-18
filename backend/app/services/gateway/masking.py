"""隐私掩码（对齐 magpie 的 Privacy → Masking）

在请求**离开本机之前**把敏感值换成占位符，在回复**回给 agent 之前**换回来。

* 规则识别：API Key、私钥、JWT、邮箱、卡号/身份证（校验位）、自定义词
* 占位符：``{{KIND_hash6}}``，同一个值永远是同一个占位符（保证 prompt cache 有效）
* **只在内存中**保存映射，绝不落盘
* 掩码关闭时零开销（直接放行）
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable

#: 规则：(名称, 正则, 是否默认启用)
DEFAULT_RULES: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("API_KEY", re.compile(r"\b(?:sk|vela_ctrl|cp|pk|rk)[-_][A-Za-z0-9_\-]{16,}\b"), True),
    ("API_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"), True),
    ("API_KEY", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"), True),
    ("API_KEY", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"), True),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]{1,20000}?-----END [A-Z ]*PRIVATE KEY-----"), True),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), True),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@(?!example\.com|example\.org|example\.net|test\b|invalid\b)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), True),
    ("CARD", re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13})\b"), False),
    ("CN_ID", re.compile(r"\b\d{17}[\dXx]\b"), False),
)


def _luhn_ok(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 12:
        return False
    checksum = 0
    parity = len(digits) % 2
    for idx, digit in enumerate(digits):
        if idx % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


@dataclass
class MaskingSession:
    """一次请求的掩码会话（映射只存在于本对象里）"""

    enabled: bool = True
    extra_words: tuple[str, ...] = ()
    mask_cards: bool = False
    mask_ids: bool = False
    #: 占位符 → 原值（只在本会话内存中）
    mapping: dict[str, str] = field(default_factory=dict)

    def _placeholder(self, kind: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:6]
        return f"{{{{{kind}_{digest}}}}}"

    def _extra_pattern(self) -> re.Pattern[str] | None:
        words = [w for w in self.extra_words if len(w) >= 3]
        if not words:
            return None
        alternation = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        return re.compile(alternation)

    def mask(self, text: str) -> tuple[str, int]:
        """返回 (掩码后文本, 命中的值数量)"""
        if not self.enabled or not text:
            return text, 0

        hits = 0
        result = text

        for kind, pattern, default_on in DEFAULT_RULES:
            if kind == "CARD" and not self.mask_cards:
                continue
            if kind == "CN_ID" and not self.mask_ids:
                continue
            if not default_on and kind not in ("CARD", "CN_ID"):
                continue

            def _replace(match: re.Match[str]) -> str:
                nonlocal hits
                value = match.group(0)
                if kind == "CARD" and not _luhn_ok(value):
                    return value
                hits += 1
                placeholder = self._placeholder(kind, value)
                self.mapping.setdefault(placeholder, value)
                return placeholder

            result = pattern.sub(_replace, result)

        extra = self._extra_pattern()
        if extra is not None:
            def _replace_extra(match: re.Match[str]) -> str:
                nonlocal hits
                hits += 1
                value = match.group(0)
                placeholder = self._placeholder("CUSTOM", value)
                self.mapping.setdefault(placeholder, value)
                return placeholder

            result = extra.sub(_replace_extra, result)

        return result, hits

    def unmask(self, text: str) -> str:
        """把占位符换回原值"""
        if not self.mapping or not text:
            return text
        result = text
        for placeholder, value in self.mapping.items():
            if placeholder in result:
                result = result.replace(placeholder, value)
        return result

    def unmask_obj(self, obj):
        """递归还原（用于 JSON 响应体）"""
        if not self.mapping:
            return obj
        if isinstance(obj, str):
            return self.unmask(obj)
        if isinstance(obj, dict):
            return {self.unmask(k) if isinstance(k, str) else k: self.unmask_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.unmask_obj(item) for item in obj]
        return obj


def mask_request_body(body: dict, session: MaskingSession) -> tuple[dict, int]:
    """掩码一个请求体（只处理文本字段，结构不变）"""
    if not session.enabled:
        return body, 0

    total = 0

    def walk(node):
        nonlocal total
        if isinstance(node, str):
            masked, hits = session.mask(node)
            total += hits
            return masked
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(body), total


def mask_text_fields(texts: Iterable[str], session: MaskingSession) -> tuple[list[str], int]:
    total = 0
    out: list[str] = []
    for text in texts:
        masked, hits = session.mask(text)
        total += hits
        out.append(masked)
    return out, total
